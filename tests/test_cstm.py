"""
Unit tests for the solver machinery itself
==========================================

The replication tests prove the whole pipeline lands on the published numbers.
These prove the individual pieces behave for inputs no published model in this
repo happens to exercise — degenerate cohorts, dominance ties, alternative
corrections — so that the next replication added here starts from a solver that
is known-good rather than merely known-to-match-two-papers.
"""

from __future__ import annotations

import numpy as np
import pytest

from cstm.icer import calculate_icers
from cstm.solver import check_transition_matrix, run_cstm
from cstm.wcc import discount_weights, gen_wcc, rate_to_prob


# ── within-cycle correction ───────────────────────────────────────────────────

def test_simpson_weights_match_published_r():
    """Spot-check against darthtools::gen_wcc for the tutorial's 75 cycles."""
    v = gen_wcc(75, "Simpson1/3")
    assert v.shape == (76,)
    assert v[0] == pytest.approx(1 / 3)
    assert v[75] == pytest.approx(1 / 3)
    assert v[1] == pytest.approx(2 / 3)      # R's 1-indexing puts 2/3 here first
    assert v[2] == pytest.approx(4 / 3)


def test_half_cycle_weights():
    v = gen_wcc(10, "half-cycle")
    assert v[0] == v[10] == 0.5
    assert np.all(v[1:10] == 1.0)


def test_no_correction_is_all_ones():
    assert np.all(gen_wcc(10, "none") == 1.0)


def test_beginning_and_end_drop_the_row_that_has_no_cycle():
    """heemod's two uncorrected conventions.

    A trace of ``n + 1`` rows spans only ``n`` cycles, so exactly one row has to
    be dropped: counting at the start of each cycle discards the final row,
    counting at the end discards the initial one.
    """
    beginning, end = gen_wcc(10, "beginning"), gen_wcc(10, "end")
    assert beginning[10] == 0.0 and np.all(beginning[:10] == 1.0)
    assert end[0] == 0.0 and np.all(end[1:] == 1.0)
    assert beginning.sum() == end.sum() == 10.0


def test_half_cycle_is_exactly_the_average_of_beginning_and_end():
    """The identity that explains what the half-cycle "correction" corrects.

    People enter states continuously through the cycle, so counting them all at
    the start overstates and counting them all at the end understates. Averaging
    the two conventions *is* the half-cycle correction — not an approximation of
    it.
    """
    for n in (1, 2, 10, 75):
        expected = (gen_wcc(n, "beginning") + gen_wcc(n, "end")) / 2
        assert np.allclose(gen_wcc(n, "half-cycle"), expected)


def test_unknown_correction_method_is_rejected():
    with pytest.raises(ValueError, match="method must be one of"):
        gen_wcc(10, "trapezoid")


@pytest.mark.parametrize("method", ["Simpson1/3", "half-cycle", "none"])
def test_correction_requires_positive_cycles(method):
    with pytest.raises(ValueError, match="positive"):
        gen_wcc(0, method)


def test_the_correction_actually_changes_the_answer():
    """If these agreed, choosing the method would not matter — and the whole
    premise that a replication must match the source's convention would be
    wrong. They must not agree."""
    P = np.array([[0.9, 0.1], [0.0, 1.0]])
    kw = dict(P=P, v_init=[1.0, 0.0], n_cycles=20,
              state_costs=np.array([100.0, 0.0]),
              state_utils=np.array([1.0, 0.0]))
    totals = {m: run_cstm(**kw, wcc=m).total_cost
              for m in ("Simpson1/3", "half-cycle", "beginning", "end", "none")}
    assert len(set(totals.values())) == len(totals), \
        f"two correction methods produced identical totals: {totals}"

    # And the disagreement is material, not a rounding artefact: counting at the
    # start of the cycle vs the end differs by more than a percent here, which is
    # wider than many published cost-effectiveness conclusions.
    spread = (max(totals.values()) - min(totals.values())) / min(totals.values())
    assert spread > 0.01


# ── rate / probability conversion ─────────────────────────────────────────────

def test_rate_to_prob_never_exceeds_one():
    """The reason p = 1 - exp(-rt) is used instead of r*t."""
    assert rate_to_prob(5.0) < 1.0
    assert rate_to_prob(100.0) == pytest.approx(1.0)


def test_rate_to_prob_approximates_the_rate_when_small():
    assert rate_to_prob(0.001) == pytest.approx(0.001, rel=1e-3)


def test_negative_rate_is_rejected():
    with pytest.raises(ValueError, match="rate"):
        rate_to_prob(-0.1)


def test_discount_weights_start_at_one_and_decay():
    w = discount_weights(10, 0.03)
    assert w[0] == 1.0
    assert w[1] == pytest.approx(1 / 1.03)
    assert np.all(np.diff(w) < 0)


def test_zero_discount_rate_leaves_weights_at_one():
    assert np.all(discount_weights(10, 0.0) == 1.0)


# ── transition matrix validation ──────────────────────────────────────────────

def test_leaking_cohort_is_caught():
    P = np.array([[0.9, 0.05], [0.0, 1.0]])          # row 0 sums to 0.95
    with pytest.raises(ValueError, match="sums to"):
        check_transition_matrix(P)


def test_out_of_range_probability_is_caught():
    P = np.array([[1.2, -0.2], [0.0, 1.0]])
    with pytest.raises(ValueError, match=r"outside \[0, 1\]"):
        check_transition_matrix(P)


