"""Re-runnable test for docs/tests.md: "STT rejection rules".

Automatic, no hardware, no model: checks stt.rejection_reason() against
real transcripts from the 2026-09-25 live runs - Chip's clear speech must
pass; Whisper's retry loop and its echoed guesses at gibberish must be
rejected. (The confidence values are the ones Whisper actually reported.)

Run: venv/bin/python tests/test_stt.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from stt import rejection_reason  # noqa: E402

NAN = float("nan")

ACCEPT = [   # (transcript, whisper's average token probability)
    ("Turn off the living room lights.", 0.66),
    ("Kath's birthday was this week.", 0.77),
    ("Hi, Captain Jack. My you sure are pretty bird.", 0.63),
    ("This is Chip, Jack, check the buildges.", 0.71),
    ("just having a nice conversation Jack.", 0.65),
    ("4 score and 7 years ago, our forefathers brought forth on this continent, a new nation.", 0.73),
    ("No, no, no, not that one.", 0.60),        # short repeats are fine
    ("Yo ho, yo ho, a pirate's life for me.", 0.60),
    ("Captain Jack, what's the weather like?", NAN),  # no probability: no verdict on it
]
REJECT = [
    ("what is the anchor? Where is the anchor? Where is the anchor? Where is the anchor? "
     "Where is the anchor? where does it", 0.60, "repetition"),        # retry loop on "Raise the anchor"
    ("Can I get moved to goodbye. Can I get moved to goodbye", 0.55, "repetition"),  # gibberish
    ("Are you a wick, Jack? Are you a wick,", 0.69, "repetition"),    # gibberish
    ("P", 0.02, "low confidence"),                                     # gibberish
    ("", 0.50, "no words"),
    ("...", 0.50, "no words"),
]


def main():
    errors = []
    for text, prob in ACCEPT:
        reason = rejection_reason(text, prob)
        if reason:
            errors.append(f"real speech rejected ({reason}): {text!r}")
    for text, prob, want in REJECT:
        reason = rejection_reason(text, prob)
        if not reason.startswith(want):
            errors.append(f"expected {want!r}, got {reason or 'accepted'!r}: {text!r}")
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print(f"PASS: {len(ACCEPT)} real transcripts accepted, {len(REJECT)} loops/gibberish rejected")


if __name__ == "__main__":
    main()
