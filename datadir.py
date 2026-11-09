"""Where Jack's live data lives: outside the repo, so a pull, a checkout
or a second checkout (the boot service's ~/jack-live, CLAUDE.md item 11)
never touches it.

    ~/jack-data/memory.md      Jack's memory (seeded once from memory/memory.md)
    ~/jack-data/voiceprints/   speaker-ID voiceprints (enroll_speaker.py)

JACK_DATA in the environment overrides the location.
"""

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("JACK_DATA") or Path.home() / "jack-data")
