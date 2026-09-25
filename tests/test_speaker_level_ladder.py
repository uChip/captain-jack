"""Re-runnable test for docs/tests.md: "XVF3800 speaker level ladder".

Manual listening test - needs a human at the bird. Plays one wavFiles/
clip through the XVF3800's speaker several times in a row, each louder
than the last, with 2s of silence between, at the XVF3800's fixed
playback format (16kHz, S16_LE, 2ch - mono duplicated to both channels,
per specification.md 4.7). Sets both ALSA PCM Playback Volume controls
on the XVF3800 to max (60) first so the only variable is digital level.
The listener reports the loudest step that still sounds clean.

Run: venv/bin/python tests/test_speaker_level_ladder.py [clip.wav] [dB ...]
     (defaults: DeadMenTellNoTales.wav, steps -14 -10 -6 -3)
"""

import array
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

WAV_DIR = Path(__file__).parent.parent / "wavFiles"
DEVICE = "hw:CARD=Array,DEV=0"
RATE = 16000
GAP_S = 2
DEFAULT_CLIP = "DeadMenTellNoTales.wav"
DEFAULT_STEPS = [-14.0, -10.0, -6.0, -3.0]


def load_mono(path):
    with wave.open(str(path)) as w:
        if w.getframerate() != RATE or w.getsampwidth() != 2:
            sys.exit(f"{path.name}: need 16kHz/16-bit, got "
                     f"{w.getframerate()}Hz/{w.getsampwidth() * 8}-bit")
        samples = array.array("h", w.readframes(w.getnframes()))
        if w.getnchannels() == 2:
            samples = samples[0::2]  # take left channel only
    return samples


def build_ladder(mono, steps_db):
    out = array.array("h")
    silence = array.array("h", [0] * (RATE * GAP_S * 2))
    for i, db in enumerate(steps_db):
        gain = 10 ** (db / 20)
        for s in mono:
            v = int(s * gain)
            out.append(v)  # left
            out.append(v)  # right (duplicate)
        if i < len(steps_db) - 1:
            out.extend(silence)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    clip = WAV_DIR / (args[0] if args else DEFAULT_CLIP)
    steps = [float(a) for a in args[1:]] or DEFAULT_STEPS

    subprocess.run(["amixer", "-q", "-c", "Array", "cset",
                    "name=PCM Playback Volume,index=0", "60,60"], check=True)
    subprocess.run(["amixer", "-q", "-c", "Array", "cset",
                    "name=PCM Playback Volume,index=1", "60"], check=True)
    ladder = build_ladder(load_mono(clip), steps)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(ladder.tobytes())
        print(f"Playing {clip.name} at " +
              ", ".join(f"step {i + 1}: {db:+g}dB" for i, db in enumerate(steps)))
        subprocess.run(["aplay", "-q", "-D", DEVICE, tmp.name], check=True)
    print("Which was the loudest step that still sounded clean?")
