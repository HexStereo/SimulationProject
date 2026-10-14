"""
tests/test_generators.py - Unit & Behavioral Tests for Code Generators
"""

import time
import numpy as np
import pytest

from generators import (
    BaseCodeGenerator,
    UniformReferenceGenerator,
    StandardPRNGGenerator,
    CryptographicGenerator,
    SeedReuseGenerator,
    LowResTimestampSeedGenerator,
    ToyShortPeriodLCGGenerator,
    DigitFrequencyBiasedGenerator,
    TimeDependentDeterministicGenerator,
    ModuloBiasGenerator,
    get_all_generators
)


def test_generator_validity_and_formatting():
    """All generators must return valid integer values in [0, 999999] and 6-digit zero-padded strings."""
    generators = get_all_generators(seed=42)

    for gen in generators:
        int_arr, str_list = gen.generate_batch(count=100)
        assert len(int_arr) == 100
        assert len(str_list) == 100
        assert np.all(int_arr >= 0) and np.all(int_arr < 1_000_000)

        for s, val in zip(str_list, int_arr):
            assert len(s) == 6
            assert s.isdigit()
            assert int(s) == val


def test_seed_reuse_defect():
    """SeedReuseGenerator must repeat identical numbers after the reseed period."""
    period = 10
    gen = SeedReuseGenerator(seed=777, period_calls=period)

    seq1 = [gen.generate_single()[0] for _ in range(period)]
    seq2 = [gen.generate_single()[0] for _ in range(period)]

    assert seq1 == seq2, "SeedReuseGenerator did not repeat sequence after period_calls!"


def test_low_res_timestamp_defect():
    """LowResTimestampSeedGenerator must yield identical codes for timestamps in the same interval."""
    interval = 2400.0  # 40 minutes
    gen = LowResTimestampSeedGenerator(resolution_seconds=interval, base_seed=999)

    t0 = 1_700_000_000.0
    t_same_bucket = t0 + 100.0  # within 40 minutes
    t_next_bucket = t0 + 3000.0 # 50 minutes later

    c0, _ = gen.generate_single(timestamp=t0)
    c1, _ = gen.generate_single(timestamp=t_same_bucket)
    c2, _ = gen.generate_single(timestamp=t_next_bucket)

    assert c0 == c1, "Codes within the same time bucket must match due to low-res timestamp seed defect!"
    assert c0 != c2, "Codes in different time buckets should generally differ."


def test_short_period_lcg_defect():
    """ToyShortPeriodLCGGenerator must exhibit a deterministic cycle bounded by modulus m."""
    m = 256
    gen = ToyShortPeriodLCGGenerator(m=m, seed=123)

    outputs = [gen.generate_single()[0] for _ in range(m * 2)]
    # Must have severe duplicate density within 2*m outputs
    assert len(set(outputs)) <= m


def test_digit_bias_defect():
    """DigitFrequencyBiasedGenerator must produce biased digits at significantly higher frequency."""
    biased_digits = [7]
    gen = DigitFrequencyBiasedGenerator(biased_digits=biased_digits, bias_weight=10.0, seed=42)

    int_arr, _ = gen.generate_batch(count=10_000)
    # Count occurrence of '7' across all 6 positions
    digits = []
    for val in int_arr:
        digits.extend([int(d) for d in f"{val:06d}"])

    counts = np.bincount(digits, minlength=10)
    # '7' should have much higher share than uniform (which would be 10%)
    seven_share = counts[7] / float(len(digits))
    assert seven_share > 0.30, f"Expected digit 7 to exceed 30% of total digits, got {seven_share:.2%}"


def test_time_dependent_deterministic_defect():
    """TimeDependentDeterministicGenerator first 3 digits must be periodic with cycle_minutes."""
    cycle_min = 40.0
    gen = TimeDependentDeterministicGenerator(cycle_minutes=cycle_min, seed=42)

    t0 = 1_700_000_000.0
    t_cycle = t0 + (cycle_min * 60.0)  # exactly 40 minutes later

    v1, _ = gen.generate_single(timestamp=t0)
    v2, _ = gen.generate_single(timestamp=t_cycle)

    prefix1 = v1 // 1000
    prefix2 = v2 // 1000

    assert prefix1 == prefix2, "First 3 digits must exactly match after one full cycle interval!"
