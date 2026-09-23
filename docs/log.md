# Captain Jack — Project Log

Companion to `specification.md` (what to build) and `CLAUDE.md` (current
state + active work queue). This file holds what those two deliberately
leave out: design changes, what didn't work, learnings from implementation
and testing, alternatives considered, resolved issues, discussion prior to
a decision, and why a decision was made the way it was. If you're asking
"why is it this way" or "what did we try before this," look here. If
you're asking "what is Captain Jack supposed to do right now," look in
`specification.md`/`CLAUDE.md` instead — they're kept current-state-only
on purpose.

Split into two parts: **Open Issues History**, one entry per
`specification.md` Section 5 issue number (issue numbers are permanent
identifiers, assigned once, never reused or renumbered — a resolved issue
keeps its number and gets tagged `**[RESOLVED]**` in place rather than
deleted), and **CLAUDE.md History**, covering the dated narrative that
used to live in `CLAUDE.md`'s "Done so far" and "Work list" sections.

## Open Issues History

### Issue 1

Originally framed as a conflict: [Use Case
2.7](specification.md#27-personalized-memory)/the goals document assumed
voice ID identifies which household member is speaking, but the brief and
memory design explicitly deferred speaker ID and relied on self-reported
names instead.

**Reframed 2026-09-14, Chip's clarification**: not actually a conflict
between two docs — a three-tier priority for resolving who's speaking,
clarified rather than newly decided:
1. **Voice ID (preferred)**: whether it actually works well enough is
   unknown until the XVF3800 arrives and the scheduled accuracy test
   runs — not a documentation gap, just hardware-gated.
2. **Explicit self-identification (today's working fallback)**: what's
   actually implemented now — fail-closed by design. Flagged 2026-09-14
   as workable but awkward in practice — untested against real
   conversation at any length.
3. **Contextual inference (fallback of last resort)**: guessing who's
   speaking without being told. Not implemented, not designed, and in
   direct tension with the project's established fail-closed principle
   (Haiku is already known to invent placeholder names rather than admit
   it doesn't know). Flagged 2026-09-14 as the riskiest tier — genuinely
   open, not just unwritten.

**Narrowed 2026-09-23**: tier 1's software engine chosen — ECAPA-TDNN
speaker embeddings (enrollment + cosine-similarity matching against
Chip/Kath/Liz's stored vectors; start with a mainstream pretrained
implementation, e.g. SpeechBrain's `spkrec-ecapa-voxceleb`, and only
move to a purpose-trained tiny variant like ECAPA-TDNNLite/TinyECAPA if
real compute pressure appears — the ServoEasing-style
ship-the-stock-thing-first pattern). See
[specification.md#415-speaker-recognition-voice-id](specification.md#415-speaker-recognition-voice-id).

Considered and rejected: Picovoice's Falcon — it does speaker
*diarization* ("who spoke when," anonymous turn segmentation), not
identification against a known, enrolled set, so it doesn't actually
solve tier 1's problem regardless of cost; it's also the same vendor as
Porcupine, whose free tier was confirmed discontinued (see Issue 16),
raising doubt about Falcon's own free-tier status too.

**Correction, same day**: "1. **Voice ID (preferred)**" above (the
2026-09-14 framing) reads as fully hardware-gated on "the XVF3800
arrives" — that's now stale. The XVF3800 arrived and has been
electrically connected to the Pi via USB since 2026-09-20 (see "reSpeaker
XVF3800 arrival and DoA investigation" below); only its physical mounting
to the statue is still outstanding, which may affect acoustics/DoA
somewhat but doesn't block exercising its real mic array. Voice-ID
*prototyping* (the software approach — embedding model + enrollment
flow) can run against the actual board now, not a stand-in mic as
CLAUDE.md's work list previously framed it; only final accuracy
validation genuinely needs the scheduled XVF3800 test referenced in tier
1 above.

### Issue 2

[Persona and Identity Prompt](specification.md#44-persona-and-identity-prompt)
was a minimal stub; the full backstory, pirate speech style, deference
protocol, and conversational-intensity fade from [Use Case
2.2](specification.md#22-persona-captain-jack-the-parrot) weren't
implemented.

**Resolved 2026-09-14**: all four added to `identity.md` as a `## Persona`
section — concrete traits + example lines rather than narrative prose, to
suit Haiku. Treated as a first baseline, not final — untested against the
live API, expected to change once Chip hears it in practice. The
deference rule was originally a one-off hardcoded exception for Kath;
generalized 2026-09-14 into a memory-driven lookup (see Issue 3).

### Issue 3

Gendered deference phrasing ("Captain" vs. "Mistress") needed per-person
gender data with no home in the memory schema.

**Partially resolved 2026-09-14**: gender is now an explicit, hand-set
fact — a leading `- gender: ...` line in each person's existing `###
Name` subsection in `memory.md`, same non-model-writable status as the
heading itself (Jack never proposes or infers it, only reads it). Chip:
male, Kath: female, Liz: female.

**Updated same day**: the honorific itself is *not* derived from gender —
it's its own explicit, hand-set `- honorific: ...` fact, same status as
gender. Chip: "Captain," Kath: "Mistress," Liz: "Matey" — Liz's gender
(female) doesn't determine her honorific, demonstrating they're
independent. The default for anyone with no noted honorific, including a
guest or stranger not in memory at all, is the gender-neutral "Matey,"
replacing the earlier "Captain" default (Chip's own follow-up to a tone
concern raised the same day). `identity.md`'s deference rule reads the
honorific fact directly, never guessing it from gender.

### Issue 4

No memory category existed for location/environment or appointment/
calendar facts, though Use Cases 2.3 and 2.7 assumed Jack tracks both.

**Resolved/split 2026-09-14**: added a `home` tag for the durable-location
half. "Current location" (volatile, needs overwrite not append) deferred
to Possible Future Enhancements rather than solved here. Appointment/
calendar was a separate concern bundled into this issue by mistake — split
out to Issue 23.

### Issue 5

Only the Online mode was implemented; Offline idle-catalog behavior and a
distinct Asleep behavior/state machine were undesigned.

**Partially resolved 2026-09-20**: the state-machine/transition-logic half
is now designed, and modes renamed Off Watch/On Watch/Asleep (Chip's
call: Offline and Asleep were both, in fact, "offline" and both ran idle
behavior off local catalogs, just different ones, so "Offline" didn't
actually distinguish anything; "Asleep" was always the right name for
what it describes). **Narrowed further 2026-09-20**: Off Watch's and
Asleep's behavior-loop mechanism is also designed (ambient/excursion
model for Off Watch/On Watch, plain sequence for Asleep).

### Issue 6

Wake word, end-session phrase, and go-to-sleep phrase were all unchosen —
no mode-transition trigger existed.

**Resolved 2026-09-20**, though not the way originally framed as "three
phrases to pick": wake phrase = "Ahoy, Captain Jack" (fixed, locally
spotted, works from either dormant mode); go-to-sleep phrase = "Goodnight,
Jack" (fixed, locally spotted, Off Watch → Asleep only); end-session and
the On-Watch → Asleep nap request are *not* fixed phrases at all — Haiku
reads the intent from natural phrasing via a meta-tag on its reply.

### Issue 7

Gesture storage location was unresolved — Arduino-resident (interpreted
from a `GESTURE <id>`) vs. Pi-composed primitive sequences — blocking a
final serial protocol spec.

**Resolved 2026-09-14**: Pi-composed. Rationale: keep as much off the
Arduino as possible. The Arduino ends up with zero autonomous behavior —
it only ever executes the most recent command the Pi sent it, so if the
Pi is down, crashed, or hasn't booted, Jack is simply motionless and
silent (no local idle/gesture fallback of any kind). Accepted as correct
behavior, not a gap.

### Issue 8

Beak-easing ownership was unresolved: whether smoothing happens in the
Pi's RMS envelope extraction, the Arduino's easing library, both, or
neither.

**Resolved 2026-09-14**: all beak smoothing lives in the Pi's RMS
envelope extraction; the Arduino applies whatever `BEAK` value it
receives directly to PWM, no easing. Rationale: `BEAK` updates already
arrive at ~30–50Hz (every 20–33ms), near the Arduino's 20ms PWM floor, so
there's barely a gap for a cubic-easing pass to smooth over — unlike a
gesture waypoint, which is hundreds of ms from the next. A correct
envelope extractor already needs attack/release-style smoothing to
produce a good envelope in the first place, so the smoothing effectively
already exists on the Pi side, at no extra cost, before a value is ever
sent. Consistent with the Arduino-thin principle from Issue 7.

### Issue 9

The Pi→Arduino serial framing had two unreconciled descriptions (the
brief's loose sketch vs. `Arduino-command-structure.md`'s fixed-width
proposal), plus open questions on ACK/retry, gesture interruptibility/
preemption, layering/blending, and baud-rate timing math.

**Partially resolved 2026-09-14**: the two framing descriptions were
reconciled into one fixed-width design. Left open, narrowed to what that
design explicitly left unpinned: exact per-axis offsets/ranges,
worst-case transmission time re-derived against the reconciled format,
and ACK/timeout-retry. Gesture interruptibility and layering were dropped
from this issue's scope (see Issue 24) — not a link-level concern.

**Resolved 2026-09-15**: command syntax locked down and implemented
(variable-length, self-delimiting `b`/`p`/`r`/`y`/`t`/`s` syntax),
superseding the fixed-width framing reconciled the day before. All three
items this issue left open are now resolved: per-axis offsets/ranges are
pinned by the shipped firmware; worst-case transmission time is accepted
as non-blocking even allowing up to 2x error in Chip's informal
under-2ms-per-command estimate; ACK/timeout-retry is judged unnecessary
given the self-resyncing design's robustness (both Chip's call, not
further measurement).

**Confidence note, 2026-09-15**: the shipped syntax is treated as settled
going forward — further testing is expected to refine implementation
details (calibration offsets, exact timing bounds), not the syntax
itself. If that assumption turns out wrong, that's a bug to call out and
deal with when found, not a reason to reopen the syntax question.

### Issue 15

No `tests.md` existed, despite the goals document requiring at least one
test per use case and per hardware/software functional block.

**Partially resolved 2026-09-14**: `tests.md` now exists, with its first
test (the `home` memory tag). Coverage is still far short of "one test
per use case and per functional block" — most implemented blocks (memory
save/dedup beyond `home`, the orchestrator's conversation loop, persona/
identity behavior) have none yet.

### Issue 16

TTS and wake-word engines were unselected; STT was only tentatively
"local Whisper."

**Narrowed 2026-09-23**: wake-word and STT engines chosen, after
comparing options via web research.

**Wake word — openWakeWord**: chosen over Picovoice's Porcupine, whose
free tier was confirmed discontinued as of 2026-06-30 (Porcupine is now a
paid product; Picovoice's Falcon, considered separately for speaker
recognition, shares the same vendor — see Issue 1). openWakeWord is fully
open-source with no account/key/network dependency at runtime, is what
Home Assistant's own voice project standardized on (active development,
unlike discontinued Snowboy or orphaned Mycroft Precise), and is cheap
enough on Pi-class hardware that running both custom phrases
simultaneously (wake + sleep) is a non-issue: a single Raspberry Pi 3
core runs 15-20 concurrent openWakeWord models in real time. Both of
Jack's phrases ("Ahoy, Captain Jack" / "Goodnight, Jack") are
non-standard multi-word phrases with no pre-trained model available, so
each will need training via openWakeWord's synthetic-TTS-data pipeline
(the same method used for its own shipped models) rather than hand-tuned
matching.

**STT — Whisper via `whisper.cpp`, plus Silero VAD**: model size (tiny
vs. base) deliberately left open pending on-device experimentation — real
Pi 5 CPU-only benchmarks put tiny comfortably faster than real-time, base
only borderline real-time at 4 threads, and small at roughly 0.4-0.6x
real-time (a 10-minute clip taking 17-25 minutes), ruling small out
outright. Silero VAD chosen as a pre-pass for utterance end-pointing
(whisper.cpp doesn't have this built in — there's an open, unmerged
feature request for it) — it's the standard current pairing (the
"wake-word → VAD → STT → LLM → TTS" shape is the documented 2026
self-hosted voice-assistant pipeline) and it directly targets
whisper.cpp's known silence/noise hallucination failure mode by only
ever feeding it real speech.

**Local-LLM ASR cleanup stage — considered and rejected**: initially
proposed alongside Whisper, dropped after two problems surfaced. First,
running a second model inference pass after Whisper adds real latency on
hardware that's already CPU-only and has no headroom to spare. Second,
and more fundamentally, the actual consumer of the transcript for
ordinary conversation is Haiku itself, which already tolerates typical
ASR noise as part of normal language understanding — a dedicated local
corrector would be strictly less capable than Haiku while duplicating
work Haiku already does for free. The research literature on this
technique confirms the risk: LLM-based ASR correction reduces error
mainly when the input transcript's error rate is already high, and
otherwise risks paraphrasing away text that was already correct. Where
correction actually would matter — the wake/sleep-phrase spotter and
home-automation intent parsing, neither of which goes through Haiku — a
whole second LLM per turn is a heavy fix for a narrow problem; Silero VAD
gating addresses the specific known Whisper failure mode more directly
and far more cheaply.

**Left open**: TTS engine is still unselected.

**Narrowed further, 2026-09-23 (same day)**: TTS engine research turned
up a real quality-vs-edge-feasibility landscape, not a clean pick. Chip's
deciding criterion, stated explicitly: voice quality is critical to the
project being perceived as a success by a non-technical listener —
movies set the expectation, and seeing Jarvis (via jaredrhod's backtalk)
already meet that bar for a similar local-only voice reinforced it as
achievable, not just aspirational.

Findings, broadest first:
- **Chatterbox** (Resemble AI, MIT): the actual open-model quality
  ceiling right now — beat ElevenLabs in blind preference tests, 65.3%
  to 24.5%. Set aside for this project regardless: 0.5B params, built
  for GPU inference, no Pi-optimized port exists. Worth remembering if
  the project ever gains a GPU budget; not viable on Pi 5's CPU-only
  hardware today.
- **Kokoro-82M** (Apache 2.0) — independently validated (not just
  because backtalk/Jarvis uses it) as the best realistic choice for
  actually-local/edge deployment among current open models; separately
  reported at a 4.5 MOS, beating every proprietary model tested on one
  benchmark. The catch: stock Kokoro-82M benchmarks at only ~0.91-0.93x
  real-time on 2 ARM cores — can't reliably keep up with live speech on
  stock Pi-class CPU. `kokoro-pi` (a community ARM-optimized fork: fused
  int8 kernel + clause-by-clause streaming) closes that gap — ~2x faster
  synthesis, ~6x faster time-to-first-audio — at the cost of being a
  small, single-maintainer project rather than a well-trodden one.
- **Piper** (MIT) — the well-trodden, rock-solid Pi choice (same
  Rhasspy/Home-Assistant-voice ecosystem as openWakeWord), 8x+ real-time
  on the same ARM cores, but the more robotic/"classic TTS"-sounding
  option. Kept in mind as a fallback, not chosen as a candidate for the
  bake-off — quality is the deciding criterion here, and Piper is the
  known-weaker voice on that axis.
- **Supertonic-3** (ONNX-native, 99M params): comparable size to Kokoro,
  independently competitive-or-faster in CPU benchmarks (official: 5x
  real-time on a 16-thread CPU; an independent bench found ~3.2x
  real-time at a usable quality setting) — but no confirmed
  Raspberry-Pi/4-core-ARM-specific benchmark was found, unlike
  `kokoro-pi`'s real ARM numbers. A genuine open question, not dismissed
  on suspicion alone.

**Plan of record**: an empirical bake-off on the real Pi — `kokoro-pi`
vs. stock Supertonic-3 — judged primarily by ear (voice quality, per
Chip's stated priority) with real-time throughput as a secondary check.
Chatterbox and Piper are not part of the bake-off (former hardware-
infeasible now, latter a known-quality fallback, not a quality-optimizing
candidate). **Blocked** on the XVF3800's speaker being wired (2-pin JST
connector in transit, ETA ~2026-09-27) — can't judge voice quality
without being able to hear the output. See
[specification.md#47-text-to-speech-tts](specification.md#47-text-to-speech-tts).

### Issue 17

Idle-audio-on-Pi tradeoff: ambient sound depends on the Pi being up,
unlike the removed MY1690-on-Arduino design — noted, not mitigated.

**Resolved 2026-09-14**: subsumed by Issue 7's Arduino-thin decision — a
Pi outage already means total stillness and silence, not just no idle
audio, and that's accepted behavior. No separate fix needed for audio
specifically.

### Issue 18

Conversational-privacy/oversharing risk (a fact told by one household
member surfacing in front of another) was listed as noted with no
technical mitigation.

**Closed 2026-09-14**: this was never actually an open design question —
the brief already made the call (accepted risk, no mitigation, revisit
only if it becomes a real annoyance in practice). Listing it as an Open
Issue mischaracterized a decision as undecided. Not reopened by the
`home` memory category or persona work added since, per Chip's call —
flagged and considered, but left as the brief decided it.

### Issue 19

The scope of "anything Haiku can do" beyond home automation was
explicitly undefined in the goals document — including whether Haiku can
be proactive within a session, and what (if anything) carries over
between sessions outside of `memory.md`.

**Resolved 2026-09-14**: the open-ended framing is dropped. Secondary
capabilities beyond home automation are deliberately scoped, not
"anything"; email/calendar/finance access deferred until much later.
"Whether Haiku can be proactive within a session" became a brainstormed
candidate in Possible Future Enhancements, not an open design question.
"What carries over between sessions outside memory.md" has a plain
answer, not a gap: nothing — each API call is stateless; `orchestrate.py`
re-sends `identity.md`/`memory.md` fresh every turn, and that's the only
persistence there is.

### Issue 20

Speculative scenarios (Alexa flirtation, community-lecture demo) were
recorded but unscoped, including the lecture scenario's own follow-on
questions about credential/network provisioning and long-form vs.
interactive delivery.

**Closed 2026-09-14**: discussed and moved to Possible Future Enhancements
item 3, with concrete implementation risks noted inline for both
scenarios rather than left as bare "undiscussed" flags.

### Issue 21

Firmware for servo-only control needed to be written for the new Arduino
Uno (old MY1690/electret-mic hardware already removed); it could be
developed and uploaded, but couldn't be validated against real actuation
until the board was wired to the head/beak servos.

**Noted 2026-09-14**: Chip wrote this sketch himself (he knows the
physical wiring) rather than handing it to a future session. Plan: ship
it first against the stock ServoEasing library as installed, known-good;
trimming that library down to just the easing algorithm(s) actually used
is a separate, later optimization (see Possible Future Enhancements).

**Written and reviewed 2026-09-15**: `arduino/ServoControl/ServoControl.ino`
exists, parsing the `b`/`p`/`r`/`y`/`t`/`s` command structure against the
stock ServoEasing library per the plan above. Code review caught, and
Chip fixed, two correctness bugs: the `b`/`p`/`r`/`y` range clamp compared
the post-offset sum against the max instead of the raw incoming integer
against the defined range, so `uint8_t` wraparound could silently produce
an angle below the intended minimum (e.g. `b200` landed at 24, outside
the 80-125 beak range); and duration (`t`) had no upper bound at all, now
capped at 9999ms — 2x the slowest gesture in `gesture-library.md` — so a
garbled/huge value can't reach the easing library unbounded.

**Closed 2026-09-20**: board wired to all four servos; erratic behavior
traced to an undersized 500mA power supply (replaced with 2000mA, which
required removing a power-enable line the old supply had and the new one
doesn't support at 5V), then resting/offset/range constants tuned
empirically. `ServoControl.ino` now drives all four servos correctly from
real commands.

### Issue 23

Split from Issue 4: no memory category existed for appointment/calendar
facts, though Use Case 2.7 assumed Jack tracks them — no allowlist tag,
no schema, not scoped.

**Closed 2026-09-14, Chip's call**: moved to Possible Future Enhancements
item 2 — whether it ends up as a new memory tag or a tool call, either is
more scope than is worth taking on now. Keeping the current feature set
focused improves the odds of actually finishing it.

### Issue 24

Reclassified out of former Issue 9's scope: gesture interruptibility/
preemption vs. queuing, and layering/blending, are undesigned. Since the
Arduino has no queue and acts on each command immediately on arrival
(Issue 7), these are purely questions for the Pi-side Gesture Engine to
answer — e.g. whether a new gesture request cuts off one in progress or
waits, and whether two gestures can run on different axes at once — not
anything the serial link or firmware need to know about.

**Noted 2026-09-20**: still undesigned, but the Gesture Engine's data
structures now pad each Move's wait time past its embedded `t<TTTT>`
duration as a safety margin, specifically because whether the ServoEasing
library ignores a new command sent before the previous easing finishes,
or interrupts it instead, is unverified — either behavior is a real
candidate answer to this issue once it's actually tested, not just an
edge case to design around blindly.

**Narrowed 2026-09-20**: resolved for Asleep specifically — its behavior
loop is a plain sequence where nothing ever plays concurrently with
anything else, so layering/blending doesn't arise there at all. Still
fully open for On Watch, and for whatever Off Watch's own behavior loop
ends up being.

### Issue 25

Added 2026-09-20: small-amplitude, slow gestures (e.g. `id-idle-breathing`'s
5° pitch swing over 2000ms) visibly moved in discrete steps on the real
bird rather than gliding smoothly, even though Issue 22's timing-budget
analysis and this issue's own investigation both confirmed the
Arduino-side easing code itself wasn't the problem.

Diagnosed against real hardware using
`arduino/EasingDiagnostic/EasingDiagnostic.ino` (a one-off diagnostic
sketch, not part of the real firmware) — it polls a ServoEasing servo's
own internal current position in microseconds (finer than
`getCurrentAngle()`'s whole degrees) every loop iteration and logs a
timestamp every time that value changes, giving an objective trace
instead of relying on counting visible steps by eye. Two moves compared,
same code path as `ServoControl.ino`'s `s` handler, same ~2000ms
duration:
- 5° move (matching `id-idle-breathing`): ~53 updates, ~20-40ms apart,
  each only ~1 microsecond. Visibly steps on the bird.
- 30° move: ~99 updates, similar cadence, each ~3 microseconds. Looks
  smooth.

Conclusion: the update mechanism itself was firing on schedule and
advancing monotonically in both cases — not a timer/interrupt bug. The
servo's own physical resolution just can't reliably resolve ~1
microsecond pulse-width changes, so a move that's both small in amplitude
*and* slow (many small ticks, none individually big enough to move the
shaft) looks stepped no matter how correctly the easing math runs.
Calibration from this test: roughly 10.4 microseconds of pulse width per
commanded degree on this pitch servo, and the visible-smoothness
threshold sits somewhere between 1 and 3 microseconds per ~20ms tick (not
pinned down more precisely than that yet). A real content/design
tradeoff, not a code fix: increase amplitude (less subtle), shorten
duration for the same amplitude (faster ticks, but undercuts "slow gentle
breathing"), or accept the stepped look for very subtle idle motion.

**Resolved for `id-idle-breathing` specifically, 2026-09-20**, through
live tuning against `exercise_hardware.py` on the real bird. Shortening
duration alone didn't work: halving `t` from 2000ms to 300ms (same 5°
amplitude) was "smoother but still not smooth" and read as panting
(~100 breaths/min) — confirming that a move's *total* achievable
positions (≈ swing distance ÷ servo resolution) is what governs
smoothness, and duration alone can't increase that. Amplitude was the
real lever: doubling it to 10° at a calmer 800ms looked "much smoother,"
but at Chip's preferred slower ~19-breath/min pace (1600ms) the same 10°
dropped back below the resolvable threshold — steady-state breathing
swings between the *two extremes* each move (e.g. target 48 to target 7),
not out from rest and back, so doubling duration at fixed amplitude
halves microseconds-per-tick just like it did in the first test. Landed
on an asymmetric swing (up +13°, down -28°, ~41° total) at 1600ms, since
pitch only has +15° of headroom above resting versus -35° below it — a
large enough symmetric swing wasn't available. Confirmed smooth on the
real bird. Roll (a secondary "micro-roll" flourish) was dropped from the
gesture entirely rather than scaled up the same way, since a roll swing
large enough to fix its own smoothness would stop reading as "micro."

## CLAUDE.md History

### Arduino toolchain and servo wiring

**Confirmed 2026-09-13**: `arduino-cli` toolchain installed and tested
against an Arduino Uno connected to the Pi — `arduino/TestBlink` compiles
and downloads successfully. Servo and ServoEasing libraries installed and
ready for real sketch development.

**Confirmed 2026-09-14**: `arduino-cli` compile + upload verified
end-to-end against a freshly connected Arduino Uno — doubled `TestBlink`'s
blink rate, compiled, uploaded via `/dev/ttyUSB0`, and Chip visually
confirmed the LED blinks at the new rate. Also resolved 2026-09-14: the
connected Arduino Uno is a fresh/new board, not the original one — the
old MY1690 + electret-mic hardware had already been removed.

**Confirmed 2026-09-20**: Arduino wired to all four servos (head
pitch/roll/yaw + beak) and `ServoControl.ino` drives them correctly.
Erratic behavior was traced to an undersized 500mA power supply, fixed
with a 2000mA supply (which meant removing the power-enable line — the
new supply has no 5V-compatible enable). Beak switched from
`ServoEasing` to plain `Servo`; resting/offset/range constants for all
four axes tuned empirically. See Issue 21 (closed) and
`specification.md` section 4.14.

### reSpeaker XVF3800 arrival and DoA investigation

**Received 2026-09-20**: the reSpeaker XVF3800 arrived and was connected
to the Pi via USB, sitting on a table in front of the parrot (not yet
mounted to the statue). No speaker connected yet — a 2-pin JST connector
was on order, ETA ~2026-09-27. A first batch of idle/ambient `.wav` clips
was added under `wavFiles/`, including an `AlignmentTone.wav` for later
beak-sync timing calibration.

**Investigated 2026-09-20**: DoA was investigated the same day — the
XVF3800 exposes a generic USB-HID interface (`/dev/hidraw0`, already
bound by the kernel's stock hidraw driver — no separate driver needed)
plus a vendor-specific USB interface, but no `xvf_host` tool or
equivalent exists on this Pi, and the actual command protocol for reading
`AEC_AZIMUTH_VALUES` over that channel isn't something to guess at —
needs Seeed's real documentation/reference host application, not found
via `apt`/`pip`/filesystem search. Reading DoA is unblocked in the sense
that the hardware needed is on hand (just the tool/docs are missing) — it
moved from "blocked on hardware" to "blocked on finding Seeed's official
tool."

### exercise_hardware.py and the servo-stepping diagnosis

**Added 2026-09-20**: `exercise_hardware.py` — a standalone hardware test
harness (not part of the real orchestration/state machine) that drives
the servos through `gesture-catalog.yaml`'s Off Watch/Asleep ambient/
excursion behavior, switching modes on a blind random 2-5 minute timer.
Gestures/wavs/mode-transitions were otherwise untested against real
actuation beyond what section 4.13's code review covered — this was the
first real exercise of the gesture data itself. No audio, no DoA, no
wake-phrase logic — `venv/bin/python exercise_hardware.py --dry-run` runs
the same logic without a serial port, for checking behavior before
running it against the real bird. `read_doa_azimuth()` in the script is a
stub (always `None`) so wiring in a real reading later is additive, not a
rewrite.

**Diagnosed 2026-09-20**: running `exercise_hardware.py` against the real
bird surfaced visible "discrete steps" in small/slow gestures (e.g.
`id-idle-breathing`). See Issue 25 for the full diagnosis and resolution.
The real `ServoControl.ino` was restored to the board afterward.

### Work-list items resolved before this log existed

- **Pi↔Arduino serial protocol design** — resolved/locked down
  2026-09-15; see Issue 9.
- **`arduino-cli` toolchain confirmation** — resolved 2026-09-14; see
  "Arduino toolchain and servo wiring" above.
- **DoA reading via `xvf_host AEC_AZIMUTH_VALUES`** — investigated
  2026-09-20; real gap found (no `xvf_host` tool on this Pi), moved from
  "blocked on the XVF3800" to "blocked on finding Seeed's tool/docs"; see
  "reSpeaker XVF3800 arrival and DoA investigation" above.

## Design History (Specification Sections 1-4)

Design changes, rejected alternatives, and rationale embedded in
`specification.md` Sections 1-4 that don't tie to a numbered Open Issue.
Keyed by the spec section they support (2026-09-21 pass, extended
2026-09-23 to give every Section 1-4 heading a `History` tag — see the
tag on each heading in `specification.md`; sections with nothing to
report yet are tagged `History: none yet.` rather than getting an empty
header here, and gain one only once real content exists to file).

### 3.2 Seeed reSpeaker XVF3800

**Chosen over alternatives**: selected over the 2-mic ReSpeaker Lite
(XU316) and the older WM8960-based 2-Mic HAT specifically for its
newer-generation AEC and 4-mic beamforming — needed because the bird's
speaker sits inches from its own mics, which a cruder echo-cancellation
stage might not handle well enough. Roughly 2x the Lite's cost and a
larger footprint, accepted as the tradeoff for that AEC quality.

**Verified directly, 2026-09-23**: queried the connected board's ALSA
`hw_params` for both its playback and capture subdevices (`aplay
--dump-hw-params` / `arecord --dump-hw-params` against `hw:2,0`) rather
than trust Seeed's general docs alone — the currently-flashed firmware
reports a fixed, non-range format on both directions: `S16_LE`, 16000Hz,
2 channels. Seeed's docs describe two firmware options (a 16kHz
"standard" USB firmware and a 48kHz Home-Assistant-oriented one); this
board is running the 16kHz one. See
[specification.md#47-text-to-speech-tts](specification.md#47-text-to-speech-tts)
for the resulting canonical output-format decision.

### 3.4 Arduino Servo Controller

**Pre-Pi role**: in the original (pre-Pi) design, the Arduino owned all
"intelligence," peripherals, and sensor input — the MY1690 audio player
and electret mics for sound-direction triangulation lived on it (see
3.7). Those roles are removed in the current design; the Arduino shrinks
to real-time servo execution only, per the Arduino-thin decision (Issue
7). Power-supply diagnosis that preceded servo validation: see Issue 21.

### 3.7 Removed and Legacy Hardware

**MY1690 audio player**: SD-card-based stereo clip player (left channel
audio, right channel a beak-level control track) that drove the original
build's idle-sound + beak-sync trick. Superseded by Pi-side playback of
local audio files through the XVF3800, using the same RMS-envelope
extraction as live TTS (see
[specification.md#410-idle-and-ambient-audio-player](specification.md#410-idle-and-ambient-audio-player)).
Tradeoff: idle sound now depends on the Pi being up, unlike the old
design where ambient noise ran independent of Pi health — accepted as a
special case of the Arduino-thin decision (Issue 7): a Pi outage already
means total silence and stillness, not just no idle audio. See Issue 17.

**Electret microphones** (2x, ADC input): used for crude sound-direction
triangulation on the original Arduino. Superseded by the XVF3800's
onboard direction-of-arrival output, read directly by the Pi (see
[specification.md#49-direction-of-arrival-doa-reader](specification.md#49-direction-of-arrival-doa-reader)).

### 4.7 Text to Speech (TTS)

**Output format decided, 2026-09-23**: rather than pick a sample
rate/format on paper, queried the connected XVF3800's actual ALSA
`hw_params` directly (see [3.2](#32-seeed-respeaker-xvf3800)) and found a
fixed, non-negotiable playback format — `S16_LE`, 16kHz, 2 channels.
Locked that in as the canonical Pi-side output format for both TTS and
idle clips. Neither TTS bake-off candidate (Kokoro-82M: 24kHz native;
Supertonic-3: 44.1kHz native) matches it natively, so a resample-down
step is needed regardless of which wins — the format decision doesn't
favor either candidate. 16kHz ("wideband" voice quality, the modern
VoIP/voice-call standard) was judged sufficient for a voice-focused
companion device, not a hi-fi concern; reflashing to Seeed's 48kHz
Home-Assistant-oriented firmware remains a possible future option, not
pursued now.

**Mono vs. stereo storage, 2026-09-23 (Chip's question while planning the
`wavFiles/` conversion)**: the XVF3800's 2-channel requirement is a
USB-audio-interface quirk of this specific board, not real stereo
content — Jack has exactly one physical speaker (3.3), so there's
nothing for a second channel to meaningfully carry beyond a duplicate of
the first. Decided to keep stored clips and TTS engine output mono
throughout, and do the mono→stereo duplication as a single shared step
right at the ALSA write, not baked into the asset library. Reasoning:
(1) it's the only way both sources (pre-recorded clips and live TTS,
which is inherently mono at the engine) go through genuinely identical
code, matching 4.8's "one code path for both cases" design, instead of
beak-sync's RMS extraction needing to know which channel to read; (2)
mono storage is half the size for identical content, and the clip
library is expected to keep growing; (3) it decouples the stored assets
from this board's specific quirk, so a future firmware/hardware change
only touches the one small duplication step, not the whole library.

### 4.10 Idle and Ambient Audio Player

**Off Watch's (and On Watch's) behavior loop**: an earlier sketch of
independent random-interval timers for wav/gesture playback had real
bugs, and a fixed "excursion, then return to a hardcoded neutral point"
model was rejected as too mechanical for something meant to read as
lifelike. The ambient/excursion model (see
[specification.md#410-idle-and-ambient-audio-player](specification.md#410-idle-and-ambient-audio-player))
was adopted instead, resolving Issue 5's remaining Off Watch scope for
the mechanism.

**Off Watch excursion tuning (2026-09-20)**: landed on a 30-90 second
random interval between completed ambient-motion steps, plus a rule
never to pick the same excursion id twice in a row. Chip's first
instinct was 10-20s; widened because the math didn't work against
today's library — with only 3 Off Watch excursion gestures and 0 wav
clips, 10-20s over a full 15-minute Off Watch session would repeat each
gesture roughly 20 times, reading as mechanical rather than lifelike.
30-90s is explicitly a starting point to tighten back down as the
library grows, not a final number — "try it and see," per Chip.

**Sample rate correction, 2026-09-23**: `specification.md` had described
the `wavFiles/` clips as 41000Hz; verified directly against
`AlignmentTone.wav`'s actual header (Python's `wave` module) and found
they're really 44100Hz, mono, 16-bit signed PCM — the spec text was
wrong, not the files. The real number matters now because of the new
canonical 16kHz output format (see
[4.7](#47-text-to-speech-tts)): these clips need a one-time batch
conversion down to 16kHz, not live resampling on every play.

**`sl-settle-to-sleep` wav idea set aside**: Chip's original "About time
they let me get some rest" idea was set aside for `sl-settle-to-sleep`
specifically — it presumes someone made Jack wait, which fits neither
`idle_timeout` (nobody did) nor really adds anything beyond what Haiku's
own live line already covers on the On-Watch path. It's a good candidate
for `sl-waking-up` instead (grumbling about *being* woken), a separate,
not-yet-tackled pairing.

### 4.12 Gesture Engine and Catalog

**`Blink` gesture removed**: a previous draft of the gesture library
included a `Blink` gesture assuming an eyelid mechanism not present in
the documented physical build ([3.5](specification.md#35-servos-head-and-beak));
it was removed.

**First-pass-to-second-pass redesign (2026-09-20)**: the first pass
resolved every gesture's deltas into one fixed absolute command at
authoring time — e.g. "+10 yaw" became a specific number computed
against a hardcoded resting position. Chip's review caught two problems
with that: (1) a real baseline should track where Jack is actually
oriented (e.g. toward whoever's speaking, per DoA), not a constant; and
(2) many gestures don't return to neutral on their own, so sequencing
several of them without a shared reference point drifts until a servo
hits its physical travel limit. The fix was the baseline/ambient-excursion
model now in
[specification.md#412-gesture-engine-and-catalog](specification.md#412-gesture-engine-and-catalog).

Consequences of that fix, at the time:
- Composing the wire string at send time (`P = clamp(baseline.pitch +
  dp, 0, 50)`, not pre-clamped at authoring time) retired the first
  pass's `CLAMPED` annotations entirely.
- What actually fixed the "too mechanical" complaint was the drifting
  baseline (not a hardcoded return point), not the removal of return
  moves themselves — most excursions still end with an explicit
  delta-(0,0,0) Move.
- The first pass's "anchor gesture" idea (should some excursions
  permanently relocate the baseline?) was retired — the ambient/
  excursion split replaced it. Off Watch's Ambient Scanning, for
  example, became just a normal (larger) excursion, not a special case.
- "Turn Toward Speaker" no longer needed runtime parameterization, since
  continuous DoA-tracked baseline yaw already does the subtle following;
  it was re-scoped to a deliberate, fixed-delta *emphasis* turn layered
  on top, resolving one of two `NEEDS-RUNTIME-PARAM` cases at the time
  (the other, "Vowel Drift," remains open — its duration is tied to live
  TTS phoneme timing, not knowable at authoring time).

**Mapped 2026-09-20 (both passes)**: every entry in
`gesture-library.md` was translated into the second-pass structure — see
`gesture-catalog.yaml`, including its own header comments for the full
first-pass-to-second-pass changelog.

### 4.14 Arduino Firmware

**SoftwareSerial interference, noted at MY1690 removal**: SoftwareSerial
was observed to interfere with the servo easing library in the prior
MY1690-era design, and was removed along with the MY1690 (see 3.7).
Firmware must not reintroduce SoftwareSerial alongside the easing library
without further research into that interaction.
