# Context-Resilient Discipline — Design (Spec A)

**Date:** 2026-05-18
**Status:** Draft for review
**Scope:** Make DAE's pipeline discipline survive context compaction and long agent
runs. Adds a per-checkpoint exit contract as the backbone, hardens the handoff
contract into a real gate, adds a mid-task re-anchoring skill, and restructures
`atdd-team` away from long-lived agents.

---

## Background

Uncle Bob ran a multi-agent swarm for a full day, deliberately letting agents
compact their contexts repeatedly. Observed failure modes:

- **Identity erosion** — agents lost their roles (the coder did the refactorer's
  job; the refactorer found nothing to do).
- **Invented false constraints** — an agent decided messaging other agents needed
  human permission (it did not).
- **Skipped expensive steps** — the architect decided not to run mutation tests
  "because they take a long time."
- **Dropped handoffs** — the coder forgot to hand off until reminded.
- **Stalls** — agents lost track of what they were doing; recovered by being asked
  "what should you be doing right now?"

Every one of these is the same root failure: **a stage gets considered "done"
without its goal verifiably met, and the discipline contract does not survive a
context boundary.** DAE's per-skill fresh-invocation model is a partial structural
defense (each skill reloads its `SKILL.md`), but long-lived agents — especially in
`atdd-team` — have no such protection, and no stage today has a uniform,
verifiable definition of done.

## Decomposition

The original review produced five learnings. They split along one seam:

- **Spec A (this document)** — context-resilient discipline + `atdd-team`
  hardening. Shared machinery: checkpoints, handoffs, `progress.md`, charter.
- **Spec B (separate cycle)** — test impact analysis: a changed-files →
  affected-scenarios mapper plus pipeline/runner wiring. No overlap with the
  discipline machinery.

Spec B is out of scope here.

---

## Component 1 — Checkpoint Exit Contract (the backbone)

### Problem

The Foundation Design doc locks the 8 checkpoints and their artifacts, and
`feature.md` is explicitly "the Ready contract (Checkpoint 1.5)" — a structured,
schema-validated definition of done for *that one stage*. No other checkpoint has
an equivalent. The `progress.md` Checkpoints table records *that* a stage was
verified ("Verified by / Verified at" columns) but never defines *what* "done"
means for it. The handoff's `status: complete` means the skill finished — not that
the goal was met.

### Design

A new locked section in the Foundation Design doc: the **Checkpoint Exit
Contract**. Every checkpoint gets three things:

- **Goal** — one line, the observable outcome of the stage.
- **Exit criteria** — a short list of verifiable conditions, each objectively
  checkable (a file conforms to a schema, a test stream is green, a metric clears
  a threshold, a human approved).
- **Verifier** — `self` or `independent`. `independent` follows Principle 7 and
  the manifest's `verification.apply_to_checkpoints`.

`feature.md` (Checkpoint 1.5) is recognized as the existing instance of this
pattern — the contract generalizes it rather than replacing it.

### The checkpoints

| CP | Goal | Exit criteria | Verifier |
|----|------|---------------|----------|
| 0 Onboard | Project mapped onto DAE | `CHARTER.md` + `manifest.yml` exist and validate; `consolidation.md` produced for existing projects; charter sign-off + tracking decision made by human | human |
| 1.5 Ready | Feature is startable | `feature.md` conforms to Foundation §4 schema; mandatory sections present; slug matches folder; `autonomy_level` within charter caps; human approved | human |
| 2 ACs | Acceptance criteria captured | `acs.md` exists; every AC is externally observable (no implementation leakage); every AC traces to the `feature.md` outcome/scope; human approved | human |
| 3 Spec | Behavior specified | `spec.md` exists in Gherkin; `dae_gherkin.py` parses it to a valid IR; every AC maps to ≥1 scenario; spec-check passes | independent (if manifest lists 3) |
| 4 Plan | Approach agreed | `plan.md` exists; Charter Check table complete; every ⚠️ deviation has a matching amendment; human approved | human |
| 5 Implement | Behavior built | both test streams green; acceptance tests cover all spec scenarios; the IR mutator confirms acceptance tests are wired to the app; PR exists | self |
| 6 Refine | Changed code improved | `refine` ran; both test streams still green; charter filter applied to every proposal | independent (if manifest lists 6) |
| 7 Light Verify | Change risk checked | CRAP ≤ `crap_max`; coverage ≥ `coverage_min` | independent |
| 8 Hardening | Test suite hardened | mutation score ≥ `mutation_score_min`, at the charter's scope and cadence | independent |

