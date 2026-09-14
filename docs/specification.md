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
  [Home Automation](#26-home-automation)). **Decided 2026-09-14** (former
  [Open Issue](#5-open-issues) 19): further secondary capabilities are
  **not** open-ended ("anything Haiku can do") — that framing is dropped.
  Email, calendar, and financial access in particular are explicitly out
  of scope for now, deferred until much later, Chip's call. Candidate
  ideas for eventual secondary capabilities are brainstormed, not
  designed, in
  [Possible Future Enhancements](#6-possible-future-enhancements).

**Testing philosophy**: at least one test per use case and per hardware/
software functional block, developed alongside each block as it's
implemented — not an exhaustive or product-grade test suite. Tests, their
procedures, and any needed test data/scripts are recorded in
[tests.md](tests.md) (per-test scripts and input files live in
[`tests/`](../tests), named after the test) as functional blocks come
online. **Added 2026-09-14** with its first entry (the `home` memory tag);
still only one test recorded — see [Open Issues](#5-open-issues).

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

**Updated 2026-09-14**: this backstory, speech-pattern detail, and
deference behavior are now in
[`identity.md`](../memory/identity.md)'s `## Persona` section — see
[Persona and Identity Prompt](#44-persona-and-identity-prompt). Untested
against the live API; treated as a first baseline, not final.

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

**Updated 2026-09-14**: "home" is now a memory category (see
[Memory Subsystem](#45-memory-subsystem)) — durable, low-frequency-change,
fits the existing append-only design. "Current location" remains
unimplemented; it changes too often for that pattern and needs an
overwrite-style save instead — deferred, see
[Possible Future Enhancements](#6-possible-future-enhancements).

### 2.4 Operational Modes

Three modes are defined:

- **Offline** (the Pi is up and running its idle loop, just not in an
  active Haiku session): Jack is not static — he cycles through a catalog
  of gestures and short local audio clips (one-liner jokes, movie quotes,
  pirate-y sayings), gesture choice random unless a script is paired with
  a specific clip, beak movement driven off the audio the same way as in
  an online session. See
  [Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player) and
  [Gesture Engine and Catalog](#412-gesture-engine-and-catalog). **This
  presumes the Pi is running** — all of Jack's behavior, including idle
  motion, is Pi-driven (see
  [Arduino Servo Controller](#34-arduino-servo-controller)); if the Pi
  itself is down, crashed, or not yet booted, Jack is simply motionless
  and silent, not in some Arduino-only idle state. That's accepted
  behavior, not a gap — see [Open Issues](#5-open-issues) issue 7.
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
goals document but not scoped against the current memory allowlist, which
has no calendar/appointment category — see
[Open Issues](#5-open-issues).

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

**Description**: a new Arduino Uno, replacing the original build's board.
**Status: connected to the Pi and confirmed working via `arduino-cli`** —
compile and upload both verified end-to-end (2026-09-13 compile/download,
2026-09-14 full compile+upload with a visually-confirmed blink-rate change
on `arduino/TestBlink`); Servo and ServoEasing libraries are installed.
The old MY1690 + electret-mic hardware has been removed (it lived on the
original board, not this one) — see
[Removed and Legacy Hardware](#37-removed-and-legacy-hardware). This new
board is **not yet wired to the head/beak servos**; servo-only firmware can
be written, compiled, and uploaded now, but real actuation can't be
validated until that connection is made — see
[Open Issues](#5-open-issues). Previously owned all "intelligence,"
peripherals, and sensor input in the pre-Pi design; those roles are removed
and it shrinks to real-time servo execution only. The real-time PWM loop
itself deliberately stays on the Arduino rather than the Pi, so it stays
fast and isn't jittered by the Pi's scheduling/serial round-trip — but the
Arduino has **no autonomous behavior of its own**: it only ever does what
the most recent serial command told it to do. If the Pi is down, crashed,
or simply not sending anything, the Arduino does nothing and Jack goes
still — accepted behavior (see
[Open Issues](#5-open-issues) issue 7), not a gap to fix.

**Intended function**: parses incoming serial commands from the Pi and
drives the four servos accordingly — head pitch/roll/yaw and beak position
— as timed, eased motion (per
[Arduino-command-structure.md](Arduino-command-structure.md)) via an
Arduino easing library layered over the standard servo library. Gesture
sequences are composed on the Pi and sent down as a series of these same
primitive commands — the Arduino has no concept of a "gesture" as such;
see [Gesture Engine and Catalog](#412-gesture-engine-and-catalog).

**Interconnect**: one-directional serial from the Pi 5 (no upstream sensor
data anymore, unlike the original design). Exact command framing is
partially specified and not fully reconciled — see
[Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link). Servo PWM
wiring itself is not yet connected — see above.

The sketch itself still needs to be written for servo-only duty; see
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
  design where ambient noise ran independent of Pi health.
  **Resolved 2026-09-14** (former [Open Issue](#5-open-issues) 17): this
  is a special case of the Arduino-thin decision in issue 7 — the Arduino
  has no autonomous behavior at all, so a Pi outage already means total
  silence and stillness, not just silence. No separate mitigation for
  idle audio specifically; accepted as correct behavior, not revisited.
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

**Status: Implemented, including the full persona design** —
`memory/identity.md`. **Updated 2026-09-14**: added a `## Persona` section
encoding the backstory, pirate speech style, deference protocol, and
conversational-intensity fade from
[Use Case 2.2](#22-persona-captain-jack-the-parrot)/
[2.1](#21-companionable-conversation) — see
[Open Issues](#5-open-issues) issue 2. Written as concrete traits + a
handful of example lines rather than narrative prose, on the theory that a
small model like Haiku follows short, concrete instructions more reliably
than it "acts out" backstory lore. Untested against the live API; treated
as a first baseline to iterate on, not a final version.

**Description**: a short, human-edited boot document establishing Jack as
a light, humorous, household-wide social companion, his backstory and
in-character voice, his action boundary (home-automation allowlist only,
no open-ended tool access), the no-voice-ID trust stance, and the exact
`MEMORY:` proposal format/tag rules.

**Intended function**: injected verbatim as (the first part of) the system
prompt every turn, establishing tone and hard behavioral rules.

**Interfaces**: read by the [Conversation Orchestrator](#43-conversation-orchestrator)
every turn.

**Persona portability**: confirmed 2026-09-14 — `orchestrate.py` treats
`identity.md` as an opaque file it reads and injects verbatim
(`load_system_prompt` in orchestrate.py:34-37); nothing in the orchestration
code or the `memory.md` schema (household/joke/automation sections) is
Captain-Jack-specific. Swapping personas is just replacing `identity.md`'s
content. The one loose end: `orchestrate.py`'s CLI banner and docstring
hardcode the literal strings "Captain Jack" and "Jack" (e.g. the
`print("Captain Jack is listening...")` startup line and the `Jack:` reply
prefix) — cosmetic only, doesn't affect behavior, but would show a
mismatched label if the persona were actually swapped.

### 4.5 Memory Subsystem

**Status: Implemented** — `memory/memory.md` +
[captain-jack-memory-design.md](captain-jack-memory-design.md) + the
save/parse logic in `orchestrate.py`.

**Description**: a deliberately simple, tag-based, plain-markdown memory
store — an identity/boot doc plus one running facts file, no daily notes,
frontmatter, or wikilinks (unlike the fuller `ai-memory-vault` pattern used
by the separate Jarvis project). Exactly four allowed tags:
`household:<Name>`, `joke`, `automation`, `home`; anything else is
discarded. Household facts can only be filed under a name with a
pre-existing `###` heading — Jack can never mint a new household member
himself.

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

**Updated 2026-09-14**: added the `home` tag, covering the durable-location
half of [Use Case 2.3](#23-environmental-and-self-awareness). Still doesn't
cover "current location" (deferred — see
[Possible Future Enhancements](#6-possible-future-enhancements)) or
appointment/calendar facts called for by
[Use Case 2.7](#27-personalized-memory) — see [Open Issues](#5-open-issues).

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
Arduino-side parsing/mechanical response time.

**Resolved 2026-09-14** (former [Open Issue](#5-open-issues) 8): all beak
smoothing happens here, as part of extracting the envelope itself
(attack/release-style shaping) — not as a separate easing step on either
side. The Arduino applies the `BEAK` value it receives directly to PWM,
no interpolation; see [Arduino Firmware](#414-arduino-firmware).

**Interfaces**: reads the live audio stream from
[TTS](#47-text-to-speech-tts) or the
[idle/ambient player](#410-idle-and-ambient-audio-player); writes `BEAK`
commands to the [Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link).

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

**Status: Content drafted, not implemented.**

**Description**: a library of named motion primitives (speech-driven,
emotional, idle, conversational, and "expressive" categories) — each a
short timed sequence of pitch/roll/yaw/beak targets — drafted in
[gesture-library.md](gesture-library.md).

**Resolved 2026-09-14** (former [Open Issue](#5-open-issues) 7): gestures
are stored and composed on the **Pi**, not the Arduino, to keep the
Arduino as thin as possible — the catalog lives in
`gesture-library.md`/its eventual code form, entirely Pi-side. The
Arduino never sees a gesture as a named unit, only the same primitive
timed servo commands it always takes. A consequence, noted 2026-09-14:
since the Arduino has no queue and acts on each command immediately as it
arrives, gesture **interruptibility/preemption and layering/blending are
entirely this engine's problem to solve, Pi-side** — not something the
serial link or firmware need any awareness of. Undesigned — see
[Open Issues](#5-open-issues) issue 24.

**Intended function**: provide reusable, named gesture sequences triggered
by DoA, text content/tags, random idle selection, or explicit request; the
Pi looks up the named sequence and sends it to the Arduino as a series of
primitive, timed servo commands — not a single opaque `GESTURE <id>`.

**Interfaces**: triggered by the
[Conversation Orchestrator](#43-conversation-orchestrator) (in-session),
the [Idle/Ambient Audio Player](#410-idle-and-ambient-audio-player) (offline),
or [DoA](#49-direction-of-arrival-doa-reader); emits a decomposed sequence
of `HEAD`/`BEAK` commands with timing over the
[serial link](#413-pi-to-arduino-serial-link), per
[Arduino-command-structure.md](Arduino-command-structure.md) — never a
single opaque `GESTURE <id>`, now that storage location is resolved (see
above). A previous draft of the library included a `Blink` gesture
assuming an eyelid mechanism not present in the
[documented physical build](#35-servos-head-and-beak); it has been removed.

### 4.13 Pi to Arduino Serial Link

**Status: Partially specified, not implemented.**

**Description**: one-directional serial protocol, Pi → Arduino only (no
upstream sensor relay in the new design). **Reconciled 2026-09-14**
(former [Open Issue](#5-open-issues) 9) into one authoritative framing,
superseding both the [project brief](parrot-project-brief.md)'s loose,
word-prefixed sketch (`HEAD p:<pitch> r:<roll> y:<yaw>`, `BEAK <0–255>`,
`GESTURE <id>`) and treating
[Arduino-command-structure.md](Arduino-command-structure.md)'s compact,
fixed-width encoding as the winning design:

- Exactly two line shapes, newline-terminated, human-readable, no spaces,
  no literal `HEAD`/`BEAK`/`GESTURE` keyword — the leading field-tag
  character *is* the command type, since that's strictly shorter and the
  two shapes are already unambiguous by their fields:
  - **Head motion**: `p<PP>r<RR>y<YYY>t<TTTT>` — pitch (2 digits), roll (2
    digits), yaw (3 digits), time-to-reach in ms (4 digits). Always
    carries all three axes, even if only one is actually changing — the
    Pi fills in the others with their last-sent value — so the Arduino's
    easing library always has a full 3-axis start/end pair to interpolate
    over `t` ms, per
    [Arduino Servo Controller](#34-arduino-servo-controller).
  - **Beak position**: `b<BB>` — beak position (2 digits) only, **no
    `t` field**. Per former [Open Issue](#5-open-issues) 8, beak motion is
    never eased on the Arduino, so there's nothing for a time field to
    do; the Arduino applies it to PWM immediately.
  - Pitch/roll/beak's 2-digit fields and yaw's 3-digit field are
    unsigned, zero-padded, offset-encoded (per
    [Arduino-command-structure.md](Arduino-command-structure.md)'s
    "use 2 digits and offset in Arduino code" note) — the exact offset
    and usable angle range per axis aren't pinned down yet, just the
    encoding shape.
  - `GESTURE <id>` is dropped entirely, not just superseded in wording:
    gesture storage lives on the Pi (former issue 7), so the Arduino
    never receives anything but the two shapes above, whether a given
    line came from a gesture sequence, DoA, or beak-sync makes no
    difference to it.
- Still **not** pinned down by this reconciliation: exact per-axis
  offsets/ranges, worst-case transmission time (that doc's own
  ~19-char/1.65ms estimate is flagged there as unconfirmed arithmetic and
  needs re-deriving against the format above), and whether the link needs
  ACK/timeout-retry.
- **Reclassified 2026-09-14**: gesture interruptibility/preemption vs.
  queuing and layering/blending are **not** link-level or Arduino-level
  concerns. Each line the Arduino receives is acted on immediately, as
  soon as it arrives — the Arduino has no queue, no concept of "gesture"
  as a unit, and nothing to preempt (per former
  [Open Issues](#5-open-issues) issue 7). Whatever "interruptibility"
  means is entirely a question of what the Pi chooses to send and when —
  see [Gesture Engine and Catalog](#412-gesture-engine-and-catalog) and
  [Open Issues](#5-open-issues) issue 24.

**Intended function**: carry all motion commands from the Pi to the
Arduino — head orientation and beak position — fast enough to support
smooth, eased, ~30–50Hz beak-sync and lifelike head motion without
exceeding the Arduino servo loop's minimum 20ms update period.

**Interfaces**: written to by
[Beak-Sync](#48-beak-sync-rms-envelope-extraction),
[DoA](#49-direction-of-arrival-doa-reader)-driven head movement, and the
[Gesture Engine](#412-gesture-engine-and-catalog) (as ordinary head-motion
lines, per above); read by [Arduino Firmware](#414-arduino-firmware).

### 4.14 Arduino Firmware

**Status: Toolchain confirmed (compile + upload), sketch not started.**
`arduino/TestBlink/TestBlink.ino` is a minimal onboard-LED blink sketch;
`arduino-cli` compile/download was confirmed 2026-09-13, and a full
compile+upload cycle (including a visually-confirmed blink-rate edit) was
confirmed 2026-09-14 against the new Arduino Uno — see
[Arduino Servo Controller](#34-arduino-servo-controller). It implements
none of the servo-control design. Servo and ServoEasing libraries are
installed and available, but the real servo/easing sketch itself hasn't
been started, and can't be validated against real actuation until the
board is wired to the servos (still pending) — see
[Open Issues](#5-open-issues).

**Description**: the real-time sketch that will parse incoming serial
commands and drive the four servos, layering an easing library over the
standard Arduino servo library for smooth, synchronized head motion
(gestures are just `HEAD`/`BEAK` command sequences from the Pi — see
[Gesture Engine and Catalog](#412-gesture-engine-and-catalog) — not a
distinct command type).

**Intended function**: execute `HEAD`/`BEAK` commands from the Pi at a
real-time loop rate no slower than the servos' 20ms PWM period, easing
pitch/roll/yaw transitions together (cubic easing, kept to integer math
where possible for speed). `BEAK` is applied directly to PWM with **no**
easing — that smoothing is done Pi-side, in
[Beak-Sync](#48-beak-sync-rms-envelope-extraction) — see former
[Open Issue](#5-open-issues) 8. Notably must **not** reintroduce
SoftwareSerial alongside the easing library without further research —
the two were observed to interfere with each other in the prior MY1690-era
design, and SoftwareSerial was removed along with the MY1690.

**Interfaces**: reads the
[Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link); writes PWM to
the [head and beak servos](#35-servos-head-and-beak) — not yet wired, see
[Arduino Servo Controller](#34-arduino-servo-controller). Chip may write
this sketch himself rather than hand it to a future session.

## 5. Open Issues

1. Voice-ID conflict: [Use Case 2.7](#27-personalized-memory)/the goals
  document assume voice ID identifies which household member is speaking,
  but the brief and memory design explicitly defer speaker ID and rely on
  self-reported names instead — see
  [captain-jack-goals-objectives-user-scenarios.md](captain-jack-goals-objectives-user-scenarios.md)
  vs.
  [parrot-project-brief.md](parrot-project-brief.md#decisions-already-made-dont-re-litigate-these-without-new-information).
2. ~~[Persona and Identity Prompt](#44-persona-and-identity-prompt) is a
  minimal stub; the full backstory, pirate speech style, deference
  protocol, and conversational-intensity fade from
  [Use Case 2.2](#22-persona-captain-jack-the-parrot) aren't implemented.~~
  **Resolved 2026-09-14**: all four added to `identity.md` as a `## Persona`
  section — concrete traits + example lines rather than narrative prose, to
  suit Haiku. Treated as a first baseline, not final — untested against the
  live API, and expected to change once Chip hears it in practice. The
  general per-person gendered-deference case is deliberately left to issue
  3 below; this only hardcodes the one known exception (Kath).
3. Gendered deference phrasing ("Captain" vs. "Mistress") needs per-person
  gender data with no home in the current
  [household memory schema](#45-memory-subsystem).
4. ~~No memory category exists for location/environment or appointment/
  calendar facts, though [Use Cases 2.3](#23-environmental-and-self-awareness)
  and [2.7](#27-personalized-memory) assume Jack tracks both.~~
  **Resolved/split 2026-09-14**: added a `home` tag for the durable-location
  half — see [Memory Subsystem](#45-memory-subsystem). "Current location"
  (volatile, needs overwrite not append) deferred to
  [Possible Future Enhancements](#6-possible-future-enhancements) rather
  than solved here. Appointment/calendar was a separate concern bundled
  into this issue by mistake — split out to issue 23 below.
5. Only the Online mode is implemented; Offline idle-catalog behavior and a
  distinct Asleep behavior/state machine
  ([4.11](#411-sleep-mode-state-machine)) are undesigned.
6. Wake word, end-session phrase, and go-to-sleep phrase are all unchosen —
  no mode-transition trigger exists yet (see
  [Session Boundaries](#25-session-boundaries)).
7. ~~Gesture storage location is unresolved — Arduino-resident (interpreted
  from a `GESTURE <id>`) vs. Pi-composed primitive sequences — blocking a
  final [serial protocol](#413-pi-to-arduino-serial-link) spec; see
  [Arduino-command-structure.md](Arduino-command-structure.md).~~
  **Resolved 2026-09-14**: Pi-composed. Rationale: keep as much off the
  Arduino as possible. The Arduino ends up with zero autonomous behavior —
  it only ever executes the most recent command the Pi sent it, so if the
  Pi is down, crashed, or hasn't booted, Jack is simply motionless and
  silent (no local idle/gesture fallback of any kind). Accepted as
  correct behavior, not a gap; updated
  [Arduino Servo Controller](#34-arduino-servo-controller),
  [Gesture Engine and Catalog](#412-gesture-engine-and-catalog),
  [Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link),
  [Operational Modes](#24-operational-modes), and
  [Arduino-command-structure.md](Arduino-command-structure.md) to remove
  any wording implying otherwise.
8. ~~Beak-easing ownership is unresolved: whether smoothing happens in the
  Pi's [RMS envelope extraction](#48-beak-sync-rms-envelope-extraction),
  the Arduino's easing library, both, or neither.~~ **Resolved
  2026-09-14**: all beak smoothing lives in the Pi's RMS envelope
  extraction; the Arduino applies whatever `BEAK` value it receives
  directly to PWM, no easing. Rationale: `BEAK` updates already arrive at
  ~30–50Hz (every 20–33ms), near the Arduino's 20ms PWM floor, so there's
  barely a gap for a cubic-easing pass to smooth over — unlike a gesture
  waypoint, which is hundreds of ms from the next. A correct envelope
  extractor already needs attack/release-style smoothing to produce a
  good envelope in the first place, so the smoothing effectively already
  exists on the Pi side, at no extra cost, before a value is ever sent.
  Consistent with the Arduino-thin principle from issue 7. Untested — this
  resolves the design question, not a validated one; still blocked on the
  XVF3800 to confirm it looks smooth enough in practice, per
  [Beak-Sync](#48-beak-sync-rms-envelope-extraction)'s status.
9. ~~The [Pi→Arduino serial framing](#413-pi-to-arduino-serial-link) has
  two unreconciled descriptions (the brief's loose sketch vs.
  [Arduino-command-structure.md](Arduino-command-structure.md)'s compact
  format), and that document's own open questions (ACK/retry, gesture
  interruptibility/preemption, layering/blending, its baud-rate timing
  math) remain unanswered.~~ **Partially resolved 2026-09-14**: the two
  framing descriptions are reconciled into one — see
  [Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link). Left open,
  narrowed to what that section explicitly leaves unpinned: exact per-axis
  offsets/ranges, worst-case transmission time re-derived against the
  reconciled format, and ACK/timeout-retry. Gesture interruptibility and
  layering were dropped from this issue's scope — see issue 24: they're
  not a link-level concern.
10. [Home-Automation Tool Schema](#46-home-automation-tool-schema) is fully
  allowlisted on paper but not wired into `orchestrate.py` — no tool schema
  currently reaches the Anthropic API call.
11. Minoston's integration path (direct API vs. hub requirement) is
  unresearched — flagged as unknown in
  [home-automation-allowlist.md](home-automation-allowlist.md) itself.
12. A per-outlet "automation-safe" allowlist doesn't exist yet, needed before
  any switched-outlet control ships per
  [home-automation-allowlist.md](home-automation-allowlist.md#switched-outlets).
13. Numeric safety bounds (thermostat clamp range, irrigation max duration)
  are marked TBD in
  [home-automation-allowlist.md](home-automation-allowlist.md).
14. Automation authoring — both vendor-executed schedules and Jack-sensed/
  Jack-executed triggers (see [Use Case 2.6](#26-home-automation)) — is
  deferred with no allowlist of its own.
15. ~~No `tests.md` exists yet, despite the goals document requiring at
  least one test per use case and per hardware/software functional
  block.~~ **Partially resolved 2026-09-14**: [tests.md](tests.md) now
  exists, with its first test (the `home` memory tag). Coverage is still
  far short of "one test per use case and per functional block" — most
  implemented blocks (memory save/dedup beyond `home`, the orchestrator's
  conversation loop, persona/identity behavior) have none yet. Left open,
  narrowed to a coverage gap rather than a missing file.
16. TTS and wake-word engines are unselected; STT is only tentatively "local
  Whisper."
17. ~~Idle-audio-on-Pi tradeoff: ambient sound now depends on the Pi being
  up, unlike the removed MY1690-on-Arduino design — noted, not mitigated
  (see [Removed and Legacy Hardware](#37-removed-and-legacy-hardware)).~~
  **Resolved 2026-09-14**: subsumed by issue 7's Arduino-thin decision —
  a Pi outage already means total stillness and silence, not just no
  idle audio, and that's accepted behavior. No separate fix needed for
  audio specifically.
18. ~~Conversational-privacy/oversharing risk (a fact told by one household
  member surfacing in front of another) is noted with no technical
  mitigation, per
  [parrot-project-brief.md](parrot-project-brief.md#decisions-already-made-dont-re-litigate-these-without-new-information).~~
  **Closed 2026-09-14**: this was never actually an open design question —
  the brief already made the call (accepted risk, no mitigation, revisit
  only if it becomes a real annoyance in practice). Listing it here
  mischaracterized a decision as undecided. Not reopened by the `home`
  memory category or persona work added since, per Chip's call — flagged
  and considered, but left as the brief decided it.
19. ~~The scope of "anything Haiku can do" beyond home automation is
  explicitly undefined in the goals document — including whether Haiku
  can be proactive within a session, and what (if anything) carries over
  between sessions outside of Jack's own `memory.md`.~~ **Resolved
  2026-09-14**: the open-ended framing is dropped — see
  [Goals and Objectives](#1-goals-and-objectives). Secondary capabilities
  beyond home automation are deliberately scoped, not "anything"; email/
  calendar/finance access deferred until much later. "Whether Haiku can
  be proactive within a session" is now a brainstormed candidate in
  [Possible Future Enhancements](#6-possible-future-enhancements), not an
  open design question. "What carries over between sessions outside
  memory.md" has a plain answer, not a gap: **nothing** — each API call
  is stateless; `orchestrate.py` re-sends `identity.md`/`memory.md` fresh
  every turn, and that's the only persistence there is.
20. Speculative scenarios (Alexa flirtation, community-lecture demo — see
  [Deferred and Speculative Scenarios](#28-deferred-and-speculative-scenarios))
  are recorded but unscoped, including the lecture scenario's own
  follow-on questions about credential/network provisioning and long-form
  vs. interactive delivery.
21. Firmware for servo-only control still needs to be written for
  the new Arduino Uno (old MY1690/electret-mic hardware already removed —
  see [Arduino Servo Controller](#34-arduino-servo-controller)); it can be
  developed and uploaded now, but can't be validated against real
  actuation until the board is wired to the head/beak servos, which
  hasn't happened yet.
22. Servo real-time loop rate: whether the 20ms PWM-period floor is fast
  enough for lifelike easing once easing math cost is accounted for is
  flagged as needing more research in
  [Arduino-command-structure.md](Arduino-command-structure.md).
23. **Added 2026-09-14, split from former issue 4**: no memory category
  exists for appointment/calendar facts, though
  [Use Case 2.7](#27-personalized-memory) assumes Jack tracks them — no
  allowlist tag, no schema, not scoped.
24. **Added 2026-09-14, reclassified out of former issue 9's scope**:
  gesture interruptibility/preemption vs. queuing, and layering/blending,
  are undesigned. Since the Arduino has no queue and acts on each command
  immediately on arrival (former issue 7), these are purely questions for
  the Pi-side [Gesture Engine](#412-gesture-engine-and-catalog) to answer
  — e.g. whether a new gesture request cuts off one in progress or waits,
  and whether two gestures can run on different axes at once — not
  anything the serial link or firmware need to know about.

## 6. Possible Future Enhancements

Ideas noted as worth doing eventually, deliberately not designed or
scheduled now — distinct from [Open Issues](#5-open-issues), which are
gaps or conflicts that need resolving, not optional extras.

1. **Volatile/overwrite-style memory.** Every current memory category
   (`household:<Name>`, `joke`, `automation`, `home`) is append-only —
   dated facts accumulate and old ones stay true forever, which fits all
   four. "Current location" (the perch is portable — see
   [Use Case 2.3](#23-environmental-and-self-awareness) and
   [Open Issues](#5-open-issues) issue 4) doesn't fit that pattern: it
   needs a single value that gets replaced on each update, not a growing
   log, or Jack will eventually treat a stale location as still current.
   Adding this well means a second save mechanism alongside the existing
   append-and-dedup one in `orchestrate.py` — worth designing as a general
   "current value" mechanism rather than a location-only special case,
   since other future volatile facts would hit the same problem.
2. **Secondary capabilities beyond home automation.** A brainstorm list,
   not a design — per
   [Goals and Objectives](#1-goals-and-objectives)/former
   [Open Issue](#5-open-issues) 19, none of this is scoped or scheduled:
   - Email reminders/notifications, given appropriate permissions —
     **deferred until much later, Chip's call 2026-09-14**, along with
     any calendar or financial account access/interaction. Not rejected
     outright, just far enough out that they're not worth designing
     against yet.
   - Appointment/calendar awareness — related to, but broader than, the
     memory-category gap in [Open Issues](#5-open-issues) issue 23; same
     deferral as above.
   - Proactive mid-session behavior — Jack bringing up something on his
     own (a reminder, a follow-up) rather than only ever responding. Not
     deferred the same way as the above — just unscoped.
