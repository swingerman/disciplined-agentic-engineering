# ATDD Team — Prompt Templates

Detailed prompt templates for each phase of the team-based ATDD workflow.
Adapt placeholders (`[feature description]`, `[feature-name]`,
`[NNN-slug]`, `[project test command]`) to the specific project.

---

## Team Creation

### When no team exists

```
Create a team called "atdd-[feature-name]" with the following teammates:

1. "spec-writer" (general-purpose) — Writes Given/When/Then acceptance
   test specs. Has the atdd plugin installed. Must follow the /atdd:atdd
   skill strictly. Never uses implementation language in specs.

2. "implementer" (general-purpose) — Implements features using TDD.
   Writes unit tests first, then code, until both acceptance tests and
   unit tests pass. Never modifies spec files.

3. "reviewer" (general-purpose) — Reviews specs for implementation
   leakage and reviews code for quality. Has the atdd plugin installed.
   Uses /atdd:spec-check. Read-heavy role — primarily analyzes, does
   not write production code.
```

### When extending an existing team

```
Add the following ATDD roles to the existing team "[team-name]":

[Include only roles that don't already exist by name]

1. "spec-writer" (general-purpose) — Writes Given/When/Then acceptance
   test specs following the atdd plugin's /atdd:atdd skill.

2. "implementer" (general-purpose) — Implements features using TDD
   until both acceptance tests and unit tests pass.

3. "reviewer" (general-purpose) — Reviews specs for implementation
   leakage and reviews code for quality. Has the atdd plugin installed.
```

---

## Phase 1 — Spec Writing

Send to **spec-writer**:

```
We're implementing [feature description].

Follow the ATDD workflow from the atdd plugin. Your job:

1. Read the existing codebase to understand the domain language
   (how does the app refer to users, orders, sessions, etc.?)
2. Write the feature's spec.md in standard Gherkin under
   features/[NNN-slug]/
3. Use ONLY external observables — no class names, no API endpoints,
   no database tables, no framework terms
4. Name each behavior with a Scenario: line; use Scenario Outline:
   + Examples: for behaviors with varying data
5. Send me the specs for review before proceeding

CRITICAL: If you're unsure whether a term is domain language or
implementation language, ask me. Do NOT guess.

Example of what I expect:

Feature: User Registration

Scenario: User can register with email and password
  Given no registered users
  When a user registers with email "bob@example.com" and password "secret123"
  Then there is 1 registered user
  And the user "bob@example.com" can log in
```

### Revision prompt (if specs need changes after review)

Send to **spec-writer**:

```
The reviewer found issues with features/[NNN-slug]/spec.md.

Issues found:
[paste reviewer's findings]

Revise the specs to fix these issues. Remember:
- Use domain language only, no implementation details
- Each spec tests one behavior
- A non-developer should understand every statement

Send me the revised specs for re-review.
```

---

## Phase 2 — Spec Review

Send to **reviewer**:

```
Review features/[NNN-slug]/spec.md for implementation leakage.

Flag ANY of these:
- Class names, function names, method names
- Database tables, columns, queries
- API endpoints, HTTP methods, status codes
- Framework terms (controller, service, repository, middleware)
- Internal state or data structures
- File paths or module names

For each violation, show the bad line and propose a rewrite using
domain language only.

Also check:
- Is each spec testing ONE behavior?
- Are the Given/When/Then steps clear to a non-developer?
- Could these specs work for a different implementation language?

Send me your review with a PASS/FAIL verdict.
```

---

## Phase 3 — Pipeline Generation

Run as team lead, or send to **implementer**:

```
Generate the test pipeline for this project. Analyze:
- Language and test framework in use
- Project structure and existing test patterns
- The feature's spec.md in features/[NNN-slug]/

The parser (dae_gherkin.py) is portable and shipped — do NOT build it.
Generate the project-specific half:
1. Generator — reads .build/spec.json (the IR), produces runnable
   tests in .build/generated/
2. Step handlers — bind each step's text to the system's internals
3. Runner script — run-acceptance-tests.sh (parse → generate → run)

The generator must have DEEP knowledge of the codebase internals.
This is NOT Cucumber. Generated tests should call directly into the
system — no manual fixture glue.

Run the acceptance tests after generation. They MUST fail (red).
If they pass, either the behavior already exists or the generator
isn't testing the right thing.

Report which tests fail and confirm the pipeline is working.
```

### Pipeline update prompt (when specs changed after initial generation)

```
The feature's spec.md in features/[NNN-slug]/ has been updated.
Re-run the pipeline to regenerate tests:

1. Re-parse the updated specs
2. Regenerate the test files
3. Run the acceptance tests
4. Report results

Do NOT modify the spec files. Only regenerate from them.
```

---

## Phase 4 — Implementation

Send to **implementer**:

