"""
The third replication claim, as assertions
==========================================

This target is doubly anchored: the same numbers are checked against the R
package's printed output *and* against the ICER reported in the clinical
literature two decades earlier. Both anchors are asserted, because agreeing with
one and not the other would itself be a finding.

The tests at the end of this file exist to prove the model is genuinely from a
different tradition than the two DARTH replications — undiscounted life-years
rather than discounted QALYs, probabilities from counts rather than rates, an
expiring treatment effect. Without those, "a third replication" would be padding.
"""

from __future__ import annotations

import numpy as np
import pytest

from replications.heemod_dmhee_hiv import model
from replications.heemod_dmhee_hiv.reference import (
    CONVENTIONS,
    PUBLISHED,
    PUBLISHED_LITERATURE_ICER,
    TOLERANCE,
)


@pytest.fixture(scope="module")
def results():
    return {r.strategy: r for r in model.run()}


@pytest.fixture(scope="module")
def icer(results):
    mono, comb = results["Monotherapy"], results["Combination therapy"]
    return ((comb.total_cost - mono.total_cost)
            / (comb.total_qaly - mono.total_qaly))


# ── anchor 1: heemod's printed output ─────────────────────────────────────────

@pytest.mark.parametrize("strategy", list(PUBLISHED))
def test_total_cost_matches_heemod(results, strategy):
    got, want = results[strategy].total_cost, PUBLISHED[strategy]["cost"]
    assert abs(got - want) <= TOLERANCE["cost"], \
        f"{strategy}: got {got:,.4f}, heemod printed {want:,.2f}"


@pytest.mark.parametrize("strategy", list(PUBLISHED))
def test_life_years_match_heemod(results, strategy):
    """Effects are life-years here, carried in the solver's QALY slot."""
    got, want = results[strategy].total_qaly, PUBLISHED[strategy]["effect"]
    assert abs(got - want) <= TOLERANCE["effect"], \
        f"{strategy}: got {got:.9f}, heemod printed {want}"


def test_icer_matches_heemod(icer):
    want = PUBLISHED["Combination therapy"]["icer"]
    assert abs(icer - want) <= TOLERANCE["icer"], \
        f"got {icer:.6f}/LY, heemod printed {want}/LY"


def test_incremental_values_match_heemod(results):
    mono, comb = results["Monotherapy"], results["Combination therapy"]
    want = PUBLISHED["Combination therapy"]
    assert abs((comb.total_cost - mono.total_cost) - want["inc_cost"]) <= 0.01
    assert abs((comb.total_qaly - mono.total_qaly) - want["inc_effect"]) <= 1e-6


# ── anchor 2: the clinical literature ─────────────────────────────────────────

def test_icer_matches_the_published_literature(icer):
    """Chancellor et al. (1997) reported £6,276 per life-year saved.

    The textbook model and the R implementation both descend from that paper, so
    landing on it is a check that the whole chain — 1997 paper → 2006 textbook →
    R package → this code — has not drifted at any link.
    """
    assert round(icer) == PUBLISHED_LITERATURE_ICER, \
        f"got £{icer:,.0f}/LY, literature reports £{PUBLISHED_LITERATURE_ICER:,}/LY"


# ── the conventions that make this a different tradition ──────────────────────

def test_effects_are_undiscounted(results):
    """0% on effects, 6% on costs — the UK convention of the model's era.

    Discounting the life-years at 6% as well, which is what a modeller trained on
    the contemporary 3%/3% convention would reach for, changes the answer
    substantially. This asserts the model really does leave them undiscounted.
    """
    assert CONVENTIONS["discount_effects"] == 0.0
    for r in results.values():
        assert r.d_e == 0.0
        assert r.d_c == 0.06


def test_undiscounted_life_years_equal_the_raw_state_time(results):
    """With no discounting and end-of-cycle counting, total effect is just the
    person-time spent alive — a check that no weighting crept in."""
    for r in results.values():
        alive = r.trace[1:, :3].sum()
        assert r.total_qaly == pytest.approx(alive, rel=1e-12)


