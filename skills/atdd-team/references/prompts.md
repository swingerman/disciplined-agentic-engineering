# ATDD Team — Prompt Templates

Per-phase agent spawn prompts for the team-based ATDD workflow. Each phase
spawns a **fresh agent** — no agent persists across phases. Adapt placeholders
(`[feature description]`, `[NNN-slug]`, `[project test command]`) to the
specific project.

---

## Per-phase agent spawn

Each phase spawns a fresh agent. Every spawn prompt begins with this **anchor
block**, which re-establishes the working contract so the agent never relies on
context that a compaction would erase:

```
You are the <role> for feature [NNN-slug], at autonomy <level>.
Phase <n> — <phase name>. This checkpoint's goal: <goal>.
Exit criteria you must satisfy: <list from Foundation Design Section 8>.
Prior phase handoff: features/[NNN-slug]/handoffs/<file> — read it first.
Non-negotiables: verification independence; the charter's mutation policy.
Constraints: <charter / autonomy limits>.
End your phase by writing a handoff summary to
features/[NNN-slug]/handoffs/ with the exit_criteria block.
```

The phase-specific instructions below follow the anchor block. A phase agent's
life ends when it writes its handoff — there is no standing team to shut down.

---

## Phase 1 — Spec Writing

Spawn a fresh **spec-writer**. After the anchor block:

```
We're implementing [feature description].

1. Read the existing codebase to understand the domain language
   (how does the app refer to users, orders, sessions, etc.?)
2. Write the feature's spec.md in standard Gherkin under features/[NNN-slug]/
3. Use ONLY external observables — no class names, no API endpoints,
   no database tables, no framework terms
4. Name each behavior with a Scenario: line; use Scenario Outline:
   + Examples: for behaviors with varying data
5. End by writing your handoff summary.

CRITICAL: If unsure whether a term is domain or implementation language,
ask the team lead. Do NOT guess.

Example of what I expect:

Feature: User Registration

Scenario: User can register with email and password
  Given no registered users
  When a user registers with email "bob@example.com" and password "secret123"
  Then there is 1 registered user
  And the user "bob@example.com" can log in
```

### Revision prompt (if specs need changes after review)

Spawn a fresh **spec-writer**. After the anchor block:

```
The reviewer found issues with features/[NNN-slug]/spec.md:
[paste reviewer's findings]

Revise the specs to fix these issues. Use domain language only; one
behavior per scenario; a non-developer should understand every step.
End by writing your handoff summary.
```

---

## Phase 2 — Spec Review

Spawn a fresh **reviewer**. After the anchor block:

```
Run the spec-guardian agent on features/[NNN-slug]/spec.md to audit for
implementation leakage. Flag ANY of:
- Class names, function names, method names
- Database tables, columns, queries
- API endpoints, HTTP methods, status codes
- Framework terms (controller, service, repository, middleware)
- Internal state, data structures, file paths

Also check: one behavior per scenario; clear to a non-developer;
portable to a different implementation language.

For each violation, show the bad line and propose a domain-language
rewrite. End by writing your handoff summary with a PASS/FAIL verdict.
```

---

## Phase 3 — Pipeline Generation

Spawn a fresh **implementer** (or run as team lead). After the anchor block:

```
Generate the project-specific test pipeline for features/[NNN-slug]/spec.md.

The parser (dae_gherkin.py) is portable and shipped — do NOT build it.
Invoke the pipeline-builder agent to generate the project-specific half:
1. Generator — reads .build/spec.json (the IR), produces runnable tests
2. Step handlers — bind each step's text to the system's internals
3. Runner — run-acceptance-tests.sh (parse -> generate -> run)

The generator must have DEEP knowledge of the codebase internals. This is
NOT Cucumber — generated tests call directly into the system.

Run the acceptance tests after generation. They MUST fail (red). Report
which fail. End by writing your handoff summary.
```

---

## Phase 4 — Implementation

Spawn a fresh **implementer**. After the anchor block:

