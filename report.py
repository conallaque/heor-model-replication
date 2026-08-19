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

import numpy as np

from cstm.icer import calculate_icers

REPLICATIONS = (
    ("replications.darth2023_intro", "Sick-Sicker, time-independent"),
    ("replications.darth2023_timedep", "Sick-Sicker, age-dependent"),
    ("replications.heemod_dmhee_hiv", "HIV combination therapy (DMHEE)"),
)

W = 104


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

    # Each replication declares what its source calls the effect measure (QALYs,
    # life-years) and to what precision it printed each column. Comparing on the
    # source's own terms is the whole discipline of the repository, so the report
    # reads those rather than assuming.
    key = getattr(ref, "EFFECT_KEY", "qaly")
    label = getattr(ref, "EFFECT_LABEL", "QALYs")
    tol = ref.TOLERANCE
    e_tol = tol.get(key, tol.get("qaly", 5e-4))

    def places(t: float) -> int:
        """Decimals to print, from the precision the source's tolerance implies."""
        return max(0, -int(round(np.log10(t * 2)))) if t > 0 else 6

    e_dp, c_dp, i_dp = places(e_tol), places(tol["cost"]), places(tol["icer"])
    cw, ew = 14 + c_dp, max(15, len(label) + 9)

    out = [_rule("═"), title, ref.CITATION, ""]
    header = (f"{'Strategy':<22}{'Cost (pub)':>{cw}}{'Cost (ours)':>{cw}}"
              f"{label + ' (pub)':>{ew}}{label + ' (ours)':>{ew}}"
              f"{'ICER (pub)':>13}{'ICER (ours)':>13}")
    out += [header, _rule()]

    all_ok = True
    for name in model.STRATEGIES:
        pub, got = ref.PUBLISHED[name], rows[name]
        cost_ok = abs(got.cost - pub["cost"]) <= tol["cost"]
        eff_ok = abs(got.effect - pub[key]) <= e_tol
        if pub["icer"] is None:
            icer_ok = got.icer is None
            icer_pub, icer_got = f"— ({pub['status']})", f"— ({got.status})"
        else:
            icer_ok = (got.icer is not None
                       and abs(got.icer - pub["icer"]) <= tol["icer"])
            icer_pub = f"{pub['icer']:,.{i_dp}f}"
            icer_got = f"{got.icer:,.{i_dp}f}"
        all_ok &= cost_ok and eff_ok and icer_ok

        mark = "✓" if (cost_ok and eff_ok and icer_ok) else "✗"
        out.append(f"{name:<22}{pub['cost']:>{cw},.{c_dp}f}"
                   f"{got.cost:>{cw},.{c_dp}f}"
                   f"{pub[key]:>{ew}.{e_dp}f}{got.effect:>{ew}.{e_dp}f}"
                   f"{icer_pub:>13}{icer_got:>13}  {mark}")

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
