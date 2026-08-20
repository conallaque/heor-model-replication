"""
Cycle length: the convention this repository documented but never checked
========================================================================

``cstm/wcc.py`` warns that discount weights use ``(1 + d·Δt)^t`` and that with
monthly cycles this is *not* ``(1 + d)^(t·Δt)`` — "published models differ on
which they use". Every replication here runs annual cycles, so until now that
warning had no test behind it: the one parameter flagged as dangerous was the one
nothing exercised.

These tests close that. They also make the case for *why* cycle length is a
modelling decision rather than a unit, which is the part a reviewer cares about.

All four use a model with a closed-form answer — a single exponential survival
curve — so agreement is checked against arithmetic truth rather than against
another run of the same code.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from cstm.solver import run_cstm
from cstm.wcc import discount_weights, rate_to_prob

RATE = 0.05          # constant annual mortality hazard
HORIZON = 20         # years
#: Life-years lived over the horizon: ∫₀^H exp(−rt) dt = (1 − exp(−rH)) / r
ANALYTIC_LIFE_YEARS = (1 - math.exp(-RATE * HORIZON)) / RATE


def _survival_model(cycle_length: float, n_cycles: int, **kw):
    """Two states, Alive → Dead, constant hazard. Rewards scaled by the caller."""
    p = rate_to_prob(RATE, cycle_length)
    P = np.array([[1 - p, p], [0.0, 1.0]])
    return run_cstm(
        P=P, v_init=[1.0, 0.0], n_cycles=n_cycles,
        state_costs=np.zeros(2),
        state_utils=np.array([1.0, 0.0]) * cycle_length,
        cycle_length=cycle_length, wcc="half-cycle",
        **{"d_c": 0.0, "d_e": 0.0, **kw})


def test_shorter_cycles_are_closer_to_the_analytic_answer():
    """Cycle length is an accuracy choice, not a unit conversion.

    A cohort model approximates a continuous process with a discrete one, so the
    cycle is the step size of a quadrature. Halving it should buy accuracy — and
    here monthly cycles land two orders of magnitude closer to the closed-form
    answer than annual ones. A reviewer asking "why annual?" is asking a real
    question, and this is the shape of the answer.
    """
    annual = _survival_model(1.0, HORIZON).total_qaly
    monthly = _survival_model(1 / 12, HORIZON * 12).total_qaly

    err_annual = abs(annual - ANALYTIC_LIFE_YEARS)
    err_monthly = abs(monthly - ANALYTIC_LIFE_YEARS)

    assert err_monthly < err_annual / 10, (
        f"monthly ({err_monthly:.2e}) should be far closer to the analytic "
        f"{ANALYTIC_LIFE_YEARS:.6f} than annual ({err_annual:.2e})")
    assert err_annual < 0.01, "even annual cycles should be within 1% here"


def test_rate_to_probability_conversion_is_exact_across_granularity():
    """Survival must not depend on how finely you slice the horizon.

    ``p = 1 − exp(−r·Δt)`` makes twelve monthly steps compose to exactly one
    annual step, because ``exp(−r/12)¹² = exp(−r)``. Using ``r·Δt`` instead — the
    common shortcut — breaks this, and the error compounds every cycle. This is
    the single best argument for the conversion the repository uses.
    """
    annual = _survival_model(1.0, HORIZON).trace[-1, 0]
    monthly = _survival_model(1 / 12, HORIZON * 12).trace[-1, 0]
    assert annual == pytest.approx(monthly, rel=1e-12)
    assert annual == pytest.approx(math.exp(-RATE * HORIZON), rel=1e-12)

    # The shortcut it replaces: linear scaling does not compose.
    naive_annual = 1 - RATE
    naive_monthly = (1 - RATE / 12) ** 12
    assert abs(naive_annual - naive_monthly) > 1e-3


def test_the_two_discounting_conventions_differ_materially_at_sub_annual_cycles():
    """Pins which convention this solver implements, and that the choice matters.

    ``(1 + d·Δt)^t`` (the DARTH tutorials' formulation, used here) and
    ``(1 + d)^(t·Δt)`` (effective-annual-rate compounding) agree when Δt = 1 and
    diverge otherwise. At ten years of monthly cycles they are ~0.4% apart —
    small per cycle, but it accumulates across a lifetime horizon and is exactly
    the kind of mismatch that makes a replication land close but wrong.
    """
    d, cl, n = 0.03, 1 / 12, 240
    ours = discount_weights(n, d, cl)
    alternative = 1.0 / ((1.0 + d) ** (np.arange(n + 1) * cl))

    t10 = 120                                            # ten years in
    assert ours[t10] == pytest.approx(1.0 / (1.0 + d * cl) ** t10)
    assert abs(ours[t10] - alternative[t10]) / alternative[t10] > 0.003

    # ...and they coincide exactly at annual cycles, which is why no existing
    # replication could have caught a mistake here.
    assert np.allclose(discount_weights(20, d, 1.0),
                       1.0 / ((1.0 + d) ** np.arange(21)))


def test_the_solver_does_not_scale_rewards_by_cycle_length():
    """The caller owns reward scaling — asserted, because it is only a docstring.

    ``run_cstm`` deliberately does not multiply rewards by ``cycle_length``: the
    published models scale their own reward vectors, and doing it in both places
    would silently halve or double every total. Nothing enforced that contract
    until now.
    """
    unscaled = _survival_model(1 / 12, HORIZON * 12)

    p = rate_to_prob(RATE, 1 / 12)
    P = np.array([[1 - p, p], [0.0, 1.0]])
    forgot_to_scale = run_cstm(
        P=P, v_init=[1.0, 0.0], n_cycles=HORIZON * 12,
        state_costs=np.zeros(2),
        state_utils=np.array([1.0, 0.0]),      # NOT scaled by cycle_length
        cycle_length=1 / 12, d_c=0.0, d_e=0.0, wcc="half-cycle")

    assert forgot_to_scale.total_qaly == pytest.approx(
        unscaled.total_qaly * 12, rel=1e-9), (
        "if these were not 12x apart, the solver would be scaling rewards "
        "itself and the replications would be double-scaling them")
