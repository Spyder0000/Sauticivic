"""Confidence Calibration Analysis — evaluates if gate confidence reflects true empirical accuracy.

Measures Expected Calibration Error (ECE) and produces reliability diagrams.
Framing: "When the gate says it's 70% confident, is it actually right about
70% of the time?" — a direct audit of whether the abstain mechanism's confidence
scores can be trusted, not just whether they exist.

Usage:
    PYTHONPATH=backend python3 -m bench.metrics.calibration_analysis
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

# Add backend to path so we can import the pipeline.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.pipeline import run_intake  # noqa: E402
from app.schemas import OutcomeStatus  # noqa: E402


def compute_calibration_bins(
    decisions: list[dict[str, Any]],
    num_bins: int = 10,
) -> dict[str, Any]:
    """Compute calibration bins and Expected Calibration Error (ECE).

    Each decision dict must contain:
      - 'confidence': float in [0.0, 1.0]
      - 'correct': bool

    ECE formula:
        ECE = sum_b (|B_b| / N) * |acc(B_b) - conf(B_b)|
    """
    total = len(decisions)
    if total == 0:
        return {
            "status": "not_available",
            "reason": "No decisions provided to calibrate",
            "ece": None,
            "bins": [],
            "total_decisions": 0,
        }

    bin_width = 1.0 / num_bins
    bins_data: list[dict[str, Any]] = []
    total_weighted_error = 0.0

    for b in range(num_bins):
        bin_lower = b * bin_width
        bin_upper = (b + 1) * bin_width

        # In last bin, include upper bound 1.0 (closed interval [0.9, 1.0])
        if b == num_bins - 1:
            in_bin = [
                d for d in decisions
                if bin_lower <= d["confidence"] <= bin_upper
            ]
        else:
            in_bin = [
                d for d in decisions
                if bin_lower <= d["confidence"] < bin_upper
            ]

        count = len(in_bin)
        if count > 0:
            avg_conf = sum(d["confidence"] for d in in_bin) / count
            actual_acc = sum(1 for d in in_bin if d["correct"]) / count
            gap = abs(avg_conf - actual_acc)
            weight = count / total
            total_weighted_error += weight * gap
        else:
            avg_conf = (bin_lower + bin_upper) / 2.0
            actual_acc = None
            gap = None

        bins_data.append({
            "bin_index": b,
            "bin_lower": round(bin_lower, 2),
            "bin_upper": round(bin_upper, 2),
            "count": count,
            "avg_confidence": round(avg_conf, 4) if count > 0 else None,
            "actual_accuracy": round(actual_acc, 4) if actual_acc is not None else None,
            "gap": round(gap, 4) if gap is not None else None,
        })

    return {
        "status": "ok",
        "total_decisions": total,
        "num_bins": num_bins,
        "ece": round(total_weighted_error, 4),
        "bins": bins_data,
    }


def generate_ascii_reliability_diagram(bins_data: list[dict[str, Any]]) -> str:
    """Generate a clean text-based reliability diagram for console reports."""
    lines = [
        "Reliability Diagram (Predicted Confidence vs. Actual Empirical Accuracy):",
        "--------------------------------------------------------------------------------",
        f"{'Bin Range':<14} | {'Count':<5} | {'Avg Conf':<8} | {'Actual Acc':<10} | {'Gap':<6} | Visual [Acc vs. Conf]",
        "--------------------------------------------------------------------------------",
    ]
    bar_width = 20

    for b in bins_data:
        range_str = f"[{b['bin_lower']:.1f}, {b['bin_upper']:.1f})"
        if b["bin_index"] == len(bins_data) - 1:
            range_str = f"[{b['bin_lower']:.1f}, {b['bin_upper']:.1f}]"

        if b["count"] == 0:
            lines.append(f"{range_str:<14} | {0:<5} | {'-':<8} | {'-':<10} | {'-':<6} | (no samples)")
            continue

        conf = b["avg_confidence"]
        acc = b["actual_accuracy"]
        gap = b["gap"]

        conf_bars = int(round(conf * bar_width))
        acc_bars = int(round(acc * bar_width))

        # Visual representation: Acc vs Conf
        vis = []
        for i in range(bar_width):
            if i < acc_bars and i < conf_bars:
                vis.append("█")
            elif i < acc_bars:
                vis.append("#")
            elif i < conf_bars:
                vis.append("░")
            else:
                vis.append("·")
        vis_str = "".join(vis)

        lines.append(
            f"{range_str:<14} | {b['count']:<5} | {conf:<8.1%} | {acc:<10.1%} | {gap:<6.3f} | [{vis_str}]"
        )
    lines.append("--------------------------------------------------------------------------------")
    lines.append("Legend: █ = Calibrated overlap, ░ = Overconfidence gap, # = Underconfidence gap")
    return "\n".join(lines)


def plot_reliability_diagram_png(
    calibration_result: dict[str, Any],
    output_path: Path | str,
) -> bool:
    """Render and save a matplotlib reliability diagram if matplotlib is available."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    if calibration_result.get("status") != "ok":
        return False

    bins = calibration_result["bins"]
    populated_bins = [b for b in bins if b["count"] > 0]
    if not populated_bins:
        return False

    confidences = [b["avg_confidence"] for b in populated_bins]
    accuracies = [b["actual_accuracy"] for b in populated_bins]
    counts = [b["count"] for b in populated_bins]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(7, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
    )

    # Upper plot: Reliability curve vs perfect calibration line
    ax1.plot([0, 1], [0, 1], "k--", label="Perfect Calibration (y = x)")
    ax1.plot(confidences, accuracies, "s-", color="#1f77b4", label="Observed Gate Decisions", lw=2)
    for conf, acc, cnt in zip(confidences, accuracies, counts):
        ax1.annotate(f"N={cnt}", (conf, acc), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)

    ax1.set_ylabel("Actual Empirical Accuracy", fontsize=10)
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_xlim(-0.05, 1.05)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ece_val = calibration_result.get("ece", 0.0)
    ax1.set_title(
        f"Gate Confidence Calibration (ECE = {ece_val:.3f})\n"
        f"Total Decisions: {calibration_result['total_decisions']}",
        fontsize=11,
        fontweight="bold",
    )
    ax1.legend(loc="upper left")

    # Lower plot: Histogram of sample counts per bin
    bin_centers = [(b["bin_lower"] + b["bin_upper"]) / 2.0 for b in bins]
    bin_counts = [b["count"] for b in bins]
    ax2.bar(bin_centers, bin_counts, width=0.08, color="#aec7e8", edgecolor="#1f77b4", align="center")
    ax2.set_xlabel("Predicted Confidence", fontsize=10)
    ax2.set_ylabel("Decision Count", fontsize=10)
    ax2.set_ylim(0, max(bin_counts + [1]) * 1.2)
    ax2.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return True


