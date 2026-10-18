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

**Correction, 2026-10-06**: that confidence note held for the syntax, but
`specification.md`'s per-axis range/offset numbers themselves had
drifted from the shipped firmware (found while building beak-sync, see
[4.8](#48-beak-sync-rms-envelope-extraction)) — it said beak was nominal
0–45; `ServoControl.ino`'s actual `BEAK_RANGE` is 60 (head axes were off
too: pitch/roll 0–50 not 0–60, yaw 0–130 not 0–90). The firmware itself
was never wrong, only the prose describing it. Fixed by reading the
constants directly rather than trusting the existing text.

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

### 4.1 Wake Word Spotter

**Confidence threshold methodology, 2026-09-23**: rather than pick
numeric accept/reject thresholds for the wake ("Ahoy, Captain Jack") and
sleep ("Goodnight, Jack") phrases on paper, decided the methodology and
starting point only — neither custom model is trained yet, and there's
no real household ambient-audio corpus to calibrate against, so a
specific number would be arbitrary. Grounded in openWakeWord's own
documentation rather than invented: its models score each 80ms frame
0-1, the documented default threshold is 0.5, and its own commonly-cited
target is <5% false-reject rate / <0.5 false-accepts per hour, calibrated
against a representative sample of real ambient audio (speech, noise,
music) — not a number that can be picked in the abstract.

Decided: thresholds are tuned **per-phrase**, not shared (the two models
are independently trained and won't share a score distribution). Both
start from openWakeWord's 0.5 default and target bar. One deliberate
asymmetry on top of that default: the **wake** phrase is biased stricter
(test above 0.5, loosen only if false-rejects prove annoying) since a
false accept there means an unprompted activation — the more disruptive
failure for a household companion — while a false reject only costs
repeating the phrase. This mirrors the fail-closed posture already
established for memory saves and the no-guessing self-ID fallback (Issue
1), applied to a new part of the system rather than invented fresh. The
**sleep** phrase stays at the vanilla default — an unwanted "go quiet" is
a softer failure than an unwanted wake, so there's less reason to bias
it. Actual calibration happens as part of the wake-word groundwork
already queued once the board can be exercised for real (see
`CLAUDE.md`'s work list) — not a separate task.

**Custom model training started, in progress 2026-10-07/08**: Chip
began training both custom models (item 9 of CLAUDE.md's work list) on
Colab, using a community-maintained notebook
([alfiedennen/openwakeword-colab-2026](https://github.com/alfiedennen/openwakeword-colab-2026))
rather than openWakeWord's own official notebook, since the official
one is reported broken since 2023 (Python-version/dependency rot) and
the community fork specifically claims to fix that.

The wake-phrase ("Ahoy, Captain Jack") run completed and produced
`wake_phrase.onnx` (now in the repo root - **not yet validated**, see
below), but needed on the order of 30 manual error-patch-restart
cycles with another AI (Gemini) to get there. The sleep-phrase
("Goodnight, Jack") rerun hit a new, more fundamental error: Colab's
current default runtime has moved to Python 3.13, and `piper-phonemize`
(a dependency of both notebooks, for TTS-based positive-sample
generation) has no prebuilt wheel for 3.13 yet - attempting to build it
anyway led to an ABI mismatch (`undefined symbol:
espeak_TextToPhonemesWithTerminator`), most likely a conflicting
system-installed espeak-ng shadowing the one the wheel bundles.

Fix in progress: Colab's "Use fallback runtime version" command
(Command Palette, `Ctrl+Shift+P`) rolls the VM back to an older image.
The earliest offered snapshot (2025.07) came up as Python 3.11.13 -
old enough to avoid the 3.13/piper-phonemize problem entirely. Rerunning
the whole notebook from scratch on that snapshot got much further with
far fewer errors (none fatal through section 5) than the original
3.13-based attempts - strong evidence the Python version, not the
notebook's own logic, was the real root cause of most of Gemini's 30
patches. It then stopped at section 6 with a silent Colab disconnect
(no Python traceback) - cause not yet identified (the usual suspects are
tab-inactivity disconnects or free-tier GPU/RAM reclaim after a lot of
GPU time used today); the resource-usage indicators and runtime log were
both unavailable to check after the disconnect. Paused here for the
day - picking back up with a fresh Colab session, same approach
(fallback runtime to 2025.07, Python 3.11.13).

**The disconnect saga, 2026-10-09/10**: resuming the next day on a fresh
session (still 2025.07/Python 3.11.13), disconnects kept recurring,
consistently in cell 7 (downloading the 17GB ACAV100M negative-feature
set) or cell 8 (downloading/converting FMA-small's ~8GB of background
noise for augmentation) - regardless of Colab tier. Moved from free to
Pay-As-You-Go with no change. Chip raised using his own desktop's RTX
2060 (adequate - one documented case trained openWakeWord with no GPU
at all) via WakeLab or WSL2 as an escape hatch, but both still require
rebuilding the same dependency surface (openWakeWord's own checkout,
piper-sample-generator, Piper voices, precomputed negative/validation
`.npy` files) on a platform Chip isn't set up to administer himself -
set aside in favor of fixing cells 7/8 in place first.

Root-caused and fixed two real problems, then systematically eliminated
everything else as a cause of the disconnects themselves:
- **FMA's host was simply unreliable** - an 8GB zip on a university
  (UNIL/SWITCH) cloud server, not a CDN. Replaced FMA entirely with
  **ESC-50** (environmental sounds, a ~600MB zip hosted on GitHub) for
  the same background-noise-augmentation role - far smaller and far more
  reliably hosted. Rewrote cell 8 around it, with per-file resume logic
  (skip filenames already converted) carried over from the original.
- **ACAV100M's 17GB download was single-stream and slow enough that any
  disconnect lost a lot of ground.** Rewrote cell 7 to fetch it via
  `aria2c` (16 parallel connections, resumable) instead of a single
  `requests` stream - dramatically faster, buying enough time margin
  that cells 7 and 8 (and then 9 and 10) finally completed in one run.
- Ruled out, in order, as explanations for the disconnects themselves:
  disk-space exhaustion (confirmed 59GB free via `df -h /content`), GPU
  preemption (disconnected on a CPU-only runtime too), tab/idle
  inactivity (disconnected even with the tab focused and the mouse kept
  moving), and a hung ffmpeg subprocess (disconnected mid-conversion at
  a steady, un-stalled rate, and a subprocess timeout fix didn't help).
  Compute-unit exhaustion was also ruled out (98+ units remained each
  time). Leading theory, never confirmed (Colab gave no specific reason
  beyond "hosted runtime disconnected," and no logs were ever
  accessible after the fact): a fixed total session-duration cap, with
  disconnects landing wherever elapsed time happened to run out that
  run - consistent with later disconnects recurring at cell 10, cell 11,
  and cell 12 on different attempts, not just cells 7/8.
- One copy/paste `SyntaxError` turned out to be SSH/clipboard
  corruption from copying more than one terminal screen at once, not a
  real code bug - fixed by pasting through an intermediate plain-text
  file with a larger terminal window.

**Checkpointing to Google Drive to survive disconnects, 2026-10-10**:
since a full disconnect wipes `/content` but a fixed-duration cap can't
be worked around, the next best thing is making each expensive step's
*output* durable so it never has to be redone. Chip created a Google
account and Drive folder solely for this (explicitly scoped to avoid
the "once it's on, it's hard to turn off" problem he's had with
iCloud/OneDrive on his other devices - a Colab-only browser mount
doesn't install anything on his phone or desktop). First attempt wrote
training clips directly to the Drive-mounted path during generation and
appeared to fail silently (files reported as generated, but none
visible on Drive) - initially diagnosed as Google Drive's FUSE mount
being too slow/unreliable for thousands of small file writes (a real,
commonly-reported limitation), but reading openWakeWord's own
`train.py` source (around the lines the notebook's own comments
referenced) found the actual cause: `generate_clips` always writes to
a path it constructs itself (`output_dir/model_name/<category>`) and
completely ignores the `positive_clips_train_dir`-style keys in
`my_model.yaml` that the wrapper cell's resume-check (and the
Drive-redirect attempt) were reading/writing - two different
conventions for "where do the clips live" that happened to coincide by
default and silently diverged once either was edited. The clips had
actually been generating correctly all along, just not where anything
was checking.

Settled design: generate locally (fast, already reliable) and
checkpoint the *real* output directory to Drive as a single zip
archive after the fact - one large write Drive handles fine, instead of
thousands of small ones it doesn't. Applied this pattern twice: to
cell 8's `fma_wav` output, and to the real clip directories (first
fixing the yaml keys to actually match `output_dir/model_name/...`,
then zipping that). A restore cell runs right after the Drive mount and
before each expensive step, extracting the matching checkpoint if one
exists; both cell 8 and cell 11's own pre-existing per-file/per-category
resume logic then transparently skips what's already there. The same
checkpoint-clips cell gets re-run again after cell 12 (the 16kHz
resample step) to capture the resampled version, so that step never has
to be redone either. Cells got labeled in the notebook (Restore
fma_wav / Checkpoint fma_wav / Restore clips / Checkpoint clips) so this
reconstructs cleanly for the sleep-phrase run.

**`wake_phrase.onnx` trained and validated, 2026-10-10**: with the GPU
runtime (L4) and all of the above in place, cells 1-15 completed in one
run. Training (cell 14, 24,000 steps across three stages) finished in
~2.3 minutes against the notebook's own 30-40 minute estimate - alarming
at first glance, but the printed per-checkpoint metrics (recall and
accuracy climbing, false-positive rate dropping as negative-class
weight ramped up, 26 checkpoints saved) show genuine convergence; the
mismatch is because the actual model is tiny (a 2-layer MLP, batch size
~128) and L4 is fast, not because training was skipped. Final
checkpoint-selection logic (require simultaneous 90th-percentile
accuracy/recall and 10th-percentile false-positive-rate across the 26
saved checkpoints) qualified zero candidates - expected behavior for a
strict three-way intersection over a small sample, with a documented
fallback to the single checkpoint with the lowest false-positive rate.
Exported `wake_phrase.onnx` (791KB); an onnxruntime sanity check
immediately after export reproduced the selected checkpoint's own
recall (0.748), confirming the file matches what was actually selected.
Final stats: accuracy ≈0.873, recall ≈0.748, false-positives ≈0.05/hour.
(The export cell's very last printed FP/hour line - 0.50 - is a
cosmetic bug reading the last training step's snapshot rather than the
exported checkpoint's own stats; the real number is 0.05.) Copied off
Colab via browser download, committed, and pulled onto the Pi,
replacing the earlier 30-patch, never-validated `wake_phrase.onnx`.

**`sleep_phrase.onnx` trained and validated, 2026-10-11**: the
Drive-checkpoint infrastructure paid off immediately - a disconnect
after cell 11 cost nothing, since the rerun restored from the checkpoint
and finished. Same convergence pattern as the wake phrase (23
checkpoints saved, best val_fp_per_hour 0.00), same zero-checkpoints-
qualified-fallback-to-single-best path, and the onnxruntime sanity
check again reproduced the selected checkpoint's own recall (0.594)
exactly. Final stats: accuracy ≈0.794, recall ≈0.594,
false-positives ≈0.10/hour (the export cell's last FP/hour print -
0.70 - is the same cosmetic last-step-snapshot bug noted above; the
real number is 0.10). Recall is noticeably lower here than the wake
phrase's 0.748, but that's an acceptable asymmetry given the
methodology already decided above: the sleep phrase stays at the
vanilla 0.5 threshold (an unwanted "go quiet" is a softer failure than
an unwanted wake), and there's headroom to lower that operating
threshold later during real-audio calibration - trading some of the
spare false-positive margin for better recall - without retraining.
Copied off Colab, committed, and pulled onto the Pi.

**Correction and contribution back, 2026-10-12**: the final validated
runs above (both `wake_phrase.onnx` and `sleep_phrase.onnx`) actually
used Colab's **2026.04** fallback snapshot (Python 3.12), not the
2025.07/Python 3.11.13 one noted earlier in this section - per Chip.
The notebook that trained both models is now committed as
`train_wakeword.ipynb` (outputs kept). Since the upstream notebook repo
has five open PRs and no merges since its initial commit, its changes
were written up as an issue rather than a PR or a public fork (Chip
didn't want to maintain a fork):
[alfiedennen/openwakeword-colab-2026#9](https://github.com/alfiedennen/openwakeword-colab-2026/issues/9) -
fallback runtime, aria2c for ACAV, ESC-50 for FMA, Drive zip
checkpoints, the clip-dir pitfall, and the misleading final FP/hour
print. Posted text kept in `docs/community/openwakeword-colab-issue.md`.

**Still outstanding**: both custom models are now trained and
validated, but training them is necessary, not sufficient, for item 9 -
the actual Pi-side wake-word spotter module (loading both `.onnx` files
via onnxruntime inside the Capture/Listener pipeline, replacing the
Enter/`sleep` keyboard stand-ins) is not built yet. That also unblocks
real-audio calibration of both phrases' operating thresholds (section
4.1's methodology above), which can't happen until the spotter exists
to run them through.

**Wake threshold calibrated, 2026-10-12**: with the spotter built and
live-validated (item 33), ran a real calibration session -
`coordinator.py --scratch-memory --save`, voice-only, no keyboard
stand-ins - covering close, soft, and distant delivery, plus a second
speaker (Kath, from the kitchen). All 5 wake attempts fired correctly,
scoring 0.82-1.00; the weakest was the soft+distant one, still well
clear of the 0.5 starting point. A stretch of ordinary background
conversation, not directed at Jack, never crossed 0.5 either -
`coordinator.py`'s live `[spotter] wake=.. sleep=..` readout (added with
the spotter itself, see 4.11/4.16 history) made both the positive and
negative data visible without extra instrumentation. On that data,
raised `WAKE_THRESHOLD` from 0.5 to 0.65 in `wakeword.py` - still well
under the weakest real attempt, with more margin against false accepts,
per this section's "bias stricter" call. Left `SLEEP_THRESHOLD`,
`PATIENCE_FRAMES`, and `COOLDOWN_S` unchanged - no real sleep-phrase
attempt happened this session (Chip typed the keyboard `sleep`
stand-in once mid-conversation instead, which was correctly ignored -
that event only fires from Off Watch, confirmed at
`coordinator.py`'s `_handle_event`); next live session will focus on
saying "Goodnight, Jack" aloud instead.

Two results logged as "garbled" from that same session turned out to be
a separate thing: STT accuracy dropping on quiet/distant speech (e.g.
"That's all for now, Jack." heard as "I saw for now Jack." at p=0.35),
not a wake-spotter miss - the spotter fired correctly in both cases.
See [4.2](#42-speech-to-text-stt) - not addressed here, flagged as a
separate, real finding about far-field STT quality.

**Sleep threshold left unchanged, 2026-10-12**: a second session that
same day focused on "Goodnight, Jack" specifically - voice only, Enter
used between cycles just to get back On Watch quickly. Of 5 real
attempts, 4 fired cleanly and printed (1.00, 1.00, 0.91, 1.00 - each
followed by 0-3 extra `[spotter]` lines as the same utterance's score
decayed across a few more frames; `COOLDOWN_S` correctly suppressed any
of those from re-firing, it's the debug *print* that isn't
cooldown-gated, printing every frame above the 0.1 floor regardless).
The 5th attempt, spoken softly, printed nothing at all - meaning it
scored under that same 0.1 floor, not merely under the 0.5 threshold.
That rules out a threshold fix: nothing between 0.1 and 0.5 would have
caught it, since it never got that high in the first place. Left
`SLEEP_THRESHOLD` at the vanilla default accordingly - matches this
section's own call that an unwanted "go quiet" is the softer failure,
less reason to bias it, and the real data here doesn't argue for moving
it either way.

One attempt in that session was a bonus data point, not a sleep-phrase
test: Chip said "Goodnight, Jack" conversationally during an On Watch
turn rather than as the fixed phrase. The spotter still scored it (the
debug print is just suppressed while On Watch - see
`coordinator.py`'s `_on_spotter_score`) but the actual transition went
through Haiku's own `MODE: NAP` tag instead, per
[4.11](#411-sleep-mode-state-machine)'s existing "no fixed phrase from On
Watch" design - worked correctly, not a new path. STT heard it as "Good
night, Jack." at p=0.42, distinctly lower than the same session's other
phrases (0.65-0.70) - consistent with the missed spotter attempt above:
people likely say "goodnight" more quietly than everyday speech, which
costs confidence on both paths the same way. Not something a threshold
number fixes either; noted as a real, cross-cutting observation rather
than acted on.

A separate, unexplained timing anomaly surfaced in the same session:
one reply's `[first audio Xs after you stopped talking]` read 5.55s
against a 3.2-3.8s baseline everywhere else that session, but - unlike
the similar-looking anomaly from the previous day (see
[4.2](#42-speech-to-text-stt)) - `stt_s` itself was perfectly normal
(1.00s) this time, so it isn't the same slow-whisper-decode pattern.
Left open; no `--save`-able root cause found yet beyond "happened once,
on a badly garbled utterance Haiku still correctly read as end-of-
session intent from."

### 4.2 Speech to Text (STT)

**Confidence/no-speech threshold methodology, 2026-09-23**: same
treatment as [4.1](#41-wake-word-spotter), decided the same day and
explicitly asked to apply the same philosophy — mechanism and starting
point now, specific numbers deferred to real testing. Found the
mechanism is already built into whisper.cpp, not something to add:
`whisper_full_params` exposes `no_speech_thold` (silence probability,
reference default 0.6), `logprob_thold` (decode confidence, default
-1.0), and `entropy_thold` (whisper.cpp's repetition/hallucination-loop
detector, default 2.4, functionally equivalent to the Python reference's
`compression_ratio_threshold`) — OpenAI's own reference defaults,
confirmed present in whisper.cpp specifically (not assumed from the
Python API), not invented for this project.

Numbers aren't set because the model size (tiny vs. base, still open —
see [4.2](specification.md#42-speech-to-text-stt)) isn't chosen and
there's no real household audio to calibrate against yet.

Clarified this is a second, distinct layer from Silero VAD, not
redundant with it: VAD decides *when to record at all*, cheaply, before
whisper.cpp ever runs; these three thresholds catch what slips past VAD
post-transcription — a noise burst energetic enough to trigger VAD but
not actual words, or genuinely garbled speech.

Same asymmetric bias as the wake/sleep thresholds, same direction and
same underlying reasoning (continuing the project's fail-closed
throughline — memory saves, self-ID, now both threshold decisions): bias
toward the reference defaults' stricter side, since trusting a garbled/
hallucinated transcript and sending it to Haiku wastes an API call and
produces an immersion-breaking non-sequitur reply, worse than a false
reject costing a repeat.

One STT-specific point beyond the number itself: a wake-word false
reject is invisible (try the phrase again), but silently dropping a
low-confidence segment mid-conversation (On Watch) would read as Jack
being broken rather than "didn't hear that." Decided the reject path
needs an explicit, in-character prompt rather than silence — the same
kind of canned-response pattern already used for idle/Asleep clips.

**A reused whisper.cpp Model drifts across calls, found and fixed
2026-10-12**: the 2026-10-11 live sessions' "text output is frequently
repeated and often garbled" complaint (same phrase coming out as totally
different, wrong text on different attempts) turned out not to be real
accuracy/noise at all. `coordinator.py` built one `STT` (and so one
underlying `pywhispercpp.model.Model`) at startup and reused it for every
utterance in the session, same as `listener.py`'s standalone mode and
this session's own first draft of `compare_stt.py`. `no_context=True`
only disables *text* context carryover between calls - it says nothing
about the Model's internal decode buffers. Proven with a real recorded
session (`coordinator.py --scratch-memory --save stt_samples/session1`,
seven utterances, a mix of short test phrases and two long quoted
passages): transcribing each saved `.wav` through one persistent `STT`,
in order, reproduced real flip-flops seen live - the same short phrase
("That's all for now, Jack.") came back with a different name each
re-run of the whole sequence, and one utterance's probability (0.26 vs.
0.30, straddling `PROB_FLOOR`) swung it between accepted and rejected
from one run to the next on identical audio. Re-running the exact same
`.wav` files through a *fresh* `STT("tiny.en")` per utterance gave fully
deterministic, consistently-correct results every time, confirming the
reused Model (not the audio or the model size) was the cause. A fresh
Model costs about 0.08-0.1s to construct (both tiny.en and base.en, Pi
5) - trivial against decode time (0.35-2.5s on this session's clips) - so
`stt.py`'s `STT.transcribe()` now builds one per call instead of once in
`__init__`. `compare_stt.py` (new - a small diagnostic tool, not part of
the automatic suite, reads a `--save` directory and runs named models
side by side for a human to judge against what was actually said) had
the same bug in its first draft and was fixed the same way. Regression
test (`tests/test_stt.py`'s `check_fresh_model_per_transcribe`) counts
real `Model()` constructions against `transcribe()` calls through one
`STT` instance; confirmed via `git stash` to fail (1 Model built for 3
calls) without the fix and pass with it.

Same recorded session also surfaced a second, independent bug: the
24.8s Preamble-quoting utterance (correctly transcribed, just one word
off - "do ordain" came out "Dour dein") was rejected as "repetition"
anyway. `is_repetition_loop()`'s rule (a 3+-word phrase appearing twice)
checked *anywhere* in the text, with no limit on distance - true
hallucination loops (every existing example, both the 2026-09-25 retry
loop and gibberish-echo cases, and this session's own
"That's all for now, Jack. That's all for now, Jack.") repeat back-to-
back, but a long, legitimate utterance can innocently reuse a short
phrase once, far apart ("the United States" at the Preamble's start and
its end). Fixed by only counting a repeat if it starts within
`n + MAX_REPEAT_GAP_WORDS` (3) words of the phrase's previous occurrence
- true loops still trigger (their repeats are adjacent), but a single
distant reuse no longer does. Added the Preamble text as a new `ACCEPT`
case and the live "That's all for now, Jack." x2 case as a new `REJECT`
case in `tests/test_stt.py`; confirmed via the same stash round-trip
that the Preamble case fails (false "repetition" reject) without the fix
and passes with it.

Net result, same recorded session re-run with both fixes: tiny.en and
base.en now agree almost everywhere and both are fully reproducible run
to run - the open "tiny vs. base" question (above, and
[CLAUDE.md](../CLAUDE.md) "Done so far" item 18) is answered by this
real, noisy-room data: tiny.en's accuracy is on par with base.en here
while running 2-2.5x faster, so tiny.en stays the default. One
remaining, much smaller-scale wrinkle: even a single fresh Model's
decode isn't bit-for-bit identical process-to-process on the same audio
(an article swapped, "The" vs. "It", in `tests/test_listener.py`'s own
fixture clip across separate runs) - almost certainly ordinary
multi-threaded (`N_THREADS=4`) floating-point reduction-order jitter,
not the across-utterance drift above, and far too small-scale to explain
the original complaint. Left alone.

**A third bug, same day, found from a second live session in a quiet
room**: with the two fixes above live, a fresh recorded session
(`coordinator.py --scratch-memory --save`, quiet house, no background
noise) still rejected two of eight utterances as "repetition" - Chip
reported he hadn't actually repeated himself (one was "Thank you, Jack.
That's all for now." - two sentences, correctly split into two separate
utterances by VAD's own end-silence gap, not a repeat at all). Checked
the saved `.wav`: `STT("tiny.en").transcribe()` on the exact bytes, no
prompt, gave the clean, correct "Thank you, Jack."; with the real
household-names `initial_prompt` (`names_prompt()`, passed to every call
for the session by `coordinator.py`), the identical audio deterministically
decoded as "Thank you Jack, thank you Jack, thank you Jack, thank" - a
genuine whisper.cpp repeat-loop hallucination, not a repeated statement.
Narrowed further: it isn't about the prompt's *wording* - a completely
unrelated prompt ("The weather today is sunny...") or even a single word
("Hello.") reproduced the same loop on the same audio just as reliably;
only an empty/`None` prompt avoided it. So *any* non-empty
`initial_prompt` can push whisper.cpp into a repeat-loop on some short
utterances, even though the same prompt measurably raises confidence on
most ordinary speech (confirmed on the other 6 of 8 utterances in this
session: every one scored higher with the prompt than without it). Since
dropping the prompt outright would lose that spelling/confidence benefit
for the common case, `STT.transcribe()` now retries once without the
prompt specifically when (and only when) the first attempt rejects as
"repetition" - a second fresh Model, same ~0.08-0.1s cost, only paid on
an already-rejected utterance. Confirmed recovering the real repro
(`tests/data/thank_you_jack_ch1.wav`, Chip's own saved "Thank you,
Jack." - committed as a fixture, same precedent as
`quick_brown_fox_ch1.wav`): `check_prompt_repetition_retried()` in
`tests/test_stt.py`, confirmed via `git stash` to fail (surfaces the
reject) without the fix and pass with it.

**Confirmed live, 2026-10-12, same day**: a second recorded session
(`stt_samples/session2`, quiet house, a real eight-turn conversation
including Chip saying "Thank you Jack. That's all for now." as one
utterance - exactly the phrase that triggered the prompt repeat-loop
above) came back 8 for 8 accepted, zero rejections, with the
household-names prompt active throughout. One minor, expected-tier
substitution noted ("how's the perch today?" heard as "how's the parrot
today?") - well within the error rate the project has always expected
from tiny.en, not a new issue. All three fixes from this day considered
closed.

**A fourth bug, same day, from a live test of the raised reply-length
target (4.4, below)**: a run with no one else around still hallucinated
two utterances Chip never spoke ("Can you tell her to say?" and "No? No?
No? No? No?") - he confirmed it was ambient noise, not digital silence
(someone else nearby talking/walking by, per his own account a couple of
exchanges later: "Oh, that was just somebody else talking, walking
by."). This is the known, already-documented gap (gibberish/other-room
speech that comes out as a plausible, confident sentence - no rule
catches that, and no-speaker-ID is itself an already-made design
decision, not revisited here). But the second hallucination, "No? No?
No? No? No?", exposed a real, separate gap in `is_repetition_loop()`:
its two rules (a 2-word phrase 3 times, or a 3-word phrase twice) can
only ever fire when the text has at least `min_words * times` words - 6
for either rule - so a 5-word single-word-repeated utterance like this
one couldn't trigger *either* rule, no matter how blatant the repeat.
Added a third rule: a single word repeated 4+ times, but kept to zero
gap (truly back-to-back, no words between) rather than the 2/3-word
rules' looser few-word tolerance - common words ("the", "a") legitimately
recur every few words in ordinary long sentences, and a looser gap on
a 1-word rule would false-positive on those (confirmed against a test
sentence using "the" four times). Added both the repro and the
ordinary-sentence check to `tests/test_stt.py`; confirmed via `git
stash` that the repro fails without the fix.

**Servo motion noise, not code, behind the "degraded" recognition,
2026-10-14**: Chip reported recognition had gotten worse - only a loud,
distinct utterance came through right. No STT/capture/listener code had
changed since the 2026-10-12 confirmation runs. Recorded sessions
(`stt_samples/session6`-`session11`, a fixed script) showed why:

- The household-names `initial_prompt` was first suspected (it
  deterministically turned "What is" into "Liz" and "perch" into
  "parrot" - both words straight from the prompt), but across all 45
  then-saved utterances it helped about as often as it hurt on
  tiny.en, and clearly helped base.en (without it, base.en rejected
  5 correct transcripts on low confidence). Kept.
- The real factor was the head servos moving. Chip ran the same script
  four ways (session7 tiny/servos on, session8 tiny/off, session9
  base/on, session10 base/off). Noise floor: about -34 dBFS with
  `--port` vs. -45 to -51 without; speech-to-noise margin 18 dB vs.
  27-31 dB. Offline, same audio for both models: servos on, tiny.en 8/17
  wrong and base.en 7/17; servos off, tiny.en 4/14 and base.en 1/14. The
  2026-10-12 sessions 1-3 (floor about -50 dBFS) appear to have run
  without `--port`, which is why they looked fine.
- It's movement, not power: the servo supply is on continuously and the
  sketch attaches all four servos at startup, so in sessions 8/10 the
  servos were powered and holding - and quiet. On Watch's ambient
  `am-attentive-sway` runs nonstop, including while someone is talking.
- Trial (session11, base.en): shrank the sway to +-3 pitch/+-1 roll with
  a ~1s hold at each end. Floor improved only ~3 dB (-37 dBFS) and
  recognition about the same (2-3/7 wrong). At 100ms resolution, the gaps
  between words sit at -20 to -30 dBFS while the head moves - close to
  speech level - and dip to about -40 only during the holds. Movement of
  any size is loud; only stopping helps. Chip kept the smaller paused
  sway anyway, for looks, pending later fine-tuning.

Next, agreed with Chip: hold the head still while the mic is open in On
Watch. First, an Off Watch wake/sleep-phrase test with and without
servos, since Off Watch's `id-idle-breathing` swings about 41deg of
pitch, and the 2026-10-12 wake calibration likely ran without `--port`
too. The tiny.en-vs-base.en default (item 34's call was made on quiet,
servo-off audio) is also still open: base.en won clearly on servo-off
audio, at about 0.5-1s more STT time per turn.

**Off Watch noise measured directly, same day**: an Off Watch wake test
with and without `--port` (sessions 12/13) matched the On Watch finding
- with servos moving, a normal voice often didn't trigger the spotter
at all (nothing printed, i.e. under the 0.1 debug floor, so no threshold
change can recover it); without, anything above a whisper did. Since
`--save` never records Off Watch audio, wrote
`tests/measure_servo_noise.py` (Capture + Motion on a fixed schedule of
modes, quiet room, nobody talking). Median mic level, 100ms slices:
still -47.8 dBFS; On Watch +-3deg sway -32.4; Off Watch 41deg breathing
-23.3, within a few dB of normal speech (about -15 to -20). That first
ad-hoc run also caught an excursion (`motion.py` starts its excursion
timer at 0, so the first Off Watch cycle plays one right away) with
bursts to -3/-9 dBFS - Chip saw the head seem to hit its mechanical stop,
though all software limits sit inside the mechanical ends; not yet
explained. The tool now disables excursions by default.

Trialled the same shrink on Off Watch breathing (+13/-28 to +-3, ~1s
holds): Off Watch median dropped ~8 dB to -31.7, the same as the On Watch
sway, and the ~10s noisy tail seen after the big swing stopped was gone.
But the 1s holds mostly sat at -34 to -40, rarely reaching the still
floor - the servos keep buzzing for a second or more after each move.
Chip could feel the easing stepping at this size. A second run with
Chip's hand resting on the head lowered moving noise by 3-4 dB but also
raised the still phases by 4-9 dB (hand contact/breathing near the mics),
so it's inconclusive beyond "some, not most, comes from the head
itself"; damped movement still sat at -35/-36.

Decided: On Watch holds the head still for as long as the mic is open
(starting at mic-open, not speech onset, given the settle time). Off
Watch, where Jack must move and listen at once, is open; Chip's
candidate fix is moving the mic array back outside the bird, isolating
it mechanically altogether.

**On Watch hold, first live run (session14, base.en, `--port`), same
day**: the head stops while the mic is open and resumes when Jack
speaks, as intended. Noise floor -45.7 dBFS (session9 moving -33.7,
session10 servos off -50.6), so the hold recovers most but not all of
the gap. Recognition 2-3/8 wrong ("How's" heard as "I was" twice,
"crew" as "courtroom" once, "That's" as "Thanks") - better than servos
moving, short of servos off. Two causes visible in the clips: Chip
spoke 3-6 dB softer than in sessions 9/10 (deliberately normal level),
and clips that opened right after a reply (utt02/05/06) start at -31 to
-36 dBFS against -44 after a fresh wake - the hold blocks new moves but
an in-flight 1.5s sway runs to completion, and the servos buzz for
about a second after it.

Chip also asked what happens if nobody speaks: as built, the head stays
frozen until speech or the 2-minute On Watch timeout. Two fixes were
proposed and **deliberately held in reserve, not built**: cap the hold
at ~8-10s of silence then re-hold at speech onset, and abort the
in-flight move when the hold starts. Chip's reasoning: a stop is a
bandaid that needs another bandaid to stay lifelike. First explore the
source instead - the head servos are AGFRC B11DLS (metal-gear, digital),
chosen for torque and reliability. Plastic gears would be quieter
acoustically, but it's unknown whether they'd be quieter by mechanical
conduction into the mic array; analog servos might move more smoothly
(less noise) or jitter at rest (more). Needs research/measurement.

**Bench servo test, 2026-10-14**: a spare B11DLS plugged into the roll
channel in place of the bird's roll servo, driven with plain `r` moves
(`tests/measure_bench_servo.py`, recordings in
`stt_samples/bench_servo*`). Two placements, same script:

| Segment | Loose, 12in away on a solid surface | Taped to the electronics enclosure |
|---|---|---|
| Still | -51.9 | -35.4 (-48.8 with its power unplugged) |
| +-3 sway, 1.5s moves | -52.0 | -34.7 |
| +-10 sway, 1.5s moves | -51.8 | -32.5 |
| +-20 sway, 1.5s moves | -48.1 | -30.8 |
| +-20, 0.4s moves | -46.7 | -22.7 |

(median dBFS of 100ms slices). Airborne, the servo is almost inaudible:
the in-bird +-3 sway's ~11dB rise (session11) can't be airborne noise.
Coupled to the enclosure, the fast move rose ~24dB to near speech level
and shifted to mostly 2-8kHz energy. The noise reaches the mic through
the structure, so mechanical isolation (servo mount grommets, a soft mount
for the XVF3800, or the array outside the bird) looks like a bigger lever
than a quieter servo alone. A candidate servo is still worth the same
taped test for comparison.

Unexpected: the taped servo, merely holding, raised the floor ~13dB as a
135-170Hz hum. Chip felt no buzz by finger, but unplugging its power
removed it (-48.8). Holding is not silent once coupled, which matters
for the On Watch hold. The bird's own held servos measured far quieter
(still -47.8, session servo_noise). Possibly because an unloaded servo
dithers more, or because the enclosure (which carries the XVF3800)
couples more directly than the head does - not determined.

**High-pass filter tried and ruled out, same day**: the in-bird servo
noise recordings (`stt_samples/servo_noise*`) put most of the motion
noise in 150-300Hz, about 10dB above 300-1000Hz, so filtering it off in
software looked like a free fix. Re-transcribed sessions 7/8/9/10/14
with base.en at no filter, 200Hz, and 300Hz (`compare_stt.py
--highpass`): word errors unchanged (session9 3/8 at all three, session7
4/9, session14 3-4/8, servos-off session10 1-3/6, session8 2/8). The
same misrecognitions survive the filter. Whisper already copes with the
low-frequency part; the damage is from the smaller (8-12dB) rise inside
the speech band, which no filter can remove without removing speech.
Mechanical isolation stands as the fix. Chip's options, in his order
of preference: a separate enclosure for the Pi, XVF3800, amp, and
speaker, with only the Arduino serial line crossing to the bird's
enclosure (the array's orientation relative to the bird needs keying,
for future DoA); heavier bird base (lead shot) plus a soft mount;
soft-mounting the array alone (unlikely enough on its own, since the
enclosure panels themselves radiate). Next cheap test before any
rework: the bird on rubber/Sorbothane pads with temporary weights,
measured with `tests/measure_servo_noise.py`.

**Bird-on-mat test, same day - soft-mounting the bird works**: bird
unbolted and set on a silicone kitchen mat (about 1in of wiring slack
allows lifting it), roll servo back in place, `tests/measure_servo_noise.py`
(default phases, excursions off; recordings in `stt_samples/servo_noise_padded*`,
`servo_noise_mat_*`). Median dBFS of 100ms slices:

| Run | Still | Off Watch | On Watch |
|---|---|---|---|
| Bolted (earlier) | -47.8 | -31.7 | -32.4 |
| Mat + 2lb lead shot, mat covering the array | -48.3 | -43.5 | -42.8 |
| Mat, no weight, array uncovered | -55.6 | -53.6 | -53.7 |
| Same, repeat | -65.2 | -55.2 | -57.5 |
| Mat + weight, array uncovered | -57.9 | -58.2 | -55.1 |

The still floor is the room (it swung -48 to -65 between runs minutes
apart), so absolute moving level is the measure, not moving-minus-still.
On the mat, motion noise drops ~23-26dB (-32 to about -55), at or below
the room's own floor. The lead shot made no difference once the array
was uncovered, so a weighted base isn't needed (at least on a mat this
soft). The covered-array run was ~12dB worse: the mat lying over the
array likely bridged vibration from the bird's base onto it - nothing
touching the bird should also touch the array or the enclosure near
it. This puts a soft-mounted bird on the existing enclosure ahead of
the two-box rework, pending a recognition check (a spoken `--save`
session with the head moving, compared against session9).

**Recognition confirmed on the mat, same day (session15)**: bird on the
mat, no weight, array uncovered, `coordinator.py --no-hold` (new flag -
head keeps swaying while the mic is open) with `--port`, same script as
sessions 9/14. Per-utterance floor (p10 of 100ms slices) and speech
level (p90), medians:

| Session | Condition | Floor | Speech | Margin | base.en wrong |
|---|---|---|---|---|---|
| session9 | bolted, moving | -29.5 | -17.8 | 11.7 | 3/8 |
| session10 | servos off | -46.4 | -22.4 | 24.0 | 1/6 |
| session14 | bolted, On Watch hold | -43.8 | -24.1 | 19.7 | 3/8 |
| session15 | mat, moving | -55.5 | -23.0 | 32.5 | 1/7 |

base.en's one miss ("House the rest of the crew") is the "How's" error
that also happens servos-off. tiny.en missed 3 (incl. "That's all for
Nanojat"), so with the noise gone base.en clearly leads - relevant to
the open tiny-vs-base default. Two further captures (utt02/utt08) were
rejected as non-speech. Conclusion: soft-mounting the bird alone solves
the servo noise problem for On Watch speech; the two-box rework and
weighted base are no longer needed on this evidence, and the On Watch
hold may be retirable. Still to check before deciding that: the Off
Watch wake phrase on the mat, and a run in a noisier house.

**Wake/sleep on the mat, same day**: `coordinator.py --port` (hold on,
tiny.en), bird on the mat, with the house noisier than any earlier run
(people moving around, neighbors' construction) - partly the
noisier-house check above. All 4 wake attempts fired over Off
Watch/Asleep motion (Off Watch 0.68 and 0.98, Asleep 1.00 and 0.99,
threshold 0.65), and "Goodnight, Jack" fired once from Off Watch (sleep
1.00) - against bolted, where a normal voice often scored under 0.1.
The first wake barely cleared; delivery not noted, so one to watch.
tiny.en misheard the two softly spoken lines: "Goodnight, Jack" as "Good
night, sir" (p=0.41) and "Time for a nap, Jack" as "Time for an app
check" (p=0.33). Haiku still did the right thing with the first; the
second only reached NAP on a follow-up. Fits session15 favoring base.en.

Decided by Chip, same day: stay on tiny.en for now. Recognition is
better on base.en, but processing time is already noticeable (first
audio ~3.0-3.3s after speech ends) and base.en adds ~0.5-1s. If base.en
wins out later, pair it with a filler (e.g. a squawk) right after the
utterance ends, so the wait reads as Jack reacting rather than lag.

### 4.15 Speaker Recognition (Voice ID)

**Enrollment flow, 2026-09-23**: decided the flow — how household
members' voices actually get enrolled — separately from the engine
choice (ECAPA-TDNN, decided earlier the same session) and from the
runtime match-confidence threshold (explicitly left undecided, expected
to get the same methodology-now/numbers-later treatment as the wake/
sleep and STT thresholds when it's tackled).

Trigger: a standalone script, not an in-conversation voice flow —
consistent with the project's ship-the-simple-thing-first pattern and
with keeping scope out of the core conversation loop while it isn't
working yet (same reasoning behind deferring home-automation). Closed
set: only names with a pre-existing `### Name` heading in `memory.md`
can be enrolled, mirroring the existing rule that household facts (and
now voices) can't be minted fresh by any automated path.

Multiple utterances, not one, and the numbers are from real research on
this exact task, not guessed: Equal Error Rate drops from ~17.6% at a
single enrollment utterance to ~8% at five or more, using the mean
(centroid) of the individual embeddings as the stored profile; ~20
seconds of total speech is reasonable practical guidance. ~5 short,
varied utterances, averaged, not a single-shot recording.

Storage decided to live outside `memory.md` entirely: embeddings are
opaque float vectors, which would break `memory.md`'s plain-markdown,
human-readable, hand-editable contract if folded in. A separate small
data store, keyed by the same household names, written only by the
enrollment script and read only by orchestration code — Haiku never
handles embeddings or raw audio directly, same posture as `memory.md`'s
own file I/O already being orchestration-owned. Re-enrollment needs no
separate design: re-running the script for a name just overwrites their
stored embedding.

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

### Issue 26

**Found 2026-09-25**, during the first playback test after the speaker
was wired. First play: `DeadMenTellNoTales.wav`, duplicated mono→2ch,
at the board's fixed 16kHz/S16_LE/2ch format straight to
`hw:CARD=Array,DEV=0`, with ALSA `PCM Playback Volume` at its
default-ish 37/60 (−23dB) — Chip heard nothing. A 4s 440Hz tone
(ffmpeg's default sine, peaking at −21dBFS) with volume raised to max
(60/60) was clearly audible. Replaying the clip at max volume: loud
enough, but mostly static.

Ruled out a file problem before blaming hardware: every `wavFiles/`
header is a plain 44-byte PCM header (format tag 1, 16kHz, 16-bit,
consistent byte rate/block align, only `fmt `/`data` chunks); the
sample data is real audio (zero-crossing rate ~0.12, vs. ~0.5 if it
were byte-swapped noise); the mono→2ch conversion was correct; and the
clips play fine on Chip's desktop. The difference was level: the tone
peaked at −21dBFS, the clips peak near 0dBFS. Replaying the clip
attenuated 20dB (still at volume 60/60) was intelligible but very quiet.
A listening ladder of the same clip at −14/−10/−6/−3dBFS put the last
clean step at −10dBFS — −6dBFS already crackled. So clipping starts
somewhere between −10 and −6dBFS at max hardware volume.

Not yet known whether the onboard amp or the speaker is what clips;
the spec already flagged the onboard amp as "reportedly mediocre."
Following the usual pattern here (decide the mechanism before the
number), no gain cap was picked. The ladder is now
`tests/test_speaker_level_ladder.py`, so the test can be re-run after
any fix.

**Narrowed 2026-09-25 (headphone test)**: Chip plugged headphones into
the XVF3800's 3.5mm jack and re-ran the ladder (volume 60/60): all four
steps (−14/−10/−6/−3dBFS) clean and plenty loud. So the USB audio
path, the XVF3800's DSP output, and its DAC are all clean near full
scale; the clipping happens only in the speaker path. Chip and Claude
both lean toward the onboard amp rather than the speaker (a 5W speaker
on a nominally 5W amp shouldn't be the weak link). Next step, Chip's
call: swap in another small speaker, or failing that, feed his existing
external amp (the one that ran plenty loud in the MY1690 → amp →
speaker build) from the XVF3800's 3.5mm jack. The bird's speaker stayed
silent while the headphones were plugged in — plugging into the jack
mutes the onboard speaker output, so it's one or the other, not both.

**Resolved 2026-10-06**: Chip wired his existing external amp (from the
old MY1690 build) between the XVF3800's 3.5mm jack and the speaker, fed
from the jack's left channel. The amp has no volume knob — gain is set
by two strap pins tied high/low, four settings total. Ran the level
ladder at each: clean at the three lower settings, clipping only at the
highest. Picked the lowest gain setting per the original plan (least
hiss, most headroom, with the other three available later if more
loudness is ever needed) — loudness at that setting was already
adequate. Extended the ladder's top step from −3dBFS to 0dBFS to check
the full digital range at that gain setting: clean throughout. Updated
`playback.py`'s `OUTPUT_GAIN_DB` from the interim −10dB cap to `0.0` —
the external amp, not a digital cap, now does the job the cap was
standing in for. Amp-vs-speaker as the original clipping culprit was
never conclusively isolated (no speaker swap test was run), but that's
now moot: the fix works regardless of which one it was.

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

### Speaker wired and first playback test

**Wired 2026-09-25**: the 2-pin JST connector arrived (ETA had been
~2026-09-27) and the speaker (40mm, 4Ω, 5W) was wired to the XVF3800's
speaker output. That unblocked the audio-*output* half of the
work list — beak-sync, idle playback, the TTS bake-off, the end-to-end
loop, and a first AEC smoke test all moved to "doable now." Only final
AEC validation and speaker-ID accuracy testing stayed blocked, now on
mounting the board to the statue rather than on the speaker. The same
day's first playback test worked end to end but found the clipping
problem logged as Issue 26.

**`wavFiles/` conversion, 2026-09-23** (Chip, commits `0fc0f40`/
`a7a9441`): all clips resampled from 44100Hz to 16kHz and three more
added (`BondJamesBond`, `FranklyMyDear`, `IAmIronman`), 19 total —
closing the work-list conversion item. Header check on 2026-09-25
(now `tests/test_wavfiles_format.py`) found all of them 16kHz/16-bit
PCM, but `IAmIronman.wav` is 2-channel where the rest are mono.
Fixed the same day: its right channel was effectively silent (peak 8
of 32767), so the left channel was kept as-is rather than averaging
both, which would have dropped the level 6dB.

### Physical construction complete

**Done 2026-10-06**: the electronics enclosure was remade to fit the
full current hardware set — Pi 5, Arduino, servo power supply, XVF3800,
external amp (see Issue 26), and speaker are all mounted inside it, and
the board is now in its final acoustic geometry relative to the speaker.
This closes out the last hardware dependency behind CLAUDE.md's former
"Blocked until the XVF3800 is mounted" list: final AEC validation and
speaker-ID accuracy testing (Issue 1) move to doable-now, since the
geometry that was going to change no longer will. Barring future bugs
or design changes, physical construction itself is done.

### Work-list items resolved before this log existed

- **Pi↔Arduino serial protocol design** — resolved/locked down
  2026-09-15; see Issue 9.
- **`arduino-cli` toolchain confirmation** — resolved 2026-09-14; see
  "Arduino toolchain and servo wiring" above.
- **DoA reading via `xvf_host AEC_AZIMUTH_VALUES`** — investigated
  2026-09-20; real gap found (no `xvf_host` tool on this Pi), moved from
  "blocked on the XVF3800" to "blocked on finding Seeed's tool/docs"; see
  "reSpeaker XVF3800 arrival and DoA investigation" above.

### Superseded source docs archived (2026-10-10)

Moved four planning docs to `docs/archive/` with a `-2026-10-10` suffix
(the folder already held undated 2026-09-21 snapshots of `CLAUDE.md`,
`specification.md`, and `parrot-project-brief.md`, so dating avoids
collisions), to declutter `docs/` down to the working set:
`gesture-library.md` (fully translated into `gesture-catalog.yaml`),
`Arduino-command-structure.md` (superseded by spec 4.13 and
`ServoControl.ino`; its open questions all resolved or tracked as Open
Issues), `jarvis-handoff-notes.md` (Jarvis is a separate project), and
`captain-jack-goals-objectives-user-scenarios.md` (fully absorbed into
spec sections 1-2 — spot-checked its distinctive items). Live links in
the spec, brief, catalog, and `ServoControl.ino` were repointed; older
mentions in this log were left as written.

Same day, also archived `exercise_hardware.py` (repo root) as
`docs/archive/exercise_hardware-2026-10-10.py`: `motion.py` is a faithful
port of its logic and its standalone `--mode/--dry-run` mode covers the
harness role. Nothing imported it. Present-tense references in
`motion.py`, `serial_link.py`, `tests/test_motion.py`, and `CLAUDE.md`
item 7 were updated; "ported from `exercise_hardware.py`" mentions in
the spec and tests.md stay, since they're still true. The archived copy
won't run as-is from its new location (its `CATALOG_PATH` resolves
relative to its own directory); left that way, with only a comment added
at the top and at `CATALOG_PATH` saying so.

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

### 3.3 Speaker

**Specified 2026-09-25**: earlier docs described the speaker only as a
carry-over from the previous prototype build; Chip pinned down its
actual specs — 40mm diameter, 4Ω, 5W.

**Connected 2026-09-25**: wired to the XVF3800's own 2-pin JST output,
per the AEC-reference requirement. The first playback test showed it
clips above roughly −10dBFS even at max hardware volume — see Issue 26.

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

### 4.8 Beak-Sync (RMS Envelope Extraction)

**Built 2026-10-06** (build step 6): `serial_link.py` (the Serial writer
thread) and beak-sync added to `playback.py`'s audio callback.

**Beak direction found while building this**: `specification.md` section
4.13 had drifted from the real firmware (it said beak was nominal 0–45;
the firmware's actual `BEAK_RANGE` is 60) and never stated which
direction was open vs. closed. Checked `ServoControl.ino` directly
rather than trust the stale prose: `b0` = open, `b60` = fully closed, and
the servo's own startup/rest position is closed. Fixed 4.13's text
(beak and head axis ranges all needed correcting, not just beak) while
in there — see that section's history for the corrected numbers.
Mapping an RMS envelope to beak angle therefore needs an *inverse*
relationship (louder audio → lower angle, since 0 is open), not the
naive "higher amplitude, higher number" a reader might assume without
checking.

**Output-latency delay, designed from data Playback already had**: the
spec's original framing ("audio playback likely needs a small
deliberate delay... accounting for RMS processing, command
transmission, and mechanical response time") suggested a bespoke
calibration pass would be needed. Realized while implementing that
Playback already timestamps every block with its `dac_time` (the stream
clock's prediction of when that block's audio actually reaches the
speaker), originally added for `wait_played()`'s and the Coordinator's
own timing needs — the same value a beak command needs to know *when*
to go out. So the Serial writer just holds a beak command until
`now() >= dac_time`, rather than needing a separately-derived delay
constant. Only a small residual (`ALIGNMENT_FUDGE_S`, serial
transmission + servo response, expected near zero) is left to tune, and
it reuses the already-recorded `AlignmentTone.wav` rather than needing a
new calibration script: playing it through `playback.py --beak` already
opens/closes the beak in sync with the tone via the normal beak-sync
path, so watching/listening to that *is* the calibration procedure.

**Envelope mapping defaults** (floor −40dBFS, ceiling −15dBFS, attack
20ms, release 100ms): reasoned from typical speech RMS levels and what
reads as a natural mouth-flap rhythm, not measured against real
recordings — explicitly a starting point for the same "ship a
reasonable default, tune by watching the real bird" pattern already used
for gesture amplitudes (Issue 25) and the TTS voice pick. Not yet tuned
against a live listen.

**First live watch, 2026-10-06**: played `AlignmentTone.wav` through
`playback.py --beak` with Chip watching the real bird. First attempt
sent nothing at all — see "Debounce-vs-throttle bug" below, found and
fixed the same session. Once fixed, Chip counted 10 open/close cycles
total: 2 from `ServoControl.ino`'s own startup self-test (it does two
full open-close cycles, not one — confirmed directly from the firmware
source) plus the 8 tone/silence reps, matching exactly. 7 of the 8 tone
cycles looked well-synced by eye; the first (the 3rd cycle overall)
consistently started late (beak opened after the tone had already
started, closed on time) across multiple runs — repeatable, not random
jitter per Chip's observation.

Ruled out before guessing further: (1) checked `AlignmentTone.wav`
itself directly (RMS per 10ms window) — clean ~100ms of near-silence
then an immediate, click-free jump to the tone level; not a file
artifact. (2) Hypothesized a device "pre-roll" startup latency spike
(dac_time running further ahead of now() right after the stream starts,
settling to steady-state later) — checked by logging dac_time/now() for
the first 40 blocks of a real stream: the gap is already at its
steady-state ~100-125ms from block 0, no spike. (3) Hypothesized a
Python-side queueing delay specific to the first command — checked by
tracing the actual queue-to-send latency per command through the real
Playback+SerialWriter path (dry-run, no Arduino needed): identically
~97-125ms for command 0 as for every later one, including right across
the first closed→open transition. None of these explain it.

Chip's read, which the evidence doesn't contradict: the servo itself
was already moving seconds earlier (finishing its own boot self-test),
so cold-servo stiction doesn't fit either — pointing instead at
something specific to the very *first command* reaching the Arduino
over serial specifically, not a Pi-side timing question at all.
Candidate mechanism: `ServoControl.ino`'s `parseInt()` waits up to a 5ms
timeout for a terminator after a bare `b<BB>` command (nothing follows
it on the wire) - a first-parse quirk on that path isn't ruled out.

**Two experiments applied together, 2026-10-06** (`serial_link.py`):
widened `ARDUINO_BOOT_DELAY_S` from 3.5s to 5.0s (more settle time after
the DTR reset), and added `WARMUP_CMD` (`t100`, sent once right after
boot, before any real traffic) — stages a move duration without
triggering a move or touching the beak, so it's invisible if it does
nothing, but gives the Arduino's parser one full cycle to run before a
command that actually needs to look right. Deliberately not isolated
(tried both at once rather than one at a time) given the session was
wrapping up.

**Re-watched same day, after both changes**: Chip recorded a second
video and reported all 8 cycles, including the first, now look evenly
timed by eye — "visually, the problem is fixed... very similar timing to
the other 7." Not root-caused (don't know which of the two changes
mattered, or whether the suspected `parseInt()` quirk was really the
mechanism), and not yet confirmed by measurement — Chip's frame-matched
video analysis against the audio waveform is still in progress,
off-line, and will also serve as the real check on whether this holds
up under precise measurement rather than just looking right by eye.

**`ALIGNMENT_FUDGE_S` measured, 2026-10-07**: Chip brought back the
frame-by-frame (30fps) analysis of the second video. Before trusting his
eyeballed frame timestamps, verified the file's own tone-on/off timing
precisely (threshold-crossing the RMS at 2ms resolution, not the ~10ms
windows used for the earlier "is there noise before the first tone"
check): each rep turns on at +106ms and off at +608ms relative to the
clip start, not the nominal 0ms/500ms Chip had assumed for his
500ms-from-onset closing anchor — reassuringly, that anchor (+606ms)
turned out only ~2ms off the true +608ms offset, so his frame counts
were trustworthy ground truth, not an artifact of a wrong reference
point.

His data: opening, beak closed at frame 0 (sound onset), 5-10% open at
frame 1 (+33ms), ~50% at frame 2 (+67ms), 100% at frame 3 (+100ms).
Closing (measured from the +500ms-from-onset anchor, ~2ms before the
true offset): 100% open at that anchor, ~50% closed one frame later
(+33ms), fully closed by two frames later (+67ms).

Math check against the design: with `ALIGNMENT_FUDGE_S` still at 0 and
a 20ms attack time constant, a response starting exactly at the true
sound onset would already predict ~80% open by frame 1 — not the 5-10%
observed. That gap is itself the measurement: the beak doesn't start
moving when the sound does, it starts moving about one frame (~30ms)
late, on both edges (the closing edge hadn't started at all by the true
tone-off instant either). Once that delay is backed out, the opening
ramp's shape (barely started at +33ms, ~100% by +100ms) is a reasonable
match for the existing 20ms attack constant, so that wasn't changed.
Updated `ALIGNMENT_FUDGE_S` from `0.0` to `0.03` in `serial_link.py`.

Secondary, lower-confidence finding from the same data: the closing
edge looked faster than the 100ms release time constant would predict
(visually complete in ~2 frames/~65ms, where 100ms would need several
hundred ms to look fully settled). Not applied — Chip himself flagged
the closing edge as harder to read from the waveform than the opening
edge when he first reported this, and release's actual job (preventing
a stutter between syllables in continuous speech) is better tested by
listening to real conversation once beak-sync is wired into the live
loop (step 7) than by further analysis of one on/off test tone. Left as
an open question in `specification.md` section 4.8 rather than acted on.

**Release time constant confirmed against real speech, 2026-10-07**:
exactly the retest suggested above, now that step 7 is live. Chip
watched `playback.py wavFiles/BilgePumpForAnger.wav --beak` (a clean,
dry `kokoro-pi/am_santa` clip - the same voice/engine Jack actually
speaks with, no reverb like the earlier movie-line clip he tried
first and found harder to read), recording video again for a
frame-by-frame look later. Verdict: "looks about right, closing does
not seem too early" - `BEAK_RELEASE_S = 0.10` stands as-is. Closes the
open question left above; nothing to change in `playback.py`.

### Debounce-vs-throttle bug (first live test sent nothing at all)

**Found and fixed 2026-10-06**, same first live watch session, before
the "first cycle" finding above: the original design held a single
"latest" beak value and released it once `now()` reached its own
`dac_time`. Measured against the real device, `dac_time` runs a fairly
constant ~100-120ms ahead of `now()`, and blocks arrive every 20ms -
faster than that gap can close. Every new block replaced the pending
one and reset the target another ~100ms further out before the old
target could ever be reached - a debounce pattern (reset the timer on
every new event) applied to a continuous 50Hz stream, which by
construction never goes quiet long enough to fire. Confirmed nothing
was ever sent in either of the first two live attempts (zero "-> bXX"
lines in both). Replaced the single slot with a small bounded FIFO delay
line (`BEAK_QUEUE_MAXLEN=15`, well above the measured ~5-6 block
pipeline depth): the front of the queue is always the *oldest* pending
value, whose target time only gets closer as real time passes, so it
converges to a steady lag instead of a receding one. A separate
shutdown-ordering bug (`player.stop()` before `writer.stop()` let the
writer thread query a torn-down stream's `.time` and crash silently) was
found and fixed in the same pass - see `serial_link.py`'s and
`playback.py`'s own history in version control for both fixes' full
detail.

### 4.9 Direction of Arrival (DoA) Reader

**Access found, 2026-10-15.** The 2026-09-20 search (see "reSpeaker
XVF3800 arrival and DoA investigation" above) only looked on this Pi.
Seeed's GitHub repo (`respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY`)
has both an `rpi_64bit` `xvf_host` binary and a short Python script,
`python_control/respeaker_get_doa.py`, that reads `DOA_VALUE` and
`AEC_AZIMUTH_VALUES` with plain USB vendor control requests (pyusb).
Used the Python route - readable, nothing to install but pyusb. The
board's USB node is root-only, so a udev rule giving `plugdev` access was
added (Chip ran it); a plain `udevadm trigger` didn't apply it to the
already-plugged board, `--action=add` did. Firmware reads 2.0.6.
`doa.py` wraps it.

**First walk-around, 2026-10-15 - inconclusive.** Jack spoke each
position; Chip counted aloud ~10s at front, front-left, left,
front-right, right (about 4ft, angles by eye), then quiet. Good: the
reading froze while Jack spoke (his own voice doesn't steer it) and moved
for Chip's voice. Not clean: it takes ~1-2s to settle and sweeps through
the angles in between; the settled values didn't step around the circle
in order (speech-flagged, last 5s of each window: front 100 with a ±114
spread - 348 for most of the window, then 150; front-left 271; left
296, ±108; front-right 126; right 173; quiet 125). 150 turned up in three
positions and 125 in the quiet stretch, flagged as speech. Likely
causes, per Chip: other household sounds, him still moving at the start
of windows, rough angles, and the bird sitting a little off axis on the
towel. The board itself is flat, two mics parallel to the enclosure's
front edge (mimicking Seeed's own enclosure), and Jack will face that
edge once mounted. Agreed to redo it after the remount, with
`tests/doa_walkaround.py` (longer windows, scores only the settled end
of each). The head cock only needs left vs. right, so it may work even
if fine angles stay rough.

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

**TTS-sourced clips pre-rendered, not live, 2026-10-06**: Chip is
supplementing Jack's Off Watch one-liners (~20 collected so far, still
gathering) with philosophical quotes — a large, readily available
supply, even though quoting philosophers isn't really in Jack's pirate
character. Design question raised: run the text through TTS live, every
time it plays, or render once and store as an ordinary `wavFiles/` clip?
Decided: render once, store as WAV, same as the existing recorded clips.

Reasoning, roughly in order of how much it mattered:
- Off Watch is exactly the mode where openWakeWord runs continuously
  for the wake phrase; live synthesis every 30-90 seconds would compete
  with that always-on detection for CPU, where a pre-rendered clip costs
  nothing at playback beyond reading bytes.
- Wav-Paired gestures (4.12) are scripted against a *known* clip
  duration; live synthesis time varies with text length and system
  load, which would break that pairing mechanism as designed.
- Quality control: philosophical quotes bring in exactly the vocabulary
  TTS mispronounces (archaic phrasing, foreign names, Latin phrases).
  Pre-rendering means listening to each line once during curation and
  fixing or dropping bad ones, rather than a bad pronunciation
  surfacing live in front of the household.
- Storage turned out not to be a real factor either way: at the
  canonical 16kHz/16-bit mono format, even a few hundred clips is tens
  of MB.

The one real downside — if the TTS voice/engine ever changes, every
pre-rendered clip needs regenerating — is mitigated by
`wavFiles/manifest.yaml`, a new sidecar file tracking each TTS-sourced
clip's source text, category (joke/quote), attribution (quotes only),
and the engine/voice it was last rendered with. Scoped to TTS-sourced
clips only; the pre-existing recorded/movie-line clips never went
through TTS and have no source text to track. Not populated yet — Chip
hasn't finalized the joke list or started picking quotes; the schema
and an example entry are in place, and the small batch-render script
that will read this file and call `tts.py`'s existing synthesize/
resample functions is deliberately not written yet, since there's
nothing real to render against.

**Content finalized and rendered, 2026-10-07**: Chip filled in
`wavFiles/manifest.yaml` with ~90 entries (jokes plus philosophical
quotes) and asked for a syntax review before rendering.

Found before trusting it: the file didn't actually parse — `clips: []`
was followed by top-level `- file:` items that were never nested under
it, a structural bug, not a cosmetic one (PyYAML: "expected <block end>,
but found '-'"). Also found three sets of accidentally-duplicated
filenames from copy-pasting entries without renaming them
(`InARoomAlone.wav` used for three unrelated quotes, `NothingPermanent.wav`
and `InsufficientEvidence.wav` each for two) — each would have silently
overwritten the previous render, permanently losing whichever clip
rendered first. Renamed the extras to match their own content rather
than just appending "II"/"III" to the wrong name. Several entries also
had unbalanced quote marks inside `text` (an opening `'` with no
matching close, or vice versa, mostly from editing a template by hand)
— fixed; one entry's nested quoting (a quote about quoting Greek
etymology) was simplified rather than made to nest correctly, since TTS
doesn't need the punctuation and the nesting was genuinely ambiguous.
Left Chip's actual content and attribution choices alone, including
loosely-sourced ones (a "best quotes" listicle-style attribution, one
quote attributed just to "Alex") — those are curatorial calls, not bugs.

Tone check on the two personal items Chip flagged (jokes at his own
expense as "retired and aged," and one nod to Claude via a cat/Claude
pun): both land as the genre of warm, groan-worthy pun they're going
for, nothing read as mean-spirited.

Chip then invited Claude to add content of its own — remixes of a few
of his quotes in Jack's voice, new quotes treated the same way, and
wholly original lines — attributed "Claude as Captain Jack[, misquoting/
paraphrasing X]" per his suggested convention, explicitly budgeted "up
to the remainder of this 5-hour period's tokens." Added 24 entries,
grounded in `memory/identity.md`'s Persona section (nautical speech
woven into ordinary sentences, not forced into every line; salty
stand-ins, never cursing; short). 144 entries total, no duplicates.

**Rendered the same day**: wrote `generate_idle_clips.py` — reads the
manifest, calls `tts.py`'s existing `TTS.synthesize()` per entry
(already resamples to the canonical format), writes `wavFiles/<file>`.
Deliberately one-directional (manifest → files, never the reverse) so
the manifest's hand-written comments and formatting are never at risk
from a render pass — `rendered`/`engine` get updated by hand, not by the
script, when a real re-render happens. All 144 clips rendered clean in
~5.3 minutes; `tests/test_wavfiles_format.py` (glob-based, no file list
to update) now covers all 163 `wavFiles/` clips automatically and
passes. Format verified programmatically; actual pronunciation/quality
of the new content needs Chip listening for real, not something Claude
can judge directly.

**Recategorized 2026-10-10**: Chip pointed out that Claude's original
lines had been tagged `joke` though most are reflective rather than
funny, and `quote` doesn't fit a remix either. Added a third category,
`saying` (Jack speaking in his own voice: original, or a real quote
recast as his own), defined in the manifest header alongside sharpened
`joke`/`quote` definitions. Dividing line between `quote` and `saying`
is how the clip text presents itself: `"X said, '...'"` is a quote
(including translations); a line Jack speaks as his own is a saying,
with the inspiring source kept in `attribution`. Moved 26 entries to
`saying`: all 24 of Claude's, plus Chip's `JoyShared` (Jack-voiced
Tiedge paraphrase) and `TheUnexaminedLifeSquawk` (Jack-voiced, no "said"
framing) — Chip okayed changing his own entries too, pending his later
review. Groucho Marx's two jokes stay `joke`. No re-render needed;
nothing reads `category` yet.

**Asleep lines rendered 2026-10-10**: `gesture-catalog.yaml`'s
`wavs.asleep` pool had named 8 files since 2026-09-20 with none
existing; their text was only in spec 4.10's prose. Nothing was
blocking them — they just predated the manifest/generator path. Added
them to the manifest as `saying` and rendered them. Chip's listening
verdict: the 3 `goodnight_phrase` replies are fine (same too-long
comma pauses as every clip, deliberately not tackled now); the
`idle_timeout` lines sounded addressed to an audience rather than
muttered to himself; and `SleepyMumble.wav` ("Mmph... 'nother day
done...") came out spelled letter by letter, M-M-P-H — dropped from
the manifest, to be a recorded clip instead.

Kokoro has no tone/emotion parameter, so "softer, said to self" was
approximated with the levers it has. Five variants of "Eight bells"
auditioned on the bird: (1) as rendered; (2) 0.85 speed, -6dB; (3) #2
with the text lowercased and ending in "..." instead of "." so the
pitch falls away; (4) #3 plus a 2.5kHz lowpass for a muffled sound; (5)
#3 with the voice style vector blended 75% `am_santa` / 25%
`am_michael`. Chip picked #5 by ear. Implemented as a named delivery,
`to_self`, in `generate_idle_clips.py`'s `DELIVERIES` table, selected
per entry by a new optional manifest field `delivery` — so the recipe
lives in one place and any future muttered line reuses it. The 4
remaining `idle_timeout` lines were re-rendered with it and confirmed
by Chip on the bird.

**Asleep entry wired, 2026-10-10**: `start_nap(why, context)` now tells
Motion how Asleep was entered — `goodnight_phrase` (sleep-phrase
stand-in), `idle_timeout` (Off Watch's 15-minute timeout), or `None`
(Haiku's `MODE: NAP`) — via a new `Motion.fall_asleep(context)`. The
settle itself runs on the Motion thread at the top of its next Asleep
step, not in the Coordinator, so a gesture already in flight finishes
first (same no-preemption rule as every other transition, issue 24);
a `set_mode()` before Motion gets there cancels it, so being woken
immediately doesn't play a stale settle. The wav is played through
Motion too, matching how Off Watch idle clips work — which means a
voice-only run (no `--port`/`--dry-run`) gets no settle line, same as it
gets no idle clips. Listed files that don't exist are filtered out of
the pick, rather than `play_random_wav()`'s skip-the-audio-but-still-
gesture behavior, so the missing `SleepyMumble.wav` never produces a
silent settle. Checked against the real catalog without hardware: each
context picks from its own pool, ~2.5s settle. `sl-waking-up` on wake
from Asleep (spec 4.10's loop) is still not played — a separate gap.

### 4.11 Sleep-Mode State Machine

**`MODE:` meta-tag, 2026-10-07**: implementing the Off Watch/On
Watch/Asleep transitions needed a way for Jack to signal "this
conversation (or watch) is winding down" from inside a normal reply,
mirroring the problem the `MEMORY:` line already solves for proposed
facts (see [4.5](specification.md#45-memory-subsystem)). Rather than
inventing a separate mechanism, `orchestrate.py` reuses the same
pattern: a new trailing `MODE: NONE|END_SESSION|NAP` line, sitting right
before `MEMORY:` (which stays the true last line of the reply),
`split_mode_line()` splits it off the same fail-closed way
`split_memory_line()` does — a missing or malformed line (e.g. an older
reply with no `MODE:` line at all) is treated as `NONE` rather than
guessed at. `take_turn()`'s `Turn` dataclass gained a third field,
`mode`, threaded through unchanged into the Coordinator.
`memory/identity.md` gained a new "Ending the session" section (placed
before "Memory") teaching Haiku the three values and that signaling
either one should come with a natural in-character sign-off as the
spoken reply itself, not a silent tag with an unrelated line. Tested in
`tests/test_mode_tag.py` with a fake Haiku client — no real API call
needed to verify the parsing/wiring.

**Full state machine wired into `coordinator.py`, same day**: the
Coordinator now owns all three modes, not just Off Watch/On Watch.
Transitions, per [specification.md#411](specification.md#411-sleep-mode-state-machine):
Haiku's `MODE:` tag (applied once the reply finishes playing, not the
instant it's received, so the in-character sign-off is actually heard
first) drives On Watch's two exits; a keyboard stand-in for "Goodnight,
Jack" (type `sleep` then Enter, alongside the existing bare-Enter wake
stand-in) and a 15-minute no-wake idle timeout drive Off Watch's exit to
Asleep; waking from Asleep goes straight back to On Watch, never through
Off Watch, per the spec's explicit call. The run loop's per-event
dispatch was factored out into `_handle_event()`/`_handle_timeout()`
specifically so tests could drive every transition directly without
starting the real audio threads — `tests/test_coordinator.py`'s
`check_state_machine()` exercises all of them (both `MODE:` values, the
plain `NONE` case, both stand-in phrases, both timeouts, and the
Asleep-skips-Off-Watch wake path) against a fake Haiku client.

Motion ([4.12](#412-gesture-engine-and-catalog)) and the Serial writer
([4.13](specification.md#413-pi-to-arduino-serial-link)) are wired in
too, but only when asked for (`--port`/`--dry-run`) — a bare
`--scratch-memory` run or any automatic test still gets `None` for both,
so nothing here needed real hardware to test. `set_mode()` is called on
every transition method (`start_session`/`end_session`/`start_nap`) so
Motion's ambient/excursion behavior always matches the Coordinator's own
mode. Confirmed end to end in dry-run (no Arduino attached): Capture,
Listener, Playback, the dry-run Serial writer, Motion, and TTS all start
and stop cleanly together.

**Reversed tag order found live, 2026-10-11**: wiring the real
`WakeSpotter` into `coordinator.py` ([4.16](#416-runtime-integration-end-to-end-turn)
history) prompted a fresh live `--port` watch, which caught a real bug
unrelated to the wake-word work itself: two replies had `MEMORY: NONE`
spoken aloud by TTS instead of being silently stripped. Root cause:
`split_memory_line()` only ever looks at the literal last line of the
reply for `MEMORY:`, but Haiku doesn't always keep to the documented
`MODE:`-then-`MEMORY:`-last order - these two replies had `MEMORY:`
*before* `MODE:`, so the true last line was `MODE:`, not `MEMORY:`, and
the memory-line search came up empty while `split_mode_line()` (run
second, on the untouched full text) still found and correctly stripped
`MODE:` off the end - leaving `MEMORY: NONE` stranded in the spoken
text. `MODE:`'s own transition still fired correctly throughout (Haiku
reliably signaled `END_SESSION`/`NAP` in-conversation during this same
test), so this was purely a stripping bug, not a signal-detection one.
Fixed with a new `split_tags()` that tries `split_mode_line()` first -
if `MODE:` turns out to already be the true last line, `MEMORY:` (if
present) is now exposed as the new last line for `split_memory_line()`
to find correctly regardless of which order Haiku used; falls back to
the original order unchanged otherwise. `take_turn()` now calls
`split_tags()` instead of the two functions directly;
`tests/test_mode_tag.py` gained `check_reversed_tag_order()`, confirmed
to fail without the fix and pass with it.

**Timeouts left as-is, decided 2026-10-12**: asked Chip whether the
2-minute On Watch / 15-minute Off Watch numbers feel right now that
there's real usage to judge by. His call: don't tune either from "feel"
at all - a deliberate test session doesn't reproduce a real social
conversation's pacing (a 2-minute silent gap feels long sitting there
testing it, but might be unremarkable mid-conversation with other things
going on), and the actual comparable failure mode is well known and
worth avoiding: Alexa's timeout is seconds, not minutes, and it visibly
drops off household conversations that are still going. Both numbers
stand unchanged; the wake/sleep-phrase spotter's own real-audio
threshold calibration (spec 4.1's methodology) is separate from this
section and is now done for the wake phrase and checked-and-left-alone
for the sleep phrase - see [4.1](#41-wake-word-spotter)'s 2026-10-12
entries.

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

### 4.13 Pi to Arduino Serial Link

**Startup head snap traced to back-to-back resets, 2026-10-15.** Chip saw
the head pitch violently full forward, hold, return to rest, then the
beak self-test, at program start. Each step below ruled something out,
with Chip watching the bird:

| Test | Lurch? | Rules out / shows |
|---|---|---|
| Sketch variant waiting 3s before attaching servos, one reset | No | (inconclusive alone) |
| Normal sketch, one reset by opening the port | No | `setup()`'s attach/write sequence |
| Squawk + speech playback while logging Arduino output | No; no mid-run reboot | 5V brownout from the amp (it's fed from the RedBoard) |
| 15 DTR resets, 5s apart | All 15, pitch only | random pulse truncation at reset (would be ~1 in 10) |
| Test sketch stopping only pitch's pulses, line LOW then floating, 4s each | No | servo going limp on signal loss (it holds) |
| 6 DTR resets, gaps 20/20/5/20/5/20s | Only the two after 5s gaps | **trigger: a reset within a few seconds of the previous one** |

The head goes forward at the reset and stays there until `setup()` runs
~1.6s later. Mechanism not found (a scope on the pitch signal line is
the next step if it ever matters); one anomaly - the port-close reset 5s
after the last test reset didn't lurch. In practice back-to-back resets
came from a program exiting (closing the port resets too, via HUPCL
dropping DTR) and another starting within seconds.

Fix: `serial_link.py` clears HUPCL on open, so only the first open after
boot resets. Side effects handled: closing no longer returns the head to
rest, so `Motion.stop()` now does it explicitly and `SerialWriter.stop()`
flushes queued head commands; programs no longer trigger the beak
self-test on exit. Confirmed live: four runs back to back 1.5s apart -
one reset (the first open), no snaps, smooth returns to rest, and a
final open produced no boot message. Chip will watch for recurrences;
a snap at the first connect after boot alone would be tolerable.

### 4.14 Arduino Firmware

**SoftwareSerial interference, noted at MY1690 removal**: SoftwareSerial
was observed to interfere with the servo easing library in the prior
MY1690-era design, and was removed along with the MY1690 (see 3.7).
Firmware must not reintroduce SoftwareSerial alongside the easing library
without further research into that interaction.

### 4.16 Runtime Integration (End-to-End Turn)

**Designed 2026-09-25**: the "interconnection" session planned at the
end of the 2026-09-23 audio-pipeline design session. Each module
section in the spec already listed its own interfaces, but nothing
described a whole turn or which part of the program owns the mic, the
speaker, and the serial port. Claude proposed the design; Chip made the
three real choices, all as recommended:

- **One process with threads**, over asyncio or several cooperating
  processes. asyncio was rejected because nearly every audio/ML library
  involved blocks, so they'd need wrapping in threads anyway, and
  async/await code is harder for Chip to read than threads plus queues,
  which map directly onto how the same program would be structured in
  C. Multiple processes would isolate crashes but add IPC plumbing and
  make sharing one mic stream between the wake-word spotter, VAD, and
  speaker-ID awkward. The threads model works because whisper.cpp,
  openWakeWord (onnxruntime), and the TTS engines do their heavy
  compute in native code that releases Python's interpreter lock.
- **Turn-taking, not barge-in**, for the first build. Barge-in depends
  on AEC keeping Jack's own voice out of the mic, not validated until
  the board is mounted, and adds cancel paths through TTS, Playback, and
  beak-sync. Parked as spec §6 item 5.
- **Sentence-by-sentence TTS**, over synthesizing the whole reply
  first: on a long reply the whole-reply approach would leave a
  multi-second silence before Jack starts talking.

Two consequences Claude settled without a separate decision, since they
follow from choices already made: beak-sync lives inside the Playback
thread (it's the one place every played sound passes through, which
also keeps it in step with what is actually being written to the
device), and the interim −10dB output gain cap from Issue 26 lives in
that same step. The keyboard stand-in for the wake word came out of the
same discussion: training the two custom openWakeWord models needs a
GPU (e.g. a Colab notebook), not the Pi, so it shouldn't gate the first
voice loop.

Same session, cleanup: spec 4.8 and 4.12 still named the long-retired
`BEAK <0–255>`/`HEAD` commands; updated to 4.13's `b<BB>` and
`p`/`r`/`y`/`t`/`s`.

**Build step 1, 2026-09-25 — Playback**: `playback.py`. Audio library
choice: `sounddevice` (PortAudio, needs the `libportaudio2` system
package) over `pyalsaaudio` (needs the ALSA dev headers and a compile).
`sounddevice` is the more widely used library, and its callback mode
reports each output block's DAC time (when those samples actually reach
the speaker), which beak-sync's latency compensation (step 6) and the
Listener's post-playback hold-off both need. Callback mode also means
the device is fed silence automatically whenever nothing is queued, with
no underrun handling. The XVF3800 is located by name, not ALSA card
number, since card numbers can change across boots. Verified by ear
twice: two clips back to back, clean, in order, no gap or click.

**Build step 2, 2026-09-25 — Capture and the channel choice**:
`capture.py`. The XVF3800's 2-channel capture stream carries the same
speech on both channels (correlation 0.92) but processed differently.
A 5-second recording of Chip talking at normal volume from a few feet
away: channel 0 was about 5dB hotter, hit 0dBFS with 61 samples pinned
at full scale, and its background dropped from −63 to −73dBFS after the
speech stopped (noise suppression gating down). Channel 1 peaked at
−8dBFS with no flattened peaks and kept a steady −60dBFS background.
Played back through the bird, Chip heard both at about the same volume,
with "some clipping" in each, and channel 1 "definitely cleaner."
Channel 0's clipping is ordinary AGC overshoot: the gain ramps up during
the quiet lead-in, and the first loud syllables overshoot before it
pulls back. AGC maximum gain and speed are tunable on the XVF3800, but
only through Seeed's control tool, which is still missing. Channel 1's
heard crackle isn't in its samples, so it's either analog overload or
processing artifacts before the ADC, or the playback path; not yet
resolved. Chose channel 1 for recognition: digital clipping is exactly
the distortion that hurts Whisper and the wake-word models, and a steady
background suits Silero VAD's end-pointing better than a gated one.

Also checked the same day: Capture and Playback run at the same time
as separate streams on one board, with no overflows, and their
timestamps share one clock, which the Listener's post-playback hold-off
depends on. While a clip played, channel 1 barely rose above the room
background: a first hint that AEC removes Jack's own voice, but at
low playback level in a noisy room, so not a validation.

**Build step 3, 2026-09-25 — Listener and STT**: `listener.py` +
`stt.py`. Library choices: `pywhispercpp` ships a prebuilt wheel for
this Pi (aarch64, Python 3.13), so whisper.cpp needed no compile and no
`cmake`; Silero VAD runs directly on `onnxruntime` from its ONNX model
(v5.1.2), avoiding the `silero-vad` pip package's PyTorch dependency.
English-only `.en` Whisper models, more accurate than the multilingual
ones at the same size for an English-speaking household.

*Speed*: out of the box, whisper.cpp took 2.0s (tiny.en) and 4.9s
(base.en) on a 5-second clip, about the same for any utterance length,
because it always encodes a padded 30-second window. The prebuilt wheel
is also compiled for baseline ARM only (NEON + FMA), not the Pi 5's
fp16 and dot-product instructions. Shrinking the window (`audio_ctx`)
to fit the utterance was tried first, as a single setting: 10-second
window 0.68s (tiny) / 1.65s (base), 6.4-second window 0.46s / 1.09s,
but the tighter window hurt accuracy on both. Settled on a window twice
the utterance length (minimum ~5s) as the starting point. A Pi-tuned
source build is parked as a later option if speed is still short.

*Rejection*: whisper.cpp's three native thresholds didn't reject pure
digital silence, where tiny.en produced "you". The binding doesn't
expose per-segment no-speech probability, and average token confidence
doesn't separate cleanly (0.37 for "you" vs 0.43 for base.en's correct
transcript). Realistic non-speech (room noise from a real recording,
and white noise) came back as annotations like `[BLANK_AUDIO]` or
`(water spraying)`, or empty, and is rejected once those are stripped.
Digital silence never comes off the live mic, so no blocklist yet.

*Live test*: Chip spoke the six suggested test sentences (the long
one being the Gettysburg opening); the first two ("Ahoy, Captain Jack", the weather question)
were said before listening began, since there was no way to tell when
it started. Five utterances came through, all complete, with two word
errors: "Kath's" heard as "Cat's", and tiny.en's "Four-scorer" (base.en
got "Four score"). base.en matched tiny.en everywhere else at 2.5-3.5x
the time. Typical delay from end of speech to text: 0.7s end-pointing
plus ~0.5s Whisper. The long Gettysburg line split at Chip's natural
pause, as END_SILENCE_MS says it should. To fix the start-timing
problem, `listener.py` now beeps through the bird when it starts
listening, and stays deaf until the beep has finished (plus a 0.3s
hold-off) - the turn-taking gate working end to end. Writing that
exposed a bug: `ignore_until()` only ever moved later (`max`), so
after going deaf with infinity it could never reopen; now it's a plain
assignment, and the test covers deaf-then-reopen.

*Issue 26 evidence, same day*: Chip listened to `cap_ch1.wav` on his
desktop: reasonably clean, apart from the start being muffled under
background noise. So the crackle he heard playing it through the bird
was the bird's playback path, not the recording.

**Build step 4, 2026-09-25 — Coordinator**: `coordinator.py`, plus
`orchestrate.py`'s turn logic factored into `take_turn()` (the text
CLI now calls it too, unchanged in behavior). Testing approach, Chip's
call: no live voice session yet, since without TTS Jack's replies only
appear on screen, which Chip can't read while standing at the bird.
Instead: an offline test with a fake Haiku client, one real API call on
the fixture recording, and the five utterances saved from step 3's live
test run through as one real conversation. All on a scratch copy of
`memory/` (Chip's call), so test facts can't land in the real
`memory.md`; `--scratch-memory` does the same for live runs.

Whisper spelling hint: `initial_prompt` set to "Captain Jack the parrot,
talking with Chip, Kath and Liz.", built from memory.md's `### Name`
headings. On the step 3 recording it turned "Cat's birthday" into
"Kath's birthday" and changed nothing else.

What the recorded conversation showed: the whole chain works (five
utterances in, five in-character replies, a household memory saved to
the scratch copy, the Mistress honorific used for Kath). Per-turn time:
Whisper 0.5-1.0s, Haiku 2.4-4.0s. But the replies aren't fit to speak:
79-180 words each (30-70 seconds of speech), growing through the
conversation, full of `*stage directions*` (`*squawks and bobs head*`)
and markdown emphasis (`*C*`, `*else*`) that TTS would read out.
Nothing in `identity.md` tells Jack his words are spoken. That needs
fixing before step 5; shorter replies also cut Haiku's time, which
grows with reply length.

**Spoken-reply rules, 2026-09-25**: added a "Speaking aloud" section to
`memory/identity.md` (Claude drafted, Chip approved as is): one to three
short sentences by default, plain words only, no stage directions, one
question at a time, numbers written as spoken, and a note that the
`MEMORY:` line isn't spoken, so brevity doesn't squeeze it out. Replayed
on the same five recorded utterances: replies went from 79-180 words to
9-39, asterisks disappeared, and Haiku's time per turn dropped from
2.4-4.0s to 1.0-1.3s. Chip wants stage directions back once gesture
work resumes, as real gesture cues rather than spoken text; parked as
spec §6 item 6. Same replay showed Jack claiming to turn off the lights
("Dousing the living room lights now") with no tools wired up — expected
until the home-automation tool schema exists, since `identity.md` tells
him he has those tools.

**Build step 5, 2026-09-25 — TTS and the first voice conversations**:
`tts.py`. `kokoro-pi` (PyPI, MIT, github.com/zreecespieces/kokoro-pi)
installed with no system packages. Its quick-start `kokoro-pi build`
fails without `--models DIR`; with it, the build downloaded the upstream
`kokoro-onnx` export (checksum-verified), compiled its ARM kernel, and
calibrated the int8 model in about 4 minutes, not the 15-25 its README
quotes. Measured 0.37x real time (3.6s of speech in 1.3s). Kokoro
outputs 24kHz; resampled to 16kHz with a windowed-sinc filter written
into `tts.py` (tested: 1kHz passes at full level, 10kHz is filtered out
rather than aliasing) instead of adding `scipy` for one function.

Voice: Chip auditioned 8 male voices by ear (4 British, 4 American),
each saying its number and the same pirate line. He liked 2
(`bm_george`), 7 (`am_michael`) and 8 (`am_santa`), and picked
`am_santa` as the most emotive.

*First live conversation* (scratch memory, `--wake-after 10`): the loop
worked end to end, and the honorific rule held (Matey until "this is
Chip", then Captain). Chip: speech good, gaps between sentences right.
Three problems:
- Replies still 50-80 words. Tightened `identity.md` to "about twenty
  words, one or two sentences"; replayed lines dropped to 12-29 words.
- Whisper stalls: "Captain, this is Chip" took 10s, and "Raise the
  anchor" took 20s and came back as "Where is the anchor?" x5. Cause:
  whisper.cpp's temperature-fallback retries, each a full decode. Fixed
  by turning retries off, capping tokens by audio length, and rejecting
  repetition.
- Two mumbles became plausible sentences ("Captain Jack, but you didn't
  know where you go.", "is good word") and Jack answered them. No audio
  had been saved, so `coordinator.py` gained `--save`, and Whisper's
  average token probability is now logged per utterance.

*Second live conversation*: no stalls (every transcription 0.38-0.69s),
delay to first sound down to 2.6-3.8s, 1.75s for the local "say
again" line. Chip did three gibberish utterances: two came back as
self-repeating guesses ("Can I get moved to goodbye" x2, "Are you a
wick, Jack?" x2) at probability 0.55 and 0.69, inside the range of his
real speech (0.60-0.80 with the names hint), and one as "P" at 0.02. So
a probability cutoff alone can't work. Adopted three layers (Chip's
call, all three): repetition rule extended to a 3+-word phrase twice; a
0.3 probability floor for extremes; and an `identity.md` line telling
Jack garbled lines should get an in-character "say again". Replayed on
the saved audio, the two local filters caught all three gibberish
samples and none of Chip's 10 real utterances ("So." at 0.10 was also
rejected; unknown whether it was speech). The `identity.md` line on its
own changed nothing on four garbled test lines: Haiku can't tell a
garbled line from an odd one without a signal. Candidate follow-up:
mark low-confidence transcripts as unclear when passing them to Haiku.

Also from the second run: utt08 was someone else in the room ("I'm
going to the bathroom..."), which Whisper transcribed in parentheses as
background, so it was rejected and Jack said "Say again?" to nobody.
Left alone until DoA and speaker ID can tell who's talking to Jack.

**Build step 7, 2026-10-07 — Motion & idle thread, full state machine**:
`motion.py` ports `exercise_hardware.py`'s already hardware-validated
gesture logic (Baseline, `resolve_move`, the ambient/excursion loops)
into a real long-lived thread — deliberately not a redesign, since that
logic is what Issue 25's breathing-gesture tuning was validated against.
The only real change from the dev harness is driving mode from
`set_mode()` (the Coordinator calls it on every transition) instead of a
blind random timer, and sending over the real `serial_link.py` writer
instead of a blocking one. A cross-library `find_gesture_anywhere()` was
needed because a Wav's paired gesture id can live in the dedicated
`wav_paired` library or directly in a mode library, as the existing
Asleep examples do — `find_gesture()` alone only checks one. Tested in
`tests/test_motion.py` against a small synthetic catalog (the real
catalog's `wait_ms` timings would make an automatic test slow); live-
checked standalone against the real bird (`motion.py --mode off_watch
--dry-run --seconds 15`, no Playback) — clean output, no crash, correct
asymmetric breathing swing, Chip confirmed correct movement by eye.
`gesture-catalog.yaml`'s `wavs: off_watch:` list was populated with all
162 real `wavFiles/` clips in the same pass (previously empty).

The `MODE:` meta-tag and the rest of the state machine (Asleep, the
15-minute Off Watch timeout, both keyboard phrase stand-ins, Motion/
Serial wiring into `coordinator.py`) were built the same session — see
[4.11](#411-sleep-mode-state-machine) for that half's own history, kept
separate since it's a distinct piece of design (transition logic) from
this one (gesture/idle-clip execution), per the spec/log split.

Build order (spec 4.16) is now fully implemented through step 7, except
the real wake-word models, which are GPU-blocked and not part of this
step - the keyboard stand-ins remain until Chip trains them.

**First live test with `--port`, 2026-10-07**: Chip ran
`coordinator.py --scratch-memory --port /dev/ttyUSB0` against the real
bird. The 2-minute On Watch no-prompt timeout fired correctly. Two real
findings:

- Every Haiku call failed with a 401 (`API key is invalid`) - Chip's
  key had hit its 30-day expiry, not a code problem; he'll get a fresh
  one. (This blocked testing the `MODE:` tag and beak-sync/motion
  against a real reply - still outstanding.)
- Both of two attempts at "Hi Jack, where are we sailing to today?"
  came back wrong and short (`"What should I do?"`, 1.4s audio; `"We're
  sailing to it today."`, 2.2s audio) - the transcribed audio length is
  much shorter than that whole sentence, and the first run's text bears
  no resemblance to it at all, consistent with the *start* of the
  utterance being lost rather than an ordinary Whisper mis-hearing.
  Root cause found by inspection (not yet re-confirmed live): `coordinator.py`
  printed `"[On Watch - speak to Jack]"` the instant `start_session()`
  queued the listening beep, not once the beep had actually finished
  playing - so someone reading that cue and immediately talking could
  easily speak into the ~0.3s the Listener is still deliberately deaf
  for (beep playback + `HOLDOFF_S`), losing exactly the sentence's
  opening words. Fixed by deferring that print to a new `beep_done`
  event, posted from `_on_playback` the same way `reply_started`/
  `reply_done` already are, so it's timed to when the beep actually
  left the speaker rather than when it was queued.
- Chip also tried the `sleep`-stand-in from what he thought was Off
  Watch and saw no effect. Reading the transcript: an Enter press
  (blank line, not visible in the pasted transcript) woke Jack back
  into On Watch between the timeout and typing `sleep` - so the fixed
  sleep phrase was correctly ignored outside Off Watch, per spec 4.11
  (nap from On Watch goes through the `MODE:` tag, never a fixed
  phrase). Working as designed, not a bug; worth re-testing by typing
  `sleep` immediately after `"[Off Watch ...]"` appears, with no Enter
  in between.

Still needed to close this out: a fresh API key, then a real live run
exercising a `MODE:` transition and beak-sync/motion together, and
confirming the beep-timing fix actually stops the clipped-start
problem.

**Beep-timing fix confirmed live, 2026-10-07**: the expired key was a
red herring (a typo in Chip's own notes - it was still valid); he
generated a fresh one anyway. Reran `coordinator.py --scratch-memory
--port ...`: Off Watch's periodic clip playback and the Enter-to-beep
On Watch transition both looked correct, and "Ahoy Jack, where are we
sailing today?" came back as 4.2s of transcribed audio ("Oh holy Jack,
where are we sailing today?" - Whisper mis-hearing "Ahoy" as "Oh holy",
p=0.61) matching the whole sentence, not a 1-2s fragment - strong
evidence the `beep_done` fix actually fixed the clipped-start problem
from the first live test, not just a plausible theory anymore. Jack's
reply was in character and conversationally apt, first audio 4.93s
after Chip stopped talking (consistent with the already-known
long-reply/no-streaming latency, not a new issue). This run ended via
the ordinary 2-minute no-prompt timeout, so it still didn't exercise a
`MODE:` transition or confirm beak-sync/motion against real speech -
both remain open for the next live run.

**Beak-sync/motion confirmed live, `MODE:` tag still not, 2026-10-07**:
same session, another attempt. Off Watch's idle clips now visibly
beak-synced correctly against real speech-shaped audio (previously only
checked against `AlignmentTone.wav` and standalone `motion.py --dry-run`)
- the first live confirmation of 4.8+4.10+4.12 all working together
through the real `coordinator.py` loop. Enter-to-On-Watch worked again.
Chip then said "That's all for now, Jack," meaning to end the session,
and Jack did return to Off Watch - but the printed line was `"[Off
Watch - no prompt for 2 minutes...]"`, the literal string
`_handle_timeout()` uses, not `_apply_pending_mode()`'s `"Jack ended the
conversation"` - so this was the ordinary 2-minute timeout firing, not
a `MODE: END_SESSION` tag. Root cause: Whisper transcribed the sentence
as "I'm so over now, Jack" (p=0.47, accepted - well above `PROB_FLOOR`
0.3), which doesn't read as an end-of-conversation cue, so Haiku
reasonably treated it as Chip sounding worn out and asked a clarifying
follow-up ("...Or just need a proper rest?") instead of signaling
`MODE: END_SESSION`. Not a coordinator bug and not the clipping bug
recurring (3.0s audio, a plausible length for the sentence) - it's
whisper-tiny's known rough accuracy on short out-of-context phrases,
the same gap spec 4.2 already flags as pending real-audio calibration.
A live `MODE:` transition still hasn't been confirmed - worth retrying,
ideally with a phrase Whisper is likely to transcribe cleanly.

**`MODE: NAP` confirmed live, and a real mic-reopen race found and
fixed, 2026-10-07**: same session, a third attempt - Chip said
"Goodnight, Jack" while On Watch. Whisper heard it correctly (p=0.49),
Jack replied in character with a two-sentence goodnight, and Jack did
go to Asleep - the first live confirmation of a `MODE:` tag actually
driving a transition - but the transcript showed an extra, unexplained
exchange in between: a rejected "no words" utterance (p=0.03) and its
own "didn't catch that" reply, printed *before* the `"[Asleep - Jack
said goodnight...]"` line. Root cause: `_on_playback` reopened the mic
(a finite `ignore_until`) after *every* sentence finished, not just the
reply's last one - so the ~0.3s gap between the goodnight reply's two
sentences was a real listening window. A stray sound there got
dispatched as a genuine `utterance` event while `mode` was still
`on_watch`, `handle_utterance()` rejected it but still called
`speak()` for the "didn't catch that" filler, which reassigns
`_first_tag`/`_last_tag` - clobbering the original reply's own tags
before its real last sentence could fire `reply_done`. The nap still
happened, but only because the filler reply's own completion later
reused the still-set `_pending_mode = "NAP"` by coincidence; had no
further utterance arrived, Jack would have silently never applied the
tag and sat in On Watch indefinitely (`speak()` also clears `deadline`,
so even the 2-minute timeout can't recover from this). Fixed in
`_on_playback`: only reopen the mic when the sentence that just
finished is the reply's actual last one (or the beep) - mid-reply
sentence boundaries now leave the mic deaf (`ignore_until(inf)`
untouched) straight through to the end of the whole reply, matching
the turn-taking (no barge-in) design already decided for this build
(see this section's "Designed 2026-09-25" entry, above) rather than
treating each sentence as its own turn boundary. Added
`check_mid_reply_sentence_gap()` to `tests/test_coordinator.py`,
verified it fails without the fix and passes with it.

**Mic-reopening fix confirmed live; `MODE: END_SESSION` and the
sleep-phrase stand-in both confirmed clean, 2026-10-07**: a fourth
live `--port` attempt, same session. Chip said "that's all for now
Jack" (transcribed correctly this time, 2.7s audio, p=0.50); Jack's
reply was again two sentences ("Aye, aye!... Matey. I'll be here when
ye need me.") - the same shape that triggered the mic-reopening race
above - and this time it went straight to `"[Off Watch - Jack ended
the conversation...]"` with no intervening rejected utterance,
confirming the fix holds live, not just in the regression test. This
is also the first clean live confirmation of `MODE: END_SESSION`
itself (the NAP transition two attempts ago only worked by the
coincidence the fix above describes). Chip then typed `sleep`
immediately after the `"[Off Watch ...]"` line, with no Enter first,
and got `"[Asleep - Goodnight, Jack...]"` - confirming the sleep-phrase
stand-in works correctly when tried as designed, resolving the "did
nothing" mystery from the very first live test as the suspected
stray-Enter explanation, not a bug.

This closes out the last open item from section 4.16's build order for
step 7: a real live voice conversation with beak-sync, ambient motion,
and a `MODE:` transition all confirmed working together end to end.
Remaining work (timeout/phrase tuning, real wake-word models, On Watch
excursions, reply-length/streaming refinements) is tracked in
CLAUDE.md's work list, not here - none of it changes this section's
design.

Correction from Chip after the fact: the leading rejected utterance in
this run (`"[BLANK_AUDIO]"`, 1.3s audio) wasn't silence caught before
he started talking, as first guessed above - the Listener actually
cut him off and Jack replied "didn't catch that" while he was still
mid-sentence. That's the VAD's end-pointing (`END_SILENCE_MS`)
declaring the utterance over too early, most likely on a brief natural
pause, rather than a beep-timing or mic-reopening issue (both of which
are about the *start* of an utterance, not an early cutoff mid-way
through). Repeating the sentence worked. Not a new bug - this is
exactly the kind of gap spec 4.1/4.2 already flag as pending
real-audio calibration (the VAD/STT thresholds are initial numbers,
not tuned against real speech cadence yet) - logged here as a concrete
data point for that future tuning, not actioned now.

**Mic permanently deafened by Motion's own clips, found live wiring in
the real `WakeSpotter`, 2026-10-11**: with `wakeword.py`'s `WakeSpotter`
already live-watched standalone and working correctly (both phrases
detected, no false positives, even with household background noise),
it was wired into `coordinator.py` - frames fan out to both `Listener`
and `WakeSpotter` from a new `_on_frame`, and `_on_playback` gates the
spotter's `ignore_until` the same way as the Listener's. The first live
`--port` watch after wiring it in: neither wake-phrase attempt worked
by voice (both times recovered via the Enter stand-in); a deliberate
follow-up batch of 10 more attempts scored 0/10 - not the ~75% recall
training measured, so not just bad luck. Root cause: `_on_playback`'s
mic-reopening check only recognized a reply's true last TTS sentence
(`_last_tag`) or the listening beep (`BEEP_TAG`) as things that should
reopen the mic when they finish - but Motion's own idle/excursion/
settle-in wav clips play through this same `Playback` instance too,
tagged with their own filename, which matched neither. The very first
such clip to finish playing in Off Watch or Asleep left the mic (and
now the spotter) at `ignore_until(inf)` permanently for the rest of
that mode - a latent bug since Motion was wired in (2026-10-07) that
had no visible effect until today, because nothing was actually
listening during Off Watch/Asleep before (only the keyboard stand-in,
which doesn't touch the mic). It also fully explains the earlier
"Goodnight, Jack" session's two failed voice-wake attempts in
retrospect: each followed a clip finishing, and each recovered by
falling back to Enter, then working fine once On Watch (since the
first real reply's last sentence finishing happened to reset
`ignore_until` correctly).

Fixed by generalizing the reopen check from "is this the reply's true
last sentence, or the beep" to "is this tag anything other than a
mid-reply sentence" - `if not isinstance(tag, tuple) or tag ==
self._last_tag`, since every reply-sentence tag is a `(reply, i)`
tuple and everything else (a wav filename, `BEEP_TAG`) is a
self-contained single item that should reopen the mic the moment it
finishes. `tests/test_coordinator.py` gained
`check_nonreply_clip_reopens_mic()`, confirmed to fail without the fix
(reproducing the exact bug) and pass with it. Also found and fixed in
the same live session, unrelated to this bug: see `MEMORY: NONE`
leaking into speech, this section's sibling fix in
[4.11](#411-sleep-mode-state-machine)'s history above.

**Confirmed live, 2026-10-11, same day**: added a debug hook
(`WakeSpotter`'s `on_score`, wired to `Coordinator._on_spotter_score`)
printing any score above a low floor (0.1) while not On Watch - cheap
visibility into near-misses vs. true silence, and exactly the kind of
data spec 4.1's threshold calibration will eventually want. First
re-watch after the mic-reopening fix reported 0/3 from Asleep still -
but closer reading showed those attempts were against a session that
had never actually reached Asleep in the first place: unrelated STT
repetition-hallucination failures (a known, separate, worse-than-usual
issue that session - see [4.2](#42-speech-to-text-stt)) kept blocking
the verbal path out of On Watch, and typing `sleep` from On Watch is
correctly a no-op by design (the stand-in is Off-Watch-only, spec
4.11) - so Jack was stuck On Watch the whole time, not failing to wake
from a genuine Asleep. Retested properly (waited out the 2-minute On
Watch timeout to Off Watch, typed `sleep` to reach Asleep with no STT
involved) and both phrases fired correctly and repeatedly by voice from
there: wake from Off Watch (0.81), sleep phrase from Off Watch (0.93,
0.92), wake from Asleep (1.00, 0.96) - cycling through the whole state
machine multiple times cleanly. Closes out the wake-word spotter's live
validation; the keyboard stand-ins remain available permanently
alongside it (2026-10-11 decision, see CLAUDE.md).


**Squawk filler and first-sentence split, 2026-10-15** (both aimed at the
~3s wait before Jack answers). Filler: a random squawk from
`wavFiles/fillers/` queued the moment an utterance is handed over -
first placeholders cut from an existing clip (Kath: "sounds like a
crow"), then six real macaw calls from xeno-canto picked by Chip and Kath
from an 8-way audition on the bird. After a live session Chip asked for a
beat before it: a squawk the instant speech ended felt abrupt, so it got
0.3s of silence first. STT already runs in parallel with it, so this
only moves the squawk within the wait. Chip felt that could still be a
little longer; session17 showed Jack's first word never came before 2.4s
after speech ended, so 0.6s was tried live (session18): squawks ended
0.9-1.2s after speech, first audio 2.32-3.48s (mean 2.78s, same as
before - the filler never delayed a reply). Chip: "0.6 felt good" - kept.
Same session, tiny.en with the bird on the towel: 3 of 6 transcripts had
an error ("What did you have" -> "What you have", "Go for sail" -> "Go for
a sale", "quick conversation" -> "quick count recession"); Haiku's
replies stayed sensible on all three.

Head tilt with the squawk, same day: `Motion.squawk_tilt()` plays a new
`fx-squawk-tilt` gesture on its own short thread, starting with the
squawk's lead-in silence (the ~0.1s playback latency means the head
arrives about as the sound starts), holding for the squawk's length,
then easing back over 350ms. It ignores the listening hold - the mic is
already deaf while the squawk plays - and the main Motion loop pauses
while it runs. Bench-auditioned on the bird with six squawks: up 8deg /
cocked 15deg looked too much; Chip's estimate of 6/10 looked right. Chip
would like the cock toward the speaker once DoA is available. Live
`--port` conversation (session19): Chip - motion smooth, angles about
right, no delay to the reply. First audio 1.92-3.32s (mean 2.60s; minus
STT 1.40-2.13s, the best yet); the tilt is back at rest by ~1.65s after
speech ends at the latest. 5/5 transcripts correct.

First-sentence split: session16's first-audio times (2.0-3.6s) minus STT
tracked the length of Jack's first sentence (1.5s for 6-7 words, 2.8s for
13) - Kokoro synthesizes a whole sentence before any of it plays. Rendered
four real long sentences whole and split at a comma/dash: first sound
0.8-1.8s sooner, piece 2 always synthesized well before piece 1 finished
(synthesis ~3x faster than playback; tightest case 6 words then 19 had
1.3s to spare), join pause 0.02-0.28s longer than Kokoro's own. Chip had
set the bar - an audible mid-reply gap would be worse than a slow start -
and in a whole-vs-split audition on the bird, heard twice, "can't really
hear the split at all." Built as `tts.split_first_sentence()`, first
sentence only (later ones already synthesize while earlier ones play).
Not yet measured live.
### 4.4 Persona and Identity Prompt

**Reply-length target raised, 2026-10-12**: live conversation runs
(both of 2026-10-12's STT confirmation sessions) consistently ran
25-45 words per reply against `identity.md`'s "about twenty words"
target - Chip's read, after getting used to Jack's cadence, was that
they don't actually feel overly long, but could stand to come down a
little. Measured the ordinary-conversation replies from one full
session: mean 31 words, range 19-36. Raised the target from twenty to
thirty words - close enough to current behavior to be realistic, with
still some room to trim the longest replies. The existing "unless
someone asks for a story, a recipe, or more detail" exception (already
in `identity.md`, unchanged) was confirmed live the same day: a reply
to "do you have a short mystery story for me?" ran well over a hundred
words and Chip didn't want it shortened - the exception, not the
baseline, is what should govern a reply like that.

### 4.3 Conversation Orchestrator

**Streamed replies, 2026-10-12**: tackled next on the work list after
the wake-threshold calibration and the timeout decision - the delay to
Jack's first sound (section 4.16's "next lever," flagged since the
original build in September) comes from waiting for Haiku's *entire*
reply, tag lines included, before any of it can be spoken, even though
TTS already synthesizes sentence by sentence once it has something to
work with.

Added `orchestrate.py`'s `SpeechStreamer`: an incremental version of
`tts.split_sentences()` (same too-short-fragment-merges-forward rule),
fed piece by piece as `client.messages.stream()`'s text arrives rather
than all at once. It stops cold at the first newline rather than
waiting for the stream to finish: a real spoken reply is single-line
prose (see `identity.md`'s style rules) and `MODE:`/`MEMORY:` always
start on their own line right after it, so a newline alone reliably
marks "no more speech after this point" - confirmed by feeding sample
replies through character-by-character and checking the result matches
`split_sentences()` exactly, for every chunk size tried. One accepted,
documented difference: a too-short trailing fragment with nothing after
it can't be merged backward into an already-dispatched sentence (that
sentence may already be synthesizing or playing by the time the stream
ends), so it's spoken as its own slightly-short sentence instead - a
cosmetic edge case, not a correctness one.

`get_reply_stream()`/`stream_turn()` wrap this the same way
`get_reply()`/`take_turn()` already wrapped the non-streaming call;
both now share one tag-parsing/memory-saving tail (`_finish_turn()`,
factored out of the old `take_turn()` body, pure extraction, no
behavior change). `coordinator.py`'s `handle_utterance()` switched from
`take_turn()` to `stream_turn()`, passing an `on_sentence` callback that
tags and queues each sentence to TTS the moment it's ready - exactly
the dispatch speak() used to do all at once, now spread across the
stream. Confirmed this is actually incremental, not just correct: a
test wraps the fake stream to count how many characters had been
consumed when the first sentence was reported, and checks it's well
short of the full reply.

This opened a real race that couldn't happen with the old all-at-once
`speak()`: a reply's true last sentence isn't known until the full
reply (tags included) has arrived, and if TTS/Playback happen to be
faster than the rest of the network round-trip, that sentence's own
"finished" playback event can come and go *before* `_last_tag` is set
to match it - exactly the class of bug the 2026-10-11 sentence-gap race
was (docs/log.md's 4.16 history), just a different pair of racing
events. Fixed by tracking how many of the current reply's sentences
have already finished playing (and the real `dac_time` of the most
recent one) as they happen, independent of whether `_last_tag` is set
yet; once the reply's sentence count is finally known,
`coordinator.py`'s new `_finish_reply()` checks whether that count was
already reached and, if so, fires the mic-reopen/`reply_done` logic
immediately using the dac_time already recorded, rather than silently
dropping it. Verified live (temporarily disabling the catch-up branch
by hand, not `git stash` - this fix lives inside an `if` body, not a
separable diff) to fail without it and pass with it
(`tests/test_coordinator.py`'s `check_late_last_sentence_race`).

Also fixed, found while handling the error path: `handle_utterance()`
now has to start pausing the On Watch timeout (`_begin_reply()`) before
knowing whether Haiku will reply at all, since sentences can start
queuing before the full turn succeeds or fails - if a turn fails with
*zero* sentences ever spoken (an API error with nothing streamed in
yet), the old all-at-once `speak()` simply never touched `deadline` at
all, but the new per-reply bookkeeping would otherwise leave it paused
forever with nothing left to resume it. `_finish_reply()` now resumes
the ordinary 2-minute timer itself in that specific case, the same way
`_apply_pending_mode()` does when Haiku signals no mode change.

All new logic (`SpeechStreamer`, `stream_turn()`,
`coordinator.py`'s per-reply bookkeeping and the race catch-up) is
covered by `tests/test_streaming_reply.py` and new cases in
`tests/test_coordinator.py`; the full existing suite (including the
2026-09-25/2026-10-07/2026-10-11 regression tests for the sentence-gap
race and the non-reply-clip mic reopen) still passes unchanged. Not yet
done: a real live-device latency measurement confirming the expected
improvement - blocked this session on an expired `ANTHROPIC_API_KEY`
in the shell environment, not a code issue; the automated fake-client
tests already confirm the mechanism is genuinely incremental.

**Second paragraphs silently dropped, 2026-10-14**: the first live run
with streaming on (Chip, `--port`, scratch memory) showed three of six
replies printed as two paragraphs separated by a blank line, and in
every case the second paragraph was never spoken. Root cause was
`SpeechStreamer`'s own design assumption above - "a real spoken reply
is single-line prose" - which held in the samples it was tested against
but not in Haiku's actual output; the first newline ended speech for
the whole reply. The non-streaming path never had this bug
(`split_tags()` peels tags off the end, and `split_sentences()` treats
a newline as whitespace), which is why it hadn't shown up before.
Fixed by stopping only at a line that *starts* like a tag (`MODE:`,
`MEMORY:`, or a ` ``` ` fence - the same three shapes `split_tags()`
already handles), holding back just the first few characters of each
new line until they rule a tag in or out, so the latency benefit is
kept. Regression samples in `tests/test_streaming_reply.py` include
the live reply's exact shape plus prose lines deliberately starting
"Memories..."/"Mode of..." (must not be mistaken for tags); confirmed
via `git stash` that they fail on the old code. The same run also
reported degraded recognition - a separate issue, not caused by this
bug (no STT/capture/listener code changed since the 2026-10-12
confirmation runs); not yet diagnosed, needs a `--save` session.

### 4.6 Home-Automation Tool Schema

**Built and live-tested, 2026-10-18.** Choices made along the way:

- **Device capabilities come from the CSV's `Type`, not the vendor's
  feature list.** Chip lists what a device *controls* (a light on an
  outlet is a light), which is also what decides what's safe to do with
  it - and it keeps the tool schema fixed rather than depending on which
  vendor clouds answered at startup. Vendor ids are looked up by name on
  first use for the same reason.
- **Fountain pump: confirmation, not a run-time cap.** First thought was
  a device-side countdown like irrigation's; Chip pointed out a filled
  fountain can rightly run for hours while a dry one burns out in
  minutes, so the guard is a spoken "it has water" instead. Code can't
  judge a yes, so it enforces the order: the first request is held and
  Haiku is told what to ask; a call in the very next turn goes through.
  Side effect accepted: "turn on the fountain, it's full" still gets
  asked.
- **First live fountain test exposed tool-description wording.** The
  `set_power` description said the pump "needs a yes from the person
  first". Haiku took that as an instruction to ask *before calling the
  tool* - no tool call, so the code's hold never ran, and it invented
  its own question ("ready to set those waters splashin'?") with nothing
  about water. Safe (a yes would only have got a second, held ask) but
  wrong. Fixed by telling Haiku to call straight away and let the result
  say what to ask; the rerun called the tool, got held, asked "does it
  have water in it?", and on "No" made no call (pump switch confirmed
  off). Lesson: when code owns a rule, the tool description should say
  "call it", not describe the rule - Haiku will try to follow a rule
  itself.
- **Stop watering stops the whole controller.** Rachio's stop is per
  controller, so the result names "Waterman (all zones)" rather than the
  first zone (it said "Courtyard" in the first live run - right action,
  misleading line).
- **First voice conversation with the tools, 2026-10-18** (session20,
  `--port`, scratch memory): "turn the office lights off" switched all
  three office lights in one call and "turn them back on" restored them;
  "it can be better with the nook light off" was taken as a request.
  Time to first word: 2.8-3.2s for ordinary turns, 3.4-4.3s for tool
  turns (the second Haiku round trip), and 6.2s for the *first* tool
  turn - the cold vendor lookups (Smart Life login, device list, each
  device's functions). Fixed by `Home.warm_up()`: the same read-only
  lookups run in a background thread at startup (~5s, finished long
  before Jack's models load). Not yet re-measured live. Haiku never
  spoke a lead-in before a tool call, so the extra second is silence
  after the filler squawk.
