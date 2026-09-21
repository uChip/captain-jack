#!/usr/bin/env python3
"""
Hardware exercise harness for the servos.

Drives arduino/ServoControl/ServoControl.ino through Off Watch's and
Asleep's ambient/excursion gesture behavior (specification.md 4.10/4.12),
switching between the two modes on a random 2-5 minute timer. This is a
standalone test tool, not the production orchestration/state machine:

  - No audio output — gestures only. Wav pairings in gesture-catalog.yaml
    are ignored entirely.
  - No wake-word/phrase detection or DoA-based mode transitions — mode
    switching here is a blind random timer, not "Ahoy, Captain Jack" /
    "Goodnight, Jack" / idle timeouts. See specification.md 4.11 for the
    real transition design this doesn't implement.
  - No DoA-driven baseline yaw tracking. Investigated 2026-09-20: the
    XVF3800 exposes a generic USB-HID control interface (/dev/hidraw0,
    already bound by the kernel's generic hidraw driver - no separate
    kernel driver needed, matching what Chip had read) and a vendor-
    specific USB interface, but no `xvf_host` tool or equivalent exists
    on this Pi, and the actual command protocol spoken over that HID
    channel (to request AEC_AZIMUTH_VALUES) isn't something to guess at
    - getting it right needs Seeed's real documentation/reference host
    application, not invented byte layouts. Baseline yaw is therefore
    just held at rest throughout, per gesture-catalog.yaml's documented
    fallback ("baseline pitch/roll ... centered on `resting` ... before
    anything has nudged it"). `read_doa_azimuth()` below is a stub
    (always returns None) so wiring in a real reading later is a small
    change here, not a rewrite.
  - Asleep exits back to Off Watch here (never to On Watch, since On
    Watch's conversation loop doesn't run in this harness at all) - a
    deliberate simplification for exercising mechanicals, not a
    statement about the real transition rules (Asleep only ever exits
    to On Watch in production - specification.md 4.11).

Run: venv/bin/python exercise_hardware.py
     venv/bin/python exercise_hardware.py --dry-run   (no serial port needed; prints what would be sent)
     venv/bin/python exercise_hardware.py --port /dev/ttyUSB0 --min-mode-minutes 1 --max-mode-minutes 2
"""

import argparse
import random
import sys
import time
from pathlib import Path

import yaml

CATALOG_PATH = Path(__file__).parent / "docs" / "gesture-catalog.yaml"
DEFAULT_PORT = "/dev/ttyUSB0"
BAUD = 115200

# Opening the serial port toggles DTR, which resets the Arduino - it runs
# ServoControl.ino's DEBUG startup self-test (beak open/close a few times)
# for roughly 2.5s before it's ready for real commands. See ServoControl.ino.
ARDUINO_BOOT_DELAY_S = 3.5

AXIS_RANGE = {"p": (0, 50), "r": (0, 50), "y": (0, 130)}
BEAK_RANGE = (0, 60)

ASLEEP_EXTRA_CHANCE_DEFAULT = 0.25  # tunable - no measured value yet, see specification.md 4.10


def load_catalog():
    return yaml.safe_load(CATALOG_PATH.read_text())


def find_gesture(catalog, lib, gesture_id):
    return next(g for g in catalog[lib] if g["id"] == gesture_id)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def read_doa_azimuth():
    """Stub - see module docstring. Always None until the XVF3800 control
    protocol is implemented against real vendor documentation."""
    return None


class Baseline:
    """Tracks the live pitch/roll/yaw center that gesture deltas resolve
    against - specification.md 4.12's "baseline," not a fixed constant."""

    def __init__(self, resting):
        self.pitch = resting["pitch"]
        self.roll = resting["roll"]
        self.yaw = resting["yaw"]

    def nudge_yaw_toward_doa(self):
        azimuth = read_doa_azimuth()
        if azimuth is not None:
            self.yaw = azimuth  # placeholder - no smoothing/rate-limiting designed yet


class Arduino:
    def __init__(self, port, dry_run=False):
        self.dry_run = dry_run
        self.ser = None
        if dry_run:
            print("[dry-run] not opening a serial port")
            return
        import serial

        self.ser = serial.Serial(port, BAUD, timeout=0.2)
        print(f"Opened {port} at {BAUD} baud; waiting {ARDUINO_BOOT_DELAY_S}s "
              f"for the board's startup self-test...")
        time.sleep(ARDUINO_BOOT_DELAY_S)
        self._drain()

    def _drain(self):
        if self.ser and self.ser.in_waiting:
            text = self.ser.read(self.ser.in_waiting).decode(errors="replace")
            if text.strip():
                print(f"  [arduino] {text.strip()}")

    def send(self, cmd):
        print(f"  -> {cmd}")
        if not self.dry_run:
            self.ser.write(cmd.encode())
            time.sleep(0.05)
            self._drain()

    def close(self):
        if self.ser:
            self.ser.close()


