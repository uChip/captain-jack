"""Captain Jack orchestration: memory-driven conversation over the Haiku API.

Implements the read/write loop from docs/captain-jack-memory-design.md.
take_turn() is one full conversational turn; the text CLI below calls
it. stream_turn() is the same turn, but speaks the reply sentence by
sentence as it streams in rather than waiting for all of it - what the
voice Coordinator (coordinator.py, spec section 4.16) calls instead.
"""

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import anthropic

from tts import MIN_SENTENCE_CHARS, SENTENCE_END_RE, clean_text

MEMORY_DIR = Path(__file__).parent / "memory"
IDENTITY_PATH = MEMORY_DIR / "identity.md"
MEMORY_PATH = MEMORY_DIR / "memory.md"

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1024

MEMORY_LINE_RE = re.compile(r"^MEMORY:\s*(.+)$", re.IGNORECASE)
TAG_RE = re.compile(
    r"^\[(?:household:(?P<name>[A-Za-z][\w'-]*)|(?P<tag>joke|automation|home))\]\s+(?P<fact>.+)$"
)

# Spec 4.11: Haiku's own understanding of session-end/nap intent, read from
# a meta-tag on the reply rather than a fixed phrase - the Coordinator only
# needs the local wake/sleep-phrase spotter to listen for fixed phrases
# while Jack isn't already On Watch. Sits right before the MEMORY: line,
# which stays the true last line.
MODE_LINE_RE = re.compile(r"^MODE:\s*(NONE|END_SESSION|NAP)\s*$", re.IGNORECASE)

SECTION_HEADINGS = {
    "household": "Household",
    "joke": "Running jokes & preferences",
    "automation": "Home automation preferences",
    "home": "Home",
}


def load_system_prompt(memory_dir: Path = MEMORY_DIR) -> str:
    identity = (memory_dir / "identity.md").read_text()
    memory = (memory_dir / "memory.md").read_text()
    return f"{identity}\n\n---\n\n{memory}"


FENCE_RE = re.compile(r"^```\w*$")


def split_memory_line(reply: str) -> tuple[str, str | None]:
    """Split Jack's trailing `MEMORY: ...` line off the spoken reply.

    Tolerates Haiku wrapping the line in a ``` code fence (observed in
    practice, inconsistently) - otherwise the fenced block leaks into the
    spoken reply verbatim and the memory proposal is silently lost.
    """
    lines = reply.rstrip().splitlines()
    i = len(lines) - 1
    saw_closing_fence = False
    while i >= 0:
        stripped = lines[i].strip()
        if stripped == "":
            i -= 1
            continue
        if FENCE_RE.match(stripped):
            saw_closing_fence = True
            i -= 1
            continue
        break
    if i < 0:
        return reply.strip(), None

    match = MEMORY_LINE_RE.match(lines[i].strip())
    if not match:
        return reply.strip(), None

    cut = i
    if saw_closing_fence:
        j = i - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        if j >= 0 and FENCE_RE.match(lines[j].strip()):
            cut = j

    spoken = "\n".join(lines[:cut]).rstrip()
    return spoken, match.group(1).strip()


def split_mode_line(text: str) -> tuple[str, str | None]:
    """Split Jack's trailing `MODE: ...` meta-tag off text that's already
    had MEMORY: split off (MODE: is the line before it, not the true last
    line - see MODE_LINE_RE above). Returns (text, None) if the last line
    isn't a recognized MODE: line - e.g. older replies or a malformed one
    fail closed to None (treated as NONE) rather than guessing.
    """
    lines = text.rstrip().splitlines()
    if not lines:
        return text, None
    match = MODE_LINE_RE.match(lines[-1].strip())
    if not match:
        return text, None
    return "\n".join(lines[:-1]).rstrip(), match.group(1).upper()


def split_tags(reply: str) -> tuple[str, str | None, str | None]:
    """Split both trailing meta-tag lines off a reply, regardless of
    which order Haiku actually put them in.

    Documented/intended order is MODE: right before the true-last
    MEMORY: line (see MODE_LINE_RE above), but Haiku doesn't always keep
    to it - a live test (2026-10-11, see docs/log.md's 4.16 history)
    caught MEMORY: NONE leaking into speech because it came before
    MODE:, so split_memory_line (which only ever looks at the literal
    last line) never found it. Tries MODE: first: if it turns out to be
    the true last line, MEMORY: (if present) is now exposed as the new
    last line for split_memory_line to find correctly either way;
    otherwise falls back to the documented order unchanged.
    """
    spoken, mode = split_mode_line(reply)
    if mode is None:
        spoken, raw_memory = split_memory_line(reply)
        spoken, mode = split_mode_line(spoken)
    else:
        spoken, raw_memory = split_memory_line(spoken)
    return spoken, raw_memory, mode


