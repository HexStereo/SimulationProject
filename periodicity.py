"""
periodicity.py - Periodicity, Spectral Analysis, and Time Correlation
======================================================================
Implements:
1. Timestamp correlation analysis (Pearson & Spearman rank correlation).
2. Spectral analysis via Fast Fourier Transform (FFT) to detect hidden cycles.
3. Recurrence interval analysis (mean/min/max steps between matching prefixes).
4. PRNG state recovery vulnerability and seed sensitivity models.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import stats, signal


class TimeCorrelationAnalysis:
    """Evaluates whether code values correlate with generation timestamps."""

    @staticmethod
    def analyze_timestamp_correlation(
        timestamps: np.ndarray,
        int_array: np.ndarray
    ) -> Dict[str, Any]:
        """
        Computes Pearson and Spearman correlation between generation timestamps
        and:
        - Full 6-digit integer values.
        - First 3 digits (prefix).
        """
        if len(timestamps) != len(int_array):
            raise ValueError("Timestamps and int_array must have the same length.")

        prefixes = int_array // 1000

        # Pearson linear correlation
        pearson_val, p_pearson_val = stats.pearsonr(timestamps, int_array)
        pearson_pre, p_pearson_pre = stats.pearsonr(timestamps, prefixes)

        # Spearman rank correlation (detects monotonic non-linear relationships)
        spearman_val, p_spearman_val = stats.spearmanr(timestamps, int_array)
        spearman_pre, p_spearman_pre = stats.spearmanr(timestamps, prefixes)

        return {
            "pearson_code_vs_time": {
                "coefficient": float(pearson_val),
                "p_value": float(p_pearson_val),
                "significant_at_05": bool(p_pearson_val < 0.05)
            },
            "pearson_prefix_vs_time": {
                "coefficient": float(pearson_pre),
                "p_value": float(p_pearson_pre),
                "significant_at_05": bool(p_pearson_pre < 0.05)
            },
            "spearman_code_vs_time": {
                "coefficient": float(spearman_val),
                "p_value": float(p_spearman_val),
                "significant_at_05": bool(p_spearman_val < 0.05)
            },
            "spearman_prefix_vs_time": {
                "coefficient": float(spearman_pre),
                "p_value": float(p_spearman_pre),
                "significant_at_05": bool(p_spearman_pre < 0.05)
            }
        }


class SpectralPeriodicityAnalysis:
    """Applies FFT and periodogram to detect cyclical and periodic behavior."""

    @staticmethod
    def detect_dominant_periods(
        series: np.ndarray,
        sampling_interval_seconds: float = 1.0,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Computes power spectral density via FFT to locate harmonic peaks.
        Returns top dominant periodic components (cycles in samples and seconds).
        """
        n = len(series)
        if n < 32:
            return {"dominant_periods_samples": [], "dominant_periods_seconds": [], "is_periodic": False}

        # Normalize series
        centered = series - np.mean(series)

        # Compute FFT
        fft_vals = np.fft.rfft(centered)
        power_spectrum = np.abs(fft_vals) ** 2
        freqs = np.fft.rfftfreq(n, d=sampling_interval_seconds)

        # Exclude DC component (0 Hz)
        if len(power_spectrum) > 1:
            power_spectrum[0] = 0.0

        # Calculate Fisher's exact test / Bonferroni threshold for white-noise periodogram
        m_freqs = len(power_spectrum) - 1
        mean_power = float(np.mean(power_spectrum[1:])) if m_freqs > 0 else 1.0
        # Bonferroni threshold at alpha = 0.001 across m_freqs frequencies: ln(M / alpha)
        bonferroni_threshold_ratio = float(np.log(max(1, m_freqs) / 0.001))

        peak_indices = np.argsort(power_spectrum)[::-1][:top_k]

        dominant_components = []
        is_periodic = False

        for idx in peak_indices:
            if idx == 0 or freqs[idx] == 0:
                continue
            freq = freqs[idx]
            period_sec = 1.0 / freq
            period_samples = period_sec / sampling_interval_seconds
            pwr = float(power_spectrum[idx])
            pwr_ratio = pwr / (mean_power + 1e-12)

            if pwr_ratio > bonferroni_threshold_ratio:
                is_periodic = True

            dominant_components.append({
                "frequency_hz": float(freq),
                "period_seconds": float(period_sec),
                "period_samples": float(period_samples),
                "power": pwr,
                "power_to_mean_ratio": float(pwr_ratio),
                "bonferroni_threshold": bonferroni_threshold_ratio
            })

        return {
            "dominant_components": dominant_components,
            "is_periodic": is_periodic,
            "spectral_entropy": float(-np.sum((power_spectrum[1:] / np.sum(power_spectrum[1:])) *
                               np.log2((power_spectrum[1:] / np.sum(power_spectrum[1:])) + 1e-12)))
        }


class RecurrenceIntervalAnalysis:
    """Analyzes intervals between consecutive occurrences of identical prefixes."""

    @staticmethod
    def analyze_prefix_recurrences(int_array: np.ndarray) -> Dict[str, Any]:
        """
        Calculates recurrence intervals (waiting times) between identical first 3 digits.
        Under uniform independent distribution, waiting time for any specific prefix
        follows a Geometric distribution with p = 1/1000 -> mean = 1000 steps.
        """
        prefixes = int_array // 1000
        n = len(prefixes)

        # Map each prefix to its indices
        last_seen: Dict[int, int] = {}
        intervals: List[int] = []

        for idx, p in enumerate(prefixes):
            if p in last_seen:
                intervals.append(idx - last_seen[p])
            last_seen[p] = idx

        if not intervals:
            return {
                "total_recurrences": 0,
                "mean_interval": None,
                "min_interval": None,
                "max_interval": None,
                "theoretical_mean_interval": 1000.0,
                "immediate_repeats": 0
            }

        intervals_arr = np.array(intervals, dtype=np.int32)
        mean_int = float(np.mean(intervals_arr))
        immediate_repeats = int(np.sum(intervals_arr == 1))

        return {
            "total_recurrences": len(intervals),
            "mean_interval": mean_int,
            "std_interval": float(np.std(intervals_arr)),
            "min_interval": int(np.min(intervals_arr)),
            "max_interval": int(np.max(intervals_arr)),
            "theoretical_mean_interval": 1000.0,
            "immediate_repeats": immediate_repeats,
            "immediate_repeat_fraction": immediate_repeats / len(intervals) if intervals else 0.0
        }
