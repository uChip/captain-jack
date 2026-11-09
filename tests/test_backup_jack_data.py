"""Re-runnable test for docs/tests.md: "Daily data backup".

Runs deploy/backup-jack-data.sh against a temp JACK_DATA, never
~/jack-data, and checks:
  - the first run snapshots memory.md and voiceprints/, not jack.env;
  - a run with nothing changed writes no new snapshot;
  - a change to memory.md (or a voiceprint) writes a new one;
  - only the newest KEEP snapshots are kept;
  - a leftover .tmp-* dir from an interrupted run is cleared;
  - an empty data dir is an error, not an empty snapshot.

Run: venv/bin/python tests/test_backup_jack_data.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "deploy" / "backup-jack-data.sh"


def backup(data, stamp, keep=30):
    env = dict(os.environ, JACK_DATA=str(data), BACKUP_STAMP=stamp, KEEP=str(keep))
    return subprocess.run([str(SCRIPT)], env=env, capture_output=True, text=True)


def snapshots(data):
    return sorted(p.name for p in (data / "backups").iterdir())


def run():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "jack-data"
        (data / "voiceprints" / "Chip").mkdir(parents=True)
        (data / "memory.md").write_text("# memory\n- fact one\n")
        (data / "voiceprints" / "Chip" / "embedding.npy").write_bytes(b"\x01\x02")
        (data / "jack.env").write_text("ANTHROPIC_API_KEY=secret\n")

        r = backup(data, "2026-11-09_033000")
        assert r.returncode == 0, r.stderr
        snap = data / "backups" / "2026-11-09_033000"
        assert (snap / "memory.md").read_text() == "# memory\n- fact one\n"
        assert (snap / "voiceprints" / "Chip" / "embedding.npy").read_bytes() == b"\x01\x02"
        assert not (snap / "jack.env").exists(), "API keys must not be backed up"

        r = backup(data, "2026-11-10_033000")
        assert r.returncode == 0 and "unchanged" in r.stdout, r.stdout
        assert snapshots(data) == ["2026-11-09_033000"]

        (data / "memory.md").write_text("# memory\n- fact one\n- fact two\n")
        backup(data, "2026-11-11_033000")
        assert snapshots(data) == ["2026-11-09_033000", "2026-11-11_033000"]

        (data / "voiceprints" / "Chip" / "embedding.npy").write_bytes(b"\x03")
        backup(data, "2026-11-12_033000")
        assert len(snapshots(data)) == 3

        (data / "backups" / ".tmp-leftover").mkdir()
        for day in (13, 14, 15):
            (data / "memory.md").write_text(f"# memory\n- day {day}\n")
            r = backup(data, f"2026-11-{day}_033000", keep=4)
            assert r.returncode == 0, r.stderr
        assert snapshots(data) == ["2026-11-12_033000", "2026-11-13_033000",
                                   "2026-11-14_033000", "2026-11-15_033000"], snapshots(data)
        assert (data / "backups" / "2026-11-15_033000" / "memory.md").read_text() == "# memory\n- day 15\n"

        empty = Path(tmp) / "empty"
        empty.mkdir()
        r = backup(empty, "2026-11-09_033000")
        assert r.returncode != 0 and "nothing to back up" in r.stdout, r.stdout
        assert snapshots(empty) == []

    print("PASS: backup snapshots only on change, skips jack.env, prunes to KEEP, "
          "clears leftovers, refuses an empty data dir")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
