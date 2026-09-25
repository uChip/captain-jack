"""Re-runnable test for docs/tests.md: "wavFiles/ clip format".

Verifies every clip in wavFiles/ is stored in the canonical Pi-side
format from specification.md 4.7/4.10: plain PCM (format tag 1),
16000Hz, 16-bit, mono. Mono on purpose - the 2-channel duplication the
XVF3800 needs happens once, at the ALSA write, not in stored assets.
Does not touch hardware.

Run: venv/bin/python tests/test_wavfiles_format.py
"""

import struct
import sys
from pathlib import Path

WAV_DIR = Path(__file__).parent.parent / "wavFiles"
EXPECTED = {"tag": 1, "channels": 1, "rate": 16000, "bits": 16}


def read_fmt(path):
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    pos = 12
    while pos + 8 <= len(data):
        cid, size = struct.unpack("<4sI", data[pos:pos + 8])
        if cid == b"fmt ":
            tag, ch, rate, _, _, bits = struct.unpack(
                "<HHIIHH", data[pos + 8:pos + 24])
            return {"tag": tag, "channels": ch, "rate": rate, "bits": bits}
        pos += 8 + size + (size & 1)
    return None


def check_clips():
    errors = []
    clips = sorted(WAV_DIR.glob("*.wav"))
    if not clips:
        errors.append(f"no .wav files found in {WAV_DIR}")
    for clip in clips:
        fmt = read_fmt(clip)
        if fmt is None:
            errors.append(f"{clip.name}: not a RIFF/WAVE file with a fmt chunk")
            continue
        for key, want in EXPECTED.items():
            if fmt[key] != want:
                errors.append(f"{clip.name}: {key}={fmt[key]}, expected {want}")
    return clips, errors


if __name__ == "__main__":
    clips, errors = check_clips()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print(f"PASS: all {len(clips)} wavFiles/ clips are 16kHz/16-bit/mono PCM")
