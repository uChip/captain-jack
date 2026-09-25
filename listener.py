"""Captain Jack listener: turns the mic's frame stream into utterances.

Implements the Listener thread from docs/specification.md section 4.16(b),
build step 3 (On Watch half): runs Silero VAD over Capture's 80ms frames
and assembles one complete utterance at a time - from a short pre-roll
before speech starts until speech has clearly ended - handing each to
on_utterance. The wake-word half (openWakeWord, Off Watch/Asleep) is
build step 7.

Turn-taking (spec 4.16): ignore_until(t) makes the Listener discard any
frame captured before stream time t, and abandon any utterance in
progress. The Coordinator sets it from Playback's events, so Jack never
listens to himself.

Run standalone to print transcripts of whatever is said to the bird,
optionally saving each utterance as a numbered .wav in a folder. It
beeps through the bird's speaker when it starts listening:
    venv/bin/python listener.py [--model base.en] [--save DIR]
"""

import collections
import queue
import sys
import threading
import wave
from pathlib import Path

import numpy as np
import onnxruntime as ort

from capture import Capture
from playback import Playback
from stt import MODELS_DIR, RATE, STT

VAD_MODEL = MODELS_DIR / "silero_vad.onnx"
VAD_WINDOW = 512        # Silero VAD v5 takes 512-sample (32ms) windows at 16kHz...
VAD_CONTEXT = 64        # ...plus the previous window's last 64 samples

# End-pointing - Silero's own defaults and common live-use values as the
# starting point, to be tuned on real household speech (spec 4.2's
# methodology).
SPEECH_THRESHOLD = 0.5      # window counts as speech at or above this
SILENCE_THRESHOLD = 0.35    # ...and as silence below this (hysteresis between)
MIN_SPEECH_MS = 250         # this much consecutive speech starts an utterance
END_SILENCE_MS = 700        # this much silence ends it
PRE_ROLL_MS = 300           # kept from before the start, so the first syllable isn't lost
MAX_UTTERANCE_S = 30        # whisper.cpp's window limit

# Turn-taking (spec 4.16): after playback ends, keep ignoring the mic this
# long so room echo of Jack's own voice isn't heard as speech. Starting
# point, to be tuned.
HOLDOFF_S = 0.3


def ms_to_windows(ms):
    return max(1, round(ms / 1000 * RATE / VAD_WINDOW))


class SileroVAD:
    def __init__(self):
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(str(VAD_MODEL), opts, providers=["CPUExecutionProvider"])
        self.sr = np.array(RATE, dtype=np.int64)
        self.reset()

    def reset(self):
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros(VAD_CONTEXT, dtype=np.float32)

    def prob(self, window: np.ndarray) -> float:
        """Speech probability for one 512-sample int16 window."""
        x = np.concatenate([self.context, window.astype(np.float32) / 32768])
        self.context = x[-VAD_CONTEXT:]
        out, self.state = self.session.run(
            None, {"input": x[np.newaxis, :], "state": self.state, "sr": self.sr})
        return float(out[0, 0])


