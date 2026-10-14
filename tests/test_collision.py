"""
tests/test_collision.py - Collision Probability & Hypothesis Test Validation
"""

import math
import pytest

from collision_analysis import (
    CollisionMath,
    BinomialInference,
    run_40min_pair_experiment
)
from generators import (
    UniformReferenceGenerator,
    SeedReuseGenerator,
    TimeDependentDeterministicGenerator
)


def test_collision_math_probabilities():
    """Verify pair collision and birthday paradox mathematical formulas."""
    # 1. Pair collision probability for 1000 categories = 0.001
    assert abs(CollisionMath.pair_collision_probability(1000) - 0.001) < 1e-12

    # 2. Birthday paradox for N=1 should be 0.0
    assert CollisionMath.birthday_probability(1, 1000) == 0.0

    # 3. Birthday paradox for N=38 with M=1000 should exceed 50%
    prob_38 = CollisionMath.birthday_probability(38, 1000)
    assert 0.50 <= prob_38 <= 0.52, f"Expected Birthday prob for N=38 to be ~50.5%, got {prob_38}"

    # 4. Target sample size for 50% risk with M=1000
    n_star = CollisionMath.sample_size_for_collision_risk(0.50, 1000)
    assert n_star in (37, 38)


def test_wilson_confidence_interval():
    """Wilson score confidence interval must be strictly within [0, 1] and contain point estimate."""
    p_hat = 10 / 10_000 # 0.001
    low, high = BinomialInference.wilson_score_interval(10, 10_000, confidence=0.95)

    assert 0.0 <= low <= p_hat <= high <= 1.0
    # Interval width should be small for N=10000
    assert (high - low) < 0.003


def test_pair_experiment_uniform_vs_defect():
    """Uniform generator should have ~0.1% collision rate, while defective should deviate."""
    uni = UniformReferenceGenerator(seed=42)
    res_uni = run_40min_pair_experiment(uni, trials=5_000, time_delta_seconds=2400.0)

    # Rate should be reasonably close to 0.001 (e.g. 0.000 to 0.004 with 5000 trials)
    assert res_uni["prefix_collision_rate"] < 0.01

    # Defect with 40-minute harmonic cycle
    defect = TimeDependentDeterministicGenerator(cycle_minutes=40.0, seed=42)
    res_def = run_40min_pair_experiment(defect, trials=500, time_delta_seconds=2400.0)
    # Severe collision anomaly: 40-minute cyclic defect should have 100% prefix collision
    assert res_def["prefix_collision_rate"] > 0.90
