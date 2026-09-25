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
    `tests/test_wavfiles_format.py` (see `docs/tests.md`).

## Work list — split by hardware dependency

Everything below "doable now" needs nothing that isn't already on hand —
including the smart-home devices themselves, which already exist and are
controllable today. Everything under "blocked" specifically needs the
XVF3800 physically mounted to the statue (the board and its speaker are
both on hand and working, just not mounted).

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
9. Real-time RMS beak-sync extraction from live audio playback/TTS
    through the reSpeaker's output (section 4.8).
10. Idle/ambient audio playback through the reSpeaker's own output
    (section 4.10), including the shared mono→2ch duplication step.
11. TTS engine bake-off — `kokoro-pi` vs. Supertonic-3 on the real Pi
    hardware (see `docs/specification.md` section 4.7 and Open Issues
    issue 16), judged primarily on voice quality (the deciding factor per
    Chip's call) with real-time throughput as a secondary check. Best
    done after item 8, so clipping doesn't muddy the voice comparison.
12. End-to-end wake-word → STT → Haiku → TTS → beak-sync → Arduino loop,
    tested for real.
13. First-pass AEC check against the bird's own speaker — possible now
    with the board unmounted, but the geometry (speaker-to-mic distance)
    will change once mounted, so this is a smoke test, not the final
    validation.

### Blocked until the XVF3800 is mounted to the statue

1. Final AEC validation against the bird's own speaker in its real
   mounted geometry.
2. Speaker-ID accuracy validation against real household voices — needs
   the real mounted acoustics and AEC-cleaned audio (see Open Issues
   issue 1).
