"""
Incremental cost-effectiveness analysis: the frontier and the two dominances
===========================================================================

An ICER is only meaningful against the right comparator, and the right
comparator is the next strategy down the **efficient frontier** — not the
control arm, and not whatever the sponsor would prefer. Getting there means
removing two kinds of loser first:

**Strong (simple) dominance** — a strategy that costs more and delivers no more
benefit than some other strategy. Nobody should ever choose it.

**Extended (weak) dominance** — a strategy that survives the first test but is
beaten by a *mixture* of two others: it sits above the line joining its
neighbours, which shows up as its ICER exceeding the ICER of the strategy after
it. Removing these is iterative, because dropping one can expose another.

Only what is left gets an ICER, each against its immediate predecessor on the
frontier. Reporting an ICER for a dominated strategy is a real and common
reporting error; this module refuses to, and labels why.

The algorithm mirrors ``dampack::calculate_icers`` so that replications of
DARTH-family models produce the same table, including the ``ND`` / ``D`` / ``ED``
status column.

Reference: Drummond MF et al., *Methods for the Economic Evaluation of Health
Care Programmes*, 4th ed., ch. 4; ``dampack`` R package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

ND, D, ED = "ND", "D", "ED"


@dataclass
class ICERRow:
    strategy: str
    cost: float
    effect: float
    inc_cost: Optional[float]
    inc_effect: Optional[float]
    icer: Optional[float]
    status: str

    def __repr__(self) -> str:  # pragma: no cover - display only
        def f(x, width, spec):
            return "—".rjust(width) if x is None else format(x, spec).rjust(width)
        return (f"{self.strategy:<18} {self.cost:>12,.0f} {self.effect:>9.3f} "
                f"{f(self.inc_cost, 12, ',.0f')} {f(self.inc_effect, 10, '.3f')} "
                f"{f(self.icer, 12, ',.0f')}  {self.status}")


def calculate_icers(costs: Sequence[float],
                    effects: Sequence[float],
                    strategies: Sequence[str]) -> List[ICERRow]:
    """Return one row per strategy, ordered as a CEA table is conventionally read.

    Rows come back sorted by cost ascending (ties broken by effect descending),
    with dominated and extendedly-dominated strategies carrying ``icer=None`` and
    a status of ``D`` / ``ED``.
    """
    if not (len(costs) == len(effects) == len(strategies)):
        raise ValueError("costs, effects and strategies must be the same length")
    if len(set(strategies)) != len(strategies):
        raise ValueError("strategy names must be unique")

    rows = sorted(
        ({"strategy": s, "cost": float(c), "effect": float(e)}
         for s, c, e in zip(strategies, costs, effects)),
        key=lambda r: (r["cost"], -r["effect"]),
    )

    # ── strong dominance: costs at least as much, delivers no more benefit
    dominated = set()
    for i in range(len(rows) - 1):
        for j in range(i + 1, len(rows)):
            if rows[j]["effect"] <= rows[i]["effect"]:
                dominated.add(rows[j]["strategy"])

    # ── extended dominance: iterate, because each removal can expose another
    ext_dominated: set = set()
    while True:
        keep = [r for r in rows
                if r["strategy"] not in dominated | ext_dominated]
        icers = _frontier_icers(keep)
        newly = {keep[i]["strategy"]
                 for i in range(1, len(keep) - 1)
                 if icers[i] is not None and icers[i + 1] is not None
                 and icers[i] > icers[i + 1]}
        if not newly:
            break
        ext_dominated |= newly

    # ── final ICERs along the surviving frontier
    frontier = [r for r in rows if r["strategy"] not in dominated | ext_dominated]
    final = _frontier_icers(frontier)
    incremental = {}
    for i, r in enumerate(frontier):
        if i == 0:
            incremental[r["strategy"]] = (None, None, None)
        else:
            prev = frontier[i - 1]
            incremental[r["strategy"]] = (r["cost"] - prev["cost"],
                                          r["effect"] - prev["effect"],
                                          final[i])

    out = []
    for r in rows:
        name = r["strategy"]
        if name in dominated:
            status, inc = D, (None, None, None)
        elif name in ext_dominated:
            status, inc = ED, (None, None, None)
        else:
            status, inc = ND, incremental[name]
        out.append(ICERRow(strategy=name, cost=r["cost"], effect=r["effect"],
                           inc_cost=inc[0], inc_effect=inc[1], icer=inc[2],
                           status=status))
    return out


def _frontier_icers(rows: List[dict]) -> List[Optional[float]]:
    """ICER of each row against its predecessor; ``None`` for the first row."""
    out: List[Optional[float]] = [None]
    for i in range(1, len(rows)):
        d_e = rows[i]["effect"] - rows[i - 1]["effect"]
        d_c = rows[i]["cost"] - rows[i - 1]["cost"]
        out.append(d_c / d_e if abs(d_e) > 1e-12 else None)
    return out


def format_icer_table(rows: Sequence[ICERRow]) -> str:
    """Render the rows as the CEA table a reviewer expects to see."""
    head = (f"{'Strategy':<18} {'Cost':>12} {'QALYs':>9} "
            f"{'Inc. Cost':>12} {'Inc. QALYs':>9} {'ICER':>12}  Status")
    return "\n".join([head, "-" * len(head)] + [repr(r) for r in rows])
