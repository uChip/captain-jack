"""Re-runnable test for docs/tests.md: "TTS thread".

Part 1 (automatic, no hardware, no model): sentence splitting, markdown
clean-up, and the 24kHz -> 16kHz resampler (a 1kHz tone keeps its pitch
and level; a 10kHz tone, above the new 8kHz limit, is filtered out
rather than aliasing into the audible band).

Part 2 (--live, needs the kokoro-pi models built in models/kokoro-pi;
no person needed): synthesizes a sentence and checks it comes back as
non-silent 16kHz int16 audio of plausible length, faster than real time.

Run: venv/bin/python tests/test_tts.py [--live]
"""

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import tts  # noqa: E402


def tone(freq, seconds=1.0, rate=tts.KOKORO_RATE):
    return (0.5 * np.sin(2 * np.pi * freq * np.arange(int(seconds * rate)) / rate)).astype(np.float32)


def peak_freq(samples, rate):
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    return np.fft.rfftfreq(len(samples), 1 / rate)[spectrum.argmax()]


def check_offline():
    errors = []

    cases = {
        "Avast! That be a fine question, matey. Set a course for Tortuga!":
            ["Avast! That be a fine question, matey.", "Set a course for Tortuga!"],
        "Aye, aye, Captain!": ["Aye, aye, Captain!"],
        "Short one. And a much longer second sentence here.":
            ["Short one. And a much longer second sentence here."],
        "Arr, *squawk* that be **grand**.": ["Arr, squawk that be grand."],
    }
    for text, want in cases.items():
        got = tts.split_sentences(text)
        if got != want:
            errors.append(f"split_sentences({text!r}) = {got}, expected {want}")

    one_k = tts.resample_24k_to_16k(tone(1000))
    if abs(len(one_k) - tts.RATE) > 2:
        errors.append(f"1s at 24kHz became {len(one_k)} samples, expected {tts.RATE}")
    mid = one_k[1000:-1000]             # skip filter edge effects
    if abs(peak_freq(mid, tts.RATE) - 1000) > 5:
        errors.append(f"1kHz tone came out at {peak_freq(mid, tts.RATE):.0f}Hz")
    if not 0.48 <= np.abs(mid).max() <= 0.52:
        errors.append(f"1kHz tone level {np.abs(mid).max():.3f}, expected 0.5")

    ten_k = tts.resample_24k_to_16k(tone(10000))[1000:-1000]
    attenuation = 20 * np.log10(np.abs(ten_k).max() / 0.5)
    if attenuation > -40:
        errors.append(f"10kHz tone only {attenuation:.0f}dB down - would alias to 6kHz")

    if (tts.to_int16(np.array([2.0, -2.0], dtype=np.float32)) != [32767, -32767]).any():
        errors.append("to_int16 doesn't clip out-of-range samples")
    return errors


def check_live():
    errors = []
    engine = tts.TTS(on_audio=lambda s, t: None)
    engine.synthesize("Warming up.")
    text = "Avast, matey! Captain Jack be speakin' at last."
    start = time.monotonic()
    audio = engine.synthesize(text)
    took = time.monotonic() - start
    seconds = len(audio) / tts.RATE
    print(f"  {engine.voice}: {seconds:.2f}s of speech in {took:.2f}s ({took / seconds:.2f}x real time)")
    if audio.dtype != np.int16:
        errors.append(f"audio dtype {audio.dtype}, expected int16")
    if not 1.5 <= seconds <= 6:
        errors.append(f"{seconds:.2f}s of audio for {len(text)} chars is implausible")
    if np.abs(audio.astype(int)).max() < 1000:
        errors.append("audio is near-silent")
    if took > seconds:
        errors.append(f"synthesis slower than real time ({took:.2f}s for {seconds:.2f}s)")
    return errors


if __name__ == "__main__":
    errors = check_offline()
    live = "--live" in sys.argv[1:]
    if live and not errors:
        errors = check_live()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: sentence split, clean-up, and 24k->16k resampling correct"
          + (", kokoro-pi synthesizes faster than real time" if live else ""))
