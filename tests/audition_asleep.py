"""Re-runnable test for docs/tests.md: "Asleep gesture audition".

Manual, on the real bird, with someone listening in a quiet room. Written
2026-11-10 to find which Asleep gesture makes the loud periodic clack.
Needs the serial port and audio device, so stop the service first:
    sudo systemctl stop captain-jack

Each test is announced aloud by number and name, then run several times.
Tests cover every gesture Asleep repeats, then snore and snort split into
beak-only and head-only (same timing), then the firmware's boot wiggle as
a comparison, then candidate softer beak closes. Capture records each test, and the report gives the
loudest 10ms slice and the highest sample of each repeat, against the
quiet room measured at the start. Audio is saved as <out>/<n>_<name>.wav.

Run: venv/bin/python tests/audition_asleep.py
         [--port /dev/ttyUSB0] [--lead-in 10] [--reps 3] [--gap 2.5]
         [--only 3,5] [--out stt_samples/asleep_audition] [--list]

--list prints each test's serial commands and touches no hardware.
"""

import argparse
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import motion as motion_mod  # noqa: E402
import serial_link  # noqa: E402
from motion import Baseline, find_gesture, load_catalog, resolve_move  # noqa: E402

BOOT_S = 6.0        # SerialWriter waits out the Arduino's boot before sending
QUIET_S = 4.0       # room level, before anything moves
SETTLE_S = 1.5      # after the spoken label, before the test starts
WIGGLE_HOLD_S = 0.5 # ServoControl.ino's setup() delay between beak moves
RAMP_STEP_MS = 40   # between beak writes in a stepped close


def steps_full(moves, baseline):
    return [(resolve_move(m, baseline), m["wait_ms"] / 1000.0) for m in moves]


def steps_beak(moves):
    """The gesture's beak writes alone, at their original times."""
    return [(f"b{m['beak']}" if "beak" in m else None, m["wait_ms"] / 1000.0) for m in moves]


def steps_head(moves, baseline):
    """The gesture's head moves alone."""
    return [(resolve_move({k: v for k, v in m.items() if k != "beak"}, baseline)
             if any(k in m for k in ("dp", "dr", "dy", "t")) else None, m["wait_ms"] / 1000.0)
            for m in moves]


def build_tests(catalog):
    base = Baseline(catalog["resting"])
    get = lambda gid: find_gesture(catalog, "asleep", gid)["moves"]
    snore, snort = get("sl-snore"), get("sl-snort")
    closed = serial_link.BEAK_RANGE
    return [
        ("breathing", steps_full(get("sl-idle-breathing-quiet"), base)),
        ("micro twitch", steps_full(get("sl-micro-twitch-quiet"), base)),
        ("snore", steps_full(snore, base)),
        ("snort", steps_full(snort, base)),
        ("snore, beak only", steps_beak(snore)),
        ("snore, head only", steps_head(snore, base)),
        ("snort, beak only", steps_beak(snort)),
        ("snort, head only", steps_head(snort, base)),
        ("boot wiggle", [(f"b{b}", WIGGLE_HOLD_S) for b in (0, closed, 0, closed)]),
        # Candidate softer closes, all from snore's opening (added 2026-11-10
        # once 1-9 showed the beak's close is the clack).
        ("close in 300 milliseconds", [("b16", 0.93)] + ramp(16, closed, 300)),
        ("close in 600 milliseconds", [("b16", 0.93)] + ramp(16, closed, 600)),
        ("fast, then gentle last bit", [("b16", 0.93), ("b40", 0.15)] + ramp(40, closed, 400)),
        ("snap, stopping short", [("b16", 0.93), (f"b{closed - 6}", 0.5), (f"b{closed}", 0.3)]),
    ]


def ramp(start, end, ms, step_ms=RAMP_STEP_MS):
    """Beak writes from start to end, evenly spaced over ms."""
    n = max(1, round(ms / step_ms))
    return [(f"b{round(start + (end - start) * k / n)}", step_ms / 1000.0) for k in range(1, n + 1)]


