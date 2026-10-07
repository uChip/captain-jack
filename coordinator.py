"""Captain Jack coordinator: the full Sleep-Mode State Machine (spec 4.11).

Implements the Coordinator from docs/specification.md section 4.16(c),
build step 7: wires Capture -> Listener -> STT -> the orchestrator's
take_turn() -> TTS -> Playback, with Playback's events driving the
Listener's turn-taking gate, and (when --port/--dry-run is given) the
Serial writer + Motion & idle thread for beak-sync and ambient gestures.
Replies are spoken sentence by sentence (and printed).

Three modes: Off Watch (idle, waiting for the wake phrase), On Watch
(conversing), Asleep (napping, woken only by the wake phrase). The real
wake-word spotter is still pending (needs trained openWakeWord models,
GPU-blocked - see CLAUDE.md); until then pressing Enter stands in for
"Ahoy, Captain Jack" (-> On Watch from Off Watch or Asleep) and typing
"sleep" then Enter stands in for "Goodnight, Jack" (Off Watch -> Asleep
only - the local spotter never needs to listen for it while already On
Watch or Asleep, per spec 4.11). A beep through the bird marks the start
of listening. Transitions:
  - On Watch -> Off Watch or Asleep: Haiku's own MODE: meta-tag
    (END_SESSION/NAP, see orchestrate.py), applied once the reply
    finishes playing - or the 2-minute no-prompt timeout (-> Off Watch).
  - Off Watch -> Asleep: the sleep-phrase stand-in above, or a
    15-minute no-wake timeout.
Timeouts are spec 4.11's initial, not-yet-tuned numbers.

Run (in its own terminal - it reads the keyboard):
    venv/bin/python coordinator.py [--model base.en] [--voice bm_fable]
                                   [--scratch-memory] [--wake-after SECONDS]
                                   [--save DIR] [--port /dev/ttyUSB0] [--dry-run]
--scratch-memory runs against a temporary copy of memory/, so test
conversations can't add facts to the real memory.md. --wake-after wakes
Jack automatically that many seconds after starting, for runs with no
keyboard (e.g. launched in the background). --save writes every
utterance heard to DIR as a numbered .wav, for diagnosing mishearings.
--port opens the Arduino for beak-sync + ambient motion (omit to run
voice-only, as before); --dry-run drives the same Motion/Serial wiring
without a real port, for testing it when no Arduino is attached.
"""

import queue
import shutil
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

import anthropic
import numpy as np

import serial_link
from capture import Capture
from listener import HOLDOFF_S, Listener
from motion import Motion
from orchestrate import MEMORY_DIR, household_names, take_turn
from playback import RATE, Playback
from stt import STT, names_prompt
from tts import TTS, split_sentences

ON_WATCH_TIMEOUT_S = 120       # spec 4.11: 2 minutes with no prompt -> Off Watch
OFF_WATCH_TIMEOUT_S = 15 * 60  # spec 4.11: 15 minutes with no wake phrase -> Asleep

# Spec 4.2: a rejected utterance gets an in-character prompt, not silence.
DIDNT_CATCH = "Arr, didn't catch that over the wind. Say again?"

# Distinct from any (reply, sentence) tag, so _on_playback can tell the
# listening beep apart from a spoken reply.
BEEP_TAG = "listening beep"


def beep() -> np.ndarray:
    t = np.arange(int(0.15 * RATE)) / RATE
    return (np.sin(2 * np.pi * 880 * t) * 16000).astype(np.int16)


