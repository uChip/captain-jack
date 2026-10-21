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

# DoaTracker's per-utterance direction: the value the board held longest
# while the person spoke. Changed 2026-10-21 from "the newest 8 readings":
# on session23 the window's start is still stuck on Jack's own reply and
# its end can swing after the talker stops - 12 right / 4 wrong / 3 unsure
# became 15 / 2 / 2 (docs/log.md 4.9). Tuned on that one session. If the
# winner is just what the board already held before they started, it
# never heard them (twice it was still on Jack's own voice): no answer.
POLL_HZ = 10
KEEP_S = 35.0           # readings kept - longer than any utterance (Listener caps at 30s)
SKIP_START_S = 0.5      # the board is still on the previous talker (often Jack)
SKIP_END_S = 0.5        # ...and can swing after they stop
MIN_READINGS = 5        # speech-flagged readings needed in between...
BIN_DEG = 15            # ...grouped into bins this wide...
MIN_SHARE = 0.4         # ...the biggest bin holding at least this share, or no answer


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
        self._readings = deque(maxlen=int(POLL_HZ * KEEP_S))
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

    def recent(self, seconds):
        """[(age_s, board_deg, speech)] for the last seconds, oldest first -
        for coordinator.py --save's per-utterance DoA log."""
        now = self._now()
        with self._lock:
            return [(round(now - t, 2), az, speech) for t, az, speech in self._readings
                    if t >= now - seconds]

    def direction(self, utterance_s):
        """Jack's angle to whoever just finished an utterance_s-long
        utterance (+ = his right): the median of the most common
        BIN_DEG-wide group of speech-flagged readings taken while they
        spoke, or None if there are too few, no group dominates, or it's
        the same direction the board held before they began."""
        now = self._now()
        began = now - utterance_s
        start, end = began + SKIP_START_S, now - SKIP_END_S
        with self._lock:
            angles = [to_jack(az) for t, az, speech in self._readings if speech and start <= t <= end]
            before = [to_jack(az) for t, az, _ in self._readings if t < began]
        if len(angles) < MIN_READINGS:
            return None
        groups = {}
        for a in angles:
            groups.setdefault(round(a / BIN_DEG), []).append(a)
        biggest = max(groups.values(), key=len)
        if len(biggest) < MIN_SHARE * len(angles):
            return None
        angle = sorted(biggest)[len(biggest) // 2]
        if before and abs((angle - before[-1] + 180) % 360 - 180) <= BIN_DEG:
            return None
        return round(angle)


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
