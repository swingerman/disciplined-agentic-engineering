---
name: simplify
description: Use after a feature's code is implemented and passing, when the changed code should be cleaned up before verification. Triggers include "/engineer.simplify", "simplify this code", "clean up the feature", "refactor what we just built", or naturally at Checkpoint 6 after atdd:atdd-team finishes implementation. Analyzes the feature branch's changed code, proposes refactors that remove incidental complexity, filters every proposal against the charter before showing it, and produces breaking changes as graceful deprecation paths when they cross a consumer boundary. Mixed mode: the agent proposes, the human picks which refactors are worth the churn.
---

# simplify

Charter-bound clean-up of a feature's changed code — Checkpoint 6 of the DAE pipeline. Modeled on Claude Code's stock `/simplify`, which dispatches a **three-subagent parallel review** (reuse / quality / efficiency lenses) over the changed code. DAE's version keeps that three-check procedure and adds two strict layers the stock skill lacks:

1. **Charter validation** — every proposal is checked against the project charter (and ADRs / other locked decisions) before the user sees it. This is the DAE skill's core strength.
2. **Graceful breaking changes** — consumer-facing breaks are produced as deprecation paths (shim + marker + migration note), not hard renames/removes.

This skill operates on code that *implements the binding behavior contract* (ACs + specs). Violating that contract via a refactor is a category error — so simplify preserves the contract and introduces any new shape alongside the old.

## When this skill runs

Checkpoint 6 (Implement phase), after `atdd:atdd-team` has produced working code that passes both test streams. Before Checkpoint 7 (Light Verify / CRAP).

### Verification independence

If `manifest.verification.apply_to_checkpoints` includes `6`, simplify is subject to Principle 7 — **it must run on a different agent than the implementer**. The agent that wrote the feature's code cannot refactor-review its own work. In that case:
- If invoked as the implementer agent → refuse; dispatch to a fresh subagent, a team `verifier` role, or a remote agent
- If invoked as a non-implementer agent → proceed

If `apply_to_checkpoints` does not include `6` (the default is `[7, 8]`), simplify may run on any agent.

## Workflow

### Step 1 — Resolve and scope

Walk up to `.engineer/manifest.yml`; resolve `methodology_root`; locate the feature (slug arg or branch name).

**Scope is the feature branch's changed code** — `git diff` against the branch point. Like `crap-analyzer`, simplify does not roam the whole repo; it cleans what this feature changed.

Load: `feature.md`, `acs.md`, `spec.md` (the behavior contract), `CHARTER.md` (architecture, conventions, methodology rules).

### Step 2 — Dispatch three parallel review subagents

Dispatch **three subagents in parallel** (see `superpowers:dispatching-parallel-agents`), each reviewing the same changed code through one lens:

- **Reuse subagent** — does the changed code duplicate logic that already exists? Could it call existing utilities/abstractions instead of reinventing them? Dead code, reinvented wheels, copy-paste that wants consolidation.
- **Quality subagent** — clarity, structure, naming, incidental complexity, maintainability. Overly long functions, awkward abstractions, leaky boundaries, naming that obscures intent, needless indirection, nested ternaries, inconsistency with surrounding patterns.
- **Efficiency subagent** — unnecessary work, redundant computation, obvious performance smells (repeated lookups, N+1 patterns, allocation in hot paths). Not deep profiling — visible waste.

Each subagent returns a list of findings, each finding a candidate refactor proposal with: location, what's wrong through that lens, proposed change.

The three subagents are inherently separate agents from the implementer — so this dispatch **satisfies verification independence by construction**, regardless of `apply_to_checkpoints` config.

### Step 3 — Consolidate findings

Merge the three subagents' findings into one proposal list:
- **Deduplicate** — if two lenses flag the same location, merge into one proposal noting both lenses (a strong signal).
- **Resolve conflicts** — if reuse and efficiency disagree (e.g., reuse says "call the shared helper", efficiency says "the shared helper is slow here"), keep both as alternatives for the human to choose between; don't silently pick one.
- Each consolidated entry is a candidate refactor proposal carried into Step 4.

### Step 4 — Charter filter (internal — before anything is shown)

For **every** candidate proposal, check it against `CHARTER.md`:
- Does it respect the architecture (topology, layering, data-store decisions)?
- Does it follow the conventions (code style, naming, test layout)?
- Does it honor the methodology declarations?
- Does it preserve the ACs + specs contract?

**Proposals that would violate the charter are rejected internally — never shown to the user.** The user only ever sees charter-compliant proposals. This filter is non-negotiable: a refactor that improves clarity but breaks an architectural rule is not an improvement.

If a charter rule itself seems to be the obstacle to a genuinely better design, that is not a simplify decision — surface it as a note in the handoff recommending `/engineer.feature-edit` or a charter amendment. simplify does not amend the charter.

### Step 5 — Classify breaking changes

