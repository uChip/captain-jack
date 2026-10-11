"""Captain Jack wake-word spotter: the real-time counterpart of the
Enter/`sleep` keyboard stand-ins in coordinator.py.

Implements the remaining piece of CLAUDE.md work-list item 9: runs
openWakeWord's own bundled feature pipeline (melspectrogram + embedding
model, both onnx, shipped inside the `openwakeword` package - no
download step needed) over Capture's 80ms frames, feeding the two
custom classifiers trained in docs/log.md's 4.1 history
(`wake_phrase.onnx`, `sleep_phrase.onnx`). On a detection, calls
on_wake()/on_sleep() - decided 2026-10-11 to be the exact same calls
Coordinator's keyboard stand-ins already make (coord.wake() /
coord.sleep_phrase()), not a parallel code path, so both ways of
triggering a mode change always funnel into one place.

ignore_until(t) mirrors Listener's turn-taking gate (same stream clock,
same semantics) - Coordinator sets it from Playback's events so Jack's
own voice (replies, idle clips, settle-in lines) can't trigger himself.

Run standalone to print live scores as you speak to the bird (say
"Ahoy, Captain Jack" or "Goodnight, Jack" to see a detection fire):
    venv/bin/python wakeword.py
"""

import queue
import sys
import threading
import time
from pathlib import Path

from openwakeword.model import Model

from capture import RATE, Capture

WAKE_MODEL = Path(__file__).parent / "wake_phrase.onnx"
SLEEP_MODEL = Path(__file__).parent / "sleep_phrase.onnx"
WAKE_NAME = WAKE_MODEL.stem
SLEEP_NAME = SLEEP_MODEL.stem

# openWakeWord's own documented default - spec 4.1's decided starting
# point for both phrases. Still needs real household audio to calibrate
# a final number (spec 4.1's methodology: wake biased stricter than this
# default since a false wake is the more disruptive failure; sleep stays
# at the vanilla default). Not yet done - see CLAUDE.md work-list item 9.
WAKE_THRESHOLD = 0.5
SLEEP_THRESHOLD = 0.5

# How many consecutive 80ms frames must clear the threshold before a
# detection counts - openWakeWord's own `patience` knob (trades a little
# latency for fewer false positives). Starting point, not measured.
PATIENCE_FRAMES = 3

# Once a phrase fires, ignore further detections of the same phrase for
# this long - one utterance of the phrase shouldn't fire more than once
# while its own score stays elevated. Starting point, not measured.
COOLDOWN_S = 2.0

# Debug visibility floor (see on_score=): report any score above this,
# well below WAKE_THRESHOLD/SLEEP_THRESHOLD, so a near-miss (scored but
# didn't cross threshold) is visible instead of indistinguishable from
# "never heard anything at all."
REPORT_FLOOR = 0.1


class WakeSpotter:
    """Consumes Capture frames; calls on_wake()/on_sleep() on detection.

    feed(samples, adc_time) is Capture's on_frame callback shape, so it
    fans out alongside Listener.feed in Coordinator. Runs model
    inference on its own thread, same pattern as Listener.
    """

    def __init__(self, on_wake, on_sleep, model=None, on_score=None):
        self.on_wake = on_wake
        self.on_sleep = on_sleep
        self.on_score = on_score   # optional debug hook: on_score(scores) above REPORT_FLOOR
        self.model = model or Model(wakeword_model_paths=[str(WAKE_MODEL), str(SLEEP_MODEL)])
        self._frames = queue.Queue()
        self._ignore_until = 0.0
        self._thread = None
        self._running = False
        self._last_fired = {WAKE_NAME: float("-inf"), SLEEP_NAME: float("-inf")}
        self.last_scores = {WAKE_NAME: 0.0, SLEEP_NAME: 0.0}   # latest, for the CLI readout below

    # --- called from other threads ---

    def feed(self, samples, adc_time):
        self._frames.put((samples, adc_time))

    def ignore_until(self, t):
        """Discard frames captured before stream time t (turn-taking) -
        same semantics as Listener.ignore_until."""
        self._ignore_until = t

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, name="wakeword", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    # --- spotter thread ---

    def _run(self):
        while self._running:
            try:
                samples, adc_time = self._frames.get(timeout=0.2)
            except queue.Empty:
                continue
            self.process(samples, adc_time)

    def process(self, samples, adc_time) -> dict:
        """Handle one frame; returns the raw scores dict (mostly for the
        standalone CLI below). Public so tests can drive it without a
        thread."""
        if adc_time + len(samples) / RATE <= self._ignore_until:
            return {}
        scores = self.model.predict(
            samples,
            patience={WAKE_NAME: PATIENCE_FRAMES, SLEEP_NAME: PATIENCE_FRAMES},
            threshold={WAKE_NAME: WAKE_THRESHOLD, SLEEP_NAME: SLEEP_THRESHOLD},
        )
        self.last_scores = scores   # set before firing, so on_wake/on_sleep see the real trigger value
        if self.on_score and (scores[WAKE_NAME] > REPORT_FLOOR or scores[SLEEP_NAME] > REPORT_FLOOR):
            self.on_score(scores)
        if (scores[WAKE_NAME] >= WAKE_THRESHOLD
                and adc_time - self._last_fired[WAKE_NAME] >= COOLDOWN_S):
            self._last_fired[WAKE_NAME] = adc_time
            self.on_wake()
        if (scores[SLEEP_NAME] >= SLEEP_THRESHOLD
                and adc_time - self._last_fired[SLEEP_NAME] >= COOLDOWN_S):
            self._last_fired[SLEEP_NAME] = adc_time
            self.on_sleep()
        return scores


def main():
    def on_wake():
        print(f"\n  >>> WAKE  ({WAKE_NAME}) detected <<<", flush=True)

    def on_sleep():
        print(f"\n  >>> SLEEP ({SLEEP_NAME}) detected <<<", flush=True)

    spotter = WakeSpotter(on_wake, on_sleep)
    capture = Capture(on_frame=spotter.feed)
    print(f"Loaded {WAKE_NAME!r}/{SLEEP_NAME!r}. Speak to the bird; Ctrl+C to quit.")
    capture.start()
    spotter.start()
    try:
        while True:
            time.sleep(0.5)
            s = spotter.last_scores
            print(f"\r  wake={s.get(WAKE_NAME, 0.0):.2f}  sleep={s.get(SLEEP_NAME, 0.0):.2f}   ",
                  end="", flush=True)
    except KeyboardInterrupt:
        print()
    finally:
        capture.stop()
        spotter.stop()
        if capture.overflows:
            print(f"WARNING: {capture.overflows} input overflow(s)")


if __name__ == "__main__":
    sys.exit(main())
