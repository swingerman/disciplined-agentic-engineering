---
name: session-summary
description: Use at the end of a work session on a DAE feature, so the next session picks up cleanly. Triggers — "/engineer.session-summary", "wrap up the session", "write the session log", "I'm stopping for the day".
---

# session-summary

Write the per-session entry in a feature's `session-log.md` so the human can close the laptop and pick back up cleanly. The human-readable counterpart to the machine handoffs. `checkpoint: null`.

## When to use

At the end of a work session on a feature. A Stop hook may auto-invoke it; that hook is optional plugin config, not part of this skill.

**Not for:** mid-session (nothing's wrapping up); syncing the tracker (`progress-log`); per-skill records (each skill's own handoff).

## Workflow

1. **Resolve + scope** — find `.engineer/manifest.yml`; resolve `methodology_root`. Scope = the feature(s) the session touched (default: current branch; multiple → an entry in each; none → nothing to log, stop).
2. **Gather** — synthesize from this session's `handoffs/*.md`, git activity on the branch, and conversation context (decisions, problems, deferrals).
3. **Append the entry** — append (never overwrite) to `features/NNN-<slug>/session-log.md`:

```markdown
## Session — <ISO date> <start>–<end>
**Current state:** <which checkpoint, one line>
### Previous tasks (done this session)
- ...
### Current task
- <in progress at session end, if any>
### Next tasks
- <concrete, actionable, ordered>
### Open questions / blockers
- <or "None">
```

Create the file with a `# Session log — <title>` heading if absent.

4. **Handoff** — emit a summary.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: null`; `human_action_needed: no`; `recommended_next`: the first "Next task" from the entry. (session-summary is not the handoff processor, so it follows the normal contract — no exemption.)

## session-log.md vs handoffs vs progress.md

Three records, three readers: `handoffs/` = machine, per-invocation; `progress.md` = machine-derived, glanceable; `session-log.md` = human, per-session, narrative. They don't duplicate — different granularity, different reader.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — `session-log.md` in the storage layout, the session-log ↔ handoffs distinction (Section 5)
