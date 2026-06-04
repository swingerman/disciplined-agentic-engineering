---
name: next
description: Use at the start of a work session, or any time the question is "what should I pick up now" across the whole project. Triggers — "/engineer.next", "what's next", "what should I work on", "what should I do next", "where do I pick up".
---

# next

The session-start skill — the human's re-entry point. Surveys every source of DAE state and answers one question: **what should I pick up now?**

Read-only and advisory. It changes nothing, produces no artifact, and emits **no handoff** (the recommendation is the whole output; a handoff would just restate it). This is a deliberate exception to the agentic-summary contract — `next` is a query, not a task that changes state.

`next` is the read-side bookend to `session-summary`: `session-summary` writes "here's where I left off, next tasks" at session end; `next` consumes that — and everything else — at session start.

## When to use

Start of a session, or any "what now?" moment. Project-scope; surveys the whole project — there is no narrower scope.

**Not for:** loading context on a feature you've already chosen (`prime-context`); checking artifact consistency (`consistency-check`); a per-feature next-step (each skill's handoff already carries `recommended_next`).

## Workflow

### Step 1 — Resolve and survey

Resolve the methodology root + manifest via `${CLAUDE_PLUGIN_ROOT}/scripts/dae_resolve.py` (see `references/resolving.md`). Then read, read-only:

- **In-flight features** — every `features/*/feature.md` (status) + `progress.md` (current checkpoint; whether it's blocked or ready to advance)
- **Consolidation backlog** — `.engineer/consolidation.md` if present (coverage backlog + triage order)
- **Parked ideas** — `features/*/` with `status: parked`; `.engineer/discussions.log`
- **Pending human actions** — recent `handoffs/*.md` (per-feature and `.engineer/handoffs/`) flagged `human_action_needed: yes`
- **Session-log next-tasks** — the latest `session-log.md` entry per active feature ("Next tasks")
- **CHARTER.md + manifest** — autonomy levels and path overrides, for execution-mode advice
- **Open fixes** — `.engineer/fixes/*.md` via `${CLAUDE_PLUGIN_ROOT}/scripts/dae_fix.py list_open_fixes` (status != closed)
- **Stale merged branch** — if the current branch is not `main`/`master`, run `git fetch origin --quiet` then check `git merge-base --is-ancestor HEAD origin/HEAD` (fallback `origin/main`). If true, the branch is merged and lingering — surface it as a STALE BRANCH item.

### Step 1.5 — Offer branch cleanup (if stale)

If a stale merged branch was detected, defer to the `post-merge` skill — it owns the full cleanup flow (checkout, pull, branch -d, prune, tracker update). At autonomy `high`/`medium`, auto-invoke `/engineer.post-merge` before continuing to Step 2. At `low`, surface the finding and stop until the user invokes it themselves. Do not inline the cleanup commands here — keep `next` advisory and let the dedicated skill do the work, so the post-merge handoff lands in the audit trail.

### Step 2 — Triage into five buckets

```
NEEDS YOUR DECISION   — blocked features; handoffs flagged human_action_needed.
                        These stall progress — surface them first.
OPEN FIXES            — bug-fix artifacts not yet closed. Sub-priority within the bucket:
                         1. blocks_user: true AND workaround: none      ← top (user is hit right now)
                         2. blocks_user: true AND workaround: <text>    ← middle (user has a workaround)
                         3. blocks_user: false                          ← bottom
                         Within each tier, order by severity (critical, high, medium, low).
READY TO ADVANCE      — in-flight features sitting at a checkpoint that can proceed.
READY TO DISPATCH     — features / consolidation tasks that can go to a remote agent
                        right now (bounded, automatable verification, no mid-stream
                        human input needed).
COULD START           — the next consolidation-backlog item; parked ideas worth
                        promoting; fresh work.
```

### Step 3 — Rank and recommend

Priority order:
1. **Unblocking first** — a blocked feature or a pending human-action stalls everything downstream; clearing it usually beats starting something new.
1b. **User-blocking defects** — an OPEN FIX with `blocks_user: true` and no workaround ranks above starting fresh feature work; a real defect hitting users now is more urgent than forward progress on new scope.
2. **Triage priority / dates** — consolidation-backlog order, feature `target` dates.
3. **Dispatchability** — if the human has limited time, favour surfacing what can be *dispatched* (freeing the human) over what *needs* them.

Present the five buckets, then **one top recommendation** — the single best next action — with a one-line rationale and a suggested execution mode (you, local subagent, agent team, or remote).

### Step 4 — Stop

`next` recommends; it does **not** act. The human picks, then invokes the relevant skill themselves (`prime-context`, `discuss`, `feature-init`, a consolidation task, …). No handoff is emitted.

## Example shape

```
NEEDS YOUR DECISION (1)
  • 042-customer-export — plan.md has a charter deviation; approve amendment ADR-012 or revise

OPEN FIXES (2)
  • 2026-05-20-login-crash [critical] blocks_user=true workaround=none — login fails on iOS 17
  • 2026-05-18-export-timeout [high] blocks_user=true workaround="retry after 30 s"

READY TO ADVANCE (1)
  • 015-image-formats — at Checkpoint 2; ACs done, ready for /atdd:atdd

READY TO DISPATCH (2)
  • consolidation #1 core-image-generation — full ATDD coverage; remote one-shot
  • consolidation #3 mcp-connector — remote one-shot

COULD START (1)
  • parked: bulk-admin-export — discussed 3 weeks ago; promote if priorities allow

→ TOP PICK: fix 2026-05-20-login-crash. Users are hitting a critical crash on iOS 17
  with no workaround — this outranks new feature work. Run /fix to continue the
  fix workflow. Then approve 042-customer-export's plan to unblock its pipeline.
```

## When NOT to use this skill

- You already know the feature and just need to start → `prime-context`
- You want full project state validated, not a recommendation → `consistency-check --project`
- You want to wrap up a session → `session-summary`

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md / progress.md / agentic summary schemas
- The DAE methodology page — the three-layer visibility model; the parallelism model (one human driving several pipelines)
- Sister skill: `session-summary` — the session-end bookend.
- Sister skill: `fix` — produces the OPEN FIXES artifacts surfaced here.
