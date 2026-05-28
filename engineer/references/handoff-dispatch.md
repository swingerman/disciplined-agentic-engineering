# Handoff Dispatch — when to keep going, when to stop

After a skill writes its handoff, the next checkpoint often needs a **fresh agent** (e.g. charter §6 separates implementer from verifier). The fresh-agent rule is structural — it means "a different agent context than the one that just ran" — and a **subagent dispatched via the Agent tool satisfies it**, just as well as a brand-new human-initiated session.

**Do not bounce mechanical dispatch decisions back to the human.** The pause where the implementing agent says "want me to dispatch the verify subagent?" is friction with no upside — the user will say yes every time, and the answer was deterministic from the handoff.

## The rule

**Stop ONLY when:**

1. Something is **genuinely ambiguous** about what to do next (multiple plausible directions, no clear winner).
2. The charter or feature explicitly requires **human verification or acceptance** at this checkpoint (e.g. a `plan_status: pending-approval` gate; a high-risk migration the charter flags).
3. The active feature's effective `autonomy_level` is **`low`** — the lowest level is explicitly the "ask first" mode.

**Otherwise: DISPATCH** the next agent automatically via the Agent tool. Brief it with the feature slug, the relevant handoff, and the next-checkpoint instructions.

## Autonomy decision table

| Effective `autonomy_level` | Default dispatch behavior |
|---|---|
| `low` | Confirm with the user before dispatching ("ready to spawn the verify subagent?"). One-line confirm, then go. |
| `medium` | Auto-dispatch. Surface the dispatch in a single line ("dispatching verify subagent for `<feature>`"); no question. |
| `high` | Auto-dispatch silently. Report only the subagent's outcome. |

Effective autonomy = `feature.md` `autonomy_level`, capped by `manifest.autonomy.path_overrides` for the feature's path. Read this once during the skill's resolve step; it's already loaded.

## Special case — the next agent needs resources you can't access

If the next-checkpoint work needs something the implementer can't provide (live emulators on the user's machine, prod credentials, hardware), **do not dispatch**. Instead, write the exact dispatch command into the handoff:

```
to dispatch verify:
  start firebase emulators in a terminal: `firebase emulators:start`
  then invoke: /engineer.verify --feature <slug>
```

Stop after writing the command. Do **not** ask "should I dispatch?" — you've already declared why you can't.

## Subagent brief template

When you do dispatch via the Agent tool, use this shape:

```
description: <Checkpoint N for <feature-slug>>
prompt:
  You are running Checkpoint <N> for feature <slug> in a DAE methodology project.

  Context:
  - Working dir: <abs path>
  - Branch: <branch>
  - Previous checkpoint's handoff: <path to handoff .md>
  - Feature artifacts: features/<slug>/{feature.md, acs.md, spec.md, plan.md, progress.md}

  Your job: <one-paragraph charge from the next-checkpoint's skill description>.

  Constraints:
  - You are the fresh agent the charter §6 calls for; do NOT relax independence.
  - Honour the effective autonomy_level: <low|medium|high>.

  Report on completion: <what the parent skill expects back>.
```

The brief is **self-contained** — the subagent doesn't see the parent skill's conversation.

## What this rule replaces

Previously, every implementing skill ended with a passive handoff and the human had to manually invoke the next checkpoint. That bounced ten mechanical decisions per feature back to the human. The rule above keeps the human in the loop for the decisions that matter (ambiguity, charter-required acceptance, low autonomy) and removes them from the ones that don't.
