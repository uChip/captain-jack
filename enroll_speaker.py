"""Enroll a household member's voice for speaker recognition (spec 4.15).

    venv/bin/python enroll_speaker.py Name [--memory-dir DIR]

Name must already have a "### Name" heading in memory.md (Chip, Kath,
Liz) - enrollment never adds a household member. Prints one sentence
at a time; read each aloud to Jack after the beep, at your normal
distance and voice. After the last one, any recording that doesn't
match the others is asked for again. The voiceprint (the average of all
the recordings) and the recordings themselves go to voiceprints/,
overwriting any earlier enrollment for that name. Run it in its own
terminal, with the room fairly quiet. The servos aren't driven, so the
head stays still.
"""

import queue
from pathlib import Path
import sys

import numpy as np

from capture import RATE, Capture
from listener import HOLDOFF_S, Listener
from orchestrate import MEMORY_DIR, household_names
from playback import Playback
from speaker_id import SpeakerID, unit

SENTENCES = [
    "Ahoy, Captain Jack. It's a fine morning on the high seas.",
    "Could you switch on the kitchen lights and the patio fan, please?",
    "My favorite breakfast is scrambled eggs with toast and a cup of coffee.",
    "Seven sailors sold sixty silver shells down by the seashore.",
    "Tell me a joke about a parrot who lost his treasure map.",
    "We're driving to Phoenix on Thursday and should be back by dinner.",
    "What's the weather looking like for the garden this afternoon?",
    "That's all for now, Jack. Thank you kindly.",
]
MIN_CLIP_S = 1.5        # anything shorter was probably cut off - asked again
CONSISTENCY_MIN = 0.35  # a clip scoring below this against the rest is redone
MAX_REDOS = 2           # rounds of redoing inconsistent clips


class Recorder:
    """Beep, then return the next utterance the Listener hears."""

    def __init__(self):
        self.utterances = queue.Queue()
        self.listener = Listener(on_utterance=lambda s, t: self.utterances.put(s))
        self.player = Playback(on_event=self._on_playback)
        self.capture = Capture(on_frame=self.listener.feed)
        self.beep = (np.sin(2 * np.pi * 880 * np.arange(int(0.15 * RATE)) / RATE)
                     * 16000).astype(np.int16)

    def _on_playback(self, kind, tag, dac_time):
        if kind == "started":
            self.listener.ignore_until(float("inf"))
        else:
            self.listener.ignore_until(dac_time + HOLDOFF_S)

    def start(self):
        self.listener.start()
        self.capture.start()
        self.player.start()

    def stop(self):
        self.capture.stop()
        self.player.stop()
        self.listener.stop()

    def record(self, sentence):
        while True:
            print(f'\n  "{sentence}"', flush=True)
            while not self.utterances.empty():   # drop anything heard before the beep
                self.utterances.get_nowait()
            self.player.play(self.beep, "beep")
            samples = self.utterances.get()
            secs = len(samples) / RATE
            if secs >= MIN_CLIP_S:
                print(f"    got {secs:.1f}s")
                return samples
            print(f"    only {secs:.1f}s - once more, please")


def leave_one_out(embeddings):
    """Each clip's score against the average of all the others."""
    e = np.array(embeddings)
    total = e.sum(0)
    return [float(unit(total - e[i]) @ e[i]) for i in range(len(e))]


def main():
    args = sys.argv[1:]
    memory_dir = MEMORY_DIR
    if "--memory-dir" in args:
        i = args.index("--memory-dir")
        memory_dir = Path(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        sys.exit(__doc__)
    names = household_names(memory_dir)
    name = next((n for n in names if n.lower() == args[0].lower()), None)
    if name is None:
        sys.exit(f"{args[0]!r} isn't in memory.md's Household section "
                 f"({', '.join(names)}) - add their ### heading by hand first.")

    sid = SpeakerID()
    rec = Recorder()
    print(f"Enrolling {name}: {len(SENTENCES)} sentences. Read each one aloud after "
          f"the beep, in your normal voice. Ctrl+C to give up (nothing is saved).")
    rec.start()
    try:
        clips = [rec.record(s) for s in SENTENCES]
        embeddings = [sid.embed(c) for c in clips]
        for _ in range(MAX_REDOS):
            scores = leave_one_out(embeddings)
            redo = [i for i, s in enumerate(scores) if s < CONSISTENCY_MIN]
            if not redo:
                break
            print(f"\n{len(redo)} recording(s) didn't sound like the rest - again, please:")
            for i in redo:
                clips[i] = rec.record(SENTENCES[i])
                embeddings[i] = sid.embed(clips[i])
        else:
            scores = leave_one_out(embeddings)
            if any(s < CONSISTENCY_MIN for s in scores):
                sys.exit("\nStill inconsistent - nothing saved. Try a quieter room, "
                         "or check only one person is speaking.")
    except KeyboardInterrupt:
        sys.exit("\nStopped - nothing saved.")
    finally:
        rec.stop()

    others = sid.score(unit(np.mean(embeddings, 0)))
    others.pop(name, None)
    sid.save_voiceprint(name, embeddings, clips)
    print(f"\nSaved {name}'s voiceprint ({sum(map(len, clips)) / RATE:.0f}s of speech). "
          f"Consistency {min(scores):.2f}-{max(scores):.2f}.")
    for other, s in sorted(others.items()):
        print(f"  similarity to {other}: {s:.2f}")


if __name__ == "__main__":
    main()
