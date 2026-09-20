"""Re-runnable test for docs/tests.md: "gesture-catalog.yaml servo bounds".

Verifies every Move command string in docs/gesture-catalog.yaml stays
within the real servo ranges defined in
arduino/ServoControl/ServoControl.ino (pitch/roll 0-50, yaw 0-130,
beak 0-60, duration 0-9999ms), and that every Move has a positive
wait_ms. Catches authoring/arithmetic mistakes in the catalog before
they'd ever reach a real servo - does not touch hardware.

Run: venv/bin/python tests/test_gesture_catalog_bounds.py
"""

import re
import sys
from pathlib import Path

import yaml

CATALOG = Path(__file__).parent.parent / "docs" / "gesture-catalog.yaml"

# Matches arduino/ServoControl/ServoControl.ino's BEAK_RANGE/PITCH_RANGE/
# ROLL_RANGE/YAW_RANGE and DURATION_MAX as tuned 2026-09-20 - the incoming
# command range, not the offset-adjusted PWM angle.
BOUNDS = {
    "p": (0, 50),
    "r": (0, 50),
    "y": (0, 130),
    "b": (0, 60),
    "t": (0, 9999),
}


def check_catalog():
    catalog = yaml.safe_load(CATALOG.read_text())
    errors = []

    for lib in ("on_watch", "off_watch", "asleep"):
        for gesture in catalog[lib]:
            for i, move in enumerate(gesture["moves"]):
                cmd = move["cmd"]
                for axis, (lo, hi) in BOUNDS.items():
                    m = re.search(axis + r"(\d+)", cmd)
                    if not m:
                        continue
                    val = int(m.group(1))
                    if not (lo <= val <= hi):
                        errors.append(
                            f"{gesture['id']} move {i}: {axis}{val} outside "
                            f"[{lo}, {hi}] in '{cmd}'"
                        )
                if move["wait_ms"] <= 0:
                    errors.append(
                        f"{gesture['id']} move {i}: wait_ms must be positive, "
                        f"got {move['wait_ms']}"
                    )

    all_ids = [
        g["id"] for lib in ("on_watch", "off_watch", "asleep") for g in catalog[lib]
    ]
    dupes = {i for i in all_ids if all_ids.count(i) > 1}
    if dupes:
        errors.append(f"duplicate gesture ids: {sorted(dupes)}")

    return errors


def run():
    errors = check_catalog()
    if errors:
        print(f"FAIL: {len(errors)} problem(s) in gesture-catalog.yaml")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("PASS: gesture-catalog.yaml stays within servo bounds, no duplicate ids")


if __name__ == "__main__":
    run()