class Listener:
    """Consumes Capture frames; calls on_utterance(samples, start_time).

    on_utterance runs on the Listener's own thread, so it may take a
    moment (e.g. queue the utterance for STT) but shouldn't block long.
    """

    def __init__(self, on_utterance):
        self.on_utterance = on_utterance
        self.vad = SileroVAD()
        self._frames = queue.Queue()
        self._ignore_until = 0.0
        self._thread = None
        self._running = False
        self._pending = np.zeros(0, dtype=np.int16)   # samples not yet a full VAD window
        self._pending_t = 0.0
        self._pre_roll = collections.deque(maxlen=ms_to_windows(PRE_ROLL_MS) + ms_to_windows(MIN_SPEECH_MS))
        self._reset_utterance()

    # --- called from other threads ---

    def feed(self, samples, adc_time):
        """Capture's on_frame callback: just queue the frame."""
        self._frames.put((samples, adc_time))

    def ignore_until(self, t):
        """Discard frames captured before stream time t (turn-taking).

        Replaces any earlier setting, so the Coordinator can go deaf with
        float("inf") when playback starts, then set the real end time when
        it finishes.
        """
        self._ignore_until = t

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, name="listener", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    # --- Listener thread ---

    def _run(self):
        while self._running:
            try:
                samples, adc_time = self._frames.get(timeout=0.2)
            except queue.Empty:
                continue
            self.process(samples, adc_time)

    def process(self, samples, adc_time):
        """Handle one frame. Public so tests can drive it without a thread."""
        if adc_time + len(samples) / RATE <= self._ignore_until:
            self._reset_all()
            return
        if not len(self._pending):
            self._pending_t = adc_time
        self._pending = np.concatenate([self._pending, samples])
        while len(self._pending) >= VAD_WINDOW:
            window = self._pending[:VAD_WINDOW]
            window_t = self._pending_t
            self._pending = self._pending[VAD_WINDOW:]
            self._pending_t += VAD_WINDOW / RATE
            self._step(window, window_t, self.vad.prob(window))

    def _step(self, window, t, prob):
        if not self._in_speech:
            self._pre_roll.append((window, t))
            self._speech_run = self._speech_run + 1 if prob >= SPEECH_THRESHOLD else 0
            if self._speech_run >= ms_to_windows(MIN_SPEECH_MS):
                self._in_speech = True
                self._windows = [w for w, _ in self._pre_roll]
                self._start_t = self._pre_roll[0][1]
                self._pre_roll.clear()
            return

        self._windows.append(window)
        if prob < SILENCE_THRESHOLD:
            self._silence_run += 1
        elif prob >= SPEECH_THRESHOLD:
            self._silence_run = 0
        too_long = len(self._windows) * VAD_WINDOW >= MAX_UTTERANCE_S * RATE
        if self._silence_run >= ms_to_windows(END_SILENCE_MS) or too_long:
            utterance = np.concatenate(self._windows)
            start_t = self._start_t
            self._reset_utterance()
            self.vad.reset()
            self.on_utterance(utterance, start_t)

    def _reset_utterance(self):
        self._in_speech = False
        self._windows = []
        self._start_t = 0.0
        self._speech_run = 0
        self._silence_run = 0

    def _reset_all(self):
        self._reset_utterance()
        self._pre_roll.clear()
        self._pending = np.zeros(0, dtype=np.int16)
        self.vad.reset()


def main():
    args = sys.argv[1:]
    model = args[args.index("--model") + 1] if "--model" in args else None
    save_dir = Path(args[args.index("--save") + 1]) if "--save" in args else None
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
    stt = STT(model) if model else STT()
    utterances = queue.Queue()

    listener = Listener(on_utterance=lambda s, t: utterances.put(s))

    def on_playback(kind, tag, dac_time):
        if kind == "started":
            listener.ignore_until(float("inf"))     # deaf while anything plays...
        else:
            listener.ignore_until(dac_time + HOLDOFF_S)   # ...until just after it ends

    player = Playback(on_event=on_playback)
    capture = Capture(on_frame=listener.feed)
    listener.start()
    capture.start()
    player.start()
    beep = (np.sin(2 * np.pi * 880 * np.arange(int(0.15 * RATE)) / RATE) * 16000).astype(np.int16)
    player.play(beep, "start beep")
    print(f"Listening (whisper {stt.model_name}) after the beep. Speak to the bird; Ctrl+C to quit.")
    count = 0
    try:
        while True:
            samples = utterances.get()
            count += 1
            t = stt.transcribe(samples)
            verdict = repr(t.text) if t.accepted else f"(rejected: {t.raw!r})"
            print(f"  {count:2d} [{t.audio_s:4.1f}s audio, {t.stt_s:.2f}s stt] {verdict}", flush=True)
            if save_dir:
                with wave.open(str(save_dir / f"utt{count:02d}.wav"), "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(RATE)
                    w.writeframes(samples.tobytes())
    except KeyboardInterrupt:
        pass
    finally:
        capture.stop()
        player.stop()
        listener.stop()
        if capture.overflows:
            print(f"WARNING: {capture.overflows} input overflow(s)")


if __name__ == "__main__":
    main()
