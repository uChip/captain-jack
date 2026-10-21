"""Re-runnable test for docs/tests.md: "Motion".

Automatic, no hardware: checks resolve_move's clamping/beak handling,
find_gesture_anywhere's cross-library search, and that a single Off
Watch step plays the ambient gesture, fires a due excursion, and
schedules an idle wav, and that entering Asleep settles in with the wav
pool matching how sleep was entered - all against a small synthetic catalog (the real
gesture-catalog.yaml's wait_ms timings would make this slow and is
exercised for real by motion.py's standalone mode against actual hardware).

Run: venv/bin/python tests/test_motion.py
"""

import copy
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import motion  # noqa: E402
import serial_link  # noqa: E402

TEST_CATALOG = {
    "resting": {"pitch": 35, "roll": 30, "yaw": 70, "beak": 60},
    "ambient": {"on_watch": "ow-amb", "off_watch": "amb", "asleep": "sl-amb"},
    "doa_yaw_tracking": {"on_watch": True, "off_watch": True, "asleep": False},
    "excursion_interval_seconds": {"off_watch": [0, 0]},   # always due - deterministic
    "on_watch": [
        {"id": "ow-amb", "name": "On Watch Ambient", "moves": [{"t": 10, "wait_ms": 1}]},
        {"id": "fx-squawk-tilt", "name": "Squawk Tilt",
         "moves": [{"dp": 8, "dr": 15, "t": 10, "wait_ms": 1}, {"t": 10, "wait_ms": 1}]},
    ],
    "off_watch": [
        {"id": "amb", "name": "Ambient", "moves": [{"dp": 1, "t": 10, "wait_ms": 1}]},
        {"id": "exc1", "name": "Excursion", "moves": [{"dp": 5, "t": 10, "wait_ms": 1}]},
    ],
    "asleep": [
        {"id": "sl-amb", "name": "Asleep Ambient", "moves": [{"t": 10, "wait_ms": 1}]},
        {"id": "sl-paired", "name": "Paired", "moves": [{"beak": 0, "t": 10, "wait_ms": 1}]},
        {"id": "sl-settle-to-sleep", "name": "Settle", "moves": [{"dr": 7, "t": 10, "wait_ms": 1}]},
    ],
    "wav_paired": [{"id": "wp-1", "name": "Wav-paired", "moves": [{"t": 10, "wait_ms": 1}]}],
    "wavs": {
        "on_watch": [],
        "off_watch": [{"file": "test_clip.wav"}],
        "asleep": [{"file": "paired_clip.wav", "gesture": "sl-paired"}],
    },
}


class FakeWriter:
    def __init__(self):
        self.sent = []

    def send_head(self, cmd):
        self.sent.append(cmd)


class FakePlayer:
    def __init__(self):
        self.played = []

    def play_file(self, path):
        self.played.append(Path(path).name)


def check_resolve_move():
    errors = []
    baseline = motion.Baseline(TEST_CATALOG["resting"])
    cmd = motion.resolve_move({"dp": 5, "dr": -3, "dy": 2, "t": 400, "wait_ms": 430}, baseline)
    if cmd != "p40r27y72t400s":
        errors.append(f"expected p40r27y72t400s, got {cmd}")

    # Clamping: pitch range is 0-50, so resting(35) + 100 must clamp to 50.
    cmd = motion.resolve_move({"dp": 100, "t": 10, "wait_ms": 10}, baseline)
    if "p50" not in cmd:
        errors.append(f"pitch delta should clamp to range max, got {cmd}")

    # beak is absolute (0-60), not baseline-relative, and clamps too.
    cmd = motion.resolve_move({"beak": 999, "t": 10, "wait_ms": 10}, baseline)
    if not cmd.startswith("b60p"):
        errors.append(f"beak should clamp to 60 and lead the command, got {cmd}")

    # Omitting beak must not emit a b<N> token at all.
    cmd = motion.resolve_move({"t": 10, "wait_ms": 10}, baseline)
    if cmd.startswith("b"):
        errors.append(f"beak omitted should mean no b<N> token, got {cmd}")
    return errors


def check_find_gesture_anywhere():
    errors = []
    g = motion.find_gesture_anywhere(TEST_CATALOG, "wp-1")
    if g["id"] != "wp-1":
        errors.append("didn't find a gesture living in wav_paired")
    g = motion.find_gesture_anywhere(TEST_CATALOG, "sl-paired")
    if g["id"] != "sl-paired":
        errors.append("didn't find a gesture living directly in a mode library (asleep)")
    try:
        motion.find_gesture_anywhere(TEST_CATALOG, "nope")
        errors.append("expected KeyError for an unknown gesture id")
    except KeyError:
        pass
    return errors


