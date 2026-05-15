---
name: session-summary
description: Use at the end of a work session on a DAE feature, to write a session-log entry so the next session picks up cleanly. Triggers include "/engineer.session-summary", "wrap up the session", "write the session log", "summarize what we did", "I'm stopping for the day", or naturally when the user signals they're closing the laptop. Synthesizes this session's handoffs, git activity, and conversation into a human-readable session-log.md entry — previous tasks done, current state, next tasks, open questions. Appends per session; never overwrites prior entries.
---

# session-summary

Write the per-session entry in a feature's `session-log.md` so the human can close the laptop and pick back up cleanly next session.

This is the human-readable counterpart to the machine handoffs. Handoffs in `handoffs/` are granular, per-skill-invocation, machine-shaped. `session-log.md` is narrative, per-session, "where am I and what's next" — the thing a human reads first thing tomorrow.

## When this skill runs

At the end of a work session on a feature. Not a checkpoint (`checkpoint: null`). Cross-cutting — a session can end at any pipeline stage.

A Stop hook may auto-invoke this skill at session end; that hook is optional plugin configuration, not part of this skill. The skill works the same whether invoked by a hook, by another skill, or directly by the user.

## Workflow

### Step 1 — Resolve and scope

Walk up to `.engineer/manifest.yml`; resolve `methodology_root`. Determine which feature(s) the session touched:
- Default → the feature on the current branch
- If the session worked multiple features → write an entry to each one's `session-log.md`
- If the session touched no feature → there is nothing to log; say so and stop

### Step 2 — Gather what happened this session

For each in-scope feature, synthesize from three sources:
- **Handoffs** — `handoffs/*.md` entries emitted during this session (their `skill`, `checkpoint`, `findings_summary`, `human_action_needed`, `recommended_next`)
- **Git activity** — commits / changed files on the feature branch during the session
- **Conversation context** — decisions made, problems hit, things deferred that aren't captured in a handoff

### Step 3 — Append the session-log entry

Append (never overwrite) an entry to `<methodology_root>/features/NNN-<slug>/session-log.md`:

```markdown
## Session — <ISO date> <start>–<end>

**Current state:** <which checkpoint the feature is at, in one line>

### Previous tasks (done this session)
- <what was accomplished — one bullet per meaningful unit of work>

### Current task
- <what was in progress when the session ended, if anything>

### Next tasks
- <what to do next session — concrete, actionable, in order>

### Open questions / blockers
- <anything unresolved the human should decide; anything blocking progress — or "None">
```

If `session-log.md` doesn't exist yet, create it with a `# Session log — <feature title>` heading, then the entry.

### Step 4 — Emit the handoff summary

session-summary follows the normal agentic summary contract (it is not the propagation engine — emitting a handoff causes no loop).

```markdown
---
skill: session-summary
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: null
artifacts:
  - features/NNN-<slug>/session-log.md
findings_summary: <one line — e.g. "session logged; feature at Checkpoint 5, 2 next tasks">
human_action_needed: no
human_action_kind: none
recommended_next: <the first "next task" from the session-log entry>
tracker_update: none
status: complete
---

# session-summary — handoff summary

## What I did
Wrote the session-log entry for `<title>`: <N> tasks done this session, feature now at <checkpoint>, <M> next tasks queued.

## Artifacts produced
- `features/NNN-<slug>/session-log.md` (session entry appended)

## Findings
<anything notable — a blocker logged, an open question that needs a decision before next session>

## Human action needed?
No — session logged. Pick up next session from the "Next tasks" list in session-log.md.

## Recommended next step
<the first next-task from the entry>
```

## session-log.md vs handoffs vs progress.md

Three records, three readers:
- **handoffs/** — machine, per-skill-invocation. The granular event stream. Consumed by `progress-log`.
- **progress.md** — machine-derived, glanceable. Checkpoint table + verification reports. The "where is this feature" board.
- **session-log.md** — human, per-session, narrative. The "what did I do, what's next" journal. Written by this skill.

They don't duplicate — different granularity, different reader. All three coexist (locked in the Foundation Design).

## When NOT to use this skill

- Mid-session, nothing's wrapping up → no entry to write yet
- You want to sync the tracker / update progress.md → that's `progress-log`
- You want a per-skill record → that's the handoff each skill already emits

## Cross-skill orchestration

session-summary runs at session end. It reads this session's handoffs + git + conversation, writes the `session-log.md` entry, emits a normal handoff.

- Upstream: every skill that ran this session (their handoffs are the raw material)
- This skill: synthesizes them into the human-readable session entry
- Downstream: the next session's human reader; optionally `progress-log` processes this skill's handoff

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — `session-log.md` in the storage layout, agentic summary contract, the session-log ↔ handoffs distinction (Section 5)
- The DAE methodology page — the three-layer visibility model (roadmap / tracker / session log)
