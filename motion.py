"""Captain Jack motion: the ambient/excursion gesture engine, live.

Implements the Motion & idle thread from docs/specification.md section
4.16(g), build step 7: runs whichever mode's gesture behavior is current
from gesture-catalog.yaml (spec 4.12) - the ambient gesture repeats
forever, excursions interrupt it at random intervals (Off Watch) or by
chance each breath (Asleep), and Off Watch also schedules idle clips
from the Wav Library (spec 4.10) into Playback. Entering Asleep via
fall_asleep() first plays the settle-to-sleep gesture, with a line from
the Asleep wav pool matching how sleep was entered (spec 4.10's "On
entering Asleep"). Sends primitive p/r/y/t/s
and b commands through serial_link.py's SerialWriter.send_head() - never
a named gesture, per Open Issues issue 7.

This ports exercise_hardware.py's already-hardware-validated gesture
logic (Baseline, resolve_move, play_gesture, the off_watch/asleep loops)
rather than redesigning it: that logic is what id-idle-breathing and
friends were tuned against (Open Issues issue 25), so behavior here
should look the same, just driven by mode changes instead of a blind
random timer, and over the real serial_link.py writer instead of a
blocking one. exercise_hardware.py has since been archived (2026-10-10,
docs/archive/exercise_hardware-2026-10-10.py); this module's own
standalone mode (below) replaces it as the hardware harness, and is the
same code the real Coordinator runs.

The Coordinator calls set_mode() on every transition; Motion picks up
the new mode at the top of its next loop iteration (gestures already in
flight finish first - preemption is still undesigned, Open Issues issue
24, same as it is for exercise_hardware.py).

On Watch's excursions are meant to be triggered by conversation content/
DoA/emotion (spec 4.10), not implemented yet - On Watch currently runs
ambient motion only. The wav-scheduling heuristic (one random wav per
excursion tick, Off Watch only) is a starting point, not measured.

Run standalone against the real Arduino for a quick check (no Playback,
so idle clips aren't exercised - see coordinator.py for the full thing):
    venv/bin/python motion.py [--port /dev/ttyUSB0] [--mode off_watch]
"""

import random
import threading
import time
from pathlib import Path

import yaml

CATALOG_PATH = Path(__file__).parent / "docs" / "gesture-catalog.yaml"
WAV_DIR = Path(__file__).parent / "wavFiles"

AXIS_RANGE = {"p": (0, 50), "r": (0, 50), "y": (0, 130)}
BEAK_RANGE = (0, 60)

ASLEEP_EXTRA_CHANCE = 0.25   # tunable, no measured value yet - spec 4.10
SETTLE_TO_SLEEP_ID = "sl-settle-to-sleep"


def load_catalog() -> dict:
    return yaml.safe_load(CATALOG_PATH.read_text())


def find_gesture(catalog, lib, gesture_id):
    return next(g for g in catalog[lib] if g["id"] == gesture_id)


def find_gesture_anywhere(catalog, gesture_id):
    """A Wav's paired gesture can come from the dedicated wav_paired
    library or, as the existing Asleep examples do, directly from a mode
    library (e.g. sl-settle-to-sleep) - ids are unique across all of
    them (spec 4.12), so search each collection that could hold one."""
    for lib in ("wav_paired", "on_watch", "off_watch", "asleep"):
        for g in catalog.get(lib) or []:
            if g["id"] == gesture_id:
                return g
    raise KeyError(f"no gesture {gesture_id!r} in wav_paired or any mode library")


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def read_doa_azimuth():
    """Stub - see CLAUDE.md work list. Always None until the XVF3800
    control protocol is implemented against real vendor documentation."""
    return None


class Baseline:
    """Tracks the live pitch/roll/yaw center that gesture deltas resolve
    against - spec 4.12's "baseline," not a fixed constant."""

    def __init__(self, resting):
        self.pitch = resting["pitch"]
        self.roll = resting["roll"]
        self.yaw = resting["yaw"]

    def nudge_yaw_toward_doa(self):
        azimuth = read_doa_azimuth()
        if azimuth is not None:
            self.yaw = azimuth   # placeholder - no smoothing/rate-limiting designed yet


def resolve_move(move, baseline) -> str:
    """Compute the real wire command for one Move against the current
    baseline - spec 4.12: deltas resolve at send time, never baked in."""
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


