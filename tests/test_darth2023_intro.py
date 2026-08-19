"""
The replication claim, as assertions
====================================

If any test in this file goes red, the sentence "this reproduces the published
results" is false. That is the point of writing it this way: the claim is
falsifiable by running ``pytest``, not by reading a README.

Tolerances come from the *source's* reporting precision, not from what the
implementation happens to achieve — costs printed to the dollar are checked to
the dollar, QALYs printed to three decimals are checked to three decimals.
"""

from __future__ import annotations

import numpy as np
import pytest

from cstm.icer import calculate_icers
from replications.darth2023_intro import model
from replications.darth2023_intro.reference import PUBLISHED, TOLERANCE


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
    """Total discounted cost matches Table 5 to the printed dollar."""
    got = results[strategy].total_cost
    want = PUBLISHED[strategy]["cost"]
    assert round(got) == want, f"{strategy}: got {got:,.2f}, published {want:,}"


@pytest.mark.parametrize("strategy", list(PUBLISHED))
def test_total_qaly_matches_published(results, strategy):
    """Total discounted QALYs match Table 5 to the printed three decimals."""
    got = results[strategy].total_qaly
    want = PUBLISHED[strategy]["qaly"]
    assert abs(round(got, 3) - want) <= TOLERANCE["qaly"], \
        f"{strategy}: got {got:.6f}, published {want}"


@pytest.mark.parametrize("strategy", list(PUBLISHED))
def test_dominance_status_matches_published(icer_rows, strategy):
    """Strategy A is dominated; the other three form the efficient frontier."""
    assert icer_rows[strategy].status == PUBLISHED[strategy]["status"]


@pytest.mark.parametrize("strategy", ["Strategy B", "Strategy AB"])
def test_icer_matches_published(icer_rows, strategy):
    """ICERs match to the dollar.

    A stronger check than it looks: the published ICER is computed from
    *unrounded* costs and effects, so matching it to the dollar means the
    underlying totals agree well beyond their printed precision.
    """
    got = icer_rows[strategy].icer
    want = PUBLISHED[strategy]["icer"]
    assert abs(round(got) - want) <= TOLERANCE["icer"], \
        f"{strategy}: got {got:,.2f}/QALY, published ${want:,}/QALY"


@pytest.mark.parametrize("strategy", ["Strategy B", "Strategy AB"])
def test_incremental_values_match_published(icer_rows, strategy):
    row, want = icer_rows[strategy], PUBLISHED[strategy]
    assert round(row.inc_cost) == want["inc_cost"]
    assert abs(round(row.inc_effect, 3) - want["inc_qaly"]) <= TOLERANCE["qaly"]


# ── structural checks a reviewer would run before believing any of the above ──

def test_cohort_is_conserved(results):
    """No one leaks out of the model in any cycle, in any strategy."""
    for r in results.values():
        sums = r.trace.sum(axis=1)
        assert np.allclose(sums, 1.0, atol=1e-12), \
            f"{r.strategy}: cohort sum drifts to {sums.min():.15f}/{sums.max():.15f}"


def test_death_is_absorbing(results):
    """The dead state only ever grows."""
    for r in results.values():
        dead = r.trace[:, -1]
        assert np.all(np.diff(dead) >= -1e-15), f"{r.strategy}: dead state decreases"


def test_trace_has_one_row_per_cycle_boundary(results):
    for r in results.values():
        assert r.trace.shape == (model.N_CYCLES + 1, len(model.STATES))


def test_treatment_b_slows_progression(results):
    """Face validity: B and AB should leave fewer people in Sicker than SoC/A."""
    s2_soc = results["Standard of care"].trace[:, 2].sum()
    s2_b = results["Strategy B"].trace[:, 2].sum()
    assert s2_b < s2_soc


def test_strategy_a_changes_only_rewards(results):
    """A alters utility and cost, never the transition matrix — so its trace is
    identical to standard of care's. A drifting trace would mean the treatment
    effect leaked into the wrong place."""
    assert np.allclose(results["Strategy A"].trace,
                       results["Standard of care"].trace, atol=0)
    assert np.allclose(results["Strategy AB"].trace,
                       results["Strategy B"].trace, atol=0)
