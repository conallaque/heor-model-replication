"""
HIV/AIDS combination therapy — the DMHEE textbook model, via heemod
====================================================================

Zidovudine monotherapy against zidovudine + lamivudine combination therapy, in a
cohort followed through four states defined by disease severity (A → B → C →
Dead), over 20 annual cycles. This is the worked example from Briggs, Claxton &
Sculpher's *Decision Modelling for Health Economic Evaluation*, itself built on
Chancellor et al. (1997).

**Why this target, when two replications already pass.** The two DARTH models
share a house style: rates converted to probabilities, hazard ratios on single
transitions, QALYs, US dollars, 3% on both costs and effects, Simpson's 1/3
correction. A solver that matches both has been tested against one tradition. This
model disagrees with that tradition on nearly every axis:

============================  ==========================  =========================
Convention                    DARTH tutorials             This model
============================  ==========================  =========================
Outcome measure               QALYs                       **Life-years**
Transition probabilities      from rates, 1 − exp(−r·t)   **from observed counts**
Treatment effect              HR on one transition        **RR on every transition,
                                                          expiring after 2 years**
Discounting                   3% costs, 3% effects        **6% costs, 0% effects**
Cycle counting                Simpson's 1/3 correction    **end-of-cycle, no
                                                          correction**
Currency / era                USD, contemporary           **GBP, 1996**
============================  ==========================  =========================

Matching this one *as well* is what makes the solver's generality a demonstrated
property rather than a design intention.

**Two things to notice, because both are places a re-implementation silently
goes wrong.**

The transition probabilities are raw observed proportions — 1251 of 1734 patients
in state A stayed in A. No rate conversion, because these are not rates; they are
counts from a cohort study. Applying ``1 − exp(−r·t)`` to them, as the DARTH
models do to *their* inputs, would be a category error.

The treatment effect is a relative risk applied to **every** off-diagonal entry,
with the diagonal absorbing the remainder — and it expires. Lamivudine is modelled
as effective for two years, after which the matrix reverts to monotherapy's and
the drug cost stops. A model that applies the effect for all 20 cycles produces a
far more favourable ICER, and nothing in the output flags it.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from cstm.solver import CSTMResult, run_cstm

# ── General setup ─────────────────────────────────────────────────────────────
N_CYCLES = 20                      # cycles = 20
STATES = ("A", "B", "C", "D")      # disease severity; D is death
STRATEGIES = ("Monotherapy", "Combination therapy")

D_C = 0.06                         # discount(..., .06) — costs only
D_E = 0.0                          # life_year is not wrapped in discount()
WCC_METHOD = "end"                 # run_model(method = "end")

# ── Transition counts ─────────────────────────────────────────────────────────
#: Observed transition counts from the monotherapy cohort, written as the
#: fractions the vignette uses. Kept as an integer matrix plus row totals so the
#: provenance stays visible: these are patients, not parameters.
TRANSITION_COUNTS = np.array([
    [1251, 350, 116, 17],          # from A
    [0, 731, 512, 15],             # from B
    [0, 0, 1312, 437],             # from C
], dtype=float)
ROW_TOTALS = np.array([1734.0, 1258.0, 1749.0])

# ── Treatment effect ──────────────────────────────────────────────────────────
RR = 0.509                         # rr — relative risk of progression on 3TC/ZDV
RR_DURATION = 2                    # rr applies while model_time <= 2

# ── Costs (GBP, 1996) ─────────────────────────────────────────────────────────
COST_HEALTH = np.array([2_756.0, 3_052.0, 9_007.0, 0.0])   # cost_health by state
COST_ZIDO = 2_278.0                # cost_zido — both strategies, all cycles
COST_LAMI = 2_086.5                # cost_lami — combination only, cycles 1-2
LAMI_DURATION = 2

# ── Effects ───────────────────────────────────────────────────────────────────
LIFE_YEARS = np.array([1.0, 1.0, 1.0, 0.0])                # life_year by state


def _monotherapy_matrix() -> np.ndarray:
    """The observed transition matrix: counts divided by their row totals."""
    P = np.zeros((4, 4))
    P[:3, :] = TRANSITION_COUNTS / ROW_TOTALS[:, None]
    P[3, 3] = 1.0                                          # death is absorbing
    return P


def _combination_matrix(rr: float) -> np.ndarray:
    """Monotherapy's off-diagonals scaled by ``rr``, diagonals taking the residue.

    This reproduces heemod's ``C`` placeholder, which means "whatever makes this
    row sum to 1". Scaling the progression probabilities and letting the stay-put
    probability absorb the difference is what it means for a treatment to slow
    progression: nobody is created or destroyed, they just move less.
    """
    P = np.zeros((4, 4))
    P[0, 1:] = TRANSITION_COUNTS[0, 1:] / ROW_TOTALS[0] * rr
    P[0, 0] = 1.0 - P[0, 1:].sum()
    P[1, 2:] = TRANSITION_COUNTS[1, 2:] / ROW_TOTALS[1] * rr
    P[1, 1] = 1.0 - P[1, 2:].sum()
    P[2, 3] = TRANSITION_COUNTS[2, 3] / ROW_TOTALS[2] * rr
    P[2, 2] = 1.0 - P[2, 3]
    P[3, 3] = 1.0
    return P


def transition_arrays() -> Dict[str, np.ndarray]:
    """``(20, 4, 4)`` transition arrays.

    Monotherapy's matrix is constant. Combination therapy's varies with time,
    because ``rr = ifelse(model_time <= 2, .509, 1)`` — for cycles 3 onward it is
    monotherapy's matrix exactly.

    ``model_time`` is 1-based in heemod; cycle index ``t`` here corresponds to
    ``model_time = t + 1``.
    """
    mono = _monotherapy_matrix()
    combo = np.array([
        _combination_matrix(RR if (t + 1) <= RR_DURATION else 1.0)
        for t in range(N_CYCLES)
    ])
    return {
        "Monotherapy": np.broadcast_to(mono, (N_CYCLES, 4, 4)).copy(),
        "Combination therapy": combo,
    }


def state_costs(strategy: str) -> np.ndarray:
    """``(21, 4)`` per-cycle state costs — time-varying, because a drug expires.

    Row ``t`` is the cost of occupying each state as counted at the end of cycle
    ``t`` (``model_time = t``). The dead accrue nothing: the vignette gives state
    D ``cost_health = 0`` and ``cost_drugs = 0``, so treatment cost stops at
    death rather than being billed to the estate.
    """
    combo = strategy == "Combination therapy"
    costs = np.zeros((N_CYCLES + 1, 4))
    for t in range(N_CYCLES + 1):
        drugs = COST_ZIDO + (COST_LAMI if (combo and t <= LAMI_DURATION) else 0.0)
        costs[t, :3] = COST_HEALTH[:3] + drugs        # states A, B, C
        costs[t, 3] = 0.0                             # state D accrues nothing
    return costs


def run() -> List[CSTMResult]:
    """Run both strategies and return their results, in table order."""
    P = transition_arrays()
    v_init = np.array([1.0, 0.0, 0.0, 0.0])           # init = c(1, 0, 0, 0)

    return [
        run_cstm(
            P=P[s],
            v_init=v_init,
            n_cycles=N_CYCLES,
            state_costs=state_costs(s),
            state_utils=LIFE_YEARS,
            payoff="state",
            d_c=D_C,
            d_e=D_E,
            wcc=WCC_METHOD,
            state_names=STATES,
            strategy=s,
        )
        for s in STRATEGIES
    ]
