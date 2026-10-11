"""Re-runnable test for docs/tests.md: "Wake-word spotter mechanism".

Verifies WakeSpotter's own logic - turn-taking (ignore_until drops
frames without even calling the model), cooldown (a sustained high
score fires once, not every frame, and fires again once the cooldown
elapses) - with a fake model so those checks are deterministic and
don't depend on real detection accuracy. Also loads the real trained
models once and confirms silence scores near zero and never fires,
as a basic sanity check that the shipped .onnx files load and run.
Real accuracy/threshold calibration against real speech is separate,
deferred work (spec section 4.1, CLAUDE.md work-list item 9) - not
what this test is for.

Run: venv/bin/python tests/test_wakeword.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from wakeword import COOLDOWN_S, SLEEP_NAME, WAKE_NAME, WakeSpotter  # noqa: E402

FRAME = np.zeros(1280, dtype=np.int16)


class FakeModel:
    """Stands in for openwakeword.Model: returns fixed scores regardless
    of input, and ignores patience/threshold - those are the real
    Model's own job, not under test here."""

    def __init__(self, scores):
        self.scores = scores
        self.calls = 0

    def predict(self, x, patience=None, threshold=None):
        self.calls += 1
        return dict(self.scores)


def check_ignore_until_gates_frames():
    errors = []
    fake = FakeModel({WAKE_NAME: 0.9, SLEEP_NAME: 0.9})
    fired = []
    spotter = WakeSpotter(lambda: fired.append("wake"), lambda: fired.append("sleep"), model=fake)

    spotter.ignore_until(10.0)
    result = spotter.process(FRAME, 5.0)   # frame's end (5.0 + 0.08) is still before the deadline
    if result != {}:
        errors.append(f"frame before ignore_until deadline should be dropped, got {result!r}")
    if fake.calls != 0:
        errors.append("model.predict() should not be called on a dropped frame")
    if fired:
        errors.append(f"a dropped frame should never fire a detection, got {fired!r}")
    return errors


def check_cooldown_suppresses_repeat_fires():
    errors = []
    fake = FakeModel({WAKE_NAME: 0.9, SLEEP_NAME: 0.9})
    fired = []
    spotter = WakeSpotter(lambda: fired.append("wake"), lambda: fired.append("sleep"), model=fake)

    spotter.process(FRAME, 0.0)                     # first high score - should fire
    spotter.process(FRAME, 0.5)                      # still within cooldown - should not fire again
    spotter.process(FRAME, COOLDOWN_S + 0.1)          # cooldown elapsed - should fire again

    if fired.count("wake") != 2:
        errors.append(f"expected 2 wake fires (initial + after cooldown), got {fired.count('wake')} ({fired!r})")
    if fired.count("sleep") != 2:
        errors.append(f"expected 2 sleep fires (initial + after cooldown), got {fired.count('sleep')} ({fired!r})")
    return errors


def check_real_model_silence_is_quiet():
    errors = []
    fired = []
    spotter = WakeSpotter(lambda: fired.append("wake"), lambda: fired.append("sleep"))

    scores = {}
    for i in range(10):
        scores = spotter.process(FRAME, i * 0.08)

    if WAKE_NAME not in scores or SLEEP_NAME not in scores:
        errors.append(f"expected both model names in the returned scores, got {scores!r}")
    if scores.get(WAKE_NAME, 1.0) > 0.1 or scores.get(SLEEP_NAME, 1.0) > 0.1:
        errors.append(f"digital silence should score near zero on both models, got {scores!r}")
    if fired:
        errors.append(f"digital silence should never fire a detection, got {fired!r}")
    return errors


if __name__ == "__main__":
    errors = (check_ignore_until_gates_frames()
              + check_cooldown_suppresses_repeat_fires()
              + check_real_model_silence_is_quiet())
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: WakeSpotter gates on ignore_until, debounces via cooldown, "
          "and the real models load and stay quiet on silence")
