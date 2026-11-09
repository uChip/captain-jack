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
  - Shutdown (CLAUDE.md item 11): from any mode, a 5s press of the
    back-panel button (button.py); in On Watch, by voice - Jack asks a
    recognized voice to confirm (MODE: SHUTDOWN_ASK), and a yes
    (MODE: SHUTDOWN) shuts down once his farewell has played. Either way:
    clean stop, exit SHUTDOWN_EXIT (the service powers the Pi off).
Timeouts are spec 4.11's initial, not-yet-tuned numbers.

Run (in its own terminal - it reads the keyboard):
    venv/bin/python coordinator.py [--model base.en] [--voice bm_fable]
                                   [--scratch-memory] [--wake-after SECONDS]
                                   [--save DIR] [--port /dev/ttyUSB0] [--dry-run]
                                   [--hold] [--no-filler] [--no-home] [--no-speaker-id]
                                   [--no-doa] [--no-button] [--boot]
--scratch-memory runs against a temporary copy of memory/, so test
conversations can't add facts to the real memory.md. --wake-after wakes
Jack automatically that many seconds after starting, for runs with no
keyboard (e.g. launched in the background). --save writes every
utterance heard to DIR as a numbered .wav, for diagnosing mishearings (with
DoA on, also uttNN_doa.csv: the direction readings leading up to it, and
doa_stream.csv: every reading all session, with when the mic reopened
after Jack's own sound and each utterance's answer), and
with --port/--dry-run, serial.log: every head command sent to the Arduino,
timestamped, with the conversation's events between them.
--port opens the Arduino for beak-sync + ambient motion (omit to run
voice-only, as before); --dry-run drives the same Motion/Serial wiring
without a real port, for testing it when no Arduino is attached.
--hold holds the head still while the mic is open in On Watch - the
default until the bird was soft-mounted, which removed the servo noise
it was for (docs/log.md's 4.2 history, 2026-10-21); kept for now in case
that noise ever comes back. --no-filler skips the squawk played the
moment an utterance ends (see FILLER_DIR), e.g. for comparing the two.
--no-speaker-id turns off voice recognition (speaker_id.py, spec 4.15):
by default each utterance is scored against the enrolled voiceprints
while Whisper transcribes it, and Haiku gets a "[voice: Name]" or
"[voice: unknown]" note ahead of the transcript (see voice_note()). It's
off anyway if nobody is enrolled or the model file is missing.
--no-doa keeps the head facing front: by default, with --port, Jack turns
toward whoever just spoke, once per utterance (doa.py's DoaTracker,
Motion.turn_toward(), spec 4.9), and the squawk cocks toward them.
--no-home leaves out the home-automation tools (home.py), so nothing in
the house can be switched - by default Jack can control the devices
marked in docs/home-automation-device-list.csv.
--no-button ignores the back-panel shutdown button (button.py): by
default, holding it 5s from any mode cuts Jack off, squawks and says a
farewell, does the clean stop, and exits 42 - the service's cue to power
the Pi off (run by hand, it just exits). It's off anyway if GPIO26 can't
be opened. SIGUSR1 acts as a long press (for testing without the
button). SIGTERM/SIGHUP do the same clean stop, exiting 0.
--boot is how the service (deploy/captain-jack.service) starts him: no
keyboard stand-ins, and the starting state by time of day - Asleep with a
silent stretch in quiet hours (22:00-06:00, or while the clock isn't yet
synced), otherwise Off Watch with a quiet squawk and a stretch.
"""

import os
import queue
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import shutil
import signal
import subprocess
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
from motion import MAX_TURN_DEG, Motion
from home import Home
from orchestrate import MEMORY_DIR, TEMPLATE_DIR, household_names, live_memory_dir, stream_turn
from doa import DoaTracker
from button import HOLD_S, LINE as BUTTON_LINE, ShutdownButton, gpio_reader
from playback import RATE, Playback, load_wav
from speaker_id import MODEL_PATH as SPEAKER_MODEL, SpeakerID
from stt import STT, names_prompt
from tts import TTS, split_first_sentence, split_sentences
from wakeword import SLEEP_NAME, WAKE_NAME, WakeSpotter

ON_WATCH_TIMEOUT_S = 120       # spec 4.11: 2 minutes with no prompt -> Off Watch
OFF_WATCH_TIMEOUT_S = 15 * 60  # spec 4.11: 15 minutes with no wake phrase -> Asleep

# Spec 4.2: a rejected utterance gets an in-character prompt, not silence.
DIDNT_CATCH = "Arr, didn't catch that over the wind. Say again?"

# Haiku unreachable (no internet, API down, key expired): said in
# character instead of going silent (CLAUDE.md item 11). Spoken by local
# TTS, so it needs no network itself.
OFFLINE_LINE = "Arr, I can't reach the mainland just now. Try me again in a bit."

# Boot greeting (--boot, CLAUDE.md item 11, Chip 2026-11-09): started by the
# service, Jack comes up Asleep with a silent stretch in quiet hours
# (QUIET_START_H to QUIET_END_H, local time), otherwise Off Watch with a
# quiet squawk (BOOT_SQUAWK_DB under a normal one) and a stretch, so you
# know he's up. With the clock not yet synced the hour can't be trusted,
# so it's treated as quiet hours.
QUIET_START_H = 22
QUIET_END_H = 6
BOOT_SQUAWK_DB = -12.0

# Distinct from any (reply, sentence) tag, so _on_playback can tell the
# listening beep apart from a spoken reply.
BEEP_TAG = "listening beep"
# Shutdown (CLAUDE.md item 11): a squawk then one of these pre-rendered
# farewells (wavFiles/manifest.yaml - pre-rendered so they play instantly
# and with no network), then a clean stop and exit SHUTDOWN_EXIT, which
# the service (systemd) takes as "power the Pi off". If the clean stop
# hasn't finished SHUTDOWN_FALLBACK_S after the request (something hung),
# the process exits with that code anyway.
SHUTDOWN_DIR = Path(__file__).parent / "wavFiles" / "shutdown"
SHUTDOWN_TAG = "shutdown farewell"
SHUTDOWN_EXIT = 42
SHUTDOWN_FALLBACK_S = 30.0

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
# Early turn (mid-utterance, doa.py's EARLY_SETTLE_N): at most this far per
# move while someone talks - 30-50 degree turns mixed into session25's lines
# changed 2 of 118 words, the 100-degree side-to-side swing 9 (docs/log.md
# 4.9). The rest of the turn waits for face_speaker() after they stop.
EARLY_STEP_DEG = 50
EARLY_MIN_DEG = 15      # closer than this to where he already faces: don't move


def voice_note(text, match) -> str:
    """What Haiku is sent for an utterance: the transcript, with a
    "[voice: Name]" note ahead of it when speaker-ID is confident who's
    speaking, "[voice: unknown]" when it isn't - never a guess. Every line
    gets its own note: with unrecognized lines left bare, Haiku carried
    the last name forward and filed a new speaker's memory under it
    (2026-10-21, docs/log.md 4.15). memory/identity.md says how to use
    them. No note at all when speaker-ID is off (match is None)."""
    if match is None:
        return text
    return f"[voice: {match.name or 'unknown'}] {text}"


def describe_voice(match) -> str:
    """Console stats for speaker-ID, e.g. 'voice Kath 0.74' or
    'voice - (too close to call: Chip 0.40 Kath 0.34)'."""
    if match is None:
        return ""
    if match.name:
        return f", voice {match.name} {match.score:.2f}"
    scores = " ".join(f"{n} {s:.2f}" for n, s in sorted(match.scores.items()))
    return f", voice - ({match.reason}{': ' + scores if scores else ''})"


def beep() -> np.ndarray:
    t = np.arange(int(0.15 * RATE)) / RATE
    return (np.sin(2 * np.pi * 880 * t) * 16000).astype(np.int16)


class Coordinator:
    def __init__(self, memory_dir=MEMORY_DIR, model=None, client=None, out=print, voice=None,
                 save_dir=None, port=None, dry_run=False, hold=False, filler=True, home=None,
                 speaker_id=None, doa=None):
        self.memory_dir = Path(memory_dir)
        self.home = home
        # A speaker_id.SpeakerID, or None for no voice recognition (tests, and
        # --no-speaker-id). Runs on its own worker thread, alongside STT.
        self.speaker_id = speaker_id
        self._voice_pool = ThreadPoolExecutor(1, thread_name_prefix="speaker-id")
        # A doa.DoaTracker, or None (tests, no --port, --no-doa): which way
        # to turn the head after each utterance. Only used with Motion.
        self.doa = doa
        if doa:
            doa.on_early = self._on_early_turn
        self.client = client or anthropic.Anthropic()
        prompt = names_prompt(household_names(self.memory_dir))
        self.stt = STT(model, prompt) if model else STT(prompt=prompt)
        self.out = out
        self.hold = hold
        self.fillers = ({p.name: load_wav(p) for p in sorted(FILLER_DIR.glob("*.wav"))}
                        if filler else {})
        self._last_filler = None
        self._shutting_down = False
        self.button = None           # button.ShutdownButton, started/stopped with run() (main() sets it)
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
        self._shutdown_asked = False  # last reply asked a recognized voice "shut down - are ye sure?"
        self._reply = 0              # counts replies, to tag their sentences
        self._first_tag = None       # first and last sentence of the reply being spoken
        self._last_tag = None        # (reply, len(sentences) - 1) - only known once fully streamed
        self._sentences_finished = 0  # how many of the CURRENT reply's sentences have played, see _finish_reply
        self._last_sentence_dac_time = 0.0  # dac_time of the most recent one, for _finish_reply's race catch-up
        self._heard_at = None        # when the utterance being answered was handed over
        self._line_heading = None    # where the head faced when the current line started (DoA)

        self.listener = Listener(on_utterance=lambda s, t: self.events.put(("utterance", s)),
                                 on_speech_start=self._on_speech_start)
        self.spotter = WakeSpotter(on_wake=self.wake, on_sleep=self.sleep_phrase,
                                    on_score=self._on_spotter_score)
        self.player = Playback(on_event=self._on_playback)
        self.capture = Capture(on_frame=self._on_frame)
        self.tts = TTS(on_audio=self._on_tts_audio, **({"voice": voice} if voice else {}))

        # Motion & the Serial writer are only stood up when asked to (tests and
        # a bare --scratch-memory run skip them entirely) - see --port/--dry-run.
        self.serial_writer = None
        self._serial_log = None
        self.motion = None
        if port is not None or dry_run:
            self._serial_log = (open(self.save_dir / "serial.log", "a", buffering=1)
                                if self.save_dir else None)
            self.serial_writer = serial_link.SerialWriter(
                now_fn=self.player.now, port=port or serial_link.PORT, dry_run=dry_run,
                on_send=self._log_serial if self._serial_log else None)
            self.player.serial_writer = self.serial_writer
            self.motion = Motion(self.serial_writer, player=self.player)

    def _log_serial(self, line):
        """--save's serial.log: a sent command (beak values are left out -
        50 a second) or a "#" note from handle_utterance()."""
        if line.startswith("b") and "p" not in line:
            return
        self._serial_log.write(f"{time.monotonic():.2f} {line}\n")

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
            if self.doa:
                self.doa.jack_started()   # the board's speech flag means Jack now
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
                if self.doa:
                    self.doa.jack_done()   # where Jack's own sound left the board
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
        if self.doa:
            self.doa.start()
        self.tts.start()
        if self.button:
            self.button.start()
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
            if self.button:
                self.button.stop()
            self.capture.stop()
            if self.doa:
                self.doa.stop()
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
        elif kind == "shutdown":
            self.player.wait_played(timeout=15)   # let the farewell finish
            raise Stop(data)
        elif kind == "boot":
            self.boot_greeting(*data)
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
        elif pending == "SHUTDOWN":
            self.out("[Shutting down - confirmed by voice]")
            raise Stop("voice")       # run()'s finally: clean stop, head to rest; exit SHUTDOWN_EXIT
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
        self._shutdown_asked = False
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
        if self._serial_log:
            self._log_serial(f"# off_watch ({why})")
        self.mode = "off_watch"
        if self.motion:
            self.motion.set_mode("off_watch")
        self.deadline = time.monotonic() + OFF_WATCH_TIMEOUT_S
        self.out(f"[Off Watch - {why}. Press Enter to wake Jack.]")

    def boot_greeting(self, hour, synced):
        """--boot: pick the starting state by time of day (see QUIET_START_H).
        hour is the local hour; synced is whether the clock is known good."""
        if not synced or in_quiet_hours(hour):
            if self.motion:
                self.motion.stretch()   # silent; the settle-in waits for it
            self.start_nap("boot, quiet hours" if synced else "boot, clock not synced")
            return
        if self.fillers:
            names = list(self.fillers)
            name = random.choice(names)
            self._last_filler = name
            quiet = self.fillers[name] * 10 ** (BOOT_SQUAWK_DB / 20)
            self.player.play(quiet.astype(np.int16), "boot squawk")
        if self.motion:
            self.motion.stretch()
        self.out("[Off Watch - booted. Say the wake phrase.]")

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
            if self.doa:
                self.doa.jack_done()
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
        if self.doa and self.motion:
            with open(self.save_dir / f"utt{self._saved:02d}_doa.csv", "w") as f:
                f.write("age_s,board_deg,speech\n")
                for age, az, speech in self.doa.recent(len(samples) / RATE + 2.0):
                    f.write(f"{age},{az},{int(speech)}\n")
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(samples.tobytes())
        return f", {path.name}"

    def _on_tts_audio(self, samples, tag):
        """TTS thread: a synthesized sentence, to play - unless Jack is
        shutting down, when anything still coming from TTS is dropped."""
        if not self._shutting_down:
            self.player.play(samples, tag)

    def long_press(self):
        """Button thread: the back-panel button was held HOLD_S - shut down,
        from any mode, no confirmation (the long press is its own; Chip,
        2026-11-09). Cuts off whatever Jack is saying, deafens the mic,
        sends the head to rest, and plays a squawk and a farewell; the main
        thread then waits for it to finish and does the clean stop
        (_handle_event's "shutdown" -> Stop("button") -> exit SHUTDOWN_EXIT)."""
        if self._shutting_down:
            return
        self._shutting_down = True
        self.out("[Button held - shutting down]")
        fallback = threading.Timer(SHUTDOWN_FALLBACK_S, os._exit, (SHUTDOWN_EXIT,))
        fallback.daemon = True       # a clean exit doesn't wait for it
        fallback.start()
        self.tts.clear()
        self.player.clear()
        self.listener.ignore_until(float("inf"))
        self.spotter.ignore_until(float("inf"))
        if self.motion:
            self.motion.stop()       # no more gestures or idle clips; head to rest
        self.player.play(farewell_audio(), SHUTDOWN_TAG)
        self.events.put(("shutdown", "button"))

    def play_filler(self, toward=None):
        """Queue a squawk (see FILLER_DIR) after FILLER_DELAY_S of silence,
        never the same one twice running, with a head tilt to match -
        cocked toward the speaker's angle if known (see face_speaker())."""
        if not self.fillers or self._shutting_down:
            return
        names = [n for n in self.fillers if n != self._last_filler] or list(self.fillers)
        name = random.choice(names)
        self._last_filler = name
        lead = np.zeros(int(FILLER_DELAY_S * RATE), dtype=np.int16)
        self.player.play(np.concatenate([lead, self.fillers[name]]), name)
        if self.motion:
            self.motion.squawk_tilt(FILLER_DELAY_S, len(self.fillers[name]) / RATE, toward)

    def _on_speech_start(self):
        """Listener thread: an utterance has just started."""
        if self.doa and self.mode == "on_watch":
            self.doa.speech_started()
            if self.motion:
                self._line_heading = self.motion.heading()   # to turn back to if it's noise

    def _on_early_turn(self, angle):
        """DoA thread, mid-utterance: the board has settled on a new
        direction - turn that way now, as an animal turns at a sound, by at
        most EARLY_STEP_DEG (bigger moves while someone talks measurably hurt
        STT - docs/log.md 4.9). face_speaker() finishes the turn after."""
        if self.mode != "on_watch" or not self.motion:
            return
        heading = self.motion.heading()
        target = max(-MAX_TURN_DEG, min(MAX_TURN_DEG, angle))
        step = max(-EARLY_STEP_DEG, min(EARLY_STEP_DEG, target - heading))
        if abs(step) <= EARLY_MIN_DEG:
            return
        self.motion.turn_toward(heading + step)
        if self._serial_log:
            self._log_serial(f"# early turn: doa {angle:+d}, heading {heading:+d} -> {heading + step:+d}")

    def face_speaker(self, samples):
        """Turn the head toward whoever just spoke samples (finishing any
        early turn made while they spoke); returns (their angle, the early
        angle), + = Jack's right, either None if DoA wasn't sure - then
        the head stays where it is."""
        if not (self.doa and self.motion):
            return None, None
        if self._line_heading is None:
            self._line_heading = self.motion.heading()
        angle = self.doa.direction(len(samples) / RATE)
        early = self.doa.take_early()
        if angle is not None:
            self.motion.turn_toward(angle)
        return angle, early

    def handle_utterance(self, samples):
        self._heard_at = time.monotonic()
        angle, early = self.face_speaker(samples)
        if self._serial_log:
            self._log_serial(f"# utt{self._saved + 1:02d} doa {angle} early {early} baseline yaw "
                             f"{self.motion.baseline.yaw if self.motion else '-'}")
        self.play_filler(angle if angle is not None else early)
        saved = self.save_utterance(samples) if self.save_dir else ""
        voice = self._voice_pool.submit(self.speaker_id.identify, samples) if self.speaker_id else None
        heard = self.stt.transcribe(samples)
        match = voice.result() if voice else None
        doa = "" if not (self.doa and self.motion) else (
            (f", doa {angle:+d}" if angle is not None else ", doa -")
            + (f" (early {early:+d})" if early is not None else ""))
        stats = (f"{heard.audio_s:.1f}s audio, stt {heard.stt_s:.2f}s, p={heard.prob:.2f}"
                 f"{describe_voice(match)}{doa}{saved}")
        before, self._line_heading = self._line_heading, None
        if not heard.accepted:
            real_voice = match is not None and match.name is not None
            if (self.motion and before is not None and not real_voice
                    and abs(self.motion.heading() - before) > EARLY_MIN_DEG):
                # STT heard no words: the turn was toward a noise. Look back,
                # as an animal does once a sound turns out to be nothing
                # (Chip, 2026-11-08: a noise turn is lifelike "but should recover").
                # Not when speaker-ID names a household voice - that was a
                # real person STT failed on (session27 utt01: a doubled
                # transcript rejected as a repeat loop), so keep facing them.
                self.motion.turn_toward(before)
                stats += f", turned back to {before:+d}"
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
            turn = stream_turn(self.client, self.history, voice_note(heard.text, match), on_sentence,
                               self.memory_dir, home=self.home)
        except anthropic.APIError as e:
            self.out(f"  [error reaching Haiku: {e}]")
            self._finish_reply(reply, n)
            if n == 0:   # nothing spoken yet: say why, rather than go silent
                self.out(f"Jack: {OFFLINE_LINE}")
                self.speak(OFFLINE_LINE)
            return
        self.out(f"Jack: {turn.spoken}   [haiku {time.monotonic() - start:.2f}s]")
        if turn.saved:
            self.out(f"  [memory saved - {turn.saved}]")
        self._pending_mode = self._shutdown_check(turn.mode, match)
        self._finish_reply(reply, n)

    def _shutdown_check(self, mode, match):
        """Voice shutdown (CLAUDE.md item 11, Chip 2026-11-09): On Watch only,
        a household voice only, and only after Jack has asked "are ye
        sure?" and been told yes. Haiku runs the exchange (identity.md's
        SHUTDOWN_ASK, then SHUTDOWN), but the rules are enforced here:
        SHUTDOWN_ASK counts only when speaker-ID names the voice asking,
        and SHUTDOWN only on the very next reply after a counted
        SHUTDOWN_ASK (a line STT rejects in between doesn't break it).
        Returns the mode to apply once the reply finishes playing."""
        asked, self._shutdown_asked = self._shutdown_asked, False
        if mode == "SHUTDOWN_ASK":
            if match is not None and match.name:
                self._shutdown_asked = True
            else:
                self.out("  [shutdown not offered: voice not recognized]")
            return None
        if mode == "SHUTDOWN" and not asked:
            self.out("  [shutdown tag ignored: Jack hadn't asked a recognized voice to confirm]")
            return None
        return mode


def in_quiet_hours(hour: int) -> bool:
    return hour >= QUIET_START_H or hour < QUIET_END_H


def clock_synced() -> bool:
    """Whether systemd says the clock has synced to NTP. The Pi 5 keeps
    time across power-off only with an RTC battery, so before a sync
    the hour may be far off."""
    try:
        out = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                             capture_output=True, text=True, timeout=5).stdout
        return out.strip() == "yes"
    except (OSError, subprocess.SubprocessError):
        return False


