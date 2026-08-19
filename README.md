# HEOR Model Replication — reproducing published cost-effectiveness models in Python

Two peer-reviewed cohort state-transition models, rebuilt from their published
parameters in a general-purpose Python solver, reproducing **every printed cost,
QALY, ICER and dominance verdict exactly**.

```bash
pip install -r requirements.txt && pytest -q      # 77 passed
python3 report.py                                 # the table below, live
```

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
5. **Authorship, plainly:** the health-economics modelling, methodological
   decisions and validation design are mine; the software implementation was
   largely AI-generated under my direction and review.

Companion to the [HEOR Toolkit](https://github.com/conallaque/heor-toolkit) and
[GenomeLens](https://github.com/conallaque/genomelens). Those build models; this
one checks that the machinery agrees with the literature.

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

`tests/test_solver_equivalence.py` checks the general solver against the 3-state
Markov engine it generalises (in the sibling [HEOR
Toolkit](https://github.com/conallaque/heor-toolkit)), reproducing its totals to
the full precision that engine reports. That separates the two failure modes: if
the equivalence test is green and a replication still misses, the fault is in the
replication's parameters, not the solver.

The test skips cleanly when the toolkit is absent. To run it:

```bash
HEOR_TOOLKIT_PATH=/path/to/heor-toolkit python3 -m pytest -q
```

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