def test_transition_probabilities_come_from_counts_not_rates(results):
    """Row A of the monotherapy matrix must be the raw observed proportions."""
    P = model.transition_arrays()["Monotherapy"][0]
    assert P[0, 0] == pytest.approx(1251 / 1734)
    assert P[0, 1] == pytest.approx(350 / 1734)
    assert P[0, 2] == pytest.approx(116 / 1734)
    assert P[0, 3] == pytest.approx(17 / 1734)
    assert P[3, 3] == 1.0


def test_treatment_effect_expires_after_two_cycles():
    """From cycle 3 the combination matrix must equal monotherapy's exactly.

    This is the model's most consequential structural feature and the easiest to
    get wrong: applying the relative risk for all 20 cycles produces a much more
    favourable ICER with no outward sign of error.
    """
    P = model.transition_arrays()
    mono, combo = P["Monotherapy"], P["Combination therapy"]
    assert not np.allclose(combo[0], mono[0]), "cycle 1 should be treated"
    assert not np.allclose(combo[1], mono[1]), "cycle 2 should be treated"
    for t in range(model.RR_DURATION, model.N_CYCLES):
        assert np.allclose(combo[t], mono[t]), f"cycle {t + 1} should be untreated"


def test_lamivudine_cost_expires_with_its_effect():
    """The drug stops being paid for at the same time it stops working."""
    combo = model.state_costs("Combination therapy")
    mono = model.state_costs("Monotherapy")
    for t in range(1, model.LAMI_DURATION + 1):
        assert combo[t, 0] == pytest.approx(mono[t, 0] + model.COST_LAMI)
    for t in range(model.LAMI_DURATION + 1, model.N_CYCLES + 1):
        assert combo[t, 0] == pytest.approx(mono[t, 0])


def test_the_dead_are_not_billed():
    """State D carries no health cost and no drug cost, in either arm."""
    for strategy in model.STRATEGIES:
        assert np.all(model.state_costs(strategy)[:, 3] == 0.0)


def test_applying_the_treatment_effect_for_all_cycles_would_miss(results, icer):
    """Pins the trap described above: the never-expiring variant does not match.

    If this ever passes trivially — i.e. the variant reproduces the published
    ICER too — then the expiry is not actually load-bearing and the docstring
    claiming it is would need correcting.
    """
    from cstm.solver import run_cstm

    P_always = np.array([model._combination_matrix(model.RR)] * model.N_CYCLES)
    never_expires = run_cstm(
        P=P_always, v_init=[1.0, 0, 0, 0], n_cycles=model.N_CYCLES,
        state_costs=model.state_costs("Combination therapy"),
        state_utils=model.LIFE_YEARS, payoff="state",
        d_c=model.D_C, d_e=model.D_E, wcc=model.WCC_METHOD)

    mono = results["Monotherapy"]
    wrong_icer = ((never_expires.total_cost - mono.total_cost)
                  / (never_expires.total_qaly - mono.total_qaly))
    assert abs(wrong_icer - icer) > 1_000, (
        "letting the treatment effect run forever barely changed the ICER — "
        "the expiry may not be doing what the model claims")


# ── structural checks ─────────────────────────────────────────────────────────

def test_cohort_is_conserved(results):
    for r in results.values():
        assert np.allclose(r.trace.sum(axis=1), 1.0, atol=1e-12)


def test_death_is_absorbing(results):
    for r in results.values():
        assert np.all(np.diff(r.trace[:, -1]) >= -1e-15)


def test_combination_therapy_keeps_more_people_alive(results):
    mono, comb = results["Monotherapy"], results["Combination therapy"]
    assert comb.trace[-1, 3] < mono.trace[-1, 3]
    assert comb.total_qaly > mono.total_qaly


def test_this_is_a_different_tradition_from_the_darth_replications():
    """Guards the claim that the third target adds coverage rather than bulk."""
    from replications.darth2023_intro import model as darth

    assert model.WCC_METHOD == "end" != darth.WCC_METHOD
    assert model.D_C != darth.D_C
    assert model.D_E == 0.0 != darth.D_E
    assert model.N_CYCLES != darth.N_CYCLES
