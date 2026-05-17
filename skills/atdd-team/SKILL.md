---
name: atdd-team
description: >-
  This skill should be used when the user asks to "build a feature with a team",
  "use ATDD with agents", "create an ATDD team", "set up a team for ATDD",
  "orchestrate agents for ATDD", "use team-based development", "coordinate
  agents for feature development", "run the ATDD workflow with teammates",
  "add ATDD to my team", "extend my team with ATDD", "join the team with
  ATDD agents", "add spec-writer and reviewer to the team", or "add ATDD
  roles to the existing team". It orchestrates a three-agent team
  (spec-writer, implementer, reviewer) through a five-phase ATDD workflow:
  spec writing, spec review, pipeline generation, implementation, and
  post-implementation review. Supports extending an existing team with
  ATDD roles without replacing current teammates.
version: 0.5.0
---

# Team-Based ATDD Workflow

Orchestrate an agent team that follows the Acceptance Test Driven Development
workflow. The team lead coordinates specialist agents through five phases:
spec writing, spec review, pipeline generation, implementation, and
post-implementation review.

## Team Detection

Before creating a team, check for existing teams:

1. Read `~/.claude/teams/` to list active teams
2. If a team exists, present the user with a choice:
   - **Extend** — Add ATDD roles (spec-writer, implementer, reviewer) to the
     existing team. Skip roles that already exist by name.
   - **Replace** — Shut down the existing team and create a fresh ATDD team.
   - **New team** — Create a separate ATDD team alongside the existing one.

If no team exists, proceed directly to team creation.

## Roles

Create three teammates with these roles:

| Name | Agent Type | Purpose |
|------|-----------|---------|
| `spec-writer` | `general-purpose` | Writes Given/When/Then acceptance specs in domain language. Follows the atdd skill strictly. |
| `implementer` | `general-purpose` | Implements features using TDD. Unit tests first, then code, until both test streams pass. |
| `reviewer` | `general-purpose` | Reviews specs for implementation leakage. Reviews code for quality. Has the atdd plugin installed. Runs /atdd:spec-check. |

The **team lead** (the orchestrating agent or user) owns the workflow, reviews
specs, approves all work, and enforces discipline. The team lead never delegates
approval — specs are the team lead's contract.

## Workflow Phases

Execute phases strictly in order. Each phase has a gate that must pass before
proceeding to the next phase.

### Phase 1 — Spec Writing

**Assign to:** `spec-writer`

Send the feature description and instruct the spec-writer to:

1. Read the existing codebase to understand domain language
2. Write the feature's `spec.md` in standard Gherkin
3. Use ONLY external observables — no implementation language
4. Follow the standard Gherkin format from the atdd skill
5. Send specs back for review before proceeding

**Gate:** Team lead reviews and approves specs. Do not proceed until approved.

For the detailed prompt template, see `references/prompts.md` — Phase 1.

### Phase 2 — Spec Review

**Assign to:** `reviewer`

Instruct the reviewer to audit specs for implementation leakage:

- Class names, function names, method names
- Database tables, columns, queries
- API endpoints, HTTP methods, status codes
- Framework terms (controller, service, repository)
- Internal state or data structures

Also verify: one behavior per spec, clarity for non-developers,
language portability.

**Gate:** Reviewer sends findings. Team lead decides whether specs need
revision. If revisions needed, return to Phase 1.

For the detailed prompt template, see `references/prompts.md` — Phase 2.

### Phase 3 — Pipeline Generation

**Assign to:** Team lead (self) or `implementer`

Generate or update the 3-stage test pipeline:

1. Parser — `dae_gherkin.py` parses `spec.md` → IR (portable, shipped)
2. Generator — reads the IR, produces runnable tests
3. Runner — `run-acceptance-tests.sh`

Run acceptance tests after generation. They **must fail** (red). If they pass,
either the behavior exists or the generator is wrong.

**Gate:** Acceptance tests fail as expected. Pipeline is functional.

For the detailed prompt template, see `references/prompts.md` — Phase 3.

### Phase 4 — Implementation

**Assign to:** `implementer`

Instruct the implementer to:

1. Run acceptance tests — confirm they fail
2. Pick the simplest failing acceptance test
3. Write a unit test, then minimal code to pass it
4. Refactor, repeat until that acceptance test passes
5. Move to next failing acceptance test
6. Continue until ALL acceptance + unit tests pass

**Rules for the implementer:**
- Never modify spec files — they are the contract
- Never modify generated test files — only regenerate
- If a spec seems wrong, stop and ask the team lead
- Report results of both test streams when done

**Gate:** Both test streams green. Implementer reports results.

For the detailed prompt template, see `references/prompts.md` — Phase 4.

### Phase 5 — Post-Implementation Review

**Assign to:** `reviewer`

Two reviews:

1. **Spec review** — Run /atdd:spec-check. Check if implementation details
   leaked into specs during development.
2. **Code review** — Check test quality, code structure, missing edge cases.

**Gate:** Reviews clean or issues addressed. Team lead approves.

For the detailed prompt template, see `references/prompts.md` — Phase 5.

### Phase 6 — Mutation Testing (Optional)

**Assign to:** `reviewer` or `implementer`

After both test streams are green and reviews pass, run mutation testing
to verify test quality:

1. Run `/atdd:mutate` to generate mutants and measure mutation score
2. Analyze surviving mutants — identify real test gaps vs. equivalent mutants
3. Run `/atdd:kill-mutants` to write targeted tests for survivors
4. Re-run mutations to confirm kills

**Gate:** Mutation score meets target (90%+ recommended). Remaining
survivors documented as equivalent mutants.

For the detailed prompt template, see `references/prompts.md` — Phase 6.

## After Completion

When all phases pass:

1. Run both test streams one final time to confirm green
2. Ask the user whether to commit (do not auto-commit)
3. Ask whether to iterate with the next feature (return to Phase 1)
   or shut down the team

## Tips for Team Leads

- **Never delegate spec approval.** Specs are the team lead's contract.
- **Run spec-check twice** — before and after implementation.
- **Test portability.** Verify specs would work for a different implementation language.
- **Scope tightly.** One feature per cycle. Do not spec the whole system.
- **Verify both streams personally** before accepting the implementer's work.
- **Keep the team informed.** When revising specs after review, notify the
  implementer so they don't work against stale specs.

## Additional Resources

### Reference Files

For detailed prompt templates for each phase:
- **`references/prompts.md`** — Copy-paste prompt templates for every phase,
  including the team creation prompt and all agent instructions
