"""Inter-annotator agreement — Cohen's Kappa + disagreement log.

Used to validate the dual-labeler ground truth for the Tier A corpus.
Two independent native speakers label each clip; this script computes how
much they agree and flags every disagreement for reconciliation.

Disagreement cases become ambiguous_subset.json — the primary test set for
validating the abstain gate actually fires where it should (per IMPL_PLAN §4.1).

Functions
---------
cohen_kappa(labels_a, labels_b)
    Cohen's κ for two annotators on the same items.
    κ = 1.0 → perfect agreement, 0.0 → chance, < 0 → worse than chance.

agreement_report(labeler1_path, labeler2_path)
    Full report: κ, % agreement, per-clip disagreement table.

write_ambiguous_subset(disagreements, output_path)
    Write disagreement cases to ambiguous_subset.json for use as the
    abstain-gate test set.

Label vocabulary (must match ground_truth.json expected_domain values):
    "infrastructure" | "legal" | "ambiguous"

Usage:
    PYTHONPATH=. python3 -m bench.metrics.inter_annotator_agreement \\
        bench/corpus/tier_a_recorded/ground_truth_labeler1.json \\
        bench/corpus/tier_a_recorded/ground_truth_labeler2.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Cohen's Kappa
# ---------------------------------------------------------------------------

_VALID_LABELS = {"infrastructure", "legal", "ambiguous"}


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> dict:
    """Compute Cohen's Kappa for two annotators.

    Args:
        labels_a: List of labels from annotator A (e.g. labeler 1).
        labels_b: List of labels from annotator B (e.g. labeler 2). Same length.

    Returns:
        {
            "kappa": float,               # Cohen's κ ∈ [-1, 1]
            "observed_agreement": float,  # P(agree)
            "expected_agreement": float,  # P(agree by chance)
            "n": int,                     # number of items
            "interpretation": str,        # Landis & Koch scale
        }

    Raises:
        ValueError: If lists have different lengths or are empty.
    """
    if len(labels_a) != len(labels_b):
        raise ValueError(
            f"Annotator lists must have the same length: "
            f"{len(labels_a)} vs {len(labels_b)}"
        )
    if not labels_a:
        raise ValueError("Cannot compute kappa on empty lists.")

    n = len(labels_a)
    categories = sorted(_VALID_LABELS | set(labels_a) | set(labels_b))

    # Observed agreement P_o
    matches = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    p_o = matches / n

    # Expected agreement P_e = sum over categories of P(A picks cat) * P(B picks cat)
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    p_e = sum(
        (counts_a.get(cat, 0) / n) * (counts_b.get(cat, 0) / n)
        for cat in categories
    )

    if p_e == 1.0:
        # Degenerate case: both annotators always pick the same single label
        kappa = 1.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    return {
        "kappa": round(kappa, 4),
        "observed_agreement": round(p_o, 4),
        "expected_agreement": round(p_e, 4),
        "n": n,
        "interpretation": _interpret_kappa(kappa),
    }


def _interpret_kappa(kappa: float) -> str:
    """Landis & Koch (1977) interpretation scale."""
    if kappa < 0:
        return "poor (worse than chance)"
    elif kappa < 0.20:
        return "slight"
    elif kappa < 0.40:
        return "fair"
    elif kappa < 0.60:
        return "moderate"
    elif kappa < 0.80:
        return "substantial"
    else:
        return "almost perfect"


# ---------------------------------------------------------------------------
# Corpus-level report
# ---------------------------------------------------------------------------

def _load_labels(path: Path | str) -> list[dict]:
    """Load a ground-truth JSON file (array of clip dicts)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def agreement_report(
    labeler1_path: Path | str,
    labeler2_path: Path | str,
) -> dict:
    """Full inter-annotator agreement report.

    Each labeler file must be a JSON array of clip dicts with at least:
        {"clip_id": "...", "expected_domain": "infrastructure"|"legal"|"ambiguous"}

    Returns:
        {
            "kappa": dict,              # from cohen_kappa()
            "per_clip": list[dict],     # per-clip comparison
            "disagreements": list[dict],# clips where labelers differ
            "agreement_count": int,
            "disagreement_count": int,
        }
    """
    clips1 = {c["clip_id"]: c for c in _load_labels(labeler1_path)}
    clips2 = {c["clip_id"]: c for c in _load_labels(labeler2_path)}

    # Only score clips present in both labelers
    common_ids = sorted(set(clips1) & set(clips2))
    only_in_1 = sorted(set(clips1) - set(clips2))
    only_in_2 = sorted(set(clips2) - set(clips1))

    labels_a = [clips1[cid]["expected_domain"] for cid in common_ids]
    labels_b = [clips2[cid]["expected_domain"] for cid in common_ids]

    kappa_result = cohen_kappa(labels_a, labels_b)

    per_clip = []
    disagreements = []
    for cid in common_ids:
        c1, c2 = clips1[cid], clips2[cid]
        label_a = c1["expected_domain"]
        label_b = c2["expected_domain"]
        agree = label_a == label_b

        row = {
            "clip_id": cid,
            "label_a": label_a,
            "label_b": label_b,
            "agree": agree,
            "transcript": c1.get("transcript", c2.get("transcript", "")),
            "notes_a": c1.get("notes", ""),
            "notes_b": c2.get("notes", ""),
        }
        per_clip.append(row)
        if not agree:
            disagreements.append(row)

    return {
        "kappa": kappa_result,
        "per_clip": per_clip,
        "disagreements": disagreements,
        "agreement_count": kappa_result["n"] - len(disagreements),
        "disagreement_count": len(disagreements),
        "clips_only_in_labeler1": only_in_1,
        "clips_only_in_labeler2": only_in_2,
    }


