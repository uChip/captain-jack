"""Captain Jack speech-to-text: whisper.cpp over one complete utterance.

Implements STT from docs/specification.md section 4.2, as called by the
Coordinator in section 4.16(c): takes one VAD-segmented utterance (mono
16kHz int16) and returns its transcript, or rejects it as silence/noise.
Uses pywhispercpp, a Python binding around whisper.cpp; the model stays
loaded between calls.

Run standalone to transcribe clips:
    venv/bin/python stt.py [--model base.en] clip.wav [...]
"""

import math
import re
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pywhispercpp.model import Model

MODELS_DIR = Path(__file__).parent / "models"
RATE = 16000

# tiny vs. base is still open (spec 4.2) - pending real utterances.
DEFAULT_MODEL = "tiny.en"
N_THREADS = 4

# whisper.cpp normally encodes a fixed 30s window (audio_ctx 1500, at 50
# per second of audio) however short the utterance, which dominates the
# cost. Sizing the window to the utterance cut tiny.en from 2.0s to 0.7s
# on a 5s clip, but windows too tight to the audio cost accuracy. Starting
# point: twice the utterance length, never under ~5s. To be tuned on real
# utterances (see docs/log.md, 4.16).
CTX_PER_SECOND = 50
CTX_SCALE = 2.0
CTX_MIN = 256
CTX_MAX = 1500

# Rejection thresholds (spec 4.2): OpenAI's reference defaults as the
# starting point, to be biased stricter once real household audio exists.
NO_SPEECH_THOLD = 0.6
LOGPROB_THOLD = -1.0
ENTROPY_THOLD = 2.4

# Whisper's non-speech annotations: [BLANK_AUDIO], (wind blowing), *coughs*
ANNOTATION_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*")


@dataclass
class Transcript:
    text: str           # cleaned transcript ("" when rejected)
    accepted: bool      # False: treat as "didn't catch that", don't send to Haiku
    raw: str            # whisper's output before cleaning
    audio_s: float      # utterance length
    stt_s: float        # time spent transcribing


def audio_ctx_for(n_samples: int) -> int:
    seconds = n_samples / RATE
    return max(CTX_MIN, min(CTX_MAX, math.ceil(seconds * CTX_SCALE * CTX_PER_SECOND)))


class STT:
    def __init__(self, model=DEFAULT_MODEL):
        self.model_name = model
        self.model = Model(
            str(MODELS_DIR / f"ggml-{model}.bin"),
            redirect_whispercpp_logs_to=None,
            n_threads=N_THREADS,
            print_realtime=False, print_progress=False, print_timestamps=False,
            no_context=True,            # each utterance stands alone
            single_segment=True,        # one utterance in, one transcript out
            no_speech_thold=NO_SPEECH_THOLD,
            logprob_thold=LOGPROB_THOLD,
            entropy_thold=ENTROPY_THOLD,
        )

    def transcribe(self, samples: np.ndarray) -> Transcript:
        audio = samples.astype(np.float32) / 32768
        start = time.monotonic()
        segments = self.model.transcribe(audio, audio_ctx=audio_ctx_for(len(samples)))
        stt_s = time.monotonic() - start

        raw = " ".join(s.text.strip() for s in segments).strip()
        text = " ".join(ANNOTATION_RE.sub(" ", raw).split())
        accepted = any(ch.isalnum() for ch in text)
        return Transcript(text if accepted else "", accepted, raw, len(samples) / RATE, stt_s)


def load_wav(path) -> np.ndarray:
    with wave.open(str(path)) as w:
        if (w.getframerate(), w.getsampwidth(), w.getnchannels()) != (RATE, 2, 1):
            raise ValueError(f"{Path(path).name}: need 16kHz/16-bit/mono")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def main():
    args = sys.argv[1:]
    model = DEFAULT_MODEL
    if args[:1] == ["--model"]:
        model, args = args[1], args[2:]
    stt = STT(model)
    for path in args:
        t = stt.transcribe(load_wav(path))
        verdict = repr(t.text) if t.accepted else f"REJECTED (raw {t.raw!r})"
        print(f"{Path(path).name}: {t.audio_s:.1f}s audio, {t.stt_s:.2f}s [{model}]: {verdict}")


if __name__ == "__main__":
    main()
