"""Inter-annotator agreement — Cohen's Kappa + disagreement log.

Used to validate the dual-labeler ground truth for the Tier A corpus.
Two independent native speakers label each clip on two distinct tasks:
  1. Transcription (transcript_heard) — feeds WER reference text.
  2. Domain Classification (domain_judgment) — independent judgment on
     whether the clip is "infrastructure", "legal", or "ambiguous".

Disagreements on domain_judgment reveal genuinely hard/borderline cases and
populate ambiguous_subset.json — the primary test set for validating that
the abstain gate fires on ambiguous civic reports (per IMPL_PLAN §4.1).

Clip Schema for Labelers:
    {
      "clip_id": "synth_011",
      "transcript_heard": "the council come demolish my shop without any notice or paper",
      "domain_judgment": "ambiguous",
      "entities_heard": {"party": null, "location": null},
      "labeler_confidence": "medium",
      "notes": "could be local gov demolition (infra) or unlawful seizure (legal)"
    }

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

Domain Judgment Vocabulary:
    "infrastructure" | "legal" | "ambiguous"

Usage:
    PYTHONPATH=. python3 -m bench.metrics.inter_annotator_agreement \\
        bench/corpus/tier_a_recorded/ground_truth_labeler1.json \\
        bench/corpus/tier_a_recorded/ground_truth_labeler2.json \\
        --write-ambiguous bench/corpus/tier_a_recorded/ambiguous_subset.json
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


def _get_domain(clip: dict) -> str:
    """Extract domain judgment supporting both new schema and legacy keys."""
    return clip.get("domain_judgment") or clip.get("expected_domain") or "ambiguous"


def _get_transcript(clip: dict) -> str:
    """Extract transcript heard supporting both new schema and legacy keys."""
    return clip.get("transcript_heard") or clip.get("transcript") or ""


def agreement_report(
    labeler1_path: Path | str,
    labeler2_path: Path | str,
) -> dict:
    """Full inter-annotator agreement report.

    Each labeler file is a JSON array of clip dicts with:
        {
            "clip_id": "...",
            "transcript_heard": "...",
            "domain_judgment": "infrastructure" | "legal" | "ambiguous",
            "entities_heard": {...},
            "labeler_confidence": "high" | "medium" | "low"
        }

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

    labels_a = [_get_domain(clips1[cid]) for cid in common_ids]
    labels_b = [_get_domain(clips2[cid]) for cid in common_ids]

    kappa_result = cohen_kappa(labels_a, labels_b)

    per_clip = []
    disagreements = []
    for cid in common_ids:
        c1, c2 = clips1[cid], clips2[cid]
        label_a = _get_domain(c1)
        label_b = _get_domain(c2)
        agree = label_a == label_b

        transcript_a = _get_transcript(c1)
        transcript_b = _get_transcript(c2)

        row = {
            "clip_id": cid,
            "label_a": label_a,
            "label_b": label_b,
            "agree": agree,
            "transcript_a": transcript_a,
            "transcript_b": transcript_b,
            "confidence_a": c1.get("labeler_confidence", ""),
            "confidence_b": c2.get("labeler_confidence", ""),
            "entities_a": c1.get("entities_heard") or c1.get("expected_entities", {}),
            "entities_b": c2.get("entities_heard") or c2.get("expected_entities", {}),
            "notes_a": c1.get("notes", ""),
            "notes_b": c2.get("notes", ""),
        }
        per_clip.append(row)
        if not agree or label_a == "ambiguous" or label_b == "ambiguous":
            disagreements.append(row)

    return {
        "kappa": kappa_result,
        "per_clip": per_clip,
        "disagreements": disagreements,
        "agreement_count": kappa_result["n"] - sum(1 for r in per_clip if not r["agree"]),
        "disagreement_count": sum(1 for r in per_clip if not r["agree"]),
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
    """Write disagreement/ambiguous cases to ambiguous_subset.json.

    These clips become the primary abstain-gate test set: the gate should fire
    on all of them (since native labelers disagreed on the domain or marked ambiguous).

    Output format matches ground_truth.json:
        [{"clip_id": ..., "transcript": ..., "expected_domain": "ambiguous",
          "expected_outcome": "needs_clarification", "notes": ...}]
    """
    subset = [
        {
            "clip_id": d["clip_id"],
            "transcript": d["transcript_a"] or d["transcript_b"],
            "expected_domain": "ambiguous",
            "expected_outcome": "needs_clarification",
            "labeler1_domain": d["label_a"],
            "labeler2_domain": d["label_b"],
            "labeler1_confidence": d.get("confidence_a", ""),
            "labeler2_confidence": d.get("confidence_b", ""),
            "notes": (
                f"Labeler disagreement/ambiguity: A={d['label_a']} (conf={d.get('confidence_a', 'N/A')}), "
                f"B={d['label_b']} (conf={d.get('confidence_b', 'N/A')}). "
                f"{d['notes_a']} {d['notes_b']}".strip()
            ),
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
