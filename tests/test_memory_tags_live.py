"""Re-runnable test for docs/tests.md: "Memory tag choice with live Haiku".

Manual, real Haiku API on scratch memory (no home tools; a few cents):
checks Jack files a "remember this" under the right MEMORY: tag - a
person's own preference under [household:Name], not [joke] or
[automation]; a running bit or nickname under [joke]; a lights/fans
preference under [automation]. Each line carries a speaker-ID voice
note, as coordinator.py sends it. Haiku isn't deterministic, so each
case runs --repeat times (default 3). Written 2026-10-21 after Kath's
"I love gardening on Sundays" was filed as [joke] in 2 of 3 runs (see
docs/log.md's 4.5 history).

Run: venv/bin/python tests/test_memory_tags_live.py [--repeat N]
(needs ANTHROPIC_API_KEY)
"""

import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent))
from coordinator import scratch_memory_copy  # noqa: E402
from orchestrate import take_turn  # noqa: E402

# (label, lines, expected tag prefix of the last turn's save)
CASES = [
    ("Kath, gardening (after Chip)", ["[voice: Chip] Morning, Jack.",
                                      "[voice: Kath] Jack, remember I love gardening on Sundays."],
     "household:Kath"),
    ("Kath, jazz", ["[voice: Kath] Remember that I'm a big fan of jazz."], "household:Kath"),
    ("Chip, coffee", ["[voice: Chip] Remember I always take my coffee black."], "household:Chip"),
    ("Chip, hates Mondays", ["[voice: Chip] Jack, remember that I can't stand Mondays."], "household:Chip"),
    ("nickname for the cat", ["[voice: Chip] From now on the cat's name is Admiral Whiskers, "
                              "and you have to salute when you say it."], "joke"),
    ("running bit", ["[voice: Kath] Every time someone says treasure, you should shout 'Where?' "
                     "Make that our thing."], "joke"),
    ("office light preference", ["[voice: Chip] Remember I like the office light on whenever "
                                 "I'm working in there."], "automation"),
]


def main():
    repeat = int(sys.argv[sys.argv.index("--repeat") + 1]) if "--repeat" in sys.argv else 3
    client = anthropic.Anthropic()
    failures = 0
    for label, lines, want in CASES:
        for run in range(repeat):
            memory, history = scratch_memory_copy(), []
            for line in lines:
                turn = take_turn(client, history, line, memory)
            ok = (turn.saved or "").startswith(want + ":")
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} [{label} #{run + 1}] want {want}, saved={turn.saved!r}",
                  flush=True)
    total = len(CASES) * repeat
    if failures:
        sys.exit(f"FAIL: {failures} of {total} runs")
    print(f"PASS: {total} runs - every memory filed under the expected tag")


if __name__ == "__main__":
    main()
