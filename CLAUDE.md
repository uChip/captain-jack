# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

This Claude Code session runs directly on the bird's own Raspberry Pi 5
(headless, accessed via SSH from Chip's desktop) — not a separate dev
machine. Hardware-facing checks (USB devices, serial ports, audio devices)
can be run directly from a session in this repo; there's no "deploy to the
Pi" step to account for.

Early implementation. `orchestrate.py` is Captain Jack's text-only
conversation loop: loads `memory/identity.md` + `memory/memory.md` as the
system prompt, calls the Claude API (Haiku), and parses/validates/saves the
model's proposed `MEMORY:` line per `docs/captain-jack-memory-design.md`.
`coordinator.py` runs the voice loop (spec section 4.16): press Enter,
speak, and Jack answers aloud (`tts.py`, kokoro-pi, voice `am_santa`).
It builds on `playback.py`, `capture.py`, `listener.py` and `stt.py`. The Pi<->Arduino serial link's command syntax is locked down and
implemented (`arduino/ServoControl/ServoControl.ino`, see
`docs/specification.md` section 4.13); the Arduino drives all four servos
(head pitch/roll/yaw + beak) correctly from real commands. The reSpeaker
XVF3800 is USB-connected to the Pi with the bird's speaker (40mm, 4Ω,
5W) wired to its output (2026-09-25), but isn't mounted to the statue yet. Playback through
it is confirmed working, but the onboard amp/speaker clips well below
digital full scale — see `docs/specification.md` Open Issues issue 26.
No home-automation tool calling yet
either — the intent allowlist (next-step below) isn't wired into a tool
schema.

**This file and `docs/specification.md` describe current state and
project definition only.** For design changes, what didn't work,
learnings from implementation/testing, alternatives considered, and why a
decision was made the way it was, see `docs/log.md` — read it before
answering questions about project history, direction, or trade-offs, not
just when doing narrow implementation.

### Running it

```bash
sudo apt install -y libportaudio2          # system library sounddevice needs (installed)
venv/bin/pip install -r requirements.txt  # already installed in venv/
ANTHROPIC_API_KEY=... venv/bin/python orchestrate.py   # text-only conversation loop
venv/bin/python playback.py [clip.wav ...]             # play clips through the bird
venv/bin/python listener.py [--model base.en]          # print transcripts of speech to the bird
venv/bin/python coordinator.py --scratch-memory        # voice loop; own terminal (reads Enter)
```

Model files live in `models/` (git-ignored — download once):

```bash
mkdir -p models && cd models
curl -fLO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin
curl -fLO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
curl -fL -o silero_vad.onnx https://github.com/snakers4/silero-vad/raw/v5.1.2/src/silero_vad/data/silero_vad.onnx
sha1sum ggml-*.bin   # tiny.en c78c86eb..., base.en 137c4040... (whisper.cpp's published hashes)
cd .. && venv/bin/kokoro-pi build --models models/kokoro-pi   # TTS: downloads + builds, ~4 min on the Pi 5
```

`orchestrate.py` needs a live `ANTHROPIC_API_KEY` (or an `ant auth login`
profile). Tests live in `tests/`, indexed with run instructions in
`docs/tests.md`.

## What this project is

An animatronic parrot ("Captain Jack") — an existing 3D-printed, servo-driven
bird — getting a Raspberry Pi 5 "brain" added for interactive voice
conversation, replacing an Arduino-only setup. Full context, hardware specs,
and rationale for every decision below live in
`docs/parrot-project-brief.md` — read it before starting implementation work,
it's the canonical source and more detailed than this summary.

## Architecture: two separate personas, two separate stacks

**Jarvis** (primary desktop assistant, not this repo's code, mentioned for
context) runs on Claude Code + backtalk voice bridge + full ai-memory-vault,
billed on the flat Pro plan.

**Captain Jack** (what actually gets built here) is a deliberately lighter,
separate stack:
- Direct Claude **API** calls (Haiku model), not Claude Code — a small, fixed
  tool schema for home-automation intents only, no open-ended tool access.
- Memory is plain markdown files (identity/boot doc + running log), same
  pattern as ai-memory-vault but with a much simpler save/skip ruleset suited
  to a lighter model.
- **File I/O for memory must live in orchestration code, not be delegated to
  the model as autonomous tool calls.** Each turn: orchestration code reads
  memory and injects it into the system prompt; Haiku responds; orchestration
  code (not the model) decides what to append, in a fixed format.
- Local, zero-marginal-cost wake-word spotting, STT (e.g. local Whisper), and
  TTS on the Pi — only the language-model turn itself goes over the network.

## Hardware/software split

