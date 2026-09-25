"""Captain Jack coordinator: mode state and the On Watch conversation turn.

Implements the Coordinator from docs/specification.md section 4.16(c),
build step 4: wires Capture -> Listener -> STT -> the orchestrator's
take_turn() -> Jack's reply, with Playback's events driving the
Listener's turn-taking gate. Replies are printed; speaking them is build
step 5 (TTS).

Modes, as far as this step goes: Off Watch (waiting for the wake word)
and On Watch (conversing). The real wake word is build step 7; until
then pressing Enter stands in for it, posting the same "wake" event. A
beep through the bird marks the start of listening. On Watch ends after
ON_WATCH_TIMEOUT_S with no accepted utterance (spec 4.11); the
end-session and nap meta-tags aren't implemented in orchestrate.py yet.

Run (in its own terminal - it reads the keyboard):
    venv/bin/python coordinator.py [--model base.en] [--scratch-memory]
--scratch-memory runs against a temporary copy of memory/, so test
conversations can't add facts to the real memory.md.
"""

import queue
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import anthropic
import numpy as np

from capture import Capture
from listener import HOLDOFF_S, Listener
from orchestrate import MEMORY_DIR, household_names, take_turn
from playback import RATE, Playback
from stt import STT, names_prompt

ON_WATCH_TIMEOUT_S = 120    # spec 4.11: 2 minutes with no prompt -> Off Watch

# Stand-in for the in-character "say again" clip (spec 4.2) until TTS exists.
DIDNT_CATCH = "(Jack didn't catch that - say again)"


def beep() -> np.ndarray:
    t = np.arange(int(0.15 * RATE)) / RATE
    return (np.sin(2 * np.pi * 880 * t) * 16000).astype(np.int16)


class Coordinator:
    def __init__(self, memory_dir=MEMORY_DIR, model=None, client=None, out=print):
        self.memory_dir = Path(memory_dir)
        self.client = client or anthropic.Anthropic()
        prompt = names_prompt(household_names(self.memory_dir))
        self.stt = STT(model, prompt) if model else STT(prompt=prompt)
        self.out = out
        self.events = queue.Queue()
        self.mode = "off_watch"
        self.history = []
        self.deadline = None        # On Watch timeout, monotonic time

        self.listener = Listener(on_utterance=lambda s, t: self.events.put(("utterance", s)))
        self.player = Playback(on_event=self._on_playback)
        self.capture = Capture(on_frame=self.listener.feed)

    # --- event sources (other threads) ---

    def _on_playback(self, kind, tag, dac_time):
        # Turn-taking: deaf while anything plays, until just after it ends.
        if kind == "started":
            self.listener.ignore_until(float("inf"))
        else:
            self.listener.ignore_until(dac_time + HOLDOFF_S)

    def wake(self):
        """Wake-word stand-in: same event the real spotter will post."""
        self.events.put(("wake", None))

    # --- Coordinator (main thread) ---

    def run(self):
        self.listener.start()
        self.capture.start()
        self.player.start()
        try:
            while True:
                timeout = None
                if self.mode == "on_watch":
                    timeout = max(0.0, self.deadline - time.monotonic())
                try:
                    kind, data = self.events.get(timeout=timeout)
                except queue.Empty:
                    self.end_session("no prompt for 2 minutes")
                    continue
                if kind == "wake" and self.mode == "off_watch":
                    self.start_session()
                elif kind == "utterance" and self.mode == "on_watch":
                    self.handle_utterance(data)
                # utterances while Off Watch are ignored: no wake word yet
        finally:
            self.capture.stop()
            self.player.stop()
            self.listener.stop()

    def start_session(self):
        self.mode = "on_watch"
        self.history = []
        self.player.play(beep(), "listening beep")
        self.deadline = time.monotonic() + ON_WATCH_TIMEOUT_S
        self.out("[On Watch - speak to Jack]")

    def end_session(self, why):
        self.mode = "off_watch"
        self.deadline = None
        self.out(f"[Off Watch - {why}. Press Enter to wake Jack.]")

    def handle_utterance(self, samples):
        heard = self.stt.transcribe(samples)
        if not heard.accepted:
            self.out(f"  {DIDNT_CATCH}   [stt {heard.stt_s:.2f}s, raw {heard.raw!r}]")
            self.deadline = time.monotonic() + ON_WATCH_TIMEOUT_S
            return
        self.out(f"You:  {heard.text}   [{heard.audio_s:.1f}s audio, stt {heard.stt_s:.2f}s]")

        start = time.monotonic()
        try:
            turn = take_turn(self.client, self.history, heard.text, self.memory_dir)
        except anthropic.APIError as e:
            self.out(f"  [error reaching Haiku: {e}]")
            return
        self.out(f"Jack: {turn.spoken}   [haiku {time.monotonic() - start:.2f}s]")
        if turn.saved:
            self.out(f"  [memory saved - {turn.saved}]")
        # Spec 4.11: the timeout clock starts when Jack's reply finishes.
        # Replies aren't spoken until build step 5, so that's now.
        self.deadline = time.monotonic() + ON_WATCH_TIMEOUT_S


def scratch_memory_copy() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="jack-memory-"))
    for name in ("identity.md", "memory.md"):
        shutil.copy(MEMORY_DIR / name, scratch / name)
    return scratch


def main():
    args = sys.argv[1:]
    model = args[args.index("--model") + 1] if "--model" in args else None
    memory_dir = MEMORY_DIR
    if "--scratch-memory" in args:
        memory_dir = scratch_memory_copy()
        print(f"Using a scratch copy of memory: {memory_dir}")

    coord = Coordinator(memory_dir, model)

    def keyboard():
        for _ in sys.stdin:
            coord.wake()

    threading.Thread(target=keyboard, name="keyboard", daemon=True).start()
    print(f"Whisper {coord.stt.model_name}. Press Enter to wake Jack; Ctrl+C to quit.")
    try:
        coord.run()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
