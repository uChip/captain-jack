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


class FakeClient:
    """Stands in for anthropic.Anthropic(): records requests, returns a canned reply."""

    def __init__(self, reply):
        self.reply = reply
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)])


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
    errors = check_offline()
    live = "--live" in sys.argv[1:]
    if live and not errors:
        errors = check_live()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: coordinator transcribes, calls Haiku, saves memory to scratch only, rejects noise"
          + (", live Haiku replied" if live else ""))
