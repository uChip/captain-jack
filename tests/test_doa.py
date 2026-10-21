"""Automatic test for docs/tests.md: "DoA per-utterance direction".

No hardware: feeds doa.py's DoaTracker fake readings with a fake clock
and checks the direction it reports for "the utterance that just
ended" - converted from board degrees to Jack's own angle (front = board
JACK_FRONT_DEG, + = his right), and None whenever the recent speech
readings are too few, too old, or disagree.

Run: venv/bin/python tests/test_doa.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import doa  # noqa: E402


def tracker():
    clock = [1000.0]
    t = doa.DoaTracker(read=lambda: (0, False), now=lambda: clock[0])

    def feed(board_deg, n, speech=True, step=0.1):
        for _ in range(n):
            clock[0] += step
            t.add(board_deg, speech)
    return t, feed, clock


def main():
    errors = []
    front = doa.JACK_FRONT_DEG
    if doa.to_jack(front) != 0 or doa.to_jack(front + 90) != 90 or doa.to_jack(front - 90) != -90:
        errors.append("to_jack() doesn't map front/right/left to 0/+90/-90")
    if doa.to_jack((front + 180) % 360) not in (180, -180):
        errors.append("to_jack() doesn't map behind to 180")

    t, feed, clock = tracker()
    feed(front + 90, 10)
    if t.direction() != 90:
        errors.append(f"steady reading on the right should give 90, got {t.direction()}")

    t, feed, clock = tracker()
    feed(front - 90, 20)        # an earlier talker on the left...
    feed(front + 45, 10)        # ...then the one who just spoke, front-right
    if t.direction() != 45:
        errors.append(f"should follow the newest readings, got {t.direction()}")

    t, feed, clock = tracker()
    feed(front + 3, 4)          # one reading short of MIN_READINGS
    feed(front + 3, 10, speech=False)
    if t.direction() is not None:
        errors.append("too few speech-flagged readings should give None")

    t, feed, clock = tracker()
    for i in range(10):         # alternating left/right - no agreement
        feed(front + (90 if i % 2 else -90), 1)
    if t.direction() is not None:
        errors.append("disagreeing readings should give None")

    t, feed, clock = tracker()
    feed(front + 90, 10)
    clock[0] += doa.LOOKBACK_S + 0.1
    if t.direction() is not None:
        errors.append("readings older than LOOKBACK_S should give None")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: board-to-Jack angle mapping, newest steady readings give the direction, "
          "too few / disagreeing / stale readings give None")


if __name__ == "__main__":
    main()
