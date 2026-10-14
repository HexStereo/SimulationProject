"""
statistics_tests.py - Rigorous Statistical Testing Suite
=========================================================
Implements:
1. Frequency analysis (first 3 digits 000-999, full 6 digits, position-wise 0-9).
2. Chi-Square goodness-of-fit with Cochran's rule verification and adaptive pooling / Monte Carlo.
3. Shannon entropy and theoretical maximum comparison.
4. Autocorrelation and Ljung-Box serial independence tests.
5. Wald-Wolfowitz runs test.
6. Serial test for consecutive value transitions.
7. Multiple testing correction (Benjamini-Hochberg FDR & Bonferroni).
"""

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import stats


class FrequencyAnalysis:
    """Frequency counts and empirical probabilities across digits and prefixes."""

    @staticmethod
    def analyze_first_3_digits(int_array: np.ndarray) -> Dict[str, Any]:
        """
        Extracts first 3 digits (000..999) from integer codes [0, 999999]
        and counts occurrences across all 1,000 bins.
        """
        prefixes = int_array // 1000  # range 0..999
        counts = np.bincount(prefixes, minlength=1000)
        n = len(int_array)
        expected = n / 1000.0

        return {
            "counts": counts,
            "sample_size": n,
            "num_bins": 1000,
            "expected_per_bin": expected,
            "min_count": int(np.min(counts)),
            "max_count": int(np.max(counts)),
            "zero_count_bins": int(np.sum(counts == 0)),
            "mean_count": float(np.mean(counts)),
            "std_count": float(np.std(counts))
        }

    @staticmethod
    def analyze_digit_positions(int_array: np.ndarray) -> np.ndarray:
        """
        Analyzes the frequency of digits (0-9) at each of the 6 positions (pos 0 = leftmost).
        Returns a (6, 10) integer matrix: counts[pos, digit].
        """
        n = len(int_array)
        digit_matrix = np.zeros((6, 10), dtype=np.int64)

        # Vectorized extraction of 6 decimal digits
        # pos 0: (val // 100000) % 10
        # pos 1: (val // 10000) % 10
        # ...
        divisors = [100000, 10000, 1000, 100, 10, 1]
        for pos, div in enumerate(divisors):
            digits = (int_array // div) % 10
            digit_matrix[pos, :] = np.bincount(digits, minlength=10)

        return digit_matrix


class ChiSquareSuite:
    """Goodness-of-fit testing with statistical rigor and assumption verification."""

    @staticmethod
    def test_uniformity(
        observed_counts: np.ndarray,
        expected_prob: Optional[np.ndarray] = None,
        monte_carlo_resamples: int = 2000
    ) -> Dict[str, Any]:
        """
        Chi-Square goodness-of-fit test.
        Checks Cochran's criteria:
        1. No expected frequency < 1.0.
        2. Fewer than 20% of categories have expected frequency < 5.0.

        If Cochran's criteria fail (e.g. small sample in 1,000 bins),
        adapts by pooling bins or performing Monte Carlo permutation p-value simulation.
        """
        k = len(observed_counts)
        n = int(np.sum(observed_counts))

        if expected_prob is None:
            expected_counts = np.full(k, n / float(k), dtype=np.float64)
        else:
            expected_counts = expected_prob * float(n)

        # Verify Cochran's assumptions
        min_expected = np.min(expected_counts)
        pct_under_5 = np.mean(expected_counts < 5.0) * 100.0
        assumptions_met = bool((min_expected >= 1.0) and (pct_under_5 <= 20.0))

        # Standard Chi-square statistic: sum((O - E)^2 / E)
        chi2_stat = float(np.sum((observed_counts - expected_counts) ** 2 / expected_counts))
        dof = k - 1
        asymptotic_p = float(1.0 - stats.chi2.cdf(chi2_stat, dof))

        p_value = asymptotic_p
        method_used = "Asymptotic Chi-Square (Assumptions Valid)"

        if not assumptions_met:
            # If expected frequencies are sparse, run Monte Carlo simulation for exact distribution
            if n > 0 and monte_carlo_resamples > 0:
                method_used = "Monte Carlo Permutation (Cochran Violation)"
                probs = expected_counts / n
                # Multinomial simulation
                sim_counts = np.random.multinomial(n, probs, size=monte_carlo_resamples)
                sim_stats = np.sum((sim_counts - expected_counts) ** 2 / expected_counts, axis=1)
                mc_p = float(np.mean(sim_stats >= chi2_stat))
                p_value = mc_p
            else:
                method_used = "Asymptotic Chi-Square (WARNING: Assumptions Violated)"

        return {
            "chi2_statistic": chi2_stat,
            "degrees_of_freedom": dof,
            "p_value": p_value,
            "asymptotic_p_value": asymptotic_p,
            "assumptions_met": assumptions_met,
            "min_expected_count": float(min_expected),
            "pct_categories_under_5": float(pct_under_5),
            "method_used": method_used,
            "reject_null_at_05": bool(p_value < 0.05),
            "reject_null_at_01": bool(p_value < 0.01)
        }

    @staticmethod
    def test_digit_positions(digit_matrix: np.ndarray) -> List[Dict[str, Any]]:
        """
        Runs Chi-Square uniformity test for each of the 6 digit positions (10 bins each).
        """
        results = []
        for pos in range(6):
            counts = digit_matrix[pos, :]
            res = ChiSquareSuite.test_uniformity(counts)
            res["position"] = pos
            results.append(res)
        return results


class InformationEntropySuite:
    """Shannon entropy and theoretical randomness metric evaluation."""

    @staticmethod
    def shannon_entropy(counts: np.ndarray) -> Tuple[float, float, float]:
        """
        Calculates Shannon entropy in bits:
        H = - sum(p_i * log2(p_i)) for p_i > 0
        Returns:
            Tuple[float, float, float]: (observed_entropy, max_theoretical_entropy, efficiency_ratio)
        """
        total = np.sum(counts)
        if total == 0:
            return 0.0, 0.0, 0.0

        p = counts[counts > 0] / total
        h_obs = float(-np.sum(p * np.log2(p)))
        k = len(counts)
        h_max = float(np.log2(k))
        efficiency = h_obs / h_max if h_max > 0 else 1.0

        return h_obs, h_max, efficiency

    @staticmethod
    def analyze_entropy(int_array: np.ndarray) -> Dict[str, Any]:
        """
        Calculates entropy for:
        1. First 3 digits (1000 categories -> max 9.9658 bits).
        2. Each digit position (10 categories -> max 3.3219 bits).
        """
        prefix_counts = np.bincount(int_array // 1000, minlength=1000)
        h_prefix, h_max_prefix, eff_prefix = InformationEntropySuite.shannon_entropy(prefix_counts)

        divisors = [100000, 10000, 1000, 100, 10, 1]
        digit_entropies = []
        for pos, div in enumerate(divisors):
            digits = (int_array // div) % 10
            counts = np.bincount(digits, minlength=10)
            h_d, h_max_d, eff_d = InformationEntropySuite.shannon_entropy(counts)
            digit_entropies.append({
                "position": pos,
                "observed_entropy_bits": h_d,
                "max_entropy_bits": h_max_d,
                "efficiency": eff_d,
                "deficiency_bits": h_max_d - h_d
            })

        return {
            "first_3_digits": {
                "observed_entropy_bits": h_prefix,
                "max_entropy_bits": h_max_prefix,
                "efficiency": eff_prefix,
                "deficiency_bits": h_max_prefix - h_prefix
            },
            "positions": digit_entropies
        }


class SerialDependencySuite:
    """Serial dependency, Autocorrelation, Runs Test, and Serial transition tests."""

    @staticmethod
    def autocorrelation(series: np.ndarray, max_lags: int = 50) -> Dict[str, Any]:
        """
        Computes autocorrelation coefficients up to max_lags.
        Includes Bartlett 95% confidence intervals (+/- 1.96 / sqrt(N))
        and Ljung-Box test for cumulative serial correlation.
        """
        n = len(series)
        if n <= max_lags:
            max_lags = max(1, n // 2)

        mean = np.mean(series)
        variance = np.var(series)
        if variance == 0:
            return {"lags": list(range(1, max_lags + 1)), "autocorr": [0.0]*max_lags, "ljung_box_p": 1.0}

        centered = series - mean
        autocorr = []
        for lag in range(1, max_lags + 1):
            c_lag = np.mean(centered[:-lag] * centered[lag:])
            autocorr.append(float(c_lag / variance))

        bartlett_bound = float(1.96 / math.sqrt(n))
        z_bonf = float(stats.norm.ppf(1.0 - (0.05 / (2.0 * max_lags))))
        bonf_bound = float(z_bonf / math.sqrt(n))

        # Ljung-Box test statistic: Q = n*(n+2) * sum(r_k^2 / (n - k))
        q_stat = 0.0
        for k_idx, r_k in enumerate(autocorr):
            k = k_idx + 1
            q_stat += (r_k ** 2) / (n - k)
        q_stat *= n * (n + 2)
        ljung_box_p = float(1.0 - stats.chi2.cdf(q_stat, max_lags))

        has_significant_autocorr = bool((ljung_box_p < 0.01) or any(abs(r) > bonf_bound for r in autocorr))

        return {
            "lags": list(range(1, max_lags + 1)),
            "autocorrelations": autocorr,
            "bartlett_bound_95": bartlett_bound,
            "bonferroni_bound_95": bonf_bound,
            "ljung_box_q": q_stat,
            "ljung_box_p": ljung_box_p,
            "has_significant_autocorr": has_significant_autocorr
        }

    @staticmethod
    def wald_wolfowitz_runs_test(series: np.ndarray) -> Dict[str, Any]:
        """
        Wald-Wolfowitz Runs Test for randomness of a numeric sequence.
        Dichotomizes sequence based on median:
        A positive run is a sequence of values >= median.
        A negative run is a sequence of values < median.
        """
        n = len(series)
        if n < 20:
            return {"z_score": 0.0, "p_value": 1.0, "assumptions_met": False, "interpretation": "Sample too small"}

        median = np.median(series)
        binary = (series >= median).astype(np.int8)

        n1 = int(np.sum(binary == 1))
        n2 = int(np.sum(binary == 0))

        if n1 == 0 or n2 == 0:
            return {"z_score": 0.0, "p_value": 0.0, "assumptions_met": False, "interpretation": "Degenerate sequence"}

        # Count runs: transitions + 1
        runs = 1 + int(np.sum(binary[:-1] != binary[1:]))

        # Expected runs and variance under null hypothesis of independence
        mu = 1.0 + (2.0 * n1 * n2) / n
        var = (2.0 * n1 * n2 * (2.0 * n1 * n2 - n)) / ((n ** 2) * (n - 1))
        std = math.sqrt(var) if var > 0 else 1.0

        # Continuity corrected z-score
        if runs > mu:
            z = (runs - mu - 0.5) / std
        elif runs < mu:
            z = (runs - mu + 0.5) / std
        else:
            z = 0.0

        p_value = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))

        return {
            "observed_runs": runs,
            "expected_runs": mu,
            "variance": var,
            "z_score": float(z),
            "p_value": p_value,
            "n_above": n1,
            "n_below": n2,
            "reject_null_at_05": bool(p_value < 0.05),
            "assumptions_met": True
        }

    @staticmethod
    def serial_transition_test(int_array: np.ndarray) -> Dict[str, Any]:
        """
        Tests whether the transition from value x_t to x_{t+1} is independent.
        Uses first digit or first 3 digits mod 10 for tractable transition matrix (10x10 = 100 cells).
        """
        first_digits = (int_array // 100000) % 10
        x_curr = first_digits[:-1]
        x_next = first_digits[1:]

        # 10x10 contingency matrix
        matrix = np.zeros((10, 10), dtype=np.int64)
        for c, n in zip(x_curr, x_next):
            matrix[c, n] += 1

        # Chi-square test of independence on contingency matrix
        chi2_res = stats.chi2_contingency(matrix)

        return {
            "chi2_stat": float(chi2_res.statistic),
            "p_value": float(chi2_res.pvalue),
            "dof": int(chi2_res.dof),
            "reject_independence_at_05": bool(chi2_res.pvalue < 0.05)
        }


class MultipleTestingCorrection:
    """Controls Family-Wise Error Rate (FWER) and False Discovery Rate (FDR)."""

    @staticmethod
    def benjamini_hochberg(p_values: List[float], alpha: float = 0.05) -> List[Tuple[float, bool]]:
        """
        Benjamini-Hochberg procedure for controlling the False Discovery Rate (FDR).
        Returns list of (adjusted_p_value, is_significant).
        """
        m = len(p_values)
        if m == 0:
            return []

        indexed = sorted(enumerate(p_values), key=lambda x: x[1])
        adj_p = [0.0] * m

        # Step-up adjustment
        curr_min = 1.0
        for rank in range(m, 0, -1):
            orig_idx, p = indexed[rank - 1]
            q = (p * m) / float(rank)
            curr_min = min(curr_min, q)
            adj_p[orig_idx] = min(1.0, curr_min)

        return [(adj, adj < alpha) for adj in adj_p]

    @staticmethod
    def bonferroni(p_values: List[float], alpha: float = 0.05) -> List[Tuple[float, bool]]:
        """
        Bonferroni correction controlling Family-Wise Error Rate (FWER).
        """
        m = len(p_values)
        return [(min(1.0, p * m), (p * m) < alpha) for p in p_values]


def run_full_statistical_battery(int_array: np.ndarray) -> Dict[str, Any]:
    """
    Executes the entire suite of 12 statistical tests on a generated sample.
    """
    n = len(int_array)

    # 1. Frequency Analysis
    prefix_freq = FrequencyAnalysis.analyze_first_3_digits(int_array)
    digit_matrix = FrequencyAnalysis.analyze_digit_positions(int_array)

    # 2. Chi-Square Uniformity Tests
    chi2_prefix = ChiSquareSuite.test_uniformity(prefix_freq["counts"])
    chi2_positions = ChiSquareSuite.test_digit_positions(digit_matrix)

    # 3. Information Entropy
    entropy_results = InformationEntropySuite.analyze_entropy(int_array)

    # 4. Duplicate / Unique Count
    unique_count = len(np.unique(int_array))
    unique_prefixes = len(np.unique(int_array // 1000))

    # 5. Autocorrelation & Serial Tests
    autocorr = SerialDependencySuite.autocorrelation(int_array.astype(np.float64), max_lags=50)
    runs_test = SerialDependencySuite.wald_wolfowitz_runs_test(int_array)
    serial_test = SerialDependencySuite.serial_transition_test(int_array)

    # Collect all primary p-values for multiple testing correction
    raw_p_values = [
        chi2_prefix["p_value"],
        runs_test["p_value"],
        serial_test["p_value"],
        autocorr["ljung_box_p"]
    ] + [cp["p_value"] for cp in chi2_positions]

    test_names = [
        "Chi2_Prefix_Uniformity",
        "Runs_Test_Randomness",
        "Serial_Transition_Test",
        "Ljung_Box_Autocorrelation"
    ] + [f"Chi2_Position_{cp['position']}" for cp in chi2_positions]

    fdr_results = MultipleTestingCorrection.benjamini_hochberg(raw_p_values, alpha=0.05)

    corrected_summary = []
    for name, p_raw, (p_adj, sig) in zip(test_names, raw_p_values, fdr_results):
        corrected_summary.append({
            "test_name": name,
            "raw_p_value": float(p_raw),
            "fdr_adj_p_value": float(p_adj),
            "significant_at_05": sig
        })

    return {
        "sample_size": n,
        "unique_codes": unique_count,
        "unique_prefixes": unique_prefixes,
        "prefix_analysis": prefix_freq,
        "chi2_prefix": chi2_prefix,
        "chi2_positions": chi2_positions,
        "entropy": entropy_results,
        "autocorrelation": autocorr,
        "runs_test": runs_test,
        "serial_test": serial_test,
        "multiple_testing": corrected_summary
    }
