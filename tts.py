"""Captain Jack text to speech: turns reply sentences into audio for Playback.

Implements the TTS thread from docs/specification.md section 4.16(d),
build step 5: sentences are queued with say(), synthesized one at a time
by kokoro-pi (a Raspberry-Pi-optimised Kokoro), resampled from Kokoro's
24kHz to the canonical 16kHz mono int16 (spec 4.7), and handed to
on_audio - Playback's play(), in the full program. Sentence 1 starts
playing while sentence 2 is still being synthesized.

Run standalone to speak text through the bird, or to audition voices -
each says its number, then the same line, so they can be compared by ear:
    venv/bin/python tts.py [--voice bm_fable] "Text to say."
    venv/bin/python tts.py --audition [voice ...]
"""

import queue
import re
import sys
import threading
import time
from pathlib import Path

import numpy as np

MODELS_DIR = Path(__file__).parent / "models" / "kokoro-pi"
RATE = 16000            # canonical Pi-side format (spec 4.7)
KOKORO_RATE = 24000

# Jack's voice, chosen by Chip by ear from an 8-voice audition on
# 2026-09-25: am_santa, the most emotive; bm_george and am_michael were
# the runners-up. bm_* are Kokoro's British male voices, am_* American.
DEFAULT_VOICE = "am_santa"
AUDITION_VOICES = ["bm_fable", "bm_george", "bm_lewis", "bm_daniel",
                   "am_puck", "am_fenrir", "am_michael", "am_santa"]
AUDITION_LINE = "Avast, matey! Set a course for Tortuga, and mind the lubbers!"
SPEED = 1.0

# Sentences shorter than this are merged into the next one, so "Avast!"
# isn't synthesized (and paused after) on its own.
MIN_SENTENCE_CHARS = 20

SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")

# Splitting a reply's long FIRST sentence so Jack starts talking sooner
# (2026-10-15): Kokoro synthesizes a whole sentence before any of it can
# play, so a long first sentence delays first audio. Spoken as two pieces,
# piece 1 plays while piece 2 synthesizes. Chip couldn't hear the join in a
# whole-vs-split audition on the bird (4 real sentences from session16), and
# first audio came 0.8-1.8s sooner. Only at a natural break (comma, dash,
# semicolon, colon, or a sentence end merged in by MIN_SENTENCE_CHARS),
# keeping that punctuation on piece 1. Piece 2 must be ready before piece 1
# finishes: synthesis ran ~3x faster than playback there, and the tightest
# case measured (6 words then 19) still had 1.3s to spare - so piece 2 may
# be at most SPLIT_MAX_RATIO times piece 1's length, in words.
SPLIT_MIN_WORDS = 10
SPLIT_MIN_FIRST_WORDS = 4
SPLIT_MIN_REST_WORDS = 3    # a near-whole first piece saves nothing
SPLIT_MAX_RATIO = 3.5
SPLIT_AFTER_RE = re.compile(r"[,;:.!?]$|^[—–-]$|[—–]$")
MARKUP_RE = re.compile(r"[*_#`~]")


def clean_text(text: str) -> str:
    """Strip markdown symbols TTS would otherwise read aloud (spec: the
    persona is told not to use them; this is the safety net)."""
    return " ".join(MARKUP_RE.sub("", text).split())


def split_sentences(text: str) -> list[str]:
    sentences = []
    carry = ""
    for part in SENTENCE_END_RE.split(clean_text(text)):
        carry = f"{carry} {part}".strip()
        if len(carry) >= MIN_SENTENCE_CHARS:
            sentences.append(carry)
            carry = ""
    if carry:
        if sentences:
            sentences[-1] = f"{sentences[-1]} {carry}"
        else:
            sentences.append(carry)
    return sentences


def split_first_sentence(sentence: str) -> list[str]:
    """[sentence], or [piece1, piece2] split at the earliest natural break
    that satisfies the SPLIT_* rules above."""
    words = sentence.split()
    if len(words) < SPLIT_MIN_WORDS:
        return [sentence]
    for i in range(SPLIT_MIN_FIRST_WORDS, len(words) - SPLIT_MIN_REST_WORDS + 1):
        if SPLIT_AFTER_RE.search(words[i - 1]) and len(words) - i <= SPLIT_MAX_RATIO * i:
            return [" ".join(words[:i]), " ".join(words[i:])]
    return [sentence]