class Coordinator:
    def __init__(self, memory_dir=MEMORY_DIR, model=None, client=None, out=print, voice=None,
                 save_dir=None, port=None, dry_run=False):
        self.memory_dir = Path(memory_dir)
        self.client = client or anthropic.Anthropic()
        prompt = names_prompt(household_names(self.memory_dir))
        self.stt = STT(model, prompt) if model else STT(prompt=prompt)
        self.out = out
        self.save_dir = Path(save_dir) if save_dir else None
        self._saved = 0
        self.events = queue.Queue()
        self.mode = "off_watch"
        self.history = []
        # Current mode's timeout, monotonic time; None while Jack speaks or while
        # Asleep. Starts counting the Off Watch -> Asleep timeout immediately,
        # same as entering Off Watch any other way (end_session()).
        self.deadline = time.monotonic() + OFF_WATCH_TIMEOUT_S
        self._pending_mode = None    # Haiku's MODE: tag for the reply in flight, applied on reply_done
        self._reply = 0              # counts replies, to tag their sentences
        self._first_tag = None       # first and last sentence of the reply being spoken
        self._last_tag = None
        self._heard_at = None        # when the utterance being answered was handed over

        self.listener = Listener(on_utterance=lambda s, t: self.events.put(("utterance", s)))
        self.player = Playback(on_event=self._on_playback)
        self.capture = Capture(on_frame=self.listener.feed)
        self.tts = TTS(on_audio=self.player.play, **({"voice": voice} if voice else {}))

        # Motion & the Serial writer are only stood up when asked to (tests and
        # a bare --scratch-memory run skip them entirely) - see --port/--dry-run.
        self.serial_writer = None
        self.motion = None
        if port is not None or dry_run:
            self.serial_writer = serial_link.SerialWriter(
                now_fn=self.player.now, port=port or serial_link.PORT, dry_run=dry_run)
            self.player.serial_writer = self.serial_writer
            self.motion = Motion(self.serial_writer, player=self.player)

    # --- event sources (other threads) ---

    def _on_playback(self, kind, tag, dac_time):
        # Turn-taking: deaf while anything plays, until just after it ends.
        if kind == "started":
            self.listener.ignore_until(float("inf"))
            if tag == self._first_tag:
                self.events.put(("reply_started", time.monotonic()))
        else:
            self.listener.ignore_until(dac_time + HOLDOFF_S)
            if tag == self._last_tag:
                self.events.put(("reply_done", None))
            elif tag == BEEP_TAG:
                self.events.put(("beep_done", None))

    def wake(self):
        """Wake-phrase stand-in ("Ahoy, Captain Jack"): same event the
        real spotter will post, from Off Watch or Asleep."""
        self.events.put(("wake", None))

    def sleep_phrase(self):
        """Sleep-phrase stand-in ("Goodnight, Jack"): same event the real
        spotter will post, from Off Watch only (spec 4.11 - there's no
        fixed phrase into Asleep from On Watch; that's the MODE: tag)."""
        self.events.put(("sleep_phrase", None))

    # --- Coordinator (main thread) ---

    def run(self):
        self.listener.start()
        self.capture.start()
        if self.serial_writer:
            self.serial_writer.start()
        self.player.start()
        if self.motion:
            self.motion.set_mode(self.mode)
            self.motion.start()
        self.tts.start()
        try:
            while True:
                timeout = None
                if self.mode in ("on_watch", "off_watch") and self.deadline is not None:
                    timeout = max(0.0, self.deadline - time.monotonic())
                try:
                    kind, data = self.events.get(timeout=timeout)
                except queue.Empty:
                    self._handle_timeout()
                    continue
                self._handle_event(kind, data)
        finally:
            self.capture.stop()
            self.tts.stop()
            if self.motion:
                self.motion.stop()
            if self.serial_writer:
                self.serial_writer.stop()   # before player.stop() - it polls player.now()
            self.player.stop()
            self.listener.stop()

    def _handle_timeout(self):
        """No event arrived before the current mode's deadline."""
        if self.mode == "on_watch":
            self.end_session("no prompt for 2 minutes")
        elif self.mode == "off_watch":
            self.start_nap("no wake phrase for 15 minutes")

    def _handle_event(self, kind, data):
        """The run() loop's event dispatch, factored out so tests can
        drive it directly without starting the real audio threads."""
        if kind == "wake" and self.mode in ("off_watch", "asleep"):
            self.start_session()
        elif kind == "sleep_phrase" and self.mode == "off_watch":
            self.start_nap("Goodnight, Jack")
        elif kind == "utterance" and self.mode == "on_watch":
            self.handle_utterance(data)
        elif kind == "reply_started" and self._heard_at is not None:
            self.out(f"  [first audio {data - self._heard_at:.2f}s after you stopped talking]")
            self._heard_at = None
        elif kind == "reply_done" and self.mode == "on_watch":
            self._apply_pending_mode()
        elif kind == "beep_done":
            self.out("[On Watch - speak to Jack]")
        # events that don't match the current mode are ignored

    def _apply_pending_mode(self):
        """Called once the reply that may have carried a MODE: tag has
        finished playing (spec 4.16(c) step 5) - switches mode if Haiku
        signaled one, otherwise starts the ordinary 2-minute timer."""
        pending, self._pending_mode = self._pending_mode, None
        if pending == "END_SESSION":
            self.end_session("Jack ended the conversation")
        elif pending == "NAP":
            self.start_nap("Jack said goodnight")
        else:
            self.deadline = time.monotonic() + ON_WATCH_TIMEOUT_S

    def start_session(self):
        self.mode = "on_watch"
        self.history = []
        if self.motion:
            self.motion.set_mode("on_watch")
        # "speak to Jack" is printed on beep_done (below), not here - printing
        # it immediately races ahead of the beep actually playing, inviting
        # someone to start talking before the mic is open again and losing
        # the start of their sentence (see docs/log.md's 4.16 history).
        self.player.play(beep(), BEEP_TAG)
        self.deadline = time.monotonic() + ON_WATCH_TIMEOUT_S

    def end_session(self, why):
        self.mode = "off_watch"
        if self.motion:
            self.motion.set_mode("off_watch")
        self.deadline = time.monotonic() + OFF_WATCH_TIMEOUT_S
        self.out(f"[Off Watch - {why}. Press Enter to wake Jack.]")

    def start_nap(self, why):
        self.mode = "asleep"
        if self.motion:
            self.motion.set_mode("asleep")
        self.deadline = None   # Asleep has no further timeout - only the wake phrase ends it
        self.out(f"[Asleep - {why}. Press Enter to wake Jack.]")

    def speak(self, text):
        """Queue text to be spoken sentence by sentence; the On Watch
        timeout pauses until the last sentence has played."""
        sentences = split_sentences(text)
        if not sentences:
            return
        self._reply += 1
        self._first_tag = (self._reply, 0)
        self._last_tag = (self._reply, len(sentences) - 1)
        self.deadline = None
        for i, sentence in enumerate(sentences):
            self.tts.say(sentence, (self._reply, i))

    def save_utterance(self, samples) -> str:
        self._saved += 1
        path = self.save_dir / f"utt{self._saved:02d}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(samples.tobytes())
        return f", {path.name}"

    def handle_utterance(self, samples):
        self._heard_at = time.monotonic()
        saved = self.save_utterance(samples) if self.save_dir else ""
        heard = self.stt.transcribe(samples)
        stats = f"{heard.audio_s:.1f}s audio, stt {heard.stt_s:.2f}s, p={heard.prob:.2f}{saved}"
        if not heard.accepted:
            self.out(f"  (rejected - {heard.reject}: {heard.raw!r})   [{stats}]")
            self.out(f"Jack: {DIDNT_CATCH}")
            self.speak(DIDNT_CATCH)
            return
        self.out(f"You:  {heard.text}   [{stats}]")

        start = time.monotonic()
        try:
            turn = take_turn(self.client, self.history, heard.text, self.memory_dir)
        except anthropic.APIError as e:
            self.out(f"  [error reaching Haiku: {e}]")
            return
        self.out(f"Jack: {turn.spoken}   [haiku {time.monotonic() - start:.2f}s]")
        if turn.saved:
            self.out(f"  [memory saved - {turn.saved}]")
        self._pending_mode = turn.mode
        self.speak(turn.spoken)


