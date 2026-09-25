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
### Playback thread

- **Covers**: [Runtime Integration](specification.md#416-runtime-integration-end-to-end-turn)
  build step 1 — `playback.py`: output gain cap (interim fix for
  [Open Issue 26](specification.md#5-open-issues)), mono→2ch
  duplication, gapless back-to-back queueing, and started/finished
  events.
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
- **Not covered**: beak-sync (build step 6), and behavior under load
  (other threads competing for CPU).


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
