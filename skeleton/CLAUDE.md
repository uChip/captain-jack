# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working on this project.

## Project state

Fill this section in with what is currently operational and current limitations.
Note any basic / common invocations or needs (credentials, etc) for access.

Update per session as changes in state evolve.

## Project Rules

1 Don't re-litigate without new information.
2 Cross-link rather than duplicate information.
3 Use github
   - Ask before committing and pushing
   - Commit/push changes promptly so as to minimize work lost if systems crash or connections drop
4 Issues get a unique number as a reference.  Number persists issue closing.
   - Add a current status tag **OPEN**, **RESOLVED**, etc following number to allow scanning list without fully reading each item.
5 Use the following project documentation structure starting with a docs folder, then in that folder
   - specification.md defines what is being created
      - contains current definition. "one truth"
      - can contain undefined blocks or open issue summaries (one line) until finalized
         - linked to full issue description in log.md
      - evolves with project until specification finalized
         - finalized means no more open issues or blocked work and all participants agree specification is complete.
      - link to external file (usually log.md) for full description, historical details, discussions etc
   - log.md keeps track of history, decisions, changes, and discussions
      - item (issue, spec section, decisions) definitions in detail
      - discussion and history
      - often contains the "why" or "how we got here" as well as alternatives, tradeoffs and the ultimate resoltion
      - updated at least per session
   - tests.md lists descriptions of tests generated
   - archive folder
      - usually not needed for current context
      - If incoming or pre-existing files auxilary to specification.md, log.md and tests.md are to be modified, copy original to archive folder first.
   - tests folder
      - Any generated test code or scripts should get placed in the tests folder and described in docs/tests.md
6 Don't delete information.  If superceded or no longer relavent, move to log and mark it as such.

## What this project is

Fill this in with a high-level summary project description.  Include key decisions
and project boundaries already decided.
This is a summary to provide general context.  Links to current definition, in docs/specifications.md.  Links to history, detailed decisions and current discussion context in docs/log.md. 

Content in this section should be at a high enough level that it doesn't necessarily change every session,
but make sure it stays up-to-date as the project progresses.

## Done so far

Keep a working list of accomplishments.  Update per session.

## Work list — split by dependency

Work list is about work still to come.  Update per session.

Separate into 

### Doable now

Work that is not blocked.

### Blocked waiting on some event or deliverable

Work that is waiting on separate deliverables.  Note what it is waiting on.
