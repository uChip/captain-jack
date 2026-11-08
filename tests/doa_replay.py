"""Re-runnable tool for docs/tests.md: "DoA stream replay".

No hardware. Replays a coordinator.py --save session's doa_stream.csv
(every board reading, each mic reopen after Jack's own sound, and each
utterance's answer) through doa.py's current DoaTracker - the real code,
on a fake clock - and prints, per utterance, the answer logged live next
to the answer the current rules give, and the early (mid-line) direction
with how far into the speech it came. Use it to try a rule change against
real sessions before taking it to the bird. Written 2026-11-08 after
session25 (docs/log.md 4.9).

--expect= (with the "=", since the list can start with "-") gives where
the person really was, one per utterance, as Jack angles or names: front,
front_left, left, front_right, right, behind (0, -45, -90, 45, 90, 180),
or "-" for "don't score" (a reject, someone moving). Scored on where the
head would end up: both angles capped at Motion's 50-degree turn limit,
then right if within --tolerance degrees (default 25), else wrong (behind:
right for a near-full turn either way); no answer counts as none.

Run: venv/bin/python tests/doa_replay.py stt_samples/session25/doa_stream.csv
         [--expect="-,front,left,right,front_right,front,-,left,left,front,right,-"]
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import doa  # noqa: E402
from motion import MAX_TURN_DEG  # noqa: E402

NAMES = {"front": 0, "front_left": -45, "left": -90, "front_right": 45, "right": 90, "behind": 180}


PRE_ROLL_S = 0.3   # listener.py's PRE_ROLL_MS: an utterance's audio starts this long before the speech


@dataclass
class Result:
    secs: float          # utterance length
    live: int | None     # end-of-line answer logged live
    end: int | None      # end-of-line answer from today's rules
    early: int | None    # early answer from today's rules (mid-line)
    early_s: float | None  # ...seconds after the speech began


def replay(path):
    """[Result] per utterance in the stream."""
    clock = [0.0]
    t = doa.DoaTracker(read=lambda: (0, False), now=lambda: clock[0])
    out = []
    with open(path) as f:
        rows = list(csv.reader(f))[1:]
    events = [(i, r[3]) for i, r in enumerate(rows) if len(r) > 3 and r[3]]
    # Streams from before jack_started was logged (session25): Jack's reply
    # starts after the squawk's mic reopen, i.e. a jack_done followed by
    # another jack_done rather than an utterance.
    old = not any(e.startswith("jack_started") for _, e in events)
    follows = {i: (events[k + 1][1] if k + 1 < len(events) else "") for k, (i, _) in enumerate(events)}
    # ...and from before speech_started was logged: the Listener knew speech
    # had started PRE_ROLL_S + SPEECH_LEAD_S after its audio began.
    starts = []
    if not any(e.startswith("speech_started") for _, e in events):
        starts = sorted(float(rows[i][0]) - float(e.split()[1].rstrip("s")) + PRE_ROLL_S + doa.SPEECH_LEAD_S
                        for i, e in events if e.startswith("utterance"))
    for i, row in enumerate(rows):
        while starts and starts[0] <= float(row[0]):
            clock[0] = starts.pop(0)
            t.speech_started()
        clock[0] = float(row[0])
        event = row[3] if len(row) > 3 else ""
        if not event:
            t.add(int(row[1]), row[2] == "1")
        elif event.startswith("jack_done"):
            t.jack_done()
            if old and follows[i].startswith("jack_done"):
                t.jack_started()
        elif event.startswith("jack_started"):
            t.jack_started()
        elif event.startswith("speech_started"):
            t.speech_started()
        elif event.startswith("utterance"):
            _, dur, _, live = event.split()
            secs = float(dur.rstrip("s"))
            live = None if live == "None" else round(float(live))
            end = t.direction(secs)
            early_at = t.early_at
            early = t.take_early()
            began = clock[0] - secs + PRE_ROLL_S
            out.append(Result(secs, live, end, early,
                              None if early is None else round(early_at - began, 1)))
    return out


def _head(angle):
    return max(-MAX_TURN_DEG, min(MAX_TURN_DEG, angle))


def score(results, expect, tolerance=25, which="end"):
    """{'right', 'wrong', 'none'} counts for the replayed answers (which:
    "end" or "early"), plus a mark per utterance ('' when unscored)."""
    counts = {"right": 0, "wrong": 0, "none": 0}
    marks = []
    for r, want in zip(results, expect):
        got = getattr(r, which)
        if want is None:
            marks.append("")
            continue
        if got is None:
            mark = "none"
        elif abs(want) >= 180:   # behind: a full turn either way is as close as the head gets
            mark = "right" if abs(_head(got)) >= MAX_TURN_DEG - tolerance else "wrong"
        else:
            mark = "right" if abs(_head(got) - _head(want)) <= tolerance else "wrong"
        counts[mark] += 1
        marks.append(mark)
    return counts, marks


def parse_expect(text):
    out = []
    for item in text.split(","):
        item = item.strip()
        out.append(None if item == "-" else NAMES[item] if item in NAMES else float(item))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stream")
    parser.add_argument("--expect")
    parser.add_argument("--tolerance", type=float, default=25)
    args = parser.parse_args()
    results = replay(args.stream)
    expect = parse_expect(args.expect) if args.expect else [None] * len(results)
    if len(expect) != len(results):
        sys.exit(f"--expect has {len(expect)} entries, the stream has {len(results)} utterances")
    _, marks = score(results, expect, args.tolerance)
    _, early_marks = score(results, expect, args.tolerance, "early")
    fmt = lambda a: "-" if a is None else f"{a:+d}"
    print(f"{'utt':>4} {'secs':>5} {'live':>5} {'end':>5} {'early':>6} {'at':>5}  expect (end / early)")
    for i, (r, want, mark, emark) in enumerate(zip(results, expect, marks, early_marks), 1):
        diff = "" if r.live == r.end else "  (end changed)"
        want_s = "" if want is None else f"{want:+.0f} {mark} / {emark or '-'}"
        at = "-" if r.early_s is None else f"{r.early_s:.1f}s"
        print(f"{i:>4} {r.secs:>5.1f} {fmt(r.live):>5} {fmt(r.end):>5} {fmt(r.early):>6} {at:>5}  {want_s}{diff}")
    if args.expect:
        for which in ("end", "early"):
            c, _ = score(results, expect, args.tolerance, which)
            print(f"{which:>5}: right {c['right']}, wrong {c['wrong']}, none {c['none']}")


if __name__ == "__main__":
    main()
