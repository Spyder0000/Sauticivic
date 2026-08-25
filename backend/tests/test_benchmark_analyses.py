"""Tests for the novel benchmark analyses (calibration, adversarial, equity)."""
import pytest
from bench.metrics.calibration_analysis import compute_calibration_bins, run_calibration_analysis
from bench.metrics.adversarial_stress_test import run_adversarial_stress_test, evaluate_adversarial_case
from bench.metrics.speaker_equity_analysis import run_speaker_equity_analysis


def test_compute_calibration_bins_perfect():
    # 10 decisions at 1.0 confidence, all correct -> ECE should be 0.0
    decisions = [{"confidence": 1.0, "correct": True} for _ in range(10)]
    res = compute_calibration_bins(decisions, num_bins=10)
    assert res["status"] == "ok"
    assert res["ece"] == 0.0
    assert res["total_decisions"] == 10


def test_compute_calibration_bins_empty():
    res = compute_calibration_bins([], num_bins=10)
    assert res["status"] == "not_available"
    assert res["ece"] is None


def test_run_calibration_analysis_on_corpus():
    res = run_calibration_analysis()
    assert res["status"] == "ok"
    assert res["total_decisions"] == 30
    assert 0.0 <= res["ece"] <= 1.0
    assert len(res["bins"]) == 10
    assert "Expected Calibration Error" in res["interpretation"]


def test_adversarial_stress_test_runs():
    res = run_adversarial_stress_test()
    assert res["status"] == "ok"
    assert res["total_cases"] == 10
    assert 0.0 <= res["harm_avoidance_rate"] <= 1.0
    assert len(res["per_case"]) == 10
    assert res["high_severity_breaches_count"] >= 0


def test_speaker_equity_analysis_runs():
    res = run_speaker_equity_analysis()
    assert res["status"] == "ok"
    assert res["total_speakers"] == 2
    assert "SPK-01" in res["per_speaker"]
    assert "SPK-02" in res["per_speaker"]
    assert res["equity_verdict"] in ("EQUITY_PARITY_PASSED", "EQUITY_WARNING", "EQUITY_INCONCLUSIVE_CONFOUNDED")
    assert "cross_tabulation" in res
    assert "confounding_analysis" in res
