"""Captain Jack playback: the sole writer to the XVF3800's speaker output.

Implements the Playback thread from docs/specification.md section 4.16(e):
every sound Jack makes (TTS sentences, idle clips, canned clips) is
queued here as mono 16kHz int16 samples and played in order, back to
back. Each output block gets the output gain (build step 1) and is
duplicated from mono to the device's 2 channels - the one shared step at
the ALSA write (section 4.7).

Build step 6: beak-sync (section 4.8) hooks into the same per-block path
- an RMS envelope of what's actually being written is mapped to a beak
angle and handed to a SerialWriter (serial_link.py), timestamped with
the block's dac_time so the beak moves when the sound actually leaves
the speaker. Pass a SerialWriter as serial_writer= to enable it; without
one, Playback behaves exactly as before (no serial dependency for
testing/playback-only use).

Run standalone to play clips through the bird's speaker:
    venv/bin/python playback.py [clip.wav ...]
(defaults to wavFiles/DeadMenTellNoTales.wav)
Add --beak [PORT] to also drive the beak in sync (opens the Arduino).
"""

import queue
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

WAV_DIR = Path(__file__).parent / "wavFiles"

RATE = 16000        # XVF3800's fixed playback format: 16kHz, S16_LE, 2ch (spec 3.2)
CHANNELS = 2
BLOCK = 320         # 20ms per block = 50Hz, the top of beak-sync's 30-50Hz range (spec 4.8)
DEVICE_MATCH = "XVF3800"
ALSA_CARD = "Array"
HW_VOLUME_MAX = 60

# Open Issues issue 26 (resolved 2026-10-06): the onboard amp clipped above
# about -10dBFS even at max hardware volume. Fixed with an external amp fed
# from the XVF3800's 3.5mm jack, set to its lowest gain setting -- clean and
# adequately loud across the full digital range, so no gain cap is needed here.
OUTPUT_GAIN_DB = 0.0

# Beak-sync (spec 4.8): maps the played audio's smoothed RMS envelope to a
# beak angle (0=open, 60=closed - ServoControl.ino; silence rests closed).
# Starting points, not measured - tune by watching the real bird talk via
# tests/test_beak_sync_alignment.py.
BEAK_RANGE = 60
BEAK_FLOOR_DBFS = -40.0   # envelope at or below this: beak fully closed
BEAK_CEIL_DBFS = -15.0    # envelope at or above this: beak fully open
BEAK_ATTACK_S = 0.02      # envelope rise time constant - fast, opens promptly
BEAK_RELEASE_S = 0.10     # envelope fall time constant - slower, avoids a stutter between syllables


def dbfs(samples: np.ndarray) -> float:
    rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
    return 20 * np.log10(max(rms, 1e-9) / 32768)


def _approach(prev: float, target: float, dt: float, tau: float) -> float:
    """Exponential approach of prev toward target over dt seconds, time
    constant tau (bigger tau = slower)."""
    alpha = 1 - np.exp(-dt / tau)
    return prev + alpha * (target - prev)


def beak_angle(env_dbfs: float) -> int:
    """Map a smoothed dBFS envelope value to a beak angle (0=open, 60=closed)."""
    opening = (env_dbfs - BEAK_FLOOR_DBFS) / (BEAK_CEIL_DBFS - BEAK_FLOOR_DBFS)
    opening = min(max(opening, 0.0), 1.0) * BEAK_RANGE
    return int(round(BEAK_RANGE - opening))


def load_wav(path) -> np.ndarray:
    """Read a clip in the canonical stored format (16kHz, 16-bit, mono)."""
    path = Path(path)
    with wave.open(str(path)) as w:
        if (w.getframerate(), w.getsampwidth(), w.getnchannels()) != (RATE, 2, 1):
            raise ValueError(
                f"{path.name}: need 16kHz/16-bit/mono, got {w.getframerate()}Hz/"
                f"{w.getsampwidth() * 8}-bit/{w.getnchannels()}ch")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def find_device() -> int:
    for i, dev in enumerate(sd.query_devices()):
        if DEVICE_MATCH in dev["name"] and dev["max_output_channels"] >= CHANNELS:
            return i
    raise RuntimeError(f"no output device matching {DEVICE_MATCH!r} - is the reSpeaker plugged in?")


def set_hw_volume_max():
    """The interim gain cap assumes hardware volume is at max (spec 4.16)."""
    subprocess.run(["amixer", "-q", "-c", ALSA_CARD, "cset",
                    "name=PCM Playback Volume,index=0", f"{HW_VOLUME_MAX},{HW_VOLUME_MAX}"],
                   check=True)
    subprocess.run(["amixer", "-q", "-c", ALSA_CARD, "cset",
                    "name=PCM Playback Volume,index=1", str(HW_VOLUME_MAX)], check=True)


