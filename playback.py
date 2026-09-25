"""Captain Jack playback: the sole writer to the XVF3800's speaker output.

Implements the Playback thread from docs/specification.md section 4.16(e),
build step 1: every sound Jack makes (TTS sentences, idle clips, canned
clips) is queued here as mono 16kHz int16 samples and played in order,
back to back. Each output block gets the interim output gain cap
(Open Issues issue 26) and is duplicated from mono to the device's 2
channels - the one shared step at the ALSA write (section 4.7).

Beak-sync (build step 6) will hook into the same per-block path.

Run standalone to play clips through the bird's speaker:
    venv/bin/python playback.py [clip.wav ...]
(defaults to wavFiles/DeadMenTellNoTales.wav)
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

# Interim fix for Open Issues issue 26: the onboard amp clips above about
# -10dBFS even at max hardware volume. Clips and TTS peak near 0dBFS, so a
# fixed -10dB gain holds output at the level ladder's clean step 2.
OUTPUT_GAIN_DB = -10.0


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

    def __init__(self, gain_db=OUTPUT_GAIN_DB, on_event=None):
        self.gain = 10 ** (gain_db / 20)
        self.on_event = on_event
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
        outdata[:, 0] = out
        outdata[:, 1] = out


def main():
    clips = [Path(a) for a in sys.argv[1:]] or [WAV_DIR / "DeadMenTellNoTales.wav"]
    clips = [c if c.exists() else WAV_DIR / c for c in clips]

    events = queue.Queue()
    player = Playback(on_event=lambda kind, tag, t: events.put((kind, tag, t)))
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


if __name__ == "__main__":
    main()
