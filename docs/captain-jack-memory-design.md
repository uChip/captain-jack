# Captain Jack — Memory System Design

Context: this is the pared-down memory system called for in
`docs/parrot-project-brief.md` (Software architecture section, and next
step #1). It's inspired by jaredrhod's `ai-memory-vault` pattern (plain
markdown files an AI reads/writes each session) but deliberately much
simpler, for two reasons specific to Captain Jack:

1. The full vault is an Obsidian vault (numbered folders, YAML frontmatter,
   wikilinks, per-folder index notes, "Jobs" master-notes for recurring
   tasks, protected-vs-AI-editable profile sections) built for a human to
   browse in Obsidian *and* a capable model (Claude Code) to maintain. None
   of that applies here — nothing ever browses these files but the
   orchestration code.
2. Captain Jack runs on the Haiku API with a fixed tool schema, not Claude
   Code, and per the brief **must not** get autonomous file-write tool
   access. Memory writes have to be a deterministic decision made by
   orchestration code, not the model.

## Files

- `memory/identity.md` — boot doc. Persona, tone, operating rules. Small,
  human-edited, doesn't change at runtime.
- `memory/memory.md` — durable facts + a running log, in one file, split
  into sections (see the file itself). No daily-note folders, no
  frontmatter, no wikilinks.

Both files are plain text injected verbatim into Haiku's system prompt each
turn — nothing in them should be meta-commentary aimed at a future Claude
Code session (that belongs here, in docs/, instead).

## Read/write loop

- **Read**: every turn, orchestration code reads `identity.md` and
  `memory.md` in full and includes them in the system prompt sent to Haiku.
- **Write**: Haiku's response ends with one fixed-format trailing line:
  `MEMORY: [tag] fact` or `MEMORY: NONE`. Orchestration code strips this
  line before anything is spoken (TTS never sees it), then deterministically
  decides whether to append it. The model proposes; code decides — this is
  what satisfies the brief's "not an autonomous file-write tool call"
  requirement without needing a second model call per turn.

## Save/skip ruleset

Exactly three allowed tags — an allowlist, not a "use judgment" rule, since
the brief explicitly warns the full vault's nuanced save/skip calls were
tuned against a more capable model than Haiku:

| Tag | Destination | Qualifies |
|---|---|---|
| `household:<Name>` | that person's `###` subsection under Household, auto-created on first mention | durable fact about a family member |
| `joke` | Running jokes & preferences | recurring bit, nickname, callback |
| `automation` | Home automation preferences | stated preference re: lights/thermostat/scenes/etc |

Anything else → `NONE`, discarded. This is a deliberate side effect, not
just a category restriction: most sensitive info (health, financial, etc.)
never fits any of the three tags, so it's filtered out by construction.

Two enforcement layers:

1. **Haiku-side**: `identity.md` gives Haiku the exact tag syntax and tells
   it to check the memory it was just given and say `NONE` rather than
   repeat something already listed.
2. **Code-side (authoritative)**: orchestration code never trusts the tag
   blindly. Malformed/unrecognized tag → discard, fail closed. Before
   appending, a cheap case-insensitive substring check against existing
   lines in the target section — if it's already there, skip. No fuzzy
   matching, no semantic dedup — accepted imprecision for a lightweight
   model, matching the brief's own caveat about not replicating the full
   vault's nuance here.

No standalone chronological log: earlier drafts had a "Recent log" section,
but once each save carries a tag, the tag *is* the filing decision — a
separate log would only duplicate entries that already live under their
category, dated. Dropped from `memory.md`.

## Open / TBD

- **Growth**: with the tag-routed design, growth is naturally bounded by
  household size × topic count rather than an unbounded feed, so no cap
  policy is needed for v1. If a section (e.g. one person's subsection)
  grows unwieldy in practice, revisit then rather than speculatively now.
- **Speaker ID**: see `parrot-project-brief.md`'s "Decisions already made"
  — deferred. If added later, it's a soft personalization signal layered
  on top of this memory model (e.g. informing *which* household subsection
  is likely relevant), not a rework of it — `memory.md`'s per-person
  grouping already accommodates that.
