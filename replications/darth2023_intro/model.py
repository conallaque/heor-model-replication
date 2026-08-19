"""
The Sick-Sicker model, time-independent — DARTH introductory cSTM tutorial
=========================================================================

A hypothetical cohort of 25-year-olds moves through Healthy (H) → Sick (S1) →
Sicker (S2), with Dead (D) absorbing, over 75 annual cycles. Four strategies are
compared: standard of care, a treatment that improves quality of life in the Sick
state (A), a treatment that slows progression from Sick to Sicker (B), and both
together (AB).

**Every parameter below is transcribed from the published source code**
(``analysis/cSTM_time_indep.R``, retrieved 2026-08-19 — see
:mod:`reference`). The R variable name is kept next to each so a reviewer can
diff the two files line by line. Nothing is tuned; if a number here does not
appear in that script, it is a bug.

Two structural details are worth calling out, because they are where a
re-implementation drifts:

1. **Transitions are conditional on survival.** ``P[H, S1]`` is
   ``(1 - p_HD) * p_HS1``, not ``p_HS1`` — you have to survive the cycle before
   you can get sick in it. Modelling these as competing risks instead changes the
   answer.
2. **Payoffs are valued on start-of-cycle occupancy** (``trace @ rewards``), with
   Simpson's 1/3 within-cycle correction. The companion time-dependent tutorial
   uses a different convention; see :mod:`replications.darth2023_timedep`.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from cstm.solver import CSTMResult, run_cstm
from cstm.wcc import rate_to_prob

# ── General setup ─────────────────────────────────────────────────────────────
CYCLE_LENGTH = 1          # cycle_length — one year
N_AGE_INIT = 25           # n_age_init
N_AGE_MAX = 100           # n_age_max
N_CYCLES = (N_AGE_MAX - N_AGE_INIT) // CYCLE_LENGTH     # n_cycles = 75
STATES = ("H", "S1", "S2", "D")                          # v_names_states
STRATEGIES = ("Standard of care", "Strategy A", "Strategy B", "Strategy AB")

D_C = 0.03                # d_c — annual discount rate for costs
D_E = 0.03                # d_e — annual discount rate for QALYs
WCC_METHOD = "Simpson1/3"

# ── Transition rates (annual) and hazard ratios ───────────────────────────────
R_HD = 0.002              # r_HD   — all-cause mortality when Healthy
R_HS1 = 0.15              # r_HS1  — becoming Sick when Healthy
R_S1H = 0.5               # r_S1H  — becoming Healthy when Sick
R_S1S2 = 0.105            # r_S1S2 — becoming Sicker when Sick
HR_S1 = 3                 # hr_S1  — hazard ratio of death, Sick vs Healthy
HR_S2 = 10                # hr_S2  — hazard ratio of death, Sicker vs Healthy
HR_S1S2_TRTB = 0.6        # hr_S1S2_trtB — treatment B slows S1 → S2

# ── State rewards ─────────────────────────────────────────────────────────────
C_H = 2_000               # c_H
C_S1 = 4_000              # c_S1
C_S2 = 15_000             # c_S2
C_D = 0                   # c_D
C_TRTA = 12_000           # c_trtA
C_TRTB = 13_000           # c_trtB

U_H = 1.0                 # u_H
U_S1 = 0.75               # u_S1
U_S2 = 0.5                # u_S2
U_D = 0.0                 # u_D
U_TRTA = 0.95             # u_trtA


def transition_matrices() -> Dict[str, np.ndarray]:
    """Build the 4×4 transition matrix for each strategy.

    Only strategy B (and therefore AB, which copies it) changes the matrix:
    treatment B applies its hazard ratio to the *rate* of progression before the
    rate → probability conversion, which is the correct order and not the same as
    scaling the probability.
    """
    r_S1D = R_HD * HR_S1
    r_S2D = R_HD * HR_S2

    p_HS1 = rate_to_prob(R_HS1, CYCLE_LENGTH)
    p_S1H = rate_to_prob(R_S1H, CYCLE_LENGTH)
    p_S1S2 = rate_to_prob(R_S1S2, CYCLE_LENGTH)
    p_HD = rate_to_prob(R_HD, CYCLE_LENGTH)
    p_S1D = rate_to_prob(r_S1D, CYCLE_LENGTH)
    p_S2D = rate_to_prob(r_S2D, CYCLE_LENGTH)

    # Treatment B: hazard ratio applied to the rate, then converted.
    p_S1S2_trtB = rate_to_prob(R_S1S2 * HR_S1S2_TRTB, CYCLE_LENGTH)

    def build(p_prog: float) -> np.ndarray:
        P = np.zeros((4, 4))
        P[0, 0] = (1 - p_HD) * (1 - p_HS1)      # H  → H
        P[0, 1] = (1 - p_HD) * p_HS1            # H  → S1
        P[0, 3] = p_HD                          # H  → D
        P[1, 0] = (1 - p_S1D) * p_S1H           # S1 → H
        P[1, 1] = (1 - p_S1D) * (1 - (p_S1H + p_prog))
        P[1, 2] = (1 - p_S1D) * p_prog          # S1 → S2
        P[1, 3] = p_S1D                         # S1 → D
        P[2, 2] = 1 - p_S2D                     # S2 → S2
        P[2, 3] = p_S2D                         # S2 → D
        P[3, 3] = 1.0                           # D absorbing
        return P

    P_soc = build(p_S1S2)
    P_b = build(p_S1S2_trtB)
    return {
        "Standard of care": P_soc,
        "Strategy A": P_soc.copy(),     # A changes rewards only, not transitions
        "Strategy B": P_b,
        "Strategy AB": P_b.copy(),
    }


def state_rewards() -> Dict[str, Dict[str, np.ndarray]]:
    """Per-strategy cost and utility vectors over (H, S1, S2, D).

    Treatment costs are paid in **both** sick states — the published code adds
    ``c_trtA`` to ``c_S1`` and ``c_S2`` alike, even though treatment A only
    improves utility in S1. That asymmetry is the source's, reproduced as-is.
    """
    return {
        "Standard of care": {
            "cost": np.array([C_H, C_S1, C_S2, C_D], dtype=float) * CYCLE_LENGTH,
            "util": np.array([U_H, U_S1, U_S2, U_D], dtype=float) * CYCLE_LENGTH,
        },
        "Strategy A": {
            "cost": np.array([C_H, C_S1 + C_TRTA, C_S2 + C_TRTA, C_D], dtype=float),
            "util": np.array([U_H, U_TRTA, U_S2, U_D], dtype=float) * CYCLE_LENGTH,
        },
        "Strategy B": {
            "cost": np.array([C_H, C_S1 + C_TRTB, C_S2 + C_TRTB, C_D],
                             dtype=float) * CYCLE_LENGTH,
            "util": np.array([U_H, U_S1, U_S2, U_D], dtype=float) * CYCLE_LENGTH,
        },
        "Strategy AB": {
            "cost": np.array([C_H, C_S1 + C_TRTA + C_TRTB, C_S2 + C_TRTA + C_TRTB,
                              C_D], dtype=float) * CYCLE_LENGTH,
            "util": np.array([U_H, U_TRTA, U_S2, U_D], dtype=float) * CYCLE_LENGTH,
        },
    }
    # Note: the published script omits the `* cycle_length` scaling on Strategy
    # A's cost vector only. With cycle_length = 1 it makes no difference; it is
    # left un-scaled here so the two files match line for line.


def run() -> List[CSTMResult]:
    """Run all four strategies and return their results, in table order."""
    P = transition_matrices()
    rewards = state_rewards()
    v_init = np.array([1.0, 0.0, 0.0, 0.0])          # everyone starts Healthy

    return [
        run_cstm(
            P=P[s],
            v_init=v_init,
            n_cycles=N_CYCLES,
            state_costs=rewards[s]["cost"],
            state_utils=rewards[s]["util"],
            payoff="state",
            cycle_length=CYCLE_LENGTH,
            d_c=D_C,
            d_e=D_E,
            wcc=WCC_METHOD,
            state_names=STATES,
            strategy=s,
        )
        for s in STRATEGIES
    ]
