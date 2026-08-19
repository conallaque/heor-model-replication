# Data provenance

## `LifeTable_USA_Mx_2015.csv`

US 2015 age-specific all-cause mortality hazard rates (`Mx`), by sex and total.

* **Retrieved:** 2026-08-19
* **From:** https://raw.githubusercontent.com/DARTH-git/cohort-modeling-tutorial-timedep/main/data/LifeTable_USA_Mx_2015.csv
* **Used by:** `replications/darth2023_timedep`
* **Modified:** no — vendored byte-for-byte so the replication runs offline and
  so that any future mismatch can be traced to the model rather than the input.

The DARTH tutorial derives this from the Human Mortality Database. Ages 25–99
(the model horizon) are selected at read time; the file itself is unfiltered.