- **Arduino**: shrinks to real-time servo execution only (head pitch/roll/yaw,
  beak position) via a one-directional serial protocol from the Pi —
  single-letter commands with variable-length integers, no
  `HEAD`/`BEAK`/`GESTURE` keywords: `p`/`r`/`y` stage head targets and
  `t` the move time, `s` starts the eased move, and `b<BB>` sets the beak
  immediately (never eased, per issue 8). See `docs/specification.md`
  section 4.13 for ranges and offsets. No
  sensor input, no audio hardware, and no autonomous behavior of its
  own — gestures are composed and stored on the Pi, sent down as the
  same primitive commands (**decided 2026-09-14**, see
  `docs/specification.md` Open Issues issue 7); the Arduino never sees a
  `GESTURE <id>`. If the Pi is down, the Arduino does nothing and Jack is
  motionless — accepted behavior.
- **Pi 5**: owns all "intelligence" — one Python process with a thread per
  shared resource (mic capture, playback + beak-sync, serial port, etc.;
  see `docs/specification.md` section 4.16) — runs the orchestration, reads
  direction-of-arrival from the reSpeaker (`xvf_host AEC_AZIMUTH_VALUES`),
  extracts a real-time RMS amplitude envelope from whatever audio is
  currently playing (idle clips or live TTS) at ~30-50Hz to drive beak-sync —
  one code path for both cases, replacing the old MY1690 dual-channel-clip
  trick.
- **Audio I/O**: Seeed reSpeaker XVF3800 (4-mic array, onboard AEC) — the
  bird's speaker must be wired directly to the XVF3800's own output, not a
  separate sound card, or its AEC has no reference signal to cancel against.

## Decisions already made — don't re-litigate without new information

See `docs/parrot-project-brief.md`'s "Decisions already made" section —
the single canonical list (trust model, two separate birds, removed
electret mics/MY1690, speaker-ID deferral, conversational-privacy stance,
automation-authoring scope, cost/billing approach). Don't re-litigate any
of it without new information.

## Done so far

Full narrative (dates, root-causing, specific numbers) for every item
below is in `docs/log.md`'s "CLAUDE.md History" section.

1. Memory scaffold + save/skip ruleset — `memory/identity.md` +
   `memory/memory.md`, design + ruleset in
   `docs/captain-jack-memory-design.md`.
2. Orchestration script's conversation loop — `orchestrate.py` has the
   system-prompt/memory-loading and Haiku call/response loop (text-only,
   no tools yet), live-tested end to end against the real API.
3. Home-automation intent allowlist — `docs/home-automation-allowlist.md`,
   one section per device category against the real device inventory, with
   bounded actions and per-vendor bridge status. Not yet wired to any tool
   schema or vendor API.
4. `arduino-cli` toolchain (compile + upload) confirmed working end-to-end
   against a real Arduino Uno.
5. Arduino wired to all four servos (head pitch/roll/yaw + beak);
   `ServoControl.ino` drives them correctly. Beak uses plain `Servo`, not
   `ServoEasing`. See `docs/specification.md` Open Issues issue 21
   (resolved) and section 4.14.
6. reSpeaker XVF3800 received and USB-connected to the Pi — not yet
   mounted to the statue. Idle/ambient `.wav` clips are in `wavFiles/`
   (19 as of 2026-09-25, all converted to 16kHz/16-bit), including
   `AlignmentTone.wav` for later beak-sync timing calibration.
7. `exercise_hardware.py` — a standalone hardware test harness (not part
   of the real orchestration/state machine) driving `gesture-catalog.yaml`'s
   Off Watch/Asleep ambient/excursion behavior. `--dry-run` runs the same
   logic without a serial port. `read_doa_azimuth()` is a stub (always
   `None`) — wiring in a real DoA reading later is additive, not a
   rewrite.
8. The "discrete steps" visible on small/slow gestures (e.g.
   `id-idle-breathing`) were root-caused to servo PWM resolution, not an
   easing bug — see `docs/specification.md` Open Issues issue 25.
   `id-idle-breathing` has been retuned and confirmed smooth on the real
   bird; other single-digit-degree/multi-second gestures haven't been yet.
9. Audio-pipeline engine choices: wake word (openWakeWord, custom-phrase
   training), STT (Whisper via `whisper.cpp` + Silero VAD for utterance
   end-pointing; tiny vs. base model size still open pending on-device
   experimentation; no local-LLM cleanup stage), and speaker recognition
   (ECAPA-TDNN speaker embeddings for tier-1 voice ID) — all design
   decisions, not yet implemented. See `docs/specification.md` sections
   4.1/4.2/4.15 and Open Issues 1/16.
