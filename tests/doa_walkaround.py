"""Re-runnable test for docs/tests.md: "DoA walk-around".

Manual measurement - needs the real bird and someone to walk around it.
Jack speaks each position aloud ("stand in front of me..."), then logs
doa.py's readings at 10Hz while the person counts aloud. Per position,
prints the circular mean and spread of the speech-flagged readings from
the last SETTLED_S seconds only - the first seconds of each window are
walking, and the board's reading takes ~1-2s to swing round (2026-10-15).
Saves the raw readings as CSV. Written 2026-10-15 for spec 4.9's
calibration: which board angle is Jack's front, and which way is left.

Run: venv/bin/python tests/doa_walkaround.py [--out doa.csv] [--window 12]
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
    ("quiet", "Now stay quiet for a moment."),
]
DONE = "That's the lot. Thank ye, matey!"


def circ_stats(deg):
    a = np.radians(deg)
    c, s = np.cos(a).mean(), np.sin(a).mean()
    spread = np.degrees(np.sqrt(-2 * np.log(max(np.hypot(c, s), 1e-9))))   # circular std dev
    return np.degrees(np.arctan2(s, c)) % 360, spread


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="doa_walkaround.csv")
    parser.add_argument("--window", type=float, default=12.0, help="seconds per position")
    args = parser.parse_args()

    doa = DoA()
    tts = TTS(on_audio=None)
    audio = {name: tts.synthesize(text) for name, text in POSITIONS + [("done", DONE)]}
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

    windows = {}
    for name, _ in POSITIONS:
        say(name)
        phase[0] = name
        start = time.monotonic() - t0
        time.sleep(args.window if name != "quiet" else 6)
        windows[name] = (start, time.monotonic() - t0)
    say("done")
    stop.set()
    time.sleep(0.3)
    player.stop()
    doa.close()

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "phase", "doa", "speech", "beam0", "beam1", "beam2", "beam3"])
        w.writerows([round(r[0], 2), *r[1:4], *(round(b) for b in r[4:])] for r in rows)

    print(f"{'position':12s} {'n':>3s} {'mean':>5s} {'spread':>6s}   (speech-flagged, last {SETTLED_S:.0f}s)")
    for name, (start, end) in windows.items():
        az = [r[2] for r in rows if r[1] == name and r[3] and r[0] >= end - SETTLED_S]
        if az:
            mean, spread = circ_stats(az)
            print(f"{name:12s} {len(az):3d} {round(mean) % 360:5d} {spread:6.0f}")
        else:
            print(f"{name:12s}   0     -      -")
    print(f"raw readings: {args.out}")


if __name__ == "__main__":
    main()
