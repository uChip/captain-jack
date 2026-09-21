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
