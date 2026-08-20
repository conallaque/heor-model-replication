"""
Published target values — DARTH time-dependent cSTM tutorial
============================================================

As in the introductory replication, nothing here is computed and nothing is
recalled. Every value was read from the open-access full text on PubMed Central
and from the public analysis script on **2026-08-19**.

This is the companion paper to :mod:`replications.darth2023_intro`, and the pair
is deliberate: the two models share almost every parameter but differ in three
conventions — age-dependent mortality from a life table, payoffs valued on
transitions rather than state occupancy, and one-off rewards attached to
*moving* between states. Reproducing both with the same solver is what shows the
solver isn't quietly fitted to one of them.
"""

from __future__ import annotations

EFFECT_KEY = "qaly"
EFFECT_LABEL = "QALYs"

CITATION = (
    "Alarid-Escudero F, Krijkamp E, Enns EA, Yang A, Hunink MGM, "
    "Pechlivanoglou P, Jalal H. A Tutorial on Time-Dependent Cohort "
    "State-Transition Models in R Using a Cost-Effectiveness Analysis Example. "
    "Med Decis Making. 2023;43(1):21-41. doi:10.1177/0272989X221121747"
)

SOURCES = {
    "results_table": {
        "what": "Table 3 — CEA results, simulation-time-dependent model",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9844995/",
        "retrieved": "2026-08-19",
    },
    "model_code": {
        "what": "analysis/cSTM_time_dep_simulation.R — parameters, arrays, payoffs",
        "url": ("https://raw.githubusercontent.com/DARTH-git/"
                "cohort-modeling-tutorial-timedep/main/analysis/"
                "cSTM_time_dep_simulation.R"),
        "retrieved": "2026-08-19",
    },
    "life_table": {
        "what": "data/LifeTable_USA_Mx_2015.csv — age-specific all-cause mortality",
        "url": ("https://raw.githubusercontent.com/DARTH-git/"
                "cohort-modeling-tutorial-timedep/main/data/"
                "LifeTable_USA_Mx_2015.csv"),
        "retrieved": "2026-08-19",
        "note": "Vendored unmodified into data/ so the replication is self-contained.",
    },
}

#: Table 3, exactly as printed.
PUBLISHED = {
    "Standard of care": {
        "cost": 116_374, "qaly": 18.879,
        "inc_cost": None, "inc_qaly": None, "icer": None, "status": "ND",
    },
    "Strategy A": {
        "cost": 218_789, "qaly": 19.636,
        "inc_cost": None, "inc_qaly": None, "icer": None, "status": "D",
    },
    "Strategy B": {
        "cost": 202_536, "qaly": 20.199,
        "inc_cost": 86_162, "inc_qaly": 1.320, "icer": 65_288, "status": "ND",
    },
    "Strategy AB": {
        "cost": 296_300, "qaly": 21.097,
        "inc_cost": 93_764, "inc_qaly": 0.898, "icer": 104_461, "status": "ND",
    },
}

RESULTS_QUOTE = (
    "The SoC Strategy is the least costly and effective strategy, followed by "
    "Strategy B, producing an expected benefit of 1.32 QALYs per individual for "
    "an additional expected cost of $86,162 with an ICER of $65,288/QALY "
    "followed by Strategy AB."
)

#: The same wrong cell as the introductory paper, with one difference worth
#: noting: here the body prose agrees with the table ($12,000) rather than
#: contradicting it, so only the table's own PSA column, the code, and the
#: results point to 13,000. Verified 2026-08-19 against
#: manuscript/cSTM_Tutorial_TimeDep.tex.
DISCREPANCIES = {
    "c_trtB": {
        "printed_in_paper_table": 12_000,
        "implied_by_table_psa_distribution": 12_999,   # gamma(86.2, 150.8)
        "stated_in_paper_prose": 12_000,               # agrees with the table here
        "used_in_code": 13_000,
        "reproduces_results": 13_000,
        "where_paper": "Table 2, row 'Cost of Treatment B, additional to "
                       "state-specific health care costs' — base-case column",
        "where_code": "analysis/cSTM_time_dep_simulation.R, `c_trtB <- 13000`",
        "note": (
            "At 12000, Strategy B costs $194,723 against a published $202,536 "
            "and its ICER falls to $59,367 against a published $65,288. 13000 "
            "reproduces Table 3 exactly. As in the introductory paper the "
            "table's own PSA distribution, gamma(86.2, 150.8), has mean "
            "$12,999 — so the base-case cell disagrees with the distribution "
            "printed beside it. Unlike the introductory paper, this one's body "
            "text also says $12,000, so the narrative and the table agree with "
            "each other and disagree with the code that produced the results."
        ),
        "verified": (
            "2026-08-19 from manuscript/cSTM_Tutorial_TimeDep.tex and "
            "analysis/cSTM_time_dep_simulation.R in the authors' public "
            "repository."
        ),
    },
}

TOLERANCE = {
    "cost": 1.0,
    "qaly": 0.0005,
    "icer": 1.0,
}