def parse_memory_proposal(raw: str):
    """Validate a proposed MEMORY line against the tag allowlist.

    Returns (section, name_or_None, fact), or None if it's NONE or doesn't
    match one of the three allowed tags - malformed/unrecognized fails
    closed per docs/captain-jack-memory-design.md.
    """
    if raw.strip().upper() == "NONE":
        return None
    match = TAG_RE.match(raw.strip())
    if not match:
        return None
    fact = match.group("fact").strip()
    if not fact:
        return None
    if match.group("name"):
        return "household", match.group("name"), fact
    return match.group("tag"), None, fact


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    """Line-index range of the body of a top-level '## heading' section."""
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"## {heading}":
            start = i + 1
            break
    if start is None:
        raise ValueError(f"section {heading!r} not found in memory.md")
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return start, end


def _is_duplicate(existing_lines: list[str], fact: str) -> bool:
    needle = fact.strip().lower()
    return any(needle in line.lower() for line in existing_lines)


def _insertion_point(lines: list[str], start: int, end: int) -> int:
    """Index right after the last non-blank line in [start, end) - skips
    trailing blank lines so appends land next to real content, not after
    a gap left by a previous save's blank-line normalization."""
    idx = end
    while idx > start and lines[idx - 1].strip() == "":
        idx -= 1
    return idx


def _normalize_blank_lines(lines: list[str]) -> list[str]:
    """Ensure a blank line before headings and collapse repeated blank lines."""
    out: list[str] = []
    for line in lines:
        if line.startswith("#") and out and out[-1].strip() != "":
            out.append("")
        if line.strip() == "" and out and out[-1].strip() == "":
            continue
        out.append(line)
    return out


def save_memory(
    section: str, name: str | None, fact: str, memory_path: Path = MEMORY_PATH
) -> bool:
    """Append fact to memory.md. Returns False if skipped as a duplicate, or
    (for household facts) if `name` has no existing "### Name" subsection."""
    lines = memory_path.read_text().splitlines()
    entry = f"- {date.today().isoformat()}: {fact}"

    if section == "household":
        start, end = _section_bounds(lines, SECTION_HEADINGS["household"])
        sub_start = next(
            (
                i + 1
                for i in range(start, end)
                if lines[i].strip().lower() == f"### {name}".lower()
            ),
            None,
        )
        if sub_start is None:
            # No existing subsection for this name - discard rather than
            # auto-create. A model-proposed name isn't trustworthy enough to
            # mint a new household member; that's a human-only decision
            # (add the "### Name" heading once, by hand).
            return False
        sub_end = next(
            (i for i in range(sub_start, end) if lines[i].startswith("### ")),
            end,
        )
        if _is_duplicate(lines[sub_start:sub_end], fact):
            return False
        at = _insertion_point(lines, sub_start, sub_end)
        lines[at:at] = [entry]
    else:
        start, end = _section_bounds(lines, SECTION_HEADINGS[section])
        if _is_duplicate(lines[start:end], fact):
            return False
        at = _insertion_point(lines, start, end)
        lines[at:at] = [entry]

    lines = _normalize_blank_lines(lines)
    memory_path.write_text("\n".join(lines) + "\n")
    return True


def household_names(memory_dir: Path = MEMORY_DIR) -> list[str]:
    """Names of the "### Name" subsections under memory.md's Household."""
    lines = (memory_dir / "memory.md").read_text().splitlines()
    start, end = _section_bounds(lines, SECTION_HEADINGS["household"])
    return [line[4:].strip() for line in lines[start:end] if line.startswith("### ")]


def get_reply(client: anthropic.Anthropic, history: list[dict], memory_dir: Path = MEMORY_DIR) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=load_system_prompt(memory_dir),
        messages=history,
    )
    return "".join(block.text for block in response.content if block.type == "text")


class SpeechStreamer:
    """Splits Haiku's reply into speakable sentences as its text streams
    in, instead of waiting for the full reply - the latency lever flagged
    in spec 4.16 build step 5 and docs/log.md's 4.16 history. Applies the
    same merge rule as `tts.split_sentences()` (a too-short fragment, e.g.
    "Aye!", gets merged forward into the next sentence rather than spoken
    alone) incrementally, instead of on the whole text at once.

    Stops cold at the first newline: a real spoken reply is single-line
    prose (see identity.md's style rules / split_tags()'s own
    assumptions), and MODE:/MEMORY: always start on their own line right
    after it, so a newline reliably marks "no more speech after this
    point" without waiting for the rest of the reply - including the
    tag lines themselves - to arrive.

    on_sentence(text) is called once per sentence, in order, as soon as
    each is ready. finish() must be called once after the stream ends,
    in case a malformed reply (e.g. an old-style one with no tags at
    all) never produces a newline to trigger the above.

    One accepted difference from the batch split_sentences(): if the
    very last fragment of the reply is still too short to stand alone
    once the stream ends, it's spoken as its own (slightly short)
    sentence rather than merged backward into the previous one - that
    sentence may already be synthesizing or playing by then, so there's
    nothing left to merge it into.
    """

    def __init__(self, on_sentence):
        self.on_sentence = on_sentence
        self._text = ""     # streamed text not yet searched for a sentence boundary
        self._carry = ""    # sentence(s) accumulated but still too short to emit
        self.done = False

    def feed(self, chunk: str):
        if self.done:
            return
        self._text += chunk
        if "\n" in self._text:
            self._text, _, _ = self._text.partition("\n")
            self._drain(final=True)
            self.done = True
            return
        self._drain(final=False)

    def finish(self):
        """Call once after the stream ends - a no-op unless feed() never
        saw a newline at all (a malformed/tagless reply)."""
        if not self.done:
            self._drain(final=True)
            self.done = True

    def _drain(self, final: bool):
        while True:
            m = SENTENCE_END_RE.search(self._text)
            if not m:
                break
            self._emit(self._text[:m.start()])
            self._text = self._text[m.end():]
        if final:
            self._emit(self._text)
            self._text = ""
            if self._carry:
                self.on_sentence(self._carry)
                self._carry = ""

    def _emit(self, piece: str):
        piece = clean_text(piece)
        if not piece:
            return
        self._carry = f"{self._carry} {piece}".strip()
        if len(self._carry) >= MIN_SENTENCE_CHARS:
            self.on_sentence(self._carry)
            self._carry = ""


