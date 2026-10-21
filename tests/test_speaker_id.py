"""Automatic test for docs/tests.md: "Speaker recognition (speaker_id.py)".

No hardware, no real household voices (those are never committed): a
stand-in "person" is enrolled from Jack's own TTS clips in wavFiles/,
and the committed recording in tests/data/ plays someone else. Needs
models/nemo_en_titanet_small.onnx (see speaker_id.py).

Run: venv/bin/python tests/test_speaker_id.py
"""

import re
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import speaker_id  # noqa: E402
from speaker_id import RATE, SpeakerID, load_wav  # noqa: E402

TTS = sorted(re.findall(r"file:\s*(\S+\.wav)", (ROOT / "wavFiles" / "manifest.yaml").read_text()))
OTHER = ROOT / "tests" / "data" / "thank_you_jack_ch1.wav"


def main():
    with tempfile.TemporaryDirectory() as d:
        sid = SpeakerID(voiceprints_dir=d)
        assert sid.identify(load_wav(OTHER)).reason == "nobody enrolled"

        clips = [load_wav(ROOT / "wavFiles" / f) for f in TTS[:5]]
        sid.save_voiceprint("Santa", [sid.embed(c) for c in clips], clips)
        assert (Path(d) / "Santa.npz").exists() and len(list((Path(d) / "Santa").glob("*.wav"))) == 5

        # A fresh instance reads it back.
        sid = SpeakerID(voiceprints_dir=d)
        assert list(sid.voiceprints) == ["Santa"], sid.voiceprints

        held_out = sid.identify(load_wav(ROOT / "wavFiles" / TTS[7]))
        assert held_out.name == "Santa", held_out
        other = sid.identify(load_wav(OTHER))
        assert other.name is None and other.reason == "below threshold", other
        short = sid.identify(load_wav(OTHER)[: int(0.5 * RATE)])
        assert short.name is None and short.reason == "too short", short

        # Two enrolled voices too alike to tell apart -> no answer.
        sid.voiceprints["Twin"] = sid.voiceprints["Santa"] + 0.01
        sid.voiceprints["Twin"] /= np.linalg.norm(sid.voiceprints["Twin"])
        twin = sid.identify(load_wav(ROOT / "wavFiles" / TTS[7]))
        assert twin.name is None and twin.reason == "too close to call", twin

        # A voiceprint from a different model is ignored, not misused.
        np.savez(Path(d) / "Old.npz", centroid=np.ones(192), embeddings=np.ones((1, 192)),
                 model="some_other_model.onnx", enrolled="2026-01-01")
        assert "Old" not in SpeakerID(voiceprints_dir=d).voiceprints

    print(f"PASS: enrolls and reloads a voiceprint; matches a held-out clip "
          f"({held_out.score:.2f}), rejects another voice ({other.score:.2f}), "
          f"skips short audio, refuses a too-close call, ignores other-model voiceprints "
          f"(threshold {speaker_id.MATCH_THRESHOLD}, margin {speaker_id.MATCH_MARGIN})")


if __name__ == "__main__":
    main()
