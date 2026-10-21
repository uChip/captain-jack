"""Re-runnable test for docs/tests.md: "Speaker-ID calibration lines".

Manual measurement for calibrating speaker_id.py's MATCH_THRESHOLD and
MATCH_MARGIN (spec 4.15) on real household speech - not enrollment-style
reading, but the way people actually talk to Jack. Two parts:

record LABEL - listens continuously and saves every utterance as
    <out>/<LABEL>_NN.wav (numbering carries on from earlier runs), printing
    who speaker_id.py thinks it is as it goes. LABEL is who is really
    speaking: an enrolled name (Chip, Kath) or "other" for anyone else
    (a YouTube video played near the bird, say). Ctrl+C stops, or --lines N.
    With --port the head sways in On Watch's ambient motion while
    listening, as it does in a real conversation (the hold is off by
    default since 2026-10-21).

score - re-scores every saved clip against the current voiceprints and
    prints, per label, how many clips each threshold/margin pair would
    name correctly, name wrongly, or leave unsure. Run it again after a
    re-enrollment or a model change; nothing needs re-recording.

Recordings are real voices: <out> defaults under stt_samples/, which is
git-ignored.

Run: venv/bin/python tests/speaker_lines.py record Chip
         [--port /dev/ttyUSB0] [--lead-in 10] [--lines N] [--out DIR]
     venv/bin/python tests/speaker_lines.py score [--out DIR] [--show]
"""

import argparse
import queue
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import speaker_id  # noqa: E402
from capture import RATE, Capture  # noqa: E402
from listener import Listener  # noqa: E402
from speaker_id import SpeakerID, load_wav, save_wav  # noqa: E402

OUT = "stt_samples/speaker_lines"
BOOT_S = 3.0          # Arduino resets when the serial port opens
THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50)
MARGINS = (0.05, 0.10, 0.15)


def describe(m):
    scores = "  ".join(f"{n} {s:.2f}" for n, s in sorted(m.scores.items()))
    return f"{m.name or '-'} ({m.reason or 'match'})  {scores}"


def record(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    taken = [int(m.group(1)) for p in out.glob(f"{args.label}_*.wav")
             if (m := re.fullmatch(rf"{re.escape(args.label)}_(\d+)\.wav", p.name))]
    n = max(taken, default=0)

    sid = SpeakerID()
    print(f"Enrolled: {', '.join(sid.voiceprints) or 'nobody'}")
    utterances = queue.Queue()
    listener = Listener(on_utterance=lambda s, t: utterances.put(s))
    cap = Capture(on_frame=listener.feed)
    writer = motion = None
    if args.port:
        import serial_link
        from motion import Motion
        writer = serial_link.SerialWriter(now_fn=time.monotonic, port=args.port)
        motion = Motion(writer, on_send=lambda c: None)

    print(f"Starting in {args.lead_in:g}s...", flush=True)
    time.sleep(args.lead_in)
    if writer:
        writer.start()
        motion.start()
        time.sleep(BOOT_S)
        motion.set_mode("on_watch")
    listener.start()
    cap.start()
    print(f"Listening - recording as {args.label!r}. Ctrl+C to stop.", flush=True)
    got = 0
    try:
        while args.lines is None or got < args.lines:
            samples = utterances.get()
            n += 1
            got += 1
            path = out / f"{args.label}_{n:02d}.wav"
            save_wav(path, samples)
            print(f"  {path.name}  {len(samples) / RATE:4.1f}s  {describe(sid.identify(samples))}",
                  flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        cap.stop()
        listener.stop()
        if motion:
            motion.stop()
            writer.stop()
    print(f"\n{got} clip(s) saved in {out}/ - `score` to see the threshold table.")


def verdict(scores, threshold, margin):
    """speaker_id.identify()'s rule, for any threshold/margin pair."""
    ranked = sorted(scores.values(), reverse=True)
    best, runner_up = ranked[0], (ranked[1] if len(ranked) > 1 else 0.0)
    if best < threshold or best - runner_up < margin:
        return None
    return max(scores, key=scores.get)


def score(args):
    sid = SpeakerID()
    if not sid.voiceprints:
        sys.exit("Nobody enrolled - run enroll_speaker.py first.")
    clips = []   # (label, file, scores) for every clip long enough to score
    skipped = 0
    for path in sorted(Path(args.out).glob("*_*.wav")):
        samples = load_wav(path)
        if len(samples) < speaker_id.MIN_SCORE_S * RATE:
            skipped += 1
            continue
        s = sid.score(sid.embed(samples))
        clips.append((path.stem.rsplit("_", 1)[0], path.name, s))
        if args.show:
            print(f"  {path.name:14s} {len(samples) / RATE:4.1f}s  "
                  + "  ".join(f"{n} {v:.2f}" for n, v in sorted(s.items())))
    if not clips:
        sys.exit(f"No clips in {args.out}/ - `record` some first.")
    labels = sorted({c[0] for c in clips})
    print(f"\nEnrolled: {', '.join(sid.voiceprints)}.  {len(clips)} clips scored"
          + (f", {skipped} under {speaker_id.MIN_SCORE_S:g}s skipped." if skipped else "."))

    print("\nScore against each voiceprint, per label (median, min-max):")
    for label in labels:
        own = [c[2] for c in clips if c[0] == label]
        cols = "   ".join(f"{name} {np.median([s[name] for s in own]):.2f} "
                          f"({min(s[name] for s in own):.2f}-{max(s[name] for s in own):.2f})"
                          for name in sorted(sid.voiceprints))
        print(f"  {label:8s} n={len(own):3d}   {cols}")

    print("\nright / WRONG / unsure per label, for each threshold and margin"
          f" (current: {speaker_id.MATCH_THRESHOLD:.2f} / {speaker_id.MATCH_MARGIN:.2f}):")
    print("  thresh margin   " + "   ".join(f"{label:>14s}" for label in labels))
    for t in THRESHOLDS:
        for mg in MARGINS:
            cells = []
            for label in labels:
                names = [verdict(c[2], t, mg) for c in clips if c[0] == label]
                right = sum(1 for v in names if v == label)
                wrong = sum(1 for v in names if v is not None and v != label)
                cells.append(f"{right:3d} /{wrong:3d} /{names.count(None):3d}")
            mark = " <" if (t, mg) == (speaker_id.MATCH_THRESHOLD, speaker_id.MATCH_MARGIN) else ""
            print(f"  {t:.2f}   {mg:.2f}     " + "   ".join(f"{c:>14s}" for c in cells) + mark)
    print("\nFor \"other\" every name is WRONG; \"right\" can only count for enrolled labels.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("label", help="who is really speaking: an enrolled name, or other")
    r.add_argument("--port", help="drive the head (On Watch sway) while listening")
    r.add_argument("--lead-in", type=float, default=10.0)
    r.add_argument("--lines", type=int)
    r.add_argument("--out", default=OUT)
    s = sub.add_parser("score")
    s.add_argument("--out", default=OUT)
    s.add_argument("--show", action="store_true", help="print every clip's scores")
    args = ap.parse_args()
    if args.cmd == "record":
        if "_" in args.label:
            sys.exit("Label can't contain '_' (it separates label from number in file names).")
        record(args)
    else:
        score(args)


if __name__ == "__main__":
    main()
