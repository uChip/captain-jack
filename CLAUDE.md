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
The Pi<->Arduino serial link's command syntax is locked down and
implemented (`arduino/ServoControl/ServoControl.ino`, see
`docs/specification.md` section 4.13); the Arduino drives all four servos
(head pitch/roll/yaw + beak) correctly from real commands. The reSpeaker
XVF3800 is electrically connected to the Pi via USB and functional
(untested), but isn't mounted to the statue yet and has no speaker wired
(2-pin JST connector on order, ETA ~2026-09-27) — so wake-word/DoA/STT/
speaker-ID work can all start now against its real mic array, but audio
output and AEC validation can't yet. No home-automation tool calling yet
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
venv/bin/pip install -r requirements.txt  # anthropic SDK, already installed in venv/
ANTHROPIC_API_KEY=... venv/bin/python orchestrate.py
```

Needs a live `ANTHROPIC_API_KEY` (or an `ant auth login` profile) — not
present in the dev environment this was built in, so the live API call path
is untested end-to-end. The memory read/parse/validate/save/dedup logic
*is* verified (offline, against a scratch copy of `memory.md`, not the real
one — no test suite committed to the repo yet).

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
  two compact, fixed-width line shapes, no `HEAD`/`BEAK`/`GESTURE`
  keywords: `p<PP>r<RR>y<YYY>t<TTTT>` for head motion (always all three
  axes + time-to-reach, eased on the Arduino) and `b<BB>` for beak
  position (no time field — never eased, per issue 8). Reconciled
  2026-09-14, see `docs/specification.md` section 4.13 / Open Issues
  issue 9 — exact per-axis offsets/ranges and timing math still TBD. No
  sensor input, no audio hardware, and no autonomous behavior of its
  own — gestures are composed and stored on the Pi, sent down as the
  same primitive commands (**decided 2026-09-14**, see
  `docs/specification.md` Open Issues issue 7); the Arduino never sees a
  `GESTURE <id>`. If the Pi is down, the Arduino does nothing and Jack is
  motionless — accepted behavior.
- **Pi 5**: owns all "intelligence" — runs the orchestration script, reads
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
   mounted to the statue or wired to a speaker (2-pin JST connector on
   order, ETA ~2026-09-27). A first batch of idle/ambient `.wav` clips is
   in `wavFiles/`, including `AlignmentTone.wav` for later beak-sync
   timing calibration.
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

## Work list — split by hardware dependency

Everything below "doable now" needs nothing that isn't already on hand —
including the smart-home devices themselves, which already exist and are
controllable today. Everything under "blocked" specifically needs the
XVF3800's speaker, still on order (the board itself already arrived and
is USB-connected).

### Doable now

Everything below is hardware-unblocked, but items 1/2/4 (home-automation)
are being deliberately sequenced *after* items 3/6/7 (the core audio
conversation loop) — Chip's own priority call, not a technical
dependency between them. Nothing here stops home-automation from being
worked in parallel if priorities change.

1. Wire orchestrate.py's tool calls for the vendors with known APIs (Govee,
   Tuya/SmartLife, ecobee, Rachio) per the allowlist, and test live against
   the real devices — none of this touches the parrot's own audio hardware.
2. Research Minoston's actual integration path (direct API vs. needs a
   hub) — the one bridge status the allowlist doc flags as genuinely
   unknown.
3. Prototype speaker-ID code (voice-embedding model + enrollment flow) —
   engine chosen (ECAPA-TDNN speaker embeddings, see
   `docs/specification.md` section 4.15). No hardware wait needed: the
   XVF3800's mic array is already electrically functional even though
   unmounted, so prototype against it directly rather than a stand-in
   mic. Real accuracy still needs its physical mounting and the scheduled
   XVF3800 test (see Open Issues issue 1).
4. Flesh out the vendor-executed automation-authoring idea (the "lights off
   at midnight" case from the brief's deferred decision) as a small design
   spec — doesn't need new hardware either.
5. More conversational/memory test vectors as they come up — continuing the
   joke/automation/NONE-case testing from this session.
6. With the reSpeaker USB-connected to the Pi (even unmounted and without
   a speaker), start on the mic/DoA-only half of the stack —
   wake-word/STT/speaker-ID groundwork (engines now chosen: openWakeWord;
   Whisper via `whisper.cpp` + Silero VAD; ECAPA-TDNN — see
   `docs/specification.md` sections 4.1/4.2/4.15). Audio *output* (TTS,
   idle clips, beak-sync, AEC validation) still needs the speaker wired —
   see "Blocked" below.
7. Track down Seeed's official XVF3800 control tool/protocol docs — no
   `xvf_host` tool or equivalent exists on this Pi (not found via
   `apt`/`pip`/filesystem search), and reading `AEC_AZIMUTH_VALUES` over
   the exposed USB-HID (`/dev/hidraw0`) or vendor-specific USB interface
   needs Seeed's real reference application, not reverse-engineering.
8. Batch-convert the existing `wavFiles/` clips from 44100Hz down to the
   canonical 16kHz/16-bit/S16_LE output format (see
   `docs/specification.md` sections 4.7/4.10) — a one-time resampling
   pass, doesn't need the speaker wired.

### Blocked until the XVF3800's speaker is wired

Blocked on the speaker being wired (2-pin JST connector on order, ETA
~2026-09-27) and on mounting the board to the statue:

1. Validate AEC quality against the bird's own speaker — can't test
   self-echo cancellation without the speaker wired.
2. Real-time RMS beak-sync extraction from live audio playback/TTS through
   the reSpeaker's output — needs the speaker wired.
3. End-to-end wake-word → STT → Haiku → TTS → beak-sync → Arduino loop,
   tested for real — needs the speaker wired for the TTS/beak-sync half.
4. Speaker-ID accuracy validation against real household voices — a
   stand-in mic won't fairly test what the AEC-cleaned audio actually buys;
   AEC itself needs the speaker wired first.
5. Idle/ambient audio playback tuning through the reSpeaker's own output —
   needs the speaker wired.
6. TTS engine bake-off — `kokoro-pi` vs. Supertonic-3 on the real Pi
   hardware (see `docs/specification.md` section 4.7 and Open Issues
   issue 16), judged primarily on voice quality (the deciding factor per
   Chip's call) with real-time throughput as a secondary check; needs the
   speaker wired to actually listen to the output.
