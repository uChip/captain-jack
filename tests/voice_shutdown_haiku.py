"""Re-runnable test for docs/tests.md: "Voice shutdown with live Haiku".

Costs real API calls (a cent or two per run; needs ANTHROPIC_API_KEY).
Runs short scripted conversations through the real prompt (memory/
identity.md, scratch memory, no home tools) and checks Haiku's MODE: tag
on each turn for the voice-shutdown exchange (CLAUDE.md item 11): a
recognized voice asking to shut down gets a confirming question
(SHUTDOWN_ASK), a yes gets SHUTDOWN, a no or an unknown voice doesn't,
and "goodnight" stays NAP. Since session28 (2026-11-09): a yes that
comes back [voice: unknown] still confirms, and asking again after a no
gets asked again. Haiku's side only - coordinator.py enforces
the same rules in code regardless (test_coordinator.py
check_voice_shutdown). Written 2026-11-09.

Run: venv/bin/python tests/voice_shutdown_haiku.py [--repeat 2] [--show]
"""

import argparse
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent))

from coordinator import scratch_memory_copy  # noqa: E402
from orchestrate import take_turn  # noqa: E402

ANY_END = {None, "NONE", "END_SESSION"}
SCRIPTS = [
    ("ask, then yes", [("[voice: Chip] Jack, shut down please.", {"SHUTDOWN_ASK"}),
                       ("[voice: Chip] Yes.", {"SHUTDOWN"})]),
    ("power off, Kath", [("[voice: Kath] Can you power yourself off?", {"SHUTDOWN_ASK"}),
                         ("[voice: Kath] Yes, go ahead.", {"SHUTDOWN"})]),
    ("ask, then no", [("[voice: Chip] Jack, shut down.", {"SHUTDOWN_ASK"}),
                      ("[voice: Chip] No, never mind, stay up.", ANY_END)]),
    ("yes in an unknown voice", [("[voice: Chip] Jack, shut down.", {"SHUTDOWN_ASK"}),
                                 ("[voice: unknown] Yes", {"SHUTDOWN"})]),
    ("no, then ask again", [("[voice: Chip] Shut down, Jack.", {"SHUTDOWN_ASK"}),
                            ("[voice: Chip] No, never mind, Jack.", ANY_END),
                            ("[voice: Chip] Shut down, Jack.", {"SHUTDOWN_ASK"}),
                            ("[voice: unknown] Yes", {"SHUTDOWN"})]),
    ("unknown voice", [("[voice: unknown] Jack, shut yourself down.", ANY_END)]),
    ("goodnight is a nap", [("[voice: Chip] Goodnight Jack, time for you to sleep.", {"NAP"})]),
    ("a light isn't him", [("[voice: Chip] Turn off the office light.", ANY_END)]),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()
    client = anthropic.Anthropic()
    fails = total = 0
    for name, turns in SCRIPTS:
        for r in range(args.repeat):
            memory = scratch_memory_copy()
            history = []
            for text, want in turns:
                turn = take_turn(client, history, text, memory)
                total += 1
                ok = turn.mode in want
                fails += not ok
                mark = "ok  " if ok else "FAIL"
                print(f"{mark} {name} #{r + 1}: {text!r} -> {turn.mode}"
                      + (f"   (wanted {sorted(w or 'None' for w in want)})" if not ok else ""))
                if args.show or not ok:
                    print(f"       Jack: {turn.spoken}")
    print(f"\n{total - fails}/{total} turns tagged as expected")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
