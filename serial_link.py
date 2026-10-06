"""Captain Jack serial link: the sole writer to the Arduino.

Implements the Serial writer thread from docs/specification.md section
4.16(f), build step 6: owns /dev/ttyUSB0, the one-directional Pi->Arduino
link (section 4.13). Takes beak commands from Playback - latest-wins, if
several queue up before one is sent, only the newest goes out, since a
stale beak position is worse than a skipped one - and (from build step 7
onward) head/gesture commands from Motion, an ordinary FIFO, none
dropped.

A beak command carries the dac_time (Playback's stream clock) of the
audio block it was computed from, and is held until that time arrives
rather than sent immediately - so the beak moves when the sound actually
leaves the speaker, compensating for the output device's own buffering
delay, not when Playback happened to compute it. See
docs/specification.md section 4.8 and ALIGNMENT_FUDGE_S below.

Run standalone for a quick wiggle check (no Playback needed):
    venv/bin/python serial_link.py [--port /dev/ttyUSB0] [--dry-run]
"""

import argparse
import queue
import threading
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

# Opening the port toggles DTR, which resets the Arduino into
# ServoControl.ino's ~2.5s DEBUG startup self-test (beak open/close a few
# times) before it's ready for real commands. See ServoControl.ino,
# exercise_hardware.py.
ARDUINO_BOOT_DELAY_S = 3.5

BEAK_RANGE = 60   # ServoControl.ino: 0 = beak open, 60 = beak fully closed (rest)

# Small fixed correction layered on top of the dac_time/now() delay
# already available from Playback's stream clock: serial transmission
# (a few bytes at 115200 baud) plus Arduino parsing and servo mechanical
# response (beak has no easing - Open Issues issue 8 - so this is just
# raw PWM response time). Expected to be near zero by physics; tune by
# watching/listening against AlignmentTone.wav
# (tests/test_beak_sync_alignment.py) before trusting it.
ALIGNMENT_FUDGE_S = 0.0

# How often the writer thread checks for new work when there's nothing
# to send. Small relative to the 20ms block period so a beak command
# isn't held up noticeably once its dac_time arrives.
POLL_INTERVAL_S = 0.005


class SerialWriter:
    """Owns the Arduino serial port.

    now_fn must return the same stream-clock time as the dac_time passed
    to send_beak() - in the real pipeline, a Playback instance's now().

    on_send(cmd), if given, is called with every command string actually
    written (or that would be written, in dry-run) - for testing without
    a real port.
    """

    def __init__(self, now_fn, port=PORT, dry_run=False, on_send=None):
        self.now_fn = now_fn
        self.dry_run = dry_run
        self.on_send = on_send
        self._port_name = port
        self._ser = None
        self._beak_lock = threading.Lock()
        self._beak_pending = None   # (angle, dac_time) not yet sent
        self._head_queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if not self.dry_run:
            import serial

            self._ser = serial.Serial(self._port_name, BAUD, timeout=0.2)
            time.sleep(ARDUINO_BOOT_DELAY_S)
            self._drain()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._ser:
            self._ser.close()
            self._ser = None

    def send_beak(self, angle: int, dac_time: float):
        """Queue a beak angle (0=open..60=closed), released when dac_time
        arrives. Overwrites any not-yet-sent beak command. Called from
        Playback's audio callback - must not block."""
        with self._beak_lock:
            self._beak_pending = (angle, dac_time)

    def send_head(self, cmd: str):
        """Queue a raw p/r/y/t/s command string (build step 7+), sent in
        order, never dropped."""
        self._head_queue.put(cmd)

    def _drain(self):
        if self._ser and self._ser.in_waiting:
            self._ser.read(self._ser.in_waiting)

    def _write(self, cmd):
        if self.on_send:
            self.on_send(cmd)
        if not self.dry_run:
            self._ser.write(cmd.encode())

    def _run(self):
        while not self._stop.is_set():
            sent = self._send_head_if_any()
            sent = self._send_beak_if_due() or sent
            if not sent:
                time.sleep(POLL_INTERVAL_S)

    def _send_head_if_any(self) -> bool:
        try:
            self._write(self._head_queue.get_nowait())
            return True
        except queue.Empty:
            return False

    def _send_beak_if_due(self) -> bool:
        with self._beak_lock:
            pending = self._beak_pending
        if pending is None:
            return False
        angle, dac_time = pending
        if self.now_fn() < dac_time - ALIGNMENT_FUDGE_S:
            return False
        self._write(f"b{angle}")
        with self._beak_lock:
            if self._beak_pending == pending:
                self._beak_pending = None
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", default=PORT)
    parser.add_argument("--dry-run", action="store_true", help="print commands instead of opening a port")
    args = parser.parse_args()

    writer = SerialWriter(now_fn=time.monotonic, port=args.port, dry_run=args.dry_run,
                           on_send=lambda cmd: print(f"  -> {cmd}"))
    print(f"Opening {args.port}..." if not args.dry_run else "[dry-run] not opening a serial port")
    writer.start()
    try:
        print("Wiggling the beak (open, closed, open, closed)...")
        for angle in (0, BEAK_RANGE, 0, BEAK_RANGE):
            writer.send_beak(angle, time.monotonic())
            time.sleep(0.6)
    finally:
        writer.stop()


if __name__ == "__main__":
    main()
