---
name: reorient
description: Use mid-task when the working thread is lost — after a context compaction, a long agent run, or coming back to a feature unsure of the role, the current checkpoint, or the next action. Triggers — "/engineer.reorient", "reorient", "re-anchor", "what should I be doing right now", "I lost track", "where was I".
---

# reorient

Restore the working contract mid-task. After a context compaction or a long
run, an agent loses role identity, invents constraints that do not exist, skips
required steps, and loses the task thread. `reorient` reloads the durable state
that should have survived — the discipline contract first, the task pointer
second.

Read-only and advisory. It changes nothing, produces no artifact, and emits
**no handoff** — like `next`, the orientation block is the whole output; a
handoff would only restate it. The third skill exempt from the agentic summary
contract.

`reorient` is the mid-task, feature-scoped counterpart to `next` (project-scoped,
session-start).

## When to use

- Right after a context compaction (a `SessionStart` hook can auto-invoke it).
- Mid-task, when unsure of the role, the current checkpoint, or the next action.
- Returning to a feature after an interruption.

**Not for:** session-start "what should I pick up across the project" (`next`);
loading a feature not yet started (`prime-context`); validating artifacts
(`consistency-check`).

## Workflow

### Step 1 — Resolve and locate

Resolve the methodology root + manifest via
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_resolve.py` (see `references/resolving.md`).
Locate the feature (slug arg or branch name). If no feature is in scope, say so
and suggest `next` instead.

### Step 2 — Reload the discipline contract, then the task pointer

Read, read-only, in this order:

1. **Role + autonomy** — `CHARTER.md` + manifest: the autonomy level in force,
   and what the agent may and may not decide. Counters invented constraints.
2. **Current checkpoint + exit criteria** — the Checkpoint Exit Contract
   (Foundation Design Section 8) for the checkpoint `progress.md` shows in
   progress: its goal, its exit criteria, and which are already met.
3. **Non-negotiables** — verification independence and charter-mandated
   mutation: steps that must not be skipped regardless of cost. The cost of a
   step is never a reason to skip it.
4. **Current task + next action** — the `progress.md` CURRENT header.
5. **Feature contract** — `feature.md` outcome + scope. Counters goal drift.

Also run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_handoff.py <feature-dir>` — report any
checkpoint marked done without a complete handoff as a discipline gap.

### Step 3 — Emit the orientation block

Output one tight block, nothing else:

```
You are <role> at autonomy <level>.
Feature NNN-slug — Checkpoint N (<goal>).
Exit criteria: <m>/<n> met — unmet: <list>.
Current task: <task> -> next action: <action>.
Must not skip: <non-negotiables>.
Constraints: <charter / autonomy limits>.
```

### Step 4 — Stop

`reorient` orients; it does not act. The human resumes the work. No handoff.

## Optional: auto-invoke on compaction

A project may add a `SessionStart` hook (`source: compact`) that nudges
`/engineer.reorient` after every compaction. See
`${CLAUDE_PLUGIN_ROOT}/examples/session-start-reorient.md`. The hook is optional
project config, not part of this skill.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) —
  the Checkpoint Exit Contract (Section 8); agentic summary exemptions (Section 5)
- Sister skill: `next` — the project-scoped, session-start counterpart