# ---------------------------------------------------------------------------
# Write ambiguous subset
# ---------------------------------------------------------------------------

def write_ambiguous_subset(
    disagreements: list[dict],
    output_path: Path | str,
) -> None:
    """Write disagreement cases to ambiguous_subset.json.

    These clips become the primary abstain-gate test set: the gate should fire
    on all of them (since even expert labelers disagreed on the domain).

    Output format matches ground_truth.json:
        [{"clip_id": ..., "transcript": ..., "expected_domain": "ambiguous",
          "expected_outcome": "needs_clarification", "notes": ...}]
    """
    subset = [
        {
            "clip_id": d["clip_id"],
            "transcript": d["transcript"],
            "expected_domain": "ambiguous",
            "expected_outcome": "needs_clarification",
            "labeler1_domain": d["label_a"],
            "labeler2_domain": d["label_b"],
            "notes": f"Labeler disagreement: A={d['label_a']}, B={d['label_b']}. {d['notes_a']}",
        }
        for d in disagreements
    ]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(subset, f, indent=2, ensure_ascii=False)
    print(f"Ambiguous subset written: {path} ({len(subset)} clips)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python3 -m bench.metrics.inter_annotator_agreement "
            "<labeler1.json> <labeler2.json> [--write-ambiguous <output.json>]"
        )
        sys.exit(1)

    path1, path2 = Path(sys.argv[1]), Path(sys.argv[2])
    write_ambiguous = "--write-ambiguous" in sys.argv
    ambiguous_out = None
    if write_ambiguous:
        idx = sys.argv.index("--write-ambiguous")
        ambiguous_out = Path(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else Path(
            path1.parent / "ambiguous_subset.json"
        )

    report = agreement_report(path1, path2)

    k = report["kappa"]
    print("\n=== Inter-Annotator Agreement ===")
    print(f"  N (common clips):      {k['n']}")
    print(f"  Observed agreement:    {k['observed_agreement']:.1%}")
    print(f"  Expected agreement:    {k['expected_agreement']:.1%}")
    print(f"  Cohen's κ:             {k['kappa']:.3f}  ({k['interpretation']})")
    print(f"  Agreements:            {report['agreement_count']}")
    print(f"  Disagreements:         {report['disagreement_count']}")

    if report["clips_only_in_labeler1"]:
        print(f"\n  ⚠ Clips only in labeler 1: {report['clips_only_in_labeler1']}")
    if report["clips_only_in_labeler2"]:
        print(f"  ⚠ Clips only in labeler 2: {report['clips_only_in_labeler2']}")

    if report["disagreements"]:
        print("\n--- Disagreements ---")
        for d in report["disagreements"]:
            print(f"  {d['clip_id']}: A={d['label_a']}  B={d['label_b']}")
            print(f"    \"{d['transcript'][:80]}\"")

    if write_ambiguous and ambiguous_out:
        write_ambiguous_subset(report["disagreements"], ambiguous_out)
