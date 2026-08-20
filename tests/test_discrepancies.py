"""
The discrepancy the replication found, pinned as a test
======================================================

Both papers' parameter tables print **$12,000** as the annual cost of treatment
B. Both of the authors' analysis scripts use **13000**. Only 13000 reproduces the
papers' own results tables.

The decisive evidence is inside the table itself: the PSA distribution printed in
the *same row*, ``gamma(86.2, 150.8)``, has mean 86.2 x 150.8 = $12,999. So the
base-case column and the distribution column of one row disagree. Treatment A's
row is consistent by contrast — ``gamma(73.5, 163.3)`` has mean $12,003, matching
its printed $12,000 — which is what makes this one mistyped cell rather than a
modelling decision.

That is a finding, not a nuisance; it is the thing replication exists to surface,
and it is only credible if it is checkable. So it is asserted from every side:

* the value in the code reproduces the published results (the two replication
  test files),
* the value printed in the table demonstrably does **not**, and
* the table's own distribution parameters imply the code's value rather than the
  printed one.

If the authors correct the tables, or if a future reading shows the transcription
was wrong, these assertions are what will catch it.

Provenance: verified 2026-08-19 against the authors' LaTeX manuscript sources
(``manuscript/cSTM_Tutorial_Intro.tex`` and ``cSTM_Tutorial_TimeDep.tex``) in
their public repositories — the source of the typeset tables themselves, rather
than text extracted from a rendered copy.
"""

from __future__ import annotations

import importlib

import pytest

from cstm.icer import calculate_icers

CASES = [
    ("replications.darth2023_intro", "Table 5"),
    ("replications.darth2023_timedep", "Table 3"),
]

#: The gamma parameters printed in the treatment-cost rows of both papers'
#: Table 2, transcribed verbatim from the manuscript source.
TABLE_PSA_DISTRIBUTIONS = {
    "c_trtA": (73.5, 163.3),
    "c_trtB": (86.2, 150.8),
}


def _run_with_trtb(module_name: str, c_trtB: int):
    """Run a replication with treatment B's cost overridden, then restore it."""
    model = importlib.import_module(f"{module_name}.model")
    original = model.C_TRTB
    try:
        model.C_TRTB = c_trtB
        results = {r.strategy: r for r in model.run()}
        ordered = [results[s] for s in model.STRATEGIES]
        return {r.strategy: r for r in calculate_icers(
            [r.total_cost for r in ordered],
            [r.total_qaly for r in ordered],
            [r.strategy for r in ordered])}
    finally:
        model.C_TRTB = original


@pytest.mark.parametrize("module_name,table", CASES)
def test_discrepancy_record_is_internally_consistent(module_name, table):
    """The recorded finding must describe the value the model actually uses."""
    model = importlib.import_module(f"{module_name}.model")
    ref = importlib.import_module(f"{module_name}.reference")
    record = ref.DISCREPANCIES["c_trtB"]

    assert record["used_in_code"] == model.C_TRTB
    assert record["reproduces_results"] == model.C_TRTB
    assert record["printed_in_paper_table"] != record["used_in_code"]
    assert record["verified"], "a discrepancy claim needs its provenance recorded"


@pytest.mark.parametrize("module_name,table", CASES)
def test_published_parameter_table_does_not_reproduce_results(module_name, table):
    """$12,000 — the printed parameter — misses the printed results.

    This is the assertion that makes the finding falsifiable rather than a claim
    in a comment. If it ever fails because 12,000 *does* reproduce the results,
    the write-up is wrong and must be retracted.
    """
    ref = importlib.import_module(f"{module_name}.reference")
    printed = ref.DISCREPANCIES["c_trtB"]["printed_in_paper_table"]

    rows = _run_with_trtb(module_name, printed)
    published = ref.PUBLISHED["Strategy B"]

    assert round(rows["Strategy B"].cost) != published["cost"], (
        f"{table}: the paper's printed c_trtB = ${printed:,} reproduces the "
        f"published cost after all — the recorded discrepancy is wrong")
    assert round(rows["Strategy B"].icer) != published["icer"]


@pytest.mark.parametrize("module_name,table", CASES)
def test_table_psa_distribution_implies_the_code_value_not_the_printed_one(
        module_name, table):
    """The strongest evidence, made executable.

    A gamma distribution's mean is shape x scale. The distribution printed
    alongside treatment B's base case implies ~$13,000, so that row contradicts
    itself — and treatment A's row does *not*, which rules out a systematic
    convention and leaves a single mistyped cell.
    """
    ref = importlib.import_module(f"{module_name}.reference")
    model = importlib.import_module(f"{module_name}.model")
    record = ref.DISCREPANCIES["c_trtB"]

    shape, scale = TABLE_PSA_DISTRIBUTIONS["c_trtB"]
    mean_b = shape * scale
    assert mean_b == pytest.approx(record["implied_by_table_psa_distribution"],
                                   abs=1.0)
    # Rounds to the code's value, not to the value printed beside it.
    assert round(mean_b, -3) == record["used_in_code"]
    assert round(mean_b, -3) != record["printed_in_paper_table"]

    # Treatment A's row is internally consistent — the control that shows this
    # is one bad cell rather than a convention applied to both treatments.
    shape_a, scale_a = TABLE_PSA_DISTRIBUTIONS["c_trtA"]
    assert round(shape_a * scale_a, -3) == model.C_TRTA


@pytest.mark.parametrize("module_name,table", CASES)
def test_overriding_the_parameter_leaves_no_residue(module_name, table):
    """The override helper must restore state, or it would poison other tests."""
    model = importlib.import_module(f"{module_name}.model")
    ref = importlib.import_module(f"{module_name}.reference")
    _run_with_trtb(module_name, 999)

    results = {r.strategy: r for r in model.run()}
    assert round(results["Strategy B"].total_cost) == ref.PUBLISHED["Strategy B"]["cost"]
