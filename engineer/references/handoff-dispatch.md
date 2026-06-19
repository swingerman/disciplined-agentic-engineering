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

## Channel — cloud-first, local fallback

The autonomy table decides *whether* to dispatch. This decides *where*. Once a DISPATCH decision is made, prefer a **cloud agent** and fall back to a **local subagent** only when the environment requires it.

1. Run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_delegable.py <feature-dir>` → `{channel, cloud_blockers}`.
2. **`channel: cloud`** and the project is remote-ready (`manifest.remote.ready: true`) → dispatch to the cloud: call the **Agent tool with `isolation: "remote"`** (fresh clone, runs in the background, opens a `claude/*` PR; its result returns to this pipeline). Use the same brief template below.
   - If `isolation: "remote"` is unavailable in this environment **and** the feature is `assignee: cloud` with a routine configured, fire the routine instead via the **`RemoteTrigger` `run` action** (fire-and-forget; the human reviews in claude.ai/code). Otherwise fall back to local.
3. **`channel: local`** (any blocker), or `manifest.remote.ready` is false/unset → dispatch a **local** subagent via the Agent tool (default isolation). The `cloud_blockers` list says why; surface it in one line at `medium`/`high`.

`assignee: cloud` is a *request*, not an override — a hard blocker (stdio MCP, unpushed branch, local infra) still routes local. `dae_delegable.py` is the source of truth; never hand-wave past a blocker.

When a cloud dispatch opens a PR, record `cloud_session_url` and the PR link in the feature's handoff so `progress-log` projects them and `next` can show the feature as **DISPATCHED — awaiting cloud PR**.

## Special case — the next agent needs infrastructure (emulators, drivers, services)

If the next checkpoint's work needs running infrastructure, **do not** write a "start this manually" command and stop. Instead:

1. Read `manifest.yml`'s `infra:` section.
2. Call `${CLAUDE_PLUGIN_ROOT}/scripts/dae_infra.py ensure <name> [<name> …]` for each dependency.
3. If `ensure` returns success → proceed with the dispatch.
4. If `ensure` returns a `start-failed` failure → surface the structured diagnosis to the user (`diagnosis`, `detail`, `suggested_fix`) and stop. This is one of the legitimate stop reasons.
5. If the required infra is not declared in `manifest.yml` → stop with: "declare `<name>` in manifest.yml `infra:` section per the DAE infra schema, or pre-start the service." Do NOT fall back to grep-the-README reasoning; the declaration discipline is the contract.

The old escape "I can't access live emulators / prod creds / hardware" is now narrowly: the script tried, the script failed, here's exactly what failed and how to fix it.

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
  - Code lookup: <LSP is available — use it for find-references / definitions / call-hierarchy | LSP is unavailable — fall back to grep + Read>. See references/code-lookup.md.

  Report on completion: <what the parent skill expects back>.
```

The brief is **self-contained** — the subagent doesn't see the parent skill's conversation.

## What this rule replaces

Previously, every implementing skill ended with a passive handoff and the human had to manually invoke the next checkpoint. That bounced ten mechanical decisions per feature back to the human. The rule above keeps the human in the loop for the decisions that matter (ambiguity, charter-required acceptance, low autonomy) and removes them from the ones that don't.

## References

- `engineer/scripts/dae_infra.py` — probe + auto-start + teardown of declared infra
