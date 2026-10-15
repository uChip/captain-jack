"""Render the squawk filler clips into wavFiles/fillers/.

The filler (CLAUDE.md work list, 2026-10-14) is a short squawk played the
moment an utterance ends, so the wait for STT + Haiku + the first TTS
sentence reads as Jack reacting rather than lag. coordinator.py plays
whatever .wav files are directly in wavFiles/fillers/, rotated.
wavFiles/fillers/unused/ holds clips kept for later but not played.

Real parrot calls from xeno-canto (2026-10-15), all CC BY-NC-SA 4.0, so
each clip here is CC BY-NC-SA 4.0 too and credited in
wavFiles/fillers/CREDITS.md (written by this script). Each recording is
downloaded once into XC_CACHE (git-ignored), converted to 16kHz mono,
high-passed (wind rumble the 40mm speaker can't play anyway), cut to one
call, and level-matched to the speech-comparable loudness Chip approved
for the first placeholder set. Chip and Kath auditioned eight on the
bird: the GreyParrot one sounded more whistle than squawk, and
RedGreenMacawXC1035594 had distracting background noise - both kept, in
unused/. Jack himself is painted as a Scarlet Macaw.

The original placeholders (Squawk1-3, from the squawk at the end of
WellAlwayHaveParisSquawk.wav - Kath: "sounds like a crow") are also
rendered into unused/.

Run:
    venv/bin/python generate_fillers.py
"""

import subprocess
import urllib.request
import wave
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.signal import butter, resample_poly, sosfilt

from playback import RATE

WAV_DIR = Path(__file__).parent / "wavFiles"
OUT_DIR = WAV_DIR / "fillers"
UNUSED_DIR = OUT_DIR / "unused"
XC_CACHE = Path(__file__).parent / "xc_cache"
XC_URL = "https://xeno-canto.org/{id}/download"
LICENSE = "CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)"

HIGHPASS_HZ = 250
PAD_BEFORE_S = 0.03
PAD_AFTER_S = 0.06
FADE_IN_S = 0.01
FADE_OUT_S = 0.04
PEAK_LIMIT = 0.89           # about -1dBFS; most calls hit this before reaching TARGET_RMS_DBFS
TARGET_RMS_DBFS = -11.1     # the placeholder Squawk1's steady part - "comparable to speaking volume"

# (output file, xeno-canto id, call start s, call length s, species, recordist, played?)
XC_CLIPS = [
    ("RedGreenMacawXC823817a.wav", 823817, 7.20, 0.46, "Red-and-green Macaw", "Hans Groot", True),
    ("RedGreenMacawXC823817b.wav", 823817, 3.83, 0.55, "Red-and-green Macaw", "Hans Groot", True),
    ("GreyParrotXC1053186.wav", 1053186, 7.08, 0.39, "Grey Parrot", "Bernard Bousquet", False),
    ("ScarletMacawXC1085669.wav", 1085669, 3.42, 0.28, "Scarlet Macaw", "Paul Driver", True),
    ("BlueYellowMacawXC956062.wav", 956062, 2.65, 0.26, "Blue-and-yellow Macaw",
     "Jayrson Araujo de Oliveira", True),
    ("RedGreenMacawXC939501.wav", 939501, 1.68, 0.24, "Red-and-green Macaw",
     "Jayrson Araujo de Oliveira", True),
    ("RedGreenMacawXC1035594.wav", 1035594, 4.18, 0.58, "Red-and-green Macaw",
     "Jayrson Araujo de Oliveira", False),
    ("ScarletMacawXC863337.wav", 863337, 4.13, 0.32, "Scarlet Macaw", "Alain Verneau", True),
]

# The original placeholders, all into unused/.
PLACEHOLDER_SOURCE = WAV_DIR / "WellAlwayHaveParisSquawk.wav"
PLACEHOLDER_START_S = 1.21   # the squawk follows ~0.2s of digital silence; ends at end of file
PLACEHOLDER_GAIN_DB = -6.0
PLACEHOLDER_STRETCH = 4 / 3  # lengthened a third without changing pitch (Chip, 2026-10-15)
PLACEHOLDER_SPLICE_AT_S = 0.22
PLACEHOLDER_SPEEDS = {"Squawk1.wav": 1.0, "Squawk2.wav": 0.88, "Squawk3.wav": 1.15}


def load_mono(path) -> np.ndarray:
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (RATE, 1, 2)
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768


def save(path, x: np.ndarray):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def fade(x: np.ndarray, fade_in_s: float, fade_out_s: float) -> np.ndarray:
    n_in, n_out = int(fade_in_s * RATE), int(fade_out_s * RATE)
    x[:n_in] *= np.linspace(0, 1, n_in)
    x[-n_out:] *= np.linspace(1, 0, n_out)
    return x


