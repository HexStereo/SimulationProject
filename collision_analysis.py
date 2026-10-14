"""
collision_analysis.py - Theoretical & Empirical Collision Analysis
===================================================================
Provides exact mathematical formulas (Birthday problem, binomial bounds),
Wilson score confidence intervals, exact hypothesis testing, and pair-collision
simulations (including the 40-minute interval scenario).
"""

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import stats

from generators import BaseCodeGenerator


class CollisionMath:
    """Theoretical probability calculations for code collisions."""

    @staticmethod
    def pair_collision_probability(num_bins: int = 1000) -> float:
        """
        Theoretical probability of two independent uniformly distributed codes
        sharing the same value across num_bins categories.
        For first 3 digits: num_bins = 1,000 -> p = 0.001 (0.1%).
        For all 6 digits: num_bins = 1,000,000 -> p = 1e-6 (0.0001%).
        """
        if num_bins <= 0:
            raise ValueError("num_bins must be positive.")
        return 1.0 / float(num_bins)

    @staticmethod
    def birthday_probability(n_samples: int, num_bins: int = 1000) -> float:
        """
        Exact probability of at least one collision among n_samples independent codes
        distributed uniformly over num_bins categories (Birthday Problem).
        Formula: P(at least 1 collision) = 1 - prod_{k=0}^{n-1} (1 - k/M).
        """
        if n_samples <= 1:
            return 0.0
        if n_samples > num_bins:
            return 1.0

        # Exact computation in log space to avoid numerical underflow
        log_prob_no_collision = 0.0
        for k in range(n_samples):
            log_prob_no_collision += math.log(1.0 - (k / float(num_bins)))

        return 1.0 - math.exp(log_prob_no_collision)

    @staticmethod
    def birthday_approx_probability(n_samples: int, num_bins: int = 1000) -> float:
        """
        Exponential approximation for the Birthday problem:
        P ≈ 1 - exp(- n*(n-1) / (2*M))
        """
        if n_samples <= 1:
            return 0.0
        exponent = - (n_samples * (n_samples - 1)) / (2.0 * float(num_bins))
        return 1.0 - math.exp(exponent)

    @staticmethod
    def expected_collisions(n_samples: int, num_bins: int = 1000) -> float:
        """
        Expected number of colliding pairs in n_samples:
        E[C] = C(n, 2) / M = n*(n-1) / (2*M)
        """
        if n_samples <= 1:
            return 0.0
        return (n_samples * (n_samples - 1)) / (2.0 * float(num_bins))

    @staticmethod
    def sample_size_for_collision_risk(target_prob: float = 0.50, num_bins: int = 1000) -> int:
        """
        Calculates the number of codes required to achieve a target collision probability.
        For 50% probability with M=1000: n ≈ sqrt(2 * M * ln(2)) ≈ 37.2 -> 38 codes.
        """
        if not (0.0 < target_prob < 1.0):
            raise ValueError("target_prob must be strictly between 0 and 1.")
        # Approximation: n ≈ sqrt(-2 * M * ln(1 - target_prob))
        return int(math.ceil(math.sqrt(-2.0 * num_bins * math.log(1.0 - target_prob))))


class BinomialInference:
    """Statistical inference, confidence intervals, and hypothesis tests for collisions."""

    @staticmethod
    def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculates the Wilson score confidence interval for a binomial proportion.
        Superior to standard normal approximation near p=0 or p=1.
        """
        if trials == 0:
            return 0.0, 0.0
        z = stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0)
        p_hat = successes / trials
        z2 = z * z
        denominator = 1.0 + z2 / trials
        center = (p_hat + z2 / (2.0 * trials)) / denominator
        half_width = (z / denominator) * math.sqrt(
            (p_hat * (1.0 - p_hat) / trials) + (z2 / (4.0 * trials * trials))
        )
        lower = max(0.0, center - half_width)
        upper = min(1.0, center + half_width)
        return lower, upper

    @staticmethod
    def clopper_pearson_interval(successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Exact Clopper-Pearson confidence interval based on Beta distribution.
        """
        if trials == 0:
            return 0.0, 0.0
        alpha = 1.0 - confidence
        lower = 0.0 if successes == 0 else stats.beta.ppf(alpha / 2.0, successes, trials - successes + 1)
        upper = 1.0 if successes == trials else stats.beta.ppf(1.0 - alpha / 2.0, successes + 1, trials - successes)
        return float(lower), float(upper)

    @staticmethod
    def test_collision_rate(observed_collisions: int, total_trials: int,
                            hypothesized_p: float = 0.001) -> Dict[str, Any]:
        """
        Performs an exact two-sided binomial test comparing observed collisions
        against the theoretical expectation (e.g. p = 0.001 for first 3 digits).
        """
        res = stats.binomtest(observed_collisions, total_trials, p=hypothesized_p, alternative="two-sided")
        ci_low, ci_high = BinomialInference.wilson_score_interval(observed_collisions, total_trials)
        obs_rate = observed_collisions / total_trials if total_trials > 0 else 0.0

        return {
            "trials": total_trials,
            "observed_collisions": observed_collisions,
            "observed_rate": obs_rate,
            "hypothesized_rate": hypothesized_p,
            "relative_ratio": obs_rate / hypothesized_p if hypothesized_p > 0 else 0.0,
            "p_value": float(res.pvalue),
            "wilson_ci_95": (ci_low, ci_high),
            "statistically_significant": bool(res.pvalue < 0.05)
        }


def run_40min_pair_experiment(
    generator: BaseCodeGenerator,
    trials: int = 50_000,
    time_delta_seconds: float = 2400.0,  # 40 minutes = 2400 seconds
    base_timestamp: float = 1_700_000_000.0
) -> Dict[str, Any]:
    """
    Simulates the core scenario: Two codes generated approximately 40 minutes apart.
    Repeats the test over 'trials' independent runs.

    Parameters:
        generator: Code generator under test.
        trials: Number of paired code generations.
        time_delta_seconds: Interval between code 1 and code 2 (default 2400s = 40m).
        base_timestamp: Base simulated UNIX timestamp.

    Returns:
        Dict containing counts, rates, confidence intervals, and hypothesis tests.
    """
    prefix_collisions = 0
    full_collisions = 0

    generator.reset()

    # Vectorized / simulated pairs
    # For deterministic or stateful generators, each trial represents a separate inquiry pair
    for i in range(trials):
        # Stagger trial times so low-resolution time generators see varying base times
        t1 = base_timestamp + (i * 300.0)  # each trial 5 minutes after previous
        t2 = t1 + time_delta_seconds       # exactly 40 minutes later

        v1, _ = generator.generate_single(timestamp=t1)
        v2, _ = generator.generate_single(timestamp=t2)

        prefix1 = v1 // 1000
        prefix2 = v2 // 1000

        if prefix1 == prefix2:
            prefix_collisions += 1

        if v1 == v2:
            full_collisions += 1

    # Statistical evaluation
    prefix_test = BinomialInference.test_collision_rate(
        observed_collisions=prefix_collisions,
        total_trials=trials,
        hypothesized_p=0.001
    )

    full_test = BinomialInference.test_collision_rate(
        observed_collisions=full_collisions,
        total_trials=trials,
        hypothesized_p=1e-6
    )

    return {
        "generator_name": generator.name,
        "trials": trials,
        "time_delta_minutes": time_delta_seconds / 60.0,
        "prefix_collisions": prefix_collisions,
        "prefix_collision_rate": prefix_collisions / trials,
        "prefix_test": prefix_test,
        "full_collisions": full_collisions,
        "full_collision_rate": full_collisions / trials,
        "full_test": full_test
    }
