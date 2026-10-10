"""Captain Jack idle-clip generator: renders wavFiles/manifest.yaml once.

Reads each entry's `text`, synthesizes it with tts.py's TTS engine
(already resamples to the canonical 16kHz mono - spec 4.7), and writes
the result to wavFiles/<file>. See docs/specification.md section 4.10
for why these are pre-rendered once rather than synthesized live.

This only ever writes wav files - it never edits manifest.yaml, so hand-
written comments and formatting in that file are never at risk from a
render pass. Update `rendered`/`engine` by hand after a real re-render if
they drift from what the manifest already says.

Run to render everything in the manifest:
    venv/bin/python generate_idle_clips.py
Render (or re-render) just one entry by its filename:
    venv/bin/python generate_idle_clips.py --only KnowingNothing.wav
Preview what would be rendered without calling TTS:
    venv/bin/python generate_idle_clips.py --dry-run
"""

import argparse
import sys
import time
import wave
from pathlib import Path

import yaml

WAV_DIR = Path(__file__).parent / "wavFiles"
MANIFEST = WAV_DIR / "manifest.yaml"

# Named alternatives to Jack's normal speaking voice, selected per entry by
# the manifest's optional `delivery` field. Kokoro has no tone/emotion
# control, so a delivery is built from the levers it does have: speed, a
# blend of voice style vectors, and output gain.
#   to_self: muttered to himself rather than to an audience (the Asleep
#     idle_timeout lines). Chip picked this by ear 2026-10-10 from five
#     variants on the bird; the manifest text for these entries is also
#     written lowercase with a trailing "..." so the pitch falls away.
DELIVERIES = {
    "to_self": {"voices": {"am_santa": 0.75, "am_michael": 0.25}, "speed": 0.85, "gain_db": -6.0},
}


def load_manifest() -> list[dict]:
    with open(MANIFEST) as f:
        data = yaml.safe_load(f)
    clips = data.get("clips") or []
    seen = set()
    for entry in clips:
        for field in ("file", "text"):
            if not entry.get(field):
                raise ValueError(f"entry missing required field {field!r}: {entry}")
        if entry.get("delivery") and entry["delivery"] not in DELIVERIES:
            raise ValueError(f"unknown delivery {entry['delivery']!r} in {entry['file']}")
        if entry["file"] in seen:
            raise ValueError(f"duplicate file in manifest: {entry['file']}")
        seen.add(entry["file"])
    return clips


def synthesize(engine, entry):
    """Renders one entry in Jack's normal voice, or its named delivery."""
    delivery = DELIVERIES.get(entry.get("delivery"))
    if delivery is None:
        return engine.synthesize(entry["text"])

    import numpy as np
    import tts as tts_module

    k = engine.kokoro
    style = sum(w * k.get_voice_style(v) for v, w in delivery["voices"].items())
    samples, rate = k.create(entry["text"], voice=style, speed=delivery["speed"], lang="en-us")
    if rate != tts_module.KOKORO_RATE:
        raise ValueError(f"kokoro returned {rate}Hz, expected {tts_module.KOKORO_RATE}Hz")
    audio = tts_module.resample_24k_to_16k(np.asarray(samples, dtype=np.float32))
    return tts_module.to_int16(audio * 10 ** (delivery["gain_db"] / 20))


def write_wav(path: Path, samples) -> float:
    """Writes mono 16kHz 16-bit samples; returns the clip's duration in seconds."""
    import tts as tts_module

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(tts_module.RATE)
        w.writeframes(samples.tobytes())
    return len(samples) / tts_module.RATE


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", metavar="FILE", help="render just this one manifest entry")
    parser.add_argument("--dry-run", action="store_true", help="list what would be rendered, call no TTS")
    args = parser.parse_args()

    clips = load_manifest()
    if args.only:
        clips = [c for c in clips if c["file"] == args.only]
        if not clips:
            print(f"no manifest entry for {args.only!r}", file=sys.stderr)
            sys.exit(1)

    print(f"{len(clips)} clip(s) to render")
    if args.dry_run:
        for c in clips:
            print(f"  [dry-run] {c['file']}: {c['text'][:60]!r}...")
        return

    import tts as tts_module

    engine = tts_module.TTS(on_audio=None)
    start = time.monotonic()
    for i, c in enumerate(clips, 1):
        samples = synthesize(engine, c)
        dur = write_wav(WAV_DIR / c["file"], samples)
        print(f"  [{i}/{len(clips)}] {c['file']} ({dur:.1f}s)")
    elapsed = time.monotonic() - start
    print(f"Rendered {len(clips)} clip(s) in {elapsed:.1f}s "
          f"({elapsed / len(clips):.1f}s/clip average)")


if __name__ == "__main__":
    main()
