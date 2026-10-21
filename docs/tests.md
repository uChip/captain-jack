# Captain Jack — Tests

Per the **testing philosophy** in
[specification.md](specification.md#1-goals-and-objectives): at least one
test per use case and per hardware/software functional block, developed
alongside each block as it's implemented — not an exhaustive or
product-grade suite. This file is the index; per-test scripts (and any
input data they need) live in `../tests/`, named after the test.

**Convention**: whenever a test is written ad hoc during a session (to
verify something just built or changed), it gets promoted here rather
than discarded once the session ends — a scratch verification that
disappears when the terminal closes doesn't help future sessions or
regression-check later changes.

Each entry: what it covers, how to run it, what passing looks like, and
when it was last confirmed passing.

## Memory Subsystem

### `home` tag save path

- **Covers**: [Memory Subsystem](specification.md#45-memory-subsystem) /
  [Use Case 2.3](specification.md#23-environmental-and-self-awareness) —
  the `[home]` memory tag added to resolve former
  [Open Issue 4](specification.md#5-open-issues).
- **Script**: [`../tests/test_home_memory_save.py`](../tests/test_home_memory_save.py)
- **Run**: `venv/bin/python tests/test_home_memory_save.py`
- **Expected**: prints `PASS: [home] tag parses, saves, and dedups
  correctly` and exits 0. Checks, against a scratch copy of
  `memory/memory.md` (the real file is never touched):
  - `parse_memory_proposal("[home] Sun Lakes, Arizona")` returns
    `("home", None, "Sun Lakes, Arizona")`.
  - `save_memory` appends a new `[home]` fact under the `## Home` heading.
  - A second, identical `save_memory` call is skipped as a duplicate.
- **Last confirmed passing**: 2026-09-14.
- **Not covered**: the live Haiku API path (whether Haiku actually
  proposes `[home]` correctly in conversation) - this only tests the
  deterministic parse/save code, same scope limit as the joke/automation
  tags' existing live-API testing noted in
  [captain-jack-memory-design.md](captain-jack-memory-design.md).

### `MODE:` end-session/nap tag

- **Covers**: [Sleep-Mode State Machine](specification.md#411-sleep-mode-state-machine)
  — the `MODE:` meta-tag `orchestrate.py` reads from Haiku's own reply
  (mirroring the `MEMORY:` line's mechanism) to signal `END_SESSION` or
  `NAP`, parsed by `split_mode_line()`/`split_memory_line()` and combined
  order-independently by `split_tags()`, threaded through `take_turn()`
  into `Turn.mode`.
- **Script**: [`../tests/test_mode_tag.py`](../tests/test_mode_tag.py)
- **Run**: `venv/bin/python tests/test_mode_tag.py` (automatic, no
  hardware, no real API — a fake Haiku client).
- **Expected**: prints `PASS: MODE: tag splits correctly (in either
  relative order with MEMORY:) and take_turn() wires it into Turn.mode`
  and exits 0. Checks `split_mode_line()` splits `END_SESSION`/`NAP`/
  `NONE` correctly, normalizes case, and fails closed to `None` on a
  missing or malformed line (e.g. an older reply with no `MODE:` line at
  all); checks `take_turn()` strips both the `MODE:` and `MEMORY:` lines
  from the spoken reply and surfaces `END_SESSION` correctly in
  `Turn.mode`, with explicit `MODE: NONE` and a missing `MODE:` line both
  surfacing as `Turn.mode is None`; and (added 2026-10-11, after a live
  test caught `MEMORY: NONE` leaking into speech) that both tags still
  get stripped and `Turn.mode` still comes through correctly when Haiku
  puts `MEMORY:` before `MODE:` instead of the documented order.
- **Last confirmed passing**: 2026-10-11.
- **Not covered**: the live Haiku API path's full range of tag-ordering/
  formatting variance beyond the one reversed-order case caught so far
  (e.g. a fence wrapping both tags together, not just `MEMORY:` alone -
  theoretical, not yet observed), and `coordinator.py` acting on
  `Turn.mode` (that part is covered by `test_coordinator.py` instead).

## Gesture Engine and Catalog

### `gesture-catalog.yaml` sanity checks

- **Covers**: [Gesture Engine and Catalog](specification.md#412-gesture-engine-and-catalog)
  — the delta-encoded Gesture/Move structure in
  [`gesture-catalog.yaml`](gesture-catalog.yaml) (second pass, 2026-09-20:
  gestures store deltas from a live baseline, not resolved servo values —
  see the catalog's own header comments and specification.md 4.10/4.12).
- **Script**: [`../tests/test_gesture_catalog_bounds.py`](../tests/test_gesture_catalog_bounds.py)
- **Run**: `venv/bin/python tests/test_gesture_catalog_bounds.py`
- **Expected**: prints `PASS: gesture-catalog.yaml deltas/beak values
  sane, ids unique, ambient gestures exist` and exits 0. Checks every
  Move's `dp`/`dr`/`dy` against each axis's total travel from
  `arduino/ServoControl/ServoControl.ino` (a loose sanity bound, since
  real validity now depends on the runtime baseline this test can't
  know), any absolute `beak` value against 0-60, every `t`/`wait_ms` is
  positive, no gesture `id` is duplicated, each mode's `ambient` entry
  actually names a gesture that exists in that mode's list, and every
  Wav's `gesture` reference (e.g. `sl-settle-to-sleep`'s wav pools)
  resolves to a real gesture id.
- **Last confirmed passing**: 2026-09-20.
- **Not covered**: whether any gesture actually looks right on the real
  bird, whether baseline/DoA tracking or the ambient/excursion engine
  behave correctly (none of that is implemented yet), or the
  `NEEDS-RUNTIME-PARAM` entry's fallback values, which are known
  placeholders, not real behavior.

### Motion engine

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 7's Motion & idle thread — `motion.py`'s `resolve_move()`
  (baseline-relative deltas → absolute servo command, with clamping and
  beak handling), `find_gesture_anywhere()` (cross-library gesture
  lookup for wav-paired gestures), and the Off Watch/Asleep/On Watch
  per-mode step logic (ambient, due excursions, idle wav scheduling),
  and `fall_asleep()`'s Asleep entry (spec 4.10: settle gesture first,
  with a wav from the pool matching how sleep was entered) —
  a faithful port of `exercise_hardware.py`'s already hardware-validated
  gesture logic into a real long-lived thread with `set_mode()`.
  Also that `stop()` returns head and beak to the catalog's resting
  pose and `SerialWriter.stop()` sends still-queued head commands
  before closing (2026-10-15: closing the port no longer resets the
  Arduino to rest - spec 4.13 "Connection and reset").
- **Script**: [`../tests/test_motion.py`](../tests/test_motion.py)
- **Run**: `venv/bin/python tests/test_motion.py` (automatic, no
  hardware — a small synthetic catalog, not the real
  `gesture-catalog.yaml`, to avoid its real `wait_ms` timings).
- **Expected**: prints `PASS: resolve_move clamping, cross-library
  gesture lookup, and ambient/excursion/wav scheduling and Asleep
  settle-in correct` and
  exits 0. Checks delta clamping against each axis's range, that beak is
  absolute (not baseline-relative) and leads the command, that omitting
  beak emits no `b<N>` token, that `find_gesture_anywhere()` finds a
  gesture living in `wav_paired` or directly in a mode library (and
  raises `KeyError` for an unknown id), and that a single Off Watch step
  plays the ambient gesture, fires a due excursion, and schedules the
  one off_watch wav (with Asleep's wav-paired-gesture beak move firing
  alongside its clip, and On Watch using its own ambient). For Asleep
  entry: the settle gesture plays first and only once; `goodnight_phrase`
  and `idle_timeout` each pick only from their own pool; `None` (MODE:
  NAP) plays no wav; a listed-but-missing file is never picked; and a
  mode change before Motion reaches the settle cancels it. Also that
  `hold(True)` stops gestures between moves, and `hold(False)` or any
  `set_mode()` releases it (On Watch's listening hold, 2026-10-14). And
  that `squawk_tilt()` waits out its delay, moves even while held, holds
  for the squawk's length, returns to baseline, and skips a second call
  while one is running (2026-10-15).
- **Last confirmed passing**: 2026-10-15.
- **First live watch, 2026-10-07** (`motion.py --mode off_watch
  --dry-run --seconds 15` against the real bird, Chip watching): clean
  output, no crash, correct asymmetric breathing swing from
  [Open Issue 25](specification.md#5-open-issues) plus an excursion;
  Chip confirmed the bird moved correctly.
- **Not covered**: DoA-based yaw tracking (`read_doa_azimuth()` is still
  a stub), On Watch excursions (not implemented — conversation/emotion-
  triggered, per spec 4.12), `sl-waking-up` on wake from Asleep (not
  implemented yet), and `Motion` inside the live `coordinator.py` loop
  (wired 2026-10-07 and checked live by hand, see log.md 4.16 — this
  test only exercises `motion.py` on its own).

### Servo motion noise at the mic (manual, measurement)

- **Covers**: how much the head servos' movement raises the noise heard
  by [STT](specification.md#42-speech-to-text-stt) and the
  [wake-word spotter](specification.md#41-wake-word-detection), per
  Motion mode — found 2026-10-14 to be the cause of degraded
  recognition (see log.md 4.2 history).
- **Script**: [`../tests/measure_servo_noise.py`](../tests/measure_servo_noise.py)
- **Run**: `venv/bin/python tests/measure_servo_noise.py [--port ...]
  [--lead-in 10] [--excursions] [--phases still:15,off_watch:20,on_watch:20,still:15]`.
  **Needs the real bird, a quiet room, and nobody talking.** Off Watch
  excursions are off unless `--excursions` is given. `--catalog FILE`
  measures a scratch copy of `docs/gesture-catalog.yaml` - a gesture
  change before committing to it.
- **Expected**: prints per-phase mic levels (median/p10/p90/max of
  100ms slices, dBFS) and saves each phase's audio. No pass/fail - for
  comparison: normal speech at the bird is about −15 to −20 dBFS.

### Bench servo noise at the mic (manual, measurement)

- **Covers**: airborne noise of a single loose servo on the bench (no
  mechanical path into the mic array), for comparing candidate quieter
  head servos against the current AGFRC B11DLS (see log.md 4.2 history).
- **Script**: [`../tests/measure_bench_servo.py`](../tests/measure_bench_servo.py)
- **Run**: `venv/bin/python tests/measure_bench_servo.py [--port ...]
  [--lead-in 10] [--out stt_samples/bench_servo] [--baseline-only]`. **Needs the test servo
  plugged into the roll channel (pin 5) in place of the bird's roll
  servo, a quiet room, and nobody talking.** Drives only `r` moves.
- **Expected**: prints mic levels while moving and holding at several
  sway sizes/speeds, plus band shares, and saves each segment's audio.
  No pass/fail - compare against the baseline segment and against
  `measure_servo_noise.py`'s in-bird numbers.
- **Last run**: 2026-10-14 (ad hoc first version, one Off Watch
  excursion accidentally included): still −47.8 median; On Watch ±3°
  sway −32.4; Off Watch 41° breathing −23.3 (two excursion bursts to
  −3/−9); still afterwards decayed from about −35 to −43 over ~10s.
- **Not covered**: excursion or speech-driven gestures (only each
  mode's ambient gesture, by default), and beak motion.

## Idle and Ambient Audio Player

### `wavFiles/` clip format

- **Covers**: [Idle and Ambient Audio Player](specification.md#410-idle-and-ambient-audio-player)
  / [TTS](specification.md#47-text-to-speech-tts)'s canonical format —
  every stored clip is plain PCM, 16kHz, 16-bit, **mono** (the 2-channel
  duplication the XVF3800 needs happens at playback, not on disk).
- **Script**: [`../tests/test_wavfiles_format.py`](../tests/test_wavfiles_format.py)
- **Run**: `venv/bin/python tests/test_wavfiles_format.py`
- **Expected**: prints `PASS: all N wavFiles/ clips are 16kHz/16-bit/mono
  PCM` and exits 0. Otherwise prints one `FAIL:` line per mismatched
  field per clip and exits 1. Parses the RIFF headers directly; doesn't
  touch hardware.
- **Last confirmed passing**: 2026-09-25 (19 clips), after
  `IAmIronman.wav` was converted to mono — the test's first run caught it
  as 2-channel.
- **Not covered**: audio content or loudness — peak level is what matters
  for [Open Issue 26](specification.md#5-open-issues), and it's checked
  by ear, not here.

## Seeed reSpeaker XVF3800 / Speaker
### STT rejection rules

- **Covers**: [STT](specification.md#42-speech-to-text-stt)'s rejection
  of retry loops, gibberish echoes, and very low confidence —
  `stt.rejection_reason()` — plus (added 2026-10-12) that `STT` builds a
  fresh whisper.cpp Model per `transcribe()` call rather than reusing one
  for the process's life, that a repeat-loop hallucination triggered
  by the household-names `initial_prompt` is recovered by one no-prompt
  retry rather than surfacing as a reject, and that a single word
  repeated rapidly (too short an utterance for the 2/3-word rules to
  ever fire) is still caught (all real bugs found live — see log.md's
  4.2 history).
- **Script**: [`../tests/test_stt.py`](../tests/test_stt.py)
- **Run**: `venv/bin/python tests/test_stt.py` (automatic, no hardware;
  `check_fresh_model_per_transcribe` and `check_prompt_repetition_retried`
  load the real tiny.en model, the latter against a committed real
  recording, `tests/data/thank_you_jack_ch1.wav`).
- **Expected**: prints `PASS: 11 real transcripts accepted, 8
  loops/gibberish rejected, STT builds a fresh Model per transcribe()
  call, and a prompt-triggered repeat-loop is recovered by retrying
  without the prompt` and exits 0. Inputs are real transcripts and
  probabilities from the 2026-09-25 and 2026-10-12 live runs: Chip's
  clear speech (including a long utterance that legitimately reuses a
  short phrase once, far apart, and one using "the" four times) must
  pass; the "Where is the anchor?" x5 loop, two echoed gibberish guesses,
  "P" (0.02), a genuine back-to-back repeat ("That's all for now,
  Jack." x2), and a hallucinated single-word storm ("No? No? No? No?
  No?") must be rejected; three `transcribe()` calls through one `STT`
  must construct three real `Model` instances, not one; and the real
  recording (clean with no prompt, a repeat-loop with the household-names
  prompt active) must come back accepted.
- **Last confirmed passing**: 2026-10-12 (confirmed via `git stash` that
  the adjacency-aware repetition check, the fresh-Model-per-call fix,
  the no-prompt retry, and the single-word rule are each independently
  necessary — the Preamble case, the Model-count check, the real
  recording, and the "No?" case each fail without their respective fix).
- **Not covered**: gibberish that comes out as a single plausible,
  confident sentence ("is good word") — no local rule catches that yet
  (this is what hallucinated "Can you tell her to say?" out of ambient
  noise, 2026-10-12 - a known, accepted gap, not a repetition-rule
  miss); `no_speech_thold`/`logprob_thold`/`entropy_thold` calibration
  against real household audio (spec 4.2's still-deferred numbers).

### STT model comparison (manual, diagnostic)

- **Covers**: the tiny-vs-base choice
  ([STT](specification.md#42-speech-to-text-stt)) — `compare_stt.py`, not
  part of the automatic suite (no pass/fail verdict, needs a human who
  knows what was actually said).
- **Script**: [`../compare_stt.py`](../compare_stt.py)
- **Run**: `venv/bin/python coordinator.py --scratch-memory --save
  stt_samples/SESSION` to record real utterances (gitignored — real
  household voices), then `venv/bin/python compare_stt.py
  stt_samples/SESSION [--models tiny.en,base.en]`.
- **Expected**: prints each utterance's audio length, then each named
  model's confidence, time, and transcript/rejection side by side.
- **Last confirmed passing**: 2026-10-12, live — a 7-utterance recorded
  session (`stt_samples/session1`, not committed) showed tiny.en and
  base.en agreeing almost everywhere once both the Model-reuse and
  repetition-adjacency bugs above were fixed, tiny.en at 2-2.5x the
  speed — settled the tiny-vs-base question for real, noisy-room audio.
- **Not covered**: anything beyond manual eyeballing — this tool makes no
  accept/reject decision of its own.

### TTS thread

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 5 and [TTS](specification.md#47-text-to-speech-tts) —
  `tts.py`'s sentence splitting, first-sentence splitting
  (`split_first_sentence()`, 2026-10-15), markdown clean-up, 24→16kHz
  resampling, and kokoro-pi synthesis.
- **Script**: [`../tests/test_tts.py`](../tests/test_tts.py)
- **Run**: `venv/bin/python tests/test_tts.py` (automatic, no hardware,
  no model) or add `--live` to synthesize with kokoro-pi (needs the
  models built in `models/kokoro-pi`, see CLAUDE.md).
- **Expected**: prints `PASS: sentence split, first-sentence split, clean-up, and 24k->16k
  resampling correct` (plus `, kokoro-pi synthesizes faster than real
  time`) and exits 0.
- **Last confirmed passing**: 2026-09-25, including `--live` (0.37x
  real time).
- **Not covered**: how the voice sounds (judged by ear:
  `venv/bin/python tts.py --audition`), and the spoken conversation as a
  whole (checked live by hand with `coordinator.py --scratch-memory
  --wake-after 10 --save DIR`, see log.md 4.16).

### Coordinator turn

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 4, the [Conversation Orchestrator](specification.md#43-conversation-orchestrator)'s
  `stream_turn()` (2026-10-12; was `take_turn()`) — utterance → Whisper
  → Haiku → reply + memory save, session start/end, noise rejection —
  and the [Sleep-Mode State Machine](specification.md#411-sleep-mode-state-machine)'s
  transitions (`MODE: END_SESSION`/`NAP`, wake from Asleep, the
  sleep-phrase stand-in's Off-Watch-only gating, both timeouts, and
  which Asleep-entry context each path hands Motion), driven
  directly through `_handle_event()`/`_handle_timeout()` without
  starting real audio threads. Also covers three real races found live:
  a multi-sentence reply must keep the mic deaf across its own internal
  sentence gaps, not just after the whole reply ends, or a stray sound
  there can clobber the in-flight reply's tag tracking and silently
  drop a pending `MODE:` tag (log.md 4.16, "Goodnight, Jack" live test,
  2026-10-07); a standalone clip (Motion's idle/excursion/settle-in
  wavs, tagged with their own filename, not a reply-sentence tuple) must
  reopen the mic/spotter as soon as *it* finishes too, or the mic (and,
  once wired in, the real `WakeSpotter`) goes permanently deaf after the
  first one plays in Off Watch/Asleep (log.md 4.11/4.16, found wiring in
  `WakeSpotter`, 2026-10-11); and, once replies started streaming in
  (2026-10-12), a reply's true last sentence can finish playing before
  Haiku's full text is even known to have ended, if TTS/Playback happen
  to be faster than the network - `_finish_reply()` must catch up
  immediately rather than drop the mic reopen/`reply_done` (log.md 4.3).
  Also that On Watch holds the head still exactly while the mic is
  open - held at session start and after each reply (and after a Haiku
  error that never spoke), released when a reply starts playing
  (log.md 4.2, servo noise, 2026-10-14). And that a squawk filler
  (`wavFiles/fillers/`, 2026-10-15) is queued the moment an utterance is
  handed over, ahead of the reply, never the same one twice running;
  that its finishing reopens the mic without firing `reply_done`; that
  Motion is asked for a `squawk_tilt` timed to it; and that
  `filler=False` (`--no-filler`) plays none.
- **Script**: [`../tests/test_coordinator.py`](../tests/test_coordinator.py),
  with fixture `../tests/data/quick_brown_fox_ch1.wav`.
- **Run**: `venv/bin/python tests/test_coordinator.py` (automatic, no
  hardware, no API — a fake Haiku client, now also standing in for
  `.messages.stream()`) or add `--live` for one real Haiku call (needs
  `ANTHROPIC_API_KEY`; a fraction of a cent).
- **Expected**: prints `PASS: coordinator transcribes, calls Haiku, saves
  memory to scratch only, rejects noise, the Sleep-Mode State Machine
  transitions correctly (telling Motion how Asleep was entered), the mic
  stays deaf across a multi-sentence reply's own sentence gaps but
  reopens after, a standalone clip (Motion's idle/excursion/settle-in
  wavs) reopens the mic and spotter too, and a streamed reply's own last
  sentence finishing before it's known to be last still reopens the
  mic/fires reply_done correctly, and the head holds still exactly while
  the mic is open` (plus `, live Haiku replied`) and
  exits 0. Everything runs on a scratch copy of `memory/`; the test
  fails if the real `memory.md` changes.
- **Last confirmed passing**: 2026-10-14.
- **Not covered**: the keyboard wake and the timeouts firing in real
  time (logic checked directly, not the timer); beak-sync/motion
  together with a live reply (checked live by hand against the real
  bird, see log.md 4.16); a real live-device latency measurement for
  streaming (see the new "Streamed Haiku replies" entry below - blocked
  this session on an expired `ANTHROPIC_API_KEY`, not a code issue).
- **Live-watched as wired in, 2026-10-11**: the real `WakeSpotter`
  (`_on_frame`/`_on_playback`, not just `test_wakeword.py`'s mechanism
  checks) against the real bird - wake from Off Watch, sleep phrase
  from Off Watch, and wake from Asleep all fired correctly and
  repeatedly by voice, cycling through the full state machine several
  times. See log.md 4.16 for the full story, including a false alarm
  (0/3 from "Asleep" that turned out to be a session stuck On Watch by
  unrelated STT failures, not a real Asleep-wake bug).

### Streamed Haiku replies

- **Covers**: [Conversation Orchestrator](specification.md#43-conversation-orchestrator)'s
  `SpeechStreamer` and `stream_turn()` (2026-10-12) - the incremental
  sentence splitter and the streaming counterpart of `take_turn()` that
  speaks a reply as it arrives instead of waiting for all of it first
  (the "next lever" flagged in
  [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 5 since the original build).
- **Script**: [`../tests/test_streaming_reply.py`](../tests/test_streaming_reply.py).
- **Run**: `venv/bin/python tests/test_streaming_reply.py` (automatic,
  no hardware, no API - a fake streaming client).
- **Expected**: prints `PASS: SpeechStreamer matches split_sentences()
  (bar one documented tail-fragment difference) and stops cleanly at
  the MODE:/MEMORY: boundary; stream_turn() calls on_sentence()
  progressively, agrees with take_turn() on the same reply, and rolls
  back history on a mid-stream API error` and exits 0. Checks
  `SpeechStreamer` against `tts.split_sentences()` across several
  sample replies and chunk sizes down to one character at a time (they
  must match, except the one accepted difference: a too-short trailing
  fragment can't be merged backward into an already-dispatched
  sentence, so it's spoken alone instead); that no tag text ever
  reaches a spoken sentence; that `stream_turn()` really does call
  `on_sentence()` before the whole reply (first sentence confirmed
  dispatched well short of the full text having streamed in, not just
  at the end); that `stream_turn()` and `take_turn()` agree on the same
  reply text; and that a simulated network failure partway through
  still rolls back history exactly like `take_turn()`'s own error path.
- **Last confirmed passing**: 2026-10-12.
- **Not covered**: a real live-device latency measurement (see the
  "Coordinator turn" entry above); the real Anthropic streaming
  endpoint's own wire behavior (chunk sizes, timing) - only exercised
  against a fake client here, though `test_coordinator.py --live`
  exercises the real one when `ANTHROPIC_API_KEY` is valid.

### Listener VAD + STT

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 3 and [STT](specification.md#42-speech-to-text-stt) —
  `listener.py`'s VAD end-pointing and turn-taking gate, and `stt.py`'s
  transcription and non-speech rejection.
- **Script**: [`../tests/test_listener.py`](../tests/test_listener.py),
  with fixture `../tests/data/quick_brown_fox_ch1.wav` (Chip on capture
  channel 1, background noise at the start).
- **Run**: `venv/bin/python tests/test_listener.py` (automatic, no
  hardware; needs the model files in `models/`, see CLAUDE.md).
- **Expected**: prints the utterance's start/length and transcript, then
  `PASS: listener segments one utterance, ignores silence and gated
  input; STT transcribes speech and rejects noise`, exit 0. Checks: one
  utterance cut from the recording (start 0.2-0.7s, 3.5-5.5s long);
  silence produces none; `ignore_until()` suppresses one, and going deaf
  then reopening the gate lets it through; the transcript contains
  "jumps over the lazy dog"; real room noise and white noise are
  rejected.
- **Last confirmed passing**: 2026-09-25.
- **Not covered**: pure digital silence (tiny.en says "you" — known,
  see specification.md 4.2); the live mic path, checked by hand with
  `venv/bin/python listener.py --save DIR` (2026-09-25: five utterances,
  two word errors, see log.md 4.16).

### Playback thread

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 1 — `playback.py`: output gain (`OUTPUT_GAIN_DB`, now
  `0.0` — see [Open Issue 26](specification.md#5-open-issues), resolved
  via an external amp), mono→2ch duplication, gapless back-to-back
  queueing, and started/finished events.
- **Script**: [`../tests/test_playback.py`](../tests/test_playback.py)
- **Run**: `venv/bin/python tests/test_playback.py` (automatic, no
  hardware) or add `--listen` to also play `IllBeBack.wav` then
  `MayGodBless.wav` through the bird (**needs a person listening**).
- **Expected**: prints `PASS: playback gain cap, mono->2ch, gapless
  queue, and events correct` and exits 0. The automatic part drives the
  audio callback directly with fake buffers: checks both channels are
  identical, samples are scaled by `OUTPUT_GAIN_DB`, the second item
  starts on the very next sample after the first (including mid-block),
  output is silent once the queue is empty, and events arrive in order
  with the right timestamps. `--listen` also checks, on the real device,
  that events arrive in order and total played time matches the clips'
  combined length within 50ms; the listener confirms both clips sound
  clean with no gap or click.
- **Last confirmed passing**: 2026-09-25, including `--listen` (twice,
  confirmed clean by ear).
- **Not covered**: behavior under load (other threads competing for CPU).


### Beak-sync

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 6 — `serial_link.py` (the Serial writer: latest-wins beak
  commands, head commands as an ordinary FIFO not yet used) and
  beak-sync in `playback.py` (RMS envelope → beak angle per block,
  timed against the block's `dac_time`). See
  [4.8](specification.md#48-beak-sync-rms-envelope-extraction).
- **Script**: [`../tests/test_beak_sync.py`](../tests/test_beak_sync.py)
- **Run**: `venv/bin/python tests/test_beak_sync.py` (automatic, no
  hardware).
- **Expected**: prints `PASS: beak mapping, envelope, callback wiring,
  and SerialWriter latest-wins/timing correct` and exits 0. Checks the
  dBFS-to-beak-angle mapping (floor/ceiling/clamping), that sustained
  loud audio opens the beak and sustained silence rests it closed, that
  nothing is sent when no `SerialWriter` is attached, and that
  `SerialWriter`'s bounded FIFO delay line sends queued beak commands in
  order once each one's `dac_time` arrives, dropping only the oldest if
  it ever backs up past `BEAK_QUEUE_MAXLEN` — all against fake
  buffers/clocks, no serial port or speaker needed.
- **Last confirmed passing**: 2026-10-06.
- **First live watch, 2026-10-06** (`playback.py wavFiles/AlignmentTone.wav
  --beak`, Chip watching the real bird): 7 of 8 tone/silence cycles
  looked well-synced by eye; the first consistently starts late
  (repeatable — see `docs/specification.md` section 4.8 and `docs/log.md`'s
  4.8 history for the full diagnosis and two untested experiments tried).
  `ALIGNMENT_FUDGE_S` and the envelope floor/ceiling/attack/release
  defaults are still untuned — Chip is doing a frame-matched video
  analysis off-line for a precise offset number.
- **Not covered — needs a person watching and listening to the real
  bird**: whether the two first-cycle experiments
  (`ARDUINO_BOOT_DELAY_S`, `WARMUP_CMD`) actually fixed it, and the
  precise alignment offset/envelope tuning above. Procedure:
  `venv/bin/python playback.py wavFiles/AlignmentTone.wav --beak` (opens
  the Arduino) and watch/listen for the beak opening exactly during the
  tone, closing exactly during the silence.


### Capture thread

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 2 — `capture.py`: keeps the chosen capture channel
  (`CAPTURE_CHANNEL`, currently 1) as mono 80ms frames with ADC
  timestamps.
- **Script**: [`../tests/test_capture.py`](../tests/test_capture.py)
- **Run**: `venv/bin/python tests/test_capture.py` (automatic, no
  hardware) or add `--live` to also record 3 seconds from the real
  XVF3800 (no person needed).
- **Expected**: prints `PASS: capture keeps channel 1 as mono 80ms
  frames` (plus `, live stream healthy` with `--live`) and exits 0. The
  automatic part feeds the callback a fake 2-channel buffer and checks
  the right channel comes out, as a 1280-sample frame, as a copy (not a
  view of the device buffer), with the timestamp passed through.
  `--live` checks frame count and size, evenly spaced timestamps, no
  input overflows, and a non-zero signal.
- **Last confirmed passing**: 2026-09-25, including `--live`.
- **Not covered**: which channel is *better* (judged by ear and level
  analysis, see log.md 4.16), and simultaneous playback + capture (checked
  once by hand 2026-09-25, not scripted yet).

### Speaker level ladder (manual, listening)

- **Covers**: [3.2](specification.md#32-seeed-respeaker-xvf3800) /
  [3.3 Speaker](specification.md#33-speaker) — Pi → USB → XVF3800 →
  speaker playback at the fixed 16kHz/S16_LE/2ch format, and where the
  output starts clipping ([Open Issue 26](specification.md#5-open-issues)).
- **Script**: [`../tests/test_speaker_level_ladder.py`](../tests/test_speaker_level_ladder.py)
- **Run**: `venv/bin/python tests/test_speaker_level_ladder.py [clip.wav] [dB ...]`
  (defaults: `DeadMenTellNoTales.wav` at −14, −10, −6, −3dBFS). Sets both
  XVF3800 `PCM Playback Volume` controls to max (60) first, then plays
  the clip once per step, loudest last, with 2s of silence between.
  **Needs a person listening at the bird.**
- **Expected**: every step is audible. The result to record is the
  loudest step that still sounds clean.
- **Last run**: 2026-09-25, board unmounted on the table: −14 and −10
  clean, −6 crackling, −3 worse (0dBFS was mostly static in an earlier
  one-off play). Same day through headphones on the 3.5mm jack: all four
  steps clean and plenty loud — the clipping is in the speaker path only.
  Record the new ceiling here after any Issue 26 fix.
- **Not covered**: AEC, and anything automated — there's no mic-side
  check that the sound actually came out.

### DoA walk-around (manual, measurement)

- **Covers**: [Direction of Arrival (DoA) Reader](specification.md#49-direction-of-arrival-doa-reader)
  calibration - which `doa.py` angle is Jack's front, and which way is
  his left.
- **Script**: [`../tests/doa_walkaround.py`](../tests/doa_walkaround.py)
- **Run**: `venv/bin/python tests/doa_walkaround.py [--out doa.csv]
  [--window 12]`. **Needs the real bird, mounted, and as quiet a house
  as possible.** Jack speaks each position aloud; count aloud there
  until he speaks again.
- **Expected**: per position, the circular mean and spread of the
  speech-flagged readings from the last 5s of its window; the raw
  readings saved as CSV. No pass/fail - a good run steps steadily round
  the circle (front, front-left, left one way; front-right, right the
  other) with small spreads, and holds still while Jack talks.
- **Last run**: 2026-10-15 (an earlier ad hoc version, 10s windows):
  inconclusive - bird loosely placed, household noise; see log.md 4.9.
- **Not covered**: positions behind the bird, distance, and wiring into
  `motion.py`.

## Wake Word Spotter

### Spotter mechanism (`WakeSpotter`)

- **Covers**: [4.1 Wake Word Spotter](specification.md#41-wake-word-spotter)
  — `wakeword.py`'s `WakeSpotter`, the real-time counterpart of
  `coordinator.py`'s Enter/`sleep` keyboard stand-ins: runs openWakeWord's
  bundled onnx feature pipeline over Capture's 80ms frames, feeding the
  two trained custom classifiers (`wake_phrase.onnx`, `sleep_phrase.onnx`
  — see `docs/log.md`'s 4.1 history for how they were trained).
- **Script**: [`../tests/test_wakeword.py`](../tests/test_wakeword.py)
- **Run**: `venv/bin/python tests/test_wakeword.py` (automatic, no
  hardware — a fake model stands in for the mechanism checks; the real
  `.onnx` files are loaded once for the silence check, CPU only).
- **Expected**: prints `PASS: WakeSpotter gates on ignore_until,
  debounces via cooldown, and the real models load and stay quiet on
  silence` and exits 0. Checks `ignore_until` drops a frame without even
  calling the model (turn-taking, same semantics as `Listener`'s),
  `COOLDOWN_S` lets a sustained high score fire once and then again only
  after the cooldown elapses (with a fake model forcing the score, so
  it's deterministic), and that the real shipped models load and return
  near-zero scores with no detections on digital silence.
- **Last confirmed passing**: 2026-10-12.
- **Live-watched standalone**, 2026-10-11 (`venv/bin/python
  wakeword.py`, real bird, low-level background family noise in another
  room): both phrases detected correctly when spoken, several other
  non-wake phrases spoken in between correctly ignored, no false
  positives, no missed detections. Not this script's job to cover -
  real detection accuracy isn't a mechanism check, and exact
  threshold/patience/cooldown numbers were still spec 4.1's deferred
  real-audio calibration at that point.
- **Wake threshold calibrated, 2026-10-12** (`coordinator.py --save`,
  voice only, no keyboard stand-ins): 5/5 wake attempts fired correctly
  across close/soft/distant delivery and a second speaker, scoring
  0.82-1.00; a stretch of undirected background talk never crossed 0.5.
  `WAKE_THRESHOLD` raised 0.5 → 0.65 on that data (see docs/log.md's 4.1
  history).
- **Sleep threshold checked, left unchanged, 2026-10-12** (same method,
  focused on "Goodnight, Jack"): 4/5 attempts fired cleanly (0.91-1.00);
  the one miss printed nothing at all (scored under the 0.1 debug floor,
  not a near-miss on 0.5), so no threshold number would have caught it.
  `SLEEP_THRESHOLD` left at the vanilla default. `PATIENCE_FRAMES`/
  `COOLDOWN_S` still untouched - no data pointing at either.
- **Not covered**: `PATIENCE_FRAMES`/`COOLDOWN_S` calibration (no data
  suggesting either needs to move). Wired into `coordinator.py` and
  live-watched there too, see `test_coordinator.py`'s entry above and
  log.md's 4.16 history for the full story (closes out build step 7's
  wake-word piece).

## Home Automation

### Home-automation tools

- **Covers**: [Home-Automation Tool Schema](specification.md#46-home-automation-tool-schema)
  (`home.py`, 2026-10-18) and the tool round trip in
  [Conversation Orchestrator](specification.md#43-conversation-orchestrator)'s
  `take_turn()`/`stream_turn()` - the allowlist in
  [home-automation-allowlist.md](home-automation-allowlist.md) enforced
  in code against the real inventory CSV.
- **Script**: [`../tests/test_home_tools.py`](../tests/test_home_tools.py).
- **Run**: `venv/bin/python tests/test_home_tools.py` (automatic, no
  network, no devices, no API - a fake vendor link and a fake client).
- **Expected**: prints `PASS: inventory loads only allowed devices;
  refusals never reach a vendor; ...` and exits 0. Checks that only
  `Jack controls = yes` rows load (no ecobee, Office Outlet, broken
  Switch 1, or disconnected Govee lights) with unique names; that
  unknown devices, actions a Type doesn't allow, out-of-range or
  wrong-typed numbers and over-cap irrigation are refused with no vendor
  call; that the fountain pump switches off freely but on only in the
  turn right after Jack asked (a fresh request or a late yes asks
  again), while the rest of a group still switches; that vendor
  failures are reported as failures; and that the round trip speaks the
  lead-in before the tool runs (confirmed failing without
  `SpeechStreamer.flush()`), sends results back, parses tags from the
  final part, keeps history valid, rolls back on an API error, and
  stops after `MAX_TOOL_ROUNDS`.
- **Last confirmed passing**: 2026-10-18.
- **Not covered**: the real vendor APIs (`vendors.py`) - see
  `list_devices.py` for a read-only check that all three answer; live
  control is confirmed by hand (2026-10-18 via `orchestrate.py`, Chip
  watching, every step correct and each device restored afterwards:
  Office Light off/"turn it back on"; Pendant Lights 20%/100%/66%+off;
  Office Fan speed 1/4/2+off; Office Strip Lights on/red/blue at 30%/
  white+off; Courtyard zone started for 3 min, "stop the watering" at
  2 min - stopped; "turn on the courtyard fountain" held and asked about
  water, "No" made no call and the plug's switch read back off).
  Whether Haiku actually asks about the
  fountain's water and only calls again on a real yes - code enforces
  the turn order, Haiku judges the answer.

### Haiku model comparison (manual, diagnostic)

- **Covers**: which Haiku model/settings Jack runs on
  ([spec 4.3](specification.md)) — `compare_models.py`, not part of the
  automatic suite (costs real API calls; persona quality needs a human
  read).
- **Script**: [`../compare_models.py`](../compare_models.py)
- **Run**: `venv/bin/python compare_models.py [--repeat N] [--only
  4.5,5.5-off] [--show]` (needs `ANTHROPIC_API_KEY`). Three scripted
  conversations (office devices, guard rails, chat/memory), 20 turns,
  through the real prompt, tools and allowlist with a fake vendor link -
  no device is switched. Fresh scratch memory per run. One full pass of
  all four configs costs about ten cents.
- **Expected**: per-turn checks (right device calls, MODE tag, memory
  saved) and a summary table: checks passed, median/max time to first
  sentence, median tool-turn time, mean words, $ per turn.
- **Last run**: 2026-10-19 — see `docs/log.md` 4.3 for results.
- **Not covered**: STT/TTS time, real vendor latency, and judging the
  pirate voice - that's done by reading `--show`'s replies.
