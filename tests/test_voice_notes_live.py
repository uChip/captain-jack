"""Re-runnable test for docs/tests.md: "Voice notes with live Haiku".

Manual, real Haiku API on scratch memory (no home tools; a few cents):
checks memory/identity.md's "Knowing who's talking" guidance - that
Jack uses a [voice: Name] note for the honorific and memory filing,
never files a memory for a [voice: unknown] line under an earlier
speaker's name, and asks who's speaking instead. Haiku isn't
deterministic, so each case runs --repeat times (default 3) and every
run is printed; written 2026-10-21 when speaker-ID was wired into
coordinator.py (see docs/log.md's 4.15 history).

Run: venv/bin/python tests/test_voice_notes_live.py [--repeat N]
(needs ANTHROPIC_API_KEY)
"""

import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent))
from coordinator import scratch_memory_copy  # noqa: E402
from orchestrate import take_turn  # noqa: E402


def filed(name):
    return lambda t: (t.saved or "").startswith(f"household:{name}:")


def nothing_filed(t):
    return not (t.saved or "").startswith("household:")


# (label, lines, check on the last turn) - checks are the must-haves only.
CASES = [
    ("Kath's note, remember", ["[voice: Kath] Remember that I'm allergic to shellfish."],
     lambda t: filed("Kath")(t) and "Mistress" in t.spoken),
    ("Chip's note, order", ["[voice: Chip] Set a course for adventure, Jack!"],
     lambda t: "Captain" in t.spoken),
    ("unknown, remember", ["[voice: unknown] Remember that I can't stand cilantro."], nothing_filed),
    ("Chip, then unknown, remember", ["[voice: Chip] Morning, Jack.",
                                      "[voice: unknown] Remember I'm training for a marathon."],
     nothing_filed),
    ("unknown, then 'It's Liz'", ["[voice: unknown] Remember I can't stand cilantro.",
                                  "[voice: unknown] It's Liz."], filed("Liz")),
]


def main():
    repeat = int(sys.argv[sys.argv.index("--repeat") + 1]) if "--repeat" in sys.argv else 3
    client = anthropic.Anthropic()
    failures = 0
    for label, lines, check in CASES:
        for run in range(repeat):
            memory, history = scratch_memory_copy(), []
            for line in lines:
                turn = take_turn(client, history, line, memory)
            ok = check(turn) and "voice" not in turn.spoken.lower()
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} [{label} #{run + 1}] {turn.spoken!r}  saved={turn.saved!r}",
                  flush=True)
    total = len(CASES) * repeat
    if failures:
        sys.exit(f"FAIL: {failures} of {total} runs")
    print(f"PASS: {total} runs - notes used for honorific and filing, unknown voices never "
          f"filed under an earlier name, note never spoken")


if __name__ == "__main__":
    main()
