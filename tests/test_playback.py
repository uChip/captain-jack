"""Re-runnable test for docs/tests.md: "Playback thread".

Part 1 (automatic, no hardware): drives Playback's audio callback
directly with fake output buffers and checks the output gain cap, the
mono->2ch duplication, gapless back-to-back items, silence when idle,
and started/finished event order.

Part 2 (--listen, needs a person at the bird): plays two real clips
back to back through the XVF3800 and checks the events arrive in order
with the expected total duration.

Run: venv/bin/python tests/test_playback.py [--listen]
"""

import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import playback  # noqa: E402

BLOCK = playback.BLOCK


def run_callback(player, n_blocks):
    """Pull n_blocks of output through the callback, as PortAudio would."""
    out = []
    for i in range(n_blocks):
        buf = np.zeros((BLOCK, 2), dtype=np.int16)
        t = SimpleNamespace(outputBufferDacTime=i * BLOCK / playback.RATE)
        player._callback(buf, BLOCK, t, None)
        out.append(buf)
    return np.concatenate(out)


def check_callback():
    errors = []
    events = []
    player = playback.Playback(on_event=lambda k, tag, t: events.append((k, tag, t)))

    # Two items whose lengths don't line up with block boundaries, so the
    # hand-off from one to the next happens mid-block.
    a = np.full(500, 30000, dtype=np.int16)
    b = np.full(700, -20000, dtype=np.int16)
    player.play(a, "a")
    player.play(b, "b")
    out = run_callback(player, 5)       # 1600 frames: 1200 of audio, then silence

    if not np.array_equal(out[:, 0], out[:, 1]):
        errors.append("left and right channels differ - mono not duplicated")
    gain = 10 ** (playback.OUTPUT_GAIN_DB / 20)
    want_a, want_b = int(30000 * gain), int(-20000 * gain)
    left = out[:, 0]
    if not (left[:500] == want_a).all():
        errors.append(f"item a not at gain-capped level {want_a}")
    if not (left[500:1200] == want_b).all():
        errors.append(f"item b not at gain-capped level {want_b} or not gapless after a")
    if left[1200:].any():
        errors.append("output not silent after the queue ran dry")

    kinds = [(k, tag) for k, tag, _ in events]
    if kinds != [("started", "a"), ("finished", "a"), ("started", "b"), ("finished", "b")]:
        errors.append(f"event order wrong: {kinds}")
    else:
        rate = playback.RATE
        times = [t for _, _, t in events]
        expected = [0, 500 / rate, 500 / rate, 1200 / rate]
        if not np.allclose(times, expected):
            errors.append(f"event dac_times {times}, expected {expected}")
    if not player.wait_idle(timeout=0):
        errors.append("wait_idle() not set after everything played")
    return errors


def check_listen():
    errors = []
    clips = [playback.WAV_DIR / "IllBeBack.wav", playback.WAV_DIR / "MayGodBless.wav"]
    expected_s = sum(len(playback.load_wav(c)) for c in clips) / playback.RATE
    events = []
    player = playback.Playback(on_event=lambda k, tag, t: events.append((k, tag, t)))
    player.start()
    try:
        for c in clips:
            player.play_file(c)
        if not player.wait_idle(timeout=expected_s + 5):
            errors.append("playback never went idle")
        while events and player.now() < events[-1][2]:
            time.sleep(0.02)
    finally:
        player.stop()
    kinds = [(k, tag) for k, tag, _ in events]
    want = [("started", clips[0].name), ("finished", clips[0].name),
            ("started", clips[1].name), ("finished", clips[1].name)]
    if kinds != want:
        errors.append(f"event order wrong: {kinds}")
    else:
        played_s = events[-1][2] - events[0][2]
        if abs(played_s - expected_s) > 0.05:
            errors.append(f"played {played_s:.3f}s, expected {expected_s:.3f}s")
    return errors


if __name__ == "__main__":
    errors = check_callback()
    if "--listen" in sys.argv[1:] and not errors:
        print("Playing IllBeBack.wav then MayGodBless.wav back to back...")
        errors = check_listen()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: playback gain cap, mono->2ch, gapless queue, and events correct")
    if "--listen" in sys.argv[1:]:
        print("Listener check: both clips clean, no gap or click between them?")