class Playback:
    """Plays queued mono buffers in order through the XVF3800.

    on_event(kind, tag, dac_time) is called with kind "started" or
    "finished" as each queued item begins and ends. dac_time is the
    stream clock time (see now()) at which that point actually reaches
    the speaker. It's called from the audio callback thread, so it must
    return quickly - e.g. just put the event on a queue.
    """

    def __init__(self, gain_db=OUTPUT_GAIN_DB, on_event=None, serial_writer=None):
        self.gain = 10 ** (gain_db / 20)
        self.on_event = on_event
        self.serial_writer = serial_writer
        self._beak_env_dbfs = BEAK_FLOOR_DBFS
        self._queue = queue.Queue()
        self._current = None        # (tag, samples) now playing
        self._pos = 0
        self._pending = 0           # items queued or playing, for wait_idle()
        self._lock = threading.Lock()
        self._idle = threading.Event()
        self._idle.set()
        self._last_dac_time = 0.0   # when the most recently finished item left the speaker
        self._stream = None

    def start(self):
        set_hw_volume_max()
        self._stream = sd.OutputStream(
            device=find_device(), samplerate=RATE, channels=CHANNELS,
            dtype="int16", blocksize=BLOCK, callback=self._callback)
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def now(self) -> float:
        """Current stream clock time, the same clock as dac_time in events."""
        return self._stream.time

    def play(self, samples: np.ndarray, tag=None):
        """Queue mono 16kHz int16 samples. Returns immediately."""
        with self._lock:
            self._pending += 1
            self._idle.clear()
        self._queue.put((tag, samples))

    def play_file(self, path, tag=None):
        self.play(load_wav(path), tag if tag is not None else Path(path).name)

    def wait_idle(self, timeout=None) -> bool:
        """Block until everything queued has been handed to the device."""
        return self._idle.wait(timeout)

    def wait_played(self, timeout=None) -> bool:
        """Block until everything queued has actually come out of the
        speaker - wait_idle() plus the device's output latency."""
        if not self.wait_idle(timeout):
            return False
        while self.now() < self._last_dac_time:
            time.sleep(0.02)
        return True

    def _emit(self, kind, tag, dac_time):
        if self.on_event:
            self.on_event(kind, tag, dac_time)

    def _callback(self, outdata, frames, time_info, status):
        mono = np.zeros(frames, dtype=np.float32)
        filled = 0
        while filled < frames:
            if self._current is None:
                try:
                    self._current = self._queue.get_nowait()
                except queue.Empty:
                    break
                self._pos = 0
                self._emit("started", self._current[0],
                           time_info.outputBufferDacTime + filled / RATE)
            tag, samples = self._current
            n = min(frames - filled, len(samples) - self._pos)
            mono[filled:filled + n] = samples[self._pos:self._pos + n]
            filled += n
            self._pos += n
            if self._pos >= len(samples):
                self._last_dac_time = time_info.outputBufferDacTime + filled / RATE
                self._emit("finished", tag, self._last_dac_time)
                self._current = None
                with self._lock:
                    self._pending -= 1
                    if self._pending == 0:
                        self._idle.set()

        out = (mono * self.gain).astype(np.int16)   # gain < 1, so no overflow

        if self.serial_writer is not None:
            level = dbfs(out)
            tau = BEAK_ATTACK_S if level > self._beak_env_dbfs else BEAK_RELEASE_S
            self._beak_env_dbfs = _approach(self._beak_env_dbfs, level, frames / RATE, tau)
            self.serial_writer.send_beak(beak_angle(self._beak_env_dbfs),
                                          time_info.outputBufferDacTime)

        outdata[:, 0] = out
        outdata[:, 1] = out


def main():
    import argparse
    import serial_link

    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("clips", nargs="*", default=["DeadMenTellNoTales.wav"])
    parser.add_argument("--beak", nargs="?", const=serial_link.PORT, default=None,
                         metavar="PORT", help="also drive the beak in sync (opens the Arduino)")
    args = parser.parse_args()
    clips = [Path(c) for c in args.clips]
    clips = [c if c.exists() else WAV_DIR / c for c in clips]

    events = queue.Queue()
    player = Playback(on_event=lambda kind, tag, t: events.put((kind, tag, t)))

    writer = None
    if args.beak:
        writer = serial_link.SerialWriter(now_fn=player.now, port=args.beak,
                                           on_send=lambda cmd: print(f"  -> {cmd}"))
        player.serial_writer = writer   # set before player.start() so the first callback sees it
        writer.start()

    player.start()
    try:
        for clip in clips:
            player.play_file(clip)
        player.wait_played()
        while not events.empty():
            kind, tag, t = events.get()
            print(f"  [{kind}] {tag}")
    finally:
        player.stop()
        if writer:
            writer.stop()


if __name__ == "__main__":
    main()
