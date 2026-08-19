# HEOR Model Replication — reproducing published cost-effectiveness models in Python

Two peer-reviewed cohort state-transition models, rebuilt from their published
parameters in a general-purpose Python solver, reproducing **every printed cost,
QALY, ICER and dominance verdict exactly**.

```bash
pip install -r requirements.txt && pytest -q      # 80 passed, 3 skipped
python3 report.py                                 # the table below, live
```

The 3 skips are the optional cross-check against the sibling engine this solver
generalises — see [Verifying the solver itself](#verifying-the-solver-itself).
Everything that backs the claim below runs on a clean clone with no setup.

```
Sick-Sicker, time-independent — Alarid-Escudero et al., Med Decis Making 2023;43(1):3-20

Strategy            Cost (pub)  Cost (ours)  QALY (pub)  QALY (ours)  ICER (pub)  ICER (ours)
────────────────────────────────────────────────────────────────────────────────────────────
Standard of care       151,580      151,580      20.711       20.711      — (ND)       — (ND)  ✓
Strategy A             284,805      284,805      21.499       21.499       — (D)        — (D)  ✓
Strategy B             259,100      259,100      22.184       22.184      72,988       72,988  ✓
Strategy AB            378,875      378,875      23.137       23.137     125,764      125,764  ✓

Sick-Sicker, age-dependent — Alarid-Escudero et al., Med Decis Making 2023;43(1):21-41

Strategy            Cost (pub)  Cost (ours)  QALY (pub)  QALY (ours)  ICER (pub)  ICER (ours)
────────────────────────────────────────────────────────────────────────────────────────────
Standard of care       116,374      116,374      18.879       18.879      — (ND)       — (ND)  ✓
Strategy A             218,789      218,789      19.636       19.636       — (D)        — (D)  ✓
Strategy B             202,536      202,536      20.199       20.199      65,288       65,288  ✓
Strategy AB            296,300      296,300      21.097       21.097     104,461      104,461  ✓
```

---

### For reviewers — the 30-second version

1. **What this is:** published health-economic models, re-implemented from their
   parameters and checked against their printed results. Not a library wrapper —
   the solver is written from first principles so every convention is visible.
2. **Why it exists:** a model engine is only as credible as its agreement with
   work that has already been refereed. This repository is the agreement, made
   executable.
3. **The claim is a test, not a sentence.** `pytest` asserts the published
   numbers. If a value drifts, the suite goes red. Nothing here is checked by
   reading prose.
4. **Where the numbers came from:** every published value carries its URL and
   retrieval date in `reference.py`. None is recalled from memory or inferred.
5. **It found something.** Both papers' parameter tables print a cost that does
   not reproduce their own results — see
   [What the replication found](#what-the-replication-found).
6. **Authorship, plainly:** the health-economics modelling, methodological
   decisions and validation design are mine; the software implementation was
   largely AI-generated under my direction and review.

Companion to [GenomeLens](https://github.com/conallaque/genomelens) and to a
sibling HEOR toolkit (not currently public). Those build models; this one checks
that the machinery agrees with the literature.

---

## Why replication is the right test

Every parameter in a portfolio health-economics model is, fairly, suspect. The
reviewer's question is not "is the code elegant?" but "does it produce the right
number?" — and that question is only answerable where a right number already
exists.

So this repository does the one thing that answers it. Take a model whose results
have been through peer review, rebuild it from the parameters the authors
published, and compare. The result is binary and public: either the ICER lands on
$72,988/QALY or it does not.

Two targets were chosen because a solver that matches one paper may simply have
been fitted to it. These two share most of their parameters but disagree on
mortality structure, payoff accrual and reward placement — so matching both is a
claim about the solver, not about one lucky configuration.

## What is replicated

| Replication | Source | What it exercises |
|---|---|---|
| [`darth2023_intro`](replications/darth2023_intro/) | Alarid-Escudero et al. (2023), *Med Decis Making* 43(1):3-20 | 4-state cohort model, constant transitions, Simpson's 1/3 within-cycle correction, strong dominance |
| [`darth2023_timedep`](replications/darth2023_timedep/) | Alarid-Escudero et al. (2023), *Med Decis Making* 43(1):21-41 | Age-dependent mortality from a US life table, time-varying transition arrays, transition rewards, transition-dynamics formulation |

Both are the Sick-Sicker model: a cohort of 25-year-olds followed to age 100
through Healthy → Sick → Sicker → Dead, comparing standard of care against a
quality-of-life treatment (A), a progression-slowing treatment (B), and both (AB).

## What is in the engine

| Module | Contents |
|---|---|
| [`cstm/solver.py`](cstm/solver.py) | General N-state cohort state-transition solver — arbitrary state count, time-varying transition arrays, state and transition rewards, two payoff conventions, per-cycle matrix validation |
| [`cstm/wcc.py`](cstm/wcc.py) | Within-cycle corrections (Simpson's 1/3, half-cycle, none), rate → probability conversion, discount weights |
| [`cstm/icer.py`](cstm/icer.py) | Efficient frontier, strong dominance, iterative extended dominance, ICERs against the correct comparator |

Everything a published model varies is an argument, never a default. That is not
generality for its own sake: a solver that hardcodes the half-cycle correction
cannot reproduce a paper that used Simpson's rule, and will miss by a few percent
while looking entirely reasonable.

## How "matching" is defined

Loosely-defined agreement is how replication claims become unfalsifiable, so the
rules are fixed in advance:

- **Tolerance comes from the source, not from the result.** The papers print
  costs to the dollar and QALYs to three decimals, so costs are asserted to the
  dollar and QALYs to three decimals — not to whatever precision happened to be
  achieved.
- **ICERs are checked too, and they are the strict test.** A published ICER is
  computed from *unrounded* totals, so matching it to the dollar implies the
  underlying values agree well past their printed precision.
- **Dominance verdicts count as results.** Reproducing the costs while
  misclassifying which strategy is dominated is not a replication.
- **A target that does not match is cut, not excused.** Both targets here match
  every value; if a future one does not, the honest options are to find the
  structural reason or to drop it — never to widen the tolerance until it passes.

This is a tighter bar than the face-validity check in the sibling toolkit, which
asks only for the correct direction and order of magnitude against published
ICERs. That check answers "is the engine sane?"; this repository answers "does it
reproduce the literature?"

## What the replication found

Both papers' parameter tables print **$12,000** as the annual cost of treatment
B. Both of the authors' analysis scripts use **$13,000**. Only $13,000
reproduces the papers' own published results:

| | Strategy B cost | ICER |
|---|---|---|
| Published (intro, Table 5) | $259,100 | $72,988 |
| Replication at `c_trtB = 13,000` (the code) | **$259,100** ✓ | **$72,988** ✓ |
| Replication at `c_trtB = 12,000` (the table) | $249,119 ✗ | $66,212 ✗ |
| Published (time-dependent, Table 3) | $202,536 | $65,288 |
| Replication at `c_trtB = 13,000` | **$202,536** ✓ | **$65,288** ✓ |
| Replication at `c_trtB = 12,000` | $194,723 ✗ | $59,367 ✗ |

So the results follow the code, and the printed parameter table is the outlier.
The same mismatch appears in both papers, which points to one shared table rather
than two independent typos.

This is minor and does not affect the tutorials' conclusions. It is worth
recording anyway, for two reasons. It is the class of thing replication exists to
catch — a reader who trusted the parameter table and rebuilt the model would miss
the published ICER by 9% with no indication of why. And it is a reminder that
"the paper says X" and "the paper's results were produced by X" are different
claims.

Both directions are asserted in [`tests/test_discrepancies.py`](tests/test_discrepancies.py):
the code value reproduces the results, and the printed value provably does not.
If the second assertion ever fails, this section is wrong and gets retracted.

> The papers' parameter tables were read by automated extraction of the PMC full
> text on 2026-08-19. That is good enough to justify the test; anyone citing this
> in writing should put a human eye on the PDFs first. The `13,000` side needs no
> such caveat — it is in the authors' published source code, and it reproduces
> eight printed values exactly.

## Provenance

Replication is worthless if the target numbers are wrong, so no value enters this
repository from memory. Each `reference.py` records the exact URL and retrieval
date for the results table, the model source code, and any data file:

- Published results: open-access full text on PubMed Central
- Model parameters: the authors' public analysis scripts on GitHub, transcribed
  with the original R variable name beside each Python constant
- Life table: `data/LifeTable_USA_Mx_2015.csv`, vendored unmodified from the
  authors' repository so the replication runs offline

Parameters live in `model.py` and targets live in `reference.py`, deliberately
apart — so that no parameter can quietly drift toward the number it is supposed
to predict.

## Verifying the solver itself

Two checks stand behind the solver independently of any paper.

**It still agrees with the engine it generalises.**
[`tests/test_solver_equivalence.py`](tests/test_solver_equivalence.py) runs the
solver against the 3-state Markov engine it grew out of (a sibling HEOR toolkit,
not currently public) and reproduces its totals to the full precision that engine
reports. That separates the two failure modes: if the equivalence check is green
and a replication still misses, the fault is in the replication's parameters, not
the solver. These are the 3 tests that skip on a clean clone; to run them, point
the suite at a directory containing `markov_model.py`:

```bash
HEOR_TOOLKIT_PATH=/path/to/heor-toolkit python3 -m pytest -q
```

**The two payoff conventions collapse into each other when they should.** Given
only state rewards, the transition-array formulation is provably identical to
`trace @ rewards`. That identity is a sharp test of the array's cycle indexing —
an off-by-one still produces plausible totals but breaks the identity at once. It
caught exactly that bug during development, before either replication was run.

## Scope and limits

- Deterministic cohort models only. No probabilistic sensitivity analysis, no
  microsimulation, no state-residence (tunnel) models — the sibling toolkit
  covers PSA, CEAC and EVPI.
- Two replications. Small and finished beats large and half-built; the structure
  is designed so a third is a directory, not a refactor.
- Both targets come from the same research group. They differ substantially in
  structure, but a target from an unrelated group and a different modelling
  tradition would strengthen the claim further, and is the obvious next addition.
- Teaching and portfolio code. Not a validated submission model, and not medical
  or financial advice.

## Licence

MIT. The replicated models and their parameters belong to their authors and are
cited in full; this repository contains an independent implementation, not their
code.