10. Verified the connected XVF3800's actual playback/capture format via
    ALSA `hw_params` (not just vendor docs): fixed at `S16_LE`, 16kHz, 2
    channels on both directions — the board is running Seeed's 16kHz
    "standard" firmware, not the 48kHz Home-Assistant variant. Locked in
    16kHz/16-bit/S16_LE/2ch as the canonical Pi-side audio-output format
    for TTS and idle clips; corrected a spec typo along the way (existing
    `wavFiles/` clips are actually 44100Hz, not the previously-documented
    41000Hz). See `docs/specification.md` sections 3.2/4.7/4.8/4.10.
11. Decided the wake/sleep-phrase confidence-threshold methodology
    (per-phrase thresholds, openWakeWord's 0.5 default as the starting
    point, wake phrase biased stricter than sleep) without picking actual
    numbers — those still need real audio to calibrate against. See
    `docs/specification.md` section 4.1.
12. Decided STT's confidence/no-speech threshold methodology the same
    way: whisper.cpp already exposes `no_speech_thold`/`logprob_thold`/
    `entropy_thold` natively (OpenAI's reference defaults), biased
    stricter same as 4.1, with rejects needing an in-character prompt
    rather than silence during On Watch. Numbers deferred to the same
    real-audio testing. See `docs/specification.md` section 4.2.
13. Decided speaker-ID's enrollment flow: a standalone script (not an
    in-conversation flow), closed to existing household names only, ~5
    utterances averaged into one embedding per person (research-backed —
    EER drops from ~17.6% at one utterance to ~8% at five-plus), stored
    separately from `memory.md` (embeddings are opaque vectors, not
    hand-editable text). Runtime match-confidence threshold intentionally
    left undecided. See `docs/specification.md` section 4.15.
14. Speaker wired to the XVF3800's output (2026-09-25) and playback
    verified by ear: Pi → USB → XVF3800 → speaker works at the fixed
    16kHz/S16_LE/2ch format. At ALSA volume max (60/60), clips play
    clean at −10dBFS but crackle by −6dBFS and turn to static near
    0dBFS — see `docs/specification.md` Open Issues issue 26. Test
    scripts: `tests/test_speaker_level_ladder.py` (listening) and
    `tests/test_wavfiles_format.py` (see `docs/tests.md`). Interim fix
    until then: playback applies a fixed −10dB gain (ladder step 2) with
    hardware volume at max.
15. End-to-end runtime design (2026-09-25): one Python process, one
    thread per shared resource, turn-taking (no barge-in), and
    sentence-by-sentence TTS, with a keyboard stand-in for the wake word
    until the custom models are trained. Includes a 7-step build order.
    See `docs/specification.md` section 4.16.
16. Build step 1 done (2026-09-25): `playback.py`, the Playback thread —
    queued mono clips played gapless through the XVF3800 with the −10dB
    cap and mono→2ch duplication, with started/finished events timed to
    when sound actually leaves the speaker. Verified by ear
    (`tests/test_playback.py --listen`).
17. Build step 2 done (2026-09-25): `capture.py`, the Capture thread —
    continuous 80ms mono frames from the XVF3800's capture channel 1
    (channel 0 is AGC-clipped and noise-gated). Runs alongside
    `playback.py` on the same board with a shared stream clock.
18. Build step 3 done (2026-09-25): `listener.py` (Silero VAD
    end-pointing, turn-taking gate) + `stt.py` (whisper.cpp via
    `pywhispercpp`, window sized per utterance). Live test: 5 utterances
    transcribed, 2 word errors; tiny.en provisionally chosen over
    base.en (same accuracy on this sample, 2.5-3.5x faster).
19. Build step 4 done (2026-09-25): `coordinator.py` — Enter (wake
    stand-in) → beep → speech → Whisper (with household-name spelling
    hint) → `take_turn()` → printed reply, with a 2-minute On Watch
    timeout. Tested with a fake Haiku client and on five recorded
    utterances against the real API, on scratch memory.
20. Build step 5 done (2026-09-25): `tts.py` (kokoro-pi, voice
    `am_santa` chosen by Chip from an audition) — the first live voice
    conversations with Jack. `identity.md` gained a "Speaking aloud"
    section (short replies, no markdown or stage directions). Live runs
    exposed Whisper retry stalls (20s) and gibberish turned into words;
    `stt.py` now skips retries and rejects repetition and very low
    confidence (all three gibberish samples caught, no real speech).

## Work list — split by hardware dependency

Everything below "doable now" needs nothing that isn't already on hand —
including the smart-home devices themselves, which already exist and are
controllable today. Everything under "blocked" specifically needs the
XVF3800 physically mounted to the statue (the board and its speaker are
both on hand and working, just not mounted).

