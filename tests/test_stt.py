"""Re-runnable test for docs/tests.md: "STT rejection rules".

Automatic, no hardware: checks stt.rejection_reason() against real
transcripts from the 2026-09-25 live runs - Chip's clear speech must
pass; Whisper's retry loop and its echoed guesses at gibberish must be
rejected. (The confidence values are the ones Whisper actually reported.)
Also loads the real tiny.en model to confirm a regression found live
2026-10-12: STT must build a fresh whisper.cpp Model per transcribe()
call, not reuse one for the process's whole life - a reused Model's
decode drifted (sometimes wrongly) depending on what it had already
transcribed. See docs/log.md, 4.2.

Run: venv/bin/python tests/test_stt.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import stt as sttmod  # noqa: E402
from stt import STT, rejection_reason  # noqa: E402

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
    # 2026-10-12, real session: a long, legitimate utterance that happens to
    # reuse a short phrase ("the United States") once, far apart - the old
    # any-distance repetition check false-rejected this.
    ("We, the people of the United States, in order to form a more perfect union, establish "
     "justice, ensure domestic tranquility, and provide for the common defense, promote the "
     "general welfare, and secure the blessings of liberty to ourselves and our posterity, do "
     "ordain and establish this constitution for the United States.", 0.74),
]
REJECT = [
    ("what is the anchor? Where is the anchor? Where is the anchor? Where is the anchor? "
     "Where is the anchor? where does it", 0.60, "repetition"),        # retry loop on "Raise the anchor"
    ("Can I get moved to goodbye. Can I get moved to goodbye", 0.55, "repetition"),  # gibberish
    ("Are you a wick, Jack? Are you a wick,", 0.69, "repetition"),    # gibberish
    ("P", 0.02, "low confidence"),                                     # gibberish
    ("", 0.50, "no words"),
    ("...", 0.50, "no words"),
    # 2026-10-12, real session: Chip repeating himself back-to-back in one
    # utterance - adjacent, so still correctly a "repetition" reject.
    ("That's all for now, Jack. That's all for now, Jack.", 0.72, "repetition"),
]


def check_rejection_reason():
    errors = []
    for text, prob in ACCEPT:
        reason = rejection_reason(text, prob)
        if reason:
            errors.append(f"real speech rejected ({reason}): {text!r}")
    for text, prob, want in REJECT:
        reason = rejection_reason(text, prob)
        if not reason.startswith(want):
            errors.append(f"expected {want!r}, got {reason or 'accepted'!r}: {text!r}")
    return errors


def check_fresh_model_per_transcribe():
    """A reused Model must not be shared across transcribe() calls (see
    module docstring) - count real Model() constructions against the
    number of transcribe() calls made through one STT instance."""
    made = []
    real_model = sttmod.Model

    class CountingModel(real_model):
        def __init__(self, *a, **k):
            made.append(1)
            super().__init__(*a, **k)

    sttmod.Model = CountingModel
    try:
        s = STT("tiny.en")
        silence = np.zeros(16000, dtype=np.int16)
        s.transcribe(silence)
        s.transcribe(silence)
        s.transcribe(silence)
    finally:
        sttmod.Model = real_model
    if len(made) != 3:
        return [f"expected a fresh Model for each of 3 transcribe() calls, got {len(made)}"]
    return []


def main():
    errors = check_rejection_reason() + check_fresh_model_per_transcribe()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print(f"PASS: {len(ACCEPT)} real transcripts accepted, {len(REJECT)} loops/gibberish rejected, "
          f"and STT builds a fresh Model per transcribe() call")


if __name__ == "__main__":
    main()
