"""Re-runnable test for docs/tests.md: "Bench servo noise at the mic".

Manual measurement - needs a spare servo plugged into the roll channel
(pin 5) in place of the bird's own roll servo, lying loose on the bench,
a quiet room, and nobody talking. Sends plain `r`/`t`/`s` commands (the
bird's pitch/yaw stay at their power-on rest, holding, so they add no
motion noise) and records the XVF3800's capture channel throughout.

Written 2026-10-14 to explore quieter head servos as the source fix for
servo motion noise (see docs/log.md's 4.2 history): with the servo off
the bird there is no mechanical path into the mic array, so this
measures airborne noise only - the baseline a candidate replacement
servo gets compared against under the same bench setup.

Each step moves the servo back and forth for a while at a fixed
amplitude and move time, then holds. Reported per step: level while
moving, in the first second of the hold (servos were found to buzz for
about a second after stopping), and in the rest of the hold. Also the
share of the moving segment's energy in three frequency bands, to tell
low gear rumble from motor whine. Each step's audio is saved as
<out>/<n>_<step>.wav for listening.

Run: venv/bin/python tests/measure_bench_servo.py
         [--port /dev/ttyUSB0] [--lead-in 10] [--out stt_samples/bench_servo]
         [--baseline-only]
"""

import argparse
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import serial_link  # noqa: E402
from capture import RATE, Capture  # noqa: E402

ROLL_REST = 30     # ServoControl.ino ROLL_RESTING (command units, 0-50)
BOOT_S = 3.0
HOLD_S = 6.0
BANDS = ((0, 500), (500, 2000), (2000, 8000))

# (name, +-amplitude in command degrees, move time ms, seconds of moving)
STEPS = (
    ("sway3_1500", 3, 1500, 12),      # today's On Watch ambient sway size
    ("sway10_1500", 10, 1500, 12),
    ("sway20_1500", 20, 1500, 12),
    ("sway20_400", 20, 400, 8),       # fast, excursion-like
)


def frame_db(x, n):
    fr = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)


def band_shares(x):
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / RATE)
    total = spec.sum() + 1e-12
    return [spec[(freqs >= lo) & (freqs < hi)].sum() / total for lo, hi in BANDS]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=serial_link.PORT)
    ap.add_argument("--lead-in", type=float, default=10.0)
    ap.add_argument("--out", default="stt_samples/bench_servo")
    ap.add_argument("--baseline-only", action="store_true",
                    help="record just the still baseline (e.g. with the test servo unplugged)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Starting in {args.lead_in:g}s - keep the room quiet...", flush=True)
    time.sleep(args.lead_in)

    frames, label = [], [None]
    cap = Capture(on_frame=lambda s, t: frames.append((label[0], s)))
    writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port)
    writer.start()
    cap.start()
    time.sleep(BOOT_S)
    segs = [("baseline", "still")]
    try:
        label[0] = 0
        print("  baseline (still) 8s", flush=True)
        time.sleep(8)
        for name, amp, ms, secs in () if args.baseline_only else STEPS:
            print(f"  {name}: +-{amp} in {ms}ms for {secs}s, then hold {HOLD_S:g}s", flush=True)
            label[0] = len(segs)
            segs.append((name, "moving"))
            end, side = time.monotonic() + secs, 1
            while time.monotonic() < end:
                writer.send_head(f"r{ROLL_REST + side * amp}t{ms}s")
                side = -side
                time.sleep(ms / 1000)
            writer.send_head(f"r{ROLL_REST}t{ms}s")
            time.sleep(ms / 1000)
            label[0] = len(segs)
            segs.append((name, "hold"))
            time.sleep(HOLD_S)
    finally:
        label[0] = None
        cap.stop()
        writer.stop()

    print("\nMic level per segment (100ms slices, dBFS):")
    for i, (name, kind) in enumerate(segs):
        s = np.concatenate([f for l, f in frames if l == i]).astype(np.int16)
        tag = f"{i}_{name}_{kind}"
        with wave.open(str(out / f"{tag}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(s.tobytes())
        x = s.astype(np.float64) / 32768
        db = frame_db(x, RATE // 10)
        line = f"  {tag:24s} median {np.median(db):6.1f}  p90 {np.percentile(db, 90):6.1f}  max {db.max():6.1f}"
        if kind == "hold":
            line += f"   (1st s median {np.median(db[:10]):.1f}, rest {np.median(db[10:]):.1f})"
        else:
            sh = band_shares(x)
            line += "   bands " + "  ".join(f"{lo}-{hi}Hz {p:4.0%}" for (lo, hi), p in zip(BANDS, sh))
        print(line)
    print(f"Audio saved in {out}/")


if __name__ == "__main__":
    main()
