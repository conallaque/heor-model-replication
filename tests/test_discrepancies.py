"""
The discrepancy the replication found, pinned as a test
======================================================

Both papers' parameter tables print **$12,000** for the annual cost of treatment
B. Both of the authors' analysis scripts use **13,000**. Only 13,000 reproduces
the papers' own results tables.

That is a finding, not a nuisance — it is the thing replication exists to
surface, and it is only credible if it is checkable. So it is asserted from both
directions:

* the value in the code reproduces the published results (covered by the two
  replication test files), and
* the value in the published parameter table demonstrably does **not**.

If the authors correct the tables, or if a future reading of the PDFs shows the
extraction was wrong, the second assertion here is what will catch it.
"""

from __future__ import annotations

import importlib

import pytest

from cstm.icer import calculate_icers

CASES = [
    ("replications.darth2023_intro", "Table 5"),
    ("replications.darth2023_timedep", "Table 3"),
]


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
    assert record["printed_in_paper"] != record["used_in_code"]


@pytest.mark.parametrize("module_name,table", CASES)
def test_published_parameter_table_does_not_reproduce_results(module_name, table):
    """$12,000 — the printed parameter — misses the printed results.

    This is the assertion that makes the finding falsifiable rather than a claim
    in a comment. If it ever goes green-by-accident (i.e. this test fails because
    12,000 *does* reproduce), the discrepancy write-up is wrong and must be
    retracted.
    """
    ref = importlib.import_module(f"{module_name}.reference")
    printed = ref.DISCREPANCIES["c_trtB"]["printed_in_paper"]

    rows = _run_with_trtb(module_name, printed)
    published = ref.PUBLISHED["Strategy B"]

    assert round(rows["Strategy B"].cost) != published["cost"], (
        f"{table}: the paper's printed c_trtB = ${printed:,} reproduces the "
        f"published cost after all — the recorded discrepancy is wrong")
    assert round(rows["Strategy B"].icer) != published["icer"]


@pytest.mark.parametrize("module_name,table", CASES)
def test_overriding_the_parameter_leaves_no_residue(module_name, table):
    """The override helper must restore state, or it would poison other tests."""
    model = importlib.import_module(f"{module_name}.model")
    ref = importlib.import_module(f"{module_name}.reference")
    _run_with_trtb(module_name, 999)

    results = {r.strategy: r for r in model.run()}
    assert round(results["Strategy B"].total_cost) == ref.PUBLISHED["Strategy B"]["cost"]