class Motion:
    """Runs the current mode's ambient/excursion gesture loop and (Off
    Watch) schedules idle clips. set_mode() switches catalogs; takes
    effect at the top of the next loop iteration.
    """

    def __init__(self, serial_writer, player=None, catalog=None, on_send=None):
        self.serial_writer = serial_writer
        self.player = player
        self.catalog = catalog or load_catalog()
        self.baseline = Baseline(self.catalog["resting"])
        self.on_send = on_send   # testing hook: called with each resolved command
        self.mode = "off_watch"
        self._stop = threading.Event()
        self._thread = None
        self._next_excursion = 0.0
        self._last_excursion_id = None
        self._last_wav = None
        self._settle_pending = False   # set by fall_asleep(), consumed by _step_asleep()
        self._settle_context = None

    def set_mode(self, mode):
        self._settle_pending = False   # a later transition cancels an unplayed settle
        self.mode = mode

    def fall_asleep(self, context=None):
        """Enter Asleep, settling in first (spec 4.10, "On entering
        Asleep"). context names how sleep was entered, picking the wav
        pool: "goodnight_phrase" (the "Goodnight, Jack" phrase),
        "idle_timeout" (Off Watch's 15-minute timeout), or None for
        Haiku's MODE: NAP - no wav then, since Jack's own live reply
        already said goodnight moments earlier."""
        self.set_mode("asleep")
        self._settle_context = context
        self._settle_pending = True

    def start(self):
        self._thread = threading.Thread(target=self._run, name="motion", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()

    # --- gesture playback ---

    def _send(self, cmd):
        if self.on_send:
            self.on_send(cmd)
        self.serial_writer.send_head(cmd)

    def play_gesture(self, gesture):
        for move in gesture["moves"]:
            self._send(resolve_move(move, self.baseline))
            time.sleep(move["wait_ms"] / 1000.0)

    # --- idle wav scheduling (Off Watch only - spec 4.10) ---

    def play_random_wav(self, lib):
        wavs = self.catalog.get("wavs", {}).get(lib) or []
        if not wavs or self.player is None:
            return
        choices = [w for w in wavs if w["file"] != self._last_wav] or wavs
        pick = random.choice(choices)
        self._last_wav = pick["file"]
        path = WAV_DIR / pick["file"]
        if path.exists():
            self.player.play_file(path)
        gesture_id = pick.get("gesture")
        if gesture_id:
            self.play_gesture(find_gesture_anywhere(self.catalog, gesture_id))

    def settle_into_sleep(self, context):
        """The settle-to-sleep gesture, with one random existing wav
        from the Asleep pool for this context playing alongside it. A
        listed file that doesn't exist yet (e.g. SleepyMumble.wav, still
        to be recorded) is skipped rather than settling in silence."""
        pool = [w for w in self.catalog.get("wavs", {}).get("asleep") or []
                if context is not None and w.get("context") == context
                and (WAV_DIR / w["file"]).exists()]
        gesture_id = SETTLE_TO_SLEEP_ID
        if pool and self.player is not None:
            choices = [w for w in pool if w["file"] != self._last_wav] or pool
            pick = random.choice(choices)
            self._last_wav = pick["file"]
            self.player.play_file(WAV_DIR / pick["file"])
            gesture_id = pick.get("gesture", SETTLE_TO_SLEEP_ID)
        self.play_gesture(find_gesture_anywhere(self.catalog, gesture_id))

    # --- per-mode steps, one ambient cycle at a time so set_mode() is
    # noticed promptly between gestures ---

    def _step_on_watch(self):
        ambient = find_gesture(self.catalog, "on_watch", self.catalog["ambient"]["on_watch"])
        self.baseline.nudge_yaw_toward_doa()
        self.play_gesture(ambient)
        # Content/DoA/emotion-triggered excursions: not implemented yet (spec 4.10).

    def _step_off_watch(self):
        lib = "off_watch"
        ambient = find_gesture(self.catalog, lib, self.catalog["ambient"][lib])
        self.baseline.nudge_yaw_toward_doa()
        self.play_gesture(ambient)
        if self.mode != lib:
            return
        if time.monotonic() >= self._next_excursion:
            excursions = [g for g in self.catalog[lib] if g["id"] != ambient["id"]]
            choices = [g for g in excursions if g["id"] != self._last_excursion_id] or excursions
            pick = random.choice(choices)
            self.play_gesture(pick)
            self._last_excursion_id = pick["id"]
            lo, hi = self.catalog["excursion_interval_seconds"][lib]
            self._next_excursion = time.monotonic() + random.uniform(lo, hi)
            self.play_random_wav(lib)   # one clip per excursion tick - starting point, not measured

    def _step_asleep(self):
        lib = "asleep"
        if self._settle_pending:
            self._settle_pending = False
            self.settle_into_sleep(self._settle_context)
            if self.mode != lib:
                return
        ambient_id = self.catalog["ambient"][lib]
        ambient = find_gesture(self.catalog, lib, ambient_id)
        skip = {ambient_id, "sl-waking-up", "sl-settle-to-sleep"}
        extras = [g for g in self.catalog[lib] if g["id"] not in skip]
        self.play_gesture(ambient)
        if self.mode != lib:
            return
        if extras and random.random() < ASLEEP_EXTRA_CHANCE:
            choices = [g for g in extras if g["id"] != self._last_excursion_id] or extras
            pick = random.choice(choices)
            self.play_gesture(pick)
            self._last_excursion_id = pick["id"]

    def _run(self):
        while not self._stop.is_set():
            mode = self.mode
            if mode == "on_watch":
                self._step_on_watch()
            elif mode == "off_watch":
                self._step_off_watch()
            elif mode == "asleep":
                self._step_asleep()
            else:
                time.sleep(0.2)


def main():
    import argparse

    import serial_link

    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", default=serial_link.PORT)
    parser.add_argument("--mode", default="off_watch", choices=["on_watch", "off_watch", "asleep"])
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port, dry_run=args.dry_run,
                                       on_send=lambda cmd: print(f"  -> {cmd}"))
    writer.start()
    motion = Motion(writer, on_send=lambda cmd: None)
    motion.set_mode(args.mode)
    print(f"Running {args.mode} motion for {args.seconds:g}s (no Playback - gestures only)...")
    motion.start()
    try:
        time.sleep(args.seconds)
    finally:
        motion.stop()
        writer.stop()


if __name__ == "__main__":
    main()
