---
name: simplify
description: Use after a feature's code is implemented and passing, to clean up the changed code before verification. Triggers — "/engineer.simplify", "simplify this code", "clean up the feature", "refactor what we built".
---

# simplify

Charter-bound clean-up of a feature's changed code — Checkpoint 6. Modeled on Claude Code's stock `/simplify` (a three-subagent parallel review) with two layers the stock skill lacks: **charter validation** of every proposal, and **graceful breaking changes**.

The behavior contract (ACs + specs) is sacred — a refactor that breaks it is a category error. New shapes are introduced alongside old, never instead of.

## When to use

Checkpoint 6, after `atdd:atdd-team` produces passing code, before `crap-analyzer` (Checkpoint 7).

**Verification independence:** if `manifest.verification.apply_to_checkpoints` includes `6`, simplify must run on a non-implementer agent. The three review subagents (Step 2) are fresh regardless, so independence is satisfied by construction.

**Not for:** changing behavior (`feature-edit`); risk analysis (`crap-analyzer`); code that isn't implemented/green yet.

## Workflow

1. **Resolve + scope** — find `.engineer/manifest.yml`; locate the feature. Scope = the feature branch's changed code (`git diff` against the branch point). Load `feature.md`, `acs.md`, `spec.md`, `CHARTER.md`.
2. **Dispatch three parallel review subagents** (`superpowers:dispatching-parallel-agents`), each over the same changed code:
   - **Reuse** — duplication, reinvented wheels, dead code, missed existing utilities
   - **Quality** — clarity, structure, naming, incidental complexity, maintainability
   - **Efficiency** — redundant computation, repeated lookups, visible performance smells
3. **Consolidate** — merge findings; dedup overlaps (note multi-lens hits as strong signals); keep genuine conflicts as alternatives for the human.
4. **Charter filter** — check every proposal against `CHARTER.md` (architecture, conventions, methodology, the ACs+specs contract). Charter-violating proposals are **rejected internally — never shown**. This filter is the DAE-specific layer the stock skill lacks.
5. **Classify breaking changes** — consumer-facing (something outside the blast radius depends on the old shape) → graceful path: deprecation-marked forwarding shim + migration note, new shape alongside old. Internal-only → hard change is fine.
6. **Present; human picks** — show charter-compliant proposals (change, why, blast radius, churn). The human selects which are worth the churn.
7. **Apply** — apply selected; install graceful paths where needed; re-run both test streams. Any failure → revert that proposal and report.
8. **Handoff** — emit a summary.

If a charter rule itself blocks a genuinely better design, surface it in the handoff (→ `feature-edit` / charter amendment). simplify does not amend the charter.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `agent_id` must differ from the implementer if checkpoint 6 is independence-gated. `checkpoint: 6`; `recommended_next`: "crap-analyzer for Light Verify".

## References

- `superpowers:dispatching-parallel-agents` — the Step 2 dispatch pattern
- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — charter format, verification independence
