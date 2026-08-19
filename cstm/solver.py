"""
A general cohort state-transition model (cSTM) solver
=====================================================

Published health-economic models do not share a shape. They differ in how many
states they have, whether the transition matrix changes with age or with time in
state, whether payoffs attach to *being* in a state or to *moving* between them,
and which within-cycle correction and discounting conventions they use. A solver
that hardcodes any of those cannot reproduce a paper that chose differently.

So everything a published model varies is an argument here:

* **arbitrary state count**, named, with the matrix validated every cycle;
* **time-varying transitions** — pass one matrix or a stack of ``n_cycles`` of them;
* **state rewards** (cost/utility per cycle spent in a state) and, separately,
  **transition rewards** (a one-off cost or disutility for *making* a move);
* **within-cycle correction** as a named method, not a boolean;
* **separate discount rates** for costs and effects, because plenty of published
  models discount them differently (the UK's 6%/1.5% era being the famous case).

Two payoff conventions are supported, because the two DARTH tutorials use
different ones and reproducing each requires the right one:

``"state"``
    ``payoff[t] = trace[t] @ rewards`` — occupancy at the *start* of cycle t.
    This is what the introductory tutorial's ``m_M %*% v_u`` computes.

``"transition"``
    Build the transition-dynamics array ``A[t]`` — the share of the cohort making
    each i→j move that lands them in cycle ``t`` — multiply elementwise by a
    reward matrix, and sum. This is the formulation that lets a reward attach to
    a *transition* rather than to a state, and it is what the time-dependent
    tutorial uses.

    Given only state rewards, the two conventions are provably the same thing:
    filling the reward matrix by destination state makes the transition sum
    collapse to ``trace[t] @ rewards`` for every ``t``. ``test_cstm.py`` pins
    that identity, and it is a useful correctness check — the array indexing is
    easy to get off by one cycle, and an offset breaks the identity immediately
    while still producing plausible-looking totals.

    The conventions diverge exactly when transition rewards are present, which is
    the case they exist for.

Reference: Alarid-Escudero F, Krijkamp E, Enns EA, Yang A, Hunink MGM,
Pechlivanoglou P, Jalal H. "An Introductory Tutorial on Cohort State-Transition
Models in R Using a Cost-Effectiveness Analysis Example." Med Decis Making.
2023;43(1):3-20; and the companion time-dependent tutorial, Med Decis Making.
2023;43(1):21-41.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from .wcc import discount_weights, gen_wcc

TOL = 1e-8


# ── validation ────────────────────────────────────────────────────────────────

def check_transition_matrix(P: np.ndarray, tol: float = TOL, label: str = "P") -> None:
    """Assert the two properties an HTA reviewer checks before reading any result.

    Every entry in [0, 1], and every row summing to exactly 1 — meaning the
    cohort is conserved and nobody leaks out of the model. A model that fails
    either is not producing a wrong answer, it is producing a meaningless one.
    """
    if P.ndim == 2:
        P = P[None, ...]
    if P.shape[-1] != P.shape[-2]:
        raise ValueError(f"{label}: transition matrices must be square, got {P.shape}")
    lo, hi = float(P.min()), float(P.max())
    if lo < -tol or hi > 1.0 + tol:
        raise ValueError(f"{label}: probabilities outside [0, 1] (min {lo:g}, max {hi:g})")
    sums = P.sum(axis=-1)
    bad = np.abs(sums - 1.0) > tol
    if bad.any():
        t, i = (int(x[0]) for x in np.where(bad))
        raise ValueError(
            f"{label}: row {i} of cycle {t} sums to {sums[t, i]:.12f}, not 1")


# ── result container ──────────────────────────────────────────────────────────

@dataclass
class CSTMResult:
    """Everything a replication needs to check, not just the headline totals."""

    strategy: str
    state_names: tuple
    trace: np.ndarray            # (n_cycles + 1, n_states) state occupancy
    cost_per_cycle: np.ndarray   # (n_cycles + 1,) undiscounted, uncorrected
    qaly_per_cycle: np.ndarray   # (n_cycles + 1,) undiscounted, uncorrected
    total_cost: float            # discounted, within-cycle corrected
    total_qaly: float
    n_cycles: int
    cycle_length: float
    wcc_method: str
    payoff_convention: str
    d_c: float
    d_e: float
    meta: dict = field(default_factory=dict)

    @property
    def life_years(self) -> float:
        """Undiscounted life-years, from occupancy of every non-absorbing state.

        Assumes the last state is the dead state, which is the convention in
        every model replicated here. Reported for face-checking the trace, not
        used in any cost-effectiveness arithmetic.
        """
        return float(self.trace[:, :-1].sum())


# ── the solver ────────────────────────────────────────────────────────────────

def run_cstm(P: np.ndarray,
             v_init: Sequence[float],
             n_cycles: int,
             state_costs: Optional[np.ndarray] = None,
             state_utils: Optional[np.ndarray] = None,
             reward_costs: Optional[np.ndarray] = None,
             reward_utils: Optional[np.ndarray] = None,
             *,
             payoff: str = "state",
             cycle_length: float = 1.0,
             d_c: float = 0.03,
             d_e: float = 0.03,
             wcc: str = "Simpson1/3",
             state_names: Optional[Sequence[str]] = None,
             strategy: str = "",
             validate: bool = True) -> CSTMResult:
    """Run one strategy through the cohort and return the trace plus totals.

    Parameters
    ----------
    P
        Either ``(n_states, n_states)`` for a time-homogeneous model, or
        ``(n_cycles, n_states, n_states)`` where ``P[t]`` governs the move from
        cycle ``t`` to ``t + 1``.
    v_init
        Starting distribution across states; must sum to 1.
    state_costs, state_utils
        ``(n_states,)`` per-cycle rewards, or ``(n_cycles + 1, n_states)`` if the
        reward itself varies over time. Used when ``payoff="state"``, and
        broadcast into the reward matrices when ``payoff="transition"``.
    reward_costs, reward_utils
        ``(n_cycles + 1, n_states, n_states)`` reward matrices for
        ``payoff="transition"``. Entry ``[t, i, j]`` is the reward accrued by the
        share of the cohort moving i→j in cycle t. If given, they are used as-is
        and ``state_costs`` / ``state_utils`` are ignored.
    payoff
        ``"state"`` or ``"transition"`` — see the module docstring. The wrong
        choice produces a close-but-wrong total, which is the single most common
        way a replication fails.

    Notes
    -----
    Rewards are **not** scaled by ``cycle_length`` here. The published models
    scale their reward vectors before passing them in (``v_c * cycle_length``),
    and doing it in both places would double-count.
    """
    if payoff not in ("state", "transition"):
        raise ValueError(f"payoff must be 'state' or 'transition', got {payoff!r}")

    v_init = np.asarray(v_init, dtype=float)
    n_states = v_init.size
    if abs(v_init.sum() - 1.0) > TOL:
        raise ValueError(f"initial state vector sums to {v_init.sum():.12f}, not 1")

    P = np.asarray(P, dtype=float)
    if P.ndim == 2:
        P = np.broadcast_to(P, (n_cycles, n_states, n_states))
    elif P.shape[0] != n_cycles:
        raise ValueError(
            f"time-varying P must have {n_cycles} matrices, got {P.shape[0]}")
    if validate:
        check_transition_matrix(P, label=strategy or "P")

    # ── cohort trace: n_cycles + 1 rows, row t = occupancy at the start of cycle t
    trace = np.empty((n_cycles + 1, n_states), dtype=float)
    trace[0] = v_init
    for t in range(n_cycles):
        trace[t + 1] = trace[t] @ P[t]

    # ── per-cycle payoffs
    if payoff == "state":
        v_c = _as_reward_vector(state_costs, n_cycles, n_states, "state_costs")
        v_u = _as_reward_vector(state_utils, n_cycles, n_states, "state_utils")
        cost_per_cycle = (trace * v_c).sum(axis=1)
        qaly_per_cycle = (trace * v_u).sum(axis=1)
    else:
        # Transition-dynamics array: A[t, i, j] = share of the cohort making the
        # i->j move that lands them in cycle t. Transcribed from the DARTH
        # time-dependent tutorial:
        #
        #     diag(a_A[, , 1]) <- v_m_init
        #     a_A[, , t + 1]   <- diag(m_M[t, ]) %*% a_P[, , t]
        #
        # The offset is load-bearing, not cosmetic. Slice 0 is the starting
        # distribution on the diagonal (nobody has moved yet); every later slice
        # is built from the *previous* cycle's occupancy. Aligning A[t] with
        # trace[t] instead shifts every payoff one cycle against the discount and
        # within-cycle-correction weights, which silently changes the totals.
        A = np.empty((n_cycles + 1, n_states, n_states), dtype=float)
        A[0] = np.diag(v_init)
        A[1:] = trace[:-1, :, None] * P
        R_c = _as_reward_matrix(reward_costs, state_costs, n_cycles, n_states, "costs")
        R_u = _as_reward_matrix(reward_utils, state_utils, n_cycles, n_states, "utils")
        cost_per_cycle = (A * R_c).sum(axis=(1, 2))
        qaly_per_cycle = (A * R_u).sum(axis=(1, 2))

    # ── discount and within-cycle correct
    v_wcc = gen_wcc(n_cycles, method=wcc)
    dwc = discount_weights(n_cycles, d_c, cycle_length)
    dwe = discount_weights(n_cycles, d_e, cycle_length)
    total_cost = float(cost_per_cycle @ (dwc * v_wcc))
    total_qaly = float(qaly_per_cycle @ (dwe * v_wcc))

    return CSTMResult(
        strategy=strategy,
        state_names=tuple(state_names or [f"s{i}" for i in range(n_states)]),
        trace=trace,
        cost_per_cycle=cost_per_cycle,
        qaly_per_cycle=qaly_per_cycle,
        total_cost=total_cost,
        total_qaly=total_qaly,
        n_cycles=n_cycles,
        cycle_length=cycle_length,
        wcc_method=wcc,
        payoff_convention=payoff,
        d_c=d_c,
        d_e=d_e,
    )


def _as_reward_vector(v, n_cycles: int, n_states: int, name: str) -> np.ndarray:
    """Broadcast a reward spec to ``(n_cycles + 1, n_states)``."""
    if v is None:
        return np.zeros((n_cycles + 1, n_states))
    v = np.asarray(v, dtype=float)
    if v.ndim == 1:
        if v.size != n_states:
            raise ValueError(f"{name}: expected {n_states} entries, got {v.size}")
        return np.broadcast_to(v, (n_cycles + 1, n_states))
    if v.shape != (n_cycles + 1, n_states):
        raise ValueError(
            f"{name}: expected shape {(n_cycles + 1, n_states)}, got {v.shape}")
    return v


def _as_reward_matrix(R, v, n_cycles: int, n_states: int, name: str) -> np.ndarray:
    """Return the ``(n_cycles + 1, n_states, n_states)`` reward matrix.

    If an explicit matrix is supplied it wins. Otherwise a state-reward vector is
    broadcast **by destination state** (``R[t, i, j] = v[j]``), which is the
    ``byrow = TRUE`` fill the DARTH tutorials use.
    """
    if R is not None:
        R = np.asarray(R, dtype=float)
        if R.shape != (n_cycles + 1, n_states, n_states):
            raise ValueError(
                f"reward_{name}: expected shape "
                f"{(n_cycles + 1, n_states, n_states)}, got {R.shape}")
        return R
    vv = _as_reward_vector(v, n_cycles, n_states, f"state_{name}")
    return np.broadcast_to(vv[:, None, :], (n_cycles + 1, n_states, n_states))
