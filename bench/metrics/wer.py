"""Word Error Rate — normalized + raw.

Pure-Python implementation, zero external dependencies.
Works on code-switched Nigerian Pidgin / Yoruba / English text.

Functions
---------
normalize(text)
    Lowercase, strip punctuation, collapse whitespace.
    Handles common Naija contractions and ASR artifacts.

wer(hypothesis, reference)
    Compute WER for a single utterance.
    Returns a dict: {wer, insertions, deletions, substitutions, word_count}.

corpus_wer(clips)
    Aggregate WER across a list of {hypothesis, reference} dicts.
    Weights by reference word count (standard corpus-level WER).

Usage (local — text only, no audio):
    PYTHONPATH=. python3 -m bench.metrics.wer

Usage (after Colab corpus run writes transcripts):
    from bench.metrics.wer import corpus_wer
    results = corpus_wer(clips)
"""
from __future__ import annotations

import re
import string

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

# ASR artifacts and Naija contractions to expand before scoring.
# Keep this conservative — only expand forms that are unambiguously equivalent.
_EXPANSIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bdon\b"), "done"),       # Naija perfective marker
    (re.compile(r"\bdey\b"), "is"),         # Naija copula
    (re.compile(r"\bwan\b"), "want"),
    (re.compile(r"\bdem\b"), "them"),
    (re.compile(r"\bwetin\b"), "what"),
    (re.compile(r"\bna\b"), "is"),
    (re.compile(r"\bno\b"), "not"),         # negation context — approximate
    (re.compile(r"\be\b"), "it"),           # 3rd person singular
    (re.compile(r"\bam\b"), "him"),         # Pidgin object pronoun
    (re.compile(r"\buna\b"), "you all"),
    (re.compile(r"\babeg\b"), "please"),
    (re.compile(r"\bnepa\b"), "electricity"),  # common ASR variant
]


def normalize(text: str, *, expand_contractions: bool = True) -> str:
    """Normalize a transcript for WER scoring.

    Steps:
    1. Lowercase
    2. Optionally expand common Naija contractions
    3. Strip punctuation (keep apostrophes inside words)
    4. Collapse whitespace

    Args:
        text: Raw transcript string.
        expand_contractions: If True, apply the Naija contraction expansion
            table. Set False when comparing two ASR outputs directly (so
            neither gets an unfair boost from normalization).
    """
    text = text.lower().strip()

    if expand_contractions:
        for pattern, replacement in _EXPANSIONS:
            text = pattern.sub(replacement, text)

    # Remove punctuation except apostrophes inside words (e.g. "can't")
    text = re.sub(r"[^\w\s']", " ", text)
    # Remove standalone apostrophes
    text = re.sub(r"(?<!\w)'|'(?!\w)", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ---------------------------------------------------------------------------
# Levenshtein edit distance on word sequences
# ---------------------------------------------------------------------------

def _edit_distance(
    hyp: list[str], ref: list[str]
) -> tuple[int, int, int]:
    """Return (insertions, deletions, substitutions) via standard DP.

    Uses O(min(len(hyp), len(ref))) space via two-row DP.
    Also returns the full edit matrix for back-tracking (we need the counts,
    not just the total distance).
    """
    n, m = len(ref), len(hyp)

    # dp[i][j] = (distance, insertions, deletions, substitutions)
    # Build full matrix for count decomposition.
    dp: list[list[tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0)] * (m + 1) for _ in range(n + 1)
    ]

    for i in range(n + 1):
        dp[i][0] = (i, 0, i, 0)  # i deletions
    for j in range(m + 1):
        dp[0][j] = (j, j, 0, 0)  # j insertions

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                del_cost = dp[i - 1][j]
                ins_cost = dp[i][j - 1]
                sub_cost = dp[i - 1][j - 1]

                best = min(del_cost, ins_cost, sub_cost, key=lambda x: x[0])

                if best is del_cost:
                    d, ins, dels, subs = del_cost
                    dp[i][j] = (d + 1, ins, dels + 1, subs)
                elif best is ins_cost:
                    d, ins, dels, subs = ins_cost
                    dp[i][j] = (d + 1, ins + 1, dels, subs)
                else:
                    d, ins, dels, subs = sub_cost
                    dp[i][j] = (d + 1, ins, dels, subs + 1)

    _, ins, dels, subs = dp[n][m]
    return ins, dels, subs


# ---------------------------------------------------------------------------
# Single-utterance WER
# ---------------------------------------------------------------------------

