"""Re-runnable test for docs/tests.md: "[home] tag save path".

Verifies parse_memory_proposal() and save_memory() correctly parse a
`[home]` proposal and file it under memory.md's "## Home" section,
without touching the real memory/memory.md - everything runs against a
scratch copy in a temp dir.

Run: venv/bin/python tests/test_home_memory_save.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrate import _finish_turn, parse_memory_proposal, save_memory  # noqa: E402

REPO_MEMORY = Path(__file__).parent.parent / "memory" / "memory.md"


def run():
    parsed = parse_memory_proposal("[home] Sun Lakes, Arizona")
    assert parsed == ("home", None, "Sun Lakes, Arizona"), parsed

    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "memory.md"
        shutil.copy(REPO_MEMORY, scratch)

        saved = save_memory(
            "home", None, "Tucson, Arizona (test)", memory_path=scratch
        )
        assert saved is True, "expected a new fact to be saved"

        text = scratch.read_text()
        assert "## Home" in text
        assert "Tucson, Arizona (test)" in text

        dup = save_memory(
            "home", None, "Tucson, Arizona (test)", memory_path=scratch
        )
        assert dup is False, "expected a duplicate fact to be skipped"

    # Every turn's memory decision is reported, saved or not.
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(REPO_MEMORY, Path(tmp) / "memory.md")
        cases = [
            ("Aye.", "no MEMORY line"),
            ("Aye.\nMEMORY: NONE", "NONE"),
            ("Aye.\nMEMORY: [recipe] stew", "rejected, bad tag: [recipe] stew"),
            ("Aye.\nMEMORY: [household:Nobody] likes tea",
             "not saved, already listed or no such person: [household:Nobody] likes tea"),
            ("Aye.\nMEMORY: [household:Chip] likes tea", ""),
            ("Aye.\nMEMORY: [household:Chip] likes tea",
             "not saved, already listed or no such person: [household:Chip] likes tea"),
        ]
        for reply, want in cases:
            turn = _finish_turn(reply, Path(tmp))
            assert turn.memory_note == want, (reply, turn.memory_note)

    print("PASS: [home] tag parses, saves, and dedups correctly; every memory decision is reported")


if __name__ == "__main__":
    run()
