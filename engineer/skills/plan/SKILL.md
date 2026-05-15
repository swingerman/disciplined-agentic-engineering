---
name: plan
description: Use when a feature has ACs and specs and needs an architecture plan before implementation. Triggers — "/engineer.plan", "plan this feature", "plan the implementation", "design the architecture".
---

# plan

Produce a feature's architecture plan — Checkpoint 4, the most consequential architectural checkpoint. Where engineering authority over **code design** and **performance** is exercised: the agent proposes, the human decides.

Mixed mode — the agent proposes the architecture, the human confirms it, then the rest of the plan is drafted.

## When to use

After `discover-acs` (Checkpoint 2) and `atdd:atdd` (Checkpoint 3). Produces `plan.md`.

If `spec.md` is missing, warn — planning should follow spec formalization — but the user may override and plan from `acs.md` alone (flag the skipped step in the handoff).

**Not for:** Given/When/Then specs (`atdd:atdd`); small changes to an existing plan (`feature-edit`).

## Workflow

1. **Resolve + load** — `feature.md`, `acs.md`, `spec.md`, `CHARTER.md`, `manifest.yml`.
2. **Propose the architecture** — draft only the Architecture section (components, data flow, where new code lives, coupling, key decisions + rationale + alternatives). Present it; iterate until the human confirms. Do not draft the rest until then.
3. **Draft the rest** — once confirmed, draft the remaining sections; the human reviews the finished file.
4. **Charter Check** — validate the plan against `CHARTER.md`. Produce the two-part structured check: a compliance table (one row per charter rule, plus auto-rows for autonomy stance, verification independence, mutation policy, and — at high autonomy — performance budgets), and an Amendments section. **Hard rule:** never finish a plan with a ⚠️ deviation that lacks a matching amendment ADR. Either write the amendment inline, or stop and emit a handoff with `human_action_needed: decision`.
5. **Write `plan.md`** — frontmatter (`slug`, `checkpoint: 4`, `plan_status`, `created`) + sections: Architecture, Charter Check, Phasing, Performance budgets, Collaboration schedule, Execution modes, Test strategy.
6. **Handoff** — emit a summary.

`plan.md` has **phasing (stages/slices), not a task list** — tasks emerge from specs (one spec = one TDD cycle), driven by `atdd:atdd-team`.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: 4`; `recommended_next`: "/atdd:atdd-team to implement against the specs". If a deviation needs a decision, `human_action_needed: yes` (decision).

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — the structured Charter Check (Section 3)
- The DAE methodology page — execution model, autonomy levels, collaboration schedule
