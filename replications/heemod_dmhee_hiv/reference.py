"""
Published target values — DMHEE HIV model, via heemod
=====================================================

The third target, chosen because it comes from a different modelling tradition
than the other two. It is a **doubly anchored** replication: the numbers can be
checked against the R package's printed output *and* against the incremental
cost-effectiveness ratio reported in the clinical literature two decades earlier.

Everything here was retrieved on **2026-08-19**. Nothing is recalled.
"""

from __future__ import annotations

EFFECT_KEY = "effect"
EFFECT_LABEL = "Life-years"

CITATION = (
    "Briggs A, Claxton K, Sculpher M. Decision Modelling for Health Economic "
    "Evaluation. Oxford University Press; 2006 — HIV/AIDS zidovudine "
    "monotherapy vs. zidovudine + lamivudine combination therapy. Reproduced in "
    "the heemod R package vignette 'Reproducing Exact Results from DMHEE'."
)

UPSTREAM_CITATION = (
    "Chancellor JV, Hill AM, Sabin CA, Simpson KN, Youle M. Modelling the "
    "cost effectiveness of lamivudine/zidovudine combination therapy in "
    "HIV infection. Pharmacoeconomics. 1997;12(1):54-66."
)

SOURCES = {
    "results_table": {
        "what": "Printed summary() output — cost_total, life_year and ICER",
        "url": ("https://cran.r-project.org/web/packages/heemod/vignettes/"
                "i_reproduction.html"),
        "retrieved": "2026-08-19",
    },
    "model_code": {
        "what": "vignettes/i_reproduction.Rmd — transitions, states, run_model",
        "url": ("https://raw.githubusercontent.com/aphp/heemod/master/"
                "vignettes/i_reproduction.Rmd"),
        "retrieved": "2026-08-19",
        "note": ("Cross-checked against the CRAN mirror at "
                 "raw.githubusercontent.com/cran/heemod/master/vignettes/"
                 "i_reproduction.Rmd; the two agree on every parameter."),
    },
}

#: heemod's printed model output.
PUBLISHED = {
    "Monotherapy": {
        "cost": 44_663.45, "effect": 7.991207,
        "inc_cost": None, "inc_effect": None, "icer": None, "status": "ND",
    },
    "Combination therapy": {
        "cost": 50_601.65, "effect": 8.937389,
        "inc_cost": 5_938.20, "inc_effect": 0.946182, "icer": 6_275.956,
        "status": "ND",
    },
}

#: The second anchor: the ICER as reported in the clinical literature, quoted in
#: the search result that led to this target and consistent with the textbook.
#: Reproducing heemod's 6,275.956 to three decimals also lands on this.
PUBLISHED_LITERATURE_ICER = 6_276
LITERATURE_QUOTE = (
    "treatment with 3TC/ZDV is predicted to yield an incremental "
    "cost-effectiveness ratio of £6276 (95% CI £5337 to £9075) per life year "
    "saved (discounted at 6% per year)"
)

#: Effects are **life-years, undiscounted**, not QALYs — the convention of the
#: model's era and jurisdiction. Costs are discounted at 6%, the UK Treasury rate
#: of the time. Getting this pair wrong is the single easiest way to miss.
CONVENTIONS = {
    "outcome": "life-years (not QALYs)",
    "currency": "GBP, 1996 prices",
    "discount_costs": 0.06,
    "discount_effects": 0.0,
    "cycle_counting": "end (heemod method = 'end')",
    "within_cycle_correction": "none — this model does not correct",
}

#: heemod prints costs to 2 dp and effects to 6 significant figures, so those are
#: the tolerances. The ICER is printed to 3 dp.
TOLERANCE = {
    "cost": 0.01,
    "effect": 5e-7,
    "icer": 0.001,
}
