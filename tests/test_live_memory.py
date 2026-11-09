"""Re-runnable test for docs/tests.md: "Live memory outside the repo".

Checks orchestrate.py's live-memory handling (CLAUDE.md item 11, step 4)
against a temp JACK_DATA, never ~/jack-data:
  - live_memory_dir() seeds memory.md from the repo template the first
    time, and never overwrites an existing one afterwards;
  - save_memory() writes atomically: the new fact lands, no .tmp file is
    left behind, and the old file survives a write that fails midway;
  - load_system_prompt() uses the repo's identity.md unless the memory
    dir carries its own (scratch copies);
  - speaker-ID voiceprints default to JACK_DATA/voiceprints.

Run: venv/bin/python tests/test_live_memory.py
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

tmp = tempfile.TemporaryDirectory()
os.environ["JACK_DATA"] = str(Path(tmp.name) / "jack-data")
sys.path.insert(0, str(Path(__file__).parent.parent))

import orchestrate  # noqa: E402
from orchestrate import (IDENTITY_PATH, MEMORY_PATH, TEMPLATE_DIR,  # noqa: E402
                         live_memory_dir, load_system_prompt, save_memory)


def run():
    data = Path(os.environ["JACK_DATA"])
    assert MEMORY_PATH == data / "memory.md", MEMORY_PATH
    assert not data.exists()

    d = live_memory_dir()
    assert d == data and MEMORY_PATH.read_text() == (TEMPLATE_DIR / "memory.md").read_text()

    MEMORY_PATH.write_text(MEMORY_PATH.read_text() + "\n<!-- live edit -->\n")
    live_memory_dir()
    assert "live edit" in MEMORY_PATH.read_text(), "seeding overwrote live memory"

    assert save_memory("joke", None, "Test parrot fact (live memory test)")
    assert "Test parrot fact" in MEMORY_PATH.read_text()
    assert not list(data.glob("*.tmp")), list(data.glob("*.tmp"))

    before = MEMORY_PATH.read_text()
    with mock.patch.object(orchestrate.os, "replace", side_effect=OSError("power cut")):
        try:
            save_memory("joke", None, "Lost fact")
        except OSError:
            pass
    assert MEMORY_PATH.read_text() == before, "a failed save changed memory.md"

    prompt = load_system_prompt(d)
    assert prompt.startswith(IDENTITY_PATH.read_text()), "repo identity.md not used"
    (d / "identity.md").write_text("OWN IDENTITY")
    assert load_system_prompt(d).startswith("OWN IDENTITY")

    from speaker_id import VOICEPRINTS_DIR
    assert VOICEPRINTS_DIR == data / "voiceprints", VOICEPRINTS_DIR

    print("PASS: live memory seeds once from the template and is never overwritten; saves are atomic "
          "(no temp left, a failed save leaves the old file); repo identity.md unless the dir has its own; "
          "voiceprints under JACK_DATA")


if __name__ == "__main__":
    run()
