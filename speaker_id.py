"""Speaker recognition (spec 4.15): who in the household is speaking.

A local speaker-embedding model (NVIDIA NeMo's TitaNet-small, run through
sherpa-onnx) turns an utterance into a voice embedding; each enrolled
person's voiceprint is the average of their enrollment embeddings, and
an utterance is matched by cosine similarity. Chosen 2026-10-21 by
measurement over CAM++ (the first pick), ResNet34 and ERes2Net - see
docs/log.md's 4.15 history.

Voiceprints live in voiceprints/ (git-ignored - biometric data, never
pushed), one <Name>.npz per person plus their enrollment clips in
<Name>/ so a model change is a re-run, not a re-recording. Only
enroll_speaker.py writes them; orchestration code only reads them.

Model file (git-ignored, download once into models/):
    curl -fLO https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/nemo_en_titanet_small.onnx
    sha256sum nemo_en_titanet_small.onnx   # ad4a1802485d8b34c722d2a9d04249662f2ece5d28a7a039063ca22f515a789e

Run standalone to score saved clips against the enrolled voiceprints:
    venv/bin/python speaker_id.py clip.wav [...]
"""

import sys
import wave
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import sherpa_onnx

ROOT = Path(__file__).parent
MODEL_PATH = ROOT / "models" / "nemo_en_titanet_small.onnx"
VOICEPRINTS_DIR = ROOT / "voiceprints"
RATE = 16000

# Provisional starting values, not calibrated (spec 4.15: the numbers come
# from real household audio, the same treatment as 4.1/4.2). Biased
# strict: filing a memory under the wrong person is worse than not
# knowing who's talking. On first measurement TitaNet scored Chip's own
# clips around 0.64 and other voices at 0.21 or below. Lowered from 0.45
# after Chip and Kath enrolled (2026-10-21): Kath's clips scored at most
# 0.36 against Chip's voiceprint, while 0.45 left a third of Chip's past
# session clips unrecognized (docs/log.md 4.15).
MATCH_THRESHOLD = 0.40   # best score must reach this...
MATCH_MARGIN = 0.10      # ...and beat the runner-up by this much
MIN_SCORE_S = 1.0        # shorter utterances ("yes") aren't scored at all


@dataclass
class Match:
    name: str | None                 # who it is, or None if not sure
    score: float = 0.0               # best cosine similarity
    runner_up: float = 0.0           # second best (0 if only one enrolled)
    scores: dict = field(default_factory=dict)
    reason: str = ""                 # why name is None


def to_float(samples) -> np.ndarray:
    """int16 (Capture/Listener's format) or float samples -> float32 in [-1, 1]."""
    a = np.asarray(samples)
    if a.dtype == np.int16:
        return a.astype(np.float32) / 32768
    return a.astype(np.float32)


def load_wav(path) -> np.ndarray:
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16)
        if w.getnchannels() > 1:
            x = x[::w.getnchannels()]
        if w.getframerate() != RATE:
            raise ValueError(f"{path}: {w.getframerate()}Hz, expected {RATE}")
    return x


def save_wav(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(np.asarray(samples, np.int16).tobytes())


def unit(v) -> np.ndarray:
    v = np.asarray(v, np.float32)
    n = np.linalg.norm(v)
    return v / n if n else v


class SpeakerID:
    def __init__(self, model_path=MODEL_PATH, voiceprints_dir=VOICEPRINTS_DIR, threads=2):
        self.model_path = Path(model_path)
        self.dir = Path(voiceprints_dir)
        self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
            sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(self.model_path),
                                                       num_threads=threads))
        self.voiceprints = self.load_voiceprints()

    def embed(self, samples) -> np.ndarray:
        """One unit-length voice embedding for an utterance (16kHz)."""
        stream = self.extractor.create_stream()
        stream.accept_waveform(RATE, to_float(samples))
        stream.input_finished()
        return unit(self.extractor.compute(stream))

    # -- voiceprints -----------------------------------------------------------

    def load_voiceprints(self) -> dict:
        """{name: centroid} for every <Name>.npz made with this model."""
        prints = {}
        for path in sorted(self.dir.glob("*.npz")):
            data = np.load(path)
            if str(data["model"]) != self.model_path.name:
                print(f"[speaker-id] skipping {path.name}: enrolled with {data['model']}, "
                      f"re-run enroll_speaker.py", file=sys.stderr)
                continue
            prints[path.stem] = unit(data["centroid"])
        return prints

    def save_voiceprint(self, name, embeddings, clips):
        """Write name's voiceprint (the mean of embeddings) and the clips it
        came from. Overwrites any earlier enrollment for name."""
        self.dir.mkdir(exist_ok=True)
        clip_dir = self.dir / name
        clip_dir.mkdir(exist_ok=True)
        for old in clip_dir.glob("enroll*.wav"):
            old.unlink()
        for i, clip in enumerate(clips, 1):
            save_wav(clip_dir / f"enroll{i:02d}.wav", clip)
        embeddings = np.array([unit(e) for e in embeddings])
        np.savez(self.dir / f"{name}.npz", centroid=unit(embeddings.mean(0)),
                 embeddings=embeddings, model=self.model_path.name,
                 enrolled=date.today().isoformat())
        self.voiceprints[name] = unit(embeddings.mean(0))

    # -- matching ----------------------------------------------------------------

    def score(self, embedding) -> dict:
        return {name: float(embedding @ c) for name, c in self.voiceprints.items()}

    def identify(self, samples) -> Match:
        """Who's speaking, or Match(None) when not confident - the caller
        then falls back to self-identification (spec Open Issues issue 1)."""
        if not self.voiceprints:
            return Match(None, reason="nobody enrolled")
        if len(samples) < MIN_SCORE_S * RATE:
            return Match(None, reason="too short")
        scores = self.score(self.embed(samples))
        ranked = sorted(scores.values(), reverse=True)
        best_name = max(scores, key=scores.get)
        best, runner_up = ranked[0], (ranked[1] if len(ranked) > 1 else 0.0)
        m = Match(best_name, best, runner_up, scores)
        if best < MATCH_THRESHOLD:
            m.name, m.reason = None, "below threshold"
        elif best - runner_up < MATCH_MARGIN:
            m.name, m.reason = None, "too close to call"
        return m


def main():
    sid = SpeakerID()
    print(f"Enrolled: {', '.join(sid.voiceprints) or 'nobody'}")
    for path in sys.argv[1:]:
        m = sid.identify(load_wav(path))
        scores = "  ".join(f"{n} {s:.2f}" for n, s in sorted(m.scores.items()))
        print(f"{path}: {m.name or '-'} ({m.reason or 'match'})  {scores}")


if __name__ == "__main__":
    main()