def test_non_square_matrix_is_caught():
    with pytest.raises(ValueError, match="square"):
        check_transition_matrix(np.ones((2, 3)))


def test_initial_vector_must_sum_to_one():
    P = np.eye(2)
    with pytest.raises(ValueError, match="sums to"):
        run_cstm(P=P, v_init=[0.5, 0.4], n_cycles=5)


def test_time_varying_matrix_stack_must_match_cycle_count():
    P = np.broadcast_to(np.eye(2), (3, 2, 2))
    with pytest.raises(ValueError, match="must have 5 matrices"):
        run_cstm(P=P, v_init=[1.0, 0.0], n_cycles=5)


# ── solver behaviour ──────────────────────────────────────────────────────────

def test_absorbing_model_accrues_nothing_after_absorption():
    """A cohort that starts dead should cost nothing and gain nothing."""
    P = np.array([[1.0, 0.0], [0.0, 1.0]])
    r = run_cstm(P=P, v_init=[0.0, 1.0], n_cycles=10,
                 state_costs=np.array([500.0, 0.0]),
                 state_utils=np.array([1.0, 0.0]))
    assert r.total_cost == 0.0
    assert r.total_qaly == 0.0


def test_payoff_conventions_agree_when_rewards_are_state_only():
    """The transition formulation must reduce to the state formulation.

    Filling the reward matrix by destination state makes the transition sum
    collapse to ``trace[t] @ rewards`` for every cycle, so the two must agree to
    floating point. This is the sharpest available check on the transition
    array's indexing: shifting it by a single cycle still yields plausible
    totals, but breaks this identity at once.
    """
    rng = np.random.default_rng(20260819)
    raw = rng.random((5, 5))
    P = raw / raw.sum(axis=1, keepdims=True)
    kw = dict(P=P, v_init=[1.0, 0, 0, 0, 0], n_cycles=40,
              state_costs=rng.random(5) * 1000, state_utils=rng.random(5))
    by_state = run_cstm(**kw, payoff="state")
    by_transition = run_cstm(**kw, payoff="transition")
    assert by_state.total_cost == pytest.approx(by_transition.total_cost, rel=1e-12)
    assert by_state.total_qaly == pytest.approx(by_transition.total_qaly, rel=1e-12)


def test_payoff_conventions_diverge_once_transition_rewards_appear():
    """...and they must diverge when a reward attaches to *moving*, which is the
    only reason the transition formulation exists."""
    P = np.array([[0.8, 0.2], [0.0, 1.0]])
    costs = np.array([1000.0, 0.0])
    n = 15
    by_state = run_cstm(P=P, v_init=[1.0, 0.0], n_cycles=n,
                        state_costs=costs, state_utils=np.array([1.0, 0.0]))

    R_c = np.broadcast_to(costs, (n + 1, 2, 2)).copy()
    R_c[:, 0, 1] += 5_000.0          # one-off cost of the 0 -> 1 transition
    by_transition = run_cstm(P=P, v_init=[1.0, 0.0], n_cycles=n,
                             reward_costs=R_c,
                             reward_utils=np.zeros((n + 1, 2, 2)),
                             payoff="transition")
    assert by_transition.total_cost > by_state.total_cost


def test_trace_length_and_conservation_for_a_random_valid_model():
    rng = np.random.default_rng(20260819)
    raw = rng.random((4, 4))
    P = raw / raw.sum(axis=1, keepdims=True)
    r = run_cstm(P=P, v_init=[0.25] * 4, n_cycles=30,
                 state_costs=np.zeros(4), state_utils=np.zeros(4))
    assert r.trace.shape == (31, 4)
    assert np.allclose(r.trace.sum(axis=1), 1.0)


# ── incremental analysis ──────────────────────────────────────────────────────

def test_strong_dominance_is_detected():
    rows = {r.strategy: r for r in calculate_icers(
        costs=[100, 200], effects=[2.0, 1.0], strategies=["cheap", "worse"])}
    assert rows["worse"].status == "D"
    assert rows["worse"].icer is None


def test_extended_dominance_is_detected():
    """B is not strongly dominated — it costs more and does more than A — but a
    mix of A and C beats it, which shows up as A→B's ICER exceeding B→C's."""
    rows = {r.strategy: r for r in calculate_icers(
        costs=[0, 1_000, 1_200], effects=[0.0, 1.0, 2.0],
        strategies=["A", "B", "C"])}
    assert rows["B"].status == "ED"
    assert rows["C"].status == "ND"
    assert rows["C"].icer == pytest.approx(600.0)   # vs A, not vs B


def test_icers_are_computed_against_the_frontier_not_the_baseline():
    rows = {r.strategy: r for r in calculate_icers(
        costs=[0, 100, 300], effects=[0.0, 1.0, 2.0],
        strategies=["base", "mid", "top"])}
    assert rows["mid"].icer == pytest.approx(100.0)
    assert rows["top"].icer == pytest.approx(200.0)   # (300-100)/(2-1)


def test_single_strategy_has_no_comparator():
    rows = calculate_icers([100], [1.0], ["only"])
    assert rows[0].icer is None and rows[0].status == "ND"


def test_duplicate_strategy_names_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        calculate_icers([1, 2], [1, 2], ["same", "same"])


def test_mismatched_input_lengths_are_rejected():
    with pytest.raises(ValueError, match="same length"):
        calculate_icers([1, 2], [1.0], ["a", "b"])
