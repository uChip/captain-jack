"""Re-runnable test for docs/tests.md: "Servo motion noise at the mic".

Manual measurement - needs the real bird (--port), a quiet room, and
nobody talking. Drives Motion through a fixed schedule of modes while
Capture records the XVF3800's capture channel, then reports the mic
level in each phase - how much louder the head servos make the room,
as heard by STT and the wake-word spotter. Written 2026-10-14 after
servo motion was found to be the cause of degraded recognition (see
docs/log.md's 4.2 history).

Off Watch excursions are disabled by default, so a phase measures only
that mode's ambient gesture (the first run accidentally included one,
whose bursts dominated the result); --excursions turns them back on.

A "still" phase right after a moving phase starts with a 4s settle
gap, and its report includes the first and second halves separately:
servos were found to stay noisy for several seconds after stopping.

Each phase's audio is saved as <out>/<n>_<phase>.wav for listening.

Run: venv/bin/python tests/measure_servo_noise.py
         [--port /dev/ttyUSB0] [--lead-in 10] [--excursions]
         [--out stt_samples/servo_noise]
         [--phases still:15,off_watch:20,on_watch:20,still:15]
         [--catalog FILE]

--catalog uses FILE in place of docs/gesture-catalog.yaml, to measure a
gesture change before committing to it.

Two more phase names (2026-10-21, after the head started turning toward
speakers): on_watch_turned sways with the head turned TURNED_DEG to
Jack's left, as after facing a speaker; still_turned holds it there
without moving - a servo holding position under load can hum.
"""

import argparse
import sys
import time
import wave
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

import serial_link  # noqa: E402
from capture import RATE, Capture  # noqa: E402
from motion import Motion, resolve_move  # noqa: E402

MODES = ("on_watch", "off_watch", "asleep")
TURNED = ("on_watch_turned", "still_turned")
TURNED_DEG = -50   # Motion.turn_toward() angle: 50 to Jack's left, the furthest it turns
SETTLE_S = 4.0     # let an in-flight gesture finish before a "still" phase
BOOT_S = 3.0       # Arduino resets when the serial port opens


def frame_db(x, n):
    fr = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=serial_link.PORT)
    ap.add_argument("--lead-in", type=float, default=10.0)
    ap.add_argument("--excursions", action="store_true")
    ap.add_argument("--out", default="stt_samples/servo_noise")
    ap.add_argument("--phases", default="still:15,off_watch:20,on_watch:20,still:15")
    ap.add_argument("--catalog", help="gesture catalog to use in place of the real one")
    args = ap.parse_args()

    phases = []
    for item in args.phases.split(","):
        name, secs = item.split(":")
        if name != "still" and name not in MODES + TURNED:
            sys.exit(f"unknown phase {name!r} - use still or one of {MODES + TURNED}")
        phases.append((name, float(secs)))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Starting in {args.lead_in:g}s - keep the room quiet...", flush=True)
    time.sleep(args.lead_in)

    frames, label = [], [None]
    cap = Capture(on_frame=lambda s, t: frames.append((label[0], s)))
    writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port)
    writer.start()
    catalog = yaml.safe_load(Path(args.catalog).read_text()) if args.catalog else None
    motion = Motion(writer, catalog=catalog, on_send=lambda c: None)
    if not args.excursions:
        motion._next_excursion = float("inf")
    motion.start()
    cap.start()
    time.sleep(BOOT_S)
    moved = False
    try:
        for i, (name, secs) in enumerate(phases):
            motion.set_mode(name if name in MODES else "on_watch" if name == "on_watch_turned" else "still")
            if name in TURNED:
                motion.turn_toward(TURNED_DEG)   # after set_mode, which faces front outside On Watch
            elif i and phases[i - 1][0] in TURNED:
                motion._send(resolve_move({"t": 800}, motion.baseline))   # face front again
            if name.startswith("still") and moved:
                time.sleep(SETTLE_S)
            moved = not name.startswith("still")
            label[0] = i
            print(f"  phase {i + 1}: {name} {secs:g}s", flush=True)
            time.sleep(secs)
            label[0] = None
    finally:
        cap.stop()
        motion.stop()
        writer.stop()

    print("\nMic level per phase (100ms slices, dBFS):")
    for i, (name, _) in enumerate(phases):
        s = np.concatenate([f for l, f in frames if l == i]).astype(np.int16)
        with wave.open(str(out / f"{i + 1}_{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(s.tobytes())
        db = frame_db(s.astype(np.float64) / 32768, RATE // 10)
        line = (f"  {i + 1}_{name:10s} p10 {np.percentile(db, 10):6.1f}  median {np.median(db):6.1f}  "
                f"p90 {np.percentile(db, 90):6.1f}  max {db.max():6.1f}")
        if name.startswith("still"):
            h = len(db) // 2
            line += f"   (1st half median {np.median(db[:h]):.1f}, 2nd {np.median(db[h:]):.1f})"
        print(line)
    print(f"Audio saved in {out}/")


if __name__ == "__main__":
    main()