def resolve_move(move, baseline):
    """Compute the real wire command for one Move against the current
    baseline - specification.md 4.12: deltas resolve at send time, never
    baked in ahead of time."""
    p = clamp(int(baseline.pitch + move.get("dp", 0)), *AXIS_RANGE["p"])
    r = clamp(int(baseline.roll + move.get("dr", 0)), *AXIS_RANGE["r"])
    y = clamp(int(baseline.yaw + move.get("dy", 0)), *AXIS_RANGE["y"])
    t = int(move.get("t", 100))

    cmd = ""
    if "beak" in move:
        b = clamp(int(move["beak"]), *BEAK_RANGE)
        cmd += f"b{b}"
    cmd += f"p{p}r{r}y{y}t{t}s"
    return cmd


def play_gesture(arduino, baseline, gesture):
    print(f"Playing gesture: {gesture['id']} ({gesture['name']})")
    for move in gesture["moves"]:
        arduino.send(resolve_move(move, baseline))
        time.sleep(move["wait_ms"] / 1000.0)


def off_watch_loop(arduino, catalog, baseline, until, args):
    lib = "off_watch"
    ambient = find_gesture(catalog, lib, catalog["ambient"][lib])
    excursions = [g for g in catalog[lib] if g["id"] != ambient["id"]]
    lo, hi = catalog["excursion_interval_seconds"][lib]
    next_excursion = time.monotonic() + random.uniform(lo, hi)
    last_excursion_id = None

    while time.monotonic() < until:
        baseline.nudge_yaw_toward_doa()
        play_gesture(arduino, baseline, ambient)
        if time.monotonic() >= until:
            return
        if time.monotonic() >= next_excursion:
            choices = [g for g in excursions if g["id"] != last_excursion_id]
            pick = random.choice(choices)
            play_gesture(arduino, baseline, pick)
            last_excursion_id = pick["id"]
            next_excursion = time.monotonic() + random.uniform(lo, hi)


def asleep_loop(arduino, catalog, baseline, until, args):
    lib = "asleep"
    ambient_id = catalog["ambient"][lib]
    ambient = find_gesture(catalog, lib, ambient_id)
    skip = {ambient_id, "sl-waking-up", "sl-settle-to-sleep"}
    extras = [g for g in catalog[lib] if g["id"] not in skip]
    last_extra_id = None

    while time.monotonic() < until:
        play_gesture(arduino, baseline, ambient)
        if time.monotonic() >= until:
            return
        if random.random() < args.asleep_extra_chance:
            choices = [g for g in extras if g["id"] != last_extra_id]
            pick = random.choice(choices)
            play_gesture(arduino, baseline, pick)
            last_extra_id = pick["id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--dry-run", action="store_true",
                         help="print commands instead of opening a serial port")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-mode-minutes", type=float, default=2.0)
    parser.add_argument("--max-mode-minutes", type=float, default=5.0)
    parser.add_argument("--asleep-extra-chance", type=float,
                         default=ASLEEP_EXTRA_CHANCE_DEFAULT)
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    catalog = load_catalog()
    baseline = Baseline(catalog["resting"])
    arduino = Arduino(args.port, dry_run=args.dry_run)

    mode = "off_watch"
    try:
        while True:
            duration_s = random.uniform(
                args.min_mode_minutes * 60, args.max_mode_minutes * 60
            )
            until = time.monotonic() + duration_s
            print(f"\n=== Entering {mode.upper()} for {duration_s / 60:.1f} minutes ===")

            if mode == "off_watch":
                off_watch_loop(arduino, catalog, baseline, until, args)
                play_gesture(arduino, baseline,
                             find_gesture(catalog, "asleep", "sl-settle-to-sleep"))
                mode = "asleep"
            else:
                asleep_loop(arduino, catalog, baseline, until, args)
                play_gesture(arduino, baseline,
                             find_gesture(catalog, "asleep", "sl-waking-up"))
                mode = "off_watch"
    except KeyboardInterrupt:
        print("\nInterrupted - returning to resting and exiting.")
    finally:
        arduino.send(f"p{baseline.pitch}r{baseline.roll}y{baseline.yaw}t500s")
        time.sleep(0.6)
        arduino.close()


if __name__ == "__main__":
    sys.exit(main())
