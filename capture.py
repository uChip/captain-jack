"""Captain Jack capture: the sole reader of the XVF3800's microphone input.

Implements the Capture thread from docs/specification.md section 4.16(a),
build step 2: reads the XVF3800's fixed 16kHz/S16_LE/2ch capture stream
continuously, keeps one channel, and hands 80ms mono frames (openWakeWord's
native frame size) to whoever consumes them - the Listener, in the full
program. Never stops reading, even while input is being ignored, so the
device buffer can't overrun.

Run standalone to record the chosen channel and print its level per second:
    venv/bin/python capture.py [seconds] [out.wav]
(defaults: 5 seconds, no file written)
"""

import queue
import sys
import threading
import wave

import numpy as np
import sounddevice as sd

RATE = 16000            # XVF3800's fixed capture format: 16kHz, S16_LE, 2ch (spec 3.2)
CHANNELS = 2
FRAME = 1280            # 80ms, openWakeWord's native frame size
DEVICE_MATCH = "XVF3800"

# Which of the two capture channels to keep. Channel 1 chosen 2026-09-25:
# channel 0 is more heavily processed (AGC boosted a normal speaking voice
# into digital clipping, and noise suppression gates the background after
# speech), while channel 1 has steady levels, headroom, and sounded
# cleaner by ear. See docs/log.md, 4.16.
CAPTURE_CHANNEL = 1


def find_device() -> int:
    for i, dev in enumerate(sd.query_devices()):
        if DEVICE_MATCH in dev["name"] and dev["max_input_channels"] >= CHANNELS:
            return i
    raise RuntimeError(f"no input device matching {DEVICE_MATCH!r} - is the reSpeaker plugged in?")


class Capture:
    """Reads the XVF3800 continuously and delivers mono 80ms frames.

    on_frame(samples, adc_time) is called once per frame with a mono
    int16 array of FRAME samples. adc_time is the stream clock time at
    which the frame's first sample was captured - the same clock as
    Playback's dac_time, so the two can be compared. It's called from
    the audio callback thread, so it must return quickly - e.g. just put
    the frame on a queue.
    """

    def __init__(self, on_frame, channel=CAPTURE_CHANNEL):
        self.on_frame = on_frame
        self.channel = channel
        self.overflows = 0      # times the device buffer overran (input lost)
        self._stream = None

    def start(self):
        self._stream = sd.InputStream(
            device=find_device(), samplerate=RATE, channels=CHANNELS,
            dtype="int16", blocksize=FRAME, callback=self._callback)
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, indata, frames, time_info, status):
        if status.input_overflow:
            self.overflows += 1
        self.on_frame(indata[:, self.channel].copy(), time_info.inputBufferAdcTime)


def dbfs(samples) -> float:
    rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
    return 20 * np.log10(max(rms, 1e-9) / 32768)


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    frames = queue.Queue()
    done = threading.Event()
    n_frames = int(seconds * RATE / FRAME)
    got = []

    def on_frame(samples, adc_time):
        if len(got) < n_frames:
            got.append(samples)
            frames.put(samples)
        else:
            done.set()

    cap = Capture(on_frame)
    print(f"Recording {seconds:g}s from channel {cap.channel}...")
    cap.start()
    try:
        per_second = RATE // FRAME * FRAME     # whole frames per ~1s line
        buf = []
        while not done.is_set() or not frames.empty():
            try:
                buf.append(frames.get(timeout=0.5))
            except queue.Empty:
                continue
            if len(buf) * FRAME >= per_second:
                chunk = np.concatenate(buf)
                print(f"  rms {dbfs(chunk):6.1f} dBFS   peak {np.abs(chunk.astype(int)).max():6d}")
                buf = []
    finally:
        cap.stop()
    if cap.overflows:
        print(f"  WARNING: {cap.overflows} input overflow(s) - audio was lost")

    if out_path:
        with wave.open(out_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(np.concatenate(got).tobytes())
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
