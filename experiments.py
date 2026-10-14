"""
experiments.py - Reproducible Simulation & Benchmark Experiments
================================================================
Manages:
1. 40-Minute Pair Collision Experiment across multiple generators and time deltas.
2. Multi-Scale Sample Size Scaling Benchmark (1k, 10k, 100k, 1,000,000).
3. Birthday Paradox Empirical vs Theoretical Verification Experiment.
"""

import time
import tracemalloc
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from generators import (
    BaseCodeGenerator,
    UniformReferenceGenerator,
    StandardPRNGGenerator,
    CryptographicGenerator,
    get_all_generators
)
from collision_analysis import (
    CollisionMath,
    BinomialInference,
    run_40min_pair_experiment
)
from statistics_tests import run_full_statistical_battery
from periodicity import (
    TimeCorrelationAnalysis,
    SpectralPeriodicityAnalysis,
    RecurrenceIntervalAnalysis
)


class CollisionExperimentRunner:
    """Executes comparative 40-minute and variable-interval pair collision experiments."""

    @staticmethod
    def run_all_generators_40min(
        trials: int = 50_000,
        time_delta_seconds: float = 2400.0,
        seed: int = 42
    ) -> List[Dict[str, Any]]:
        """
        Runs the 40-minute pair collision experiment across all available generators.
        """
        generators = get_all_generators(seed=seed)
        results = []

        for gen in generators:
            res = run_40min_pair_experiment(
                generator=gen,
                trials=trials,
                time_delta_seconds=time_delta_seconds
            )
            results.append(res)

        return results

    @staticmethod
    def run_interval_sweep(
        generator: BaseCodeGenerator,
        intervals_minutes: List[float] = [5.0, 10.0, 20.0, 30.0, 40.0, 60.0, 80.0, 120.0],
        trials: int = 20_000
    ) -> List[Dict[str, Any]]:
        """
        Sweeps time intervals between code pairs to observe whether collision rate
        is sensitive to specific time deltas (e.g. 40-minute resonance).
        """
        sweep_results = []
        for mins in intervals_minutes:
            res = run_40min_pair_experiment(
                generator=generator,
                trials=trials,
                time_delta_seconds=mins * 60.0
            )
            sweep_results.append({
                "interval_minutes": mins,
                "prefix_collisions": res["prefix_collisions"],
                "prefix_collision_rate": res["prefix_collision_rate"],
                "p_value": res["prefix_test"]["p_value"],
                "wilson_ci_95": res["prefix_test"]["wilson_ci_95"]
            })
        return sweep_results


class SampleScalingBenchmark:
    """Benchmarks statistical tests and performance across 1k, 10k, 100k, and 1,000,000 codes."""

    @staticmethod
    def run_benchmark(
        generator: BaseCodeGenerator,
        sample_sizes: List[int] = [1_000, 10_000, 100_000, 1_000_000]
    ) -> List[Dict[str, Any]]:
        """
        Executes statistical battery across increasing sample sizes,
        measuring execution time and peak memory consumption.
        """
        benchmark_results = []

        for n in sample_sizes:
            generator.reset()

            # Track runtime and memory
            tracemalloc.start()
            t0 = time.perf_counter()

            # Vectorized / batch generation
            int_array, _ = generator.generate_batch(count=n, step_seconds=1.0)
            t_gen = time.perf_counter() - t0

            # Execute statistical battery
            t_stat_start = time.perf_counter()
            stats_out = run_full_statistical_battery(int_array)
            t_total = time.perf_counter() - t0

            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            benchmark_results.append({
                "sample_size": n,
                "generation_time_sec": t_gen,
                "statistical_time_sec": t_total - t_gen,
                "total_time_sec": t_total,
                "peak_memory_mb": peak_mem / (1024.0 * 1024.0),
                "unique_codes": stats_out["unique_codes"],
                "chi2_prefix_p_value": stats_out["chi2_prefix"]["p_value"],
                "chi2_assumptions_met": stats_out["chi2_prefix"]["assumptions_met"],
                "chi2_method": stats_out["chi2_prefix"]["method_used"],
                "prefix_entropy_bits": stats_out["entropy"]["first_3_digits"]["observed_entropy_bits"],
                "prefix_entropy_efficiency": stats_out["entropy"]["first_3_digits"]["efficiency"],
                "runs_test_p_value": stats_out["runs_test"]["p_value"],
                "autocorr_ljung_box_p": stats_out["autocorrelation"]["ljung_box_p"]
            })

        return benchmark_results


class BirthdayParadoxExperiment:
    """Verifies Birthday Paradox empirical collision probabilities against exact mathematics."""

    @staticmethod
    def run_verification(
        generator: BaseCodeGenerator,
        sequence_lengths: List[int] = [5, 10, 20, 30, 38, 50, 75, 100],
        repetitions: int = 1_000,
        num_bins: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        For each sequence length n, generates 'repetitions' sequences of length n,
        and checks if at least one prefix collision occurs in each sequence.
        """
        results = []

        for n in sequence_lengths:
            theoretical_prob = CollisionMath.birthday_probability(n_samples=n, num_bins=num_bins)
            empirical_collisions = 0

            generator.reset()
            for _ in range(repetitions):
                int_arr, _ = generator.generate_batch(count=n)
                prefixes = int_arr // 1000
                if len(np.unique(prefixes)) < n:
                    empirical_collisions += 1

            obs_rate = empirical_collisions / float(repetitions)
            ci_low, ci_high = BinomialInference.wilson_score_interval(empirical_collisions, repetitions)

            results.append({
                "sequence_length": n,
                "repetitions": repetitions,
                "empirical_collision_rate": obs_rate,
                "theoretical_probability": theoretical_prob,
                "wilson_ci_95": (ci_low, ci_high),
                "absolute_error": abs(obs_rate - theoretical_prob)
            })

        return results
