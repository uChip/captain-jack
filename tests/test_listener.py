"""Re-runnable test for docs/tests.md: "Listener VAD + STT".

Automatic, no hardware: feeds a real recording from the XVF3800's
capture channel 1 (tests/data/quick_brown_fox_ch1.wav - Chip saying "The
quick brown fox jumps over the lazy dog", with background noise at the
start) through the Listener frame by frame, exactly as Capture would,
followed by 1.5s of silence. Checks:
  - exactly one utterance comes out, covering the speech;
  - silence alone produces no utterance;
  - ignore_until() suppresses an utterance captured during "playback",
    and going deaf (inf) then reopening the gate before the speech starts
    lets it through again;
  - STT transcribes the utterance, recognizing "jumps over the lazy dog"
    (the start of the recording is too noisy to require "quick brown").
  - STT rejects non-speech noise - real room noise from the same
    recording, and white noise - rather than sending it on. (Pure
    digital silence isn't tested: the live mic never produces it, and
    tiny.en hallucinates "you" on it - see docs/log.md, 4.16.)

Run: venv/bin/python tests/test_listener.py
"""

import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from capture import FRAME  # noqa: E402
from listener import Listener  # noqa: E402
from stt import RATE, STT  # noqa: E402

CLIP = Path(__file__).parent / "data" / "quick_brown_fox_ch1.wav"


def feed(listener, samples):
    """Drive the listener as Capture would: 80ms frames with timestamps."""
    n = len(samples) // FRAME * FRAME
    for i in range(0, n, FRAME):
        listener.process(samples[i:i + FRAME], i / RATE)


def run(samples, ignore_until=None):
    got = []
    listener = Listener(on_utterance=lambda s, t: got.append((s, t)))
    if ignore_until is not None:
        listener.ignore_until(ignore_until)
    feed(listener, samples)
    return got


def main():
    errors = []
    with wave.open(str(CLIP)) as w:
        speech = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    silence = np.zeros(int(1.5 * RATE), dtype=np.int16)
    clip = np.concatenate([speech, silence])

    got = run(clip)
    if len(got) != 1:
        errors.append(f"expected 1 utterance from the clip, got {len(got)}")
    else:
        utt, start_t = got[0]
        dur = len(utt) / RATE
        print(f"  utterance: starts {start_t:.2f}s, {dur:.2f}s long")
        if not 0.2 <= start_t <= 0.7:
            errors.append(f"utterance starts at {start_t:.2f}s; speech begins ~0.6s")
        if not 3.5 <= dur <= 5.5:
            errors.append(f"utterance is {dur:.2f}s; speech lasts ~3.8s")

    if run(np.zeros(3 * RATE, dtype=np.int16)):
        errors.append("silence produced an utterance")
    if run(clip, ignore_until=len(clip) / RATE):
        errors.append("ignore_until() didn't suppress the utterance")

    reopened = []
    listener = Listener(on_utterance=lambda s, t: reopened.append(s))
    listener.ignore_until(float("inf"))             # playback started: deaf
    feed(listener, np.zeros(RATE, dtype=np.int16))  # 1s of "playback"
    listener.ignore_until(0.3)                      # finished; hold-off ends before speech
    for i in range(0, len(clip) // FRAME * FRAME, FRAME):
        listener.process(clip[i:i + FRAME], 1.0 + i / RATE)
    if len(reopened) != 1:
        errors.append(f"after reopening the gate, expected 1 utterance, got {len(reopened)}")

    stt = STT()
    if got:
        t = stt.transcribe(got[0][0])
        print(f"  transcript [{stt.model_name}, {t.stt_s:.2f}s]: {t.text!r}")
        if not t.accepted or "lazy dog" not in t.text.lower() or "jumps over" not in t.text.lower():
            errors.append(f"transcript doesn't contain 'jumps over the lazy dog': {t.raw!r}")
    room = np.tile(speech[:int(0.55 * RATE)], 4)     # room noise before Chip spoke
    white = (np.random.default_rng(0).standard_normal(2 * RATE) * 327).astype(np.int16)
    for name, noise in (("room noise", room), ("white noise", white)):
        t = stt.transcribe(noise)
        if t.accepted:
            errors.append(f"STT accepted {name} as {t.text!r}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: listener segments one utterance, ignores silence and gated input; STT transcribes speech and rejects noise")


if __name__ == "__main__":
    main()
