"""Shutdown button: a long press on the enclosure's back button shuts Jack down.

Chip's button (2026-11-09, CLAUDE.md item 11) closes to ground and isn't
debounced. Wiring: GPIO26 (header pin 37) to one side, ground (pin 39) to
the other; the Pi's internal pull-up holds the line high, so pressed reads
low. No resistor or capacitor needed.

LongPress is the logic alone, fed (time, pressed) samples, so it can be
tested with a simulated, bouncing pin. ShutdownButton is the thread that
polls the real pin every POLL_S and calls on_long_press() once when a
press has been held HOLD_S.

Rules:
  - Debounce: the pin must read the same for DEBOUNCE_S before a change
    counts, so contact bounce on press or release is ignored, and so is
    a glitch shorter than that in the middle of a hold.
  - The hold is timed from the first low reading of the press that
    stuck, and fires once per press, HOLD_S after that.
  - A button already down when watching starts doesn't count: the pin
    must first be seen released, so a press held through a boot or
    restart doesn't shut Jack down the moment he comes up.

Run (watch the pin by hand; prints presses, never shuts anything down):
    venv/bin/python button.py [--hold 5]
"""

import argparse
import threading
import time

CHIP = "/dev/gpiochip0"     # the Pi 5's RP1 header GPIOs (pinctrl-rp1)
LINE = 26                   # GPIO26, header pin 37
HOLD_S = 5.0                # Chip: "at least 5 seconds"
DEBOUNCE_S = 0.05
POLL_S = 0.01


class LongPress:
    """Debounced long-press detector. update() returns True exactly once
    per press, when it has been held hold_s."""

    def __init__(self, hold_s=HOLD_S, debounce_s=DEBOUNCE_S):
        self.hold_s = hold_s
        self.debounce_s = debounce_s
        self.pressed = None        # debounced state; None until the first reading settles
        self.armed = False         # seen released at least once
        self._raw = None
        self._raw_since = 0.0
        self._press_t = None       # when the current debounced press began
        self._fired = False

    def update(self, t, pressed) -> bool:
        if pressed != self._raw:
            self._raw, self._raw_since = pressed, t
        if self._raw != self.pressed and t - self._raw_since >= self.debounce_s:
            self.pressed = self._raw
            if self.pressed:
                self._press_t, self._fired = self._raw_since, False
            else:
                self.armed = True
                self._press_t = None
        if (self.pressed and self.armed and not self._fired
                and t - self._press_t >= self.hold_s):
            self._fired = True
            return True
        return False

    def held_s(self, t) -> float:
        """How long the current press has been held (0 when released)."""
        return t - self._press_t if self.pressed and self._press_t is not None else 0.0


def gpio_reader(chip=CHIP, line=LINE):
    """A read() -> pressed function for the real pin, plus its close().
    Raises if the pin can't be had (no gpiod, line busy, no permission)."""
    import gpiod
    from gpiod.line import Bias, Direction, Value

    req = gpiod.request_lines(chip, consumer="captain-jack-button", config={
        line: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)})
    return (lambda: req.get_value(line) == Value.INACTIVE), req.release


class ShutdownButton:
    """Polls the button on its own thread; calls on_long_press() (on that
    thread) once per long press."""

    def __init__(self, on_long_press, read=None, now=time.monotonic,
                 hold_s=HOLD_S, poll_s=POLL_S):
        self.on_long_press = on_long_press
        self.read = read
        self.now = now
        self.poll_s = poll_s
        self.detector = LongPress(hold_s)
        self._close = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self.read is None:
            self.read, self._close = gpio_reader()
        self._thread = threading.Thread(target=self._run, name="button", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        if self._close:
            self._close()

    def _run(self):
        while not self._stop.is_set():
            if self.detector.update(self.now(), self.read()):
                self.on_long_press()
            self._stop.wait(self.poll_s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hold", type=float, default=HOLD_S)
    args = ap.parse_args()
    read, close = gpio_reader()
    d = LongPress(args.hold)
    print(f"Watching GPIO{LINE} (pin 37); long press = {args.hold:g}s. Ctrl+C to quit.")
    print(f"pin now: {'pressed' if read() else 'released'}", flush=True)
    last = None
    try:
        while True:
            t = time.monotonic()
            fired = d.update(t, read())
            if d.pressed != last and d.pressed is not None:
                print(f"{'pressed' if d.pressed else 'released'}"
                      f"{'' if d.armed or not d.pressed else ' (not armed: held since start)'}", flush=True)
                last = d.pressed
            if fired:
                print(f"LONG PRESS - Jack would shut down now", flush=True)
            time.sleep(POLL_S)
    except KeyboardInterrupt:
        print()
    finally:
        close()


if __name__ == "__main__":
    main()
