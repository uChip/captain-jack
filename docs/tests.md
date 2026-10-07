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
  `NAP`, parsed by `split_mode_line()` and threaded through `take_turn()`
  into `Turn.mode`.
- **Script**: [`../tests/test_mode_tag.py`](../tests/test_mode_tag.py)
- **Run**: `venv/bin/python tests/test_mode_tag.py` (automatic, no
  hardware, no real API — a fake Haiku client).
- **Expected**: prints `PASS: MODE: tag splits correctly and take_turn()
  wires it into Turn.mode` and exits 0. Checks `split_mode_line()`
  splits `END_SESSION`/`NAP`/`NONE` correctly, normalizes case, and fails
  closed to `None` on a missing or malformed line (e.g. an older reply
  with no `MODE:` line at all); checks `take_turn()` strips both the
  `MODE:` and `MEMORY:` lines from the spoken reply and surfaces
  `END_SESSION` correctly in `Turn.mode`, with explicit `MODE: NONE` and
  a missing `MODE:` line both surfacing as `Turn.mode is None`.
- **Last confirmed passing**: 2026-10-07.
- **Not covered**: the live Haiku API path (whether Haiku actually emits
  `MODE:` correctly in conversation), `identity.md`'s instructions
  (added this session) actually producing good end-of-session behavior,
  and `coordinator.py` acting on `Turn.mode` — none of that is wired up
  yet.

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
  per-mode step logic (ambient, due excursions, idle wav scheduling) —
  a faithful port of `exercise_hardware.py`'s already hardware-validated
  gesture logic into a real long-lived thread with `set_mode()`.
- **Script**: [`../tests/test_motion.py`](../tests/test_motion.py)
- **Run**: `venv/bin/python tests/test_motion.py` (automatic, no
  hardware — a small synthetic catalog, not the real
  `gesture-catalog.yaml`, to avoid its real `wait_ms` timings).
- **Expected**: prints `PASS: resolve_move clamping, cross-library
  gesture lookup, and ambient/excursion/wav scheduling correct` and
  exits 0. Checks delta clamping against each axis's range, that beak is
  absolute (not baseline-relative) and leads the command, that omitting
  beak emits no `b<N>` token, that `find_gesture_anywhere()` finds a
  gesture living in `wav_paired` or directly in a mode library (and
  raises `KeyError` for an unknown id), and that a single Off Watch step
  plays the ambient gesture, fires a due excursion, and schedules the
  one off_watch wav (with Asleep's wav-paired-gesture beak move firing
  alongside its clip, and On Watch using its own ambient).
- **Last confirmed passing**: 2026-10-07.
- **First live watch, 2026-10-07** (`motion.py --mode off_watch
  --dry-run --seconds 15` against the real bird, Chip watching): clean
  output, no crash, correct asymmetric breathing swing from
  [Open Issue 25](specification.md#5-open-issues) plus an excursion;
  Chip confirmed the bird moved correctly.
- **Not covered**: DoA-based yaw tracking (`read_doa_azimuth()` is still
  a stub), On Watch excursions (not implemented — conversation/emotion-
  triggered, per spec 4.12), and `Motion` wired into the live
  `coordinator.py` loop (not done yet — this test and the dry-run above
  only exercise `motion.py` standalone).

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
  `stt.rejection_reason()`.
- **Script**: [`../tests/test_stt.py`](../tests/test_stt.py)
- **Run**: `venv/bin/python tests/test_stt.py` (automatic, no hardware,
  no model).
- **Expected**: prints `PASS: 9 real transcripts accepted, 6
  loops/gibberish rejected` and exits 0. Inputs are real transcripts and
  probabilities from the 2026-09-25 live runs: Chip's clear speech must
  pass; the "Where is the anchor?" x5 loop, two echoed gibberish guesses
  and "P" (0.02) must be rejected.
- **Last confirmed passing**: 2026-09-25.
- **Not covered**: gibberish that comes out as a single plausible,
  confident sentence ("is good word") — no local rule catches that yet.

### TTS thread

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 5 and [TTS](specification.md#47-text-to-speech-tts) —
  `tts.py`'s sentence splitting, markdown clean-up, 24→16kHz resampling,
  and kokoro-pi synthesis.
- **Script**: [`../tests/test_tts.py`](../tests/test_tts.py)
- **Run**: `venv/bin/python tests/test_tts.py` (automatic, no hardware,
  no model) or add `--live` to synthesize with kokoro-pi (needs the
  models built in `models/kokoro-pi`, see CLAUDE.md).
- **Expected**: prints `PASS: sentence split, clean-up, and 24k->16k
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
  `take_turn()` — utterance → Whisper → Haiku → reply + memory save,
  session start/end, noise rejection — and the
  [Sleep-Mode State Machine](specification.md#411-sleep-mode-state-machine)'s
  transitions (`MODE: END_SESSION`/`NAP`, wake from Asleep, the
  sleep-phrase stand-in's Off-Watch-only gating, both timeouts), driven
  directly through `_handle_event()`/`_handle_timeout()` without
  starting real audio threads. Also covers a real race found in a live
  test: a multi-sentence reply must keep the mic deaf across its own
  internal sentence gaps, not just after the whole reply ends, or a
  stray sound there can clobber the in-flight reply's tag tracking and
  silently drop a pending `MODE:` tag (see log.md 4.16, "Goodnight,
  Jack" live test, 2026-10-07).
- **Script**: [`../tests/test_coordinator.py`](../tests/test_coordinator.py),
  with fixture `../tests/data/quick_brown_fox_ch1.wav`.
- **Run**: `venv/bin/python tests/test_coordinator.py` (automatic, no
  hardware, no API — a fake Haiku client) or add `--live` for one real
  Haiku call (needs `ANTHROPIC_API_KEY`; a fraction of a cent).
- **Expected**: prints `PASS: coordinator transcribes, calls Haiku, saves
  memory to scratch only, rejects noise, the Sleep-Mode State Machine
  transitions correctly, and the mic stays deaf across a multi-sentence
  reply's own sentence gaps` (plus `, live Haiku replied`) and exits 0.
  Everything runs on a scratch copy of `memory/`; the test fails if the
  real `memory.md` changes.
- **Last confirmed passing**: 2026-10-07.
- **Not covered**: the keyboard wake and the timeouts firing in real
  time (logic checked directly, not the timer); beak-sync/motion
  together with a live reply (checked live by hand against the real
  bird, see log.md 4.16).

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
