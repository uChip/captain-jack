"""Manual check for docs/tests.md: "Head yaw direction".

Needs the real bird, Chip watching. Turns the head to what
gesture-catalog.yaml calls "turned left" (yaw above resting) for 5
seconds, then back to center. Answer: is Jack looking toward his own
left - the side with the nearest wall? Written 2026-10-21 when the first
live DoA turn went the wrong way (docs/log.md 4.9): either this sign or
the walk-around's left/right is backwards.

Run: venv/bin/python tests/check_yaw_direction.py [--port /dev/ttyUSB0] [--lead-in 10]
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import serial_link  # noqa: E402
from motion import Motion  # noqa: E402

TURN = 30   # degrees above resting yaw - "turned left" per the catalog


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=serial_link.PORT)
    ap.add_argument("--lead-in", type=float, default=10.0)
    args = ap.parse_args()
    writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port)
    writer.start()
    motion = Motion(writer, on_send=lambda c: None)   # not started: no ambient motion
    resting = motion.catalog["resting"]
    print(f"Starting in {args.lead_in:g}s - watch which way Jack looks...", flush=True)
    time.sleep(max(args.lead_in, 3.0))   # also covers the Arduino's boot after the port opens
    try:
        writer.send_head(f"p{resting['pitch']}r{resting['roll']}y{resting['yaw'] + TURN}t800s")
        print(f"  head turned to yaw {resting['yaw'] + TURN} (catalog: turned LEFT) - holding 5s", flush=True)
        time.sleep(5.8)
    finally:
        motion.stop()    # back to rest
        writer.stop()
    print("Back to center. Was Jack looking toward his own left (the wall side)?")


if __name__ == "__main__":
    main()
