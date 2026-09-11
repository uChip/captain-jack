# Animatronic Parrot Project — Handoff Brief

Context for Claude Code: this project was designed in a series of planning conversations
with Claude (chat). Nothing has been built yet — this document captures the decisions
made so far so implementation can start from here instead of from scratch.

## Who's building this

Retired engineer, formally trained in computer systems, career mostly in software
program/technical management. Technical knowledge is somewhat dated; this is a
returning-to-AI hobby project, not income-generating. Cost-conscious in the sense of
wanting to *understand and predict* ongoing/recurring costs, not stick to a hard budget.

## Current physical build (already exists)

- Life-size 3D-printed parrot on a branch. Started as single STL, edited so the head pivots in
  pitch, roll, and yaw; lower beak also moves.
- Head: three 9G servos. Beak: one 2G servo.
- An Arduino-style board controls the servos and currently owns all the "intelligence."
- Peripherals on that board:
  - An MY1690-based audio player. Its SD card holds many short stereo audio clips —
    left channel is the actual audio, right channel encodes a beak-movement level,
    skewed so the beak syncs to the pre-recorded audio.
  - Two electret microphones on ADC inputs, used for crude sound-direction
    triangulation so the head turns toward a sound.
  - Head gestures are predefined in Arduino memory and play more or less randomly.

## Planned hardware upgrade

- Add a Raspberry Pi 5 as the "brain," with an audio I/O board, so the bird can hold
  an interactive spoken conversation.
- Arduino's role shrinks to: real-time servo execution from Pi commands, plus
  relaying the electret-mic triangulation angle upstream. Keep this loop on the
  Arduino, not the Pi — it needs to stay fast and shouldn't depend on the Pi's
  scheduling/serial round-trip.
- Audio board: leaning toward Seeed's **ReSpeaker Lite** (XMOS XU316, onboard
  acoustic echo cancellation + noise suppression, USB). This matters because the
  bird will be talking through its own speaker inches from its own mics — a board
  without real AEC will hear itself. The older ReSpeaker 2-Mic HAT (WM8960) is
  cheaper but is an older GPIO HAT design — verify Pi 5 HAT+ compatibility before
  committing to it instead.
- The MY1690's beak-sync trick (dual-channel clips) only works for pre-rendered
  audio. For live AI-generated speech, extract a real-time amplitude envelope
  (simple RMS over a short window) from the outgoing TTS audio and stream it to the
  Arduino at ~30–50Hz as the beak-position value. Keep the MY1690 + its clip library
  wired to the Arduino as a separate, low-power idle/ambient-sound-effects layer
  that doesn't require waking the AI pipeline.
- Simple Pi→Arduino / Arduino→Pi serial protocol (exact framing still TBD):
  `HEAD p:<pitch> r:<roll> y:<yaw>`, `BEAK <0–255>`, `GESTURE <id>` downstream;
  `MIC_ANGLE <deg>` upstream.

## Software architecture: two personas, separate hardware/stacks

**Jarvis** — the primary desktop assistant.
- Personality: companionable but more formal, "major domo" — butlerish.
- Broad task responsibility and system access (this is the "full agentic" instance).
- Runs on **Claude Code**, voice-bridged using jaredrhod's **backtalk** pattern
  (push-to-talk voice I/O into a live Claude Code session, local STT, real-voice
  TTS output, full tool access preserved).
- Memory: jaredrhod's **ai-memory-vault** ("Jarvis" stack), full install — a folder
  of plain markdown files (`CLAUDE.md` boot/identity doc, profile, daily notes,
  "Jobs") that the agent reads/writes each session.
- Billing: Claude **Pro plan** ($17–20/mo flat), which includes Claude Code.

**Captain Jack** — the parrot's persona.
- Personality: light, humorous social companion, available to the whole household
  (not just the primary user).
- Capabilities: home automation (needs an explicit, deliberately bounded allowlist
  of intents — lights, thermostat, locks, scenes, etc. — write this down explicitly
  before implementing, so the scope doesn't quietly creep toward full-Jarvis
  capability over time) plus "perhaps other limited tasks," still to be scoped.
- Does **not** run Claude Code and does **not** get the full ai-memory-vault. It's a
  lighter, custom, purpose-built stack:
  - Direct Claude **API** calls (model: **Haiku**) with a small, defined tool
    schema for the home-automation intents. No open-ended tool access.
  - Memory: a pared-down, custom setup using the *same plain-markdown pattern* as
    ai-memory-vault (an identity/boot doc + a running conversational log), but with
    a much simpler ruleset than the full vault spec — deliberately, since the full
    vault's nuanced save/skip/dedupe judgment calls were tuned against a more
    capable model. Suggested starting rule: save durable facts about family
    members, running jokes/preferences, and stated home-automation preferences;
    skip everything else.
  - **File I/O should live in your own orchestration code, not be delegated to the
    model as autonomous tool calls.** Each turn: your code reads the relevant
    memory file(s) and injects them into the system prompt; Haiku responds; your
    code (using the model's output, not an autonomous file-write action from the
    model) decides what — if anything — to append, in a fixed format. This is more
    predictable and easier to debug than giving a lightweight model open-ended
    file-write authority.
  - Local (zero marginal cost) wake-word spotting, speech-to-text (e.g. local
    Whisper), and TTS on the Pi 5 — only the actual language-model turn goes over
    the network to the API.

## Decisions already made (don't re-litigate these without new information)

- Trust/security model: deliberately Alexa-like. No voice-ID firewall between
  household members — the home is treated as a trusted environment, same
  assumption behind most smart speakers. This is *why* Captain Jack doesn't need
  a hard mode-switching/security mechanism between "social" and "task" use — his
  capability set is simply bounded by design instead.
- One bird (dual-persona) vs. **two physically separate birds** (one per persona)
  is an open, deliberately deferred decision. It doesn't block designing either
  persona's software — same wake-word/gating logic (if needed at all) works either
  way.
- Cost approach: Jarvis on a flat subscription (predictability matters more than
  minimizing cost for the "always available" piece); Captain Jack on metered
  Haiku API calls (usage is naturally light and cheap — modeled at roughly $1–2/mo
  for three 10-minute conversations a day, though real usage should be checked
  against Anthropic's live billing dashboard rather than trusted as a firm number).
- Jarvis's Pro-plan usage is shared across *all* Claude/Claude Code activity on
  that account — if heavy unrelated desktop coding work happens on the same
  account, it competes with Jarvis-the-parrot-adjacent-assistant's usage for the
  same 5-hour session budget. Worth monitoring via `/status` before assuming Pro
  is sufficient long-term.

## Suggested next steps for Claude Code

1. Scaffold Captain Jack's pared-down memory files (identity/boot doc + log format)
   and write out the explicit, simple save/skip ruleset.
2. Write the orchestration script (Python is a natural fit given the Pi ecosystem)
   that: loads Captain Jack's system prompt + memory context, calls the Haiku API
   with the home-automation tool schema, extracts the TTS amplitude envelope for
   beak-sync, and manages the Pi↔Arduino serial link.
3. Define the home-automation intent allowlist explicitly before wiring up tool
   calls for it.
4. Set up jaredrhod's `ai-memory-vault` + `backtalk` for Jarvis if not already
   running, per the fullstack-agent installer.
5. Pick and test the audio I/O board (ReSpeaker Lite vs. 2-Mic HAT) against the
   Pi 5 specifically.
6. Revisit the one-bird-vs-two-birds hardware question once the software side is
   further along and real constraints (cost, complexity, how it actually feels to
   use) are clearer.