```
The acceptance specs are in features/[NNN-slug]/spec.md.
The test pipeline is set up — run ./run-acceptance-tests.sh to execute.

Implement the feature using TDD:

1. Run acceptance tests first — confirm they FAIL
2. Pick the simplest failing acceptance test
3. Write a unit test for the smallest piece needed
4. Write minimal code to make the unit test pass
5. Refactor
6. Repeat 3-5 until that acceptance test passes
7. Move to the next failing acceptance test
8. Continue until ALL acceptance tests AND unit tests pass

RULES:
- Never modify spec.md — it is the contract
- Never modify generated test files — only regenerate via the pipeline
- If a spec seems wrong or ambiguous, STOP and ask me
- Run both test streams before reporting done:
  ./run-acceptance-tests.sh  (acceptance tests)
  [project test command]      (unit tests)
- Send me the results when both streams are green
```

### Unblocking prompt (if implementer reports a spec issue)

Send as team lead after reviewing the issue:

```
I've reviewed your concern about the spec:
"[spec line in question]"

[One of these responses:]

A) The spec is correct. The implementation needs to handle this case.
   Continue implementing.

B) The spec needs revision. I'm sending updated specs to the spec-writer.
   Pause implementation until I notify you that new specs are ready.

C) The spec is ambiguous. Here's what it means: [clarification].
   Continue with this interpretation.
```

---

## Phase 5 — Post-Implementation Review

Send to **reviewer**:

```
Implementation is complete. Do two reviews:

1. SPEC REVIEW: Run /atdd:spec-check on features/[NNN-slug]/spec.md
   Check if any implementation details leaked into specs during
   development. Propose cleanups if found.

2. CODE REVIEW: Review the implementation for:
   - Test quality (are unit tests testing the right things?)
   - Code structure (does it match what the specs describe?)
   - Missing edge cases (any specs that should be added?)

Send me both reviews with a PASS/FAIL verdict for each.
```

### Follow-up prompt (if review found issues)

```
The reviewer found issues:

SPEC REVIEW: [PASS/FAIL]
[findings if any]

CODE REVIEW: [PASS/FAIL]
[findings if any]

[Route to the appropriate agent:]

For spec leakage → send to spec-writer for cleanup
For code issues → send to implementer for fixes
For missing specs → send to spec-writer, then repeat from Phase 2
```

---

## Completion

### Wrap-up prompt to user

```
ATDD team workflow complete for [feature description].

Results:
- Specs: features/[NNN-slug]/spec.md (reviewed, no leakage)
- Acceptance tests: ALL PASSING
- Unit tests: ALL PASSING
- Code review: CLEAN

Next steps:
1. Commit the changes?
2. Start the next feature with the team?
3. Shut down the team?
```

---

## Phase 6 — Mutation Testing (Optional)

Send to **reviewer** or **implementer**:

```
Both test streams are green and code review is clean.
Now verify test quality with mutation testing.

1. Run /atdd:mutate to set up the mutation framework and run mutations
2. Review the mutation score and surviving mutants
3. For each survivor, determine:
   - Is it a real test gap? → write a unit test to kill it
   - Is it an equivalent mutant? → document and ignore
4. Run /atdd:kill-mutants to write tests for real survivors
5. Re-run /atdd:mutate to confirm kills

Target: 90%+ mutation score.

RULES:
- Only add new tests — never modify existing tests or source code
- Never mutate spec files or generated test files
- If a surviving mutant reveals a real BUG in source code, report
  it to me instead of writing a test for the buggy behavior

Send me the mutation score (before and after) and any remaining
equivalent mutants.
```

### If mutation score is low

```
The mutation score is [X]% — below the 90% target.

Focus on the [N] surviving mutants in these files:
[list files with most survivors]

For each survivor, write a targeted unit test that exercises the
exact code path. Re-run mutations after each batch of new tests
to track progress.

Send me updates as the score improves.
```

---

### Shutdown prompt

Send a `shutdown_request` message to each teammate (`spec-writer`,
`implementer`, `reviewer`) using the SendMessage tool. The team
framework handles graceful shutdown — each agent receives the request
and confirms before exiting.

---

## Handling Edge Cases

### Spec-writer and implementer disagree

The team lead arbitrates. Read the spec, read the implementation concern,
decide whether the spec or implementation needs to change. Never let the
implementer unilaterally modify specs.

### Pipeline can't handle a spec

The spec may need to be broken into smaller behaviors, or the pipeline
generator needs improvement. Ask the implementer to update the generator,
NOT the spec. Specs describe what, generators figure out how to test it.

### Reviewer finds leakage after implementation

This is expected and normal. Route the finding to the spec-writer for
cleanup. The implementer does NOT need to change code — leakage cleanup
only affects spec wording, not behavior.