The exact criteria are a working draft; the implementation plan finalizes them
against each owning skill. The *contract* — that every checkpoint has a goal,
verifiable criteria, and a named verifier — is what this component locks.

### The `exit_criteria` handoff block

The agentic summary schema (Foundation §5) gains one block. Every
checkpoint-advancing skill's handoff asserts each criterion's status with
evidence:

```yaml
exit_criteria:
  - criterion: "every AC traces to the feature.md outcome/scope"
    met: true
    evidence: "8/8 ACs cross-referenced; see acs.md trace column"
  - criterion: "human approved"
    met: false
    evidence: "awaiting review — handoff flagged human_action_needed"
```

A checkpoint is marked done in `progress.md` only when its handoff asserts every
criterion `met: true`. A handoff with any `met: false` leaves the checkpoint
`in progress` (or `blocked` if the unmet criterion needs a human).

### Data flow

`skill emits handoff (with exit_criteria block)` → `progress-log reads it` →
`progress.md Checkpoints row marked done only if all criteria met` →
`CURRENT header recomputed`.

---

## Component 2 — Handoff-as-gate

### Problem

The handoff contract says every skill emits a summary, but nothing checks it. A
skipped handoff is silent (Bob: "the coder simply forgets to hand off").

### Design

The handoff becomes a real gate, enforced at two points and built on Component 1:

1. **Entry gate (blocking).** Before a checkpoint-advancing skill begins
   checkpoint N+1, it verifies checkpoint N emitted a handoff *and* that the
   handoff asserts all of checkpoint N's exit criteria `met: true`. A new
   stdlib helper — `engineer/scripts/dae_handoff.py` — takes a feature folder and
   reports: the latest checkpoint with a complete handoff, and any checkpoint
   `progress.md` claims done whose handoff is missing or has unmet criteria. On a
   mismatch the skill **stops and surfaces to the human** — it does not auto-fix
   or silently proceed.
2. **Sweep (after-the-fact).** `consistency-check` flags any checkpoint marked
   done in `progress.md` without a matching complete handoff. `reorient`
   (Component 3) reports the same as a discipline gap.

### Contract wording

`engineer/references/handoff-summary.md` gets the rule explicit: *"A checkpoint is
not complete until its handoff exists and asserts every exit criterion met. The
next checkpoint must not begin until the prior handoff is complete."* Each
checkpoint-advancing skill gains the entry gate as an explicit first workflow
step.

### Error handling

`dae_handoff.py` is read-only and never mutates state. A missing or malformed
handoff is reported, not repaired. An `interrupted`-status handoff counts as
*not complete* — the gate treats it like a missing handoff and surfaces it.

---

## Component 3 — the `reorient` skill

### Problem

After compaction an agent loses role identity, invents false constraints, skips
required steps, and loses the task thread. Bob's cheap fix was asking "what should
you be doing right now?" — DAE needs a structured version.

### Design

A new engineer-plugin skill, `reorient`. Read-only, produces no artifact, emits
**no handoff** — the same justified exception as `next` (it is a query, not a
state change). Feature-scoped and mid-task; it is the sibling of `next` (which is
project-scoped and session-start).

It reloads, discipline contract first, task pointer second:

1. **Role + autonomy** — from `CHARTER.md` + manifest: autonomy level, what the
   agent may and may not decide. Counters invented false constraints.
2. **Current checkpoint + its exit criteria + which are satisfied** — from the
   Checkpoint Exit Contract and `progress.md`. Counters skipped steps and goal
   ambiguity.
3. **Non-negotiable checkpoints** — verification independence, charter-mandated
   mutation. Counters "the architect decided not to run mutation tests."
