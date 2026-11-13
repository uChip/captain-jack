"""Re-runnable test for docs/tests.md: "Asleep sequence, live wiring".

Manual, on the real bird, in a quiet room. Written 2026-11-13: the Asleep
clack never showed in tests/audition_asleep.py, which sends gestures with
nothing else running. This runs Asleep the way coordinator.py does -
Playback's stream open with beak-sync wired to the Serial writer, Motion
in Asleep - records the mic throughout, and lists every loud moment
against the gesture running at the time.

Found with it: the open stream's beak-sync sent "closed" every 20ms even
in silence, snapping shut every gesture's beak move (fixed in
playback.py). --old-beak-sync puts that behavior back, to compare.

Needs the serial port and audio device, so stop the service first:
    sudo systemctl stop captain-jack

Run: venv/bin/python tests/asleep_sequence.py
         [--seconds 180] [--extra-chance 0.5] [--old-beak-sync]
         [--threshold 15] [--lead-in 10] [--port /dev/ttyUSB0]
         [--out stt_samples/asleep_sequence]

--extra-chance raises how often a snore/snort/twitch follows a breath
(live: motion.ASLEEP_EXTRA_CHANCE), so a few minutes covers them all.
--threshold: dB above the quiet room that counts as a loud moment.
"""

import argparse
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import motion as motion_mod  # noqa: E402
import serial_link  # noqa: E402
from capture import Capture  # noqa: E402
from playback import Playback  # noqa: E402

RATE = 16000
BOOT_S = 6.0     # SerialWriter waits out the Arduino's boot before sending
QUIET_S = 4.0    # room level, before anything moves
SLICE = RATE // 100


class OldBeakSync(Playback):
    """Beak-sync as it was before 2026-11-13: sends every block, forever."""

    @property
    def _beak_active(self):
        return True

    @_beak_active.setter
    def _beak_active(self, value):
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=serial_link.PORT)
    ap.add_argument("--seconds", type=float, default=180.0)
    ap.add_argument("--extra-chance", type=float, default=0.5)
    ap.add_argument("--old-beak-sync", action="store_true")
    ap.add_argument("--threshold", type=float, default=15.0)
    ap.add_argument("--lead-in", type=float, default=10.0)
    ap.add_argument("--out", default="stt_samples/asleep_sequence")
    args = ap.parse_args()

    motion_mod.ASLEEP_EXTRA_CHANCE = args.extra_chance
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    wav_path = out / ("old_beak_sync.wav" if args.old_beak_sync else "fixed.wav")

    print(f"Starting in {args.lead_in:g}s - keep the room quiet...", flush=True)
    time.sleep(args.lead_in)

    chunks = []
    cap = Capture(on_frame=lambda s, t: chunks.append(s))
    player = (OldBeakSync if args.old_beak_sync else Playback)()
    writer = serial_link.SerialWriter(now_fn=player.now, port=args.port)
    player.serial_writer = writer
    bird = motion_mod.Motion(writer, player=player, on_send=lambda c: None)

    gestures = []   # (start, end, id), seconds since the recording started
    t0 = [None]
    real_play = bird.play_gesture

    def logged_play(g):
        start = time.monotonic() - t0[0]
        print(f"  {start:7.2f}s  {g['id']}", flush=True)
        real_play(g)
        gestures.append((start, time.monotonic() - t0[0], g["id"]))

    bird.play_gesture = logged_play

    writer.start()
    cap.start()          # same order as coordinator.py: capture, then playback
    t0[0] = time.monotonic()
    player.start()
    time.sleep(BOOT_S)
    quiet_from = len(chunks)
    time.sleep(QUIET_S)
    quiet_to = len(chunks)

    mode = "OLD beak-sync (bug back in)" if args.old_beak_sync else "fixed beak-sync"
    print(f"Asleep for {args.seconds:g}s, {mode}, extra chance {args.extra_chance:g}:", flush=True)
    bird.start()
    bird.fall_asleep()
    try:
        time.sleep(args.seconds)
    finally:
        bird.stop()
        time.sleep(1.0)
        cap.stop()
        player.stop()
        writer.stop()

    audio = np.concatenate(chunks)
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(audio.astype(np.int16).tobytes())

    x = audio.astype(np.float64) / 32768
    n = len(x) // SLICE
    db = 20 * np.log10(np.sqrt((x[:n * SLICE].reshape(n, SLICE) ** 2).mean(1)) + 1e-9)
    q_lo = sum(len(c) for c in chunks[:quiet_from]) // SLICE
    q_hi = sum(len(c) for c in chunks[:quiet_to]) // SLICE
    floor = float(np.median(db[q_lo:q_hi]))
    print(f"\nQuiet room {floor:.1f} dBFS. Loud moments (>= +{args.threshold:g} dB, 10ms slices):")

    events, i = [], q_hi
    while i < n:
        if db[i] >= floor + args.threshold:
            j = i
            while j < n and db[j] >= floor + args.threshold - 6:
                j += 1
            events.append((i / 100, float(db[i:j].max()) - floor))
            i = j + 5
        else:
            i += 1
    for t, peak in events:
        during = [g for g in gestures if g[0] - 0.1 <= t <= g[1] + 0.1]
        where = ", ".join(f"{gid} +{t - s:.2f}s" for s, _, gid in during) or "between gestures"
        print(f"  {t:7.2f}s  +{peak:4.1f} dB  {where}")
    counts = {}
    for _, _, gid in gestures:
        counts[gid] = counts.get(gid, 0) + 1
    print(f"\n{len(events)} loud moments; gestures played: "
          + ", ".join(f"{k} x{v}" for k, v in sorted(counts.items())))
    print(f"Audio saved as {wav_path}")


if __name__ == "__main__":
    main()