def run_calibration_analysis(
    corpus_path: Path | str | None = None,
    audit_log_path: Path | str | None = None,
    plot_path: Path | str | None = None,
    num_bins: int = 10,
) -> dict[str, Any]:
    """Run calibration evaluation over either corpus ground truth or audit log.

    Returns structured calibration results including ECE, bin breakdown,
    plain-language interpretation, and data provenance.
    """
    corpus_path = Path(corpus_path) if corpus_path else (
        _REPO_ROOT / "bench" / "corpus" / "tier_a_recorded" / "ground_truth.json"
    )

    decisions: list[dict[str, Any]] = []
    data_source_label = "corpus_ground_truth"

    if audit_log_path and Path(audit_log_path).exists():
        data_source_label = f"audit_log ({Path(audit_log_path).name})"
        with open(audit_log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    cls_info = entry.get("classification", {})
                    conf = cls_info.get("confidence")
                    if conf is not None:
                        expected_outcome = entry.get("expected_outcome")
                        actual_outcome = entry.get("status")
                        correct = (expected_outcome == actual_outcome) if expected_outcome else True
                        decisions.append({
                            "clip_id": entry.get("session_id", "unknown"),
                            "confidence": float(conf),
                            "correct": correct,
                        })
                except (json.JSONDecodeError, KeyError):
                    continue

    if not decisions and corpus_path.exists():
        data_source_label = f"corpus ({corpus_path.name})"
        with open(corpus_path, "r", encoding="utf-8") as f:
            corpus = json.load(f)

        for clip in corpus:
            transcript = clip["transcript"]
            expected_domain = clip["expected_domain"]
            expected_outcome = clip["expected_outcome"]

            outcome = run_intake(transcript)
            actual_domain = outcome.domain.value if outcome.domain else None
            actual_outcome = outcome.status.value
            confidence = outcome.classification.confidence

            if expected_outcome == "routed":
                is_correct = (actual_outcome == "routed" and actual_domain == expected_domain)
            elif expected_outcome == "needs_clarification":
                is_correct = (actual_outcome == "needs_clarification")
            else:
                is_correct = False

            decisions.append({
                "clip_id": clip["clip_id"],
                "confidence": float(confidence),
                "correct": is_correct,
                "expected_domain": expected_domain,
                "actual_domain": actual_domain,
                "expected_outcome": expected_outcome,
                "actual_outcome": actual_outcome,
            })

    binned = compute_calibration_bins(decisions, num_bins=num_bins)

    if binned["status"] == "ok":
        ece = binned["ece"]
        interpretation = (
            f"Expected Calibration Error (ECE) is {ece:.1%}. "
            "Plain-language audit: when the gate reports a given confidence score, "
            "its actual probability of making the correct routing/abstaining decision "
            f"diverges by an average of {ece:.1%}. "
            "A well-calibrated gate enables reliable thresholding (τ) for safety-critical civic routing."
        )
        ascii_diagram = generate_ascii_reliability_diagram(binned["bins"])
    else:
        interpretation = "Insufficient decision data to compute calibration."
        ascii_diagram = "No diagram available."

    plot_saved = False
    if plot_path and binned["status"] == "ok":
        plot_saved = plot_reliability_diagram_png(binned, plot_path)

    mock_caveat = (
        "NOTE: This calibration run is on the MOCK classifier's heuristic confidence scores, "
        "not a real probabilistic model — this number should be RE-RUN once Sahara/LLM-driven "
        "classification replaces the mock, and is not itself evidence of a calibration problem "
        "in the final system, only a baseline to compare against once real numbers exist."
    )

    result = {
        "status": binned["status"],
        "data_source": data_source_label,
        "total_decisions": len(decisions),
        "ece": binned.get("ece"),
        "interpretation": interpretation,
        "bins": binned.get("bins", []),
        "ascii_diagram": ascii_diagram,
        "plot_saved": plot_saved,
        "plot_path": str(plot_path) if plot_saved else None,
        "note": mock_caveat,
    }
    return result


if __name__ == "__main__":
    default_plot = _REPO_ROOT / "bench" / "results" / "calibration_reliability_diagram.png"
    res = run_calibration_analysis(plot_path=default_plot)

    print("\n=== Confidence Calibration Analysis ===")
    print(f"Data Source:      {res['data_source']}")
    print(f"Total Decisions:  {res['total_decisions']}")
    print(f"ECE Score:        {res['ece'] if res['ece'] is not None else 'N/A'}")
    print(f"\nInterpretation:\n  {res['interpretation']}\n")
    print(f"Caveat / Notice:\n  {res['note']}\n")
    print(res["ascii_diagram"])
    if res["plot_saved"]:
        print(f"\n✓ Reliability diagram saved to: {res['plot_path']}")
