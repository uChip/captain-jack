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

Not yet calibrated to the bird - first walk-around (2026-10-15) was
inconclusive with the bird loosely placed and household noise; redo after
the remount (docs/log.md's 4.9 history, tests/doa_walkaround.py).

Run standalone to print readings:
    venv/bin/python doa.py [--seconds 10]
"""

import math
import struct
import time

import usb.core
import usb.util

VID, PID = 0x2886, 0x001A
_IN = usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
TIMEOUT_MS = 1000

# name: (resid, cmdid, payload bytes)
VERSION = (48, 0, 3)
DOA_VALUE = (20, 18, 4)            # uint16 degrees, then a speech-detected flag
AEC_AZIMUTH_VALUES = (33, 75, 16)  # 4 x float32 radians, one per beam


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
