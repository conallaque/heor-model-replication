"""
The second replication claim, as assertions
===========================================

Same falsifiability contract as the introductory replication: if these go red,
the claim is false.

This file carries extra weight, because matching a second paper that uses
*different* conventions is what distinguishes a general solver from one fitted to
a single target. The last test in this file exists purely to prove the two
replications are not the same model run twice.
"""

from __future__ import annotations

import numpy as np
import pytest

from cstm.icer import calculate_icers
from replications.darth2023_timedep import model
from replications.darth2023_timedep.reference import PUBLISHED, TOLERANCE


@pytest.fixture(scope="module")
def results():
    return {r.strategy: r for r in model.run()}


@pytest.fixture(scope="module")
def icer_rows(results):
    res = [results[s] for s in model.STRATEGIES]
    return {r.strategy: r for r in calculate_icers(
        [r.total_cost for r in res],
        [r.total_qaly for r in res],
        [r.strategy for r in res])}


# ── the headline claim ────────────────────────────────────────────────────────

@pytest.mark.parametrize("strategy", list(PUBLISHED))
def test_total_cost_matches_published(results, strategy):
    got, want = results[strategy].total_cost, PUBLISHED[strategy]["cost"]
    assert round(got) == want, f"{strategy}: got {got:,.2f}, published {want:,}"


@pytest.mark.parametrize("strategy", list(PUBLISHED))
def test_total_qaly_matches_published(results, strategy):
    got, want = results[strategy].total_qaly, PUBLISHED[strategy]["qaly"]
    assert abs(round(got, 3) - want) <= TOLERANCE["qaly"], \
        f"{strategy}: got {got:.6f}, published {want}"


@pytest.mark.parametrize("strategy", list(PUBLISHED))
def test_dominance_status_matches_published(icer_rows, strategy):
    assert icer_rows[strategy].status == PUBLISHED[strategy]["status"]


@pytest.mark.parametrize("strategy", ["Strategy B", "Strategy AB"])
def test_icer_matches_published(icer_rows, strategy):
    got, want = icer_rows[strategy].icer, PUBLISHED[strategy]["icer"]
    assert abs(round(got) - want) <= TOLERANCE["icer"], \
        f"{strategy}: got {got:,.2f}/QALY, published ${want:,}/QALY"


@pytest.mark.parametrize("strategy", ["Strategy B", "Strategy AB"])
def test_incremental_values_match_published(icer_rows, strategy):
    row, want = icer_rows[strategy], PUBLISHED[strategy]
    assert round(row.inc_cost) == want["inc_cost"]
    assert abs(round(row.inc_effect, 3) - want["inc_qaly"]) <= TOLERANCE["qaly"]


# ── the inputs this model adds over the introductory one ──────────────────────

def test_life_table_covers_exactly_the_horizon():
    """Ages 25–99 inclusive: one mortality rate per cycle, no off-by-one."""
    rates = model.mortality_rates_by_age()
    assert rates.shape == (model.N_CYCLES,)
    assert np.all(rates > 0)
    assert np.all(np.diff(rates[10:]) > -0.02), "mortality should rise with age"


def test_mortality_is_age_dependent_not_constant():
    """The whole point of this model: the hazard at 99 dwarfs the hazard at 25."""
    rates = model.mortality_rates_by_age()
    assert rates[-1] > 50 * rates[0]


def test_transition_arrays_are_time_varying():
    P = model.transition_arrays()["Standard of care"]
    assert P.shape == (model.N_CYCLES, 4, 4)
    assert not np.allclose(P[0], P[-1]), "matrix should change with age"


def test_death_cost_is_charged_on_transition_not_occupancy():
    """``ic_D`` must hit the into-D cells only.

    Adding it to the D→D cell as well would charge every dead cohort member
    $2,000 in every remaining cycle — a mistake that inflates costs enormously
    and is invisible in the totals unless you look here.
    """
    v_c = model.state_reward_vectors()["Standard of care"]["cost"]
    v_u = model.state_reward_vectors()["Standard of care"]["util"]
    R_c, _ = model.reward_arrays(v_c, v_u)
    assert R_c[0, 0, 3] == model.C_D + model.IC_D      # H  → D charged
    assert R_c[0, 2, 3] == model.C_D + model.IC_D      # S2 → D charged
    assert R_c[0, 3, 3] == model.C_D                   # D  → D NOT charged


def test_sickness_onset_rewards_are_applied():
    v_c = model.state_reward_vectors()["Standard of care"]["cost"]
    v_u = model.state_reward_vectors()["Standard of care"]["util"]
    R_c, R_u = model.reward_arrays(v_c, v_u)
    assert R_c[0, 0, 1] == model.C_S1 + model.IC_HS1
    assert R_u[0, 0, 1] == pytest.approx(model.U_S1 - model.DU_HS1)


# ── structural checks ─────────────────────────────────────────────────────────

def test_cohort_is_conserved(results):
    for r in results.values():
        assert np.allclose(r.trace.sum(axis=1), 1.0, atol=1e-12)


def test_death_is_absorbing(results):
    for r in results.values():
        assert np.all(np.diff(r.trace[:, -1]) >= -1e-15)


def test_almost_everyone_is_dead_by_age_100(results):
    """Face validity against the life table: a cohort followed from 25 to 100
    under real US mortality should have very few survivors left."""
    for r in results.values():
        assert r.trace[-1, -1] > 0.97, f"{r.strategy}: {r.trace[-1, -1]:.4f} dead"


# ── the two replications are genuinely different models ───────────────────────

def test_differs_from_the_time_independent_replication(results):
    """Guards against the failure where one model is silently reused for both.

    The introductory model's constant 0.002 mortality rate is far kinder than a
    real life table, so it must produce materially more QALYs. If these two ever
    agree, one of the replications has stopped being what it claims to be.
    """
    from replications.darth2023_intro import model as intro

    intro_results = {r.strategy: r for r in intro.run()}
    for s in model.STRATEGIES:
        assert results[s].total_qaly < intro_results[s].total_qaly - 1.0
        assert results[s].payoff_convention == "transition"
        assert intro_results[s].payoff_convention == "state"