def get_reply_stream(
    client: anthropic.Anthropic, history: list[dict], on_sentence, memory_dir: Path = MEMORY_DIR
) -> str:
    """Like get_reply(), but calls on_sentence(text) for each spoken
    sentence as soon as it's streamed in, via SpeechStreamer. Returns the
    full raw reply (tags included), same as get_reply() - split_tags()
    still happens in stream_turn(), same as take_turn()."""
    streamer = SpeechStreamer(on_sentence)
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=load_system_prompt(memory_dir),
        messages=history,
    ) as stream:
        for text in stream.text_stream:
            streamer.feed(text)
        reply = stream.get_final_text()
    streamer.finish()
    return reply


@dataclass
class Turn:
    spoken: str             # what Jack says aloud
    saved: str | None       # "section: fact" if a memory was saved, else None
    mode: str | None        # "END_SESSION" or "NAP" if Jack signaled either, else None


def _finish_turn(reply: str, memory_dir: Path) -> Turn:
    """Shared tail of take_turn()/stream_turn(): split off and save any
    proposed memory, once the full reply (and history) is in hand."""
    spoken, raw_memory, mode = split_tags(reply)
    if mode == "NONE":
        mode = None
    saved = None
    if raw_memory:
        proposal = parse_memory_proposal(raw_memory)
        if proposal:
            section, name, fact = proposal
            if save_memory(section, name, fact, memory_dir / "memory.md"):
                label = f"{section}:{name}" if name else section
                saved = f"{label}: {fact}"
    return Turn(spoken, saved, mode)


def take_turn(
    client: anthropic.Anthropic, history: list[dict], user_text: str, memory_dir: Path = MEMORY_DIR
) -> Turn:
    """One conversational turn: call Haiku, split off and save any memory.

    Appends both sides to history. On an API error, history is left as it
    was and the anthropic exception propagates to the caller.
    """
    history.append({"role": "user", "content": user_text})
    try:
        reply = get_reply(client, history, memory_dir)
    except anthropic.APIError:
        history.pop()
        raise
    history.append({"role": "assistant", "content": reply})
    return _finish_turn(reply, memory_dir)


def stream_turn(
    client: anthropic.Anthropic, history: list[dict], user_text: str, on_sentence, memory_dir: Path = MEMORY_DIR
) -> Turn:
    """Like take_turn(), but speaks the reply as it streams in rather
    than waiting for Haiku to finish it first - cuts the delay to first
    audio for any reply with 2+ sentences, since TTS can start
    synthesizing the first one while Haiku is still generating the rest.
    on_sentence(text) is called once per spoken sentence, in order,
    typically well before the trailing MODE:/MEMORY: tags (let alone the
    rest of a longer reply) have finished streaming in. Everything else
    - history, tag parsing, memory saving - is identical to take_turn().
    """
    history.append({"role": "user", "content": user_text})
    try:
        reply = get_reply_stream(client, history, on_sentence, memory_dir)
    except anthropic.APIError:
        history.pop()
        raise
    history.append({"role": "assistant", "content": reply})
    return _finish_turn(reply, memory_dir)


def main():
    client = anthropic.Anthropic()
    history: list[dict] = []
    print("Captain Jack is listening. Ctrl+D to quit.")
    while True:
        try:
            user_input = input("> ").strip()
        except EOFError:
            print()
            break
        if not user_input:
            continue

        try:
            turn = take_turn(client, history, user_input)
        except anthropic.APIConnectionError:
            print("[error] network problem reaching the API", file=sys.stderr)
            continue
        except anthropic.APIStatusError as e:
            print(f"[error] {e.status_code}: {e.message}", file=sys.stderr)
            continue

        print(f"Jack: {turn.spoken}")
        if turn.saved:
            print(f"  [memory saved - {turn.saved}]")


if __name__ == "__main__":
    main()
