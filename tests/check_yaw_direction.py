"""Manual check for docs/tests.md: "Head yaw direction".

Needs the real bird, Chip watching. Turns the head to what
gesture-catalog.yaml calls "turned left" (yaw above resting) for 5
seconds, then back to center. Answer: is Jack looking toward his own
left - the side with the nearest wall? Written 2026-10-21 when the first
live DoA turn went the wrong way (docs/log.md 4.9): either this sign or
the walk-around's left/right is backwards. (Answer, 2026-10-21: the sign
is right.)

--full instead turns to Motion.turn_toward()'s furthest left, center,
furthest right, center, 4s each (yaw 120, 70, 20, 70): watch and listen
for the head binding, a buzzing servo, or not coming back - in session23
the head stayed turned right after a full turn that way.

--axes moves one axis at a time, small, from rest and back (pitch up 10,
roll right 10, yaw left 15, 3s each), to see which head servos respond -
written after the head stopped moving entirely (2026-10-21).

Run: venv/bin/python tests/check_yaw_direction.py [--full | --axes] [--port /dev/ttyUSB0] [--lead-in 10]
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import serial_link  # noqa: E402
from motion import MAX_TURN_DEG, Motion  # noqa: E402

TURN = 30   # degrees above resting yaw - "turned left" per the catalog


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=serial_link.PORT)
    ap.add_argument("--lead-in", type=float, default=10.0)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--axes", action="store_true")
    args = ap.parse_args()
    writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port)
    writer.start()
    motion = Motion(writer, on_send=lambda c: None)   # not started: no ambient motion
    resting = motion.catalog["resting"]
    print(f"Starting in {args.lead_in:g}s - watch which way Jack looks...", flush=True)
    time.sleep(max(args.lead_in, 3.0))   # also covers the Arduino's boot after the port opens
    try:
        if args.axes:
            p0, r0, y0 = resting["pitch"], resting["roll"], resting["yaw"]
            for (p, r, y), what in (((p0 + 10, r0, y0), "PITCH up 10"), ((p0, r0 + 10, y0), "ROLL right 10"),
                                    ((p0, r0, y0 + 15), "YAW left 15")):
                writer.send_head(f"p{p}r{r}y{y}t600s")
                print(f"  {what} - 3s", flush=True)
                time.sleep(3.0)
                writer.send_head(f"p{p0}r{r0}y{y0}t600s")
                time.sleep(1.5)
        elif args.full:
            y0 = resting["yaw"]
            for yaw, where in ((y0 + MAX_TURN_DEG, "furthest LEFT"), (y0, "center"),
                               (y0 - MAX_TURN_DEG, "furthest RIGHT"), (y0, "center")):
                writer.send_head(f"p{resting['pitch']}r{resting['roll']}y{yaw}t800s")
                print(f"  yaw {yaw} ({where}) - 4s", flush=True)
                time.sleep(4.8)
        else:
            writer.send_head(f"p{resting['pitch']}r{resting['roll']}y{resting['yaw'] + TURN}t800s")
            print(f"  head turned to yaw {resting['yaw'] + TURN} (catalog: turned LEFT) - holding 5s", flush=True)
            time.sleep(5.8)
    finally:
        motion.stop()    # back to rest
        writer.stop()
    print("Back to center. Was Jack looking toward his own left (the wall side)?")


if __name__ == "__main__":
    main()
