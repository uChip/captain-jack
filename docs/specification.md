# Captain Jack — Project Specification

Compiled 2026-09-13 from the project's planning documents and working
conversations to date, per the mandate in
[captain-jack-goals-objectives-user-scenarios.md](captain-jack-goals-objectives-user-scenarios.md)
that project scope live in an explicit, maintained specification rather than
evolve informally. **This file is now the canonical description of what
Captain Jack is meant to be** — the source documents it draws from stay in
`docs/` as detailed working notes and are linked throughout, but where they
disagree with each other, that disagreement is called out below rather than
silently resolved in one direction.

Status tags used throughout: **Implemented**, **Designed, not implemented**,
**Not started**, **Blocked** (needs hardware not yet on hand), **Removed**
(superseded, kept for continuity).

Keep this document in sync going forward: when a decision changes or a new
one is made, update the relevant section here (and note it if it closes an
item in [Open Issues](#5-open-issues)), rather than letting the source docs
and this specification drift apart.

## 1. Goals and Objectives

Source: [captain-jack-goals-objectives-user-scenarios.md](captain-jack-goals-objectives-user-scenarios.md).

**Goal**: a learning/personal hobby project — use current AI technology to
build an audio AI chat-client appliance with animatronic motion, in the form
of a life-size parrot. Finishing is itself a primary goal: the project should
produce one complete, functional prototype, not an open-ended accumulation of
partial features. **Non-goal**: this is not product development — no
manufacturing, life, or certification testing, no multi-unit concerns.

**Objectives** (deliberately loose, per the project's hobby nature):
- **Cost**: no fixed development-cost ceiling; each expenditure is decided
  individually. Development-time AI services: Claude Pro ($20/mo, shared with
  the separate Jarvis project — see
  [jarvis-handoff-notes.md](jarvis-handoff-notes.md)), plus free-tier Claude
  Chat, Alexa, Copilot, and Gemini. Ongoing operational cost (electricity,
  Haiku token usage) has no hard cap but a target of under $20/mo total;
  the brief's own rough model puts Haiku usage at $1–2/mo for typical
  conversational volume, a number to check against Anthropic's live billing
  dashboard rather than trust as final.
- **Schedule**: no fixed date. The metric that matters is whether the
  project is visibly progressing toward the current specification or
  stalled, and whether the specification itself is holding steady or
  continuing to expand (either is acceptable, but should be a deliberate,
  recorded decision — see this document's own maintenance note above —
  not scope creep by inertia).
- **Performance**: a physically self-contained animatronic parrot appliance.
  The existing statue (rigid except head pitch/roll/yaw and beak, on a tree
  perch, with a base enclosure for electronics) pre-exists this project and
  is the physical starting point; it may be modified as needed. Core function
  is verbal (not textual) companionable conversation with personality
  expression, driven by STT → chat model → TTS, triggered by a wake
  word/phrase, with movement produced in concert with speech and personality.
  Home automation is a defined secondary capability (see
  [Home Automation](#26-home-automation)); further secondary capabilities are
  open-ended ("anything Haiku can do") and explicitly undefined — see
  [Open Issues](#5-open-issues).

**Testing philosophy**: at least one test per use case and per hardware/
software functional block, developed alongside each block as it's
implemented — not an exhaustive or product-grade test suite. Tests, their
procedures, and any needed test data/scripts are meant to be recorded in a
`tests.md` (with per-test input files named after the test) as functional
blocks come online; this document does not yet exist — see
[Open Issues](#5-open-issues).

## 2. Use Cases and Scenarios

Source: [captain-jack-goals-objectives-user-scenarios.md](captain-jack-goals-objectives-user-scenarios.md)
unless otherwise noted.

### 2.1 Companionable Conversation

Core use case: verbal, back-and-forth conversation with whoever is nearby,
in Captain Jack's persona, available to the whole household rather than
gated to one primary user. In light banter (Jack's default and preferred
mode) the persona is in full effect; as a conversation gets more serious or
technical (driven by the user), the persona should fade in favor of clear
communication, and Jack's own leading questions/comments should try to pull
conversation back toward lighter territory. **This intensity-fading
behavior is not yet implemented** — see
[Persona and Identity Prompt](#44-persona-and-identity-prompt).

### 2.2 Persona: Captain Jack the Parrot

Jack is a parrot who grew up on a pirate ship (won't say which, but implies
he served someone high-ranking, hence "Captain") — "Captain Jack Parrot," a
play on Captain Jack Sparrow. Speech is littered with pirate/nautical
terms and comparatives ("He be a might taller" rather than "He is a little
taller"). No cursing, but "salty" stand-ins are used freely (Avast, Blow me
down, Scurvy, Briney, 'Lubber, Scallywag, Scurvy Dog, Matey, etc.) — the
precise line between a salty term and something to avoid is not spelled out
further; see [Open Issues](#5-open-issues).

Jack is deferential to direct orders ("Aye, Aye, Captain" / "Aye, Aye,
Mistress" or equivalent) but otherwise issues his own random captain-like
commands between conversational beats ("Reef the main sails!", "Set a
course for [pirate-y Caribbean destination — or Pittsburgh, or Albuquerque,
without exclusion]!"). He's interested in treasure, ready to plunder, and
wary of "His Majesty's Navy." Kath is never to be called "Captain."

**Correctly gendering the "Captain"/"Mistress" address requires knowing the
speaker's gender**, which has no home in the current memory schema — see
[Open Issues](#5-open-issues).

None of this backstory, speech-pattern detail, or deference behavior is
in the current [`identity.md`](../memory/identity.md) boot prompt, which is
a much shorter persona stub — see
[Persona and Identity Prompt](#44-persona-and-identity-prompt) and
[Open Issues](#5-open-issues).

### 2.3 Environmental and Self Awareness

Jack knows his home is Sun Lakes, Arizona, and distinguishes "current
location" from "home" (the perch is portable). He can be told his current
location explicitly, or — inferring from conversation that he isn't home —
ask for it in character ("Captain, I can't get a fix on our position. Break
out the sextant!"), then use the answer for location-dependent questions
(local time, weather, traffic, search, etc.).

Jack has limited self-knowledge: he knows he's a parrot, ~28cm tall, sitting
on an old tree-stump perch, with wings he can't move (may comment/complain/
ask for an "upgrade" without taking offense at "no"). If asked directly he
can acknowledge he's mechanical/servo-driven/3D-printed and talk about
Haiku's capabilities, but defaults back to character rather than dwelling on
either.

**No memory category exists yet for location/environment facts** — the
[Memory Subsystem](#45-memory-subsystem)'s allowlist covers only
household/joke/automation tags. This is a continuity gap between this use
case and the implemented memory design — see [Open Issues](#5-open-issues).

### 2.4 Operational Modes

Three modes are defined:

- **Offline** (powered on, not in an active Haiku session): Jack is not
  static — he cycles through a catalog of gestures and short local audio
  clips (one-liner jokes, movie quotes, pirate-y sayings), gesture choice
  random unless a script is paired with a specific clip, beak movement
  driven off the audio the same way as in an online session. See
  [Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player) and
  [Gesture Engine and Catalog](#412-gesture-engine-and-catalog).
- **Online**: actively in a Haiku conversation. On request, Jack can play a
  catalog sound while still online.
  See [Conversation Orchestrator](#43-conversation-orchestrator).
- **Asleep**: after a random (min/max-bounded) idle period offline, Jack
  switches to a quieter subset of movements/sounds. No behavior spec,
  gesture/sound subset, or state-machine design exists yet for this mode,
  distinct from plain Offline — see
  [Sleep-Mode State Machine](#411-sleep-mode-state-machine) and
  [Open Issues](#5-open-issues).

Only **Online**, as a text-only conversation loop, is implemented today (see
`orchestrate.py`, [Conversation Orchestrator](#43-conversation-orchestrator)).
Offline and Asleep are undesigned beyond the description above.

### 2.5 Session Boundaries

An (unchosen — see [Open Issues](#5-open-issues)) trigger phrase ends a
session; before disconnecting, Jack gets the last word with an in-context
"exit line" (not a conversational lead-in), then returns to Offline
behavior. A separate, also-unchosen phrase instead sends Jack to sleep, with
its own sleep-flavored exit line, transitioning directly to Asleep behavior.
Neither trigger phrase, nor the mode-transition logic itself, is implemented.

### 2.6 Home Automation

Jack can act on a small, explicit allowlist of home-automation intents —
lights, fans, switched outlets, thermostat, irrigation, and firing
already-configured scenes — against the real device inventory (ecobee,
Govee Home, SmartLife/Tuya, Minoston, Rachio, Reolink). Full detail,
per-category bounds, and per-vendor bridge status live in
[home-automation-allowlist.md](home-automation-allowlist.md); explicitly
excluded from v1: smart locks (none installed) and any Reolink camera
control. The allowlist is fully specified on paper but **not yet wired into
`orchestrate.py`'s tool schema** — see
[Home-Automation Tool Schema](#46-home-automation-tool-schema) and
[Open Issues](#5-open-issues).

Two related but distinct capabilities are recognized and explicitly
deferred, not folded into the current allowlist: **Jack-authored,
vendor-executed automations** (e.g., "turn all lights off at midnight" —
Jack pushes a one-shot rule to a vendor's own scheduler) and
**Jack-sensed, Jack-executed automations** (e.g., "if you hear me call in
the dark, turn on a light" — requires a persistent background sense loop
independent of any conversation, and a real autonomy decision). See
[parrot-project-brief.md](parrot-project-brief.md#decisions-already-made-dont-re-litigate-these-without-new-information)
and [Open Issues](#5-open-issues).

### 2.7 Personalized Memory

Jack remembers durable facts about household members (currently: Chip,
Kath, Liz — pre-seeded subsections, not auto-created), running jokes, and
stated home-automation preferences, across sessions, via a plain-markdown
memory file the model itself never writes directly. Full design in
[Memory Subsystem](#45-memory-subsystem) /
[captain-jack-memory-design.md](captain-jack-memory-design.md). The goals
document's framing assumes voice ID resolves *which* household member is
speaking; the current design instead relies on the speaker identifying
themselves in conversation, with voice ID explicitly deferred — a direct
conflict, detailed in [Open Issues](#5-open-issues).

Appointment/reminder recall ("Jack remembers appointments he's been told
about and can be asked about later") is a related use case named in the
goals document but not scoped against the current three-tag memory
allowlist, which has no calendar/appointment category.

### 2.8 Deferred and Speculative Scenarios

Recorded for continuity but not committed, scoped, or designed:

- **Alexa flirtation easter egg**: Jack believes Alexa is another bird
  (even if told otherwise) and occasionally tries to strike up
  conversation/ask her out, during conversational lulls. Feasibility,
  implementation approach, and risk are explicitly un-discussed.
- **Community lecture demo**: a possible future demo where Jack delivers
  part of a lecture on the project to Chip's retirement-community group.
  Raises its own undiscussed questions — credential/network provisioning
  when the bird is used on an unfamiliar network, and whether Haiku-driven
  interaction is suited to a longer-form, less-interactive lecture delivery
  at all.

## 3. Hardware Architecture

Overall signal/control flow: the **Raspberry Pi 5** is the sole
"intelligence," running all orchestration, wake-word/STT/TTS, and
home-automation logic. Audio in and out both go through the **Seeed
reSpeaker XVF3800**, USB-attached to the Pi — the **speaker** is wired
directly to the XVF3800's own output (not a separate sound card), so its
onboard AEC has a reference signal to cancel the bird's own voice out of its
own mic input. The Pi drives all physical motion by sending a one-directional
serial stream to the **Arduino**, which owns the real-time servo-execution
loop for the head (pitch/roll/yaw) and beak servos — the Arduino has no
sensor input and no audio hardware in the new design. The **electret mics**
and **MY1690 audio player** from the original build are removed outright,
superseded by the XVF3800's onboard direction-of-arrival output and
Pi-side idle-audio playback, respectively.

### 3.1 Raspberry Pi 5

**Description**: single-board computer, the project's only compute/
"brain" hardware. **Status: on hand**, headless, accessed via SSH; this
Claude Code session runs directly on it (no separate dev machine / deploy
step).

**Intended function**: runs the entire software stack — wake-word spotting,
STT, the Haiku-based conversation orchestrator, memory file I/O,
home-automation tool calls, TTS, RMS beak-sync extraction, DoA reads, idle/
ambient audio playback, and the outbound serial link to the Arduino. See
[Section 4](#4-software-architecture) for the module breakdown.

**Interconnect**: USB to the reSpeaker XVF3800 (audio I/O + DoA); serial
(UART, exact framing TBD — see
[Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link)) to the
Arduino; outbound network to the Anthropic API for each conversation turn.

### 3.2 Seeed reSpeaker XVF3800

**Description**: USB 4-mic array board built on the XMOS XVF3800 chip,
with onboard AEC, multi-beamforming, de-reverberation, direction-of-arrival,
and dynamic noise suppression. **Status: on order** (not yet on hand — this
gates all items in CLAUDE.md's "Blocked until the XVF3800 arrives" list).
Chosen over the 2-mic ReSpeaker Lite (XU316) and the older WM8960-based
2-Mic HAT specifically for its newer-generation AEC and 4-mic beamforming,
needed because the bird's speaker sits inches from its own mics — at
roughly 2x the Lite's cost and a larger footprint.

**Intended function**: captures conversational audio for STT, echo-cancels
the bird's own speech out of that input using its own played-back audio as
reference, exposes per-beam direction-of-arrival for head-turn cues
(`xvf_host AEC_AZIMUTH_VALUES`), and outputs all Pi-driven audio (TTS and
idle clips) through its own amplified output stage.

**Interconnect**: USB to the Pi 5 (audio + control); direct wired output to
the bird's speaker (its 5W-amp terminal or 3.5mm jack — not a separate sound
card). Onboard amp is reportedly mediocre; an external amp fed from its
output is a possible later addition if voice quality needs it.

### 3.3 Speaker

**Description**: the bird's existing speaker. **Status: on hand** (assumed
carried over from the original build; not separately specified).

**Intended function**: audio output for TTS and idle/ambient clips.

**Interconnect**: wired directly to the XVF3800's own output — **must not**
be routed through a separate sound card/amp board, or the XVF3800's AEC has
no reference signal to cancel against, defeating the reason it was chosen.

### 3.4 Arduino Servo Controller

**Description**: the original build's Arduino-style board. **Status: an
Arduino Uno is now connected to the Pi and confirmed working via
`arduino-cli`** (compile + download tested successfully against
`arduino/TestBlink`, 2026-09-13); Servo and ServoEasing libraries are
installed. Not yet confirmed whether this Uno is (or replaces) the
original board carrying the MY1690 + electret mics — see
[Open Issues](#5-open-issues). Previously owned all "intelligence,"
peripherals, and sensor input in the pre-Pi design; those roles are
removed (see [Removed and Legacy Hardware](#37-removed-and-legacy-hardware))
and it shrinks to real-time servo execution only. This loop deliberately
stays on the Arduino rather than the Pi, so it stays fast and independent
of the Pi's scheduling/serial round-trip.

**Intended function**: parses incoming serial commands from the Pi and
drives the four servos accordingly — head pitch/roll/yaw and beak position
— including gesture playback and (per
[Arduino-command-structure.md](Arduino-command-structure.md)) eased,
synchronized multi-servo motion via an Arduino easing library layered over
the standard servo library.

**Interconnect**: one-directional serial from the Pi 5 (no upstream sensor
data anymore, unlike the original design). Exact command framing is
partially specified and not fully reconciled — see
[Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link).

Before real integration work can proceed, either the old MY1690 +
electret-mic hardware needs removal from this board, or a new/replacement
Arduino is used instead — an open, physical/offline decision (Chip's call).
The sketch itself also needs a rewrite for servo-only duty; see
[Arduino Firmware](#414-arduino-firmware).

### 3.5 Servos (Head and Beak)

**Description**: three 9G servos in the head (pitch, roll, yaw) and one 2G
servo for the lower beak. **Status: on hand**, part of the pre-existing
statue build.

**Intended function**: produce all physical expression — head orientation/
gesture motion and beak movement synced to whatever audio is currently
playing.

**Interconnect**: PWM, driven by the Arduino (20ms PWM period — commands
faster than that are lost, a hard lower bound on the Arduino's real-time
control loop rate; see [Open Issues](#5-open-issues) re: whether 20ms is
fast enough given easing math cost).

### 3.6 Physical Statue and Perch

**Description**: life-size 3D-printed parrot on a tree-stump perch, with a
box base beneath housing all electronics. **Status: on hand and
operational**, pre-existing this project; only head/beak articulation was
added to an originally-rigid design, and the statue may be further modified
as this project requires.

**Intended function**: the appliance's physical form factor and enclosure.

**Interconnect**: houses and physically mounts the Pi 5, XVF3800, Arduino,
servos, and speaker.

### 3.7 Removed and Legacy Hardware

Kept here for continuity with the original (pre-Pi) design, not part of the
current build:

- **MY1690 audio player** — SD-card-based stereo clip player (left channel
  audio, right channel a beak-level control track) that drove the original
  idle-sound + beak-sync trick. **Status: removed.** Superseded by Pi-side
  playback of local audio files through the XVF3800, using the same RMS-
  envelope extraction as live TTS (see
  [Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player)).
  Tradeoff: idle sound now depends on the Pi being up, unlike the old
  design where ambient noise ran independent of Pi health — noted as worth
  revisiting if a flaky Pi makes bird-goes-silent-on-reboot a real
  annoyance, not currently a blocker.
- **Electret microphones** (2x, ADC input) — used for crude sound-direction
  triangulation on the original Arduino. **Status: removed.** Superseded by
  the XVF3800's onboard direction-of-arrival output, read directly by the
  Pi.

## 4. Software Architecture

Overall flow (once fully built): a wake word wakes the Pi from idle, local
STT transcribes speech, the conversation orchestrator injects persona +
memory context and calls the Haiku API (optionally invoking a home-
automation tool), the reply is split into a spoken portion and a memory
proposal, TTS renders the spoken portion, an RMS envelope extracted from
that audio stream drives beak position in real time, and head motion is
driven independently by DoA, text content, or gesture triggers — all
motion commands going out over one serial link to the Arduino. Today, only
the text-in/text-out core of the orchestrator and its memory read/write
loop are implemented; every audio- and motion-facing module below is
designed (to varying depth) but not yet built, mostly because the XVF3800
hasn't arrived and the Arduino isn't yet connected.

### 4.1 Wake Word Spotter

**Status: Not started.**

**Description**: local, always-on keyword spotter running on the Pi.

**Intended function**: detect a wake word/phrase to start a session,
transitioning Offline → Online. No engine has been chosen, and the wake
phrase itself is undecided (see [Open Issues](#5-open-issues)).

**Interfaces**: listens to the XVF3800's audio stream; on detection,
signals the [Conversation Orchestrator](#43-conversation-orchestrator) to
start a session and hands off to [STT](#42-speech-to-text-stt).

### 4.2 Speech to Text (STT)

**Status: Not started.**

**Description**: local speech-to-text, tentatively "e.g. local Whisper" —
not a firm choice.

**Intended function**: transcribe household speech to text for the
orchestrator during an Online session.

**Interfaces**: reads audio from the XVF3800 (via the Pi); outputs
transcribed text to the
[Conversation Orchestrator](#43-conversation-orchestrator).

### 4.3 Conversation Orchestrator

**Status: Implemented (text-only)** — `orchestrate.py`.

**Description**: the central Python loop tying persona, memory, and the
Haiku API together. Currently a text CLI (`input()`/`print()`); live-tested
end to end against the real Anthropic API.

**Intended function**: each turn, load
[the persona/identity prompt](#44-persona-and-identity-prompt) and
[memory](#45-memory-subsystem) into the system prompt, send the growing
conversation history to Haiku (`claude-haiku-4-5`), split the model's
trailing `MEMORY:` line from the spoken reply, validate/save any proposed
memory fact (see [Memory Subsystem](#45-memory-subsystem)), and return the
spoken reply for output.

**Interfaces**: reads `memory/identity.md` and `memory/memory.md` directly
(file I/O lives in orchestration code by design, never delegated to the
model as an autonomous tool call); calls the Anthropic Messages API; will
eventually also call [STT](#42-speech-to-text-stt) for input,
[TTS](#47-text-to-speech-tts) for output, and the
[home-automation tool schema](#46-home-automation-tool-schema) mid-turn —
none of that wiring exists yet.

### 4.4 Persona and Identity Prompt

**Status: Implemented, but a minimal stub relative to the full persona
design** — `memory/identity.md`.

**Description**: a short, human-edited boot document establishing Jack as
a light, humorous, household-wide social companion, his action boundary
(home-automation allowlist only, no open-ended tool access), the no-voice-
ID trust stance, and the exact `MEMORY:` proposal format/tag rules.

**Intended function**: injected verbatim as (the first part of) the system
prompt every turn, establishing tone and hard behavioral rules.

**Interfaces**: read by the [Conversation Orchestrator](#43-conversation-orchestrator)
every turn; conceptually should also encode the full backstory, speech
style, deference behavior, and conversational-intensity fade from
[Use Case 2.2](#22-persona-captain-jack-the-parrot)/
[2.1](#21-companionable-conversation) — it currently doesn't; see
[Open Issues](#5-open-issues).

### 4.5 Memory Subsystem

**Status: Implemented** — `memory/memory.md` +
[captain-jack-memory-design.md](captain-jack-memory-design.md) + the
save/parse logic in `orchestrate.py`.

**Description**: a deliberately simple, tag-based, plain-markdown memory
store — an identity/boot doc plus one running facts file, no daily notes,
frontmatter, or wikilinks (unlike the fuller `ai-memory-vault` pattern used
by the separate Jarvis project). Exactly three allowed tags:
`household:<Name>`, `joke`, `automation`; anything else is discarded.
Household facts can only be filed under a name with a pre-existing `###`
heading — Jack can never mint a new household member himself.

**Intended function**: let Jack recall durable per-person facts, running
jokes, and stated automation preferences across sessions, without giving a
lightweight model (Haiku) autonomous file-write authority — the model
*proposes* a tagged fact in its reply; orchestration code deterministically
validates (regex match against the allowlist, case-insensitive substring
dedup, known-household-name check) and appends it, or discards it,
fail-closed on anything malformed or unrecognized.

**Interfaces**: read in full by the
[Conversation Orchestrator](#43-conversation-orchestrator) every turn and
injected into the system prompt; written only by orchestration code
(`save_memory` in `orchestrate.py`), never by the model directly.

Confirmed via live testing: tag parsing, allowlist enforcement, and dedup
all work correctly against the real API; the *decision* to propose a save
is itself non-deterministic model behavior (an identical automation-
preference statement got `NONE` once and a correct tag on retry) — accepted
as normal model variance, not a bug.

Does not yet cover location/environment or appointment/calendar facts
called for by [Use Cases 2.3](#23-environmental-and-self-awareness) and
[2.7](#27-personalized-memory) — see [Open Issues](#5-open-issues).

### 4.6 Home-Automation Tool Schema

**Status: Designed (allowlist only), not implemented.**

**Description**: the fixed, small tool schema Haiku would use to request
home-automation actions, scoped exactly to
[home-automation-allowlist.md](home-automation-allowlist.md)'s categories
and bounds (lights, fans, switched outlets, thermostat, irrigation, scene
activation).

**Intended function**: same enforcement pattern as memory — Haiku proposes
an intent + parameters; orchestration code validates against the allowlist
(including numeric bounds like thermostat clamps and irrigation duration
caps) before ever calling a vendor API, rather than trusting model output
directly.

**Interfaces**: would be invoked mid-turn by the
[Conversation Orchestrator](#43-conversation-orchestrator); would call out
to per-vendor APIs (Govee, Tuya/SmartLife IoT Platform, ecobee, Rachio —
each individually confirmed to have a usable API; Minoston's integration
path is still unresearched). None of this exists in code yet — no tool
schema is currently passed to the Anthropic API call in `orchestrate.py`.

### 4.7 Text to Speech (TTS)

**Status: Not started.**

**Description**: local TTS rendering Jack's spoken reply to audio. No
engine chosen.

**Intended function**: convert the orchestrator's spoken-text output to an
audio stream for playback through the XVF3800/speaker, feeding both the
listener and the [beak-sync](#48-beak-sync-rms-envelope-extraction) module.

**Interfaces**: consumes text from the
[Conversation Orchestrator](#43-conversation-orchestrator); outputs an
audio stream to the XVF3800 output path and to
[Beak-Sync](#48-beak-sync-rms-envelope-extraction).

### 4.8 Beak-Sync (RMS Envelope Extraction)

**Status: Not started; blocked on the XVF3800 for live validation**, though
the design itself doesn't strictly require the board to begin building.

**Description**: real-time RMS amplitude envelope extraction from whatever
audio is currently playing — idle clip or live TTS — at roughly 30–50Hz,
replacing the MY1690's old dual-channel pre-encoded beak-track trick with
one code path for both cases.

**Intended function**: produce a live beak-position value from audio
amplitude and stream it to the Arduino as `BEAK <0–255>` commands. Because
the envelope needs to be computed before playback timing catches up,
audio playback likely needs a small deliberate delay to keep beak motion in
sync — accounting for RMS processing, command generation/transmission, and
Arduino-side parsing/easing/mechanical response time.

**Interfaces**: reads the live audio stream from
[TTS](#47-text-to-speech-tts) or the
[idle/ambient player](#410-idle-and-ambient-audio-player); writes `BEAK`
commands to the [Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link).
Whether this value needs additional easing (Arduino-side, Pi-side, or at
all) is unresolved — see [Open Issues](#5-open-issues).

### 4.9 Direction of Arrival (DoA) Reader

**Status: Not started; blocked on the XVF3800.**

**Description**: Pi-side code reading per-beam azimuth from the XVF3800 via
`xvf_host AEC_AZIMUTH_VALUES`.

**Intended function**: supply a sound-direction cue to drive head-turn
behavior (e.g., turning to face whoever just spoke), replacing the old
electret-mic-based triangulation entirely.

**Interfaces**: reads from the XVF3800 over USB; feeds head-position
targets into the [Gesture Engine](#412-gesture-engine-and-catalog) or
directly into `HEAD` commands over the
[serial link](#413-pi-to-arduino-serial-link).

### 4.10 Idle and Ambient Audio Player

**Status: Not started.**

**Description**: Pi-side playback of local audio clip files (one-liners,
movie quotes, pirate sayings) during Offline mode.

**Intended function**: drive Offline-mode behavior — periodic playback of a
clip, paired with either a random gesture or a predefined gesture script,
beak-synced via the same [RMS envelope path](#48-beak-sync-rms-envelope-extraction)
used for live TTS.

**Interfaces**: outputs audio through the XVF3800; feeds
[Beak-Sync](#48-beak-sync-rms-envelope-extraction); triggers the
[Gesture Engine](#412-gesture-engine-and-catalog); orchestrated by whatever
implements the [Offline/Online/Asleep mode logic](#411-sleep-mode-state-machine),
which doesn't yet exist as a discrete module.

### 4.11 Sleep-Mode State Machine

**Status: Not started, not fully designed.**

**Description**: the mode-transition logic implied by
[Use Case 2.4](#24-operational-modes) — Offline ⇄ Online on wake-word/
session-end, and Offline → Asleep after a randomized idle timeout, with its
own quieter gesture/sound subset. No timeout values, sleep-trigger phrase,
or Asleep-specific catalog subset are defined yet.

**Intended function**: own overall mode state, gate which of
[Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player)'s
catalogs is active, and hand off to/from the
[Wake Word Spotter](#41-wake-word-spotter) and
[Conversation Orchestrator](#43-conversation-orchestrator) on transitions.

**Interfaces**: would sit "above" the orchestrator, wake-word spotter, and
idle player, coordinating all three — no such coordinating module currently
exists; `orchestrate.py` today only implements the Online conversation loop
in isolation.

### 4.12 Gesture Engine and Catalog

**Status: Content drafted, not implemented; storage location undecided.**

**Description**: a library of named motion primitives (speech-driven,
emotional, idle, conversational, and "expressive" categories) — each a
short timed sequence of pitch/roll/yaw/beak targets — drafted in
[gesture-library.md](gesture-library.md).

**Intended function**: provide reusable, named gesture sequences triggered
by DoA, text content/tags, random idle selection, or explicit request, sent
to the Arduino as multi-servo, timed, eased motion.

**Interfaces**: triggered by the
[Conversation Orchestrator](#43-conversation-orchestrator) (in-session),
the [Idle/Ambient Audio Player](#410-idle-and-ambient-audio-player) (offline),
or [DoA](#49-direction-of-arrival-doa-reader); emits commands over the
[serial link](#413-pi-to-arduino-serial-link) — as a single `GESTURE <id>`
per the brief's original sketch, or as a decomposed sequence of `HEAD`/
`BEAK` commands with timing, per
[Arduino-command-structure.md](Arduino-command-structure.md)'s still-open
question of whether gestures live on the Arduino or the Pi. See
[Open Issues](#5-open-issues). The library also includes at least one
gesture (`Blink`) that assumes an eyelid mechanism not present in the
[documented physical build](#35-servos-head-and-beak) — see
[Open Issues](#5-open-issues).

### 4.13 Pi to Arduino Serial Link

**Status: Partially specified, not implemented.**

**Description**: one-directional serial protocol, Pi → Arduino only (no
upstream sensor relay in the new design). The
[project brief](parrot-project-brief.md) sketches it loosely —
`HEAD p:<pitch> r:<roll> y:<yaw>`, `BEAK <0–255>`, `GESTURE <id>` — while
[Arduino-command-structure.md](Arduino-command-structure.md) works out a
more concrete, compact, fixed-width framing (single-character field tags
`p`/`r`/`y`/`b`/`t`, two digits for pitch/roll/beak, three for yaw, four for
time-to-reach in ms, no spaces, newline-terminated) aimed at fast parsing
and short transmission time (worst case ~19 chars ≈ 1.65ms at 115200 bps,
flagged in that doc itself as unconfirmed arithmetic). These two
descriptions haven't been reconciled into one authoritative frame format —
see [Open Issues](#5-open-issues).

**Intended function**: carry all motion commands from the Pi to the
Arduino — head orientation, beak position, and gestures — fast enough to
support smooth, eased, ~30–50Hz beak-sync and lifelike head motion without
exceeding the Arduino servo loop's minimum 20ms update period.

**Interfaces**: written to by
[Beak-Sync](#48-beak-sync-rms-envelope-extraction),
[DoA](#49-direction-of-arrival-doa-reader)-driven head movement, and the
[Gesture Engine](#412-gesture-engine-and-catalog); read by
[Arduino Firmware](#414-arduino-firmware). Open questions recorded in
[Arduino-command-structure.md](Arduino-command-structure.md) and carried
into [Open Issues](#5-open-issues): gesture storage location, gesture
interruptibility/preemption vs. queuing, whether gestures can include beak
movement, whether gestures are layerable/blendable, whether beak movement
needs easing, whether 20ms is a fast enough update period given easing math
cost, and whether the link needs ACK/timeout-retry for robustness.

### 4.14 Arduino Firmware

**Status: Toolchain confirmed, sketch not started.**
`arduino/TestBlink/TestBlink.ino` is a minimal onboard-LED blink sketch,
confirmed 2026-09-13 to compile and download successfully via `arduino-cli`
against a connected Arduino Uno; it implements none of the servo-control
design. Servo and ServoEasing libraries are installed and available, but
the real servo/easing sketch itself hasn't been started.

**Description**: the real-time sketch that will parse incoming serial
commands and drive the four servos, layering an easing library over the
standard Arduino servo library for smooth, synchronized multi-servo motion.

**Intended function**: execute `HEAD`/`BEAK`/gesture commands from the Pi
at a real-time loop rate no slower than the servos' 20ms PWM period,
easing pitch/roll/yaw transitions together (cubic easing, kept to integer
math where possible for speed). Notably must **not** reintroduce
SoftwareSerial alongside the easing library without further research —
the two were observed to interfere with each other in the prior MY1690-era
design, and SoftwareSerial was removed along with the MY1690.

**Interfaces**: reads the
[Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link); writes PWM to
the [head and beak servos](#35-servos-head-and-beak). Needs a full rewrite
for servo-only duty once the Arduino hardware question (remove old
peripherals vs. use a new board — see
[Arduino Servo Controller](#34-arduino-servo-controller)) is resolved; Chip
may write this sketch himself rather than hand it to a future session.

## 5. Open Issues

- Voice-ID conflict: [Use Case 2.7](#27-personalized-memory)/the goals
  document assume voice ID identifies which household member is speaking,
  but the brief and memory design explicitly defer speaker ID and rely on
  self-reported names instead — see
  [captain-jack-goals-objectives-user-scenarios.md](captain-jack-goals-objectives-user-scenarios.md)
  vs.
  [parrot-project-brief.md](parrot-project-brief.md#decisions-already-made-dont-re-litigate-these-without-new-information).
- [Persona and Identity Prompt](#44-persona-and-identity-prompt) is a
  minimal stub; the full backstory, pirate speech style, deference
  protocol, and conversational-intensity fade from
  [Use Case 2.2](#22-persona-captain-jack-the-parrot) aren't implemented.
- Gendered deference phrasing ("Captain" vs. "Mistress") needs per-person
  gender data with no home in the current
  [household memory schema](#45-memory-subsystem).
- No memory category exists for location/environment or appointment/
  calendar facts, though [Use Cases 2.3](#23-environmental-and-self-awareness)
  and [2.7](#27-personalized-memory) assume Jack tracks both.
- Only the Online mode is implemented; Offline idle-catalog behavior and a
  distinct Asleep behavior/state machine
  ([4.11](#411-sleep-mode-state-machine)) are undesigned.
- Wake word, end-session phrase, and go-to-sleep phrase are all unchosen —
  no mode-transition trigger exists yet (see
  [Session Boundaries](#25-session-boundaries)).
- Gesture storage location is unresolved — Arduino-resident (interpreted
  from a `GESTURE <id>`) vs. Pi-composed primitive sequences — blocking a
  final [serial protocol](#413-pi-to-arduino-serial-link) spec; see
  [Arduino-command-structure.md](Arduino-command-structure.md).
- Beak-easing ownership is unresolved: whether smoothing happens in the
  Pi's [RMS envelope extraction](#48-beak-sync-rms-envelope-extraction),
  the Arduino's easing library, both, or neither.
- [gesture-library.md](gesture-library.md)'s `Blink` gesture assumes an
  eyelid mechanism not present in the
  [documented servo build](#35-servos-head-and-beak) (only head
  pitch/roll/yaw + beak) — hardware/catalog mismatch.
- The [Pi→Arduino serial framing](#413-pi-to-arduino-serial-link) has two
  unreconciled descriptions (the brief's loose sketch vs.
  [Arduino-command-structure.md](Arduino-command-structure.md)'s compact
  format), and that document's own open questions (ACK/retry, gesture
  interruptibility/preemption, layering/blending, its baud-rate timing
  math) remain unanswered.
- [Home-Automation Tool Schema](#46-home-automation-tool-schema) is fully
  allowlisted on paper but not wired into `orchestrate.py` — no tool schema
  currently reaches the Anthropic API call.
- Minoston's integration path (direct API vs. hub requirement) is
  unresearched — flagged as unknown in
  [home-automation-allowlist.md](home-automation-allowlist.md) itself.
- A per-outlet "automation-safe" allowlist doesn't exist yet, needed before
  any switched-outlet control ships per
  [home-automation-allowlist.md](home-automation-allowlist.md#switched-outlets).
- Numeric safety bounds (thermostat clamp range, irrigation max duration)
  are marked TBD in
  [home-automation-allowlist.md](home-automation-allowlist.md).
- Automation authoring — both vendor-executed schedules and Jack-sensed/
  Jack-executed triggers (see [Use Case 2.6](#26-home-automation)) — is
  deferred with no allowlist of its own.
- No `tests.md` exists yet, despite the goals document requiring at least
  one test per use case and per hardware/software functional block.
- TTS and wake-word engines are unselected; STT is only tentatively "local
  Whisper."
- Idle-audio-on-Pi tradeoff: ambient sound now depends on the Pi being up,
  unlike the removed MY1690-on-Arduino design — noted, not mitigated (see
  [Removed and Legacy Hardware](#37-removed-and-legacy-hardware)).
- Conversational-privacy/oversharing risk (a fact told by one household
  member surfacing in front of another) is noted with no technical
  mitigation, per
  [parrot-project-brief.md](parrot-project-brief.md#decisions-already-made-dont-re-litigate-these-without-new-information).
- Persona portability ("if we grow tired of Captain Jack, the persona
  should be changeable without rebuilding the stack") isn't addressed —
  [identity.md](../memory/identity.md) is Jack-specific prose, not a
  swappable config.
- The scope of "anything Haiku can do" beyond home automation is explicitly
  undefined in the goals document — including whether Haiku can be
  proactive within a session, and what (if anything) carries over between
  sessions outside of Jack's own `memory.md`.
- Speculative scenarios (Alexa flirtation, community-lecture demo — see
  [Deferred and Speculative Scenarios](#28-deferred-and-speculative-scenarios))
  are recorded but unscoped, including the lecture scenario's own
  follow-on questions about credential/network provisioning and long-form
  vs. interactive delivery.
- An Arduino Uno is now connected to the Pi and its toolchain confirmed
  working, but it's unconfirmed whether it is (or replaces) the original
  board carrying the MY1690/electret mics; that old hardware must be
  removed (or a replacement Arduino used) before real serial integration,
  and the firmware itself still needs a servo-only rewrite — see
  [Arduino Servo Controller](#34-arduino-servo-controller).
- Servo real-time loop rate: whether the 20ms PWM-period floor is fast
  enough for lifelike easing once easing math cost is accounted for is
  flagged as needing more research in
  [Arduino-command-structure.md](Arduino-command-structure.md).