### Doable now

Everything below is hardware-unblocked, but items 1/2/4 (home-automation)
are being deliberately sequenced *after* items 3/6/7/9 (the core audio
conversation loop) — Chip's own priority call, not a technical
dependency between them. Nothing here stops home-automation from being
worked in parallel if priorities change.

1. Wire orchestrate.py's tool calls for the vendors with known APIs (Govee,
   Tuya/SmartLife, ecobee, Rachio) per the allowlist, and test live against
   the real devices — none of this touches the parrot's own audio hardware.
2. Research Minoston's actual integration path (direct API vs. needs a
   hub) — the one bridge status the allowlist doc flags as genuinely
   unknown.
3. Build speaker-ID: engine (ECAPA-TDNN) and enrollment flow (standalone
   script, ~5 utterances averaged, closed to existing household names,
   embeddings stored separately from `memory.md`) are both designed —
   see `docs/specification.md` section 4.15. Runtime match-confidence
   threshold still needs deciding (methodology, not numbers, matching
   4.1/4.2's treatment). No hardware wait needed: the XVF3800's mic array
   is already electrically functional even though unmounted, so
   prototype against it directly rather than a stand-in mic. Real
   accuracy still needs its physical mounting and the scheduled XVF3800
   test (see Open Issues issue 1).
4. Flesh out the vendor-executed automation-authoring idea (the "lights off
   at midnight" case from the brief's deferred decision) as a small design
   spec — doesn't need new hardware either.
5. More conversational/memory test vectors as they come up — continuing the
   joke/automation/NONE-case testing from this session.
6. Start on the mic/DoA-only half of the stack —
   wake-word/STT/speaker-ID groundwork (engines now chosen: openWakeWord;
   Whisper via `whisper.cpp` + Silero VAD; ECAPA-TDNN — see
   `docs/specification.md` sections 4.1/4.2/4.15). Includes collecting
   real positive/negative audio to calibrate the wake/sleep phrase
   confidence thresholds and STT's no_speech/logprob/entropy thresholds
   (methodology decided for both, see sections 4.1/4.2 — actual numbers
   for both still pending this testing).
7. Track down Seeed's official XVF3800 control tool/protocol docs — no
   `xvf_host` tool or equivalent exists on this Pi (not found via
   `apt`/`pip`/filesystem search), and reading `AEC_AZIMUTH_VALUES` over
   the exposed USB-HID (`/dev/hidraw0`) or vendor-specific USB interface
   needs Seeed's real reference application, not reverse-engineering.
8. Resolve output headroom (Open Issues issue 26): the onboard
   amp/speaker clips above roughly −10dBFS even with ALSA volume at max,
   and −10dBFS may be too quiet in a real room. Decide the mechanism
   (fixed digital gain cap in the shared playback step, a limiter, an
   XVF3800-side output-gain setting if Seeed's tool exposes one — ties to
   item 7 — or an external amp) before picking numbers.
9. **Build the audio loop per `docs/specification.md` section 4.16's
   build order** — the current focus. Steps 1-5 are done: the thin
   end-to-end voice loop works (`coordinator.py`). Next is step 6
   (beak-sync, section 4.8), then step 7 (motion/idle thread, section
   4.10, the state machine, and real wake-word models). Open refinements
   from the live runs: replies still often 25-45 words against a
   20-word target; stream Haiku's reply into TTS to cut the 2.6-3.8s
   delay; pass low-confidence transcripts to Haiku marked unclear (see
   spec 4.2).
10. Train the two custom openWakeWord models ("Ahoy, Captain Jack",
    "Goodnight, Jack") — needs a GPU (e.g. openWakeWord's Colab training
    notebook), not the Pi. Not a blocker: build step 4 uses a keyboard
    stand-in.
11. Optional: TTS engine bake-off — Supertonic-3 against the `kokoro-pi`
    now in place (see `docs/specification.md` section 4.7 and Open Issues
    issue 16), judged primarily on voice quality with real-time
    throughput as a secondary check. Best done after item 8, so clipping
    doesn't muddy the voice comparison.
12. First-pass AEC check against the bird's own speaker — possible now
    with the board unmounted, but the geometry (speaker-to-mic distance)
    will change once mounted, so this is a smoke test, not the final
    validation.

### Blocked until the XVF3800 is mounted to the statue

1. Final AEC validation against the bird's own speaker in its real
   mounted geometry.
2. Speaker-ID accuracy validation against real household voices — needs
   the real mounted acoustics and AEC-cleaned audio (see Open Issues
   issue 1).
