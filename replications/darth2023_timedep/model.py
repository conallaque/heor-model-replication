"""
The Sick-Sicker model, age-dependent — DARTH time-dependent cSTM tutorial
=========================================================================

Same disease, same four strategies, same 75 annual cycles from age 25 as the
introductory model — and a different answer, because three conventions change.
Reproducing this one *and* the introductory one with a single solver is the
point: it is easy to write a solver that matches one paper, and much harder to
write one that matches two papers that disagree about how to accrue a payoff.

What changes:

1. **Background mortality comes from a life table**, not a constant rate. The
   ``r_HD = 0.002`` of the introductory model is replaced by US 2015 age-specific
   all-cause mortality for ages 25–99, so the transition matrix is a *stack* of
   75 matrices rather than one. Real mortality is far higher at older ages, which
   is why every strategy here is cheaper and less effective than its introductory
   counterpart.

2. **Payoffs are accrued over transitions, not state occupancy.** The tutorial
   builds a transition-dynamics array ``A[t] = diag(trace[t-1]) @ P[t-1]`` — the
   share of the cohort making each i→j move — and multiplies it by a reward
   matrix. On state rewards alone this is *arithmetically identical* to the
   introductory model's ``trace @ rewards`` (see
   ``test_payoff_conventions_agree_when_rewards_are_state_only``); it is not a
   different answer, it is a more general way of writing the same one. What it
   buys is point 3.

3. **Some rewards attach to moving, not to being.** Getting sick costs a one-off
   ``ic_HS1`` on top of the annual cost, and carries a one-off disutility
   ``du_HS1``; dying costs ``ic_D``. These cannot be expressed as state rewards
   at all — they are the reason the transition formulation exists.

Every parameter is transcribed from ``analysis/cSTM_time_dep_simulation.R``
(retrieved 2026-08-19). The R variable name is kept beside each one.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

import numpy as np

from cstm.solver import CSTMResult, run_cstm
from cstm.wcc import rate_to_prob

# ── General setup ─────────────────────────────────────────────────────────────
CYCLE_LENGTH = 1
N_AGE_INIT = 25
N_AGE_MAX = 100
N_CYCLES = (N_AGE_MAX - N_AGE_INIT) // CYCLE_LENGTH      # 75
STATES = ("H", "S1", "S2", "D")
STRATEGIES = ("Standard of care", "Strategy A", "Strategy B", "Strategy AB")

D_C = 0.03
D_E = 0.03
WCC_METHOD = "Simpson1/3"

# ── Transition rates (annual) and hazard ratios ───────────────────────────────
R_HS1 = 0.15              # r_HS1
R_S1H = 0.5               # r_S1H
R_S1S2 = 0.105            # r_S1S2
HR_S1 = 3                 # hr_S1
HR_S2 = 10                # hr_S2
HR_S1S2_TRTB = 0.6        # hr_S1S2_trtB

# ── State rewards ─────────────────────────────────────────────────────────────
C_H, C_S1, C_S2, C_D = 2_000, 4_000, 15_000, 0
C_TRTA, C_TRTB = 12_000, 13_000
U_H, U_S1, U_S2, U_D = 1.0, 0.75, 0.5, 0.0
U_TRTA = 0.95

# ── Transition rewards ────────────────────────────────────────────────────────
DU_HS1 = 0.01             # du_HS1 — disutility of transitioning H → S1
IC_HS1 = 1_000            # ic_HS1 — one-off cost of transitioning H → S1
IC_D = 2_000              # ic_D   — one-off cost of dying

LIFE_TABLE = Path(__file__).resolve().parents[2] / "data" / "LifeTable_USA_Mx_2015.csv"


def mortality_rates_by_age() -> np.ndarray:
    """Age-specific all-cause mortality hazard rates for ages 25–99.

    Transcribed from::

        lt_usa_2015 <- read.csv("data/LifeTable_USA_Mx_2015.csv")
        v_r_mort_by_age <- lt_usa_2015 %>%
          dplyr::filter(Age >= n_age_init & Age < n_age_max) %>%
          dplyr::select(Total) %>% as.matrix()

    Note the half-open interval: ages 25 through 99 inclusive, giving exactly
    ``n_cycles`` = 75 rates.
    """
    with LIFE_TABLE.open() as fh:
        rows = [r for r in csv.DictReader(fh)
                if N_AGE_INIT <= int(r["Age"]) < N_AGE_MAX]
    rates = np.array([float(r["Total"]) for r in rows])
    if rates.size != N_CYCLES:
        raise ValueError(
            f"life table gave {rates.size} rates for ages "
            f"{N_AGE_INIT}–{N_AGE_MAX - 1}, expected {N_CYCLES}")
    return rates


def transition_arrays() -> Dict[str, np.ndarray]:
    """Build the ``(75, 4, 4)`` transition array for each strategy.

    Mortality hazard ratios are applied to the age-specific *rate* before the
    rate → probability conversion; the disease transitions stay constant with
    age. As in the introductory model, every non-death transition is conditional
    on surviving the cycle.
    """
    v_r_mort = mortality_rates_by_age()                  # v_r_mort_by_age
    v_p_HDage = rate_to_prob(v_r_mort, CYCLE_LENGTH)     # v_p_HDage
    v_p_S1Dage = rate_to_prob(v_r_mort * HR_S1, CYCLE_LENGTH)
    v_p_S2Dage = rate_to_prob(v_r_mort * HR_S2, CYCLE_LENGTH)

    p_HS1 = rate_to_prob(R_HS1, CYCLE_LENGTH)
    p_S1H = rate_to_prob(R_S1H, CYCLE_LENGTH)
    p_S1S2 = rate_to_prob(R_S1S2, CYCLE_LENGTH)
    p_S1S2_trtB = rate_to_prob(R_S1S2 * HR_S1S2_TRTB, CYCLE_LENGTH)

    def build(p_prog: float) -> np.ndarray:
        P = np.zeros((N_CYCLES, 4, 4))
        P[:, 0, 0] = (1 - v_p_HDage) * (1 - p_HS1)
        P[:, 0, 1] = (1 - v_p_HDage) * p_HS1
        P[:, 0, 3] = v_p_HDage
        P[:, 1, 0] = (1 - v_p_S1Dage) * p_S1H
        P[:, 1, 1] = (1 - v_p_S1Dage) * (1 - (p_S1H + p_prog))
        P[:, 1, 2] = (1 - v_p_S1Dage) * p_prog
        P[:, 1, 3] = v_p_S1Dage
        P[:, 2, 2] = 1 - v_p_S2Dage
        P[:, 2, 3] = v_p_S2Dage
        P[:, 3, 3] = 1.0
        return P

    P_soc, P_b = build(p_S1S2), build(p_S1S2_trtB)
    return {
        "Standard of care": P_soc,
        "Strategy A": P_soc.copy(),
        "Strategy B": P_b,
        "Strategy AB": P_b.copy(),
    }


def state_reward_vectors() -> Dict[str, Dict[str, np.ndarray]]:
    """Per-strategy state cost and utility vectors over (H, S1, S2, D)."""
    return {
        "Standard of care": {
            "cost": np.array([C_H, C_S1, C_S2, C_D], float) * CYCLE_LENGTH,
            "util": np.array([U_H, U_S1, U_S2, U_D], float) * CYCLE_LENGTH,
        },
        "Strategy A": {
            "cost": np.array([C_H, C_S1 + C_TRTA, C_S2 + C_TRTA, C_D],
                             float) * CYCLE_LENGTH,
            "util": np.array([U_H, U_TRTA, U_S2, U_D], float) * CYCLE_LENGTH,
        },
        "Strategy B": {
            "cost": np.array([C_H, C_S1 + C_TRTB, C_S2 + C_TRTB, C_D],
                             float) * CYCLE_LENGTH,
            "util": np.array([U_H, U_S1, U_S2, U_D], float) * CYCLE_LENGTH,
        },
        "Strategy AB": {
            "cost": np.array([C_H, C_S1 + C_TRTA + C_TRTB,
                              C_S2 + C_TRTA + C_TRTB, C_D], float) * CYCLE_LENGTH,
            "util": np.array([U_H, U_TRTA, U_S2, U_D], float) * CYCLE_LENGTH,
        },
    }


def reward_arrays(v_cost: np.ndarray, v_util: np.ndarray):
    """Expand state rewards into ``(76, 4, 4)`` matrices and add transition rewards.

    Transcribed from the published loop::

        m_c_str   <- matrix(v_c_str, nrow = n_states, ncol = n_states, byrow = T)
        a_R_c_str <- array(m_c_str, dim = c(n_states, n_states, n_cycles + 1))
        a_R_u_str["H", "S1", ]      <- a_R_u_str["H", "S1", ]      - du_HS1
        a_R_c_str["H", "S1", ]      <- a_R_c_str["H", "S1", ]      + ic_HS1
        a_R_c_str[-n_states, "D", ] <- a_R_c_str[-n_states, "D", ] + ic_D

    Two details carry the meaning. ``byrow = TRUE`` fills each row with the
    reward of the *destination* state, so ``R[i, j]`` is what you get for landing
    in ``j``. And ``[-n_states, "D", ]`` is R's negative indexing — "every row
    except the last" — so the cost of dying is charged to those who transition
    into D, not to those already there. Charging it to the D→D cell instead would
    bill the dead an extra $2,000 every year for the rest of the horizon.
    """
    n = len(STATES)
    R_c = np.broadcast_to(v_cost, (N_CYCLES + 1, n, n)).copy()
    R_u = np.broadcast_to(v_util, (N_CYCLES + 1, n, n)).copy()

    R_u[:, 0, 1] -= DU_HS1          # H → S1 disutility
    R_c[:, 0, 1] += IC_HS1          # H → S1 one-off cost
    R_c[:, :-1, 3] += IC_D          # anything → D, excluding D → D
    return R_c, R_u


def run() -> List[CSTMResult]:
    """Run all four strategies and return their results, in table order."""
    P = transition_arrays()
    rewards = state_reward_vectors()
    v_init = np.array([1.0, 0.0, 0.0, 0.0])

    out = []
    for s in STRATEGIES:
        R_c, R_u = reward_arrays(rewards[s]["cost"], rewards[s]["util"])
        out.append(run_cstm(
            P=P[s],
            v_init=v_init,
            n_cycles=N_CYCLES,
            reward_costs=R_c,
            reward_utils=R_u,
            payoff="transition",
            cycle_length=CYCLE_LENGTH,
            d_c=D_C,
            d_e=D_E,
            wcc=WCC_METHOD,
            state_names=STATES,
            strategy=s,
        ))
    return out
