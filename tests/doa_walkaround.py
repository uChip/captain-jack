"""Re-runnable test for docs/tests.md: "DoA walk-around".

Manual measurement - needs the real bird and someone to walk around it.
Jack speaks each position aloud ("stand in front of me..."), then logs
doa.py's readings at 10Hz while the person counts aloud. Per position,
prints the circular mean and spread of the speech-flagged readings from
the last SETTLED_S seconds only - the first seconds of each window are
walking, and the board's reading takes ~1-2s to swing round (2026-10-15).
Saves the raw readings as CSV. Written 2026-10-15 for spec 4.9's
calibration: which board angle is Jack's front, and which way is left.
2026-10-21, for the rerun on the permanent mount: a "behind" position
(front/left/right/behind pin down the 90-degree offset and the
direction), --laps to walk the circle more than once (do the readings
repeat?), and a lead-in before Jack's first instruction.

After the per-position table it fits Jack's front angle and which way
the board's angle runs (search over every offset and both directions,
minimizing the median error) for both the DOA_VALUE reading and beam 2
of AEC_AZIMUTH_VALUES, and prints how often each position read as left
or right of front - the 2026-10-21 analysis (docs/log.md 4.9).
--analyze CSV re-runs just that on an earlier recording.

Run: venv/bin/python tests/doa_walkaround.py [--out stt_samples/doa_walkaround.csv] [--window 12]
         [--laps 2] [--lead-in 10]
     venv/bin/python tests/doa_walkaround.py --analyze stt_samples/doa_walkaround.csv
"""

import argparse
import csv
import sys
import threading
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from doa import DoA  # noqa: E402
from playback import Playback  # noqa: E402
from tts import TTS  # noqa: E402

SETTLED_S = 5.0
POSITIONS = [
    ("front", "Stand right in front of me, about four feet away, and count out loud until I speak again."),
    ("front_left", "Now move to my front left, halfway round, and keep counting."),
    ("left", "Now straight off my left side, and keep counting."),
    ("front_right", "Now go round to my front right, and keep counting."),
    ("right", "Now straight off my right side, and keep counting."),
    ("behind", "Now go right round behind me, and keep counting."),
    ("quiet", "Now stay quiet for a moment."),
]
AGAIN = "Once more round, starting in front of me again. Count until I speak."
DONE = "That's the lot. Thank ye, matey!"


def circ_stats(deg):
    a = np.radians(deg)
    c, s = np.cos(a).mean(), np.sin(a).mean()
    spread = np.degrees(np.sqrt(-2 * np.log(max(np.hypot(c, s), 1e-9))))   # circular std dev
    return np.degrees(np.arctan2(s, c)) % 360, spread


TRUE_DEG = {"front": 0, "front_left": -45, "left": -90, "front_right": 45, "right": 90, "behind": 180}


def wrap(x):
    return (x + 180) % 360 - 180


def fit(csv_path):
    """Fit Jack's front (board degrees) and direction to a recording's
    settled, speech-flagged readings; print the result per reading."""
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    ends = {}
    for r in rows:
        ends[r["phase"]] = float(r["t"])
    for col, label in (("doa", "DOA_VALUE"), ("beam2", "beam 2")):
        samples = []
        for r in rows:
            base = r["phase"] if r["phase"] in TRUE_DEG else r["phase"].rsplit("_", 1)[0]
            if base in TRUE_DEG and r["speech"] == "1" and float(r["t"]) >= ends[r["phase"]] - SETTLED_S:
                samples.append((TRUE_DEG[base], float(r[col]), base))
        if not samples:
            print(f"{label}: no speech-flagged readings")
            continue
        best = None
        for sign in (1, -1):
            for off in range(360):
                err = np.abs([wrap(sign * (m - off) - t) for t, m, _ in samples])
                if best is None or np.median(err) < best[0]:
                    best = (np.median(err), sign, off, err)
        score, sign, off, err = best
        way = "right" if sign == 1 else "left"
        print(f"\n{label}: Jack's front = {off}, angle increases toward Jack's {way}; "
              f"median error {score:.0f}, 75th pct {np.percentile(err, 75):.0f}")
        for base in TRUE_DEG:
            rel = np.array([sign * wrap(m - off) for _, m, b in samples if b == base])
            if len(rel):
                print(f"  {base:12s} n={len(rel):3d}  median {np.median(rel):5.0f}  "
                      f"left {np.mean(rel < 0) * 100:3.0f}%  right {np.mean(rel > 0) * 100:3.0f}%")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="stt_samples/doa_walkaround.csv")   # git-ignored
    parser.add_argument("--window", type=float, default=12.0, help="seconds per position")
    parser.add_argument("--laps", type=int, default=1)
    parser.add_argument("--lead-in", type=float, default=10.0)
    parser.add_argument("--analyze", metavar="CSV", help="only fit an earlier recording")
    args = parser.parse_args()
    if args.analyze:
        fit(args.analyze)
        return

    doa = DoA()
    tts = TTS(on_audio=None)
    audio = {name: tts.synthesize(text) for name, text in POSITIONS + [("done", DONE), ("again", AGAIN)]}
    player = Playback()
    player.start()

    phase = ["start"]
    rows = []
    stop = threading.Event()
    t0 = time.monotonic()

    def poll():
        while not stop.is_set():
            az, speech = doa.read()
            rows.append((time.monotonic() - t0, phase[0], az, int(speech), *doa.beam_azimuths()))
            time.sleep(0.1)

    threading.Thread(target=poll, daemon=True).start()

    def say(name):
        phase[0] = "jack_" + name
        player.play(audio[name], name)
        time.sleep(0.2)
        player.wait_idle()

    print(f"Starting in {args.lead_in:g}s...", flush=True)
    time.sleep(args.lead_in)
    windows = {}
    for lap in range(1, args.laps + 1):
        for i, (name, _) in enumerate(POSITIONS):
            say("again" if lap > 1 and i == 0 else name)
            key = name if args.laps == 1 else f"{name}_{lap}"
            phase[0] = key
            start = time.monotonic() - t0
            print(f"  {key}", flush=True)
            time.sleep(args.window if name != "quiet" else 6)
            windows[key] = (start, time.monotonic() - t0)
    say("done")
    stop.set()
    time.sleep(0.3)
    player.stop()
    doa.close()

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "phase", "doa", "speech", "beam0", "beam1", "beam2", "beam3"])
        w.writerows([round(r[0], 2), *r[1:4], *(round(b) for b in r[4:])] for r in rows)

    print(f"{'position':14s} {'n':>3s} {'mean':>5s} {'spread':>6s}   (speech-flagged, last {SETTLED_S:.0f}s)")
    for name, (start, end) in windows.items():
        az = [r[2] for r in rows if r[1] == name and r[3] and r[0] >= end - SETTLED_S]
        if az:
            mean, spread = circ_stats(az)
            print(f"{name:14s} {len(az):3d} {round(mean) % 360:5d} {spread:6.0f}")
        else:
            print(f"{name:14s}   0     -      -")
    print(f"raw readings: {args.out}")
    fit(args.out)


if __name__ == "__main__":
    main()
