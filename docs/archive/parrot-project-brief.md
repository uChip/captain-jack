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
    skewed so the beak syncs to the pre-recorded audio. (Slated for removal — see
    "Planned hardware upgrade" below.)
  - Two electret microphones on ADC inputs, used for crude sound-direction
    triangulation so the head turns toward a sound. (Slated for removal — see
    "Planned hardware upgrade" below.)
  - Head gestures are predefined in Arduino memory and play more or less randomly.

## Planned hardware upgrade

- Add a Raspberry Pi 5 as the "brain," with an audio I/O board, so the bird can hold
  an interactive spoken conversation.
- Audio in: **Seeed reSpeaker XVF3800** USB 4-mic array (newer-gen XMOS XVF3800
  chip; onboard AEC, multi-beamforming, de-reverberation, direction-of-arrival,
  dynamic noise suppression) — on order. Chosen over the ReSpeaker Lite (XU316,
  2-mic) and the older 2-Mic HAT (WM8960, no onboard AEC, GPIO HAT) specifically
  because the bird talks through its own speaker inches from its own mics; the
  XVF3800's newer-generation AEC and 4-mic beamforming is the most robust answer
  to that self-echo problem, at roughly 2x the Lite's cost and a larger footprint
  to fit inside the bird body.
- Audio out: speaker wired directly to the XVF3800's own output (its 5W-amp
  speaker terminal or 3.5mm jack) — **not** a separate board such as the Waveshare
  WM8960 Audio HAT (considered, rejected). The XVF3800's AEC uses its own playback
  stream as the echo-cancellation reference signal; routing the bird's speaker
  through a different sound card would give the AEC nothing to cancel against and
  defeat the reason the board was chosen. The XVF3800's onboard amp is reportedly
  mediocre — acceptable for now, with room to add an external amp fed from its
  output later if voice quality needs it.
- Electret mics + Arduino sound-triangulation: **removed**. The XVF3800 exposes
  direction-of-arrival straight to the Pi over USB (`xvf_host AEC_AZIMUTH_VALUES`,
  per-beam azimuth in degrees), so the Pi reads sound direction from the mic array
  itself instead of from Arduino-relayed electret-mic ADC readings. Arduino no
  longer needs any mic input.
- MY1690 idle-sound player: **removed**. Idle/ambient sounds become local audio
  files played by Pi-side code through the XVF3800's output, using the same
  real-time RMS-envelope extraction built for live TTS beak-sync (below) — one
  code path drives the beak for both idle clips and live speech, instead of a
  separate pre-encoded dual-channel format on a second piece of hardware.
  Tradeoff worth remembering: idle sounds now depend on the Pi being up, where the
  MY1690-on-Arduino design let ambient noise run independent of Pi health. Not a
  blocker, but revisit if a flaky Pi ever makes "the bird goes completely silent
  when it reboots" a real annoyance.
- Arduino's role shrinks to real-time servo execution only — head position, beak
  position, and canned gestures, all commanded from the Pi. It no longer owns any
  sensor input or audio hardware, and this loop should stay on the Arduino, not
  the Pi, so it stays fast and doesn't depend on the Pi's scheduling/serial
  round-trip.
- The MY1690's beak-sync trick (dual-channel clips) only worked for pre-rendered
  audio; it's replaced entirely by the RMS-envelope approach above — extracted
  from whatever the Pi is currently playing (idle clip or live TTS) and streamed
  to the Arduino at ~30–50Hz as the beak-position value.
- Simple Pi→Arduino serial protocol (exact framing still TBD), now one-directional
  since Arduino no longer relays mic data upstream:
  `HEAD p:<pitch> r:<roll> y:<yaw>`, `BEAK <0–255>`, `GESTURE <id>`.

## Software architecture: Captain Jack's stack

