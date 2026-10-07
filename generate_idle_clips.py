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


def load_manifest() -> list[dict]:
    with open(MANIFEST) as f:
        data = yaml.safe_load(f)
    clips = data.get("clips") or []
    seen = set()
    for entry in clips:
        for field in ("file", "text"):
            if not entry.get(field):
                raise ValueError(f"entry missing required field {field!r}: {entry}")
        if entry["file"] in seen:
            raise ValueError(f"duplicate file in manifest: {entry['file']}")
        seen.add(entry["file"])
    return clips


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
        samples = engine.synthesize(c["text"])
        dur = write_wav(WAV_DIR / c["file"], samples)
        print(f"  [{i}/{len(clips)}] {c['file']} ({dur:.1f}s)")
    elapsed = time.monotonic() - start
    print(f"Rendered {len(clips)} clip(s) in {elapsed:.1f}s "
          f"({elapsed / len(clips):.1f}s/clip average)")


if __name__ == "__main__":
    main()