4. **Current task + next action** — from the `progress.md` CURRENT header.
5. **Feature contract** — `feature.md` outcome + scope. Counters goal drift.

**Output:** a tight orientation block —
`You are <role> at autonomy <level>. Feature NNN-slug, Checkpoint N (<goal>).
Exit criteria: <m/n met> — unmet: <list>. Current task: X → next action: Y.
Must not skip: <non-negotiables>. Constraints: <...>.`

**Trigger:** manual `/engineer.reorient`, or an optional plugin `SessionStart`
hook (`source: compact`) that auto-invokes it — the same pattern as
`session-summary`'s optional Stop hook. The hook ships as example project config,
not as mandatory machinery.

---

## Component 4 — the `progress.md` CURRENT header

### Problem

`progress.md` has a "Current stage" line, but re-orientation should be a single
glance, not a parse of the whole file.

### Design

`progress.md` carries a fixed, parseable one-line header, exit-criteria-aware:

```
▶ CP5 Implement — 3/4 criteria met | NEXT: wire IR-mutator check | BLOCKED: none
```

`progress-log` owns keeping it current — a small change to its existing
"recompute the Current stage header" step. `reorient`, a fresh `atdd-team`
phase-agent, and a human all read this one line.

---

## Component 5 — `atdd-team` rewrite

### Problem

`atdd-team` keeps three teammates (spec-writer, implementer, reviewer) alive
across all six phases — a multi-hour lifespan. It *is* Bob's swarm, and it
inherits every erosion failure mode. It also compresses four natural roles into
three: the `reviewer` does triple duty, and code improvement has no owner.

### Design

1. **Fresh agent per phase.** Each phase spawns a fresh agent invocation scoped to
   that phase, then ends. No agent persists across phases → no cross-phase
   identity bleed. This is the same insight as the engineer plugin's per-skill
   model: fresh context = `SKILL.md` reloads = discipline restored.
2. **Durable handoffs between phases.** Phase transitions become handoff artifacts
   (`handoffs/*.md`, the engineer contract with the Component 1 `exit_criteria`
   block), not chat messages. The next phase's fresh agent reads the prior handoff
   for context — this survives compaction.
3. **`agent_id` binding.** Each phase handoff records `agent_id`. The `architect`'s
   `agent_id` must differ from both the `implementer`'s and the `refiner`'s — the
   verifier verifies neither its own coding nor its own refinement (Principle 7).
   The team lead verifies the binding.
4. **Five roles** (each a fresh per-phase agent type):

   | Role | Maps to | Owns |
   |------|---------|------|
   | `spec-writer` | discuss, discover-acs, atdd spec step | Phase 1 |
   | `reviewer` | spec-guardian agent | Phase 2 |
   | `implementer` | atdd impl, pipeline-builder | Phases 3–4 |
   | `refiner` | the `refine` skill | Phase 5 |
   | `architect` | consistency-check, crap-analyzer, atdd-mutate | Phase 6 |

5. **Six phases**, each gate **is** the relevant checkpoint's exit criteria
   (Component 1), not one-line prose:

   1. Spec Writing — `spec-writer`
   2. Spec Review — `reviewer`
   3. Pipeline Generation — `implementer`
   4. Implementation — `implementer`
   5. **Refine (new)** — `refiner`: the post-green code-improvement pass that
      previously had no owner.
   6. **Verify & Harden** (was "Optional Mutation") — `architect`: CRAP, coverage,
      mutation, acceptance mutation. **Charter-driven**, not optional by agent
      discretion — the charter's mutation policy decides whether and how it runs.

