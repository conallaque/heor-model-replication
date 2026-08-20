# HEOR Model Replication — reproducing published cost-effectiveness models in Python

[![tests](https://github.com/conallaque/heor-model-replication/actions/workflows/tests.yml/badge.svg)](https://github.com/conallaque/heor-model-replication/actions/workflows/tests.yml)

I rebuilt three published health-economic models from their printed parameters,
using one general-purpose Python solver, and checked whether it reproduces every
cost, effect, ICER, and dominance verdict the papers report. It does — exactly.

The badge is the claim, not decoration. CI reruns every replication from scratch
on Python 3.10 and 3.13, and `report.py` exits non-zero if a single published
value is missed. A green check means the tables below were reproduced on a clean
machine, so you don't have to take this page's word for it.

```bash
pip install -r requirements.txt && pytest -q      # 100 passed, 3 skipped
python3 report.py                                 # the tables below, live
```

The 3 skips are an optional cross-check against the sibling engine this solver
generalises — see [Verifying the solver itself](#verifying-the-solver-itself).
Everything backing the claim runs on a clean clone with no setup.

```
Sick-Sicker, time-independent — Alarid-Escudero et al., Med Decis Making 2023;43(1):3-20

Strategy                  Cost (pub)   Cost (ours)    QALYs (pub)   QALYs (ours)   ICER (pub)  ICER (ours)
─────────────────────────────────────────────────────────────────────────────────────────────────────────────
Standard of care             151,580       151,580         20.711         20.711       — (ND)       — (ND)  ✓
Strategy A                   284,805       284,805         21.499         21.499        — (D)        — (D)  ✓
Strategy B                   259,100       259,100         22.184         22.184       72,988       72,988  ✓
Strategy AB                  378,875       378,875         23.137         23.137      125,764      125,764  ✓

Sick-Sicker, age-dependent — Alarid-Escudero et al., Med Decis Making 2023;43(1):21-41

Strategy                  Cost (pub)   Cost (ours)    QALYs (pub)   QALYs (ours)   ICER (pub)  ICER (ours)
─────────────────────────────────────────────────────────────────────────────────────────────────────────────
Standard of care             116,374       116,374         18.879         18.879       — (ND)       — (ND)  ✓
Strategy A                   218,789       218,789         19.636         19.636        — (D)        — (D)  ✓
Strategy B                   202,536       202,536         20.199         20.199       65,288       65,288  ✓
Strategy AB                  296,300       296,300         21.097         21.097      104,461      104,461  ✓

HIV combination therapy — Briggs et al., DMHEE (2006), via the heemod R package

Strategy                    Cost (pub)     Cost (ours)   Life-years (pub)  Life-years (ours)   ICER (pub)  ICER (ours)
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Monotherapy                  44,663.45       44,663.45           7.991207           7.991207       — (ND)       — (ND)  ✓
Combination therapy          50,601.65       50,601.65           8.937389           8.937389    6,275.956    6,275.956  ✓
```

---

## The 30-second version

1. **What this is.** Published health-economic models, re-implemented from their
   parameters and checked against their printed results. It isn't a wrapper
   around an existing library — I wrote the solver from first principles so every
   modelling convention is visible in the code.
2. **Why I built it.** A model engine is only as trustworthy as its agreement
   with work that's already been through peer review. This repo is that
   agreement, made executable.
3. **The claim is a test, not a sentence.** `pytest` asserts the published
   numbers directly. If a value drifts, the suite goes red. None of this is
   verified by reading prose.
4. **Where the numbers came from.** Every published value carries its URL and
   retrieval date in `reference.py`. Nothing is recalled from memory or inferred.
5. **It found something.** Two of the papers print a parameter that doesn't
   reproduce their own results — see
   [What the replication found](#what-the-replication-found).
6. **Authorship, plainly.** The health-economics modelling, methodological
   decisions, and validation design are mine; the software implementation was
   largely AI-generated under my direction and review.

Companion to [GenomeLens](https://github.com/conallaque/genomelens) and to a
sibling HEOR toolkit (not currently public). Those build models; this one checks
that the machinery agrees with the literature.

### Where to look

```
cstm/                    the solver — a general N-state cohort model, ~500 lines
replications/            one directory per published model
  darth2023_intro/         model.py = the parameters · reference.py = the targets
  darth2023_timedep/
  heemod_dmhee_hiv/
tests/                   the claim, as assertions — this is the proof
data/                    the one input file, with its provenance
report.py                run this: prints published vs. computed, exits 1 on a miss
```

**Reading it in five minutes:** the [`report.py`](report.py) output is at the top
of this page. Then open any one `reference.py` —
[`heemod_dmhee_hiv/reference.py`](replications/heemod_dmhee_hiv/reference.py) is a
good one — to see what a target looks like and where it came from. Then
[`cstm/solver.py`](cstm/solver.py) is the engine all three run on.

---

## Why replication is the right test

Every parameter in a portfolio health-economics model is fair game for suspicion.
The question a reviewer actually cares about isn't "is the code elegant?" — it's
"does it produce the right number?" And that's only answerable somewhere a right
number already exists.

So that's what this repo does. Take a model whose results have been peer
reviewed, rebuild it from the parameters the authors published, and compare. The
result is binary: either the ICER lands on $72,988/QALY or it doesn't.

I used three targets rather than one, because a solver that matches a single
paper may just have been fitted to it — and two papers from the same group can
share a house style. The third comes from a different tradition entirely, and
disagrees with the first two on nearly every convention:

| Convention | DARTH tutorials (2023) | DMHEE HIV model (2006/1997) |
|---|---|---|
| Outcome measure | QALYs | **Life-years** |
| Transition probabilities | from rates, `1 − exp(−r·t)` | **from observed patient counts** |
| Treatment effect | hazard ratio on one transition | **relative risk on all transitions, expiring after 2 years** |
| Discounting | 3% costs, 3% effects | **6% costs, 0% effects** |
| Cycle counting | Simpson's 1/3 correction | **end-of-cycle, uncorrected** |
| Currency / era | USD, contemporary | **GBP, 1996** |

Matching all three is what makes the solver's generality something I can
demonstrate rather than just assert.

## What is replicated

| Replication | Source | What it exercises |
|---|---|---|
| [`darth2023_intro`](replications/darth2023_intro/) | Alarid-Escudero et al. (2023), *Med Decis Making* 43(1):3-20 | 4-state cohort model, constant transitions, Simpson's 1/3 correction, strong dominance |
| [`darth2023_timedep`](replications/darth2023_timedep/) | Alarid-Escudero et al. (2023), *Med Decis Making* 43(1):21-41 | Age-dependent mortality from a US life table, time-varying transition arrays, transition rewards |
| [`heemod_dmhee_hiv`](replications/heemod_dmhee_hiv/) | Briggs, Claxton & Sculpher, *DMHEE* (2006), after Chancellor et al. (1997) | Probabilities from observed counts, expiring treatment effect, differential discounting, end-of-cycle counting |

The first two are the Sick-Sicker model: a cohort of 25-year-olds followed to age
100 through Healthy → Sick → Sicker → Dead, comparing standard of care against a
quality-of-life treatment (A), a progression-slowing treatment (B), and both (AB).
The third compares zidovudine monotherapy against zidovudine + lamivudine
combination therapy in HIV, over 20 years.

The HIV replication is anchored twice over: it matches the R package's printed
output to the last decimal, and the £6,276 per life-year reported in the clinical
literature back in 1997. Agreeing with both means the whole chain checks out —
1997 paper → 2006 textbook → R package → this code — with no drift at any link.

## What is in the engine

| Module | Contents |
|---|---|
| [`cstm/solver.py`](cstm/solver.py) | General N-state cohort state-transition solver — arbitrary state count, time-varying transition arrays, time-varying rewards, state and transition rewards, two payoff conventions, per-cycle matrix validation |
| [`cstm/wcc.py`](cstm/wcc.py) | Within-cycle corrections (Simpson's 1/3, half-cycle) and the uncorrected counting conventions (beginning, end); rate → probability conversion; discount weights |
| [`cstm/icer.py`](cstm/icer.py) | Efficient frontier, strong dominance, iterative extended dominance, ICERs against the correct comparator |

Anything a published model might vary is an argument, never a default. That's not
generality for its own sake — a solver that hardcodes the half-cycle correction
simply can't reproduce a paper that used Simpson's rule. It'll miss by a few
percent and look completely reasonable while doing it.

## How "matching" is defined

Vague agreement is how replication claims turn unfalsifiable, so I fixed the
rules in advance:

- **Tolerance comes from the source, not from the result.** The DARTH papers
  print costs to the dollar and QALYs to three decimals; heemod prints costs to
  the penny and life-years to six figures. Each is asserted at its own printed
  precision — not at whatever precision I happened to hit.
- **ICERs are checked too, and they're the strict test.** A published ICER is
  computed from unrounded totals, so matching one implies the underlying values
  agree well past their printed precision.
- **Dominance verdicts count as results.** Reproducing the costs but
  misclassifying which strategy is dominated isn't a replication.
- **A target that doesn't match gets cut, not excused.** All three here match
  every value. If a future one doesn't, the honest options are to find the
  structural reason or drop it — never to widen the tolerance until it passes.

This is a tighter bar than the face-validity check in the sibling toolkit, which
only asks for the right direction and order of magnitude against published ICERs.
That one answers "is the engine sane?"; this repo answers "does it reproduce the
literature?"

## What the replication found

Both DARTH papers print **$12,000** as the annual cost of treatment B in their
parameter tables. Both of the authors' analysis scripts use **$13,000**. Only
$13,000 reproduces the papers' own published results:

| | Strategy B cost | ICER |
|---|---|---|
| Published (intro, Table 5) | $259,100 | $72,988 |
| Replication at `c_trtB = 13,000` (the code) | **$259,100** ✓ | **$72,988** ✓ |
| Replication at `c_trtB = 12,000` (the table) | $249,119 ✗ | $66,212 ✗ |
| Published (time-dependent, Table 3) | $202,536 | $65,288 |
| Replication at `c_trtB = 13,000` | **$202,536** ✓ | **$65,288** ✓ |
| Replication at `c_trtB = 12,000` | $194,723 ✗ | $59,367 ✗ |

So the results follow the code, and the printed table is the outlier. The same
mismatch shows up in both papers, which points to one shared table rather than two
independent typos.

This is minor and doesn't affect the tutorials' conclusions. I'm recording it
anyway for two reasons. It's exactly the class of thing replication exists to
catch — someone who trusted the parameter table and rebuilt the model would miss
the published ICER by 9% with no indication of why. And it's a reminder that "the
paper says X" and "the paper's results were produced by X" are two different
claims.

Both directions are asserted in
[`tests/test_discrepancies.py`](tests/test_discrepancies.py): the code value
reproduces the results, and the printed value provably doesn't. If that second
assertion ever fails, this section is wrong and I'll retract it.

> The parameter tables were read by automated extraction of the PMC full text on
> 2026-08-19. That's good enough to justify the test, but anyone citing this in
> writing should put a human eye on the PDFs first. The $13,000 side needs no such
> caveat — it's in the authors' published source code, and it reproduces eight
> printed values exactly.

## Provenance

Replication is worthless if the target numbers are wrong, so no value enters this
repo from memory. Each `reference.py` records the exact URL and retrieval date for
the results, the model source code, and any data file:

- **Published results:** open-access full text on PubMed Central; the rendered
  CRAN vignette for the heemod target
- **Model parameters:** the authors' public analysis scripts and vignette sources,
  transcribed with the original R variable name next to each Python constant. The
  heemod parameters were cross-checked against a second mirror of the vignette
- **Life table:** `data/LifeTable_USA_Mx_2015.csv`, vendored unmodified from the
  authors' repository so the replication runs offline

Parameters live in `model.py` and targets live in `reference.py`, deliberately
kept apart — so no parameter can quietly drift toward the number it's supposed to
predict.

**No personal health data, enforced rather than promised.** This repo shares an
author with a genomics tool that reads real genome files, so
[`tests/test_no_genomic_data.py`](tests/test_no_genomic_data.py) scans every
tracked file for anything shaped like a genotype record — rsIDs, VCF headers,
consumer-export columns, raw base runs — and CI fails the build if it finds one.
The only data file here is an aggregate US life table, and a test asserts that's
what it is.

## Verifying the solver itself

Three checks stand behind the solver independently of any single paper.

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
an off-by-one still produces plausible-looking totals but breaks the identity
immediately. It caught exactly that bug during development, before I'd run any
replication.

**The half-cycle correction is exactly the average of the two uncorrected
conventions.** Counting the cohort at the start of each cycle overstates; counting
at the end understates; the correction splits the difference. I assert that as an
identity rather than describing it, which ties the DARTH and heemod conventions
into one framework instead of two special cases.

## Scope and limits

- Deterministic cohort models only. No probabilistic sensitivity analysis, no
  microsimulation, no state-residence (tunnel) models — the sibling toolkit covers
  PSA, CEAC, and EVPI.
- Three replications, from two traditions and two languages' idioms. Small and
  finished beats large and half-built, and the structure is set up so a fourth is
  a new directory, not a refactor.
- Effects are carried in the solver's QALY slot regardless of what the source
  actually measures. For the HIV model those are undiscounted life-years — the
  label is the replication's business, not the solver's.
- Teaching and portfolio code. Not a validated submission model, and not medical
  or financial advice.

## Licence

**All rights reserved.** Read it, clone it, run the tests — evaluating the work is
exactly what it's here for, and that holds whether you're doing it for yourself or
for an employer assessing me. What the licence doesn't do is let an organisation
put the code to work: it's a grant to people reading, not to organisations
building. Commercial use, redistribution, and derivative works need written
permission. Full terms in [`LICENSE`](LICENSE).

The replicated models and their published parameters belong to their authors and
are cited in full in each `reference.py`; this repo contains an independent
implementation, not their code. Third-party material redistributed here — the US
life table — stays under its own MIT licence, unaffected by the above. See
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).
