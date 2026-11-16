"""Manual hardware tool for docs/tests.md: "Audio path tone trace".

Plays a continuous sine tone (default 800Hz) through the XVF3800 until
Ctrl+C, for tracing the audio path XVF3800 3.5mm jack -> amp -> speaker
with a probe, meter, scope or headphones, and for wiggling connectors
while listening for dropouts.

The stream is generated live (no file), so it runs indefinitely. Hardware
volume is set to max first, the same as playback.py, so the only variable
is the --level digital level. Once a second it prints a status line;
"underrun"/"xrun" flags or a lost device mean a problem on the Pi/USB side,
not the analog wiring.

The Jack service holds the audio device exclusively - stop it first:
    sudo systemctl stop captain-jack

Run: venv/bin/python tests/tone_trace.py [--freq 800] [--level -10]
         [--channel both|left|right] [--pulse SECONDS]
  --level   dBFS of the tone peak (default -10; 0 is full scale)
  --channel which XVF3800 output channel carries the tone (default both),
            to check whether the amp is fed from left, right, or a mix
  --pulse   alternate tone/silence every SECONDS instead of continuous -
            makes an intermittent easier to tell from a steady signal
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playback import CHANNELS, RATE, find_device, set_hw_volume_max  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--freq", type=float, default=800.0)
    ap.add_argument("--level", type=float, default=-10.0, help="peak dBFS")
    ap.add_argument("--channel", choices=["both", "left", "right"], default="both")
    ap.add_argument("--pulse", type=float, default=0.0,
                    help="seconds on / seconds off (0 = continuous)")
    args = ap.parse_args()
    if args.level > 0:
        sys.exit("--level must be <= 0 dBFS")

    amp = 10 ** (args.level / 20)
    chan_mask = {"both": [1, 1], "left": [1, 0], "right": [0, 1]}[args.channel]
    chan_mask = np.array(chan_mask, dtype=np.float32)
    phase_step = 2 * np.pi * args.freq / RATE
    state = {"phase": 0.0, "frame": 0, "flags": set()}

    def callback(outdata, frames, time_info, status):
        if status:
            state["flags"].add(str(status))
        n = np.arange(frames)
        tone = amp * np.sin(state["phase"] + phase_step * n)
        if args.pulse > 0:
            t = (state["frame"] + n) / RATE
            tone *= (np.floor(t / args.pulse) % 2 == 0)
        state["phase"] = (state["phase"] + phase_step * frames) % (2 * np.pi)
        state["frame"] += frames
        outdata[:] = (tone[:, None] * chan_mask[None, :CHANNELS] * 32767).astype(np.int16)

    try:
        device = find_device()
    except RuntimeError as e:
        sys.exit(str(e))
    set_hw_volume_max()
    mode = f"pulsed {args.pulse:g}s on/off" if args.pulse > 0 else "continuous"
    print(f"Playing {args.freq:g}Hz at {args.level:+g}dBFS, {args.channel} "
          f"channel(s), {mode}, on {sd.query_devices(device)['name']}. Ctrl+C to stop.")

    start = time.monotonic()
    try:
        with sd.OutputStream(device=device, samplerate=RATE, channels=CHANNELS,
                             dtype="int16", callback=callback):
            while True:
                time.sleep(1)
                flags = state["flags"]
                state["flags"] = set()
                note = ("  ** " + ", ".join(sorted(flags))) if flags else ""
                print(f"\r{time.monotonic() - start:7.0f}s playing{note}   ",
                      end="\n" if flags else "", flush=True)
    except KeyboardInterrupt:
        print("\nStopped.")
    except sd.PortAudioError as e:
        sys.exit(f"\nAudio stream failed (device lost?): {e}")


if __name__ == "__main__":
    main()
