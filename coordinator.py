"""Captain Jack coordinator: the full Sleep-Mode State Machine (spec 4.11).

Implements the Coordinator from docs/specification.md section 4.16(c),
build step 7: wires Capture -> Listener -> STT -> the orchestrator's
stream_turn() -> TTS -> Playback, with Playback's events driving the
Listener's turn-taking gate, and (when --port/--dry-run is given) the
Serial writer + Motion & idle thread for beak-sync and ambient gestures.
Replies are spoken sentence by sentence (and printed).

Three modes: Off Watch (idle, waiting for the wake phrase), On Watch
(conversing), Asleep (napping, woken only by the wake phrase). The real
wake-word spotter (wakeword.py's WakeSpotter, build step 7 complete
2026-10-11) runs continuously alongside the keyboard stand-ins, not
replacing them (decided 2026-10-11 - a permanent manual override/test
aid, see CLAUDE.md): pressing Enter stands in for "Ahoy, Captain Jack"
(-> On Watch from Off Watch or Asleep) and typing "sleep" then Enter
stands in for "Goodnight, Jack" (Off Watch -> Asleep only - the spotter
never needs to listen for it while already On Watch or Asleep, per spec
4.11). Both paths post the exact same internal event. A beep through
the bird marks the start of listening. Transitions:
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
                                   [--no-hold] [--no-filler]
--scratch-memory runs against a temporary copy of memory/, so test
conversations can't add facts to the real memory.md. --wake-after wakes
Jack automatically that many seconds after starting, for runs with no
keyboard (e.g. launched in the background). --save writes every
utterance heard to DIR as a numbered .wav, for diagnosing mishearings.
--port opens the Arduino for beak-sync + ambient motion (omit to run
voice-only, as before); --dry-run drives the same Motion/Serial wiring
without a real port, for testing it when no Arduino is attached.
--no-hold keeps the head moving while the mic is open in On Watch, for
measuring recognition over servo motion (e.g. with the bird soft-mounted,
docs/log.md's 4.2 history). --no-filler skips the squawk played the
moment an utterance ends (see FILLER_DIR), e.g. for comparing the two.
"""

import queue
import random
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
from orchestrate import MEMORY_DIR, household_names, stream_turn
from playback import RATE, Playback, load_wav
from stt import STT, names_prompt
from tts import TTS, split_first_sentence, split_sentences
from wakeword import SLEEP_NAME, WAKE_NAME, WakeSpotter

ON_WATCH_TIMEOUT_S = 120       # spec 4.11: 2 minutes with no prompt -> Off Watch
OFF_WATCH_TIMEOUT_S = 15 * 60  # spec 4.11: 15 minutes with no wake phrase -> Asleep

# Spec 4.2: a rejected utterance gets an in-character prompt, not silence.
DIDNT_CATCH = "Arr, didn't catch that over the wind. Say again?"

# Distinct from any (reply, sentence) tag, so _on_playback can tell the
# listening beep apart from a spoken reply.
BEEP_TAG = "listening beep"

# Filler squawks (CLAUDE.md work list, 2026-10-14): one is played the moment
# an utterance is handed over, before STT even starts, so the ~3s wait for
# STT + Haiku + the first TTS sentence reads as Jack reacting, not lag.
# Every .wav here is a candidate, rotated so the same one never plays twice
# in a row - drop in new squawks without touching code (generate_fillers.py
# renders the current set). Played on turn-taking's own terms: the mic is
# deaf while it plays, like any other clip.
FILLER_DIR = Path(__file__).parent / "wavFiles" / "fillers"
# Silence played ahead of the squawk (Chip, 2026-10-15): a squawk the instant
# you stop talking felt abrupt; a beat first breaks up the wait better. 0.3s
# tried first, 0.6s kept after session18. Costs nothing - STT starts
# immediately either way, in parallel with playback.
FILLER_DELAY_S = 0.6


def beep() -> np.ndarray:
    t = np.arange(int(0.15 * RATE)) / RATE
    return (np.sin(2 * np.pi * 880 * t) * 16000).astype(np.int16)