def slice_db(x, n):
    fr = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)


def report(i, name, reps, floor_db, out, rate):
    """One line per test: the loudest 10ms slice and highest sample of each repeat."""
    cells = []
    for r in reps:
        x = r.astype(np.float64) / 32768
        loud = slice_db(x, rate // 100).max()
        peak = 20 * np.log10(np.abs(x).max() + 1e-9)
        cells.append(f"{loud - floor_db:+5.1f}/{peak:6.1f}")
    print(f"  {i:2d} {name:18s} " + "   ".join(cells), flush=True)
    with wave.open(str(out / f"{i}_{name.replace(', ', '_').replace(' ', '_')}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.concatenate(reps).astype(np.int16).tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=serial_link.PORT)
    ap.add_argument("--lead-in", type=float, default=10.0)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--gap", type=float, default=2.5)
    ap.add_argument("--only", help="comma-separated test numbers")
    ap.add_argument("--out", default="stt_samples/asleep_audition")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    catalog = load_catalog()
    tests = list(enumerate(build_tests(catalog), 1))
    if args.only:
        wanted = {int(n) for n in args.only.split(",")}
        tests = [t for t in tests if t[0] in wanted]

    if args.list:
        for i, (name, steps) in tests:
            print(f"{i:2d} {name}: " + "  ".join(f"{c or '-'} ({w:.2f}s)" for c, w in steps))
        return

    # Imported here so --list needs no audio libraries or models.
    from capture import RATE, Capture
    from playback import Playback
    from tts import TTS

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("Rendering spoken labels...", flush=True)
    tts = TTS(on_audio=lambda *a, **k: None)
    labels = {i: tts.synthesize(f"Test {i}. {name}.") for i, (name, _) in tests}

    print(f"Starting in {args.lead_in:g}s - keep the room quiet...", flush=True)
    time.sleep(args.lead_in)

    frames, tag = [], [None]
    cap = Capture(on_frame=lambda s, t: frames.append((tag[0], s)))
    player = Playback()
    writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port)
    writer.start()
    bird = motion_mod.Motion(writer, catalog=catalog, on_send=lambda c: None)
    cap.start()              # same order as coordinator.py: capture, then playback
    player.start()
    time.sleep(BOOT_S)

    def grab(t):
        chunks = [s for l, s in frames if l == t]
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)

    try:
        tag[0] = "quiet"
        time.sleep(QUIET_S)
        tag[0] = None
        quiet = grab("quiet").astype(np.float64) / 32768
        floor_db = float(np.median(slice_db(quiet, RATE // 100)))
        print(f"\nQuiet room: {floor_db:.1f} dBFS (10ms median)")
        print("Each repeat: loudest 10ms slice above quiet room (dB) / highest sample (dBFS)\n", flush=True)

        for i, (name, steps) in tests:
            tag[0] = ("label", i)
            player.play(labels[i])
            player.wait_played(timeout=15)
            time.sleep(0.3)
            tag[0] = None
            heard = grab(("label", i)).astype(np.float64) / 32768
            print(f"  (label {i}: mic peak {20 * np.log10(np.abs(heard).max() + 1e-9):.1f} dBFS)", flush=True)
            time.sleep(SETTLE_S)
            reps = []
            for r in range(args.reps):
                tag[0] = (i, r)
                for cmd, wait in steps:
                    if cmd:
                        writer.send_head(cmd)
                    time.sleep(wait)
                time.sleep(args.gap)
                tag[0] = None
                reps.append(grab((i, r)))
            report(i, name, reps, floor_db, out, RATE)
    finally:
        cap.stop()
        bird.stop()
        player.stop()
        writer.stop()
    print(f"\nAudio saved in {out}/")


if __name__ == "__main__":
    main()