```
The acceptance specs are in features/[NNN-slug]/spec.md and the pipeline
is set up — run ./run-acceptance-tests.sh to execute.

Implement the feature using TDD:
1. Run acceptance tests — confirm they FAIL
2. Pick the simplest failing acceptance test
3. Write a unit test for the smallest piece needed
4. Write minimal code to make the unit test pass
5. Refactor in-the-small
6. Repeat 3–5 until that acceptance test passes
7. Move to the next failing acceptance test
8. Continue until ALL acceptance AND unit tests pass

RULES:
- Never modify spec.md — it is the contract
- Never modify generated test files — only regenerate via the pipeline
- Take the code to GREEN only — deep refactoring is the refiner's phase (5).
  Do not pre-empt it.
- If a spec seems wrong or ambiguous, STOP and ask the team lead

End by writing your handoff summary — state explicitly what you did NOT
do (e.g. deep refactoring left for the refiner) and report both test
streams' results.
```

### Unblocking prompt (if the implementer reports a spec issue)

Team lead, after reviewing the issue:

```
I've reviewed your concern about the spec: "[spec line in question]"

[One of:]
A) The spec is correct. The implementation handles this case. Continue.
B) The spec needs revision — Phase 1 will re-run. Pause until new specs land.
C) The spec is ambiguous. It means: [clarification]. Continue with this.
```

---

## Phase 5 — Refine

Spawn a fresh **refiner**. After the anchor block:

```
Both test streams are green. Run the engineer plugin's `refine` skill on
the feature's changed code — the post-green improvement pass across three
lenses: reuse (duplication, dead code), quality (clarity, structure,
naming), efficiency (redundant computation).

Every proposal must pass the charter filter. Re-run both test streams
after applying — any failure reverts that proposal.

End by writing your handoff summary: what was improved, what was left,
and confirmation both streams are still green.
```

---

## Phase 6 — Verify & Harden

Spawn a fresh **architect**. Its `agent_id` MUST differ from the implementer's
and the refiner's. After the anchor block:

```
Independently verify and harden the feature:
1. Run /engineer.consistency-check — confirm the artifacts agree.
2. Run /crap-analyzer — CRAP + coverage on the changed code (Checkpoint 7).
3. Run mutation testing per the CHARTER's mutation policy (Checkpoint 8).
   This is charter-driven, NOT your discretion: if the charter mandates
   mutation for this feature, run it — its slowness is never a reason to
   skip it. Run /atdd:mutate, then /atdd:kill-mutants for real survivors,
   then re-run to confirm kills.

End by writing your handoff summary with the CRAP, coverage, and mutation
results measured against the charter's thresholds.
```

### If mutation score is low

```
The mutation score is [X]% — below the [N]% target. For each surviving
mutant, write a targeted unit test that exercises the exact code path, or
document it as an equivalent mutant. If a survivor reveals a real BUG in
source code, report it to the team lead — do not write a test for the
buggy behavior. Re-run mutations after each batch.
```

---

## Completion

When all six phases pass:

```
ATDD pipeline complete for [feature description].
- Specs: features/[NNN-slug]/spec.md (reviewed, no leakage)
- Acceptance + unit tests: ALL PASSING
- Refine: applied, charter-filtered
- Verify & Harden: CRAP / coverage / mutation within charter thresholds

Next: commit? start the next feature? stop?
```

Do not auto-commit — the team lead asks the user.

---

## Handling Edge Cases

### A phase agent disagrees with the prior handoff

The team lead arbitrates. Read the prior phase's handoff and the concern,
decide whether the artifact or the approach changes. Never let a downstream
agent silently modify an upstream artifact (spec, ACs).

### The pipeline can't handle a spec

The spec may need to be broken into smaller behaviors, or the generator
needs improvement. Fix the generator, NOT the spec — specs describe what,
generators figure out how to test it.

### The reviewer finds leakage after implementation

Expected. Route the finding to a fresh spec-writer for cleanup. The
implementer does not change code — leakage cleanup only affects spec wording.
