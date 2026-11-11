"""Re-runnable test for docs/tests.md: "Head-turn noise at the mic".

Manual recording - needs the real bird (--port), a quiet room, and nobody
talking. Holds the head still, then makes a fixed series of head turns
(Motion's turn_toward() move, at each --turn-ms speed), each followed by
a quiet gap, while Capture records the XVF3800's capture channel. Saves
each turn as <out>/turn_<ms>ms_<from>_to_<to>.wav, starting the moment
the move is sent, and prints its level. Written 2026-11-08 to judge
turning toward a speaker *while they're still talking* (an early turn,
docs/log.md 4.9): tests/turn_noise_stt.py mixes these into saved
utterances and compares recognition with and without.

Run: venv/bin/python tests/record_turn_noise.py
         [--port /dev/ttyUSB0] [--lead-in 10] [--turn-ms 600,1200]
         [--gap 3] [--out stt_samples/turn_noise]
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
from motion import AXIS_RANGE, MAX_TURN_DEG, Motion, clamp, resolve_move  # noqa: E402

# Jack angles (+ = his right), from the previous heading: small, medium,
# full side, and the biggest swing there is (one side to the other).
HEADINGS = [-30, 0, 50, -50, 0, 30, 0]
BOOT_S = 3.0
SETTLE_S = 3.0


def frame_db(x, n):
    fr = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=serial_link.PORT)
    ap.add_argument("--lead-in", type=float, default=10.0)
    ap.add_argument("--turn-ms", default="600,1200")
    ap.add_argument("--gap", type=float, default=3.0, help="seconds recorded after each turn is sent")
    ap.add_argument("--out", default="stt_samples/turn_noise")
    args = ap.parse_args()
    speeds = [int(x) for x in args.turn_ms.split(",")]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Starting in {args.lead_in:g}s - keep the room quiet...", flush=True)
    time.sleep(args.lead_in)

    frames, label = [], [None]
    cap = Capture(on_frame=lambda s, t: frames.append((label[0], s)))
    writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port)
    writer.start()
    motion = Motion(writer, on_send=lambda c: None)
    motion.excursions = False
    motion.set_mode("still")
    motion.start()
    cap.start()
    time.sleep(BOOT_S)
    rest = motion.catalog["resting"]["yaw"]
    segments = []
    try:
        label[0] = "quiet"
        print("  quiet (head still)", flush=True)
        time.sleep(SETTLE_S)
        heading = 0
        for ms in speeds:
            for target in HEADINGS:
                if target == heading:
                    continue
                name = f"turn_{ms}ms_{heading:+d}_to_{target:+d}"
                turn = clamp(target, -MAX_TURN_DEG, MAX_TURN_DEG)
                motion.baseline.yaw = clamp(int(round(rest - turn)), *AXIS_RANGE["y"])
                label[0] = name
                motion._send(resolve_move({"t": ms}, motion.baseline))
                print(f"  {name}", flush=True)
                segments.append(name)
                time.sleep(args.gap)
                heading = target
        label[0] = None
        if heading != 0:
            motion.baseline.yaw = rest
            motion._send(resolve_move({"t": 800}, motion.baseline))
            time.sleep(1.0)
    finally:
        cap.stop()
        motion.stop()
        writer.stop()

    def save(name):
        s = np.concatenate([f for l, f in frames if l == name]).astype(np.int16)
        with wave.open(str(out / f"{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(s.tobytes())
        return frame_db(s.astype(np.float64) / 32768, RATE // 10)

    q = save("quiet")
    print(f"\nquiet: median {np.median(q):.1f} dBFS (100ms slices)")
    print("turns: loudest 100ms, and median of the first 1s (the move) vs the last 1s")
    for name in segments:
        db = save(name)
        print(f"  {name:28s} max {db.max():6.1f}  first 1s {np.median(db[:10]):6.1f}  "
              f"last 1s {np.median(db[-10:]):6.1f}")
    print(f"Audio saved in {out}/")


if __name__ == "__main__":
    main()
