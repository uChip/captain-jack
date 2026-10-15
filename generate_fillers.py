"""Render the squawk filler clips into wavFiles/fillers/.

The filler (CLAUDE.md work list, 2026-10-14) is a short squawk played the
moment an utterance ends, so the wait for STT + Haiku + the first TTS
sentence reads as Jack reacting rather than lag. coordinator.py plays
whatever .wav files are in wavFiles/fillers/, rotated - so better squawks
(real recordings) can replace these by just dropping files in.

These are all cut from the one real squawk already in the library (the
tail of WellAlwayHaveParisSquawk.wav), lengthened by repeating part of its
steady middle (2026-10-15: Chip found the 0.38s original too short;
slowing it down instead would also lower its pitch, and it already
sounds more crow than parrot), then resampled to a few speeds, which
shifts pitch and length together the way a real bird's call varies.

Run:
    venv/bin/python generate_fillers.py
"""

import wave
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from playback import RATE

WAV_DIR = Path(__file__).parent / "wavFiles"
OUT_DIR = WAV_DIR / "fillers"
SOURCE = WAV_DIR / "WellAlwayHaveParisSquawk.wav"
SQUAWK_START_S = 1.21   # the squawk follows ~0.2s of digital silence; ends at end of file
GAIN_DB = -6.0          # the source squawk peaks near -1dBFS, well above Jack's speech
FADE_IN_S = 0.005
FADE_OUT_S = 0.02       # source is cut off at -20dB, not faded
STRETCH = 4 / 3         # lengthen the squawk by a third (Chip, 2026-10-15)...
SPLICE_AT_S = 0.22      # ...by jumping back from here, inside the steady middle
                        # (squawk-relative; it's loud and even from ~0.04s to ~0.31s)
CROSSFADE_S = 0.01

# Playback speed of each variant: >1 is shorter and higher-pitched.
SPEEDS = {"Squawk1.wav": 1.0, "Squawk2.wav": 0.88, "Squawk3.wav": 1.15}


def load_mono(path) -> np.ndarray:
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (RATE, 1, 2)
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64)


def stretch(squawk: np.ndarray) -> np.ndarray:
    """Lengthen by STRETCH without changing pitch: play up to SPLICE_AT_S,
    jump back by about the extra length needed, and play on from there to
    the end - so one chunk of the steady middle plays twice. The exact
    jump is picked by cross-correlation so the waveforms line up at the
    join, then crossfaded, so it doesn't click."""
    a = int(SPLICE_AT_S * RATE)
    extra = int(len(squawk) * (STRETCH - 1))
    w = int(CROSSFADE_S * RATE)
    ref = squawk[a:a + w]
    candidates = range(a - extra - 40, a - extra + 40)   # +-2.5ms around the target jump
    b = max(candidates, key=lambda b: float(np.dot(ref, squawk[b:b + w])))
    fade = np.linspace(0, 1, w)
    join = squawk[a:a + w] * (1 - fade) + squawk[b:b + w] * fade
    return np.concatenate([squawk[:a], join, squawk[b + w:]])


def render(squawk: np.ndarray, speed: float) -> np.ndarray:
    ratio = Fraction(1 / speed).limit_denominator(50)
    out = resample_poly(squawk, ratio.numerator, ratio.denominator)
    out *= 10 ** (GAIN_DB / 20)
    n_in, n_out = int(FADE_IN_S * RATE), int(FADE_OUT_S * RATE)
    out[:n_in] *= np.linspace(0, 1, n_in)
    out[-n_out:] *= np.linspace(1, 0, n_out)
    return np.clip(out, -32768, 32767).astype(np.int16)


def main():
    squawk = stretch(load_mono(SOURCE)[int(SQUAWK_START_S * RATE):])
    OUT_DIR.mkdir(exist_ok=True)
    for name, speed in SPEEDS.items():
        clip = render(squawk, speed)
        with wave.open(str(OUT_DIR / name), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(clip.tobytes())
        print(f"{name}: {len(clip) / RATE:.2f}s, speed {speed}")


if __name__ == "__main__":
    main()
