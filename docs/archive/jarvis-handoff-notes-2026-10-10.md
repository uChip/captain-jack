# Jarvis — Handoff Notes (extracted from captain-jack)

Extracted from `parrot-project-brief.md` on 2026-09-11, once the
one-bird-vs-two-birds question was decided in favor of two physically
separate birds. Jarvis is a separate project on separate hardware from
Captain Jack — this file exists so nothing gets lost, but it belongs in
Jarvis's own project directory once one exists, not tracked here.

## Jarvis — the primary desktop assistant

- Personality: companionable but more formal, "major domo" — butlerish.
- Broad task responsibility and system access (this is the "full agentic"
  instance).
- Runs on **Claude Code**, voice-bridged using jaredrhod's **backtalk**
  pattern (push-to-talk voice I/O into a live Claude Code session, local
  STT, real-voice TTS output, full tool access preserved).
- Memory: jaredrhod's **ai-memory-vault** ("Jarvis" stack), full install —
  a folder of plain markdown files (`CLAUDE.md` boot/identity doc, profile,
  daily notes, "Jobs") that the agent reads/writes each session.
- Billing: Claude **Pro plan** ($17-20/mo flat), which includes Claude Code.

## Former next step (removed from captain-jack's list)

Set up jaredrhod's `ai-memory-vault` + `backtalk` for Jarvis if not already
running, per the fullstack-agent installer.

## Still relevant to Captain Jack (kept in the brief, not duplicated here)

- Cost approach and the shared-Pro-plan-usage caveat — both still live in
  `parrot-project-brief.md`'s "Decisions already made," since they concern
  the same Anthropic account regardless of which project Jarvis ends up
  living in.