def rms_dbfs(x: np.ndarray) -> float:
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def xc_recording(xc_id: int) -> np.ndarray:
    """The recording as 16kHz mono, downloaded and converted once."""
    XC_CACHE.mkdir(exist_ok=True)
    raw, wav = XC_CACHE / f"XC{xc_id}.download", XC_CACHE / f"XC{xc_id}.wav"
    if not wav.exists():
        if not raw.exists():
            urllib.request.urlretrieve(XC_URL.format(id=xc_id), raw)
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(raw),
                        "-ac", "1", "-ar", str(RATE), "-sample_fmt", "s16", str(wav)], check=True)
    return load_mono(wav)


def render_xc(xc_id: int, start_s: float, length_s: float) -> np.ndarray:
    x = sosfilt(butter(4, HIGHPASS_HZ, "highpass", fs=RATE, output="sos"), xc_recording(xc_id))
    clip = x[int((start_s - PAD_BEFORE_S) * RATE):int((start_s + length_s + PAD_AFTER_S) * RATE)].copy()
    call = clip[int(PAD_BEFORE_S * RATE):int((PAD_BEFORE_S + length_s) * RATE)]
    clip *= 10 ** ((TARGET_RMS_DBFS - rms_dbfs(call)) / 20)
    clip *= min(1.0, PEAK_LIMIT / np.abs(clip).max())
    return fade(clip, FADE_IN_S, FADE_OUT_S)


def stretch(squawk: np.ndarray, factor: float, splice_at_s: float) -> np.ndarray:
    """Lengthen without changing pitch: play up to splice_at_s, jump back by
    about the extra length needed, and play on to the end - one chunk of
    the steady middle plays twice. The jump is picked by cross-correlation
    so the waveforms line up at the join, then crossfaded (10ms)."""
    a = int(splice_at_s * RATE)
    extra = int(len(squawk) * (factor - 1))
    w = int(0.01 * RATE)
    ref = squawk[a:a + w]
    b = max(range(a - extra - 40, a - extra + 40), key=lambda b: float(np.dot(ref, squawk[b:b + w])))
    ramp = np.linspace(0, 1, w)
    join = squawk[a:a + w] * (1 - ramp) + squawk[b:b + w] * ramp
    return np.concatenate([squawk[:a], join, squawk[b + w:]])


def render_placeholder(squawk: np.ndarray, speed: float) -> np.ndarray:
    ratio = Fraction(1 / speed).limit_denominator(50)
    out = resample_poly(squawk, ratio.numerator, ratio.denominator) * 10 ** (PLACEHOLDER_GAIN_DB / 20)
    return fade(out, 0.005, 0.02)


def write_credits():
    lines = ["# Filler squawk credits", "",
             "Generated by `generate_fillers.py` - edit its `XC_CLIPS` table, not this file.", "",
             f"Each xeno-canto clip below is a trimmed, filtered, level-adjusted excerpt of the "
             f"original recording and is licensed {LICENSE}, as the original is.", "",
             "| File | Played? | Species | Recordist | Source |", "|---|---|---|---|---|"]
    for name, xc_id, _, _, species, recordist, played in XC_CLIPS:
        where = name if played else f"unused/{name}"
        lines.append(f"| `{where}` | {'yes' if played else 'no'} | {species} | {recordist} | "
                     f"[XC{xc_id}](https://xeno-canto.org/{xc_id}) |")
    lines += ["", "`unused/Squawk1-3.wav` are cut from `WellAlwayHaveParisSquawk.wav` in this "
              "repo's own clip library (the original placeholders).", ""]
    (OUT_DIR / "CREDITS.md").write_text("\n".join(lines))


def main():
    UNUSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, xc_id, start, length, species, _, played in XC_CLIPS:
        clip = render_xc(xc_id, start, length)
        save((OUT_DIR if played else UNUSED_DIR) / name, clip)
        print(f"{'' if played else 'unused/'}{name}: {len(clip) / RATE:.2f}s, {species}")

    squawk = load_mono(PLACEHOLDER_SOURCE)[int(PLACEHOLDER_START_S * RATE):]
    squawk = stretch(squawk, PLACEHOLDER_STRETCH, PLACEHOLDER_SPLICE_AT_S)
    for name, speed in PLACEHOLDER_SPEEDS.items():
        clip = render_placeholder(squawk, speed)
        save(UNUSED_DIR / name, clip)
        print(f"unused/{name}: {len(clip) / RATE:.2f}s, placeholder")
    write_credits()


if __name__ == "__main__":
    main()
