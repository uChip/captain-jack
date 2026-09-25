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

# No temperature-fallback retries. When a decode trips a threshold,
# whisper.cpp normally retries at up to 5 rising temperatures, each a full
# decode: live, that turned a 2s utterance into 20s of waiting (and a
# 5x-repeated wrong transcript). One decode, then reject if it's bad.
TEMPERATURE_INC = 0.0

# Cap the transcript's length by the audio's: normal speech is ~3-4
# tokens per second, so this is generous for real speech but stops a
# runaway repetition loop early.
TOKENS_PER_SECOND = 6
TOKENS_MIN = 10

# Reject a transcript that repeats itself - Whisper's signature both for
# retry loops ("Where is the anchor?" x5) and for filling gibberish with
# an echoed guess ("Are you a wick, Jack? Are you a wick,"). Each rule is
# (phrase length in words, times it appears): a 2+-word phrase 3 times,
# or a 3+-word phrase twice. Starting points from the 2026-09-25 live
# runs (see docs/log.md, 4.16): caught both gibberish echoes, no real
# speech.
REPEAT_RULES = [(2, 3), (3, 2)]

# Reject when whisper's average token probability is below this. Real
# speech scored 0.52-0.76 in the live runs, but so did most gibberish
# (0.55, 0.69), so this only catches the extreme cases ("P" at 0.02) -
# set well below the lowest real speech seen. Starting point.
PROB_FLOOR = 0.3

# Whisper's non-speech annotations: [BLANK_AUDIO], (wind blowing), *coughs*
ANNOTATION_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*")
WORD_RE = re.compile(r"[a-z0-9']+")


@dataclass
class Transcript:
    text: str           # cleaned transcript ("" when rejected)
    accepted: bool      # False: treat as "didn't catch that", don't send to Haiku
    raw: str            # whisper's output before cleaning
    audio_s: float      # utterance length
    stt_s: float        # time spent transcribing
    prob: float         # whisper's average token probability (logged, not yet used)
    reject: str = ""    # why it was rejected, if it was


def audio_ctx_for(n_samples: int) -> int:
    seconds = n_samples / RATE
    return max(CTX_MIN, min(CTX_MAX, math.ceil(seconds * CTX_SCALE * CTX_PER_SECOND)))


def is_repetition_loop(text: str) -> bool:
    words = WORD_RE.findall(text.lower())
    for min_words, times in REPEAT_RULES:
        for n in range(min_words, len(words) // times + 1):
            counts = {}
            for i in range(len(words) - n + 1):
                phrase = tuple(words[i:i + n])
                counts[phrase] = counts.get(phrase, 0) + 1
                if counts[phrase] >= times:
                    return True
    return False


def rejection_reason(text: str, prob: float) -> str:
    """Why a cleaned transcript shouldn't go to Haiku, or "" if it's fine."""
    if not any(ch.isalnum() for ch in text):
        return "no words"
    if is_repetition_loop(text):
        return "repetition"
    if prob < PROB_FLOOR:           # False for nan, so no probability means no verdict
        return f"low confidence ({prob:.2f})"
    return ""


def names_prompt(names) -> str | None:
    """Spelling hint for Whisper: it copies the spelling of names it has
    just "seen" in its prompt (e.g. "Kath", not "Cat")."""
    if not names:
        return None
    listed = ", ".join(names[:-1]) + (f" and {names[-1]}" if len(names) > 1 else names[0])
    return f"Captain Jack the parrot, talking with {listed}."


class STT:
    def __init__(self, model=DEFAULT_MODEL, prompt=None):
        self.model_name = model
        self.prompt = prompt
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
            temperature_inc=TEMPERATURE_INC,
            **({"initial_prompt": prompt} if prompt else {}),   # binding rejects None
        )

    def transcribe(self, samples: np.ndarray) -> Transcript:
        audio = samples.astype(np.float32) / 32768
        start = time.monotonic()
        audio_s = len(samples) / RATE
        segments = self.model.transcribe(
            audio, audio_ctx=audio_ctx_for(len(samples)), extract_probability=True,
            max_tokens=max(TOKENS_MIN, math.ceil(audio_s * TOKENS_PER_SECOND)))
        stt_s = time.monotonic() - start

        raw = " ".join(s.text.strip() for s in segments).strip()
        probs = [s.probability for s in segments if not math.isnan(s.probability)]
        prob = float(np.mean(probs)) if probs else float("nan")
        text = " ".join(ANNOTATION_RE.sub(" ", raw).split())
        reject = rejection_reason(text, prob)
        return Transcript("" if reject else text, not reject, raw, audio_s, stt_s, prob, reject)


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
        verdict = repr(t.text) if t.accepted else f"REJECTED, {t.reject} (raw {t.raw!r})"
        print(f"{Path(path).name}: {t.audio_s:.1f}s audio, {t.stt_s:.2f}s, p={t.prob:.2f} [{model}]: {verdict}")


if __name__ == "__main__":
    main()