For each surviving proposal that changes a name, signature, or location, determine its blast radius:

- **Consumer-facing** — something outside this change's blast radius depends on the old shape (a module's public API, the feature's contract surface, another feature's code). → Produce a **graceful path**: keep the old shape as a deprecation-marked forwarding shim to the new shape, add migration notes. New shape alongside old.
- **Internal-only** — the old shape has no consumer beyond this change (private function, single caller within the diff). → A hard change is fine; no consumer to protect, no ceremony needed.

The graceful-path mechanics are language-specific (Python `DeprecationWarning`, JS re-pointed exports, Java `@Deprecated`, etc.) — the skill picks the idiom for the project's language.

### Step 6 — Present proposals; human picks

Show the charter-compliant proposals as a list. For each: what it changes, why it's cleaner, blast radius (internal / consumer-facing + graceful-path note), rough churn size.

> "Here are <N> charter-compliant refactor proposals for the changed code. Which are worth the churn?"

The human selects. The agent applies **only** the selected proposals. Checkpoint 6's human decision is exactly this: which refactors are worth it.

### Step 7 — Apply selected refactors

For each selected proposal:
- Apply the refactor
- For consumer-facing breaking changes, install the graceful path (shim + deprecation marker + migration note)
- Re-run both test streams (acceptance + unit) — the contract must still hold; if any test fails, the refactor broke the contract → revert that proposal and report it

### Step 8 — Emit the handoff summary

```markdown
---
skill: simplify
agent_id: <main | subagent-N | team-verifier — must differ from implementer if checkpoint 6 is independence-gated>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: 6
artifacts:
  - <changed source files>
findings_summary: <one line — e.g. "12 proposals, 9 charter-compliant, 5 applied, 1 graceful path">
human_action_needed: no
human_action_kind: none
recommended_next: "Checkpoint 7 — invoke crap-analyzer for Light Verify"
tracker_update: <tracker_ref> — checkpoint_6: complete
status: complete
---

# simplify — handoff summary

## What I did
Reviewed the changed code for `<title>` via three parallel subagents (reuse / quality / efficiency). Consolidated to <N> candidate refactors; <M> passed the charter filter; the human selected <K> to apply. <note any graceful deprecation paths installed>. Both test streams re-run and green after refactoring.

## Artifacts produced
- <list of changed source files>

## Findings
<notable refactors applied; charter-rejected proposals worth noting; any proposal reverted because it broke a test; any charter rule that blocked a genuinely better design — recommend feature-edit / charter amendment if so>

## Human action needed?
No — selected refactors applied, contract preserved (both test streams green).

## Recommended next step
Invoke crap-analyzer for Light Verify (Checkpoint 7).

## Tracker update
Wrote: <tracker_ref> — checkpoint_6 marked complete.
```

## Relationship to crap-analyzer

Both skills can suggest refactoring the same function — that's fine, not a conflict:
- **`simplify`** (Checkpoint 6, Implement) — lens is *clarity / incidental complexity*; runs to keep code clean as you go
- **`crap-analyzer`** (Checkpoint 7, Light Verify) — lens is *risk* (complexity × untested-ness); runs to find where bugs hide

Distinct timing, distinct lens. Two lenses converging on the same function is a strong signal, not a duplicate.

## Key principles encoded

- **Three lenses, run in parallel.** Reuse, quality, and efficiency are different review modes — dispatching a dedicated subagent per lens catches more than one agent scanning for "anything wrong." The three subagents also satisfy verification independence by construction.
- **Charter validation is the DAE strength.** The stock `/simplify` does the three checks but knows nothing about the project's charter, ADRs, or locked decisions. DAE's version filters every proposal against them — this is what the stock skill lacks.
- **The behavior contract is sacred.** ACs + specs define what the code must do; a refactor that breaks the contract is a category error. Both test streams must be green after every applied refactor.
- **The charter filter runs before the human sees anything.** Charter-violating proposals are never surfaced — they are not "improvements."
- **Breaking changes are graceful when they have consumers.** Deprecation path + shim + migration notes for consumer-facing breaks; hard changes only when nothing depends on the old shape.
- **The human decides which refactors are worth the churn.** simplify proposes; it does not unilaterally rewrite.

## When NOT to use this skill

- Code isn't implemented / tests aren't green yet → finish Checkpoint 5 first
- You want risk analysis, not clean-up → that's `crap-analyzer` (Checkpoint 7)
- You want to change the feature's behavior → that's `feature-edit`, not a refactor
- The charter itself is blocking a better design → surface it; use `feature-edit` or a charter amendment

## References

Skill patterns:
- `superpowers:dispatching-parallel-agents` — the parallel-subagent dispatch pattern used in Step 2

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — charter format, agentic summary contract, verification independence
- The DAE methodology page — Checkpoint 6, Principle 7 (verification independence), the clean-code gap description