def _lowpass_taps(cutoff, rate, n_taps=241, beta=8.6):
    """Windowed-sinc low-pass FIR (Kaiser window), unity gain at DC."""
    n = np.arange(n_taps) - (n_taps - 1) / 2
    taps = np.sinc(2 * cutoff / rate * n) * np.kaiser(n_taps, beta)
    return taps / taps.sum()


# 24kHz -> 16kHz is up by 2, down by 3. Filter at the 48kHz intermediate
# rate, cutting off just under the new 8kHz Nyquist limit.
_UP, _DOWN = 2, 3
_TAPS = _lowpass_taps(7600, KOKORO_RATE * _UP) * _UP


def resample_24k_to_16k(samples: np.ndarray) -> np.ndarray:
    """float32 at 24kHz -> float32 at 16kHz."""
    up = np.zeros(len(samples) * _UP, dtype=np.float64)
    up[::_UP] = samples
    filtered = np.convolve(up, _TAPS, mode="same")
    return filtered[::_DOWN].astype(np.float32)


def to_int16(samples: np.ndarray) -> np.ndarray:
    return (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)


class TTS:
    """Synthesizes queued sentences in order; calls on_audio(samples, tag).

    on_audio gets mono 16kHz int16 samples and runs on the TTS thread.
    """

    def __init__(self, on_audio, voice=DEFAULT_VOICE, speed=SPEED):
        from kokoro_pi import Kokoro     # slow import (onnxruntime); only when used
        self.kokoro = Kokoro(models=MODELS_DIR)
        self.on_audio = on_audio
        self.voice = voice
        self.speed = speed
        self._queue = queue.Queue()
        self._pending = 0
        self._lock = threading.Lock()
        self._thread = None

    def synthesize(self, text: str) -> np.ndarray:
        samples, rate = self.kokoro.create(text, voice=self.voice, speed=self.speed, lang="en-us")
        if rate != KOKORO_RATE:
            raise ValueError(f"kokoro returned {rate}Hz, expected {KOKORO_RATE}Hz")
        return to_int16(resample_24k_to_16k(np.asarray(samples, dtype=np.float32)))

    def say(self, sentence: str, tag=None):
        """Queue one sentence. Returns immediately."""
        with self._lock:
            self._pending += 1
        self._queue.put((sentence, tag))

    def pending(self) -> int:
        """Sentences queued or being synthesized, not yet handed to on_audio."""
        return self._pending

    def start(self):
        self._thread = threading.Thread(target=self._run, name="tts", daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread:
            self._queue.put(None)
            self._thread.join()

    def _run(self):
        while (item := self._queue.get()) is not None:
            sentence, tag = item
            self.on_audio(self.synthesize(sentence), tag)
            with self._lock:
                self._pending -= 1


def main():
    from playback import Playback

    args = sys.argv[1:]
    if args[:1] == ["--audition"]:
        audition(args[1:] or AUDITION_VOICES)
        return
    voice = DEFAULT_VOICE
    if args[:1] == ["--voice"]:
        voice, args = args[1], args[2:]
    text = " ".join(args) or "Avast, matey! Captain Jack be speakin' at last. Set a course for Tortuga!"

    sentences = split_sentences(text)
    player = Playback()
    player.start()
    tts = TTS(on_audio=player.play, voice=voice)
    tts.start()
    start = time.monotonic()
    try:
        for i, s in enumerate(sentences):
            tts.say(s, i)
        while tts.pending():            # all synthesized and queued to Playback...
            time.sleep(0.05)
        player.wait_played()            # ...and all of it out of the speaker
    finally:
        tts.stop()
        player.stop()
    print(f"{voice}: {len(sentences)} sentence(s) in {time.monotonic() - start:.1f}s")


def audition(voices):
    from playback import Playback

    player = Playback()
    player.start()
    engine = TTS(on_audio=None)
    gap = np.zeros(RATE, dtype=np.int16)
    try:
        for n, voice in enumerate(voices, 1):
            engine.voice = voice
            print(f"  {n}: {voice}", flush=True)
            player.play(engine.synthesize(f"Number {n}. {AUDITION_LINE}"), voice)
            player.play(gap)
        player.wait_played()
    finally:
        player.stop()


if __name__ == "__main__":
    main()