class Coordinator:
    def __init__(self, memory_dir=MEMORY_DIR, model=None, client=None, out=print, voice=None,
                 save_dir=None, port=None, dry_run=False, hold=True, filler=True):
        self.memory_dir = Path(memory_dir)
        self.client = client or anthropic.Anthropic()
        prompt = names_prompt(household_names(self.memory_dir))
        self.stt = STT(model, prompt) if model else STT(prompt=prompt)
        self.out = out
        self.hold = hold
        self.fillers = ({p.name: load_wav(p) for p in sorted(FILLER_DIR.glob("*.wav"))}
                        if filler else {})
        self._last_filler = None
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
        self._last_tag = None        # (reply, len(sentences) - 1) - only known once fully streamed
        self._sentences_finished = 0  # how many of the CURRENT reply's sentences have played, see _finish_reply
        self._last_sentence_dac_time = 0.0  # dac_time of the most recent one, for _finish_reply's race catch-up
        self._heard_at = None        # when the utterance being answered was handed over

        self.listener = Listener(on_utterance=lambda s, t: self.events.put(("utterance", s)))
        self.spotter = WakeSpotter(on_wake=self.wake, on_sleep=self.sleep_phrase,
                                    on_score=self._on_spotter_score)
        self.player = Playback(on_event=self._on_playback)
        self.capture = Capture(on_frame=self._on_frame)
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

    def _on_frame(self, samples, adc_time):
        """Capture's on_frame callback: fans each frame out to both the
        Listener (On Watch utterances) and the WakeSpotter (wake/sleep
        phrase, Off Watch/Asleep) - they're independent consumers of the
        same mic stream."""
        self.listener.feed(samples, adc_time)
        self.spotter.feed(samples, adc_time)

    def _on_spotter_score(self, scores):
        """WakeSpotter's debug hook (runs on its own thread): prints any
        near-miss or real detection's score live. Earned its keep
        2026-10-11 diagnosing a since-resolved Asleep wake-detection
        report; kept on since the same numbers are exactly what spec
        4.1's still-deferred real-audio threshold calibration needs.
        Only while wake detection actually matters (Off Watch/Asleep),
        so real conversation doesn't get spammed with it."""
        if self.mode != "on_watch":
            self.out(f"  [spotter] wake={scores[WAKE_NAME]:.2f}  sleep={scores[SLEEP_NAME]:.2f}")

    def _on_playback(self, kind, tag, dac_time):
        # Turn-taking: deaf while anything plays, until just after it ends.
        # The spotter is gated the same way as the Listener, same reason -
        # Jack's own voice (replies, idle clips, settle-in lines) must
        # never trigger himself.
        if kind == "started":
            self.listener.ignore_until(float("inf"))
            self.spotter.ignore_until(float("inf"))
            if tag == self._first_tag:
                self._hold_head(False)   # mic just closed - Jack may move while he talks
                self.events.put(("reply_started", time.monotonic()))
        else:
            # Reopen the mic once a *whole* self-contained thing is done
            # playing - any single-tag item (a wav filename, BEEP_TAG) is
            # one on its own, but a reply's sentences share a (reply, i)
            # tuple tag and only its true last one counts, not after each
            # sentence - otherwise a stray sound in the gap between two
            # sentences becomes a real "utterance" event while the reply is
            # still mid-flight, and handling it clobbers _first_tag/_last_tag
            # (see docs/log.md's 4.16 history) before the reply's own last
            # sentence gets a chance to fire reply_done. Found live,
            # 2026-10-11: Motion's own idle/excursion/settle-in wav clips
            # play through this same Playback instance tagged with their
            # filename, which matched neither the old `_last_tag`-or-
            # `BEEP_TAG` check nor anything else - so the mic (and, once
            # wired in, the WakeSpotter) went deaf after the first such
            # clip in Off Watch/Asleep and never reopened for the rest of
            # that mode. See docs/log.md's 4.11/4.16 history.
            if isinstance(tag, tuple) and tag[0] == self._reply:
                self._sentences_finished += 1
                self._last_sentence_dac_time = dac_time
            if not isinstance(tag, tuple) or tag == self._last_tag:
                self.listener.ignore_until(dac_time + HOLDOFF_S)
                self.spotter.ignore_until(dac_time + HOLDOFF_S)
            if tag == self._last_tag:
                self.events.put(("reply_done", None))
            elif tag == BEEP_TAG:
                self.events.put(("beep_done", None))

    def wake(self):
        """Wake-phrase event ("Ahoy, Captain Jack"), from Off Watch or
        Asleep - called by both the Enter keyboard stand-in and
        WakeSpotter.on_wake, kept permanently side by side (decided
        2026-10-11, see CLAUDE.md)."""
        self.events.put(("wake", None))

    def sleep_phrase(self):
        """Sleep-phrase event ("Goodnight, Jack"), from Off Watch only
        (spec 4.11 - there's no fixed phrase into Asleep from On Watch;
        that's the MODE: tag) - called by both the `sleep` keyboard
        stand-in and WakeSpotter.on_sleep."""
        self.events.put(("sleep_phrase", None))

    # --- Coordinator (main thread) ---

    def run(self):
        self.listener.start()
        self.spotter.start()
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
            self.spotter.stop()
            if self.capture.overflows:
                self.out(f"WARNING: {self.capture.overflows} input overflow(s) - audio was lost")

    def _handle_timeout(self):
        """No event arrived before the current mode's deadline."""
        if self.mode == "on_watch":
            self.end_session("no prompt for 2 minutes")
        elif self.mode == "off_watch":
            self.start_nap("no wake phrase for 15 minutes", "idle_timeout")

    def _handle_event(self, kind, data):
        """The run() loop's event dispatch, factored out so tests can
        drive it directly without starting the real audio threads."""
        if kind == "wake" and self.mode in ("off_watch", "asleep"):
            self.start_session()
        elif kind == "sleep_phrase" and self.mode == "off_watch":
            self.start_nap("Goodnight, Jack", "goodnight_phrase")
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
            self._hold_head(True)   # mic is open again

    def _hold_head(self, on: bool):
        """Hold the head still while the mic is open in On Watch - moving
        servos measurably drown out speech (docs/log.md's 4.2 history,
        2026-10-14). Held from session start and after each reply,
        i.e. for exactly as long as the mic is open; released when a
        reply's first sentence starts playing (the mic closes then), so
        Jack still moves while he talks. Any mode change releases it too
        (Motion.set_mode)."""
        if self.motion and self.hold:
            self.motion.hold(on)

    def start_session(self):
        self.mode = "on_watch"
        self.history = []
        if self.motion:
            self.motion.set_mode("on_watch")
        self._hold_head(True)
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

    def start_nap(self, why, context=None):
        """context picks the settle-in line (spec 4.10): "goodnight_phrase",
        "idle_timeout", or None for MODE: NAP - Haiku's reply already said
        goodnight. Played by Motion, so only with --port/--dry-run."""
        self.mode = "asleep"
        if self.motion:
            self.motion.fall_asleep(context)
        self.deadline = None   # Asleep has no further timeout - only the wake phrase ends it
        self.out(f"[Asleep - {why}. Press Enter to wake Jack.]")

    def _begin_reply(self) -> int:
        """Starts a new tagged reply: bumps the reply counter and resets
        the per-reply bookkeeping speak() and the streaming path in
        handle_utterance() both need. Returns the new reply number."""
        self._reply += 1
        self._first_tag = None
        self._last_tag = None
        self._sentences_finished = 0
        self.deadline = None
        return self._reply

    def _queue_sentence(self, reply: int, i: int, sentence: str):
        """Tags and queues one sentence to TTS - the first one queued
        for a reply also becomes _first_tag (for the first-audio timing
        print), however many more are still to come."""
        tag = (reply, i)
        if self._first_tag is None:
            self._first_tag = tag
        self.tts.say(sentence, tag)

    def _finish_reply(self, reply: int, n_sentences: int):
        """Call once all of a reply's sentences are known and queued -
        marks (reply, n_sentences - 1) as _last_tag, the one
        _on_playback watches for to reopen the mic and fire reply_done.

        Streaming (handle_utterance below) can't know this number until
        Haiku's full reply, tags included, has arrived - by which point
        TTS may already be partway through synthesizing/playing earlier
        sentences. In the (expected to be rare) case where the reply's
        true last sentence already finished playing before we got here
        - its own _on_playback("finished", ...) call came and went while
        _last_tag still pointed at the previous reply, so it never
        matched - catch up immediately instead of silently dropping the
        mic reopen/reply_done, same class of race as the sentence-gap
        bug found live 2026-10-11 (docs/log.md's 4.16 history), just a
        different pair of racing events. Reuses the dac_time that
        playback event itself already recorded, rather than asking
        Playback for the current time - by now that sentence's audio is
        in the past, not "now"."""
        if n_sentences == 0:
            # Nothing was ever said for this reply (a Haiku error before
            # any sentence streamed in, or - in principle - an empty
            # spoken reply). _begin_reply() already paused the On Watch
            # timeout for it; resume it the same way _apply_pending_mode
            # does when Haiku signals no mode change, rather than leaving
            # it paused with nothing left to ever resume it.
            self.deadline = time.monotonic() + ON_WATCH_TIMEOUT_S
            self._hold_head(True)   # the mic never closed, so it's still open
            return
        self._last_tag = (reply, n_sentences - 1)
        if self._sentences_finished >= n_sentences:
            t = self._last_sentence_dac_time
            self.listener.ignore_until(t + HOLDOFF_S)
            self.spotter.ignore_until(t + HOLDOFF_S)
            self.events.put(("reply_done", None))

    def speak(self, text):
        """Queue a fixed string to be spoken sentence by sentence, all
        at once - used for DIDNT_CATCH, not Haiku's replies (those
        stream in progressively, see handle_utterance below)."""
        sentences = split_sentences(text)
        reply = self._begin_reply()
        for i, sentence in enumerate(sentences):
            self._queue_sentence(reply, i, sentence)
        self._finish_reply(reply, len(sentences))

    def save_utterance(self, samples) -> str:
        self._saved += 1
        path = self.save_dir / f"utt{self._saved:02d}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(samples.tobytes())
        return f", {path.name}"

    def play_filler(self):
        """Queue a squawk (see FILLER_DIR) after FILLER_DELAY_S of silence,
        never the same one twice running, with a head tilt to match."""
        if not self.fillers:
            return
        names = [n for n in self.fillers if n != self._last_filler] or list(self.fillers)
        name = random.choice(names)
        self._last_filler = name
        lead = np.zeros(int(FILLER_DELAY_S * RATE), dtype=np.int16)
        self.player.play(np.concatenate([lead, self.fillers[name]]), name)
        if self.motion:
            self.motion.squawk_tilt(FILLER_DELAY_S, len(self.fillers[name]) / RATE)

    def handle_utterance(self, samples):
        self._heard_at = time.monotonic()
        self.play_filler()
        saved = self.save_utterance(samples) if self.save_dir else ""
        heard = self.stt.transcribe(samples)
        stats = f"{heard.audio_s:.1f}s audio, stt {heard.stt_s:.2f}s, p={heard.prob:.2f}{saved}"
        if not heard.accepted:
            self.out(f"  (rejected - {heard.reject}: {heard.raw!r})   [{stats}]")
            self.out(f"Jack: {DIDNT_CATCH}")
            self.speak(DIDNT_CATCH)
            return
        self.out(f"You:  {heard.text}   [{stats}]")

        reply = self._begin_reply()
        n = 0

        def on_sentence(sentence):
            # A long first sentence is spoken in two pieces so Jack starts
            # sooner (tts.split_first_sentence); each piece is just another
            # tagged sentence from here on.
            nonlocal n
            for piece in split_first_sentence(sentence) if n == 0 else [sentence]:
                self._queue_sentence(reply, n, piece)
                n += 1

        start = time.monotonic()
        try:
            turn = stream_turn(self.client, self.history, heard.text, on_sentence, self.memory_dir)
        except anthropic.APIError as e:
            self.out(f"  [error reaching Haiku: {e}]")
            self._finish_reply(reply, n)
            return
        self.out(f"Jack: {turn.spoken}   [haiku {time.monotonic() - start:.2f}s]")
        if turn.saved:
            self.out(f"  [memory saved - {turn.saved}]")
        self._pending_mode = turn.mode
        self._finish_reply(reply, n)


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

    coord = Coordinator(memory_dir, model, voice=voice, save_dir=save_dir, port=port, dry_run=dry_run,
                        hold="--no-hold" not in args, filler="--no-filler" not in args)

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
