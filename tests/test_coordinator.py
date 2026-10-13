"""Re-runnable test for docs/tests.md: "Coordinator turn".

Part 1 (automatic, no hardware, no API): builds a Coordinator on a
scratch copy of memory/ with a fake Haiku client, then feeds it the
recorded utterance tests/data/quick_brown_fox_ch1.wav as if the Listener
had just heard it. Checks:
  - wake starts an On Watch session; the timeout ends it;
  - the utterance is transcribed and sent to Haiku as the user turn;
  - Jack's reply is output with its MEMORY: line split off, and the
    proposed memory is saved to the scratch copy, never the real file;
  - noise is answered with "didn't catch that" and never sent to Haiku;
  - the Whisper spelling hint names the household members.

Part 2 (--live, real Haiku API, a fraction of a cent): the same
utterance through the real API, still on scratch memory. Checks Jack
replies with something non-empty.

Run: venv/bin/python tests/test_coordinator.py [--live]
"""

import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import coordinator  # noqa: E402
from orchestrate import MEMORY_PATH  # noqa: E402

CLIP = Path(__file__).parent / "data" / "quick_brown_fox_ch1.wav"


class FakeStream:
    """Stands in for anthropic's MessageStream: yields the canned reply
    one character at a time, the strictest test of boundary-detection
    across chunks - a real streamed reply can split anywhere."""

    def __init__(self, reply):
        self.reply = reply

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        return iter(self.reply)

    def get_final_text(self):
        return self.reply


class FakeClient:
    """Stands in for anthropic.Anthropic(): records requests, returns a canned reply."""

    def __init__(self, reply):
        self.reply = reply
        self.requests = []
        self.messages = SimpleNamespace(create=self._create, stream=self._stream)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)])

    def _stream(self, **kwargs):
        self.requests.append(kwargs)
        return FakeStream(self.reply)