def scratch_memory_copy() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="jack-memory-"))
    for name in ("identity.md", "memory.md"):
        shutil.copy(TEMPLATE_DIR / name, scratch / name)
    return scratch


def farewell_audio():
    """A random squawk, a short beat, and a random farewell line."""
    squawk = load_wav(random.choice(sorted(FILLER_DIR.glob("*.wav"))))
    line = load_wav(random.choice(sorted(SHUTDOWN_DIR.glob("*.wav"))))
    return np.concatenate([squawk, np.zeros(int(0.3 * RATE), dtype=np.int16), line])


class Stop(BaseException):
    """Raised in the main thread by SIGTERM (systemd stopping the service,
    `sudo poweroff`, a plain `kill`) or SIGHUP (the SSH session running
    Jack dropped). A BaseException, like KeyboardInterrupt, so it unwinds
    through run() and its finally runs the same clean stop as Ctrl+C:
    every thread stopped, head and beak back to rest (CLAUDE.md item 11)."""


def install_stop_signals():
    """Turn SIGTERM/SIGHUP into Stop in the main thread. After the first,
    both are ignored, so a second signal can't cut the clean stop short
    (systemd's stop timeout still ends a stop that hangs)."""
    def handler(signum, frame):
        for sig in (signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        raise Stop(signal.Signals(signum).name)
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, handler)


