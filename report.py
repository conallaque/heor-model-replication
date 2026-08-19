#!/usr/bin/env python3
"""
Print every replication side by side with the number the paper published.

    python3 report.py

No arguments, no configuration. The output is the whole claim of this
repository: for each published model, what the paper reported, what this code
computes, and the difference between them.
"""

from __future__ import annotations

import importlib
import sys
from typing import List, Tuple

from cstm.icer import calculate_icers

REPLICATIONS = (
    ("replications.darth2023_intro", "Sick-Sicker, time-independent"),
    ("replications.darth2023_timedep", "Sick-Sicker, age-dependent"),
)

W = 92


def _rule(char: str = "─") -> str:
    return char * W


def compare(module_name: str, title: str) -> Tuple[List[str], bool]:
    model = importlib.import_module(f"{module_name}.model")
    ref = importlib.import_module(f"{module_name}.reference")

    results = {r.strategy: r for r in model.run()}
    ordered = [results[s] for s in model.STRATEGIES]
    rows = {r.strategy: r for r in calculate_icers(
        [r.total_cost for r in ordered],
        [r.total_qaly for r in ordered],
        [r.strategy for r in ordered])}

    out = [_rule("═"), title, ref.CITATION, ""]
    header = (f"{'Strategy':<18}{'Cost (pub)':>12}{'Cost (ours)':>13}"
              f"{'QALY (pub)':>12}{'QALY (ours)':>13}{'ICER (pub)':>12}"
              f"{'ICER (ours)':>13}")
    out += [header, _rule()]

    all_ok = True
    for name in model.STRATEGIES:
        pub, got = ref.PUBLISHED[name], rows[name]
        cost_ok = round(got.cost) == pub["cost"]
        qaly_ok = abs(round(got.effect, 3) - pub["qaly"]) <= ref.TOLERANCE["qaly"]
        if pub["icer"] is None:
            icer_ok = got.icer is None
            icer_pub, icer_got = f"— ({pub['status']})", f"— ({got.status})"
        else:
            icer_ok = (got.icer is not None
                       and abs(round(got.icer) - pub["icer"]) <= ref.TOLERANCE["icer"])
            icer_pub, icer_got = f"{pub['icer']:,.0f}", f"{got.icer:,.0f}"
        all_ok &= cost_ok and qaly_ok and icer_ok

        mark = "✓" if (cost_ok and qaly_ok and icer_ok) else "✗"
        out.append(f"{name:<18}{pub['cost']:>12,}{got.cost:>13,.0f}"
                   f"{pub['qaly']:>12.3f}{got.effect:>13.3f}"
                   f"{icer_pub:>12}{icer_got:>13}  {mark}")

    out += ["", f"Match: {'ALL VALUES' if all_ok else 'INCOMPLETE — see failures above'}",
            f"Source of published values: {ref.SOURCES['results_table']['url']}",
            f"  (retrieved {ref.SOURCES['results_table']['retrieved']})", ""]
    return out, all_ok


def discrepancies() -> List[str]:
    """Surface anything the replication found that the papers get wrong."""
    out = [_rule("═"), "Discrepancies found by the replication", ""]
    for module_name, title in REPLICATIONS:
        ref = importlib.import_module(f"{module_name}.reference")
        for param, rec in getattr(ref, "DISCREPANCIES", {}).items():
            out.append(
                f"  {title}: {param} — paper prints "
                f"${rec['printed_in_paper']:,}, authors' code uses "
                f"${rec['used_in_code']:,}; only ${rec['reproduces_results']:,} "
                f"reproduces the published results.")
    out += ["", "  See README 'What the replication found' and "
                "tests/test_discrepancies.py.", ""]
    return out


def main() -> int:
    lines, ok = [], True
    for module_name, title in REPLICATIONS:
        block, block_ok = compare(module_name, title)
        lines += block
        ok &= block_ok
    lines += discrepancies()
    lines.append(_rule("═"))
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
