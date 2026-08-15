"""Runnable demo of the abstain gate — no server, no API keys.

    PYTHONPATH=backend python3 backend/demo_gate.py

Feeds a handful of code-switched complaints through the pipeline and prints,
for each, whether it was routed (and where) or held for clarification (and what
question we'd ask back), plus the reasons behind the decision.
"""
from app.pipeline import run_intake

EXAMPLES = [
    "There is a big pothole for Allen Avenue junction, e don spoil plenty tyre.",  # clear infra
    "My landlord wan evict me and refuse to return my rent deposit.",             # clear legal
    "Water don burst for our street since morning.",                              # infra via place-word
    "My landlord refused to fix the burst pipe in the flat.",                     # ambiguous -> abstain
    "Abeg I get one small problem, make una help me.",                            # no signal -> abstain
]


def main() -> None:
    for text in EXAMPLES:
        out = run_intake(text)
        print("=" * 76)
        print(f"INPUT:  {text}")
        line = f"STATUS: {out.status.value}"
        if out.domain:
            line += f"  ->  {out.domain.value}"
        print(line)
        if out.clarifying_question:
            print(f"ASK:    {out.clarifying_question}")
        print("WHY:")
        for reason in out.reasons:
            print(f"   - {reason}")
    print("=" * 76)


if __name__ == "__main__":
    main()
