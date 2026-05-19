---
name: atdd-mutate
description: >-
  This skill should be used when the user asks to "run mutation testing",
  "mutate my code", "kill mutants", "check test quality", "find surviving
  mutants", "verify test effectiveness with mutations", "run stryker", "run
  mutmut", "run pitest", "set up mutation testing", "how good are my tests",
  "are my tests catching bugs", or mentions mutation testing, mutation score,
  or mutant survival in the context of testing. It adds a third validation
  layer to the ATDD workflow: after acceptance tests verify WHAT and unit
  tests verify HOW, mutation testing verifies that tests actually catch bugs.
version: 0.6.0
---

# Mutation Testing

Add a third validation layer to the ATDD two-stream testing approach.
Acceptance tests verify WHAT, unit tests verify HOW, mutation testing
verifies that the tests **actually catch bugs**.

## Core Concept

Mutation testing introduces deliberate bugs (mutants) into source code,
then runs the test suite. If tests fail, the mutant is **killed** (good).
If tests pass despite the bug, the mutant **survives** (test gap found).

```
Source code → introduce mutation → run tests
                                     ├── tests FAIL → mutant killed ✓
                                     └── tests PASS → mutant survived ✗
```

A project with 100% code coverage can still have a 60% mutation score —
meaning 40% of introduced bugs go undetected by the test suite.

## When to Use

Run mutation testing **after both test streams are green**:

1. Acceptance tests pass (WHAT is correct)
2. Unit tests pass (HOW is correct)
3. **Mutation testing** — verify tests actually detect regressions

This is Phase 6 in the team-based ATDD workflow, or a standalone
quality check at any point during development.

## Approach: Custom Mutation Tool (Preferred)