def main():
    # One line at a time even into a file or the journal - block-buffered,
    # a session log showed nothing until exit (session28, 2026-11-09).
    sys.stdout.reconfigure(line_buffering=True)
    args = sys.argv[1:]
    model = args[args.index("--model") + 1] if "--model" in args else None
    voice = args[args.index("--voice") + 1] if "--voice" in args else None
    save_dir = args[args.index("--save") + 1] if "--save" in args else None
    port = args[args.index("--port") + 1] if "--port" in args else None
    dry_run = "--dry-run" in args
    if save_dir:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
    if "--scratch-memory" in args:
        memory_dir = scratch_memory_copy()
        print(f"Using a scratch copy of memory: {memory_dir}")
    else:
        memory_dir = live_memory_dir()
        print(f"Memory: {memory_dir / 'memory.md'}")

    speaker = None
    if "--no-speaker-id" not in args:
        if not SPEAKER_MODEL.exists():
            print(f"Speaker-ID off: no {SPEAKER_MODEL} (see speaker_id.py to download it)")
        else:
            speaker = SpeakerID()
            if speaker.voiceprints:
                print(f"Speaker-ID: {', '.join(speaker.voiceprints)} enrolled")
            else:
                print("Speaker-ID off: nobody enrolled (enroll_speaker.py)")
                speaker = None
    doa = None
    if port and "--no-doa" not in args:
        doa_log = None
        if save_dir:
            Path(save_dir).mkdir(parents=True, exist_ok=True)
            doa_log = open(Path(save_dir) / "doa_stream.csv", "a", buffering=1)
            doa_log.write("t,board_deg,speech,event\n")
        doa = DoaTracker(log=doa_log)
    coord = Coordinator(memory_dir, model, voice=voice, save_dir=save_dir, port=port, dry_run=dry_run,
                        hold="--hold" in args, filler="--no-filler" not in args, speaker_id=speaker,
                        doa=doa)
    if "--no-home" not in args:
        coord.home = Home(log=coord.out)
        coord.home.warm_up()

    def keyboard():
        for line in sys.stdin:
            if line.strip().lower() == "sleep":
                coord.sleep_phrase()
            else:
                coord.wake()

    if "--boot" in args:   # started by the service: no keyboard, greeting by time of day
        synced = clock_synced()
        coord.events.put(("boot", (datetime.now().hour, synced)))
    else:
        threading.Thread(target=keyboard, name="keyboard", daemon=True).start()
    if "--wake-after" in args:
        delay = float(args[args.index("--wake-after") + 1])
        threading.Timer(delay, coord.wake).start()
    print(f"Whisper {coord.stt.model_name}. Press Enter to wake Jack; "
          f"type sleep + Enter for \"Goodnight, Jack\"; Ctrl+C to quit.")
    if "--no-button" not in args:
        try:
            coord.button = ShutdownButton(coord.long_press)
            coord.button.read, coord.button._close = gpio_reader()
            print(f"Shutdown button: GPIO{BUTTON_LINE} (hold {HOLD_S:g}s)")
        except Exception as e:     # no gpiod, line busy, no permission: run without it
            coord.button = None
            print(f"Shutdown button off: {e}")
    install_stop_signals()
    # SIGUSR1 = a long press, for testing the shutdown path without the
    # button (`kill -USR1 <pid>`); run on its own thread, as the button's is.
    signal.signal(signal.SIGUSR1, lambda *a: threading.Thread(target=coord.long_press, daemon=True).start())
    try:
        coord.run()
    except KeyboardInterrupt:
        print()
    except Stop as e:
        print(f"Stopped ({e}) - clean stop done.", flush=True)
        if str(e) in ("button", "voice"):
            print(f"Exit {SHUTDOWN_EXIT}: shutdown requested (the service powers the Pi off).", flush=True)
            sys.exit(SHUTDOWN_EXIT)


if __name__ == "__main__":
    main()
