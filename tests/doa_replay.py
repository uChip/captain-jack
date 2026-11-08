"""Re-runnable tool for docs/tests.md: "DoA stream replay".

No hardware. Replays a coordinator.py --save session's doa_stream.csv
(every board reading, each mic reopen after Jack's own sound, and each
utterance's answer) through doa.py's current DoaTracker - the real code,
on a fake clock - and prints, per utterance, the answer logged live next
to the answer the current rules give. Use it to try a rule change against
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import doa  # noqa: E402
from motion import MAX_TURN_DEG  # noqa: E402

NAMES = {"front": 0, "front_left": -45, "left": -90, "front_right": 45, "right": 90, "behind": 180}


def replay(path):
    """[(utterance seconds, live answer or None, replayed answer or None)]."""
    clock = [0.0]
    t = doa.DoaTracker(read=lambda: (0, False), now=lambda: clock[0])
    out = []
    with open(path) as f:
        rows = list(csv.reader(f))[1:]
    for row in rows:
        clock[0] = float(row[0])
        event = row[3] if len(row) > 3 else ""
        if not event:
            t.add(int(row[1]), row[2] == "1")
        elif event.startswith("jack_done"):
            t.jack_done()
        elif event.startswith("utterance"):
            _, dur, _, live = event.split()
            live = None if live == "None" else round(float(live))
            out.append((float(dur.rstrip("s")), live, t.direction(float(dur.rstrip("s")))))
    return out


def _head(angle):
    return max(-MAX_TURN_DEG, min(MAX_TURN_DEG, angle))


def score(results, expect, tolerance=25):
    """{'right', 'wrong', 'none'} counts for the replayed answers, plus a
    mark per utterance ('' when unscored)."""
    counts = {"right": 0, "wrong": 0, "none": 0}
    marks = []
    for (_, _, got), want in zip(results, expect):
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
    fmt = lambda a: "-" if a is None else f"{a:+d}"
    print(f"{'utt':>4} {'secs':>5} {'live':>5} {'now':>5}  expect")
    for i, ((dur, live, got), want, mark) in enumerate(zip(results, expect, marks), 1):
        diff = "" if live == got else "  (changed)"
        want_s = "" if want is None else f"{want:+.0f} {mark}"
        print(f"{i:>4} {dur:>5.1f} {fmt(live):>5} {fmt(got):>5}  {want_s}{diff}")
    if args.expect:
        counts, _ = score(results, expect, args.tolerance)
        print(f"right {counts['right']}, wrong {counts['wrong']}, none {counts['none']}")


if __name__ == "__main__":
    main()
