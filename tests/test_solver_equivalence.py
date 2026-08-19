"""
Does the general solver still agree with the engine it generalises?
==================================================================

The solver in :mod:`cstm.solver` was written to reproduce published models of
arbitrary shape. It started life as a 3-state, half-cycle-corrected, fixed-signature
Markov model in the author's HEOR toolkit. Generalising a working model is a good
way to break it silently, so this test pins the two together: configured to the
3-state ``Well / Disease / Dead`` case, the general solver must reproduce the
original's totals to the full precision the original reports.

That isolates the two failure modes. If this test is green and a replication
still misses, the miss is in the replication's parameters or conventions, not in
the solver. If this test goes red, nothing downstream can be trusted.

The toolkit is not vendored into this repository — a copy would drift. The test
locates it, and **skips with a clear message** if it is not present, so the rest
of the suite stays runnable anywhere.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

from cstm.solver import run_cstm

#: Where to find the sibling HEOR toolkit. Override with HEOR_TOOLKIT_PATH.
TOOLKIT_PATHS = [
    Path(os.environ.get("HEOR_TOOLKIT_PATH", "")),
    Path.home() / "Desktop" / "dna-project" / "heor-toolkit",
    Path.home() / "heor-toolkit",
]

#: The toolkit rounds its returned totals to 2 dp (cost) and 4 dp (QALYs), so
#: agreement can only be asserted to half of the last reported digit. Anything
#: larger than this is a real disagreement, not a display artefact.
COST_ATOL = 0.005
QALY_ATOL = 0.00005

PARAMS = dict(
    start_age=40.0, cycles=45, incidence_rate=0.010, rrr_intervention=0.30,
    cost_intervention_annual=250.0, cost_disease_annual=12_000.0,
    cost_well_annual=0.0, utility_well=0.90, utility_disease=0.68,
    excess_mortality_rate=0.035, discount_rate=0.03,
)


def _load_toolkit():
    for p in TOOLKIT_PATHS:
        if p and (p / "markov_model.py").exists():
            sys.path.insert(0, str(p))
            import markov_model  # noqa: WPS433 - deliberate late import
            return markov_model
    return None


mk = _load_toolkit()
pytestmark = pytest.mark.skipif(
    mk is None,
    reason=("HEOR toolkit not found — set HEOR_TOOLKIT_PATH to the directory "
            "containing markov_model.py to run the equivalence check"),
)


def _via_general_solver(strategy: str):
    """Express the toolkit's model in the general solver's terms.

    Two mappings matter and are the whole content of this translation:

    * The toolkit accrues payoffs for ``cycles`` periods using start-of-cycle
      occupancy, i.e. trace rows 0..cycles-1. The general solver produces
      ``n_cycles + 1`` payoff rows, so ``n_cycles = cycles - 1``.
    * Its transition matrix is rebuilt every cycle from age-dependent Gompertz
      mortality, so it becomes a *stack* of matrices, not one matrix.
    """
    guided = strategy == "genomic_guided"
    incidence = (PARAMS["incidence_rate"] * (1 - PARAMS["rrr_intervention"])
                 if guided else PARAMS["incidence_rate"])
    n_cycles = PARAMS["cycles"] - 1

    P = np.array([
        mk.build_transition_matrix(
            mk.rate_to_prob(incidence),
            mk.rate_to_prob(PARAMS["excess_mortality_rate"]),
            mk.rate_to_prob(mk._gompertz_mortality(PARAMS["start_age"] + t)),
        )
        for t in range(n_cycles)
    ])

    costs = np.array([
        PARAMS["cost_well_annual"]
        + (PARAMS["cost_intervention_annual"] if guided else 0.0),
        PARAMS["cost_disease_annual"],
        0.0,
    ])
    utils = np.array([PARAMS["utility_well"], PARAMS["utility_disease"], 0.0])

    return run_cstm(
        P=P, v_init=[1.0, 0.0, 0.0], n_cycles=n_cycles,
        state_costs=costs, state_utils=utils,
        payoff="state", d_c=PARAMS["discount_rate"], d_e=PARAMS["discount_rate"],
        wcc="half-cycle", state_names=("Well", "Disease", "Dead"),
        strategy=strategy,
    )


@pytest.mark.parametrize("strategy", ["standard_care", "genomic_guided"])
def test_general_solver_reproduces_toolkit(strategy):
    original = mk.run_markov(strategy=strategy, **PARAMS)
    general = _via_general_solver(strategy)

    assert abs(general.total_cost - original["total_cost"]) < COST_ATOL, (
        f"{strategy}: general {general.total_cost:.6f} vs "
        f"toolkit {original['total_cost']:.2f}")
    assert abs(general.total_qaly - original["total_qaly"]) < QALY_ATOL, (
        f"{strategy}: general {general.total_qaly:.8f} vs "
        f"toolkit {original['total_qaly']:.4f}")


def test_general_solver_reproduces_toolkit_icer():
    """The derived quantity, not just the components.

    An ICER divides two small differences, so the toolkit's display rounding is
    amplified: an incremental QALY of ~0.42 built from two totals each rounded to
    4 dp is itself uncertain by ±1e-4, which is ~2.4e-4 in relative terms. Rather
    than pick a tolerance and hope, this propagates the rounding into an interval
    and asserts the general solver's ICER falls inside it — the tightest claim the
    original's reported precision actually supports.
    """
    sc = _via_general_solver("standard_care")
    gg = _via_general_solver("genomic_guided")
    icer = (gg.total_cost - sc.total_cost) / (gg.total_qaly - sc.total_qaly)

    original = mk.markov_cost_effectiveness(**PARAMS)
    d_cost, d_qaly = original["incremental_cost"], original["incremental_qaly"]

    # Each total is rounded, so each difference carries twice the half-ULP.
    candidates = [(d_cost + dc) / (d_qaly + dq)
                  for dc in (-2 * COST_ATOL, 2 * COST_ATOL)
                  for dq in (-2 * QALY_ATOL, 2 * QALY_ATOL)]
    lo, hi = min(candidates), max(candidates)

    assert lo <= icer <= hi, (
        f"general solver ICER {icer:,.4f} outside the interval [{lo:,.4f}, "
        f"{hi:,.4f}] implied by the toolkit's reported precision "
        f"(its printed ICER: {original['icer']:,.2f})")
