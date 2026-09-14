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
