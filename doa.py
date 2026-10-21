"""Read direction of arrival (DoA) from the reSpeaker XVF3800.

Spec section 4.9. The board answers vendor control requests on USB
endpoint 0 - no driver, no claimed interface, so reading never disturbs
the audio streams Capture/Playback have open. Parameter ids come from
Seeed's own python_control/respeaker_get_doa.py
(github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY, commit 4b49bfd,
found 2026-10-15); that repo also ships an rpi_64bit `xvf_host` binary
with the full command set, not needed for these reads.

Needs read/write access to the board's USB device node, which is
root-only by default. Installed on this Pi 2026-10-15:
    /etc/udev/rules.d/99-respeaker.rules:
    SUBSYSTEM=="usb", ATTR{idVendor}=="2886", ATTR{idProduct}=="001a", MODE="0660", GROUP="plugdev"
(apply to an already-plugged board with
`sudo udevadm trigger --action=add --subsystem-match=usb --attr-match=idVendor=2886`;
a plain `udevadm trigger` didn't).

Calibrated 2026-10-21 (tests/doa_walkaround.py, bird at the rear of the
enclosure - centered, it blocks a mic): Jack's front is board 84 degrees
and the angle increases toward his right. Settled readings tell left
from right reliably, but fine angles are rough and the reading lags a
new talker by 2-6s, so DoaTracker gives one direction per utterance -
the head turns once, toward whoever just spoke - not continuous
tracking (spec 4.9, docs/log.md's 4.9 history).

Run standalone to print readings:
    venv/bin/python doa.py [--seconds 10]
"""

import math
import struct
import threading
import time
from collections import deque

import usb.core
import usb.util

VID, PID = 0x2886, 0x001A
_IN = usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
TIMEOUT_MS = 1000

# name: (resid, cmdid, payload bytes)
VERSION = (48, 0, 3)
DOA_VALUE = (20, 18, 4)            # uint16 degrees, then a speech-detected flag
AEC_AZIMUTH_VALUES = (33, 75, 16)  # 4 x float32 radians, one per beam

JACK_FRONT_DEG = 84     # board angle of Jack's front, measured 2026-10-21

# DoaTracker's per-utterance direction - starting values, judged by eye.
POLL_HZ = 10
LOOKBACK_S = 3.0        # utterance end is detected ~0.7s after speech stops
LAST_READINGS = 8       # the newest speech-flagged readings in the lookback...
MIN_READINGS = 5        # ...need at least this many...
MAX_SPREAD_DEG = 25     # ...agreeing this closely (circular std dev), or no answer


def to_jack(board_deg) -> float:
    """Board azimuth -> Jack's own angle, -180..180, + = to his right."""
    return (board_deg - JACK_FRONT_DEG + 180) % 360 - 180


def circular_mean(degs) -> tuple[float, float]:
    """(mean, spread) of angles in degrees; spread is the circular std dev."""
    a = [math.radians(d) for d in degs]
    c, s = sum(map(math.cos, a)) / len(a), sum(map(math.sin, a)) / len(a)
    r = max(math.hypot(c, s), 1e-9)
    return math.degrees(math.atan2(s, c)) % 360, math.degrees(math.sqrt(-2 * math.log(min(r, 1.0))))


class DoA:
    def __init__(self):
        self.dev = usb.core.find(idVendor=VID, idProduct=PID)
        if self.dev is None:
            raise RuntimeError("reSpeaker XVF3800 not found on USB")

    def _read(self, param) -> bytes:
        resid, cmdid, n = param
        # First byte back is a status byte, then the payload.
        return self.dev.ctrl_transfer(_IN, 0, 0x80 | cmdid, resid, n + 1, TIMEOUT_MS).tobytes()[1:]

    def version(self) -> tuple:
        return tuple(self._read(VERSION))

    def read(self) -> tuple[int, bool]:
        """(azimuth in degrees 0-359 in the board's own frame, speech
        detected). The board holds its last value while nobody's talking,
        including while Jack himself speaks."""
        b = self._read(DOA_VALUE)
        return b[0] | (b[1] << 8), bool(b[2])

    def beam_azimuths(self) -> list[float]:
        """The four per-beam azimuths, degrees."""
        return [math.degrees(a) for a in struct.unpack("<4f", self._read(AEC_AZIMUTH_VALUES))]

    def close(self):
        usb.util.dispose_resources(self.dev)


class DoaTracker:
    """Polls the board on its own thread and answers "where did that
    utterance come from?" once it has ended. read is any function
    returning (board azimuth, speech flag) - DoA().read by default; tests
    pass a fake."""

    def __init__(self, read=None, now=time.monotonic):
        self._read = read
        self._now = now
        self._readings = deque(maxlen=int(POLL_HZ * LOOKBACK_S * 2))
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._doa = None

    def start(self):
        if self._read is None:
            self._doa = DoA()
            self._read = self._doa.read
        self._thread = threading.Thread(target=self._run, name="doa", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        if self._doa:
            self._doa.close()

    def _run(self):
        while not self._stop.wait(1 / POLL_HZ):
            try:
                az, speech = self._read()
            except Exception:   # a USB hiccup - skip this reading, keep polling
                continue
            self.add(az, speech)

    def add(self, board_deg, speech):
        with self._lock:
            self._readings.append((self._now(), board_deg, speech))

    def direction(self):
        """Jack's angle to whoever just finished speaking (+ = his right),
        or None if the recent speech readings are too few or disagree."""
        cutoff = self._now() - LOOKBACK_S
        with self._lock:
            recent = [az for t, az, speech in self._readings if speech and t >= cutoff]
        recent = recent[-LAST_READINGS:]
        if len(recent) < MIN_READINGS:
            return None
        mean, spread = circular_mean(recent)
        return round(to_jack(mean)) if spread <= MAX_SPREAD_DEG else None


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seconds", type=float, default=10.0)
    args = parser.parse_args()
    doa = DoA()
    print("firmware", ".".join(map(str, doa.version())))
    end = time.monotonic() + args.seconds
    while time.monotonic() < end:
        az, speech = doa.read()
        beams = " ".join(f"{a:4.0f}" for a in doa.beam_azimuths())
        print(f"doa {az:3d}{' speech' if speech else '       '}   beams {beams}", flush=True)
        time.sleep(0.25)
    doa.close()


if __name__ == "__main__":
    main()
