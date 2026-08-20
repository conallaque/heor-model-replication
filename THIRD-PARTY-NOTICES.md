# Third-party notices

The repository's [`LICENSE`](LICENSE) reserves all rights in the code and
documentation written for this project. It does **not** apply to the third-party
material listed here, which is redistributed under its own licence and carries
its own permissions. Those permissions are unaffected by anything in `LICENSE`.

---

## `data/LifeTable_USA_Mx_2015.csv`

US 2015 age-specific all-cause mortality hazard rates, used by
[`replications/darth2023_timedep`](replications/darth2023_timedep/).

* **Source:** [DARTH-git/cohort-modeling-tutorial-timedep](https://github.com/DARTH-git/cohort-modeling-tutorial-timedep)
  (`data/LifeTable_USA_Mx_2015.csv`), retrieved 2026-08-19
* **Redistributed unmodified**, byte for byte
* **Licence:** MIT

```
MIT License

Copyright (c) 2021 Decision Analysis in R for Technologies in Health (DARTH)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## The replicated models themselves

No model code from any source is reproduced in this repository — every model here
is an independent Python implementation written from published parameters. What
*is* reproduced, and what therefore needs acknowledging:

**Published parameter values and reference results**, transcribed into each
replication's `model.py` and `reference.py`. Individual facts and numbers are not
themselves copyrightable, and each is cited to its source with a retrieval date.
The models and their results remain the intellectual work of:

* **Alarid-Escudero F, Krijkamp E, Enns EA, Yang A, Hunink MGM, Pechlivanoglou P,
  Jalal H.** An Introductory Tutorial on Cohort State-Transition Models in R Using
  a Cost-Effectiveness Analysis Example. *Med Decis Making.* 2023;43(1):3-20.
  Companion analysis code released by DARTH under MIT.

* **Alarid-Escudero F, et al.** A Tutorial on Time-Dependent Cohort
  State-Transition Models in R Using a Cost-Effectiveness Analysis Example.
  *Med Decis Making.* 2023;43(1):21-41. Companion analysis code released by DARTH
  under MIT.

* **Briggs A, Claxton K, Sculpher M.** *Decision Modelling for Health Economic
  Evaluation.* Oxford University Press; 2006 — the HIV therapy model, after
  **Chancellor JV, Hill AM, Sabin CA, Simpson KN, Youle M.** Modelling the cost
  effectiveness of lamivudine/zidovudine combination therapy in HIV infection.
  *Pharmacoeconomics.* 1997;12(1):54-66. Reference implementation via the
  [`heemod`](https://github.com/aphp/heemod) R package (GPL-2+), whose vignette
  source was read to transcribe parameters. **No heemod code is included or
  derived from here** — only its published parameter values and printed output
  were used as replication targets.

The point of this repository is agreement *with* that work. Nothing here is
offered as a substitute for reading the originals, and all three are worth
reading.
