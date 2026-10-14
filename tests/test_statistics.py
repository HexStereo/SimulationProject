"""
tests/test_statistics.py - Unit & Statistical Battery Validation Tests
"""

import math
import numpy as np
import pytest

from statistics_tests import (
    FrequencyAnalysis,
    ChiSquareSuite,
    InformationEntropySuite,
    SerialDependencySuite,
    MultipleTestingCorrection
)


def test_frequency_analysis_properties():
    """Verify first 3 digits frequency counting matches known values."""
    # 5 codes with known prefixes
    arr = np.array([123456, 123999, 456000, 999111, 0], dtype=np.int32)
    res = FrequencyAnalysis.analyze_first_3_digits(arr)

    assert res["sample_size"] == 5
    assert res["counts"][123] == 2
    assert res["counts"][456] == 1
    assert res["counts"][999] == 1
    assert res["counts"][0] == 1
    assert res["zero_count_bins"] == 996


def test_chi_square_uniform_vs_biased():
    """Chi-Square test must pass on synthetic uniform data and reject heavily biased data."""
    rng = np.random.default_rng(123)

    # 1. Truly uniform data (large sample)
    uniform_data = rng.integers(0, 1000, size=50_000)
    counts_u = np.bincount(uniform_data, minlength=1000)
    res_u = ChiSquareSuite.test_uniformity(counts_u)

    assert res_u["assumptions_met"] is True
    # For truly uniform data, p-value should comfortably exceed 0.01
    assert res_u["p_value"] > 0.01

    # 2. Heavily skewed data (all in first 100 bins)
    biased_data = rng.integers(0, 100, size=50_000)
    counts_b = np.bincount(biased_data, minlength=1000)
    res_b = ChiSquareSuite.test_uniformity(counts_b)

    assert res_b["reject_null_at_01"] is True
    assert res_b["p_value"] < 1e-10


def test_entropy_calculation():
    """Shannon entropy for 1000 uniform categories must be close to log2(1000) ≈ 9.96578 bits."""
    # Perfectly uniform distribution
    counts = np.full(1000, 100, dtype=np.int64)
    h_obs, h_max, eff = InformationEntropySuite.shannon_entropy(counts)

    expected_max = math.log2(1000)
    assert abs(h_obs - expected_max) < 1e-9
    assert abs(eff - 1.0) < 1e-9

    # Degenerate single-category distribution: entropy must be 0
    counts_degen = np.zeros(1000, dtype=np.int64)
    counts_degen[0] = 1000
    h_degen, _, eff_degen = InformationEntropySuite.shannon_entropy(counts_degen)
    assert h_degen == 0.0
    assert eff_degen == 0.0


def test_runs_test():
    """Wald-Wolfowitz runs test should detect deterministic alternation (0, 1, 0, 1...)."""
    # Alternating sequence has maximum possible runs -> strong z-score
    alternating = np.array([0, 1] * 500, dtype=np.float64)
    res_alt = SerialDependencySuite.wald_wolfowitz_runs_test(alternating)

    assert res_alt["reject_null_at_05"] is True
    assert abs(res_alt["z_score"]) > 10.0


def test_multiple_testing_correction():
    """Benjamini-Hochberg FDR correction must adjust p-values monotonically."""
    raw_p = [0.001, 0.01, 0.04, 0.20, 0.80]
    bh_out = MultipleTestingCorrection.benjamini_hochberg(raw_p, alpha=0.05)

    adj_p_vals = [item[0] for item in bh_out]
    # Adjusted p-values must be >= raw p-values
    for raw, adj in zip(raw_p, adj_p_vals):
        assert adj >= raw - 1e-12
