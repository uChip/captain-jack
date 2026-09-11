"""Captain Jack orchestration: memory-driven conversation over the Haiku API.

Implements the read/write loop from docs/captain-jack-memory-design.md.
Text-only CLI for now - audio I/O, reSpeaker DoA, and the Pi<->Arduino
serial link are separate, hardware-dependent next steps (see CLAUDE.md).
"""

import re
import sys
from datetime import date
from pathlib import Path

import anthropic

MEMORY_DIR = Path(__file__).parent / "memory"
IDENTITY_PATH = MEMORY_DIR / "identity.md"
MEMORY_PATH = MEMORY_DIR / "memory.md"

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1024

MEMORY_LINE_RE = re.compile(r"^MEMORY:\s*(.+)$", re.IGNORECASE)
TAG_RE = re.compile(
    r"^\[(?:household:(?P<name>[A-Za-z][\w'-]*)|(?P<tag>joke|automation))\]\s+(?P<fact>.+)$"
)

SECTION_HEADINGS = {
    "household": "Household",
    "joke": "Running jokes & preferences",
    "automation": "Home automation preferences",
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


def get_reply(client: anthropic.Anthropic, history: list[dict]) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=load_system_prompt(),
        messages=history,
    )
    return "".join(block.text for block in response.content if block.type == "text")


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

        history.append({"role": "user", "content": user_input})
        try:
            reply = get_reply(client, history)
        except anthropic.APIConnectionError:
            print("[error] network problem reaching the API", file=sys.stderr)
            history.pop()
            continue
        except anthropic.APIStatusError as e:
            print(f"[error] {e.status_code}: {e.message}", file=sys.stderr)
            history.pop()
            continue
        history.append({"role": "assistant", "content": reply})

        spoken, raw_memory = split_memory_line(reply)
        print(f"Jack: {spoken}")

        if raw_memory:
            proposal = parse_memory_proposal(raw_memory)
            if proposal:
                section, name, fact = proposal
                if save_memory(section, name, fact):
                    label = f"{section}:{name}" if name else section
                    print(f"  [memory saved - {label}: {fact}]")


if __name__ == "__main__":
    main()
