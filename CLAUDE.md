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
No audio I/O, reSpeaker DoA, or Pi<->Arduino serial link yet — those need
hardware that hasn't arrived and specs that aren't written (serial framing
still TBD, see the brief). No home-automation tool calling yet either — the
intent allowlist (next-step below) isn't defined.

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
  beak position, canned gestures) via a one-directional serial protocol from
  the Pi (`HEAD p:<pitch> r:<roll> y:<yaw>`, `BEAK <0-255>`, `GESTURE <id>`;
  exact framing still TBD). No sensor input, no audio hardware.
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

- Trust model is deliberately Alexa-like: no voice-ID firewall between
  household members; Captain Jack's capabilities are bounded by a small
  explicit intent allowlist instead of a security/mode-switching layer.
- **Two physically separate birds** (one per persona) — decided. Jarvis is
  a separate project on separate hardware; its implementation details live
  in `docs/jarvis-handoff-notes.md`, not tracked in this repo.
- Electret mics + Arduino-side sound triangulation, and the MY1690 audio
  player, are both removed — superseded by the reSpeaker's onboard DoA and
  Pi-side idle-clip playback, respectively.

## Done so far

1. Memory scaffold + save/skip ruleset — `memory/identity.md` +
   `memory/memory.md`, design + ruleset in
   `docs/captain-jack-memory-design.md`.
2. Orchestration script's conversation loop — `orchestrate.py` has the
   system-prompt/memory-loading and Haiku call/response loop (text-only,
   no tools yet), live-tested end to end including several bugs found and
   fixed (see git log).
3. Home-automation intent allowlist — `docs/home-automation-allowlist.md`,
   one section per device category against the real device inventory, with
   bounded actions and per-vendor bridge status. Not yet wired to any tool
   schema or vendor API.

## Work list — split by hardware dependency

Everything below "doable now" needs nothing that isn't already on hand —
including the smart-home devices themselves, which already exist and are
controllable today. Everything under "blocked" specifically needs the
XVF3800, still on order.

### Doable now

1. Wire orchestrate.py's tool calls for the vendors with known APIs (Govee,
   Tuya/SmartLife, ecobee, Rachio) per the allowlist, and test live against
   the real devices — none of this touches the parrot's own audio hardware.
2. Research Minoston's actual integration path (direct API vs. needs a
   hub) — the one bridge status the allowlist doc flags as genuinely
   unknown.
3. Design the Pi↔Arduino serial protocol precisely — framing is still TBD
   per the brief; pure spec work, no audio board needed.
4. **Confirmed 2026-09-11**: the Arduino is not yet connected to this Pi.
   Before that changes, the old audio hardware (MY1690 + electret mics)
   needs to come out of the existing board, or a new Arduino is used
   instead — Chip's call, still open, and a physical/offline task. The
   sketch also needs rewriting for servo-only control (no more mic/audio
   duties) to match the serial protocol from item 3 above — that part
   doesn't need the physical connection to write, only to test, and Chip
   may hand the sketch itself to a future session rather than write it
   solo.
5. Prototype speaker-ID code (voice-embedding model + enrollment flow)
   against a stand-in mic (the Pi's own, or any USB mic on hand) — validates
   the software approach even though real accuracy needs the XVF3800's
   cleaned audio eventually (see the deferred decision in the brief).
6. Flesh out the vendor-executed automation-authoring idea (the "lights off
   at midnight" case from the brief's deferred decision) as a small design
   spec — doesn't need new hardware either.
7. More conversational/memory test vectors as they come up — continuing the
   joke/automation/NONE-case testing from this session.

### Blocked until the XVF3800 arrives

1. Validate AEC quality against the bird's own speaker — can't test
   self-echo cancellation without the real board.
2. Validate reading DoA (`xvf_host AEC_AZIMUTH_VALUES`) from Pi-side code.
3. Real-time RMS beak-sync extraction from live audio playback/TTS through
   the reSpeaker's output.
4. End-to-end wake-word → STT → Haiku → TTS → beak-sync → Arduino loop,
   tested for real.
5. Speaker-ID accuracy validation against real household voices — a
   stand-in mic won't fairly test what the AEC-cleaned audio actually buys.
6. Idle/ambient audio playback tuning through the reSpeaker's own output.
