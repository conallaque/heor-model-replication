"""
Published target values — DARTH introductory cSTM tutorial
==========================================================

Nothing in this file is computed. These are the numbers the paper printed, kept
separate from the model so that no parameter can quietly drift toward its own
target. If a value here is wrong, the replication is worthless; so each one
carries where it came from and when it was retrieved.

Every number below was read from the open-access full text on PubMed Central on
**2026-08-19**. None of it is recalled from memory.
"""

from __future__ import annotations

EFFECT_KEY = "qaly"
EFFECT_LABEL = "QALYs"

CITATION = (
    "Alarid-Escudero F, Krijkamp E, Enns EA, Yang A, Hunink MGM, "
    "Pechlivanoglou P, Jalal H. An Introductory Tutorial on Cohort "
    "State-Transition Models in R Using a Cost-Effectiveness Analysis Example. "
    "Med Decis Making. 2023;43(1):3-20. doi:10.1177/0272989X221103163"
)

SOURCES = {
    "results_table": {
        "what": "Table 5 — CEA results for the four Sick-Sicker strategies",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9742144/",
        "retrieved": "2026-08-19",
    },
    "model_code": {
        "what": "analysis/cSTM_time_indep.R — every model parameter, verbatim",
        "url": ("https://raw.githubusercontent.com/DARTH-git/"
                "cohort-modeling-tutorial-intro/main/analysis/cSTM_time_indep.R"),
        "retrieved": "2026-08-19",
    },
    "helper_functions": {
        "what": "R/Functions.R — gen_wcc, rate_to_prob, calculate_icers",
        "url": ("https://raw.githubusercontent.com/DARTH-git/"
                "cohort-modeling-tutorial-intro/main/R/Functions.R"),
        "retrieved": "2026-08-19",
    },
}

#: Table 5, exactly as printed. Costs are whole dollars, QALYs to 3 decimals —
#: which is what sets the tolerance the replication has to clear.
PUBLISHED = {
    "Standard of care": {
        "cost": 151_580, "qaly": 20.711,
        "inc_cost": None, "inc_qaly": None, "icer": None, "status": "ND",
    },
    "Strategy A": {
        "cost": 284_805, "qaly": 21.499,
        "inc_cost": None, "inc_qaly": None, "icer": None, "status": "D",
    },
    "Strategy B": {
        "cost": 259_100, "qaly": 22.184,
        "inc_cost": 107_521, "inc_qaly": 1.473, "icer": 72_988, "status": "ND",
    },
    "Strategy AB": {
        "cost": 378_875, "qaly": 23.137,
        "inc_cost": 119_775, "inc_qaly": 0.952, "icer": 125_764, "status": "ND",
    },
}

#: Quoted from the Results section, as a second check on the table.
RESULTS_QUOTE = (
    "Strategy B producing an expected incremental benefit of 1.473 QALYs per "
    "individual for an additional expected cost of $107,521 with an ICER of "
    "$72,988/QALY followed by Strategy AB with an ICER $125,764/QALY."
)

#: Discrepancies found *by* the replication — the point of doing one.
DISCREPANCIES = {
    "c_trtB": {
        "printed_in_paper": 12_000,
        "used_in_code": 13_000,
        "reproduces_results": 13_000,
        "where_paper": "Table 2, 'Cost of Treatment B, additional to "
                       "state-specific health care costs'",
        "where_code": "analysis/cSTM_time_indep.R, `c_trtB <- 13000`",
        "note": (
            "The paper's parameter table prints $12,000 for treatment B; the "
            "authors' analysis script uses 13000. Only 13000 reproduces the "
            "paper's own results table — at 12000, Strategy B costs $249,119 "
            "against a published $259,100, and its ICER falls to $66,212 against "
            "a published $72,988. So the results are internally consistent with "
            "the code, and the parameter table is where the error is. The same "
            "mismatch appears in the companion time-dependent paper, which "
            "suggests one shared table rather than two independent typos. "
            "Pinned by test_published_parameter_table_does_not_reproduce_results."
        ),
        "paper_table_retrieved": "2026-08-19 (automated extraction of the PMC "
                                 "full text; worth a human eye on the PDF before "
                                 "citing this in writing)",
    },
}

#: Reporting precision of the source, which is the honest tolerance to hold the
#: replication to. Costs printed to the dollar, QALYs to 3 dp.
TOLERANCE = {
    "cost": 1.0,        # absolute dollars
    "qaly": 0.0005,     # half of the last printed digit
    "icer": 1.0,        # dollars per QALY, after accounting for table rounding
}
