"""Manual check for docs/tests.md: "Yaw exercise".

Needs the real bird, Chip watching. Swings the head left and right of
center on yaw alone, over and over, to prove the rebuilt yaw mechanism
(replacement B11DLS, NTA1220 thrust bearing, 5.5V servo supply -
2026-10-30, after the first yaw servo went limp; docs/log.md 4.9) works
reliably before turns get any bigger. Pitch and roll stay at rest.

Starts by holding center (resting yaw) for a few seconds - check the new
servo's horn put "center" where it should be - then swings
center -> left -> right -> left ... with each left<->right sweep taking
--sweep-ms, plus a short --dwell-ms at each end so each eased move has
finished before the next starts. Ctrl+C stops early; either way the head
returns to rest.

--hold N instead visits center, left, center, right, center at --swing,
holding each N seconds, for measuring where the head actually points
(e.g. a protractor or a photo from above): written 2026-10-30 when the
+-30 swing looked to turn 6-8 degrees further right than left, with
center about 2 degrees right.

--roll N holds the head tipped N degrees (+ = right, - = left, as in
gesture-catalog.yaml) for the whole run, from the center hold on -
added 2026-10-30 after a slight mechanical noise at the far left of a
+-50 swing (a wire catching?), to see whether the tip changes it.

Watch and listen for: hesitation or stutter partway through a sweep,
buzzing or straining at either end, the two ends not matching (one side
short), drift in where center lands, and the servo case getting warm
(touch it after a long run).

Run: venv/bin/python tests/exercise_yaw.py [--swing 20] [--sweep-ms 1000]
     [--dwell-ms 100] [--cycles 30] [--hold SECONDS] [--roll N] [--port /dev/ttyUSB0]
     [--lead-in 10] [--dry-run]
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import serial_link  # noqa: E402
from motion import Motion  # noqa: E402

YAW_MIN, YAW_MAX = 0, 130   # nominal yaw range the firmware accepts (spec 4.13)
ROLL_MIN, ROLL_MAX = 0, 50
CENTER_HOLD_S = 4.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--swing", type=int, default=20, help="degrees each side of center (default 20)")
    ap.add_argument("--sweep-ms", type=int, default=1000, help="one left<->right sweep (default 1000)")
    ap.add_argument("--dwell-ms", type=int, default=100, help="pause at each end (default 100)")
    ap.add_argument("--cycles", type=int, default=30, help="left-right-left round trips (default 30)")
    ap.add_argument("--hold", type=float, help="step and hold each position this many seconds instead")
    ap.add_argument("--roll", type=int, default=0, help="hold the head tipped this much (+ = right)")
    ap.add_argument("--port", default=serial_link.PORT)
    ap.add_argument("--lead-in", type=float, default=10.0)
    ap.add_argument("--dry-run", action="store_true", help="print commands, no serial port")
    args = ap.parse_args()

    writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port, dry_run=args.dry_run,
                                      on_send=(lambda c: print(f"    > {c}")) if args.dry_run else None)
    motion = Motion(writer, on_send=lambda c: None)   # not started: no ambient motion
    resting = motion.catalog["resting"]
    p0, r0, y0 = resting["pitch"], resting["roll"] + args.roll, resting["yaw"]
    if not ROLL_MIN <= r0 <= ROLL_MAX:
        sys.exit(f"--roll {args.roll} goes past the roll range: rest {resting['roll']}, allowed {ROLL_MIN}-{ROLL_MAX}")
    left, right = y0 + args.swing, y0 - args.swing
    if left > YAW_MAX or right < YAW_MIN:
        sys.exit(f"--swing {args.swing} goes past the yaw range: center {y0}, "
                 f"allowed {YAW_MIN}-{YAW_MAX} (at most {min(YAW_MAX - y0, y0 - YAW_MIN)})")

    def move(yaw, ms):
        writer.send_head(f"p{p0}r{r0}y{yaw}t{ms}s")

    writer.start()
    if args.hold:
        print(f"Starting in {args.lead_in:g}s - hold center/left/center/right/center at "
              f"+-{args.swing} deg, {args.hold:g}s each", flush=True)
    else:
        print(f"Starting in {args.lead_in:g}s - swing +-{args.swing} deg (yaw {right}..{left}), "
              f"{args.sweep_ms}ms per sweep, {args.cycles} cycles, roll {args.roll:+d}", flush=True)
    time.sleep(max(args.lead_in, 3.0))   # also covers the Arduino's boot after the port opens
    started = time.monotonic()
    done = 0
    try:
        if args.hold:
            for yaw, where in ((y0, "center"), (left, f"LEFT {args.swing}"), (y0, "center"),
                               (right, f"RIGHT {args.swing}"), (y0, "center")):
                move(yaw, 1000)
                print(f"  yaw {yaw} ({where}) - {args.hold:g}s", flush=True)
                time.sleep(1.0 + args.hold)
            return
        move(y0, 1000)
        print(f"  center (yaw {y0}) - {CENTER_HOLD_S:g}s: is the head facing straight ahead?", flush=True)
        time.sleep(1.0 + CENTER_HOLD_S)
        half = args.sweep_ms // 2
        move(left, half)                      # center -> left is half a sweep
        time.sleep((half + args.dwell_ms) / 1000)
        step = (args.sweep_ms + args.dwell_ms) / 1000
        next_at = time.monotonic()
        for done in range(1, args.cycles + 1):
            for yaw in (right, left):
                move(yaw, args.sweep_ms)
                next_at += step                    # scheduled, so print/serial time doesn't drift
                time.sleep(max(0.0, next_at - time.monotonic()))
            print(f"  cycle {done}/{args.cycles}", flush=True)
    except KeyboardInterrupt:
        print("\n  stopped early", flush=True)
        done -= 1                             # the interrupted cycle didn't finish
    finally:
        motion.stop()    # back to rest
        writer.stop()
    if args.hold:
        print("Back to center.")
        return
    print(f"Back to center. {max(done, 0)} full cycles in {time.monotonic() - started:.0f}s.")


if __name__ == "__main__":
    main()
