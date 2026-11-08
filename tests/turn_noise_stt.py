"""Re-runnable test for docs/tests.md: "Head-turn noise vs recognition".

No hardware. Mixes recorded head-turn noise (tests/record_turn_noise.py)
into saved utterances (coordinator.py --save) at a fixed point in each
line, and runs STT (as coordinator.py does, with the household-names
prompt) and speaker-ID on the clean and the mixed audio side by side -
to judge whether Jack can turn toward a speaker *while they're still
talking* (an early turn, docs/log.md 4.9) without hurting recognition.
Written 2026-11-08.

Each line is scored by word changes against its own clean transcript
(not against what was really said - the question is what the turn
changes), plus confidence, rejection, and the voice match.

Run: venv/bin/python tests/turn_noise_stt.py stt_samples/session25
         [--turns stt_samples/turn_noise/turn_600ms_+50_to_-50.wav,...]
         [--at 1.2] [--model tiny.en]
"""

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrate import household_names  # noqa: E402
from speaker_id import SpeakerID  # noqa: E402
from stt import RATE, STT, names_prompt  # noqa: E402

DEFAULT_TURNS = ",".join(f"stt_samples/turn_noise/turn_{n}.wav" for n in
                         ("600ms_+0_to_-30", "600ms_+0_to_+50", "600ms_+50_to_-50",
                          "1200ms_+50_to_-50"))


def load(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def mix(speech, noise, at_s):
    out = speech.astype(np.int32)
    i = int(at_s * RATE)
    n = noise[: max(0, len(out) - i)].astype(np.int32)
    out[i:i + len(n)] += n
    return np.clip(out, -32768, 32767).astype(np.int16)


def word_changes(a, b):
    """Word-level edit distance between two transcripts."""
    a, b = a.lower().split(), b.lower().split()
    d = list(range(len(b) + 1))
    for i, wa in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, wb in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (wa.strip(".,?!") != wb.strip(".,?!")))
    return d[-1]


def describe(t, m):
    voice = f"{m.name or '-'} {m.score:.2f}"
    text = t.text if t.accepted else f"(rejected: {t.reject})"
    return f"p={t.prob:.2f} voice {voice:10s} {text}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session")
    ap.add_argument("--turns", default=DEFAULT_TURNS)
    ap.add_argument("--at", type=float, default=1.2, help="seconds into each line the turn starts")
    ap.add_argument("--model")
    args = ap.parse_args()
    prompt = names_prompt(household_names())
    stt = STT(args.model, prompt) if args.model else STT(prompt=prompt)
    sid = SpeakerID()
    utts = sorted(Path(args.session).glob("utt[0-9][0-9].wav"))
    turns = [Path(p) for p in args.turns.split(",")]

    clean = {}
    print(f"Clean ({stt.model_name}):")
    for u in utts:
        s = load(u)
        clean[u] = (stt.transcribe(s), sid.identify(s))
        print(f"  {u.stem}  {describe(*clean[u])}")

    summary = []
    for tp in turns:
        noise = load(tp)
        print(f"\n{tp.stem} at {args.at:g}s:")
        changes = rejects = voice_lost = 0
        dp = []
        for u in utts:
            ct, cm = clean[u]
            s = mix(load(u), noise, args.at)
            t, m = stt.transcribe(s), sid.identify(s)
            w = word_changes(ct.text, t.text) if ct.accepted and t.accepted else 0
            changes += w
            rejects += ct.accepted and not t.accepted
            voice_lost += bool(cm.name) and m.name != cm.name
            dp.append(t.prob - ct.prob)
            flag = "" if (w == 0 and t.accepted == ct.accepted and m.name == cm.name) else "  <-"
            print(f"  {u.stem}  {describe(t, m)}{flag}")
        words = sum(len(clean[u][0].text.split()) for u in utts if clean[u][0].accepted)
        summary.append((tp.stem, changes, words, rejects, voice_lost, float(np.mean(dp))))

    print(f"\nSummary ({len(utts)} lines, turn at {args.at:g}s):")
    for name, ch, words, rej, vl, mdp in summary:
        print(f"  {name:26s} word changes {ch}/{words}, new rejects {rej}, voice lost {vl}, "
              f"mean confidence change {mdp:+.2f}")


if __name__ == "__main__":
    main()
