# Subagent prompt template for parallel per-finding analysis

Use when SKILL.md step 5 dispatches one subagent per CRAP finding. Each subagent is self-contained and cannot see the main conversation, so the prompt must carry every piece of context needed to produce the deliverable.

## Per-subagent prompt template

Fill in the `<…>` placeholders from the finding JSON returned by `scripts/compute_crap.py`:

> **Draft a refactor + test stubs for one CRAP finding.**
>
> **Finding:** `<file>:<start_line>` — `<name>` (`<kind>`, `<language>`). Complexity `<N>`, coverage `<pct>%` (`<covered>/<executable>` lines), CRAP score **`<crap>`**.
>
> **File to read:** `<absolute path to source file>`. Read the entire file for context, then focus on lines `<body_start_line>–<body_end_line>`.
>
> **Test framework in this repo:** `<Jest | pytest | JUnit 5 | Go testing | RSpec | …>`. Test file convention: `<e.g. alongside source as *.spec.ts>`.
>
> **Codebase conventions to respect:** `<2–3 bullets from the repo — e.g. "uses pytest fixtures", "async errors return Result<E>", "DI via constructor">`. Read nearby files if more context is needed.
>
> **Deliverable** — one markdown block in exactly this shape:
>
> ```markdown
> ### `<file>:<line>` — `<name>` (CRAP `<score>`)
>
> **Why it's flagged:** <one sentence naming the dominant factor — complexity, coverage, or both — and pointing at the specific branches>.
>
> **Refactor proposal:**
> <unified diff OR fenced code block of the proposed replacement; pick whichever is clearer for the change>
>
> **Safe to auto-apply?** <yes | no — reason if no, per the rules in SKILL.md step 7>
>
> **Test stubs to add:**
> <framework-appropriate fenced block with at least one real assertion per stub>
> ```
>
> Keep it tight — one paragraph of "why", the diff, the stubs. No preamble, no alternatives, no "you could also…". If the function is already fine and the high CRAP comes purely from missing tests, skip the refactor block and say so.

## Aggregation by the main agent

1. Wait for all subagents to return.
2. Sort results by CRAP score descending (same order as the findings table).
3. Print them back-to-back under the report table, unchanged.
4. **Sanity-check each "safe to auto-apply" claim** against SKILL.md step 7. Subagents sometimes mislabel. Downgrade to "no" if the diff shows a reordered async op, a touched constructor / lifecycle hook, or a split across a `try` boundary.
5. Continue to the wrap-up menu (step 6 in SKILL.md).

## Tool-use hygiene

- All `Agent` tool calls must go in a **single message** so the runtime can truly parallelize.
- Each prompt is self-contained — the subagent cannot see this file, SKILL.md, or the conversation.
- Pass absolute paths, not relative ones.
- Do not include the full diff in the prompt — the subagent only needs the finding metadata and the file path.
- Pick the `general-purpose` agent type unless the repo has a more specialized one configured.

## What not to delegate

- The coverage toolchain discovery (step 2) — do that once in the main agent.
- The wrap-up menu and per-change confirmation loop (step 6) — these are user-interactive and must stay in the main conversation.
- Applying edits — subagents draft, the main agent applies after user confirmation.