The preferred approach is to **build a custom mutation tool** for the
project. This follows the methodology Uncle Bob developed for
[empire-2025](https://github.com/unclebob/empire-2025/blob/master/docs/plans/2026-02-21-mutation-testing.md)
— a project-specific tool that walks the AST/source tree, applies one
mutation at a time, runs targeted tests, and reports survivors.

### Why Custom is Preferred

- **Tight integration** with the project's test runner and source structure
- **Targeted execution** — run only the tests affected by each mutation
- **Language-agnostic** — works for any language, including those without
  established mutation frameworks
- **No external dependencies** — the tool lives in the project
- **AST-level precision** — understands the language's constructs natively

### Architecture (3 modules)

1. **Mutations** — rules table (e.g., `+` → `-`, `true` → `false`,
   `>=` → `>`) plus matching logic that walks the AST/form tree
2. **Runner** — source-to-test mapping, test execution, pass/fail capture
3. **Core** — orchestration: read source → discover sites → apply one
   at a time → run tests → restore original → report

### Core Mutation Categories

| Category | Examples |
|----------|----------|
| Arithmetic | `+` ↔ `-`, `*` ↔ `/`, `++` ↔ `--` |
| Comparison | `>` ↔ `>=`, `<` ↔ `<=` |
| Equality | `==` ↔ `!=` |
| Boolean | `true` ↔ `false`, `&&` ↔ `||` |
| Conditional | negate conditions, swap if/if-not |
| Constant | `0` ↔ `1`, `""` ↔ `"mutant"` |
| Return value | return `true` → return `false` |
| Void method | remove method call entirely |

For the full architecture and detailed reference, see
`references/frameworks.md`.

## Alternative: Existing Frameworks

When speed of setup is more important than tight integration, use an
established mutation framework as a secondary option:

| Language | Framework |
|----------|-----------|
| JavaScript/TypeScript | [Stryker](https://stryker-mutator.io/) |
| Python | [mutmut](https://github.com/boxed/mutmut) |
| Java/JVM | [PIT (pitest)](https://pitest.org/) |
| C# | [Stryker.NET](https://stryker-mutator.io/) |
| Rust | [cargo-mutants](https://github.com/sourcefrog/cargo-mutants) |
| Go | [go-mutesting](https://github.com/zimmski/go-mutesting) |
| Ruby | [mutant](https://github.com/mbj/mutant) |
| Scala | [Stryker4s](https://stryker-mutator.io/) |

For install commands, configuration, and CLI reference, see
`references/frameworks.md`.

## Workflow

Before Step 1, create one TodoWrite todo per step of this workflow (Steps 1–6),
all at once — the full list up front, as a roadmap. Flip each todo to
`in_progress` / `completed` as you go. See
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`.

### Step 1: Verify Prerequisites

Before running mutation testing, confirm:

- Both test streams are green (acceptance + unit)
- The project has meaningful unit tests (mutation testing runs against unit tests)
- No uncommitted changes (mutations modify source files temporarily)

### Step 2: Set Up Mutation Tool

If no mutation tool is configured:

1. Detect the project language from source files and build config
2. **Preferred:** Build a custom mutation tool following the 3-module
   architecture (mutations, runner, core). Use TDD to build the tool itself.
3. **Alternative:** Install an existing framework if rapid setup is needed
4. Configure to target source directories and exclude test/spec/generated files
5. Exclude `.build/` (generated tests and IR) and the `acceptance/` pipeline code from mutation

**Important:** Configure mutation testing to target **source code only**.
Never mutate test files, spec files, or generated pipeline code.

### Step 3: Run Mutations

Execute the mutation framework and collect results:

- Total mutants generated
- Mutants killed (tests caught the bug)
- Mutants survived (test gap)
- Mutation score (killed / total × 100)

### Step 4: Analyze Survivors

For each surviving mutant:

1. Read the mutation — what was changed? (e.g., `>=` → `>`, removed function call)
2. Identify which behavior is unguarded
3. Determine whether this represents a real test gap or an equivalent mutant

**Equivalent mutants** are mutations that don't change observable behavior
(e.g., changing `x = x + 0`). These can be ignored.

### Step 5: Kill Surviving Mutants

For each real survivor:

1. Write a new unit test that specifically targets the unguarded behavior
2. Run the test to confirm it fails against the mutant
3. Run the full test suite to confirm it passes against the original code
4. Re-run mutation testing to confirm the kill

### Step 6: Report

Present a summary:

```
Mutation Testing Report
═══════════════════════
Score:     87% → 95% (after killing survivors)
Killed:    190 / 200
Survived:  10 → 5 (5 equivalent mutants ignored)
New tests: 5 unit tests added

Remaining survivors (equivalent mutants):
- src/utils.js:42 — changed `x + 0` to `x + 1` (no-op mutation)
- ...
```

## Mutation Score Targets

| Score | Assessment |
|-------|-----------|
| 90%+  | Strong test suite — minor gaps only |
| 70-89% | Moderate — meaningful gaps to address |
| < 70% | Weak — significant untested behavior |

A 100% mutation score is not always practical or necessary. Focus on
killing mutants that represent real behavioral gaps, not chasing
equivalent mutants.

## Integration with ATDD Workflow

Mutation testing extends the existing two-stream approach:

```
1. Write specs (WHAT)           ← acceptance tests
2. Implement with TDD (HOW)     ← unit tests
3. Verify test quality (REAL?)  ← mutation testing
```

When using the `atdd-team` skill, mutation testing is part of Phase 6
(Verify & Harden), run by the **architect** — an agent whose `agent_id`
is independent of the implementer and the refiner.

## Anti-Patterns

### "Let me mutate before tests are green"
No. Fix failing tests first. Mutation testing assumes a green baseline.

### "100% mutation score or nothing"
Not practical. Equivalent mutants inflate the denominator. Aim for 90%+
and document the equivalent mutants that remain.

### "Mutate everything including generated code"
Never mutate generated test files or the acceptance pipeline.
Only mutate source code under development.

## Additional Resources

### Reference Files

For detailed framework setup and configuration:
- **`references/frameworks.md`** — Installation, configuration, and CLI
  reference for each supported mutation testing framework
