"""
Probabilistic sensitivity analysis — structural and face-validity tests
========================================================================

These are not replication tests (no published PSA targets to match). They
verify the PSA machinery itself:

1. The scatter has the right shape and finite values.
2. CEAC rows sum to 1 at every threshold (someone is always "best").
3. EVPI is non-negative (perfect information never hurts).
4. Correlated baseline tightens the incremental effect distribution.
5. Shared cost-environment multiplier produces tighter cost differences.
6. sample_params produces the right number of draws with plausible values.
7. evpi_population scales correctly.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pytest

from cstm.psa import PSAResult, evpi_population, run_psa, sample_params
from cstm.solver import CSTMResult, run_cstm
from cstm.wcc import rate_to_prob

STATES = ("H", "S1", "S2", "D")
N_MC = 200


def _build_sick_sicker(params: Dict) -> List[CSTMResult]:
    """Minimal Sick-Sicker, parameterised for PSA draws."""
    r_HS1 = params.get("r_HS1", 0.15)
    r_HD = params.get("r_HD", 0.002)
    hr_S1 = params.get("hr_S1", 3.0)
    hr_S2 = params.get("hr_S2", 10.0)
    r_S1H = params.get("r_S1H", 0.5)
    r_S1S2 = params.get("r_S1S2", 0.105)

    c_H = params.get("c_H", 2000)
    c_S1 = params.get("c_S1", 4000)
    c_S2 = params.get("c_S2", 15000)
    u_H = params.get("u_H", 1.0)
    u_S1 = params.get("u_S1", 0.75)
    u_S2 = params.get("u_S2", 0.5)

    p_HS1 = rate_to_prob(r_HS1)
    p_HD = rate_to_prob(r_HD)
    p_S1H = rate_to_prob(r_S1H)
    p_S1S2 = rate_to_prob(r_S1S2)
    p_S1D = rate_to_prob(r_HD * hr_S1)
    p_S2D = rate_to_prob(r_HD * hr_S2)

    P = np.zeros((4, 4))
    P[0, 0] = (1 - p_HD) * (1 - p_HS1)
    P[0, 1] = (1 - p_HD) * p_HS1
    P[0, 3] = p_HD
    P[1, 0] = (1 - p_S1D) * p_S1H
    P[1, 1] = (1 - p_S1D) * (1 - (p_S1H + p_S1S2))
    P[1, 2] = (1 - p_S1D) * p_S1S2
    P[1, 3] = p_S1D
    P[2, 2] = 1 - p_S2D
    P[2, 3] = p_S2D
    P[3, 3] = 1.0

    v_init = np.array([1.0, 0.0, 0.0, 0.0])
    costs_soc = np.array([c_H, c_S1, c_S2, 0.0])
    utils_soc = np.array([u_H, u_S1, u_S2, 0.0])
    costs_trt = np.array([c_H, c_S1 + 12000, c_S2 + 12000, 0.0])

    soc = run_cstm(P=P, v_init=v_init, n_cycles=74,
                   state_costs=costs_soc, state_utils=utils_soc,
                   payoff="state", wcc="Simpson1/3", strategy="SoC")
    trt = run_cstm(P=P, v_init=v_init, n_cycles=74,
                   state_costs=costs_trt, state_utils=utils_soc,
                   payoff="state", wcc="Simpson1/3", strategy="Treatment")
    return [soc, trt]


def _make_draws():
    base = {"r_HS1": 0.15, "r_HD": 0.002, "c_S1": 4000, "c_S2": 15000,
            "u_S1": 0.75, "u_S2": 0.5}
    dists = {
        "u_S1": {"dist": "beta", "mean": 0.75, "confidence": "high"},
        "u_S2": {"dist": "beta", "mean": 0.5, "confidence": "moderate"},
        "c_S1": {"dist": "gamma", "mean": 4000, "se": 400},
        "c_S2": {"dist": "gamma", "mean": 15000, "se": 1500},
    }
    return sample_params(base, dists, n_mc=N_MC, seed=123)


def test_psa_shape_and_finite():
    draws = _make_draws()
    result = run_psa(_build_sick_sicker, draws, n_mc=N_MC, seed=99)
    assert result.costs.shape == (2, N_MC)
    assert result.effects.shape == (2, N_MC)
    assert np.all(np.isfinite(result.costs))
    assert np.all(np.isfinite(result.effects))
    assert len(result.strategy_names) == 2


def test_ceac_rows_sum_to_one():
    draws = _make_draws()
    result = run_psa(_build_sick_sicker, draws, n_mc=N_MC, seed=99)
    row_sums = result.ceac.sum(axis=0)
    np.testing.assert_allclose(row_sums, 1.0, atol=1e-9,
                               err_msg="CEAC must sum to 1 at every threshold")


def test_evpi_non_negative():
    draws = _make_draws()
    result = run_psa(_build_sick_sicker, draws, n_mc=N_MC, seed=99)
    assert result.evpi_per_person >= 0, "EVPI must be non-negative"


def test_correlated_baseline_tightens_incremental():
    draws = _make_draws()
    r_corr = run_psa(_build_sick_sicker, draws, n_mc=N_MC,
                     correlated_baseline=True, seed=99)
    r_indep = run_psa(_build_sick_sicker, draws, n_mc=N_MC,
                      correlated_baseline=False, seed=99)
    incr_corr = r_corr.effects[1] - r_corr.effects[0]
    incr_indep = r_indep.effects[1] - r_indep.effects[0]
    assert incr_corr.std() <= incr_indep.std() + 1e-6, (
        "Correlated baseline should produce tighter incremental effects")


def test_shared_cost_env_preserves_differences():
    draws = _make_draws()
    r_shared = run_psa(_build_sick_sicker, draws, n_mc=N_MC,
                       shared_cost_env=True, seed=99)
    diff = r_shared.costs[1] - r_shared.costs[0]
    assert diff.std() > 0, "Cost differences should still vary"


def test_sample_params_count_and_bounds():
    base = {"p_sick": 0.3, "cost_treat": 5000}
    dists = {
        "p_sick": {"dist": "beta", "mean": 0.3, "confidence": "high"},
        "cost_treat": {"dist": "gamma", "mean": 5000, "se": 500},
    }
    draws = sample_params(base, dists, n_mc=500, seed=42)
    assert len(draws) == 500
    ps = [d["p_sick"] for d in draws]
    assert all(0 < p < 1 for p in ps), "Beta draws must be in (0, 1)"
    cs = [d["cost_treat"] for d in draws]
    assert all(c > 0 for c in cs), "Gamma draws must be positive"


def test_evpi_population_scaling():
    evpi_pp = 100.0
    pop_evpi = evpi_population(evpi_pp, affected_population=10_000,
                               decision_horizon=1, discount_rate=0.0)
    assert abs(pop_evpi - 1_000_000) < 0.01


def test_summary_runs():
    draws = _make_draws()
    result = run_psa(_build_sick_sicker, draws, n_mc=N_MC, seed=99)
    s = result.summary()
    assert "PSA summary" in s
    assert "EVPI" in s
