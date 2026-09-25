"""Re-runnable test for docs/tests.md: "Capture thread".

Part 1 (automatic, no hardware): drives Capture's audio callback directly
with a fake 2-channel buffer and checks it keeps the right channel, as a
mono 80ms frame, passing the ADC timestamp through.

Part 2 (--live, needs the XVF3800 plugged in; no person needed): records
3 seconds from the real device and checks frame size and count, evenly
spaced timestamps, no input overflows, and a live signal (not all zeros).

Run: venv/bin/python tests/test_capture.py [--live]
"""

import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import capture  # noqa: E402

FRAME = capture.FRAME
FRAME_S = FRAME / capture.RATE


def check_callback():
    errors = []
    got = []
    cap = capture.Capture(on_frame=lambda s, t: got.append((s, t)))
    fake = np.zeros((FRAME, 2), dtype=np.int16)
    fake[:, 0] = 111
    fake[:, 1] = 222
    status = SimpleNamespace(input_overflow=False)
    cap._callback(fake, FRAME, SimpleNamespace(inputBufferAdcTime=12.5), status)

    if len(got) != 1:
        return [f"expected 1 frame delivered, got {len(got)}"]
    samples, t = got[0]
    want = 222 if capture.CAPTURE_CHANNEL == 1 else 111
    if samples.shape != (FRAME,):
        errors.append(f"frame shape {samples.shape}, expected ({FRAME},)")
    if not (samples == want).all():
        errors.append(f"frame isn't channel {capture.CAPTURE_CHANNEL}")
    if t != 12.5:
        errors.append(f"adc_time {t}, expected 12.5")
    fake[:, 1] = 0      # the delivered frame must be a copy, not a view
    if not (samples == want).all():
        errors.append("delivered frame shares memory with the device buffer")
    return errors


def check_live():
    errors = []
    got = []
    cap = capture.Capture(on_frame=lambda s, t: got.append((s, t)))
    cap.start()
    try:
        time.sleep(3.0)
    finally:
        cap.stop()

    expected = 3.0 / FRAME_S
    if abs(len(got) - expected) > 3:
        errors.append(f"got {len(got)} frames in 3s, expected about {expected:.0f}")
    if any(s.shape != (FRAME,) for s, _ in got):
        errors.append("a frame had the wrong shape")
    gaps = np.diff([t for _, t in got])
    if len(gaps) and not np.allclose(gaps, FRAME_S, atol=0.005):
        errors.append(f"frame timestamps not evenly spaced: {gaps.min():.4f}-{gaps.max():.4f}s")
    if cap.overflows:
        errors.append(f"{cap.overflows} input overflow(s)")
    if got and not np.concatenate([s for s, _ in got]).any():
        errors.append("all samples zero - mic not delivering signal")
    return errors


if __name__ == "__main__":
    errors = check_callback()
    live = "--live" in sys.argv[1:]
    if live and not errors:
        errors = check_live()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: capture keeps channel", capture.CAPTURE_CHANNEL,
          "as mono 80ms frames" + (", live stream healthy" if live else ""))
