"""Re-runnable test for docs/tests.md: "Clean stop on SIGTERM/SIGHUP".

No hardware. coordinator.install_stop_signals() must turn SIGTERM (systemd
stopping the service, `sudo poweroff`) and SIGHUP (a dropped SSH session)
into a Stop raised in the main thread - even while it's blocked waiting
on the event queue, as Coordinator.run() is most of the time - so run()'s
finally does the same clean stop as Ctrl+C. After the first signal both
are ignored, so a second can't cut that stop short. Written 2026-11-09
(CLAUDE.md item 11, boot straight into Jack).

Run: venv/bin/python tests/test_stop_signal.py
"""

import os
import queue
import signal
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import coordinator  # noqa: E402


def blocked_until(sig):
    """Block on an empty queue (no timeout, as run() does Asleep) and
    send ourselves sig from another thread; return what was raised."""
    threading.Timer(0.2, os.kill, (os.getpid(), sig)).start()
    try:
        queue.Queue().get(timeout=5)
    except coordinator.Stop as e:
        return e
    except queue.Empty:
        return None


def main():
    errors = []
    saved = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGHUP)}
    try:
        for sig in (signal.SIGTERM, signal.SIGHUP):
            coordinator.install_stop_signals()
            e = blocked_until(sig)
            if e is None:
                errors.append(f"{sig.name} didn't interrupt a blocked event wait")
            elif str(e) != sig.name:
                errors.append(f"{sig.name}: Stop says {e!s}")
            for other in (signal.SIGTERM, signal.SIGHUP):
                if signal.getsignal(other) != signal.SIG_IGN:
                    errors.append(f"after {sig.name}, {other.name} should be ignored during the stop")
            os.kill(os.getpid(), signal.SIGTERM)   # ignored now: must not raise or kill us
    finally:
        for s, h in saved.items():
            signal.signal(s, h)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("PASS: SIGTERM and SIGHUP each raise Stop in the main thread, even mid-wait, "
          "and a second signal during the clean stop is ignored")


if __name__ == "__main__":
    main()
