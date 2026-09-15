"""Keep displayed benchmark evidence aligned with the authoritative report."""
from pathlib import Path


def test_frontend_benchmark_values_match_authoritative_report():
    report = Path("docs/BENCHMARK_REPORT.md").read_text(encoding="utf-8")
    display = Path("frontend/src/data/benchmark.js").read_text(encoding="utf-8")

    for value in ("0/21", "10/21", "11/21", "0/30", "10/10"):
        assert value in report
        assert value in display
