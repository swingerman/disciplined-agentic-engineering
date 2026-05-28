---
name: fix
description: Use to drive a bug fix from first report through close, with a "why didn't we catch it?" loop at the end. Triggers — "/engineer.fix", "a bug came in", "this is broken", "a user reported X", "there's a defect", "we have a regression", "this needs a fix".
---

# fix

The defect unit-of-work — parallel to "feature" in the DAE pipeline. Tracks a bug from first report through a regression spec, code fix, hardening, and a structured retrospective that feeds back into the methodology.

Unlike ad-hoc fixes, the `fix` workflow enforces a regression spec that must be RED on current code before any change, and closes the loop with a "why didn't we catch it?" gap analysis tied to a closed category vocabulary. That loop is the methodology contribution: bugs become methodology feedback, not just patches.

## When to use

- A bug report arrives (user report, Sentry alert, stack trace, regression in CI).
- A defect needs a repeatable reproduction path and a tracked fix.
- A regression must be proven to stay fixed (mutation gate).

**Not for:** building a new capability (`/engineer.discuss` or `/engineer.feature-init`); adjusting an in-flight feature's scope (`/engineer.feature-edit`); reviewing recent changes without a defect (`/engineer.verify` or `/crap-analyzer`).

## Workflow

### Step 1 — Capture

Accept free-form input; no feature slug required. Collect: title, severity (`low | medium | high | critical`), source (`kind: sentry|github|slack|user|internal`, `ref: <url-or-id>`), whether it blocks users (`blocks_user`), workaround (`"none"` if none), and a concise repro/expected/actual.

Write `.engineer/fixes/<YYYY-MM-DD-slug>.md` via the schema in `references/artifact-template.md`. Set `status: investigating`.

CLI shortcut: `/engineer.fix "title" --source <url>` pre-fills title and source; skip the prompt for those fields.

Validate the new artifact: `${CLAUDE_PLUGIN_ROOT}/scripts/dae_fix.py --validate <fix-file>`. Surface any errors before proceeding.

### Step 2 — Investigate

**Goal:** identify which feature(s) own the broken code.

Heuristics — run cheapest first to bound token cost:
1. Stack trace files → cross-reference `feature.files` in known features.
2. Error text grep across `.engineer/features/*/feature.md`.
3. Recent commits on the affected path (`git log --oneline -- <file>`).
4. User-provided hints.

**Match resolution:**
- Single clean candidate and `prime-context` confirms strong relevance → AUTO-POPULATE `feature_refs`; record `match_mode: auto`.
- Multiple candidates or ambiguous → rank top 3, invoke `prime-context` per candidate, present ranked list, ask user to confirm. Record `match_mode: manual`.
- No match → record `match_mode: none`; proceed as a loose fix (no `feature_refs`).

Record `investigation.candidates_considered`. Set `status: pinned-pending`.

### Step 3 — Pin (CONFIRM-FIRST GATE 1)

Write one regression Given/When/Then spec **per `feature_refs` entry** (not a shared spec). Use `references/regression-spec-template.md`.

Run the spec on current code. It **MUST be RED**. If it passes (GREEN) the spec does not pin the bug — redraft until RED. Record `red_run.result: red` + command + output in `pin_confirmation.feature_refs[*]`.

Present the spec(s) and red-run evidence to the user for confirmation before proceeding. Set `status: pinned`.

### Step 4 — Fix (CP5-style)

Implement the fix using the same discipline as Checkpoint 5. The regression spec must turn GREEN. Update `fix_commits`. Set `status: fixed`.

### Step 5 — Refine (CP6)

Invoke `engineer:refine` on touched code. Set `status: refined`.

### Step 6 — Verify (CP7)

Run `engineer:arch-check` on each touched feature. Run `crap-analyzer` on the fix diff. Record results. Set `status: verified`.

### Step 7 — Harden (CP8 + CONFIRM-FIRST GATE 2)

Run `atdd:atdd-mutate` on touched files. Record `harden_results.mutation_score`.

**Bug-line mutation gate:** recover the buggy line(s) via `git show HEAD~1 -- <file>`, apply locally, run only the regression spec, assert RED. If the spec stays GREEN the spec is coupled to the fix, not the bug — back to Step 3 (Pin). Restore the fix. Record `harden_results.bug_line_mutation_confirmed: true`.

Record `harden_results.arch_check`. Set `status: hardened`.

### Step 8 — Gap analysis ("why didn't we catch it?")

For each affected feature, identify which DAE phase leaked. Use the closed vocabulary in `references/gap-analysis-categories.md` — one entry per distinct finding.

**CONFIRM-FIRST:** present findings to the user for approval before writing to the artifact. Findings are claims about methodology gaps; the user is the source of truth.

Write approved findings to `gap_analysis[*]`. Determine blockers via `blocker_categories()` (see `references/gap-analysis-categories.md` for the rule). Advisory followups go to `.engineer/consolidation.md` tagged with the fix slug; blocker followups must be applied inline or the charter explicitly amended. Set `status: gap-analyzed`.

### Step 9 — Close

Run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_fix.py` `close_ready(rec)`. Hard preconditions: pin confirmed, hardened (including bug-line gate), `gap_analysis` non-empty, no unresolved blockers.

Emit a handoff that reference-links each `feature_refs[*]/progress.md`. Set `status: closed`.

Then dispatch per `${CLAUDE_PLUGIN_ROOT}/references/handoff-dispatch.md`: advisory followups already landed in `.engineer/consolidation.md` (no dispatch — `next` surfaces them); blocker followups are already applied. Auto-invoke `/engineer.progress-log` to propagate the closure entry to each affected feature's `progress.md` at autonomy `medium`/`high`; confirm-then-dispatch at `low`.

## When NOT to use this skill

- Building a new feature → `/engineer.discuss` or `/engineer.feature-init`
- Refining an in-flight feature's scope → `/engineer.feature-edit`
- Reviewing recent changes without a defect → `/engineer.verify` or `/crap-analyzer`

## References

- `references/artifact-template.md` — canonical `.engineer/fixes/<slug>.md` schema
- `references/regression-spec-template.md` — Given/When/Then template used in Step 3
- `references/gap-analysis-categories.md` — closed vocabulary + blocker rule
- Sister skills: `prime-context` (Step 2 per candidate), `arch-check` + `crap-analyzer` (Step 6), `atdd-mutate` (Step 7), `progress-log` (Step 9), `next` (surfaces open fixes)