def check_off_watch_step():
    errors = []
    writer = FakeWriter()
    player = FakePlayer()
    m = motion.Motion(writer, player=player, catalog=TEST_CATALOG)
    m.set_mode("off_watch")
    m._step_off_watch()

    if len(writer.sent) < 2:
        errors.append(f"expected at least an ambient move and an excursion move, got {writer.sent}")
    else:
        if "p36" not in writer.sent[0]:   # ambient: resting pitch 35 + dp 1
            errors.append(f"first command should be the ambient gesture's move, got {writer.sent[0]}")
        if "p40" not in writer.sent[1]:   # excursion: resting pitch 35 + dp 5
            errors.append(f"second command should be the due excursion's move, got {writer.sent[1]}")
    if player.played != ["test_clip.wav"]:
        errors.append(f"expected the one off_watch wav to be scheduled, got {player.played}")
    return errors


def check_asleep_wav_pairing():
    errors = []
    writer = FakeWriter()
    player = FakePlayer()
    m = motion.Motion(writer, player=player, catalog=TEST_CATALOG)
    m.play_random_wav("asleep")   # the only asleep wav is paired with sl-paired
    if player.played != ["paired_clip.wav"]:
        errors.append(f"expected the paired clip to play, got {player.played}")
    if not any("b0" in c for c in writer.sent):
        errors.append(f"expected sl-paired's beak move to fire alongside the clip, got {writer.sent}")
    return errors


def check_fall_asleep():
    """Spec 4.10's "On entering Asleep": the settle gesture always plays
    first, with one wav from the pool matching how sleep was entered -
    none for MODE: NAP (context None), and never a listed-but-missing file."""
    errors = []
    catalog = copy.deepcopy(TEST_CATALOG)
    catalog["wavs"]["asleep"] = [
        {"file": "goodnight_clip.wav", "gesture": "sl-settle-to-sleep", "context": "goodnight_phrase"},
        {"file": "drift_clip.wav", "gesture": "sl-settle-to-sleep", "context": "idle_timeout"},
        {"file": "not_recorded_yet.wav", "gesture": "sl-settle-to-sleep", "context": "idle_timeout"},
    ]
    settle = "r37"   # resting roll 30 + sl-settle-to-sleep's dr 7

    for context, expected in (("goodnight_phrase", ["goodnight_clip.wav"]),
                              ("idle_timeout", ["drift_clip.wav"]),
                              (None, [])):
        for _ in range(5):   # random pick - repeat so a missing file would show up
            writer, player = FakeWriter(), FakePlayer()
            m = motion.Motion(writer, player=player, catalog=catalog)
            m.fall_asleep(context)
            m._step_asleep()
            if player.played != expected:
                errors.append(f"context {context!r}: expected {expected}, got {player.played}")
                break
            if not writer.sent or settle not in writer.sent[0]:
                errors.append(f"context {context!r}: settle gesture should play first, got {writer.sent}")
                break
            # ...and only once - the next step is ordinary Asleep breathing.
            writer.sent.clear()
            m._step_asleep()
            if any(settle in c for c in writer.sent):
                errors.append(f"context {context!r}: settle gesture repeated on the next step")
                break

    # A transition before Motion gets to it cancels the settle (woken right away).
    writer, player = FakeWriter(), FakePlayer()
    m = motion.Motion(writer, player=player, catalog=catalog)
    m.fall_asleep("goodnight_phrase")
    m.set_mode("on_watch")
    m.set_mode("asleep")
    m._step_asleep()
    if player.played or any(settle in c for c in writer.sent):
        errors.append("a later set_mode() should cancel an unplayed settle")
    return errors


def check_on_watch_uses_its_own_ambient():
    errors = []
    writer = FakeWriter()
    m = motion.Motion(writer, catalog=TEST_CATALOG)
    m.set_mode("on_watch")
    m._step_on_watch()
    if not writer.sent:
        errors.append("on_watch step sent nothing")
    return errors


def check_hold():
    """hold(True) stops gestures between moves (On Watch's listening
    hold, 2026-10-14 - servo noise drowns out speech); hold(False) and
    any set_mode() release it."""
    errors = []
    writer = FakeWriter()
    m = motion.Motion(writer, catalog=TEST_CATALOG)
    m.set_mode("off_watch")
    m.hold(True)
    m.play_gesture(motion.find_gesture(TEST_CATALOG, "off_watch", "amb"))
    if writer.sent:
        errors.append(f"held Motion still sent {writer.sent!r}")
    m.hold(False)
    m.play_gesture(motion.find_gesture(TEST_CATALOG, "off_watch", "amb"))
    if len(writer.sent) != 1:
        errors.append(f"released Motion should send the gesture's one move, sent {writer.sent!r}")
    m.hold(True)
    m.set_mode("on_watch")
    if m.holding:
        errors.append("set_mode() should release hold")
    return errors


