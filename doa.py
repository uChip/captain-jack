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
(180 since the 2026-11-08 inner-box enclosure - see JACK_FRONT_DEG) and the angle increases toward his right. Settled readings tell left
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

# Board angle of Jack's front. 84 on 2026-10-21 (matched the board layout's
# 90). Every walk-around since the 2026-11-07 enclosure rebuild puts it
# at 180-194, and it stayed at 180 once the board sat sealed in its own
# inner box (2026-11-08) - the board itself never moved (USB to the rear),
# so 180 is taken as right and the October 84 as the outlier
# (docs/log.md 4.9).
JACK_FRONT_DEG = 180

# DoaTracker's per-utterance direction: the value the board held longest
# while the person spoke. Changed 2026-10-21 from "the newest 8 readings":
# on session23 the window's start is still stuck on Jack's own reply and
# its end can swing after the talker stops - 12 right / 4 wrong / 3 unsure
# became 15 / 2 / 2 (docs/log.md 4.9). Tuned on that one session.
# Stale readings: if Jack's own sound (squawk, reply) moved the board, a
# winner that is still where his sound left it never heard the person: no
# answer. Changed 2026-11-08 from "what the board held just before they
# began": with one person talking from one spot (session24) the board
# rightly stays on them, and that rule threw away every line after the
# first from each spot. Now the board's value when the mic reopens is
# compared with where the person was last heard - unchanged means Jack's
# sound didn't move it, and it's still them. Two more changes the same day
# after session25 (7 of 10 right), checked by replaying its logged stream
# (tests/doa_replay.py): every place Jack's sound moved the board since the
# last utterance is refused, not just the last mic reopen (his own sound
# reads at a different angle each time - reflections - and the squawk's
# value was missed once the reply drifted off it), and only the second half
# of the utterance is counted (a person who has moved holds the board on
# their old spot for up to ~3.5s). Replayed: 8 right, none wrong, 1 none.
POLL_HZ = 10
KEEP_S = 35.0           # readings kept - longer than any utterance (Listener caps at 30s)
COUNT_FROM = 0.5        # count from this far through the utterance - before that the
                        # board can still be on the previous talker, or their old spot
SKIP_END_S = 0.5        # ...and can swing after they stop
MIN_READINGS = 5        # speech-flagged readings needed in between...
BIN_DEG = 15            # ...grouped into bins this wide...
MIN_SHARE = 0.4         # ...the biggest bin holding at least this share, or no answer

# Early turn (2026-11-08): once the Listener hears speech start, report a
# direction as soon as the board has moved off where it was when the mic
# reopened and held one
# direction (every reading within BIN_DEG of their median) for this many
# speech-flagged readings in a row - unless that's where Jack's own sound
# left it. Once per line; the end-of-line direction() then corrects it.
# Replayed on session25: 8 of 8 right, 0.6-2.0s into the line, vs 2.5-8s for
# the end-of-line turn (docs/log.md 4.9).
EARLY_SETTLE_N = 5
SPEECH_LEAD_S = 0.25    # the Listener knows an utterance has started after 250ms of speech
EARLY_WINDOW_S = 4.0    # no early direction later than this into the speech - after that it
                        # isn't early, and session26's one was a 16s non-speech sound


def to_jack(board_deg) -> float:
    """Board azimuth -> Jack's own angle, -180..180, + = to his right."""
    return (board_deg - JACK_FRONT_DEG + 180) % 360 - 180


