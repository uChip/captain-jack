"""Re-runnable test for docs/tests.md: "Shutdown button (simulated pin)".

No hardware. Feeds button.py's LongPress (and the ShutdownButton thread,
on a fake clock) a simulated pin that bounces like a real undebounced
switch: a press held 5s fires once; contact bounce on press and release
never fires or double-fires; a short glitch mid-hold doesn't restart the
hold, but a real release does; a press held from the start doesn't count
until the button has been released once. Written 2026-11-09 (CLAUDE.md
item 11) before the button was wired.

Run: venv/bin/python tests/test_button.py
"""

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import button  # noqa: E402

STEP = button.POLL_S


def bounce(t0, settle_to, n=6, every=0.003):
    """Contact bounce: the pin flips n times, every few ms, then settles."""
    out = [(t0 + i * every, i % 2 == 0) for i in range(n)]
    return out + [(t0 + n * every, settle_to)]


def run(events, until, hold_s=5.0, start=False):
    """Simulate polling: events are (time, pressed) changes in the raw
    pin. Returns the times update() fired."""
    d = button.LongPress(hold_s)
    events = sorted(events)
    level, fired, t, i = start, [], 0.0, 0
    while t <= until:
        while i < len(events) and events[i][0] <= t:
            level = events[i][1]
            i += 1
        if d.update(t, level):
            fired.append(round(t, 2))
        t = round(t + STEP / 10, 4)    # poll faster than the bounce so it's seen
    return fired


def main():
    errors = []

    def check(name, got, want):
        if got != want:
            errors.append(f"{name}: fired at {got}, expected {want}")

    def near(name, got, at):
        if len(got) != 1 or abs(got[0] - at) > 0.06:
            errors.append(f"{name}: fired at {got}, expected once near {at}")

    # Clean 5.5s press at t=1 (pressed after bounce), released with bounce.
    press = bounce(1.0, True) + bounce(6.5, False)
    near("clean long press", run(press, 10), 6.0)

    # Bouncing on press and release, but only 3s held: never fires.
    check("short press", run(bounce(1.0, True) + bounce(4.0, False), 10), [])

    # A 20ms glitch (released) mid-hold doesn't restart the hold.
    glitch = bounce(1.0, True) + [(3.0, False), (3.02, True)] + bounce(8.0, False)
    near("glitch mid-hold", run(glitch, 10), 6.0)

    # A real 0.5s release mid-hold restarts it: fires 5s after the re-press.
    rehold = bounce(1.0, True) + bounce(3.0, False) + bounce(3.5, True) + bounce(10.0, False)
    near("released and re-pressed", run(rehold, 12), 8.5)

    # Held 20s: fires once, not every poll after 5s.
    near("one fire per press", run(bounce(1.0, True) + bounce(21.0, False), 25), 6.0)

    # Two separate long presses: two fires.
    two = bounce(1.0, True) + bounce(7.0, False) + bounce(9.0, True) + bounce(15.0, False)
    got = run(two, 16)
    if len(got) != 2:
        errors.append(f"two long presses: fired at {got}, expected twice")

    # Held since start (button down through a restart): no fire, even after
    # 10s; after a release, a fresh long press works.
    check("held from start", run([(10.0, False)], 12, start=True), [])
    near("held from start, then a fresh press",
         run([(10.0, False)] + bounce(11.0, True) + bounce(17.0, False), 18, start=True), 16.0)

    # The thread: fake pin and clock, a real thread; calls back exactly once.
    clock = [0.0]
    pin = [False]
    calls = []
    done = threading.Event()
    btn = button.ShutdownButton(lambda: (calls.append(clock[0]), done.set()),
                                read=lambda: pin[0], now=lambda: clock[0], poll_s=0.001)
    btn.start()
    for step in range(900):          # 9s of fake time in 10ms steps
        clock[0] = step * 0.01
        pin[0] = 1.0 <= clock[0] < 8.0
        threading.Event().wait(0.002)
    btn.stop()
    if len(calls) != 1 or not 5.9 <= calls[0] <= 6.2:
        errors.append(f"ShutdownButton thread: called back at {calls}, expected once near 6.0")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: a 5s press fires once; bounce, short presses and mid-hold glitches don't; "
          "a real release restarts the hold; a press held from start needs a release first; "
          "the polling thread calls back once")


if __name__ == "__main__":
    main()
