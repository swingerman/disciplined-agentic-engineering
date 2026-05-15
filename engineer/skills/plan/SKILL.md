---
name: plan
description: Use when a feature has acceptance criteria and Given/When/Then specs and needs an architecture plan before implementation. Triggers include "/engineer.plan", "plan this feature", "let's plan the implementation", "design the architecture for X", or naturally after atdd:atdd has produced spec.md. Produces plan.md (Checkpoint 4) — architecture, a structured Charter Check, phasing, performance budgets, collaboration schedule, execution modes, and test strategy. Mixed mode: the agent proposes the architecture and the human confirms it before the rest of the plan is drafted. Refuses to finish a plan that deviates from the charter without a corresponding amendment.
---

# plan

Produce the architecture plan for a feature — Checkpoint 4, the most consequential architectural checkpoint in the DAE pipeline. This is where engineering authority over **code design** and **performance** is exercised: the agent proposes, the human decides.

## When this skill runs

After `discover-acs` (Checkpoint 2) and `atdd:atdd` (Checkpoint 3) — the feature has `acs.md` and `spec.md`. Produces `plan.md`.

**Soft dependency on `spec.md`:** if `spec.md` is missing (user jumped from `discover-acs` straight to planning), warn:
> "No `spec.md` found — the plan should follow spec formalization. Proceed planning from `acs.md` alone, or run `/atdd:atdd` first?"
The user may override and plan from ACs directly, but the skill flags the skipped checkpoint in its handoff.

## Workflow

### Step 1 — Resolve and load

Walk up to `.engineer/manifest.yml`; resolve `methodology_root`; locate the feature. Load:
- `feature.md` — outcome, scope, autonomy_level, relevant_adrs
- `acs.md` — the acceptance criteria
- `spec.md` — Given/When/Then specs (soft-required; see above)
- `CHARTER.md` — architecture, conventions, quality stance, autonomy stance, ADRs
- `manifest.yml` — autonomy rules, quality thresholds, team default_roles, repos

### Step 2 — Propose the architecture (human confirms before proceeding)

Draft the **Architecture** section only and present it to the user for confirmation. This is the high-stakes human decision — do not draft the rest of the plan until architecture is confirmed.

The architecture proposal covers:
- Components — what's new, what's modified
- Data flow — how information moves through the feature
- Where new code lives — modules, files, directories
- How it couples to existing code — the integration surface
- Key design decisions with rationale (and alternatives considered)

Present it, then:
> "This is the proposed architecture. Confirm it, push back, or ask for alternatives before I draft the rest of the plan."

Iterate until the human confirms. If the architecture deviates from the charter, see Step 4 *before* asking for confirmation — surface the deviation honestly.

### Step 3 — Draft the rest of the plan

Once architecture is confirmed, draft the remaining sections. The human reviews the complete `plan.md` file at the end (no further mid-skill checkpoints).

### Step 4 — Charter Check (structured compliance report)

Validate the plan against `CHARTER.md`. Produce the two-part Charter Check (per the Foundation Design):

**Compliance table** — one row per charter rule, plus auto-included rows for autonomy stance, verification independence, mutation policy, and (when `autonomy_level: high`) performance budgets:

| Charter rule | Plan position | Compliance | Notes |
|---|---|---|---|
| ... | what the plan actually does | ✅ / ⚠️ deviation | ... |

**Charter amendments proposed** — for every ⚠️ deviation row, a corresponding amendment (an ADR with rationale, alternatives, consequences).

**Hard rule:** `plan` must NOT finish a plan that has a ⚠️ deviation without a matching amendment. Either:
- (a) produce the amendment ADR inline (in the Charter Check section), or
- (b) if the deviation needs a human decision the agent can't make, stop and emit a handoff with `human_action_needed: decision` describing the deviation

Never ship a silently-noncompliant plan.

### Step 5 — Write `plan.md`