Jarvis (the primary desktop assistant) is now a separate project on
separate hardware — see the "two birds" decision below. Its implementation
details have moved to `docs/jarvis-handoff-notes.md` rather than living in
this brief; the cost/billing considerations that still cross-cut both
projects (same Anthropic account) stay in "Decisions already made" below.

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
- **Two physically separate birds** (one per persona), not one dual-persona
  bird — decided 2026-09-11. Jarvis is accordingly a separate project on
  separate hardware; its implementation details have moved to
  `docs/jarvis-handoff-notes.md`, out of this brief.
- **Speaker ID for Captain Jack**: deferred, not rejected. Considered while
  designing his memory model (per-person preferences like dad-joke tolerance
  surfaced the question). Hardware supports it — a Pi-side voice-embedding
  model (e.g. ECAPA-TDNN-style, one-time per-person enrollment) run against
  the XVF3800's AEC-cleaned audio, compared to per-user wake words which
  don't scale to guests/kids. If added, it should be a soft personalization
  signal only ("probably Kath, dial back the dad jokes"), not a security
  gate — that would reopen the Alexa-like trust decision above, which stays
  as-is. Nothing in the current memory design (`memory/memory.md`'s
  per-person grouping) blocks adding this later.
- **Conversational privacy (oversharing risk)**: noted, not addressed.
  Jack's action boundary (tools limited to the home-automation allowlist)
  doesn't limit what he can *say* — he has no sense of who's in the room,
  so a fact told to him by one household member could surface in front of
  a guest or another family member at an inconvenient moment. The memory
  category allowlist already keeps most genuinely sensitive info (health
  specifics, financial details) out of storage by construction, but
  doesn't stop innocuous-seeming facts from being repeated at the wrong
  time. Explicitly low-priority for now — revisit only if it becomes a
  real annoyance in practice; the household applying the same "assume it
  repeats things" norm people already use with smart speakers may be
  enough without any technical fix.
- **Automation/rules authoring (not just firing existing scenes)**:
  deferred, not rejected. Surfaced while defining the home-automation
  allowlist (`docs/home-automation-allowlist.md`) via two test cases: "turn
  all lights off at midnight" (a schedule) and "if you hear me call in the
  dark, turn on a light" (a Jack-sensed condition). These are different
  problems and shouldn't be conflated into one "can Jack create
  automations" question:
  - **Jack-authored, vendor-executed** (the midnight-lights case): Jack
    doesn't need to run this himself. If a vendor's API supports creating a
    schedule/automation (not just flipping device state), Jack pushing a
    rule to the vendor on request is still worth doing even though the
    vendor app could technically do it — these apps are frequently not
    user-friendly, so a natural-language front end for authoring is a real
    win on its own. Lower engineering cost than it first looks: execution
    stays vendor-side, Jack only needs a one-shot "create this rule" API
    call at authoring time, no new always-on component in Jack's own stack.
  - **Jack-sensed, Jack-executed** (the call-in-the-dark case): can't be
    delegated to any vendor — only Jack's own mic/wake-word pipeline can
    sense that trigger. This needs a persistent background loop inside
    Jack's own stack, running independent of any conversation, plus a real
    decision about autonomy (Jack silently acting with nobody in a
    conversation is a bigger step than anything built so far, including the
    model-proposes/code-decides caution already applied to memory writes).
  Neither is in the current allowlist, which only covers firing
  already-existing scenes and direct device state changes. If pursued,
  each needs its own bounded-allowlist pass — the same "write it down
  before implementing" treatment the current allowlist got — not a
  blanket "Jack can create automations" grant.
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
   with the home-automation tool schema, extracts a real-time RMS amplitude
   envelope from whatever audio is playing (idle clips or live TTS) for beak-sync,
   reads direction-of-arrival from the reSpeaker for head-turn cues, plays local
   idle/ambient audio files through the reSpeaker output, and manages the
   Pi→Arduino serial link.
3. Define the home-automation intent allowlist explicitly before wiring up tool
   calls for it.
4. Once the reSpeaker XVF3800 arrives: confirm AEC quality against the bird's own
   speaker live, and validate reading DoA (`xvf_host AEC_AZIMUTH_VALUES`) from
   Pi-side code.
