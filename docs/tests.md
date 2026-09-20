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

### `gesture-catalog.yaml` servo bounds

- **Covers**: [Gesture Engine and Catalog](specification.md#412-gesture-engine-and-catalog)
  — every Move command string in
  [`gesture-catalog.yaml`](gesture-catalog.yaml) (the first-pass mapping
  of [gesture-library.md](gesture-library.md) into the agreed Gesture/Move
  structure).
- **Script**: [`../tests/test_gesture_catalog_bounds.py`](../tests/test_gesture_catalog_bounds.py)
- **Run**: `venv/bin/python tests/test_gesture_catalog_bounds.py`
- **Expected**: prints `PASS: gesture-catalog.yaml stays within servo
  bounds, no duplicate ids` and exits 0. Checks every `p`/`r`/`y`/`b`/`t`
  value against the real ranges in `arduino/ServoControl/ServoControl.ino`
  (pitch/roll 0-50, yaw 0-130, beak 0-60, duration 0-9999ms), every
  `wait_ms` is positive, and no gesture `id` is duplicated across
  On Watch/Off Watch/Asleep.
- **Last confirmed passing**: 2026-09-20.
- **Not covered**: whether any gesture actually looks right on the real
  bird — this only checks the data won't ask a servo to go somewhere it
  can't. Also doesn't check the two `NEEDS-RUNTIME-PARAM` entries'
  fallback values, which are known placeholders, not real behavior.
