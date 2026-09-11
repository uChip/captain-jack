# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

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
- One bird (dual-persona) vs. two physically separate birds is an open,
  deliberately deferred decision — doesn't block software design either way.
- Electret mics + Arduino-side sound triangulation, and the MY1690 audio
  player, are both removed — superseded by the reSpeaker's onboard DoA and
  Pi-side idle-clip playback, respectively.

## Suggested next steps (from the brief, still open)

1. Scaffold Captain Jack's memory files (identity/boot doc + log format) and
   write the explicit save/skip ruleset. **Done** — `memory/identity.md` +
   `memory/memory.md`, design + ruleset in
   `docs/captain-jack-memory-design.md`. Not yet implemented in code (that's
   next-step #2, below).
2. Write the orchestration script (Python) covering: system prompt + memory
   loading, Haiku API calls with the home-automation tool schema, RMS
   beak-sync extraction, reSpeaker DoA reads, idle-audio playback, and the
   Pi→Arduino serial link. **Partly done** — `orchestrate.py` has the
   system-prompt/memory-loading and Haiku call/response loop (text-only,
   no tools yet). Tool schema, RMS extraction, DoA, idle-audio, and serial
   link are still open — each blocked on something not yet available
   (allowlist undefined, hardware not arrived, serial framing TBD).
3. Define the home-automation intent allowlist explicitly before wiring up
   any tool calls for it. **Done** —
   `docs/home-automation-allowlist.md`, one section per device category
   (lights, fans, outlets, thermostat, irrigation, scenes) against the real
   device inventory (ecobee/Govee/SmartLife/Minoston/Rachio/Reolink), each
   with bounded actions and per-vendor bridge status. Locks excluded (no
   hardware); cameras excluded (no display + security-bypass risk). Not yet
   wired to any tool schema or vendor API — that's still open, and several
   vendor bridges (Minoston in particular) need API research before they can
   be.
4. Once the XVF3800 arrives: validate AEC quality against the bird's own
   speaker, and validate reading DoA from Pi-side code.
