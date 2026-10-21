"""Automatic test for docs/tests.md: "DoA per-utterance direction".

No hardware: feeds doa.py's DoaTracker fake readings with a fake clock
and checks the direction it reports for "the utterance that just
ended" - converted from board degrees to Jack's own angle (front = board
JACK_FRONT_DEG, + = his right): the value the board held longest while
the person spoke. Includes the two patterns seen live in session23
(2026-10-21): the window opening still stuck on Jack's own voice, and a
swing after the talker stops. None when there are too few readings, no
direction dominates, or the board never moved off what it held before.

Run: venv/bin/python tests/test_doa.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import doa  # noqa: E402

F = doa.JACK_FRONT_DEG


def tracker():
    clock = [1000.0]
    t = doa.DoaTracker(read=lambda: (0, False), now=lambda: clock[0])

    def feed(jack_deg, seconds, speech=True):
        for _ in range(int(seconds * doa.POLL_HZ)):
            clock[0] += 1 / doa.POLL_HZ
            t.add((F + jack_deg) % 360, speech)
    return t, feed


def main():
    errors = []
    if doa.to_jack(F) != 0 or doa.to_jack(F + 90) != 90 or doa.to_jack(F - 90) != -90:
        errors.append("to_jack() doesn't map front/right/left to 0/+90/-90")
    if doa.to_jack((F + 180) % 360) not in (180, -180):
        errors.append("to_jack() doesn't map behind to 180")

    t, feed = tracker()
    feed(90, 3.0)
    if t.direction(3.0) != 90:
        errors.append(f"steady reading on the right should give 90, got {t.direction(3.0)}")

    t, feed = tracker()
    feed(40, 5.0)       # Jack's own reply...
    feed(40, 1.2)       # ...still held as the person starts (4s utterance)
    feed(-93, 2.0)      # the person, on his left
    feed(127, 0.4)      # a swing once they've stopped
    feed(68, 0.4)
    if t.direction(4.0) != -93:
        errors.append(f"should pick the value held longest while they spoke (-93), got {t.direction(4.0)}")

    t, feed = tracker()
    feed(-90, 10.0)     # an earlier talker - before this utterance began
    feed(45, 3.0)
    if t.direction(3.0) != 45:
        errors.append(f"readings from before the utterance should be ignored, got {t.direction(3.0)}")

    t, feed = tracker()
    feed(40, 5.0)       # Jack's own reply, and the board never moves off it
    feed(40, 3.0)
    if t.direction(3.0) is not None:
        errors.append("a direction unchanged from before the utterance should give None")

    t, feed = tracker()
    feed(3, 0.4)
    feed(3, 2.0, speech=False)
    if t.direction(2.4) is not None:
        errors.append("too few speech-flagged readings should give None")

    t, feed = tracker()
    for a in (-150, -90, -30, 30, 90, 150):   # all over the place - nothing dominates
        feed(a, 0.5)
    if t.direction(3.0) is not None:
        errors.append(f"scattered readings should give None, got {t.direction(3.0)}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: board-to-Jack angle mapping; the direction held longest while the person spoke, "
          "ignoring Jack's own voice at the start, a swing at the end and earlier talkers; "
          "too few / scattered readings, or no change from before, give None")


if __name__ == "__main__":
    main()