def scratch_memory_copy() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="jack-memory-"))
    for name in ("identity.md", "memory.md"):
        shutil.copy(MEMORY_DIR / name, scratch / name)
    return scratch


def main():
    args = sys.argv[1:]
    model = args[args.index("--model") + 1] if "--model" in args else None
    voice = args[args.index("--voice") + 1] if "--voice" in args else None
    save_dir = args[args.index("--save") + 1] if "--save" in args else None
    port = args[args.index("--port") + 1] if "--port" in args else None
    dry_run = "--dry-run" in args
    if save_dir:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
    memory_dir = MEMORY_DIR
    if "--scratch-memory" in args:
        memory_dir = scratch_memory_copy()
        print(f"Using a scratch copy of memory: {memory_dir}")

    coord = Coordinator(memory_dir, model, voice=voice, save_dir=save_dir, port=port, dry_run=dry_run)

    def keyboard():
        for line in sys.stdin:
            if line.strip().lower() == "sleep":
                coord.sleep_phrase()
            else:
                coord.wake()

    threading.Thread(target=keyboard, name="keyboard", daemon=True).start()
    if "--wake-after" in args:
        delay = float(args[args.index("--wake-after") + 1])
        threading.Timer(delay, coord.wake).start()
    print(f"Whisper {coord.stt.model_name}. Press Enter to wake Jack; "
          f"type sleep + Enter for \"Goodnight, Jack\"; Ctrl+C to quit.")
    try:
        coord.run()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
