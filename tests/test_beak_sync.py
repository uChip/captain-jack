"""Re-runnable test for docs/tests.md: "Beak-sync".

Automatic, no hardware: checks the dBFS/envelope/beak-angle mapping
functions directly, that Playback's callback drives a SerialWriter with
a beak angle per block (opening for loud audio, resting closed for
silence) and does nothing when no serial_writer is set, and that
SerialWriter's latest-wins/time-release behavior is correct against a
fake clock.

This doesn't check the *alignment* between a block's dac_time and when
its sound actually leaves the speaker - that needs a person watching and
listening to the real bird. See docs/tests.md's "Beak-sync" entry for
that procedure (it reuses playback.py --beak, no separate script).

Run: venv/bin/python tests/test_beak_sync.py
"""

import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import playback  # noqa: E402
import serial_link  # noqa: E402

BLOCK = playback.BLOCK
RATE = playback.RATE


def run_callback(player, n_blocks, start_block=0):
    for i in range(start_block, start_block + n_blocks):
        buf = np.zeros((BLOCK, 2), dtype=np.int16)
        t = SimpleNamespace(outputBufferDacTime=i * BLOCK / RATE)
        player._callback(buf, BLOCK, t, None)


def check_mapping():
    errors = []
    if playback.beak_angle(playback.BEAK_FLOOR_DBFS) != playback.BEAK_RANGE:
        errors.append("floor dBFS should map to fully closed")
    if playback.beak_angle(playback.BEAK_CEIL_DBFS) != 0:
        errors.append("ceiling dBFS should map to fully open")
    if playback.beak_angle(playback.BEAK_FLOOR_DBFS - 20) != playback.BEAK_RANGE:
        errors.append("below floor should clamp to fully closed, not go negative")
    if playback.beak_angle(playback.BEAK_CEIL_DBFS + 20) != 0:
        errors.append("above ceiling should clamp to fully open, not go below 0")
    mid_angle = playback.beak_angle((playback.BEAK_FLOOR_DBFS + playback.BEAK_CEIL_DBFS) / 2)
    if not (20 <= mid_angle <= 40):
        errors.append(f"midpoint dBFS gave angle {mid_angle}, expected roughly half-open (~30)")
    return errors


def check_callback_drives_beak():
    errors = []
    sent = []   # (angle, dac_time)
    writer = SimpleNamespace(send_beak=lambda angle, t: sent.append((angle, t)))
    player = playback.Playback(serial_writer=writer)

    # Sustained loud audio (well above BEAK_CEIL_DBFS) across many blocks.
    loud = np.full(BLOCK * 20, 20000, dtype=np.int16)
    player.play(loud, "loud")
    run_callback(player, 20)

    if not sent:
        errors.append("no beak commands sent while serial_writer is set")
    elif sent[-1][0] > 10:
        errors.append(f"after sustained loud audio, beak should be nearly open, got b{sent[-1][0]}")
    dac_times = [t for _, t in sent]
    if dac_times != sorted(dac_times):
        errors.append("beak dac_times not monotonically increasing")

    # Queue now empty: silence should close the beak back down.
    sent.clear()
    run_callback(player, 20, start_block=20)
    if not sent or sent[-1][0] != playback.BEAK_RANGE:
        errors.append(f"after sustained silence, beak should rest fully closed, got {sent[-1:] or 'nothing'}")
    return errors


def check_no_serial_writer_is_a_noop():
    player = playback.Playback()   # serial_writer=None by default
    player.play(np.full(BLOCK, 20000, dtype=np.int16), "x")
    run_callback(player, 3)        # must not raise
    return []


def check_serial_writer_latest_wins_and_timing():
    errors = []
    sent = []
    clock = [0.0]
    writer = serial_link.SerialWriter(now_fn=lambda: clock[0], dry_run=True,
                                       on_send=lambda cmd: sent.append((cmd, clock[0])))
    writer.start()
    try:
        writer.send_beak(10, dac_time=1.0)
        writer.send_beak(20, dac_time=1.0)   # supersedes b10 before either is due
        time.sleep(0.1)
        if sent:
            errors.append(f"sent before dac_time arrived: {sent}")

        clock[0] = 1.0
        time.sleep(0.1)
        if sent != [("b20", 1.0)]:
            errors.append(f"expected only the latest value (b20), got {sent}")
    finally:
        writer.stop()
    return errors


if __name__ == "__main__":
    errors = (check_mapping() + check_callback_drives_beak()
              + check_no_serial_writer_is_a_noop() + check_serial_writer_latest_wins_and_timing())
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: beak mapping, envelope, callback wiring, and SerialWriter latest-wins/timing correct")