def wer(
    hypothesis: str,
    reference: str,
    *,
    normalize_text: bool = True,
    expand_contractions: bool = True,
) -> dict:
    """Compute WER for a single utterance.

    Args:
        hypothesis: ASR-produced transcript.
        reference:  Ground-truth transcript.
        normalize_text: Apply normalize() before scoring.
        expand_contractions: Passed to normalize(). Ignored if normalize_text=False.

    Returns:
        {
            "wer": float,           # 0.0 – ∞ (> 1.0 means more errors than words)
            "insertions": int,
            "deletions": int,
            "substitutions": int,
            "edit_distance": int,
            "word_count": int,      # reference word count
            "hyp_normalized": str,
            "ref_normalized": str,
        }

    Examples:
        >>> wer("the cat sat", "the cat sat")["wer"]
        0.0
        >>> wer("cat sat", "the cat sat")["wer"]  # 1 deletion
        0.3333...
        >>> wer("a b c", "x y z")["wer"]  # 3 substitutions
        1.0
    """
    if normalize_text:
        hyp_norm = normalize(hypothesis, expand_contractions=expand_contractions)
        ref_norm = normalize(reference, expand_contractions=expand_contractions)
    else:
        hyp_norm = hypothesis.strip()
        ref_norm = reference.strip()

    hyp_words = hyp_norm.split() if hyp_norm else []
    ref_words = ref_norm.split() if ref_norm else []

    word_count = len(ref_words)

    if word_count == 0:
        # Empty reference — WER is 0 if hyp is also empty, else undefined (return 0).
        return {
            "wer": 0.0,
            "insertions": len(hyp_words),
            "deletions": 0,
            "substitutions": 0,
            "edit_distance": len(hyp_words),
            "word_count": 0,
            "hyp_normalized": hyp_norm,
            "ref_normalized": ref_norm,
        }

    ins, dels, subs = _edit_distance(hyp_words, ref_words)
    edit_dist = ins + dels + subs
    wer_score = edit_dist / word_count

    return {
        "wer": round(wer_score, 6),
        "insertions": ins,
        "deletions": dels,
        "substitutions": subs,
        "edit_distance": edit_dist,
        "word_count": word_count,
        "hyp_normalized": hyp_norm,
        "ref_normalized": ref_norm,
    }


# ---------------------------------------------------------------------------
# Corpus-level WER
# ---------------------------------------------------------------------------

def corpus_wer(
    clips: list[dict],
    *,
    normalize_text: bool = True,
    expand_contractions: bool = True,
) -> dict:
    """Aggregate WER across a corpus of clips.

    Standard corpus-level WER: sum of edit distances / sum of reference words.
    This weights long utterances more heavily than a simple mean of per-clip WERs.

    Args:
        clips: List of dicts, each with keys:
            - "clip_id": str
            - "hypothesis": str  (ASR transcript)
            - "reference":  str  (ground-truth transcript)
        normalize_text: Apply normalize() before scoring (default True).
        expand_contractions: Passed to normalize(). Ignored if normalize_text=False.

    Returns:
        {
            "corpus_wer": float,
            "total_edit_distance": int,
            "total_word_count": int,
            "total_insertions": int,
            "total_deletions": int,
            "total_substitutions": int,
            "num_clips": int,
            "per_clip": [ {clip_id, wer, ...}, ... ]
        }
    """
    per_clip = []
    total_edit = total_words = total_ins = total_dels = total_subs = 0

    for clip in clips:
        result = wer(
            clip["hypothesis"],
            clip["reference"],
            normalize_text=normalize_text,
            expand_contractions=expand_contractions,
        )
        result["clip_id"] = clip.get("clip_id", "unknown")
        per_clip.append(result)

        total_edit += result["edit_distance"]
        total_words += result["word_count"]
        total_ins += result["insertions"]
        total_dels += result["deletions"]
        total_subs += result["substitutions"]

    corpus_score = (total_edit / total_words) if total_words > 0 else 0.0

    return {
        "corpus_wer": round(corpus_score, 6),
        "total_edit_distance": total_edit,
        "total_word_count": total_words,
        "total_insertions": total_ins,
        "total_deletions": total_dels,
        "total_substitutions": total_subs,
        "num_clips": len(clips),
        "per_clip": per_clip,
    }


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _examples = [
        ("the cat sat on the mat", "the cat sat on the mat"),
        ("cat sat on mat", "the cat sat on the mat"),
        ("there is a big pothole for allen avenue junction", "there is a big pothole for allen avenue junction"),
        ("e don burst for street since morning everywhere don flood",
         "water don burst for our street since morning everywhere don flood"),
        ("my landlord wan evict me and refuse return my rent deposit",
         "my landlord wan evict me and refuse to return my rent deposit"),
    ]

    print("=== WER Smoke Test ===\n")
    for hyp, ref in _examples:
        r = wer(hyp, ref)
        print(f"  REF: {ref}")
        print(f"  HYP: {hyp}")
        print(f"  WER: {r['wer']:.1%}  (ins={r['insertions']} del={r['deletions']} sub={r['substitutions']})")
        print()