def load_clip():
    with wave.open(str(CLIP)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def check_offline():
    errors = []
    real_before = MEMORY_PATH.read_text()
    scratch = coordinator.scratch_memory_copy()
    out = []
    client = FakeClient("Arr, a nimble fox indeed!\nMEMORY: [joke] Test fox fact (coordinator test)")
    coord = coordinator.Coordinator(scratch, client=client, out=out.append)

    names = coord.stt.prompt or ""
    for name in ("Chip", "Kath", "Liz"):
        if name not in names:
            errors.append(f"Whisper spelling hint missing {name}: {names!r}")

    coord.start_session()
    if coord.mode != "on_watch":
        errors.append("start_session() didn't enter On Watch")

    coord.handle_utterance(load_clip())
    if len(client.requests) != 1:
        errors.append(f"expected 1 Haiku call, got {len(client.requests)}")
    else:
        sent = client.requests[0]["messages"][0]["content"].lower()
        if "lazy dog" not in sent:
            errors.append(f"Haiku was sent {sent!r}, not the transcript")
    text = "\n".join(out)
    if "Jack: Arr, a nimble fox indeed!" not in text or "MEMORY:" in text.split("Jack:")[-1].split("\n")[0]:
        errors.append(f"reply not output cleanly: {text!r}")
    if "Test fox fact (coordinator test)" not in (scratch / "memory.md").read_text():
        errors.append("memory not saved to the scratch copy")
    if MEMORY_PATH.read_text() != real_before:
        errors.append("the REAL memory.md was modified")

    noise = np.tile(load_clip()[:int(0.55 * 16000)], 4)     # room noise before speech
    coord.handle_utterance(noise)
    if len(client.requests) != 1:
        errors.append("noise was sent to Haiku")
    if coordinator.DIDNT_CATCH not in out[-1]:
        errors.append(f"noise not answered with didn't-catch-that: {out[-1]!r}")

    coord.end_session("test")
    if coord.mode != "off_watch":
        errors.append("end_session() didn't return to Off Watch")
    return errors


def check_state_machine():
    """Exercises the Sleep-Mode State Machine (spec 4.11) end to end
    through _handle_event()/_handle_timeout() - the same dispatch run()
    uses - without starting any real audio threads."""
    errors = []

    def new_coord(reply):
        client = FakeClient(reply)
        return coordinator.Coordinator(coordinator.scratch_memory_copy(), client=client,
                                        out=lambda *a: None)

    # MODE: END_SESSION, applied once the reply "finishes playing" (reply_done).
    coord = new_coord("Fair winds, matey!\nMODE: END_SESSION\nMEMORY: NONE")
    coord.start_session()
    coord.handle_utterance(load_clip())
    if coord.mode != "on_watch":
        errors.append("handle_utterance shouldn't switch mode before reply_done")
    coord._handle_event("reply_done", None)
    if coord.mode != "off_watch":
        errors.append(f"MODE: END_SESSION should end the session, got mode={coord.mode!r}")
    if coord.deadline is None:
        errors.append("Off Watch should start its 15-minute nap timeout")

    # MODE: NAP, same mechanism, -> Asleep instead.
    coord = new_coord("Sleepy now, goodnight!\nMODE: NAP\nMEMORY: NONE")
    coord.start_session()
    coord.handle_utterance(load_clip())
    coord._handle_event("reply_done", None)
    if coord.mode != "asleep":
        errors.append(f"MODE: NAP should start a nap, got mode={coord.mode!r}")
    if coord.deadline is not None:
        errors.append("Asleep should have no timeout deadline")

    # Waking from Asleep goes straight to On Watch, never through Off Watch.
    coord._handle_event("wake", None)
    if coord.mode != "on_watch":
        errors.append(f"wake from Asleep should enter On Watch directly, got mode={coord.mode!r}")

    # No MODE: tag -> the ordinary 2-minute On Watch timer, mode unchanged.
    coord = new_coord("Just chatting, Captain.\nMODE: NONE\nMEMORY: NONE")
    coord.start_session()
    coord.handle_utterance(load_clip())
    coord._handle_event("reply_done", None)
    if coord.mode != "on_watch":
        errors.append("MODE: NONE shouldn't change mode")
    if coord.deadline is None:
        errors.append("MODE: NONE should still (re)start the 2-minute timer")

    # The sleep-phrase stand-in only takes effect from Off Watch...
    coord._handle_event("reply_done", None)   # already on_watch/no pending mode - harmless
    coord.end_session("test")                 # -> off_watch
    coord._handle_event("sleep_phrase", None)
    if coord.mode != "asleep":
        errors.append("sleep-phrase stand-in from Off Watch should start a nap")

    # ...not from On Watch or Asleep (the local spotter never listens for it there).
    coord = new_coord("Just chatting, Captain.\nMODE: NONE\nMEMORY: NONE")
    coord.start_session()
    coord._handle_event("sleep_phrase", None)
    if coord.mode != "on_watch":
        errors.append("sleep-phrase stand-in should be ignored while On Watch")

    # Timeouts: On Watch -> Off Watch, Off Watch -> Asleep.
    coord = new_coord("Just chatting, Captain.\nMODE: NONE\nMEMORY: NONE")
    coord.start_session()
    coord._handle_timeout()
    if coord.mode != "off_watch":
        errors.append("On Watch timeout should end the session")
    coord._handle_timeout()
    if coord.mode != "asleep":
        errors.append("Off Watch timeout should start a nap")

    return errors


class FakeMotion:
    """Records what the Coordinator asks Motion to do."""

    def __init__(self):
        self.calls = []

    def set_mode(self, mode):
        self.calls.append(("set_mode", mode))

    def fall_asleep(self, context=None):
        self.calls.append(("fall_asleep", context))


def check_asleep_entry_context():
    """Each way into Asleep tells Motion which settle-in line to play
    (spec 4.10): the sleep phrase -> goodnight_phrase, Off Watch's
    timeout -> idle_timeout, MODE: NAP -> none."""
    errors = []
    coord = coordinator.Coordinator(coordinator.scratch_memory_copy(),
                                     client=FakeClient("Sleepy now!\nMODE: NAP\nMEMORY: NONE"),
                                     out=lambda *a: None)
    coord.motion = FakeMotion()

    coord.end_session("test")
    coord._handle_event("sleep_phrase", None)
    coord._handle_event("wake", None)
    coord.end_session("test")
    coord._handle_timeout()
    coord._handle_event("wake", None)
    coord.handle_utterance(load_clip())
    coord._handle_event("reply_done", None)

    got = [c for c in coord.motion.calls if c[0] == "fall_asleep"]
    want = [("fall_asleep", "goodnight_phrase"), ("fall_asleep", "idle_timeout"), ("fall_asleep", None)]
    if got != want:
        errors.append(f"expected Motion entry contexts {want}, got {got}")
    return errors


def check_mid_reply_sentence_gap():
    """A multi-sentence reply shouldn't reopen the mic between its own
    sentences - only once the whole reply is done - or a stray sound in
    that gap can clobber _first_tag/_last_tag and silently drop the
    MODE: tag (see docs/log.md's 4.16 history, "Goodnight, Jack" live
    test, 2026-10-07)."""
    errors = []
    client = FakeClient("Aye, sweet dreams to ye, Matey. Fair winds and following seas till "
                         "morning!\nMODE: NAP\nMEMORY: NONE")
    coord = coordinator.Coordinator(coordinator.scratch_memory_copy(), client=client,
                                     out=lambda *a: None)
    coord.start_session()
    coord.handle_utterance(load_clip())
    first, last = coord._first_tag, coord._last_tag
    if first == last:
        errors.append(f"test reply didn't split into 2+ sentences: {first!r} == {last!r}")

    def pump():
        while not coord.events.empty():
            coord._handle_event(*coord.events.get())

    coord._on_playback("started", first, 0.0)
    coord._on_playback("finished", first, 1.0)   # first sentence done, more still queued
    pump()
    if coord.listener._ignore_until != float("inf"):
        errors.append("mic reopened between sentences of the same reply, not just after it")
    if coord.mode == "asleep":
        errors.append("reply_done fired early, from a mid-reply sentence boundary")

    coord._on_playback("started", last, 1.0)
    coord._on_playback("finished", last, 2.0)    # the reply's actual last sentence
    pump()
    if coord.listener._ignore_until == float("inf"):
        errors.append("mic never reopened after the whole reply finished")
    if coord.mode != "asleep":
        errors.append(f"MODE: NAP should apply once the real last sentence finishes, got {coord.mode!r}")

    return errors


def check_nonreply_clip_reopens_mic():
    """A standalone clip (Motion's own idle/excursion/settle-in wavs,
    tagged with their filename, not a (reply, i) tuple) must reopen the
    mic/spotter as soon as IT finishes, same as the reply case above -
    found live, 2026-10-11: the old check only recognized a reply's true
    last sentence or BEEP_TAG, so the mic went permanently deaf after
    the first such clip played in Off Watch/Asleep and the real
    WakeSpotter never heard the wake phrase again for the rest of that
    mode (see docs/log.md's 4.11/4.16 history)."""
    errors = []
    client = FakeClient("shouldn't be called")
    coord = coordinator.Coordinator(coordinator.scratch_memory_copy(), client=client,
                                     out=lambda *a: None)

    coord._on_playback("started", "SomeIdleClip.wav", 0.0)
    if coord.spotter._ignore_until != float("inf"):
        errors.append("spotter should go deaf once the clip starts playing")
    coord._on_playback("finished", "SomeIdleClip.wav", 1.0)
    if coord.listener._ignore_until == float("inf"):
        errors.append("mic never reopened after a non-reply clip finished (listener)")
    if coord.spotter._ignore_until == float("inf"):
        errors.append("spotter never reopened after a non-reply clip finished - "
                       "the real bug this test was written for")

    return errors


def check_late_last_sentence_race():
    """Streaming (coordinator.py's handle_utterance(), 2026-10-12) opens
    a race that couldn't happen with the old all-at-once speak(): a
    reply's sentences are queued to TTS as Haiku's text streams in, so
    the true last one isn't known until the full reply (tags included)
    has arrived - by which point, if TTS/Playback happen to be faster
    than the rest of the network round-trip, that last sentence's own
    "finished" playback event may already have come and gone while
    _last_tag still pointed at the previous reply, never matching.
    _finish_reply() must catch up immediately rather than silently
    dropping the mic reopen/reply_done - see its own comment."""
    errors = []
    coord = coordinator.Coordinator(coordinator.scratch_memory_copy(),
                                     client=FakeClient("shouldn't be called"),
                                     out=lambda *a: None)
    coord.start_session()

    reply = coord._begin_reply()
    coord._queue_sentence(reply, 0, "First sentence spoken here now.")
    coord._queue_sentence(reply, 1, "Second and last sentence spoken too.")
    # Both sentences' playback finishes before _finish_reply ever runs -
    # _last_tag is still None, so neither "finished" call below can match it.
    coord._on_playback("started", (reply, 0), 0.0)
    coord._on_playback("finished", (reply, 0), 1.0)
    coord._on_playback("started", (reply, 1), 1.0)
    coord._on_playback("finished", (reply, 1), 2.0)
    if coord.listener._ignore_until == float("inf"):
        pass   # expected so far - nothing has told _on_playback which tag is last yet

    coord._pending_mode = "END_SESSION"
    coord._finish_reply(reply, 2)   # learns the count only now, after both already finished

    while not coord.events.empty():
        coord._handle_event(*coord.events.get())

    if coord.listener._ignore_until == float("inf"):
        errors.append("mic never reopened - the race-finalized reply_done was dropped")
    if coord.mode != "off_watch":
        errors.append(f"MODE: END_SESSION should still apply after the race, got mode={coord.mode!r}")

    return errors


def check_live():
    scratch = coordinator.scratch_memory_copy()
    out = []
    coord = coordinator.Coordinator(scratch, out=out.append)
    coord.start_session()
    coord.handle_utterance(load_clip())
    print("  " + "\n  ".join(out))
    reply = [line for line in out if line.startswith("Jack: ")]
    if not reply or len(reply[0]) < 10:
        return [f"no reply from live Haiku: {out!r}"]
    return []


if __name__ == "__main__":
    errors = (check_offline() + check_state_machine() + check_asleep_entry_context()
              + check_mid_reply_sentence_gap() + check_nonreply_clip_reopens_mic()
              + check_late_last_sentence_race())
    live = "--live" in sys.argv[1:]
    if live and not errors:
        errors = check_live()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: coordinator transcribes, calls Haiku, saves memory to scratch only, rejects noise, "
          "the Sleep-Mode State Machine transitions correctly (telling Motion how Asleep was "
          "entered), the mic stays deaf across a "
          "multi-sentence reply's own sentence gaps but reopens after, a standalone "
          "clip (Motion's idle/excursion/settle-in wavs) reopens the mic and spotter too, and a "
          "streamed reply's own last sentence finishing before it's known to be last still "
          "reopens the mic/fires reply_done correctly"
          + (", live Haiku replied" if live else ""))
