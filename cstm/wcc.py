"""
Within-cycle correction
=======================

A cohort model moves people between states at discrete cycle boundaries, but the
events it represents happen continuously *inside* the cycle. Someone who dies in
March did not accrue a full year of costs and utility. Summing state occupancy at
cycle boundaries therefore over- or under-counts, and the fix — a quadrature
weight applied to the per-cycle payoff vector — is called a **within-cycle
correction (WCC)**.

Which correction a study used is not a detail. A model run with Simpson's 1/3
and the same model run with the half-cycle correction produce different totals,
and a replication that silently swaps them will land close-but-wrong. So the
method is an explicit argument here, never a default buried in a solver.

The implementations below are transcribed from the reference sources so that a
replication can select the *source's* convention:

* ``"Simpson1/3"`` and ``"half-cycle"`` follow ``darthtools::gen_wcc``, as
  published in ``R/Functions.R`` of DARTH-git/cohort-modeling-tutorial-intro
  (fetched 2026-08-19). See :func:`gen_wcc` for the verbatim R.
* ``"none"`` is the no-correction case, kept because some published models
  genuinely do not correct and reproducing them requires not correcting either.

Reference: Elbasha & Chhatwal (2016), *Health Economics* 25(12):1447-1458,
"Theoretical foundations and practical applications of within-cycle correction
methods".
"""

from __future__ import annotations

import numpy as np

METHODS = ("Simpson1/3", "half-cycle", "none")


def gen_wcc(n_cycles: int, method: str = "Simpson1/3") -> np.ndarray:
    """Return the length ``n_cycles + 1`` within-cycle-correction weight vector.

    The vector is one element longer than the number of cycles because a trace
    with ``n_cycles`` transitions has ``n_cycles + 1`` state-occupancy rows
    (cycle 0 through cycle ``n_cycles``).

    Transcribed from ``darthtools::gen_wcc``::

        gen_wcc <- function (n_cycles, method = c("Simpson1/3", "half-cycle", "none")) {
          if (method == "Simpson1/3") {
            v_cycles <- seq(1, n_cycles + 1)
            v_wcc <- ((v_cycles %% 2) == 0) * (2/3) + ((v_cycles %% 2) != 0) * (4/3)
            v_wcc[1] <- v_wcc[n_cycles + 1] <- 1/3
          }
          if (method == "half-cycle") {
            v_wcc <- rep(1, n_cycles + 1)
            v_wcc[1] <- v_wcc[n_cycles + 1] <- 0.5
          }
          if (method == "none") {
            v_wcc <- rep(1, n_cycles + 1)
          }
          return(v_wcc)
        }

    Note the R is 1-indexed: ``v_cycles`` runs 1..n_cycles+1, so the *first*
    interior weight (position 2) is 2/3, not the 4/3 a textbook Simpson's rule
    would put there. That asymmetry is reproduced deliberately — the goal is to
    match the published implementation, not to improve on it.
    """
    if n_cycles <= 0:
        raise ValueError("Number of cycles should be positive")
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    n = int(n_cycles)

    if method == "none":
        return np.ones(n + 1)

    if method == "half-cycle":
        v = np.ones(n + 1)
        v[0] = v[n] = 0.5
        return v

    # Simpson's 1/3. R's v_cycles = 1..n+1 maps to python index i -> i + 1.
    v_cycles = np.arange(1, n + 2)
    v = np.where(v_cycles % 2 == 0, 2.0 / 3.0, 4.0 / 3.0)
    v[0] = v[n] = 1.0 / 3.0
    return v


def rate_to_prob(r, t: float = 1.0):
    """Convert a continuous-time rate to a per-cycle probability: ``p = 1 - exp(-r·t)``.

    Using ``r·t`` directly is the most common arithmetic error in applied
    modelling: it is only accurate for small ``r`` and can exceed 1 for large
    ``r``. Transcribed from ``darthtools::rate_to_prob``.
    """
    r = np.asarray(r, dtype=float)
    if np.any(r < 0):
        raise ValueError("rate not greater than or equal to 0")
    p = 1.0 - np.exp(-r * t)
    return float(p) if p.ndim == 0 else p


def discount_weights(n_cycles: int, rate: float, cycle_length: float = 1.0) -> np.ndarray:
    """Discount weights for cycles 0..``n_cycles``.

    Transcribed from the DARTH tutorials::

        v_dwc <- 1 / ((1 + (d_c * cycle_length)) ^ (0:n_cycles))

    Two conventions worth flagging, because both are places a replication drifts:

    1. The base is ``1 + d * cycle_length``, i.e. the annual rate is scaled
       *linearly* to the cycle. With monthly cycles this is not the same as
       ``(1 + d) ** (1/12)``; published models differ on which they use.
    2. Cycle 0 gets weight 1 — costs in the first cycle are undiscounted.
    """
    if n_cycles <= 0:
        raise ValueError("Number of cycles should be positive")
    return 1.0 / ((1.0 + rate * cycle_length) ** np.arange(0, int(n_cycles) + 1))
