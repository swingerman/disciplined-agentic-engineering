# Wrap-up menu and apply loop

After the CRAP report and per-finding proposals are on screen, present an actionable menu via `AskUserQuestion` so the user can dispatch work in one step. Do this every time, even with a single finding.

## Global menu (always shown first)

Ask one multi-select question — phrase the prompt *"How should I address these findings?"* — with these options:

| Header | Option label | What it does |
|---|---|---|
| Refactors | Apply safe refactors for **all** findings | Iterate findings, apply only the refactors marked safe in [refactor-patterns.md](refactor-patterns.md), one Edit per function |
| Refactors | Apply safe refactors for the **top N** | Ask a follow-up for N, then apply to the top-N by CRAP score |
| Tests | Add test stubs for **all** findings | Create or extend the test file next to each source file using templates from [test-stub-templates.md](test-stub-templates.md) |
| Tests | Add test stubs for **top N** | Ask for N, then stub only those |
| Per-item | Pick per finding | Drop into the per-finding loop below |
| Skip | Skip — report only | Leave code untouched |

Multi-select is on so the user can combine choices (e.g. "safe refactors for top 3" + "tests for all").

## Per-finding loop

If the user picked "Pick per finding", walk findings worst-first and ask one multi-select per function:

*"`funcName` at `file:line` (CRAP N) — what should I do?"*

Options:

- Apply the proposed refactor
- Add the proposed test stubs
- Skip this function
- Stop — no more per-item prompts (exits the loop, reports what was applied so far)

Between iterations, keep the message terse: name, `file:line`, score, action taken. Do not re-print the full diff the user already saw.

## Execution rules

- **One Edit per action.** Never bundle multiple functions into a single tool call.
- **Refactor before tests for the same function.** Stub examples should reference the final names.
- **Run the test stubs just added** if the user has a test runner and accepts. Use the framework's most-scoped command (e.g. `jest --findRelatedTests`, `pytest path/to/test.py::TestClass`, `go test -run TestName`). Failures after stubbing are expected — flag them and let the user fill in assertions.
- **Re-run the analyzer at the end** if any refactor or test was applied. Show before/after CRAP scores side-by-side in a short summary.

## Summary block

After the menu loop ends, print one summary:

```markdown
## Wrap-up

- Refactored: 3 function(s) — `foo`, `bar`, `baz`
- Tests stubbed: 5 spec file(s) — see `test_*.py` / `*.spec.ts` / `*_test.go` alongside sources
- Skipped: 2 function(s) — `qux` (user skipped), `quux` (no safe refactor available)

Re-run CRAP: top score dropped from **240 → 43**, 4 findings → 1.
```
