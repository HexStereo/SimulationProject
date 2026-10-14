"""
tests/test_live_engine.py - Unit Tests for Module 1 and Module 2
=============================================================================
Tests:
- TimeSeedEngine code generation across all time seeding algorithms.
- LiveConsistencyEvaluator metrics, similarity calculations, and anomaly alerts.
- LiveStreamingManager thread lifecycle and REST snapshot payloads.
"""

import time
import pytest
import numpy as np

from time_generator import TimeSeedEngine, GeneratedCodeEvent
from live_evaluator import LiveConsistencyEvaluator, CollisionEvent
from desktop_server import LiveStreamingManager


def test_time_seed_engine_all_methods():
    methods = [
        "high_res_crypto",
        "standard_second",
        "coarse_periodic_40m",
        "harmonic_drift",
        "linear_congruential_time",
        "digit_biased_time",
    ]
    for method in methods:
        engine = TimeSeedEngine(method=method)
        event = engine.generate_next()

        assert isinstance(event, GeneratedCodeEvent)
        assert 0 <= event.code_int <= 999_999
        assert len(event.code_str) == 6
        assert event.prefix == event.code_int // 1000
        assert len(event.digit_list) == 6
        assert event.index == 1
        assert event.method_name == method
        assert isinstance(event.to_dict(), dict)


def test_time_seed_engine_standard_second_repeat():
    engine = TimeSeedEngine(method="standard_second")
    fixed_time = 1700000000.123
    ev1 = engine.generate_next(current_time=fixed_time)
    ev2 = engine.generate_next(current_time=fixed_time + 0.05) # same second!

    assert ev1.code_int == ev2.code_int
    assert ev1.prefix == ev2.prefix


def test_time_seed_engine_harmonic_drift():
    engine = TimeSeedEngine(method="harmonic_drift")
    # At t=0, phase=0 => first 3 digits should be 000
    ev0 = engine.generate_next(current_time=0.0)
    assert ev0.prefix == 0

    # At t=1200 (half of 2400s cycle) => phase=0.5 => first 3 digits ~ 500
    ev_half = engine.generate_next(current_time=1200.0)
    assert ev_half.prefix == 500


def test_live_evaluator_empty():
    evaluator = LiveConsistencyEvaluator()
    metrics = evaluator.get_live_metrics()
    assert metrics["total_generated"] == 0
    assert metrics["uniqueness_pct"] == 100.0
    assert metrics["anomaly_level"] == "CONSISTENT_UNIFORM"
    assert len(metrics["recent_codes"]) == 0


def test_live_evaluator_uniform_stream():
    engine = TimeSeedEngine(method="high_res_crypto")
    evaluator = LiveConsistencyEvaluator()

    for _ in range(200):
        ev = engine.generate_next()
        evaluator.process_code(ev)

    metrics = evaluator.get_live_metrics()
    assert metrics["total_generated"] == 200
    assert metrics["uniqueness_pct"] >= 95.0 # High uniqueness
    assert metrics["digit_similarity_pct"] < 25.0 # Should be around 10%
    assert metrics["anomaly_level"] in ("CONSISTENT_UNIFORM", "SUSPICIOUS")
    assert len(metrics["recent_codes"]) == 25


def test_live_evaluator_detects_anomaly_on_repeats():
    engine = TimeSeedEngine(method="standard_second")
    evaluator = LiveConsistencyEvaluator()

    # Feed repeated codes with the exact same timestamp
    fixed_time = 1700000000.0
    for _ in range(50):
        ev = engine.generate_next(current_time=fixed_time)
        evaluator.process_code(ev)

    metrics = evaluator.get_live_metrics()
    assert metrics["total_generated"] == 50
    assert metrics["uniqueness_pct"] < 20.0 # Repeated code drops uniqueness sharply
    assert metrics["full_collisions_count"] >= 45
    assert metrics["anomaly_score"] >= 30
    assert metrics["anomaly_level"] in ("SUSPICIOUS", "CRITICAL_ANOMALY")


def test_live_evaluator_reset():
    evaluator = LiveConsistencyEvaluator()
    engine = TimeSeedEngine(method="high_res_crypto")
    for _ in range(10):
        evaluator.process_code(engine.generate_next())

    assert evaluator.total_processed == 10
    evaluator.reset()
    assert evaluator.total_processed == 0
    assert len(evaluator.recent_events) == 0
    assert len(evaluator.recent_collisions) == 0


def test_live_streaming_manager():
    manager = LiveStreamingManager()
    manager.set_config(method="high_res_crypto", speed=50.0, is_paused=False)

    # Let daemon thread produce codes
    time.sleep(0.15)
    snapshot = manager.get_snapshot()

    assert "total_generated" in snapshot
    assert "active_method" in snapshot
    assert snapshot["active_method"] == "high_res_crypto"
    assert snapshot["speed_eps"] == 50.0
    assert snapshot["is_paused"] is False

    # Pause
    manager.set_config(is_paused=True)
    assert manager.is_paused is True
