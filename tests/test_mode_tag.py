"""Re-runnable test for docs/tests.md: "MODE: end-session/nap tag".

Verifies split_mode_line() correctly splits the MODE: meta-tag off a
reply that's already had MEMORY: split off, fails closed to None on a
missing/malformed line, and that take_turn() wires it through into
Turn.mode (with a fake Haiku client - no real API, no hardware).

Run: venv/bin/python tests/test_mode_tag.py
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrate import split_mode_line, take_turn  # noqa: E402


class FakeClient:
    """Stands in for anthropic.Anthropic(): records requests, returns a canned reply."""

    def __init__(self, reply):
        self.reply = reply
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)])


def check_split_mode_line():
    errors = []

    text, mode = split_mode_line("Fair winds, matey.\nMODE: END_SESSION")
    if (text, mode) != ("Fair winds, matey.", "END_SESSION"):
        errors.append(f"END_SESSION not split correctly, got {(text, mode)!r}")

    text, mode = split_mode_line("Sleepy now, goodnight.\nMODE: nap")
    if (text, mode) != ("Sleepy now, goodnight.", "NAP"):
        errors.append(f"lowercase mode not normalized/split, got {(text, mode)!r}")

    text, mode = split_mode_line("Still here, Captain.\nMODE: NONE")
    if (text, mode) != ("Still here, Captain.", "NONE"):
        errors.append(f"explicit NONE not split correctly, got {(text, mode)!r}")

    text, mode = split_mode_line("Just an ordinary reply.")
    if (text, mode) != ("Just an ordinary reply.", None):
        errors.append(f"missing MODE: line should fail closed to None, got {(text, mode)!r}")

    text, mode = split_mode_line("An old reply with no tag at all.")
    if mode is not None:
        errors.append("malformed/absent MODE: line should fail closed to None")

    return errors


def check_take_turn_wires_mode():
    errors = []

    client = FakeClient("Fair winds till next we meet, matey.\nMODE: END_SESSION\nMEMORY: NONE")
    turn = take_turn(client, [], "Goodnight Jack")
    if turn.mode != "END_SESSION":
        errors.append(f"expected Turn.mode == 'END_SESSION', got {turn.mode!r}")
    if "MODE:" in turn.spoken or "MEMORY:" in turn.spoken:
        errors.append(f"spoken reply should have both tag lines stripped, got {turn.spoken!r}")

    client = FakeClient("Just chatting along, Captain.\nMODE: NONE\nMEMORY: NONE")
    turn = take_turn(client, [], "How are you")
    if turn.mode is not None:
        errors.append(f"explicit MODE: NONE should surface as Turn.mode is None, got {turn.mode!r}")

    client = FakeClient("An old-style reply with no MODE: line.\nMEMORY: NONE")
    turn = take_turn(client, [], "Hello")
    if turn.mode is not None:
        errors.append(f"a reply with no MODE: line should fail closed to None, got {turn.mode!r}")

    return errors


if __name__ == "__main__":
    errors = check_split_mode_line() + check_take_turn_wires_mode()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: MODE: tag splits correctly and take_turn() wires it into Turn.mode")
