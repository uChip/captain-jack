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

History: none yet.

Source: [captain-jack-goals-objectives-user-scenarios.md](captain-jack-goals-objectives-user-scenarios.md).

**Goal**: a learning/personal hobby project — use current AI technology to
build an audio AI chat-client appliance with animatronic motion, in the form
of a life-size parrot. Finishing is itself a primary goal: the project should
produce one complete, functional prototype, not an open-ended accumulation of
partial features. **Non-goal**: this is not product development — no
manufacturing, life, or certification testing, no multi-unit concerns.

**Objectives** (deliberately loose, per the project's hobby nature):
- **Cost**: no fixed development-cost ceiling; each expenditure is decided
  individually. Development-time AI services: Claude Pro ($20/mo, potentially
  shared with other and future projects), plus free-tier Claude
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
  [Home Automation](#26-home-automation)). Further secondary capabilities
  are **not** open-ended ("anything Haiku can do") — email, calendar, and
  financial access in particular are explicitly out of scope for now,
  deferred until much later, Chip's call. Candidate ideas for eventual
  secondary capabilities are brainstormed, not designed, in
  [Possible Future Enhancements](#6-possible-future-enhancements). History:
  [log.md#issue-19](log.md#issue-19).

**Testing philosophy**: at least one test per use case and per hardware/
software functional block, developed alongside each block as it's
implemented — not an exhaustive or product-grade test suite. Tests, their
procedures, and any needed test data/scripts are recorded in
[tests.md](tests.md) (per-test scripts and input files live in
[`tests/`](../tests), named after the test) as functional blocks come
online. Coverage today is tracked in [Open Issues](#5-open-issues)
issue 15.

## 2. Use Cases and Scenarios

Source: [captain-jack-goals-objectives-user-scenarios.md](captain-jack-goals-objectives-user-scenarios.md)
unless otherwise noted.

### 2.1 Companionable Conversation

History: none yet.

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

History: [log.md#issue-2](log.md#issue-2).

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

**Correctly gendering the "Captain"/"Mistress" address** uses hand-set
`gender`/`honorific` facts in `memory.md` (see [Memory
Subsystem](#45-memory-subsystem)) — see [Open Issues](#5-open-issues)
issue 3 for the still-open question of whether gender leaks into broader
tone.

This backstory, speech-pattern detail, and deference behavior are
implemented in [`identity.md`](../memory/identity.md)'s `## Persona`
section — see [Persona and Identity Prompt](#44-persona-and-identity-prompt).
Untested against the live API; treated as a first baseline, not final.

### 2.3 Environmental and Self Awareness

History: none yet.

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

"home" is a memory category (see
[Memory Subsystem](#45-memory-subsystem)) — durable, low-frequency-change,
fits the existing append-only design. "Current location" remains
unimplemented; it changes too often for that pattern and needs an
overwrite-style save instead — deferred, see
[Possible Future Enhancements](#6-possible-future-enhancements).

### 2.4 Operational Modes

History: [log.md#issue-5](log.md#issue-5).

Three modes are defined, with nautical naming chosen to fit Jack's
persona:

- **On Watch** (formerly "Online"): actively in a Haiku conversation. On
  request, Jack can play a catalog sound while still on watch.
  See [Conversation Orchestrator](#43-conversation-orchestrator).
- **Off Watch** (formerly "Offline" — the Pi is up and running its idle
  loop, just not in an active Haiku session): Jack is not static — he
  cycles through a catalog of gestures and short local audio clips
  (one-liner jokes, movie quotes, pirate-y sayings), gesture choice random
  unless a script is paired with a specific clip, beak movement driven off
  the audio the same way as in an On Watch session. See
  [Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player) and
  [Gesture Engine and Catalog](#412-gesture-engine-and-catalog). **This
  presumes the Pi is running** — all of Jack's behavior, including idle
  motion, is Pi-driven (see
  [Arduino Servo Controller](#34-arduino-servo-controller)); if the Pi
  itself is down, crashed, or not yet booted, Jack is simply motionless
  and silent, not in some Arduino-only idle state. That's accepted
  behavior, not a gap — see [Open Issues](#5-open-issues) issue 7.
- **Asleep**: reached from Off Watch after a randomized idle period, or
  directly from On Watch on request. Jack switches to a quieter subset of
  movements/sounds. The mode-transition logic (when Asleep is entered/
  exited) is now specified — see
  [Sleep-Mode State Machine](#411-sleep-mode-state-machine). The
  Asleep-specific gesture/sound *subset itself* (which clips, which
  gestures) is still undesigned — see [Open Issues](#5-open-issues)
  issue 5.

Only **On Watch**, as a text-only conversation loop, is implemented today
(see `orchestrate.py`,
[Conversation Orchestrator](#43-conversation-orchestrator)). Off Watch's
and Asleep's own catalog behavior are undesigned beyond the description
above; their transition logic is designed but unimplemented — see
[Sleep-Mode State Machine](#411-sleep-mode-state-machine).

### 2.5 Session Boundaries

History: none yet.

See [Sleep-Mode State Machine](#411-sleep-mode-state-machine) for the full
transition design; summary: a fixed wake phrase ("Ahoy, Captain Jack",
spotted locally, not by Haiku) starts a session from either Off Watch or
Asleep. Ending a session or going to sleep *while already On Watch* is
not phrase-matched at all — Haiku itself recognizes the intent from
however the household member actually phrases it (a meta-tag on the
reply, same mechanism as the `MEMORY:` line) and Jack's own reply already
serves as the in-context exit/sleep-flavored line, so no separate
scripted line is needed. A second fixed phrase ("Goodnight, Jack",
also locally spotted) sends Jack from Off Watch directly to Asleep
without a conversation. None of this is implemented yet.

### 2.6 Home Automation

History: none yet.

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

History: none yet.

Jack remembers durable facts about household members (currently: Chip,
Kath, Liz — pre-seeded subsections, not auto-created), running jokes, and
stated home-automation preferences, across sessions, via a plain-markdown
memory file the model itself never writes directly. Full design in
[Memory Subsystem](#45-memory-subsystem) /
[captain-jack-memory-design.md](captain-jack-memory-design.md). Voice ID
is the *preferred* mechanism for resolving which household member is
speaking — engine chosen, not yet implemented, see [Speaker
Recognition](#415-speaker-recognition-voice-id) and [Open
Issues](#5-open-issues) issue 1; explicit self-identification is today's
working fallback, not the intended end state.

Appointment/reminder recall ("Jack remembers appointments he's been told
about and can be asked about later") is a related use case named in the
goals document but not scoped against the current memory allowlist, which
has no calendar/appointment category — see
[Open Issues](#5-open-issues).

### 2.8 Deferred and Speculative Scenarios

History: none yet.

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

History: none yet.

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
(UART, framing locked down — see
[Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link)) to the
Arduino; outbound network to the Anthropic API for each conversation turn.

### 3.2 Seeed reSpeaker XVF3800

History: [log.md#32-seeed-respeaker-xvf3800](log.md#32-seeed-respeaker-xvf3800).

**Description**: USB 4-mic array board built on the XMOS XVF3800 chip,
with onboard AEC, multi-beamforming, de-reverberation, direction-of-arrival,
and dynamic noise suppression. **Status: connected to the Pi via USB,
speaker wired to its output, playback verified by ear (2026-09-25)** —
not yet physically mounted to the statue (currently sits on a table in
front of the parrot), which may affect acoustics/DoA somewhat but doesn't
block using its real mic array or speaker output. Final AEC validation
and speaker-ID accuracy testing wait on mounting, since the
speaker-to-mic geometry will change — see CLAUDE.md's "Blocked until the
XVF3800 is mounted to the statue" list. Output headroom is limited: with
ALSA `PCM Playback Volume` at max (60/60, 0dB), audio is clean up to
about −10dBFS and audibly clips above that — see
[Open Issues](#5-open-issues) issue 26.

Verified directly against the connected board (ALSA `hw_params` on both
its playback and capture subdevices): the currently-flashed firmware
exposes a **fixed** format on both directions — `S16_LE`, 16kHz, 2
channels — not a negotiable range. Seeed also ships a 48kHz-oriented
firmware variant (aimed at Home Assistant use); reflashing to it is a
possible future option for higher output fidelity, not pursued now given
the board is already connected and working. See
[4.7](#47-text-to-speech-tts) for the resulting canonical Pi-side audio
format.

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

History: [log.md#33-speaker](log.md#33-speaker), [log.md#issue-26](log.md#issue-26).

**Description**: 40mm diameter, 4Ω, 5W speaker (the XVF3800 doesn't
ship with one). Its 5W rating matches the XVF3800's nominal 5W onboard
amp. **Status: connected** to the XVF3800's
2-pin JST speaker output (2026-09-25) and verified playing; clips above
roughly −10dBFS at max hardware volume — whether the limit is the
XVF3800's onboard amp or the speaker itself isn't yet known (see
[Open Issues](#5-open-issues) issue 26).

**Intended function**: audio output for TTS and idle/ambient clips.

**Interconnect**: the audio the speaker plays **must originate from the
XVF3800's own output** — not from a separate sound card or audio source
(e.g. the removed MY1690) — or the XVF3800's AEC has no reference signal
to cancel against, defeating the reason it was chosen. Currently wired
directly to the XVF3800's 2-pin JST speaker terminals (onboard amp). An
external amp placed *after* the XVF3800 is allowed, since the AEC
reference is the XVF3800's own internal copy of what it outputs: the
external amp should be fed from the XVF3800's 3.5mm jack, not its
speaker terminals, so the onboard amp's clipping isn't amplified along
with the signal (see [3.2](#32-seeed-respeaker-xvf3800) and
[Open Issues](#5-open-issues) issue 26).

### 3.4 Arduino Servo Controller

History: [log.md#34-arduino-servo-controller](log.md#34-arduino-servo-controller).

**Description**: a new Arduino Uno, replacing the original build's board.
**Status: connected to the Pi, wired to all four servos, and driving them
correctly.** Resting/offset/range constants for all four axes are tuned
empirically against the real mechanism — see
[Arduino Firmware](#414-arduino-firmware). The old MY1690 + electret-mic
hardware has been removed (it lived on the original board, not this one)
— see [Removed and Legacy Hardware](#37-removed-and-legacy-hardware).
It shrinks to real-time servo execution only. The real-time PWM loop
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
data anymore, unlike the original design). Command framing is locked down
— see [Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link). Servo PWM
wiring is connected — see above.

The sketch itself has been written for servo-only duty; see
[Arduino Firmware](#414-arduino-firmware).

### 3.5 Servos (Head and Beak)

History: none yet.

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

History: none yet.

**Description**: life-size 3D-printed parrot on a tree-stump perch, with a
box base beneath housing all electronics. **Status: on hand and
operational**, pre-existing this project; only head/beak articulation was
added to an originally-rigid design, and the statue may be further modified
as this project requires.

**Intended function**: the appliance's physical form factor and enclosure.

**Interconnect**: houses and physically mounts the Pi 5, XVF3800, Arduino,
servos, and speaker.

### 3.7 Removed and Legacy Hardware

History: [log.md#37-removed-and-legacy-hardware](log.md#37-removed-and-legacy-hardware).

Kept here for continuity with the original (pre-Pi) design, not part of the
current build:

- **MY1690 audio player** — SD-card-based stereo clip player. **Status:
  removed.** Superseded by Pi-side playback of local audio files through
  the XVF3800, using the same RMS-envelope extraction as live TTS (see
  [Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player)).
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
designed (to varying depth) but not yet built. The Arduino is wired and
validated ([3.4](#34-arduino-servo-controller)) and the XVF3800 is
USB-connected with the speaker wired ([3.2](#32-seeed-respeaker-xvf3800),
[3.3](#33-speaker)), so no module is waiting on hardware to start; only
final AEC and speaker-ID validation wait on mounting the board. How the
modules run together as one program — threads, what each owns, and one
full turn start to finish — is in
[Runtime Integration](#416-runtime-integration-end-to-end-turn).

### 4.1 Wake Word Spotter

History: [log.md#issue-16](log.md#issue-16), [log.md#41-wake-word-spotter](log.md#41-wake-word-spotter).

**Status: Engine chosen, not implemented.**

**Description**: local, always-on keyword spotter running on the Pi,
using **openWakeWord** — open-source, no account/network dependency at
runtime, and already validated at low CPU cost on Pi-class hardware (a
single Pi 3 core runs 15-20 concurrent openWakeWord models in real
time). Per [Sleep-Mode State Machine](#411-sleep-mode-state-machine),
this same spotter (not Haiku) is what listens for the small fixed set of
mode-transition phrases while Jack isn't On Watch — it isn't limited to
just the wake phrase.

**Intended function**: detect the wake phrase **"Ahoy, Captain Jack"**
(chosen 2026-09-20) to start a session, transitioning Off Watch/Asleep →
On Watch. Also detects the separate go-to-sleep phrase **"Goodnight,
Jack"** (Off Watch → Asleep). Both are custom, non-standard multi-word
phrases with no pre-trained model available, so each needs its own model
trained on openWakeWord's synthetic-TTS-data pipeline (matching how its
own shipped models were trained) rather than hand-tuned matching; running
two custom models simultaneously is cheap given the per-model overhead
above.

**Confidence threshold methodology — decided 2026-09-23**: exact numeric
thresholds are deliberately *not* set here — neither model is trained
yet and there's no real household ambient-audio corpus to calibrate
against, so picking a number now would be deciding on paper, same
reasoning already applied to STT's model size and the TTS bake-off.
What's decided instead:
- **Per-phrase thresholds**, not one shared number — the wake and sleep
  phrases get independently trained models with their own score
  distributions.
- **Starting point**: openWakeWord's own documented default threshold of
  0.5 (its models score each 80ms audio frame 0-1), targeting its own
  commonly-cited bar of <5% false-reject rate and <0.5 false-accepts/hour
  — an externally-validated reference point, not invented for this
  project.
- **Wake phrase biased stricter**: test starting above the 0.5 default,
  loosening only if false-rejects prove annoying in practice. A false
  *accept* here means Jack activates unprompted — more disruptive for a
  household companion than a false *reject*, which just costs repeating
  the phrase. Matches the fail-closed posture already established
  elsewhere in the project (memory's fail-closed saves, no-guessing
  self-ID fallback — see [4.5](#45-memory-subsystem)/[Open
  Issues](#5-open-issues) issue 1).
- **Sleep phrase left at the vanilla default** — an unwanted "go quiet"
  is a softer failure than an unwanted wake, so there's less reason to
  bias it.
- **Calibration rides on groundwork already planned**, not a new task:
  collecting real positive utterances (household members, varied
  distance/noise) and real negative audio (TV, ambient conversation) to
  tune against happens as part of the wake-word testing already queued
  once the board can be exercised (see `CLAUDE.md`'s work list).

**Interfaces**: listens to the XVF3800's audio stream (already usable —
see [3.2](#32-seeed-respeaker-xvf3800)); on detecting the wake phrase,
signals the
[Conversation Orchestrator](#43-conversation-orchestrator) to start a
session and hands off to [STT](#42-speech-to-text-stt). On detecting the
sleep phrase, signals the
[Sleep-Mode State Machine](#411-sleep-mode-state-machine) directly — no
Haiku call involved.

### 4.2 Speech to Text (STT)

History: [log.md#issue-16](log.md#issue-16), [log.md#42-speech-to-text-stt](log.md#42-speech-to-text-stt).

**Status: Engine chosen, not implemented.**

**Description**: local speech-to-text via **`whisper.cpp`** (Whisper),
now a firm choice — model size (tiny vs. base) still open, pending
on-device experimentation against the real XVF3800 mic: tiny runs
comfortably faster than real time on the Pi 5's CPU, base is only
borderline real-time even at 4 threads, and small already misses
real-time by roughly 2x, ruling it out outright. Utterances are segmented
before reaching whisper.cpp by **Silero VAD** (a small, fast local model,
run as a pre-pass rather than a whisper.cpp built-in) — real end-pointing
(record until speech actually ends) instead of push-to-talk or a fixed
recording window, and the standard mitigation for whisper.cpp's known
silence/noise hallucination failure mode. Deliberately **no local-LLM
cleanup stage** after transcription — considered and rejected: Haiku's
own turn already tolerates ordinary transcription noise as part of normal
language understanding, so a dedicated local corrector mostly duplicates
that at extra latency on CPU-only hardware, and the technique itself is
documented to risk paraphrasing away already-correct text except when the
underlying transcript's error rate is already high.

**Confidence/no-speech threshold methodology — decided 2026-09-23**: same
approach as the wake/sleep-phrase thresholds ([4.1](#41-wake-word-spotter)) —
mechanism and starting point decided now, specific numbers deliberately
deferred. Mechanism is whisper.cpp-native, no custom code needed: its
`whisper_full_params` already exposes `no_speech_thold` (silence
probability, reference default 0.6), `logprob_thold` (decode confidence,
default -1.0), and `entropy_thold` (repetition/hallucination-loop
detector, default 2.4) — OpenAI's own reference defaults, not invented
for this project. Numbers aren't set yet because the model size (tiny
vs. base, above) isn't chosen and there's no real household audio to
calibrate against.

This is a second, distinct layer from Silero VAD, not redundant with it:
VAD decides *when to record at all*, cheaply, before whisper.cpp ever
runs; these three thresholds catch what slips past VAD post-transcription
— a noise burst energetic enough to trigger VAD but not actual words, or
genuinely garbled speech.

Same asymmetric bias as [4.1](#41-wake-word-spotter), same direction:
start from the reference defaults and bias stricter (more willing to
discard/ask-again) rather than looser, since trusting a garbled/
hallucinated transcript and sending it to Haiku as real speech wastes an
API call and produces an immersion-breaking non-sequitur reply — worse
than a false reject, which only costs a repeat.

One STT-specific implication beyond the number itself: unlike a
wake-word false reject (invisible — the household member just tries the
phrase again), silently dropping a low-confidence segment mid-conversation
(On Watch) would read as Jack being broken, not as "didn't hear that." The
reject path needs an explicit, in-character prompt (e.g., "Arr, didn't
catch that over the wind — say again?") rather than silence — the same
kind of canned-response pattern already used for idle/Asleep clips.

Calibration rides on the same real-audio testing already queued for
wake-word groundwork (see `CLAUDE.md`'s work list), not a separate task.

**Intended function**: transcribe household speech to text for the
orchestrator during an On Watch session.

**Interfaces**: reads VAD-segmented audio from the XVF3800 (via the Pi —
already usable, see [3.2](#32-seeed-respeaker-xvf3800)); outputs
transcribed text to the
[Conversation Orchestrator](#43-conversation-orchestrator).

### 4.3 Conversation Orchestrator

History: none yet.

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
none of that wiring exists yet. In the full program its per-turn logic
is called by the Coordinator thread (see
[4.16](#416-runtime-integration-end-to-end-turn)).

### 4.4 Persona and Identity Prompt

History: [log.md#issue-2](log.md#issue-2).

**Status: Implemented, including the full persona design** —
`memory/identity.md`'s `## Persona` section, encoding the backstory,
pirate speech style, deference protocol, and conversational-intensity
fade from [Use Case 2.2](#22-persona-captain-jack-the-parrot)/
[2.1](#21-companionable-conversation). Written as concrete traits + a
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

**Persona portability**: `orchestrate.py` treats
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

History: none yet.

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
himself. Each household subsection may also carry
leading `- gender: ...` and `- honorific: ...` lines — hand-set only,
same as the heading itself, never proposed or inferred by the model, and
independent of each other (honorific is not derived from gender); see
[Open Issues](#5-open-issues) issue 3.

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

The `home` tag covers the durable-location
half of [Use Case 2.3](#23-environmental-and-self-awareness). Still doesn't
cover "current location" (deferred — see
[Possible Future Enhancements](#6-possible-future-enhancements)) or
appointment/calendar facts called for by
[Use Case 2.7](#27-personalized-memory) — see [Open Issues](#5-open-issues).

### 4.6 Home-Automation Tool Schema

History: none yet.

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

History: [log.md#issue-16](log.md#issue-16), [log.md#47-text-to-speech-tts](log.md#47-text-to-speech-tts).

**Status: Not started** — the speaker is now wired (see
[3.3](#33-speaker)), so the bake-off is unblocked; best run after
[Open Issues](#5-open-issues) issue 26's output headroom is settled, so
amp/speaker clipping doesn't skew the voice-quality comparison.

**Description**: local TTS rendering Jack's spoken reply to audio.
Candidates narrowed to two, both local/offline/no-API-key, comparably
small (Kokoro-82M vs. Supertonic-3's 99M params): **`kokoro-pi`** (a
Raspberry-Pi-optimized build of Kokoro — the same engine
[jaredrhod/backtalk](https://github.com/jaredrhod/backtalk) uses for
Jarvis, independently validated elsewhere as the best available choice
for genuinely local/edge deployment, not chosen just because Jarvis uses
it) and **Supertonic-3** (ONNX-native, competitive-or-faster than Kokoro
in CPU benchmarks, but without a confirmed Pi/ARM-specific benchmark the
way `kokoro-pi` has one). Final choice deferred to an empirical bake-off
on the real Pi rather than decided on paper — see [Open
Issues](#5-open-issues) issue 16. A clearly higher-quality option,
Chatterbox (MIT, beats ElevenLabs in blind preference tests), was
considered and set aside for now: at 0.5B params and built for GPU
inference, with no Pi-optimized port available, it doesn't fit this
project's CPU-only hardware today.

**Output format — decided 2026-09-23**: 16kHz, 16-bit signed PCM
(`S16_LE`), 2 channels (mono content duplicated across both) — the
connected XVF3800 board has a fixed, non-negotiable playback format at
exactly that spec (verified via ALSA `hw_params`, see
[3.2](#32-seeed-respeaker-xvf3800)), not a range to choose within.
Neither TTS candidate outputs this natively (Kokoro-82M: 24kHz;
Supertonic-3: 44.1kHz), so both need a resample-down step regardless of
which wins the bake-off — this isn't itself a factor in that decision.
The same canonical format applies to
[idle/ambient clips](#410-idle-and-ambient-audio-player), so
[beak-sync](#48-beak-sync-rms-envelope-extraction) has one uniform PCM
stream to process regardless of source.

Storage and processing (idle clips, beak-sync's RMS extraction, and TTS
engine output) stay **mono** throughout — the 2-channel requirement above
is purely this board's USB-audio-interface quirk, not real stereo
content (Jack has one physical speaker, see [3.3](#33-speaker)), so
duplication to 2 channels happens as a single shared step at the point
of writing to the ALSA device, not baked into stored assets or done
per-source.

**Intended function**: convert the orchestrator's spoken-text output to an
audio stream for playback through the XVF3800/speaker, feeding both the
listener and the [beak-sync](#48-beak-sync-rms-envelope-extraction) module.

**Interfaces**: consumes text from the
[Conversation Orchestrator](#43-conversation-orchestrator); outputs an
audio stream to the XVF3800 output path and to
[Beak-Sync](#48-beak-sync-rms-envelope-extraction).

### 4.8 Beak-Sync (RMS Envelope Extraction)

History: none yet.

**Status: Not started** — no hardware wait: the XVF3800 and speaker are
both connected and playing.

**Description**: real-time RMS amplitude envelope extraction from whatever
audio is currently playing — idle clip or live TTS — at roughly 30–50Hz,
replacing the MY1690's old dual-channel pre-encoded beak-track trick with
one code path for both cases. Operates on the canonical 16kHz/16-bit PCM
stream established in [TTS](#47-text-to-speech-tts) — both sources are
normalized to that one format before playback, so this module never
needs source-specific handling.

**Intended function**: produce a live beak-position value from audio
amplitude and stream it to the Arduino as `b<BB>` commands (nominal
0–45, see [4.13](#413-pi-to-arduino-serial-link)). Because
the envelope needs to be computed before playback timing catches up,
audio playback likely needs a small deliberate delay to keep beak motion in
sync — accounting for RMS processing, command generation/transmission, and
Arduino-side parsing/mechanical response time.

All beak smoothing happens here, as part of extracting the envelope itself
(attack/release-style shaping) — not as a separate easing step on either
side (see [Open Issues](#5-open-issues) issue 8). The Arduino applies the
`b` value it receives directly to PWM, no interpolation; see
[Arduino Firmware](#414-arduino-firmware).

**Interfaces**: reads the live audio stream from
[TTS](#47-text-to-speech-tts) or the
[idle/ambient player](#410-idle-and-ambient-audio-player); writes `b`
commands to the [Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link).

### 4.9 Direction of Arrival (DoA) Reader

History: none yet.

**Status: Not started** — the XVF3800 is USB-connected to the Pi, so this
needs no hardware that isn't on hand, just code and Seeed's control-tool
documentation (see `CLAUDE.md`'s work list).

**Description**: Pi-side code reading per-beam azimuth from the XVF3800 via
`xvf_host AEC_AZIMUTH_VALUES`.

**Intended function**: supply a continuous sound-direction cue that pulls
On Watch's and Off Watch's baseline yaw toward whoever's currently
talking or making noise — not a one-shot "turn to face" gesture. Asleep
deliberately doesn't use it (see
[Gesture Engine and Catalog](#412-gesture-engine-and-catalog)). Replaces
the old electret-mic-based triangulation entirely.

**Interfaces**: reads from the XVF3800 over USB; feeds the
[Gesture Engine](#412-gesture-engine-and-catalog)'s baseline-yaw tracking
for whichever mode has `doa_yaw_tracking` enabled
([gesture-catalog.yaml](gesture-catalog.yaml)).

### 4.10 Idle and Ambient Audio Player

History: [log.md#410-idle-and-ambient-audio-player](log.md#410-idle-and-ambient-audio-player).

**Status: Not started; clip library seeded; both Asleep's and Off
Watch's own behavior loops are designed (see below).** The `wavFiles/`
folder holds 19 mono, 16kHz signed-16-bit-PCM clips (converted from
their original 44100Hz 2026-09-23, per [TTS](#47-text-to-speech-tts)'s
canonical output format)
(movie lines, song snippets with music removed, etc.) plus
`AlignmentTone.wav` — a 0.5s 880Hz-tone/0.5s-silence pattern repeated 8x,
intended for measuring timing offset between audio output and beak
movement once beak-sync exists. More clips, including short recordings of
notable live Captain Jack responses, are expected to be added over time,
including after project end. Playback code itself is still unwritten.
Clips stay **mono** on disk, not the 2-channel format the XVF3800 needs
at playback time — that duplication happens once, shared, in the
playback code rather than being baked into the files. Clips are
normalized to peaks near 0dBFS, well above the ~−10dBFS clean-output
ceiling found on the real speaker, so playback needs the level handling
decided under [Open Issues](#5-open-issues) issue 26 before it'll sound
clean at full volume.

**Description**: Pi-side playback of local audio clip files (one-liners,
movie quotes, pirate sayings) during Off Watch mode, and the sparser
breathing/snore/shift clips during Asleep.

**Intended function**: drive Off-Watch and Asleep ambient behavior —
periodic playback of a clip, paired with either a random gesture or a
predefined gesture script, beak-synced via the same
[RMS envelope path](#48-beak-sync-rms-envelope-extraction) used for live
TTS.

**Asleep's behavior loop**: a plain repeating
sequence, not independent wav/gesture timers — deliberately simpler than
Off Watch's, since Asleep only has a handful of clips/gestures and
nothing in it ever needs to play at the same time as anything else (no
layering/blending question here, unlike [Open Issues](#5-open-issues)
issue 24, which remains open for On Watch):

```
On entering Asleep:
    play the going-to-sleep transition gesture (sl-settle-to-sleep) —
      always, regardless of how Asleep was entered
    if entered via the "Goodnight, Jack" phrase (Off Watch):
        play one random wav from the "goodnight acknowledgment" pool
          (context: goodnight_phrase) alongside it
    else if entered via Off Watch's 15-minute idle timeout:
        play one random wav from the "drifting off" pool
          (context: idle_timeout) alongside it
    else (entered via On Watch's nap-intent meta-tag):
        no wav — Haiku's own live reply already gave the sleep-flavored
          exit line moments earlier (see Session Boundaries, 2.5);
          playing a second canned line here would step on it

Loop:
    play the "breath" gesture (sl-idle-breathing-quiet in
      gesture-catalog.yaml) all the way through
    if wake phrase "Ahoy, Captain Jack" detected:
        play the "waking up" gesture (sl-waking-up)
        go to On Watch state
    else, with some (tunable) chance:
        play one random extra gesture from {sl-snore, sl-snort,
          sl-micro-twitch-quiet ("shift to get comfortable")}
        if wake phrase detected: play "waking up", go to On Watch
    # otherwise loop back to the next breath
```

The wake-phrase check happens only *between* completed gestures, never
mid-playback — nothing here needs true interruption (see issue 24),
since everything is a few seconds long at most. Playing "waking up" in
full before actually transitioning is deliberate, not a latency
compromise: a real animal is slow to react right out of sleep, so the
delay reads as in-character. `sl-settle-to-sleep` deliberately runs
longer (~2.3s: yawn, release the stretch, a tuck toward one side —
loosely evoking the head-under-wing stereotype, which the fixed-wing
build can't actually do — then a droop that isn't forced back to
neutral, physically continuous either way since ServoEasing always
eases from wherever the servo actually is, not from a stored baseline)
than `sl-waking-up`'s ~530ms startle, matching how falling asleep is
gradual while waking is a quick reflex. `sl-snore` is a slow pitch lift
with a little beak movement, settling back; `sl-snort` is snappier — a
small twitch, a sharp pitch jerk, a beak flap, then resettle. All of
Asleep's named gestures are now wired to a real `sl-*` id in
[gesture-catalog.yaml](gesture-catalog.yaml).

`sl-settle-to-sleep`'s two wav pools (lines not yet recorded — see
`wavs.asleep` in [gesture-catalog.yaml](gesture-catalog.yaml)):
- **`idle_timeout`** — unprompted, Jack narrating to himself, nobody to
  address: "Eight bells... my watch is done." / "Furl the sails, Cap'n's
  turnin' in." / "Even an old parrot's got to perch and rest sometime."
  / "Droppin' anchor for the night, mateys." / a trailing mumble that
  doesn't resolve into a full sentence, e.g. "Mmph... 'nother day
  done..."
- **`goodnight_phrase`** — a direct reciprocal reply to whoever just
  said "Goodnight, Jack," generic since there's no speaker ID (same
  "Matey" default as the honorific system, [Open Issues](#5-open-issues)
  issue 3): "Goodnight, Matey." A short courtesy reply tolerates
  repetition much better than a personality monologue does — real
  people say "goodnight" the same way every night without it reading as
  stale — so one line may be enough here, but "'Night, Matey — sleep
  tight" and "Sweet dreams, ye scallywag" are on hand if more variety is
  wanted later.

A grumbling-about-being-woken line is a candidate for `sl-waking-up`'s
wav pairing, not yet tackled.

One open question noted
in the catalog: `sl-settle-to-sleep`'s roll tuck will ease back toward
upright over breath's own oscillation (which is centered on a fixed
`resting`, not wherever the tuck left off) — worth watching once this
can actually run.

**Off Watch's (and On Watch's) behavior loop**: not Asleep's plain
sequence — both Off Watch and On Watch use the **ambient/excursion
model** described in
[Gesture Engine and Catalog](#412-gesture-engine-and-catalog): a
designated ambient gesture runs continuously as the default state (Idle
Breathing for Off Watch, Attentive Sway for On Watch —
[gesture-catalog.yaml](gesture-catalog.yaml)'s `ambient:` map), its
baseline drifting with live DoA yaw rather than sitting at a fixed point
([DoA Reader](#49-direction-of-arrival-doa-reader)), and excursion
gestures/wavs are chosen at random intervals to briefly interrupt it,
handing control back to the ambient gesture's own next step when they
finish rather than snapping to a stored constant.

**Off Watch excursion tuning**: a random interval of 30-90 seconds
between completed ambient-motion steps (`excursion_interval_seconds` in
[gesture-catalog.yaml](gesture-catalog.yaml)), plus a rule never to pick
the same excursion id twice in a row — an explicit starting point to
tighten as the gesture library grows, not a final number.

**Interfaces**: outputs audio through the XVF3800; feeds
[Beak-Sync](#48-beak-sync-rms-envelope-extraction); triggers the
[Gesture Engine](#412-gesture-engine-and-catalog); orchestrated by whatever
implements the [On Watch/Off Watch/Asleep mode logic](#411-sleep-mode-state-machine),
which doesn't yet exist as a discrete module.

### 4.11 Sleep-Mode State Machine

History: [log.md#issue-5](log.md#issue-5), [log.md#issue-6](log.md#issue-6).

**Status: Transition design specified; not implemented.**

**Description**: the mode-transition logic among the three
[Operational Modes](#24-operational-modes). This section covers
transitions only — each mode's own internal behavior (Off Watch's idle
catalog, Asleep's quieter subset, On Watch's conversation loop) is
specified elsewhere ([4.10](#410-idle-and-ambient-audio-player),
[4.12](#412-gesture-engine-and-catalog),
[4.3](#43-conversation-orchestrator)).

Key design principle: the local, always-on
[Wake Word Spotter](#41-wake-word-spotter) only needs to listen for a
small fixed set of exact phrases, and only while Jack **isn't** On
Watch — while On Watch, Haiku is already in the loop for every turn, so
mode-exit intent is read from the model's own understanding of whatever
phrasing a household member actually used (a meta-tag on the reply,
same mechanism as the `MEMORY:` line — see
[Memory Subsystem](#45-memory-subsystem)), not a second fixed-phrase
listener running in parallel. This keeps the zero-marginal-cost local
spotter simple while still tolerating varied phrasing where it matters
(mid-conversation), consistent with the project's local-spotting-only,
network-for-the-LLM-turn-only principle (see `CLAUDE.md`).

**Transitions:**

- **→ On Watch**
  - From Off Watch or Asleep: wake phrase **"Ahoy, Captain Jack"**
    detected by the local spotter. Same phrase from either mode — Asleep
    always wakes directly into a full conversation, never into Off
    Watch first (Chip's call: no reason to pass through ambient idle
    behavior on the way out of a nap).
- **→ Off Watch**
  - From On Watch: no fixed phrase. Haiku recognizes session-end intent
    from natural phrasing (e.g. "Thanks, Jack, that's enough," "Goodbye,
    Jack," or any equivalent) and emits an end-session meta-tag with its
    reply; that reply *is* the in-context exit line — see
    [Session Boundaries](#25-session-boundaries). No transition into Off
    Watch from Asleep exists (see Asleep, below).
  - From On Watch, also on a **2-minute no-prompt timeout**. The clock
    starts when Jack's reply (including TTS playback) finishes, not when
    the household member's last prompt was received — so a slow reply
    doesn't eat into the timeout window. **Not yet validated against a
    real long-form reply** (see the deferred community-lecture scenario,
    [2.8](#28-deferred-and-speculative-scenarios)).
- **→ Asleep**
  - From On Watch: no fixed phrase, same meta-tag mechanism as the Off
    Watch exit above, but for nap/sleep intent (e.g. "Time for a nap,
    Jack," "Go to sleep, Jack.") — reply carries the sleep-flavored exit
    line.
  - From Off Watch: fixed phrase **"Goodnight, Jack"**, detected by the
    local spotter (no Haiku call).
  - From Off Watch, also on an **idle timeout of 15 minutes** with no
    wake phrase detected.

Timeout values (2 minutes On Watch, 15 minutes Off Watch) are Chip's
initial numbers, not yet tuned against real use. Still undefined: exact
match/variant tolerance for the two fixed phrases (see
[Wake Word Spotter](#41-wake-word-spotter)), and the Asleep-specific
gesture/sound catalog subset (see [Open Issues](#5-open-issues) issue 5).

**Intended function**: own overall mode state, gate which of
[Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player)'s
catalogs is active, and hand off to/from the
[Wake Word Spotter](#41-wake-word-spotter) and
[Conversation Orchestrator](#43-conversation-orchestrator) on transitions.

**Interfaces**: sits "above" the orchestrator, wake-word spotter, and
idle player, coordinating all three — runs in the Coordinator thread (see
[4.16](#416-runtime-integration-end-to-end-turn)); not yet implemented.
`orchestrate.py` today only implements the On Watch conversation loop in
isolation.

### 4.12 Gesture Engine and Catalog

History: [log.md#412-gesture-engine-and-catalog](log.md#412-gesture-engine-and-catalog).

**Status: Content drafted, not implemented.**

**Description**: a library of named motion primitives (speech-driven,
emotional, idle, conversational, and "expressive" categories) — each a
short timed sequence of pitch/roll/yaw/beak targets — drafted in
[gesture-library.md](gesture-library.md).

Gestures are stored and composed on the **Pi**, not the Arduino, to keep
the Arduino as thin as possible (see [Open Issues](#5-open-issues) issue
7) — the catalog lives in `gesture-library.md`/its eventual code form,
entirely Pi-side. The Arduino never sees a gesture as a named unit, only
the same primitive timed servo commands it always takes. A consequence:
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
of `p`/`r`/`y`/`t`/`s` and `b` commands over the
[serial link](#413-pi-to-arduino-serial-link), per
[Arduino-command-structure.md](Arduino-command-structure.md) — never a
single opaque `GESTURE <id>`.

**Data structures**:

- **Gesture Library**: one array of Gestures each for **On Watch**,
  **Off Watch**, and **Asleep**, plus a fourth, separate **Wav-Paired**
  library — gestures scripted to accompany one specific wav clip's
  timing, a distinct *purpose* from the three mode libraries, not a
  fourth mode.
  - **Gesture**: `id` (stable, assigned once, never reused), human-
    readable name/description, array of **Move**.
  - **Move**: signed per-axis deltas (`dp`/`dr`/`dy`, each relative to a
    live **baseline** pose, not a fixed resting position — see below;
    omitted = 0, i.e. matches baseline on that axis), an optional
    absolute `beak` value (0-60; omitted = don't touch the beak, which is
    normally RMS-driven, not gesture-driven), a duration `t` (ms), and a
    `wait_ms` before advancing to the next Move or exiting the gesture.
    Not a literal Arduino command string — see "Baseline and
    the ambient/excursion model" below for why.
- **Wav Library**: one array of Wavs each for On Watch, Off Watch, and
  Asleep (no Wav-Paired variant — that would be circular).
  - **Wav**: filename of the clip to play (path to `wavFiles/` stored
    separately), the `id` of the Wav-Paired Gesture to play alongside it
    (empty/`null` means none — an integer sentinel like -1 no longer
    fits now that Gestures are id-keyed, not index-keyed), and an
    optional `context` tag distinguishing which
    Wavs paired to the *same* gesture apply to which trigger — e.g.
    several Wavs can all pair to `sl-settle-to-sleep` while only being
    valid for one specific way Asleep was entered. Most Wavs won't need
    it at all; it only matters where a gesture's wav pairing depends on
    context, which right now is only true for `sl-settle-to-sleep` (see
    [Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player)).

**Baseline and the ambient/excursion model**: baseline tracks the ambient
gesture's own live center rather than a fixed resting position, so a
sequence of gestures composes without drifting into a servo's physical
travel limit.

Applied uniformly to all three mode libraries:
- Each mode has exactly one designated **ambient gesture** (see
  `ambient:` in [gesture-catalog.yaml](gesture-catalog.yaml)) that the
  engine treats as its default/base state — it never "finishes"; the
  engine just keeps re-triggering it whenever nothing else is queued.
  Everything else in that mode's library is an **excursion**: it
  temporarily takes over, and once its own Move list ends, control
  simply resumes the ambient gesture's next step. This is still
  sequential, not concurrent — the Arduino only ever has one eased move
  in flight — so this doesn't reopen [Open Issues](#5-open-issues) issue
  24, which stays scoped to true simultaneous layering/blending
  (currently still only a live question for On Watch — see
  [Idle and Ambient Audio Player](#410-idle-and-ambient-audio-player)).
- **Baseline is the ambient gesture's own current center**, not a stored
  constant. Baseline yaw is pulled toward the live DoA azimuth wherever
  `doa_yaw_tracking` is true for that mode (On Watch and Off Watch, not
  Asleep — a sleeping bird isn't meant to track household noise; see
  [DoA Reader](#49-direction-of-arrival-doa-reader)). Baseline pitch/roll
  has no DoA input and only moves via the ambient gesture's own gentle
  oscillation, centered on `resting` as a fallback before anything has
  nudged it.
- The engine composes the real wire string only at send time:
  `P = clamp(baseline.pitch + dp, 0, 50)`, and likewise for roll/yaw —
  meaning a gesture's authored delta is the *original* magnitude from
  gesture-library.md, and how much of it actually lands depends on
  where baseline is right now, not a value pre-clamped against an
  assumed-resting baseline.
- Most excursions still end with an explicit delta-(0,0,0) Move for
  tight control over how fast they snap back — but "back" now means
  "current baseline," which is always drifting, not a hardcoded number.
  A few gestures (Look Back) don't need a separate return move at all,
  because "recover to baseline" is already their described motion.
- Off Watch's Ambient Scanning is an ordinary (larger) excursion, not a
  special case.
- Turn Toward Speaker is realized via continuous DoA-tracked baseline yaw
  plus a deliberate, fixed-delta *emphasis* turn layered on top (e.g.
  noticeably acknowledging a new speaker) — not runtime parameterization.
  Vowel Drift is unrelated (duration tied to live TTS phoneme timing) and
  is marked `NEEDS-RUNTIME-PARAM` (see Known gaps below), still open.

Other design decisions:
- Gestures usable in more than one mode are **duplicated** into each
  mode's library rather than shared via a common catalog + per-mode
  allowlist. Deliberate: the system isn't memory-constrained, and
  duplication is the simpler structure to author and reason about.
- Gestures are referenced by a stable **id**, not array position —
  chosen specifically so hand-editing/reordering a library over time
  can't silently repoint a Wav's paired-gesture reference the way an
  index would.
- The Move's `wait_ms` is **intentionally independent of** (and
  typically ≥) its own `t` duration — not a redundant encoding of the
  same number. Two reasons: (1) it avoids the engine ever needing to
  parse timing back out of something it already knows the timing of at
  authoring time, and (2) the
  [serial link](#413-pi-to-arduino-serial-link) is one-directional with
  no Arduino→Pi "done" acknowledgment, and whether the ServoEasing
  library ignores a new command sent before the previous easing
  finishes, or instead interrupts it, is unverified either way — so the
  wait is a deliberate safety margin, not just an optimization. Directly
  relevant to [Open Issues](#5-open-issues) issue 24.

Known gaps, left for a later pass (not blocking this one):
- No representation for frequency-based oscillation (e.g. "Excited Bob,"
  4–6Hz) — still hand-unrolled into repeated fixed Moves, so a gesture
  plays identically every time.
- No machine-matchable selection tag on Gesture beyond the human-readable
  name/description — this section's own "Intended function" above lists
  four trigger sources (DoA, text content/tags, random idle selection,
  explicit request); picking a gesture programmatically from any of
  those will eventually need more structure than a free-text name.
- "Vowel Drift" still can't be expressed as static data — its duration is
  real TTS phoneme timing, not knowable at authoring time. Still marked
  `NEEDS-RUNTIME-PARAM`.

Every entry in [gesture-library.md](gesture-library.md) is translated
into this structure — see [gesture-catalog.yaml](gesture-catalog.yaml).

### 4.13 Pi to Arduino Serial Link

History: [log.md#issue-9](log.md#issue-9).

**Status: Command syntax locked down, servo actuation validated.**
Implemented in `arduino/ServoControl/ServoControl.ino` and code-reviewed
(see [Open Issues](#5-open-issues) issue 21) — the wire format below is
settled; further testing is expected to refine implementation details
(calibration offsets, exact timing bounds), not the syntax itself.

**Description**: one-directional serial protocol, Pi → Arduino only (no
upstream sensor relay in the new design):

- Variable-length, self-delimiting integers — no fixed field width, no
  zero-padding. Each field is a command-type character immediately
  followed by a variable-length decimal integer, terminated by whatever
  non-numeric character follows (typically the next command character,
  or a line terminator). No spaces, no literal `HEAD`/`BEAK`/`GESTURE`
  keyword — the leading character *is* the command type, same principle
  as the superseded fixed-width design, just without the fixed width:
  - **Beak position**: `b<BB>` — moves the beak servo immediately on
    receipt, no easing (per [Open Issues](#5-open-issues) issue 8). `BB`
    is a nominal 0–45 value, clamped, then offset in firmware onto the
    physical 80–125 PWM range.
  - **Head motion axes**: `p<PP>` (nominal 0–60), `r<RR>` (nominal 0–60),
    and `y<YY>` (nominal 0–90) each stage a pitch/roll/yaw target —
    clamped, then offset in firmware onto their physical PWM ranges —
    without moving anything yet. `t<TTTT>` (0–9999ms, clamped) stages
    the move duration. Any of `b`/`p`/`r`/`y`/`t` can arrive
    individually or concatenated on one line, in any order; repeating
    one before the move is triggered overwrites the staged value
    rather than moving anything.
  - **Move trigger**: `s` — starts an eased, synchronized pitch/roll/yaw
    move to the currently staged targets over the currently staged
    duration. Sending `s` alone repeats the last staged move. `b` is
    independent of `s` and never eased, per Open Issues issue 8.
  - Any character that isn't a recognized command char or digit
    (including `\r`/`\n` and stray digits not immediately following a
    command char) is simply discarded — the stream is self-resyncing by
    construction, so there's no positional/framing state to get out of
    sync, unlike the fixed-width proposal it replaced.
  - Per-axis nominal ranges and their offsets onto the physical PWM range
    are now pinned by the constants in
    `arduino/ServoControl/ServoControl.ino`: beak 0–45 → 80–125, pitch
    0–60 → 60–120, roll 0–60 → 60–120, yaw 0–90 → 45–135.
  - `GESTURE <id>` is still dropped entirely, not just superseded in
    wording: gesture storage lives on the Pi (issue 7), so the
    Arduino never receives anything but the primitives above, whether a
    given line came from a gesture sequence, DoA, or beak-sync makes no
    difference to it.
- Worst-case transmission time and ACK/timeout-retry are accepted as
  non-blocking — see [Open Issues](#5-open-issues) issue 9.
- Gesture interruptibility/preemption vs.
  queuing and layering/blending are **not** link-level or Arduino-level
  concerns. Each line the Arduino receives is acted on immediately, as
  soon as it arrives — the Arduino has no queue, no concept of "gesture"
  as a unit, and nothing to preempt (per
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

History: [log.md#issue-21](log.md#issue-21), [log.md#414-arduino-firmware](log.md#414-arduino-firmware).

**Status: Implemented and validated against real actuation** —
`arduino/ServoControl/ServoControl.ino`, written by Chip. `arduino/TestBlink/TestBlink.ino`
is a minimal onboard-LED blink sketch used earlier to confirm the
`arduino-cli` toolchain — see [Arduino Servo
Controller](#34-arduino-servo-controller).

**Description**: the real-time sketch that parses incoming serial
commands and drives the four servos, layering the ServoEasing library
over the standard Arduino servo library for smooth, synchronized head
motion (gestures are just `p`/`r`/`y`/`t`/`b`/`s` command sequences from
the Pi — see
[Gesture Engine and Catalog](#412-gesture-engine-and-catalog) — not a
distinct command type).

**Intended function**: execute `p`/`r`/`y`/`t`/`b`/`s` commands from the
Pi at a real-time loop rate no slower than the servos' 20ms PWM period,
easing pitch/roll/yaw transitions together (cubic easing, kept to integer
math where possible for speed) once triggered by `s`. Beak (`b`) is
applied directly to PWM with **no** easing — that smoothing is done
Pi-side, in [Beak-Sync](#48-beak-sync-rms-envelope-extraction) — see
[Open Issues](#5-open-issues) issue 8. Notably must **not** reintroduce
SoftwareSerial alongside the easing library without further research. The
beak servo is attached as a plain `Servo` rather than `ServoEasing` (it was
only ever driven via `.write()`, never eased).

**Interfaces**: reads the
[Pi-to-Arduino Serial Link](#413-pi-to-arduino-serial-link); writes PWM to
the [head and beak servos](#35-servos-head-and-beak) — wired and
validated, see [Arduino Servo Controller](#34-arduino-servo-controller).

### 4.15 Speaker Recognition (Voice ID)

History: [log.md#issue-1](log.md#issue-1), [log.md#415-speaker-recognition-voice-id](log.md#415-speaker-recognition-voice-id).

**Status: Engine chosen, not implemented.**

**Description**: the software half of tier 1 in [Use Case
2.7](#27-personalized-memory)'s speaker-resolution priority (see [Open
Issues](#5-open-issues) issue 1) — a local speaker-embedding model
identifying which enrolled household member (Chip, Kath, or Liz) is
currently speaking, without requiring self-identification. Engine:
**ECAPA-TDNN**, the standard speaker-verification architecture since 2020
and still current; start with a mainstream pretrained implementation
(e.g. SpeechBrain's `spkrec-ecapa-voxceleb`) for the prototype, moving to
a purpose-trained tiny variant (ECAPA-TDNNLite/TinyECAPA-class, roughly
150k-320k params) only if real compute pressure shows up in practice —
the same ship-the-known-good-stock-thing-first, optimize-later approach
used for the Arduino's ServoEasing library. Considered and rejected:
Picovoice's Falcon, which solves a different problem (speaker
*diarization* — anonymous "who spoke when" turn segmentation, no
enrollment or identity matching) and is the same vendor whose Porcupine
free tier was discontinued, making it a poor fit twice over.

**Intended function**: enroll each household member once (a short
reference recording → one stored embedding vector per person); at
runtime, extract an embedding from each VAD-segmented utterance (see
[STT](#42-speech-to-text-stt)) and compare it by cosine similarity
against the enrolled vectors — the best match above a confidence
threshold resolves who's speaking, and below it falls through to tier 2
(explicit self-identification, already implemented) per Issue 1's
existing fail-closed design. Enrollment happens rarely and can afford a
larger, slower model; runtime verification happens on every utterance and
needs the cheap one — an asymmetric enroll/verify split already
established in the speaker-verification literature.

**Enrollment flow — decided 2026-09-23**:
- **Trigger**: a standalone script (e.g. `enroll_speaker.py <name>`), run
  directly, not an in-conversation voice flow. Matches the project's
  ship-the-simple-thing-first pattern (stock ServoEasing before trimming
  it, stock Kokoro before chasing the tiniest variant) and keeps
  enrollment out of the core conversation loop's scope while that loop
  isn't working yet, consistent with home-automation also being
  deliberately deferred for the same reason. An in-conversation "Jack,
  enroll my voice" flow is a reasonable future enhancement, not the MVP.
- **Closed set**: only names with a pre-existing `### Name` heading in
  `memory.md` (Chip, Kath, Liz) can be enrolled — the same rule already
  governing household memory facts (Jack/the tooling never mints a new
  household member; see [Memory Subsystem](#45-memory-subsystem)),
  applied here too.
- **Multiple enrollment utterances, not one**: research on this exact
  setup shows Equal Error Rate dropping from ~17.6% at a single
  enrollment utterance to ~8% at five or more, using the mean (centroid)
  of the individual embeddings as the stored profile, with roughly 20
  seconds of total speech as practical guidance. The script should
  prompt for ~5 short, varied utterances and store their averaged
  embedding, not a single-shot recording.
- **Storage: separate from `memory.md`, not folded into it.** Embeddings
  are opaque 192-256-dimension float vectors — the opposite of
  `memory.md`'s plain-markdown, human-readable, hand-editable design
  contract. They live in their own small data store, keyed by the same
  name used in `memory.md`, written only by the enrollment script and
  read only by orchestration code at runtime — never touched by Haiku
  directly, same as `memory.md`'s own file I/O being orchestration-owned
  rather than delegated to the model.
- **Re-enrollment is free**: re-running the script for a name overwrites
  their stored embedding; no separate design needed for a bad initial
  enrollment or a voice changing over time.
- **Explicitly out of scope here**: the runtime match-confidence
  threshold (how close a cosine-similarity score needs to be before
  trusting a match vs. falling through to tier 2) is a separate decision
  from enrollment flow, not yet made — expected to get the same
  methodology-now/numbers-from-real-testing treatment as
  [4.1](#41-wake-word-spotter)/[4.2](#42-speech-to-text-stt) when it's
  tackled.

**Interfaces**: reads VAD-segmented audio alongside
[STT](#42-speech-to-text-stt) — the XVF3800's mic array is already
electrically usable for this, see [3.2](#32-seeed-respeaker-xvf3800);
resolves a speaker identity for the [Conversation
Orchestrator](#43-conversation-orchestrator) to use when addressing
[Memory Subsystem](#45-memory-subsystem) facts.

### 4.16 Runtime Integration (End-to-End Turn)

History: [log.md#416-runtime-integration-end-to-end-turn](log.md#416-runtime-integration-end-to-end-turn).

**Status: Designed 2026-09-25; build steps 1-2 (Playback, Capture)
implemented** — `playback.py` and `capture.py`, verified on the real
board 2026-09-25.

**Description**: how the modules in 4.1–4.15 run together as one
program. Each module section above states its own interfaces; this
section describes a whole turn from start to finish, and which part of
the program owns each shared resource.

**Process model — decided 2026-09-25**: one Python process with a small
fixed set of long-lived threads, each owning one resource, handing data
to each other only through thread-safe queues (no shared mutable state
beyond the current mode). Heavy compute (whisper.cpp, openWakeWord,
TTS) runs inside native libraries that release Python's interpreter
lock, so threads genuinely run in parallel where it matters.

```
 mic ─► Capture ─► Listener ─► Coordinator ─► TTS ─► Playback ─► speaker
          (a)   frames (b) events (c)  sentences (d) audio (e)
                                  │                    ▲    │ b<BB>
                                  │ mode    idle clips │    ▼
                                  └──► Motion & idle ──┘  Serial ─► Arduino
                                           (g) ── p/r/y/t/s ─► writer (f)
```

**Threads and what each owns:**

- **(a) Capture** — sole reader of the XVF3800's capture device (fixed
  16kHz/S16_LE/2ch, see [3.2](#32-seeed-respeaker-xvf3800)). Keeps one
  of the two channels (which one carries the XVF3800's processed voice
  output is not yet determined — a record-and-compare test) and emits
  mono 80ms frames (1280 samples, openWakeWord's native frame size) to
  the Listener. **Channel 1 chosen 2026-09-25**: channel 0 is more
  heavily processed (automatic gain drove a normal speaking voice into
  digital clipping, and noise suppression gates the background after
  speech); channel 1 has steady levels and headroom, and sounded cleaner
  by ear. Seeed's documentation of what each channel carries is still
  missing (see CLAUDE.md work list item 7). Never stops reading, even while input is being ignored,
  so the device buffer can't overrun.
- **(b) Listener** — turns frames into events for the Coordinator.
  Behavior depends on the current mode: in Off Watch/Asleep it runs
  [openWakeWord](#41-wake-word-spotter) and posts *wake* or
  *sleep-phrase* events; in On Watch it runs
  [Silero VAD](#42-speech-to-text-stt), assembles one complete utterance
  (including a short pre-roll buffer, so the first syllable isn't
  clipped by VAD's detection lag), and posts it as an *utterance* event.
  **Turn-taking, not barge-in (decided 2026-09-25)**: while anything is
  playing, and for a short hold-off after playback ends (room echo
  tail, length to be tuned), the Listener discards frames rather than
  acting on them — in every mode, including idle clips in Off Watch.
  Interruption is a possible later addition once AEC has been validated
  on the mounted board (see [Possible Future
  Enhancements](#6-possible-future-enhancements)).
- **(c) Coordinator** (main thread) — owns the mode (the
  [Sleep-Mode State Machine](#411-sleep-mode-state-machine)) and runs
  the On Watch turn in sequence, blocking while it works (nothing else
  needs it meanwhile, since the Listener is ignoring input while Jack
  speaks):
  1. utterance → [STT](#42-speech-to-text-stt) (whisper.cpp + its
     confidence thresholds). A reject plays an in-character "say again"
     clip instead of calling Haiku.
  2. (later) same utterance audio → [speaker ID](#415-speaker-recognition-voice-id).
  3. transcript → the [Conversation Orchestrator](#43-conversation-orchestrator)'s
     turn function → spoken reply + optional `MEMORY:` proposal +
     optional end-session/nap meta-tag (the meta-tag isn't implemented
     yet in `orchestrate.py`). Memory is saved here, in orchestration
     code, as today.
  4. spoken reply → split into sentences → queued to TTS.
  5. if the reply carried a meta-tag, switch mode once its playback
     finishes; otherwise start On Watch's 2-minute no-prompt timer when
     the last sentence finishes playing (per 4.11).
  The orchestrator's per-turn logic, currently inline in
  `orchestrate.py`'s `main()`, gets factored into a callable turn
  function; the text CLI stays as a thin wrapper around it for testing
  without audio.
- **(d) TTS** — takes sentences one at a time, synthesizes each, and
  resamples to the canonical 16kHz mono (see
  [4.7](#47-text-to-speech-tts)), queuing each finished sentence to
  Playback. **Sentence by sentence (decided 2026-09-25)**: sentence 1
  starts playing while sentence 2 is being synthesized, so the wait
  before Jack starts talking is roughly one sentence's synthesis time,
  not the whole reply's.
- **(e) Playback** — sole writer to the XVF3800's playback device. Takes
  mono 16kHz buffers from any source (TTS sentences, idle clips, canned
  clips) through one queue and plays them in order. Per output block it
  applies the output gain cap (see below), computes the
  [beak-sync](#48-beak-sync-rms-envelope-extraction) RMS value and sends
  a `b<BB>` command to the Serial writer, then duplicates mono to the
  device's 2 channels and writes it — the "one shared step at the ALSA
  write" from 4.7, and the one place every played sound passes through.
  Beak commands are delayed by the measured device output latency so
  the beak moves when the sound actually leaves the speaker
  (calibrated with `AlignmentTone.wav`). Posts *playback started* and
  *playback finished* events, which drive the Listener's gating and the
  Coordinator's timers.
- **(f) Serial writer** — sole owner of the Arduino serial port. Accepts
  command strings from Playback (beak) and Motion (head) and writes
  them. Beak commands are latest-wins: if several queue up, only the
  newest is sent, since a stale beak position is worse than a skipped
  one.
- **(g) Motion & idle** — runs the current mode's gesture behavior from
  [gesture-catalog.yaml](gesture-catalog.yaml) (the ambient/excursion
  loops `exercise_hardware.py` prototypes today) and, in Off
  Watch/Asleep, schedules idle clips into the Playback queue per
  [4.10](#410-idle-and-ambient-audio-player). Later, DoA-driven
  baseline yaw ([4.9](#49-direction-of-arrival-doa-reader)) feeds in
  here. Switches catalogs when the Coordinator changes mode.

**Output gain cap — interim, decided 2026-09-25**: until
[Open Issues](#5-open-issues) issue 26 is fixed, Playback scales every
sample by a fixed −10dB (×0.316), with the XVF3800's ALSA `PCM Playback
Volume` at max (60/60). Since clips and TTS peak near 0dBFS, that holds
output at or below −10dBFS — step 2 of the level ladder, the loudest
level heard clean through the onboard amp. A plain fixed gain, not a
limiter; revisit when issue 26 is resolved.

**First build — a stand-in for the wake word**: until the custom
openWakeWord models for "Ahoy, Captain Jack" and "Goodnight, Jack" are
trained (see [4.1](#41-wake-word-spotter)), a keyboard trigger (Enter
in the terminal) posts the same *wake* event the Listener would. Because
it's just another source of the same event, swapping in the real
spotter later changes nothing downstream.

**Build order** (each step runnable and testable on its own):
1. Playback thread: gain cap + mono→2ch; play a `wavFiles/` clip.
   **Done** — `playback.py` (PortAudio via `sounddevice`, callback
   mode, 20ms blocks).
2. Capture thread; determine which of the two capture channels to use.
   **Done** — `capture.py`, channel 1. Runs alongside Playback on the
   same board, sharing one stream clock.
3. Listener VAD + whisper.cpp: print transcripts of spoken utterances.
4. Coordinator with the keyboard wake stand-in: speak → transcript →
   Haiku turn → printed reply (orchestrator turn function factored out).
5. TTS thread (`kokoro-pi` to start, pending the bake-off), sentence by
   sentence — the thin end-to-end voice loop is complete here.
6. Beak-sync in Playback + Serial writer.
7. Motion & idle thread, state machine and timeouts, real wake-word
   models.

**Interfaces**: this section *is* the wiring between 4.1–4.15; each
module's own Interfaces paragraph remains the source for what it
consumes and produces.

## 5. Open Issues

History: [log.md#open-issues-history](log.md#open-issues-history).

Full resolution history, rationale, and alternatives considered for every
issue below — including the ones still marked open here — live there,
keyed by issue number. Issue numbers are permanent identifiers, assigned
once and never reused or renumbered; a resolved issue keeps its number
and is tagged **[RESOLVED]** in place.

1. Resolving who's speaking uses a three-tier priority: (1) voice ID —
  preferred; software engine chosen (ECAPA-TDNN speaker embeddings, see
  [4.15](#415-speaker-recognition-voice-id)), not yet implemented, with
  final accuracy still pending the XVF3800's scheduled accuracy test —
  though prototyping itself isn't hardware-blocked, since the board's mic
  array is already electrically functional (only its physical mounting is
  outstanding); (2) explicit self-identification — today's working
  fallback, fail-closed by design, workable but untested against real
  conversation at length; (3) contextual inference — not implemented, in
  tension with the project's fail-closed memory principle, the riskiest
  tier. **Left open**: whether tier 1 works well enough that tiers 2–3
  rarely matter in practice is an empirical question for the XVF3800
  test, not a design question. History: [log.md#issue-1](log.md#issue-1).
2. **[RESOLVED]** Persona and Identity Prompt was a minimal stub, missing
  backstory, pirate speech style, deference protocol, and
  conversational-intensity fade. History: [log.md#issue-2](log.md#issue-2).
3. Gendered deference phrasing ("Captain" vs. "Mistress") is resolved via
  explicit, hand-set `gender`/`honorific` facts in `memory.md`, independent
  of each other (Jack never proposes or infers either) — default
  honorific for anyone unset is the gender-neutral "Matey." **Left open**,
  a genuinely harder question Chip is still thinking through: even given
  only as an explicit, narrowly-instructed fact, does gender still leak
  into broader conversational tone/word choice no instruction ever asked
  for? A real, not fully predictable LLM-behavior question — Liz's case is
  a live, deliberate test of exactly this, not yet observed in practice.
  History: [log.md#issue-3](log.md#issue-3).
4. **[RESOLVED]** No memory category existed for location/environment or
  appointment/calendar facts, though [Use Cases
  2.3](#23-environmental-and-self-awareness) and
  [2.7](#27-personalized-memory) assume Jack tracks both. History:
  [log.md#issue-4](log.md#issue-4).
5. Off Watch/Asleep behavior design: transition logic and each mode's
  behavior-loop mechanism are both designed (ambient/excursion model for
  Off Watch/On Watch, plain sequence for Asleep — see
  [4.10](#410-idle-and-ambient-audio-player)/[4.11](#411-sleep-mode-state-machine)).
  **Left open**: Off Watch's excursion-frequency tuning, and none of this
  (transitions, ambient/excursion engine, or gesture catalog) is
  implemented in code yet — only On Watch's conversation loop is. History:
  [log.md#issue-5](log.md#issue-5).
6. **[RESOLVED]** Wake word, end-session phrase, and go-to-sleep phrase
  were all unchosen — no mode-transition trigger existed. History:
  [log.md#issue-6](log.md#issue-6).
7. **[RESOLVED]** Gesture storage location (Arduino-resident vs.
  Pi-composed primitive sequences) was unresolved, blocking a final
  [serial protocol](#413-pi-to-arduino-serial-link) spec. History:
  [log.md#issue-7](log.md#issue-7).
8. **[RESOLVED]** Beak-easing ownership (Pi's RMS extraction vs. the
  Arduino's easing library vs. both vs. neither) was unresolved. History:
  [log.md#issue-8](log.md#issue-8).
9. **[RESOLVED]** The [Pi→Arduino serial
  framing](#413-pi-to-arduino-serial-link) had two unreconciled
  descriptions, plus open questions on ACK/retry, per-axis offsets, and
  worst-case transmission time. History: [log.md#issue-9](log.md#issue-9).
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
15. Test coverage is short of "one test per use case and per functional
  block" per the goals document — [tests.md](tests.md) exists with its
  first test (the `home` memory tag), but most implemented blocks (memory
  save/dedup beyond `home`, the orchestrator's conversation loop, persona/
  identity behavior) have none yet. History:
  [log.md#issue-15](log.md#issue-15).
16. **Narrowed 2026-09-23**: wake-word engine (openWakeWord) and STT engine
  (Whisper via `whisper.cpp` + Silero VAD; model size tiny vs. base still
  pending on-device experimentation) are now chosen — see
  [4.1](#41-wake-word-spotter)/[4.2](#42-speech-to-text-stt). **Narrowed
  further, same day**: TTS candidates narrowed to `kokoro-pi` vs.
  Supertonic-3 (see [4.7](#47-text-to-speech-tts)); plan of record is an
  empirical bake-off on the real Pi, judged primarily on voice quality
  per Chip's call, once the speaker is wired. **Unblocked 2026-09-25**:
  speaker wired and playing. **Left open**: which of the two wins the
  bake-off — best run after issue 26's output headroom is settled.
  History:
  [log.md#issue-16](log.md#issue-16).
17. **[RESOLVED]** Idle-audio-on-Pi tradeoff (ambient sound depends on the
  Pi being up, unlike the removed MY1690-on-Arduino design) was noted,
  unmitigated. History: [log.md#issue-17](log.md#issue-17).
18. **[RESOLVED]** Conversational-privacy/oversharing risk (a fact told by
  one household member surfacing in front of another) was listed as an
  open design question. History: [log.md#issue-18](log.md#issue-18).
19. **[RESOLVED]** The scope of "anything Haiku can do" beyond home
  automation was explicitly undefined in the goals document. History:
  [log.md#issue-19](log.md#issue-19).
20. **[RESOLVED]** Speculative scenarios (Alexa flirtation, community-
  lecture demo) were recorded but unscoped. History:
  [log.md#issue-20](log.md#issue-20).
21. **[RESOLVED]** Servo-only firmware needed to be written for the new
  Arduino Uno; couldn't be validated against real actuation until the
  board was wired to the head/beak servos. History:
  [log.md#issue-21](log.md#issue-21).
22. **Downgraded 2026-09-14, low risk per analysis, not closed** (pending
  empirical confirmation): the ATmega328P runs at 16MHz with a hardware
  8-bit multiplier; only 3 servos need easing math per update (pitch/
  roll/yaw — beak has none, per issue 8); a cubic-easing evaluation per
  axis kept to integer math (already the plan, per
  [Arduino-command-structure.md](Arduino-command-structure.md)) is on the
  order of tens of cycles — call it 100-300 cycles for all three, roughly
  10-20 microseconds. Even 10x pessimistic, that's under 1% of the 20ms
  (20,000 microsecond) budget; PWM generation itself runs on a hardware
  timer interrupt, not the main loop, and serial reception is
  interrupt-driven rather than blocking. Separately, 20ms is a 50Hz
  update rate — comfortably above typical human motion-smoothness
  perception thresholds (better than standard 24-30fps video), so there's
  good general reason to expect it reads as smooth. What this reasoning
  can't settle: whether a specific easing curve/timing/amplitude choice
  actually looks *lifelike* — that's a tuning judgment only real servo
  motion can confirm, once the board is wired (see
  [Open Issues](#5-open-issues) issue 21).
23. **[RESOLVED]** No memory category existed for appointment/calendar
  facts, split from issue 4. History:
  [log.md#issue-23](log.md#issue-23).
24. Gesture interruptibility/preemption vs. queuing, and layering/
  blending, are undesigned — purely a Pi-side
  [Gesture Engine](#412-gesture-engine-and-catalog) question, not a
  link/firmware-level one (per issue 7). **Resolved for Asleep**
  specifically — its [behavior loop](#410-idle-and-ambient-audio-player)
  is a plain sequence with no concurrency. Off Watch's ambient/excursion
  loop is also sequential, not concurrent, so it doesn't reopen this
  issue either (see [4.12](#412-gesture-engine-and-catalog)). **Left
  open** for On Watch, where true simultaneous layering/blending is
  still a live question. History: [log.md#issue-24](log.md#issue-24).
25. Small-amplitude, slow gestures (e.g. `id-idle-breathing`'s 5° pitch
  swing over 2000ms) visibly move in discrete steps on the real bird
  rather than gliding smoothly — root-caused to servo pulse-width
  resolution (~10.4 microseconds of pulse width per commanded degree on
  the pitch servo tested), not an easing bug; a real amplitude/duration/
  stepped-look design tradeoff, not a code fix. **Resolved for
  `id-idle-breathing`** via an asymmetric swing (+13°/-28°, ~41° total)
  at 1600ms, confirmed smooth on the real bird; its roll flourish was
  dropped rather than scaled up. **Left open**: `sl-idle-breathing-quiet`
  (Asleep), `sl-snore`, and other single-digit-degree/multi-second
  gestures haven't been retuned — Asleep's case is sharper, since it
  should read *quieter and slower* than Off Watch, cutting against the
  amplitude/duration fix. History: [log.md#issue-25](log.md#issue-25).
26. Speaker output headroom: with the XVF3800's ALSA `PCM Playback
  Volume` at max (60/60, 0dB), a speech clip plays clean at −10dBFS,
  starts crackling by −6dBFS, and is mostly static near 0dBFS
  (2026-09-25 listening ladder, board unmounted). −20dBFS is clean but
  very quiet. Every `wavFiles/` clip peaks near 0dBFS, and TTS output
  presumably will too, so something has to hold output below the
  clipping point. **Narrowed 2026-09-25**: the same ladder through
  headphones on the XVF3800's 3.5mm jack was clean and plenty loud at
  every step up to −3dBFS, so the digital path and DAC are fine — the
  clipping is in the speaker path (onboard amp or the speaker itself,
  40mm/4Ω/5W, see [3.3](#33-speaker)), with the onboard amp the likelier
  culprit given the speaker's 5W rating. That makes an external amp fed
  from the 3.5mm jack a strong candidate. Plugging into the jack mutes
  the onboard speaker output (confirmed the same day), so the jack and
  the speaker terminals are one or the other, never both. **Left open**: amp vs. speaker
  (a swap test with another speaker, or Chip's existing external amp,
  will settle it); which mechanism to use (a fixed digital gain cap in the
  shared mono→2ch playback step, a limiter/compressor there to keep
  loudness up, an XVF3800-side output-gain setting if Seeed's control
  tool exposes one, or an external amp fed from the XVF3800's output per
  [3.2](#32-seeed-respeaker-xvf3800)); and whether ~−10dBFS is loud
  enough in a real room. This matters for AEC too, not just sound
  quality: clipping is nonlinear distortion that the XVF3800's echo
  canceller can't model from its clean reference signal. **Interim
  (2026-09-25)**: playback applies a fixed −10dB gain with hardware
  volume at max, holding output at the ladder's clean step 2 until this
  is fixed (see [4.16](#416-runtime-integration-end-to-end-turn)). History:
  [log.md#issue-26](log.md#issue-26).

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
   - Appointment/calendar awareness (former
     [Open Issue](#5-open-issues) 23) — no memory-allowlist tag or schema
     exists for it, though [Use Case 2.7](#27-personalized-memory)
     assumes Jack tracks it; same deferral as above. **Closed as an Open
     Issue 2026-09-14, Chip's call**: keeping the current feature set
     focused gives a better chance of actually finishing it — whether
     this ends up as a new memory tag or an actual tool Jack calls,
     either is more scope than is worth taking on now.
   - Proactive mid-session behavior — Jack bringing up something on his
     own (a reminder, a follow-up) rather than only ever responding. Not
     deferred the same way as the above — just unscoped.
3. **Speculative demo scenarios.** Recorded for continuity, not designed
   or scheduled — see
   [Use Case 2.8](#28-deferred-and-speculative-scenarios)/former
   [Open Issue](#5-open-issues) 20. Discussed 2026-09-14:
   - **Alexa flirtation easter egg**: cheapest version is a scripted
     one-liner in the existing idle-audio catalog
     ([4.10](#410-idle-and-ambient-audio-player)) — needs no new
     capability. Concrete risk: if the line literally says "Alexa" as
     its first word, a real Amazon Echo in the house could start
     listening/responding to it as its actual wake word, turning the
     joke into Jack accidentally addressing a real device — write around
     that, or test against a real Echo before shipping. If the intent is
     instead for Jack to notice a lull and speak up unprompted, that's
     the same "proactive mid-session behavior" idea already listed in
     item 2 above, not a separate problem.
   - **Community lecture demo**: three concrete issues, not just
     undiscussed:
     - Network provisioning is a real failure mode, not just a TBD —
       there's no on-device WiFi UI (SSH or a keyboard/monitor only),
       and a venue's captive-portal guest WiFi can't be completed
       headless at all. A live demo depending on venue WiFi risks
       silent API failure on stage; default to a cellular hotspot as
       the plan, not a fallback.
     - `orchestrate.py`'s `MAX_TOKENS = 1024` caps every reply to
       roughly 750-800 words — incompatible with sustained monologue
       delivery as-is. Would need either raising it (cost/latency
       tradeoff) or restructuring into a scripted multi-turn sequence,
       which undercuts the "lecture" format the idea was going for.
     - Interacts with [Open Issues](#5-open-issues) issue 18 (closed):
       that closure accepted conversational-privacy risk in a
       *household* context. A public audience of strangers is a
       different blast radius for the same risk (a household joke or
       health detail surfacing to a room of strangers) — worth its own
       narrow mitigation (e.g. a blank/demo `memory.md` for public
       appearances) if this is ever actually scheduled, not a reason to
       reopen issue 18 generally.
4. **Trim the ServoEasing library to just the algorithm(s) actually used.**
   Noted 2026-09-14, per [Open Issues](#5-open-issues) issue 21. The
   installed library (see
   [Arduino Servo Controller](#34-arduino-servo-controller)) bundles
   multiple easing algorithms (e.g. bounce) when Jack's head motion will
   realistically only ever use one or two — carrying the rest costs
   Arduino flash/memory for no benefit, and may slow per-update easing
   math too. Sequencing matters here: get the sketch running against the
   stock, known-good library first (Chip's task — see issue 21); only
   once real use has settled which algorithm(s) to keep does trimming
   make sense. A good task to hand to Claude: fork a local copy of the
   ServoEasing repo and strip everything not in use.
5. **Barge-in (interrupting Jack mid-reply).** Set aside 2026-09-25 in
   favor of strict turn-taking for the first build (see
   [4.16](#416-runtime-integration-end-to-end-turn)). Letting a household
   member cut Jack off mid-sentence would feel more natural, but it
   depends on AEC keeping Jack's own voice out of the mic well enough
   that he doesn't interrupt himself — not validated until the board is
   mounted — and adds cancel/cleanup paths through TTS, Playback, and
   beak-sync. Revisit after AEC validation.