6. **Role-boundary rule.** More roles means more role-bleed surface (Bob's
   "refactorer has nothing to do because the coder did it"). Counter-measures: the
   `implementer` gets the code to green only — it does *not* do deep refactoring
   (that is the `refiner`'s phase); every phase handoff explicitly states *what
   was NOT done and what is left for the next role*; each phase-agent's spawn
   prompt embeds a `reorient`-style anchor.

The team still exists for **parallelism** — multiple feature pipelines can run
concurrently. Only the long-lived-agent property is dropped.

### Out of scope

Deeper convergence — `atdd-team` delegating directly to engineer-plugin skills per
phase — is explicitly deferred. This rewrite keeps `atdd-team`'s phase structure
and changes only the agent lifecycle, handoff durability, roles, and gates.

---

## Component 6 — rename `simplify` → `refine`

The `simplify` skill runs three lenses (Reuse, Quality, **Efficiency**) and calls
itself a "clean-up" — the name `simplify` undersells the reuse and efficiency
work. `refactor` is rejected: it collides with TDD's inline red-green-**refactor**
micro-step, and that naming collision mirrors the exact role collision Bob hit.

Rename to `refine`:

- engineer-plugin skill directory `simplify/` → `refine/`
- `SKILL.md` frontmatter `name: simplify` → `name: refine`
- the `/engineer.simplify` trigger → `/engineer.refine`
- cross-references in other skills and references
- the Foundation `progress.md` Checkpoint 6 label "Refactor" → "Refine"
- the Notion mention of `simplify`

The `atdd-team` role is `refiner` (Component 5).

---

## Component 7 — Notion foundation updates

- **Foundation Design — new section: Checkpoint Exit Contract.** The goal /
  exit-criteria / verifier model and the checkpoint table from Component 1.
- **Foundation Design §5** — add the `exit_criteria` handoff block; add
  handoff-as-gate to the agentic summary contract; document the `progress.md`
  CURRENT header and the `reorient` skill's no-handoff exemption (joining
  `progress-log` and `next`).
- **Foundation Design §6 / progress.md** — Checkpoint 6 label "Refactor" →
  "Refine".
- **DAE methodology page — new principle: "Context Resilience."** Compaction
  silently erodes role identity and discipline; prefer fresh, checkpoint-scoped
  invocations over long-running agents; re-anchor on compaction.

The implementation plan sequences these Notion changes **first**, so the
foundations do not go stale while the plugin is edited against them.

---

## Component 8 — testing

Per the writing-skills discipline (RED-GREEN-REFACTOR with subagents):

- **`reorient`** — pressure scenarios with a subagent whose context is
  artificially "compacted" (key facts withheld): does it re-anchor, resume the
  correct task, and refuse to skip non-negotiables? Baseline first (no skill),
  then with the skill, then close rationalization loopholes.
- **handoff-as-gate** — pressure scenarios where a subagent is tempted to advance
  past a missing or incomplete handoff: does the entry gate stop it?
- **`dae_handoff.py`** — stdlib `unittest` suite alongside the other
  `engineer/scripts/` scripts (missing handoff, interrupted handoff, unmet
  criteria, checkpoint-claim mismatch, clean pass).
- **`atdd-team` rewrite** — verify a fresh per-phase agent reads the prior phase's
  durable handoff correctly, and that the `agent_id` independence binding is
  enforced.

---

## Implementation sequencing

1. **Notion first** — lock the Checkpoint Exit Contract, the §5 handoff-schema
   changes, and the Context Resilience principle. Nothing downstream is built
   against an unlocked contract.
2. **`dae_handoff.py`** + its tests — the gate helper.
3. **Handoff contract + exit-criteria** wiring into `engineer/references/` and
   each checkpoint-advancing skill.
4. **`reorient`** skill + its tests + the example `SessionStart` hook.
5. **`progress.md` CURRENT header** — `progress-log` change.
6. **Rename `simplify` → `refine`.**
7. **`atdd-team` rewrite** + `prompts.md` update.
8. **`consistency-check`** sweep for missing/incomplete handoffs.

## Open items

- **`reviewer` as a separate 5th role.** Defaulted to separate (pre-code spec
  review and post-code verification need different framing). Could fold to four
  roles; flagged for the reviewer's call.
- **Exact exit criteria per checkpoint.** The Component 1 table is a working
  draft; the implementation plan finalizes each criterion against its owning
  skill.

## Out of scope

- **Spec B — test impact analysis.** Separate brainstorm + spec cycle.
- **Deeper `atdd-team` ↔ engineer-plugin convergence** — `atdd-team` delegating to
  engineer skills per phase.
