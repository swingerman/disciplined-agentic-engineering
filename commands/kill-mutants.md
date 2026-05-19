---
name: kill-mutants
description: Analyze surviving mutants from a mutation testing run and write targeted unit tests to kill them. Re-runs mutations to confirm kills.
arguments:
  - name: ARGUMENTS
    description: Optional mutant IDs or file path to focus on (e.g., "src/auth.ts" or "1,3,5" for specific mutant IDs)
    required: false
---

Analyze surviving mutants and write tests to kill them.

## Instructions

1. Read the most recent mutation testing report/results.
   If no report exists, inform the user to run `/atdd:mutate` first.

2. List all surviving mutants. For each, determine:
   - What was mutated (the operator: boundary change, removed call, inverted condition, etc.)
   - What behavior is unguarded by the current test suite
   - Whether the mutant is **equivalent** (mutation doesn't change observable behavior)

3. If `$ARGUMENTS` specifies a file or mutant IDs, filter to only those survivors.

4. For each non-equivalent survivor:
   a. Write a targeted unit test that:
      - Exercises the exact code path affected by the mutation
      - Asserts the correct behavior that the mutation would break
      - Follows existing test naming conventions and patterns in the project
   b. Run the new test against the original code — it must **pass**
   c. Verify the test would **fail** against the mutant (conceptual verification)

5. After writing all new tests, re-run mutation testing (`/atdd:mutate`) to confirm:
   - Previously surviving mutants are now killed
   - No regressions (previously killed mutants still killed)
   - This re-run is differential — adding a test changes the covering tests'
     hash, so only the affected function re-mutates; the rest are reused from
     the manifest

6. Report the updated mutation score and remaining survivors.

7. For any remaining equivalent mutants, document them:
   ```
   Equivalent mutants (safe to ignore):
   - src/utils.ts:42 — `x + 0` → `x + 1` (no behavioral change)
   ```

## Rules

- Never modify existing tests to make mutants survive. Only ADD new tests.
- Never modify source code to kill mutants. The source is correct; the tests need strengthening.
- Never modify spec files. Mutation testing operates on unit tests only.
- If a surviving mutant reveals a genuine **bug** in the source code (not just a test gap),
  report it to the user rather than writing a test that asserts the buggy behavior.
