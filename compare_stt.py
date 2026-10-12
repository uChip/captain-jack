"""Captain Jack STT model comparison: tiny.en vs. base.en on real, saved
utterances - the real-audio test spec 4.2 has been waiting on to settle
the tiny-vs-base question (CLAUDE.md "Done so far" item 18 picked tiny.en
provisionally, on five quiet-room utterances only).

Reads every utterance Coordinator's `--save DIR` already writes
(`coordinator.py [--save DIR] [--port ...]`), transcribes each with both
models, and prints them side by side so a human (who knows what was
actually said) can judge accuracy - this tool makes no accept/reject
decision of its own, unlike stt.py's own rejection_reason().

Run against a directory of saved utterances:
    venv/bin/python compare_stt.py DIR [--models tiny.en,base.en]
"""

import sys
import time
from pathlib import Path

from stt import STT, load_wav


def verdict(t) -> str:
    return repr(t.text) if t.accepted else f"REJECTED {t.reject} (raw {t.raw!r})"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    models = ["tiny.en", "base.en"]
    if "--models" in args:
        i = args.index("--models")
        models = args[i + 1].split(",")
        del args[i:i + 2]
    wav_dir = Path(args[0])
    paths = sorted(wav_dir.glob("*.wav"))
    if not paths:
        print(f"no .wav files in {wav_dir}")
        return 1

    for path in paths:
        samples = load_wav(path)
        print(f"\n{path.name}  ({len(samples) / 16000:.1f}s audio)")
        for name in models:
            start = time.monotonic()
            t = STT(name).transcribe(samples)   # fresh per file - see stt.py's STT._new_model
            took = time.monotonic() - start
            print(f"  {name:8s} p={t.prob:.2f} {took:5.2f}s: {verdict(t)}")


if __name__ == "__main__":
    sys.exit(main())
