"""Automatic test for docs/tests.md: "DoA per-utterance direction".

No hardware: feeds doa.py's DoaTracker fake readings with a fake clock
and checks the direction it reports for "the utterance that just
ended" - converted from board degrees to Jack's own angle (front = board
JACK_FRONT_DEG, + = his right): the value the board held longest while
the person spoke. Includes the two patterns seen live in session23
(2026-10-21): the window opening still stuck on Jack's own voice, and a
swing after the talker stops. None when there are too few readings, no
direction dominates, or the board is still where Jack's own sound left it
(jack_done()) - but a board that stayed on the same person through Jack's
reply is trusted (session24, 2026-11-08: one person talking from one spot
got no turns at all under the old "unchanged from before" rule). Also the
--save stream log, and a replay of session25's logged stream
(tests/data/doa_session25_stream.csv, via tests/doa_replay.py): a person who
moved is found where they are now, not their old spot, and any place Jack's
own sound moved the board since the last line is refused.

Run: venv/bin/python tests/test_doa.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import doa  # noqa: E402

F = doa.JACK_FRONT_DEG


def tracker(log=None):
    clock = [1000.0]
    t = doa.DoaTracker(read=lambda: (0, False), now=lambda: clock[0], log=log)

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
    feed(-90, 3.0)
    t.direction(3.0)    # the person, on his left
    feed(96, 4.0)       # Jack's reply moves the board to his speaker...
    t.jack_done()
    feed(96, 3.0)       # ...and it never leaves it while the next line is spoken
    if t.direction(3.0) is not None:
        errors.append("a board still where Jack's own sound left it should give None")

    t, feed = tracker()
    feed(40, 3.0)       # first line after waking: board still on the beep
    t.jack_done()
    feed(40, 3.0)
    if t.direction(3.0) is not None:
        errors.append("with nobody heard yet, a board unmoved since Jack's sound should give None")

    t, feed = tracker()
    feed(-81, 3.0)
    t.direction(3.0)    # the person, on his left...
    feed(-81, 4.0, speech=False)   # ...the board holds still through Jack's reply...
    t.jack_done()
    feed(-81, 3.0)      # ...and they speak again from the same spot (session24 utt04)
    if t.direction(3.0) != -81:
        errors.append(f"same person, same spot, board unmoved by Jack should give -81, got {t.direction(3.0)}")

    t, feed = tracker()
    feed(0, 3.0)
    t.direction(3.0)
    feed(96, 4.0)       # Jack's reply moves the board...
    t.jack_done()
    feed(96, 0.4)
    feed(-32, 3.0)      # ...then the person, now front-left (session24 utt02)
    if t.direction(3.4) != -32:
        errors.append(f"a person away from where Jack's sound left the board should give -32, got {t.direction(3.4)}")

    t, feed = tracker()
    feed(96, 3.0)
    t.jack_done()       # moved=True, nobody heard yet...
    feed(-45, 3.0)
    t.direction(3.0)    # ...an utterance uses that up...
    feed(96, 3.0)       # ...so the next one, with no Jack sound between, is trusted
    if t.direction(3.0) != 96:
        errors.append(f"with no Jack sound since the last utterance, nothing should be stale, got {t.direction(3.0)}")

    t, feed = tracker()
    feed(38, 3.0)
    t.direction(3.0)    # the person at his front-right...
    feed(38, 4.0, speech=False)
    t.jack_done()
    feed(38, 3.4)       # ...walks to front: the board holds the old spot for 3.4s
    feed(1, 2.6)        # (session25 utt06)
    if t.direction(6.0) != 1:
        errors.append(f"a person who moved should be found where they are now (1), got {t.direction(6.0)}")

    t, feed = tracker()
    feed(4, 3.0)
    t.direction(3.0)    # the person in front
    feed(37, 2.0)       # the squawk moves the board to +37...
    t.jack_done()
    feed(4, 3.0)        # ...the reply drifts back to the person's spot before the mic reopens
    t.jack_done()
    feed(37, 3.0)       # the board latches on +37 again (session25 utt11)
    if t.direction(3.0) is not None:
        errors.append(f"any place Jack's sound moved the board since the last line should be refused, "
                      f"got {t.direction(3.0)}")

    import io
    log = io.StringIO()
    t, feed = tracker(log)
    feed(10, 1.0)
    t.jack_done()
    feed(10, 1.0)
    t.direction(1.0)
    lines = log.getvalue().splitlines()
    if (len(lines) != 22 or lines[0] != f"1000.10,{(F + 10) % 360},1,"
            or not lines[10].endswith("jack_done +10 moved=1") or "utterance 1.0s -> " not in lines[-1]):
        errors.append(f"stream log wrong: {lines[:2]} ... {lines[-2:]}")

    t, feed = tracker()
    feed(3, 0.4)
    feed(3, 2.0, speech=False)
    if t.direction(2.4) is not None:
        errors.append("too few speech-flagged readings should give None")

    t, feed = tracker()
    for a in (-150, -90, -30, 30, 90, 150) * 5:   # all over the place - nothing dominates
        feed(a, 0.1)
    if t.direction(3.0) is not None:
        errors.append(f"scattered readings should give None, got {t.direction(3.0)}")

    # session25's logged stream, replayed through the current rules: where
    # Chip said he was (docs/log.md 4.9) - 8 right, none wrong, utt11 none.
    import doa_replay
    results = doa_replay.replay(Path(__file__).parent / "data" / "doa_session25_stream.csv")
    expect = doa_replay.parse_expect("-,front,left,right,front_right,front,-,left,left,front,right,-")
    counts, marks = doa_replay.score(results, expect)
    if counts != {"right": 8, "wrong": 0, "none": 1}:
        errors.append(f"session25 replay: {counts}, per line {marks}")
    counts, marks = doa_replay.score(results, expect, which="early")
    if counts != {"right": 8, "wrong": 0, "none": 1}:
        errors.append(f"session25 replay, early turns: {counts}, per line {marks}")

    # session26 (the first live early turns): Chip's spots where he said
    # them. utt07 is the board itself reading -26/-30 for "in front". The two
    # fixes that followed it: no early turn 14s into utt01's 16s non-speech
    # sound (EARLY_WINDOW_S), and utt02 turns to Chip (+1) although he spoke
    # between the squawk and Jack's reply (jack_done vs jack_started).
    results = doa_replay.replay(Path(__file__).parent / "data" / "doa_session26_stream.csv")
    expect = doa_replay.parse_expect("-,front,left,left,left,front_right,front,front,front,-,-,-,-,front,-")
    end = doa_replay.score(results, expect)[0]
    early = doa_replay.score(results, expect, which="early")[0]
    if end != {"right": 8, "wrong": 1, "none": 0} or early != {"right": 5, "wrong": 1, "none": 3}:
        errors.append(f"session26 replay: end {end}, early {early}")
    if results[0].early is not None or results[1].end != 1:
        errors.append(f"session26 utt01 should have no early turn ({results[0].early}) "
                      f"and utt02 should turn to +1 ({results[1].end})")

    # Early direction: only once speech has started, once the board has held
    # a new direction for EARLY_SETTLE_N readings, once per line.
    fired = []
    t, feed = tracker()
    t.on_early = fired.append
    feed(0, 3.0)
    t.direction(3.0)                 # someone in front
    feed(0, 2.0, speech=False)
    t.jack_done()                    # Jack's reply didn't move the board
    feed(-90, 2.0)                   # flagged sound before anyone speaks (footsteps)...
    if fired:
        errors.append(f"early direction fired before speech started: {fired}")
    t.speech_started()               # (counts from SPEECH_LEAD_S before: 2 readings)
    feed(-90, 0.1)
    if fired:
        errors.append(f"early direction fired before {doa.EARLY_SETTLE_N} settled readings: {fired}")
    feed(-90, 0.3)
    if fired != [-90] or t.take_early() != -90:
        errors.append(f"early direction should fire once at -90: {fired}")
    feed(45, 1.0)
    if fired != [-90]:
        errors.append(f"early direction fired twice in one line: {fired}")

    fired = []
    t, feed = tracker()
    t.on_early = fired.append
    feed(-81, 3.0)
    t.direction(3.0)
    feed(-81, 2.0, speech=False)
    t.jack_done()
    t.speech_started()
    feed(-81, 2.0)                   # same person, same spot - he already faces them
    t.direction(2.0)
    feed(30, 1.0)
    t.jack_started()                 # Jack's own sound: flagged, but him
    feed(30, 1.0)
    if fired:
        errors.append(f"no early direction for an unmoved board or for Jack's own sound: {fired}")

    fired = []
    t, feed = tracker()
    t.on_early = fired.append
    feed(-16, 3.0)
    t.direction(3.0)
    t.jack_done()                         # the board already at -16 (session26 utt01)
    t.speech_started()
    feed(-16, doa.EARLY_WINDOW_S + 0.5)   # a long sound that doesn't move it...
    feed(97, 1.0)                         # ...that ends somewhere new, too late to be early
    if fired:
        errors.append(f"early direction fired after EARLY_WINDOW_S: {fired}")

    t, feed = tracker()
    feed(147, 3.0)
    t.direction(3.0)                 # a noise on his right
    t.jack_started()
    feed(147, 1.0, speech=False)     # the squawk
    t.jack_done()
    feed(1, 1.0)                     # the person speaks up in front, before the reply...
    t.jack_started()
    feed(1, 2.0, speech=False)       # ...the reply doesn't move the board
    t.jack_done()
    feed(1, 3.0)
    if t.direction(3.0) != 1:
        errors.append(f"a person who spoke between Jack's sounds isn't Jack's sound (session26 utt02), "
                      f"got {t.direction(3.0)}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: board-to-Jack angle mapping; the direction held longest while the person spoke, "
          "ignoring Jack's own voice at the start, a swing at the end and earlier talkers; "
          "too few / scattered readings, or a board still where Jack's own sound left it, give None; "
          "the same person in the same spot is trusted; a person who moved is found where they are now; "
          "any place Jack's sound moved the board since the last line is refused; stream log; "
          "session25 replay 8 right / 0 wrong / 1 none, end-of-line and early; early direction "
          "only after speech starts, once settled, once per line, within EARLY_WINDOW_S, never for "
          "Jack's own sound; someone speaking between Jack's sounds isn't his sound; session26 replay")


if __name__ == "__main__":
    main()
