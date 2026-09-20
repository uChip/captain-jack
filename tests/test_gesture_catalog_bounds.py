"""Re-runnable test for docs/tests.md: "gesture-catalog.yaml sanity checks".

Verifies docs/gesture-catalog.yaml's structure: every Move's delta stays
within the axis's total travel (a loose sanity bound - real validity
depends on the runtime baseline, which this can't know statically), any
absolute `beak` value is in range, every wait_ms/t is positive, gesture
ids are unique, and every mode's `ambient` entry actually exists in that
mode's own gesture list. Does not touch hardware.

Run: venv/bin/python tests/test_gesture_catalog_bounds.py
"""

import sys
from pathlib import Path

import yaml

CATALOG = Path(__file__).parent.parent / "docs" / "gesture-catalog.yaml"

# Total travel per axis, from arduino/ServoControl/ServoControl.ino as
# tuned 2026-09-20 - a delta can't exceed this even before baseline is
# known, since baseline itself is always within [0, range].
AXIS_SPAN = {"dp": 50, "dr": 50, "dy": 130}
BEAK_RANGE = (0, 60)
LIBS = ("on_watch", "off_watch", "asleep")


def check_catalog():
    catalog = yaml.safe_load(CATALOG.read_text())
    errors = []

    for lib in LIBS:
        for gesture in catalog[lib]:
            for i, move in enumerate(gesture["moves"]):
                for axis, span in AXIS_SPAN.items():
                    val = move.get(axis, 0)
                    if abs(val) > span:
                        errors.append(
                            f"{gesture['id']} move {i}: {axis}={val} exceeds "
                            f"total axis travel of {span}"
                        )
                if "beak" in move:
                    lo, hi = BEAK_RANGE
                    if not (lo <= move["beak"] <= hi):
                        errors.append(
                            f"{gesture['id']} move {i}: beak={move['beak']} "
                            f"outside [{lo}, {hi}]"
                        )
                if move.get("t", 1) <= 0:
                    errors.append(f"{gesture['id']} move {i}: t must be positive")
                if move["wait_ms"] <= 0:
                    errors.append(
                        f"{gesture['id']} move {i}: wait_ms must be positive, "
                        f"got {move['wait_ms']}"
                    )

    all_ids = [g["id"] for lib in LIBS for g in catalog[lib]]
    dupes = {i for i in all_ids if all_ids.count(i) > 1}
    if dupes:
        errors.append(f"duplicate gesture ids: {sorted(dupes)}")

    for lib, ambient_id in catalog["ambient"].items():
        if ambient_id not in [g["id"] for g in catalog[lib]]:
            errors.append(
                f"ambient['{lib}'] = '{ambient_id}' not found in the "
                f"'{lib}' gesture list"
            )

    for lib, interval in catalog.get("excursion_interval_seconds", {}).items():
        lo, hi = interval
        if not (0 < lo < hi):
            errors.append(
                f"excursion_interval_seconds['{lib}'] = {interval} must "
                f"satisfy 0 < min < max"
            )

    return errors


def run():
    errors = check_catalog()
    if errors:
        print(f"FAIL: {len(errors)} problem(s) in gesture-catalog.yaml")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print(
        "PASS: gesture-catalog.yaml deltas/beak values sane, ids unique, "
        "ambient gestures exist"
    )


if __name__ == "__main__":
    run()
