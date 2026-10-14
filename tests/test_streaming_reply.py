"""Re-runnable test for docs/tests.md: "Streamed Haiku replies".

Verifies orchestrate.py's SpeechStreamer (the incremental sentence
splitter streaming replies on, see docs/log.md's 4.16 history) and
stream_turn() (the streaming counterpart of take_turn()):
  - fed in any chunk size, SpeechStreamer produces the same sentences as
    the batch tts.split_sentences() - except for one accepted, documented
    difference (a too-short trailing fragment can't be merged backward
    into an already-dispatched sentence);
  - it stops at the first newline, never leaking MODE:/MEMORY: text into
    a spoken sentence;
  - stream_turn() calls on_sentence() progressively, as the reply
    streams in, not only once the whole thing (including the trailing
    tags) has arrived - the entire point of streaming;
  - stream_turn() returns the same Turn take_turn() would for the same
    reply text, and leaves history correctly rolled back on an API error
    partway through the stream.

Run: venv/bin/python tests/test_streaming_reply.py
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic  # noqa: E402

from orchestrate import SpeechStreamer, stream_turn, take_turn  # noqa: E402
from tts import split_sentences  # noqa: E402

SAMPLE_REPLIES = [
    "Aye, sweet dreams to ye, Matey. Fair winds and following seas till morning!\nMODE: NAP\nMEMORY: NONE",
    "Just chatting, Captain.\nMODE: NONE\nMEMORY: NONE",
    "Avast! A little from Al, ye say? Blow me down, I be needin a touch more detail there, "
    "Matey.\nMODE: NONE\nMEMORY: NONE",
    "Aye.\nMODE: NONE\nMEMORY: NONE",
]


class FakeStream:
    """Stands in for anthropic's MessageStream. chunks lets a test control
    exactly how the text is split across text_stream iterations - a real
    stream can split anywhere, including mid-word."""

    def __init__(self, reply, chunks):
        self.reply = reply
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        return iter(self.chunks)

    def get_final_text(self):
        return self.reply


class FakeClient:
    """Stands in for anthropic.Anthropic(): records requests, returns a
    canned reply - or raises partway through, for the error-path check."""

    def __init__(self, reply, chunk_size=1, fail_after=None, stream_cls=FakeStream):
        self.reply = reply
        self.chunk_size = chunk_size
        self.fail_after = fail_after
        self.stream_cls = stream_cls
        self.requests = []
        self.messages = SimpleNamespace(create=self._create, stream=self._stream)

    def _chunks(self):
        chunks = [self.reply[i:i + self.chunk_size] for i in range(0, len(self.reply), self.chunk_size)]
        if self.fail_after is not None:
            chunks = chunks[:self.fail_after] + [RuntimeError]
        return chunks

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)])

    def _stream(self, **kwargs):
        self.requests.append(kwargs)
        return self.stream_cls(self.reply, self._chunks())


class RaisingFakeStream(FakeStream):
    """Like FakeStream, but a sentinel RuntimeError in chunks becomes a
    real anthropic.APIError raised mid-iteration - simulating a network
    failure partway through a reply, after some sentences already
    streamed in."""

    @property
    def text_stream(self):
        def gen():
            for c in self.chunks:
                if c is RuntimeError:
                    raise anthropic.APIConnectionError(request=SimpleNamespace())
                yield c
        return gen()


def check_speech_streamer_matches_batch():
    """SpeechStreamer, fed in various chunk sizes (including the
    strictest case, one character at a time), should produce the same
    sentences as the batch split_sentences() - for the spoken text, i.e.
    everything before the first newline."""
    errors = []
    for reply in SAMPLE_REPLIES:
        spoken = reply.split("\n")[0]
        want = split_sentences(spoken)
        for chunk_size in (1, 3, 7, 1000):
            got = []
            streamer = SpeechStreamer(got.append)
            for i in range(0, len(reply), chunk_size):
                streamer.feed(reply[i:i + chunk_size])
            streamer.finish()
            if got != want:
                errors.append(f"chunk={chunk_size}, reply={reply!r}: got {got!r}, want {want!r}")
    return errors


def check_speech_streamer_tail_fragment_difference():
    """The one accepted, documented difference from split_sentences():
    a too-short trailing fragment with nothing after it can't be merged
    backward into an already-dispatched sentence, so it's spoken as its
    own (slightly short) final sentence instead."""
    errors = []
    reply = "This is a perfectly normal full sentence here. Aye!\nMODE: NONE\nMEMORY: NONE"
    want_batch = ["This is a perfectly normal full sentence here. Aye!"]
    want_streamed = ["This is a perfectly normal full sentence here.", "Aye!"]

    spoken = reply.split("\n")[0]
    got_batch = split_sentences(spoken)
    if got_batch != want_batch:
        errors.append(f"split_sentences() behavior assumed by this test changed: {got_batch!r}")

    got_streamed = []
    streamer = SpeechStreamer(got_streamed.append)
    for ch in reply:
        streamer.feed(ch)
    streamer.finish()
    if got_streamed != want_streamed:
        errors.append(f"streamed tail-fragment handling changed: got {got_streamed!r}, want {want_streamed!r}")
    return errors


def check_speech_streamer_stops_at_newline():
    """No tag text should ever reach on_sentence(), regardless of
    whether MODE:/MEMORY: lines happen to contain sentence-ending
    punctuation of their own."""
    errors = []
    got = []
    streamer = SpeechStreamer(got.append)
    streamer.feed("Just an ordinary reply.\nMODE: NONE\nMEMORY: [joke] Something. With periods.\n")
    streamer.finish()
    if got != ["Just an ordinary reply."]:
        errors.append(f"tag text leaked into on_sentence(): {got!r}")
    return errors


def check_stream_turn_calls_sentences_incrementally():
    """The entire point of streaming: on_sentence() must be called for
    the first sentence before the rest of the reply (the second
    sentence, let alone the trailing tags) has finished arriving - not
    just once at the very end."""
    errors = []
    reply = SAMPLE_REPLIES[0]
    client = FakeClient(reply, chunk_size=1)

    seen = []       # (sentence, chunks_consumed_so_far) pairs
    consumed = 0
    orig_stream = client.messages.stream

    def counting_stream(**kwargs):
        stream = orig_stream(**kwargs)
        chunks = stream.chunks

        def counting_chunks():
            nonlocal consumed
            for c in chunks:
                consumed += 1
                yield c
        stream.chunks = counting_chunks()
        return stream
    client.messages.stream = counting_stream

    def on_sentence(text):
        seen.append((text, consumed))

    turn = stream_turn(client, [], "Can we chat", on_sentence)

    if len(seen) < 2:
        errors.append(f"expected 2 sentences from a 2-sentence reply, got {seen!r}")
        return errors
    first_sentence, chunks_when_first_seen = seen[0]
    if chunks_when_first_seen >= len(reply):
        errors.append("first sentence wasn't emitted until the whole reply had streamed in - "
                       f"no latency benefit (consumed {chunks_when_first_seen}/{len(reply)} chunks)")
    if turn.mode != "NAP":
        errors.append(f"expected Turn.mode == 'NAP', got {turn.mode!r}")
    return errors


def check_stream_turn_matches_take_turn():
    """stream_turn() and take_turn(), given the same reply text, should
    agree on Turn - streaming how the reply arrives shouldn't change
    what it means."""
    errors = []
    for reply in SAMPLE_REPLIES:
        want = take_turn(FakeClient(reply), [], "hello")
        sentences = []
        got = stream_turn(FakeClient(reply, chunk_size=1), [], "hello", sentences.append)
        if got != want:
            errors.append(f"reply={reply!r}: stream_turn {got!r} != take_turn {want!r}")
    return errors


def check_stream_turn_error_rolls_back_history():
    """A network failure partway through streaming (after some
    sentences already arrived) should still leave history exactly as
    take_turn()'s own error path does - the failed turn never happened,
    as far as history is concerned."""
    errors = []
    reply = SAMPLE_REPLIES[0]
    client = FakeClient(reply, chunk_size=1, fail_after=40, stream_cls=RaisingFakeStream)

    history = [{"role": "user", "content": "earlier turn"},
               {"role": "assistant", "content": "earlier reply"}]
    before = list(history)
    seen = []
    try:
        stream_turn(client, history, "hello", seen.append)
        errors.append("expected an anthropic.APIError to propagate")
    except anthropic.APIError:
        pass
    if history != before:
        errors.append(f"history should be rolled back on error, got {history!r}")
    if not seen:
        errors.append("expected at least one sentence to have streamed in before the failure")
    return errors


if __name__ == "__main__":
    errors = (check_speech_streamer_matches_batch()
              + check_speech_streamer_tail_fragment_difference()
              + check_speech_streamer_stops_at_newline()
              + check_stream_turn_calls_sentences_incrementally()
              + check_stream_turn_matches_take_turn()
              + check_stream_turn_error_rolls_back_history())
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: SpeechStreamer matches split_sentences() (bar one documented tail-fragment "
          "difference) and stops cleanly at the MODE:/MEMORY: boundary; stream_turn() calls "
          "on_sentence() progressively, agrees with take_turn() on the same reply, and rolls "
          "back history on a mid-stream API error")