def _apart(a, b) -> float:
    """Angle between two directions in degrees, 0-180."""
    return abs((a - b + 180) % 360 - 180)


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

    def __init__(self, read=None, now=time.monotonic, log=None, on_early=None):
        self._read = read
        self._now = now
        self._log = log                 # coordinator.py --save's doa_stream.csv (an open file), or None
        self.on_early = on_early        # called with a Jack angle, from the polling thread
        self._armed = False             # mic open, no early direction yet this line
        self._listen_t = 0.0            # when the mic reopened...
        self._reopen_angle = None       # ...and where the board was then
        self._start_angle = None        # board angle when Jack's current sound started
        self._early = None              # this line's early direction, if any...
        self.early_at = None            # ...and when it was found
        self._person = None             # Jack angle the last utterance ended on
        self._jack_angles = []          # where Jack's own sound moved the board since the last utterance
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
            t = self._now()
            self._readings.append((t, board_deg, speech))
            self._write(t, f"{board_deg},{int(speech)},")
            early = self._check_early() if self._armed and speech else None
        if early is not None and self.on_early:
            self.on_early(early)

    def _check_early(self):
        # Caller holds the lock. The last EARLY_SETTLE_N speech-flagged
        # readings since the mic reopened, if they agree and are new.
        if self._now() - self._listen_t - SPEECH_LEAD_S > EARLY_WINDOW_S:
            self._armed = False
            return None
        recent = []
        for t, az, speech in reversed(self._readings):
            if t < self._listen_t or len(recent) == EARLY_SETTLE_N:
                break
            if speech:
                recent.append(to_jack(az))
        if len(recent) < EARLY_SETTLE_N:
            return None
        mid = sorted(recent)[len(recent) // 2]
        if max(_apart(a, mid) for a in recent) > BIN_DEG:
            return None
        if self._reopen_angle is not None and _apart(mid, self._reopen_angle) <= BIN_DEG:
            return None        # hasn't moved: the same person, same spot, or still Jack's sound
        if any(_apart(mid, j) <= BIN_DEG for j in self._jack_angles):
            return None
        self._armed = False
        self._early = round(mid)
        self.early_at = self._now()
        self._write(self._now(), f",,early {self._early:+d}")
        return self._early

    def speech_started(self):
        """Call when the Listener hears an utterance start: from here until
        it ends (direction()) or Jack makes a sound, look for an early
        direction. Counting only from the speech, not from the mic
        reopening: sounds before it (footsteps, the board still settling)
        gave wrong early turns in the session25 replay."""
        with self._lock:
            self._armed = True
            self._listen_t = self._now() - SPEECH_LEAD_S
            self._early = None
            self._write(self._now(), ",,speech_started")

    def jack_started(self):
        """Call when Jack's own sound starts (squawk, reply, beep): the
        board's speech flag now means him, so no early direction until the
        mic reopens."""
        with self._lock:
            self._armed = False
            if self._readings:
                self._start_angle = to_jack(self._readings[-1][1])
            self._write(self._now(), ",,jack_started")

    def take_early(self):
        """This line's early direction (or None), cleared once read."""
        with self._lock:
            early, self._early = self._early, None
            return early

    def _write(self, t, rest):
        # Caller holds the lock. One line per reading or event, for replaying
        # a whole session offline (each uttNN_doa.csv holds only 2s before).
        if self._log:
            self._log.write(f"{t:.2f},{rest}\n")

    def jack_done(self):
        """Call when the mic reopens after Jack's own sound (squawk, reply,
        beep): notes where the board is now, and whether his sound moved it -
        off both where it was when that sound started (jack_started()) and
        where the person was last heard. The start too since session26:
        Chip spoke between the squawk and the reply, the board followed him,
        and comparing with the person alone took his new spot for Jack's own
        sound."""
        with self._lock:
            if not self._readings:
                return
            t, az, _ = self._readings[-1]
            angle = to_jack(az)
            off_start = self._start_angle is None or _apart(angle, self._start_angle) > BIN_DEG
            off_person = self._person is None or _apart(angle, self._person) > BIN_DEG
            self._start_angle = None
            moved = off_start and off_person
            if moved:
                self._jack_angles.append(angle)
            self._reopen_angle = angle
            self._early = None
            self._write(self._now(), f",,jack_done {angle:+.0f} moved={int(moved)}")

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
        still where Jack's own sound moved the board (see jack_done())."""
        now = self._now()
        start, end = now - utterance_s * (1 - COUNT_FROM), now - SKIP_END_S
        with self._lock:
            self._armed = False   # one early direction per line
            angles = [to_jack(az) for t, az, speech in self._readings if speech and start <= t <= end]
            jack_angles, self._jack_angles = self._jack_angles, []
            if angles:
                self._person = angles[-1]
            angle = self._pick(angles)
            if angle is not None and any(_apart(angle, j) <= BIN_DEG for j in jack_angles):
                angle = None
            self._write(now, f",,utterance {utterance_s:.1f}s -> {angle}")
        return None if angle is None else round(angle)

    @staticmethod
    def _pick(angles):
        if len(angles) < MIN_READINGS:
            return None
        groups = {}
        for a in angles:
            groups.setdefault(round(a / BIN_DEG), []).append(a)
        biggest = max(groups.values(), key=len)
        if len(biggest) < MIN_SHARE * len(angles):
            return None
        return sorted(biggest)[len(biggest) // 2]


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
