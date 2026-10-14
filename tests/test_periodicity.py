"""
tests/test_periodicity.py - Periodicity, FFT & Time Correlation Tests
"""

import numpy as np
import pytest

from periodicity import (
    TimeCorrelationAnalysis,
    SpectralPeriodicityAnalysis,
    RecurrenceIntervalAnalysis
)


def test_time_correlation_detection():
    """TimeCorrelationAnalysis must detect linear relationship with timestamp."""
    timestamps = np.arange(1000, dtype=np.float64)
    # Perfectly correlated code values
    linear_codes = (timestamps * 10).astype(np.int32) % 1_000_000

    res = TimeCorrelationAnalysis.analyze_timestamp_correlation(timestamps, linear_codes)
    assert res["pearson_code_vs_time"]["significant_at_05"] is True
    assert res["pearson_code_vs_time"]["coefficient"] > 0.90


def test_spectral_fft_periodic_signal():
    """SpectralPeriodicityAnalysis must detect periodic sinusoidal harmonic."""
    # Synthetic periodic signal with period of 50 samples
    t = np.arange(2000, dtype=np.float64)
    period_samples = 50.0
    signal_50 = 500_000 + 400_000 * np.sin(2.0 * np.pi * t / period_samples)

    res = SpectralPeriodicityAnalysis.detect_dominant_periods(signal_50, sampling_interval_seconds=1.0)
    assert res["is_periodic"] is True
    top_period = res["dominant_components"][0]["period_samples"]
    assert abs(top_period - period_samples) < 2.0


def test_recurrence_interval_calculation():
    """Recurrence interval analysis should calculate step distance between duplicate prefixes."""
    # Prefixes: [1, 2, 1, 3, 1] -> prefix 1 recurs after 2 steps, then after 2 steps
    arr = np.array([1000, 2000, 1000, 3000, 1000], dtype=np.int32)
    res = RecurrenceIntervalAnalysis.analyze_prefix_recurrences(arr)

    assert res["total_recurrences"] == 2
    assert res["mean_interval"] == 2.0
    assert res["min_interval"] == 2