```markdown
---
slug: <slug>
checkpoint: 4
plan_status: draft
created: <ISO date>
---

# Plan — <feature title>

## Architecture
<components, data flow, where new code lives, how it couples to existing code, key decisions + rationale + alternatives considered>

## Charter Check

### Compliance table
| Charter rule | Plan position | Compliance | Notes |
|---|---|---|---|
| <rule> | <what the plan does> | ✅ / ⚠️ deviation | <notes> |

### Charter amendments proposed
<ADR-N per deviation, with rationale / alternatives / consequences — or "None; plan is fully compliant.">

## Phasing
<vertical slices / stages, each a shippable increment. NOT a granular task list — tasks emerge from specs, one spec = one TDD cycle. Phasing defines stage boundaries and ordering.>

## Performance budgets
<required when autonomy_level is high — explicit, measurable targets the agent self-checks against (response time, throughput, complexity). Omit or mark "n/a" for low/medium autonomy unless the feature is performance-sensitive.>

## Collaboration schedule
<given the autonomy level, when the human engages and when the agent runs unattended. Maps checkpoints to human-contact moments. This is the feature's "designed schedule" — Principle 1.>

## Execution modes
<per stage: single agent / subagent / agent team / remote one-shot / routine — per the DAE execution model. Driven by: needs mid-stream human input? + how heavy is the work?>

## Test strategy
<which ACs/specs map to which acceptance tests; unit-test approach; the hardening (mutation) decision for this feature — required or skipped, per charter + autonomy level>
```

Write to `<methodology_root>/features/NNN-<slug>/plan.md`.

### Step 6 — Emit the handoff summary

```markdown
---
skill: plan
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: 4
artifacts:
  - features/NNN-<slug>/plan.md
findings_summary: <one line — e.g. "plan drafted; 1 charter deviation with amendment ADR-012">
human_action_needed: <yes | no — yes if any deviation needs a decision>
human_action_kind: <review | decision>
recommended_next: "Checkpoint 5 — invoke /atdd:atdd-team to implement against the specs"
tracker_update: <tracker_ref> — checkpoint_4: complete
status: complete
---

# plan — handoff summary

## What I did
Drafted the architecture plan for `<title>`. Architecture confirmed with the human in <N> iterations. Charter Check: <fully compliant | N deviations, all with amendments>.

## Artifacts produced
- `features/NNN-<slug>/plan.md`

## Findings
<key architectural decisions, notable tradeoffs, charter deviations + their amendments, execution-mode choices>

## Human action needed?
<For clean compliant plan: "Review plan.md; once approved, invoke /atdd:atdd-team to implement.">
<For a deviation needing a decision: "DECISION NEEDED — the plan deviates from the charter on <rule>. Amendment ADR-N is proposed; approve the amendment or revise the plan.">

## Recommended next step
Once plan.md approved → invoke /atdd:atdd-team for implementation (Checkpoint 5).

## Tracker update
Wrote: <tracker_ref> — checkpoint_4 marked complete.
```

## Key principles encoded

- **`plan.md` has phasing, not tasks.** Stages/slices define ordering and boundaries. Granular tasks emerge from specs (one Given/When/Then spec = one TDD cycle) and are driven by `atdd:atdd-team`, not enumerated here.
- **Architecture is the human's decision.** The agent proposes; the human confirms before anything else is drafted. This is Checkpoint 4's whole purpose.
- **The Charter Check is a compliance contract, not a checklist.** Deviations must surface as amendments. A noncompliant plan never ships silently.
- **Performance budgets are mandatory at high autonomy.** When the human won't see the implementation mid-stream, the plan must declare measurable performance targets the agent self-checks against.

## When NOT to use this skill

- No `acs.md` yet → run `/engineer.discover-acs` first
- You want Given/When/Then specs (not an architecture plan) → that's `/atdd:atdd`
- Small change to an existing plan → use `/engineer.feature-edit`

## Cross-skill orchestration

Upstream: `discover-acs` → `acs.md`; `atdd:atdd` → `spec.md`.
This skill: reads acs.md + spec.md + charter + feature.md; produces `plan.md` with the Charter Check.
Downstream: `atdd:atdd-team` consumes `plan.md` + `spec.md` for implementation (Checkpoint 5).

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — the structured Charter Check (Section 3), agentic summary contract
- The DAE methodology page — execution model, autonomy levels, collaboration schedule (Principle 1)