def check_squawk_tilt():
    """squawk_tilt() sends the tilt after its delay even while held (the
    mic is deaf during the squawk), holds it for the squawk's length,
    returns to baseline, and a second call while one runs is skipped."""
    errors = []
    writer = FakeWriter()
    m = motion.Motion(writer, catalog=TEST_CATALOG)
    m.hold(True)
    start = time.monotonic()
    m.squawk_tilt(0.05, 0.1)
    m.squawk_tilt(0.0, 0.1)   # still running - skipped
    time.sleep(0.03)
    if writer.sent:
        errors.append(f"squawk_tilt sent before its delay: {writer.sent!r}")
    while m._one_shot.locked() and time.monotonic() - start < 2:
        time.sleep(0.01)
    want = ["p43r45y70t10s", "p35r30y70t10s"]
    if writer.sent != want:
        errors.append(f"squawk_tilt should send {want!r}, sent {writer.sent!r}")
    if time.monotonic() - start < 0.15:
        errors.append("squawk_tilt didn't wait out its delay plus the squawk's length")
    return errors


def check_turn_toward():
    """turn_toward() moves the baseline yaw toward the speaker (yaw + =
    turned left, so a speaker on Jack's right lowers it), capped at
    MAX_TURN_DEG, sending one TURN_MS move even while held; the squawk
    tilt then cocks toward a speaker on the left, and leaving On Watch
    faces front again."""
    errors = []
    writer = FakeWriter()
    m = motion.Motion(writer, catalog=TEST_CATALOG)
    m.set_mode("on_watch")
    m.hold(True)
    m.turn_toward(30)
    if writer.sent != [f"p35r30y40t{motion.TURN_MS}s"]:
        errors.append(f"turn_toward(30) should face 30 to the right, sent {writer.sent!r}")
    m.turn_toward(-120)
    want_yaw = 70 + motion.MAX_TURN_DEG
    if m.baseline.yaw != want_yaw:
        errors.append(f"turn_toward(-120) should cap at yaw {want_yaw}, got {m.baseline.yaw}")

    writer.sent.clear()
    m.squawk_tilt(0.0, 0.0, toward=-120)
    while m._one_shot.locked():
        time.sleep(0.01)
    if writer.sent[:1] != [f"p43r15y{want_yaw}t10s"]:
        errors.append(f"squawk toward the left should cock left and keep the heading, sent {writer.sent!r}")
    writer.sent.clear()
    m.squawk_tilt(0.0, 0.0, toward=10)   # nearly straight ahead - the catalog's own way
    while m._one_shot.locked():
        time.sleep(0.01)
    if writer.sent[:1] != [f"p43r45y{want_yaw}t10s"]:
        errors.append(f"squawk near front should cock the catalog's way, sent {writer.sent!r}")

    m.set_mode("off_watch")
    if m.baseline.yaw != 70:
        errors.append(f"leaving On Watch should face front again, yaw {m.baseline.yaw}")
    return errors


def check_stop_returns_to_rest():
    """stop() sends head and beak to the catalog's resting pose (not the
    drifted baseline), and SerialWriter.stop() sends whatever head
    commands are still queued before closing - together they replace the
    return to rest that closing the port used to cause by resetting the
    Arduino (serial_link.py clears HUPCL since 2026-10-15)."""
    errors = []
    writer = FakeWriter()
    m = motion.Motion(writer, catalog=TEST_CATALOG)
    m.baseline.pitch = 10   # drifted away from resting
    m.stop()
    want = f"b60p35r30y70t{motion.REST_ON_STOP_MS}s"
    if writer.sent[-1:] != [want]:
        errors.append(f"stop() should end with {want!r}, sent {writer.sent!r}")

    sent = []
    sw = serial_link.SerialWriter(now_fn=time.monotonic, dry_run=True, on_send=sent.append)
    sw.send_head(want)   # queued, never picked up by a running writer thread
    sw.stop()
    if sent != [want]:
        errors.append(f"SerialWriter.stop() should send queued head commands, sent {sent!r}")
    return errors


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        motion.WAV_DIR = Path(tmp)   # play_random_wav checks the file exists; none need to be real audio
        (motion.WAV_DIR / "test_clip.wav").touch()
        (motion.WAV_DIR / "paired_clip.wav").touch()
        (motion.WAV_DIR / "goodnight_clip.wav").touch()
        (motion.WAV_DIR / "drift_clip.wav").touch()

        errors = (check_resolve_move() + check_find_gesture_anywhere()
                  + check_off_watch_step() + check_asleep_wav_pairing()
                  + check_fall_asleep() + check_on_watch_uses_its_own_ambient()
                  + check_hold() + check_squawk_tilt() + check_turn_toward()
                  + check_stop_returns_to_rest())

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: resolve_move clamping, cross-library gesture lookup, and "
          "ambient/excursion/wav scheduling, Asleep settle-in, and the listening hold and squawk tilt correct, "
          "turning toward the speaker moves the baseline (capped, cocks the squawk their way, faces front "
          "after On Watch), and stopping returns the head to rest")
