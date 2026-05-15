---
name: clarify
description: Use when a DAE artifact (feature.md, acs.md, spec.md, plan.md, or CHARTER.md) has ambiguities that should be resolved before downstream work depends on it. Triggers include "/engineer.clarify", "clarify this spec", "resolve ambiguities in the ACs", "this plan is vague — tighten it", or naturally when a reader can't tell what an artifact means. Reads one artifact, identifies ambiguities, presents them one at a time as multiple-choice or open questions, and edits the artifact in place as each is resolved. Single-artifact only — flags downstream staleness but does not cascade (that is feature-edit's job).
---

# clarify

Resolve ambiguities in a single DAE artifact through an iterative interview. A cross-cutting quality gate — it can run on any artifact at any pipeline stage.

The `clarify` *pattern* (read artifact → find ambiguities → ask → resolve) is also embedded directly inside artifact-producing skills (`discover-acs`, `plan`, etc.) for their own in-flight ambiguities. This standalone skill is for **ad-hoc cleanup** of an artifact after the fact.

## When this skill runs

Any time, on any of: `feature.md`, `acs.md`, `spec.md`, `plan.md`, `CHARTER.md`. Not a checkpoint — `checkpoint: null` in the handoff.

Invoked as `/engineer.clarify <slug> <artifact>` (e.g. `clarify customer-export acs`) or `/engineer.clarify <path>`.

## Workflow

### Step 1 — Resolve and load the target artifact

Walk up to `.engineer/manifest.yml`; resolve `methodology_root`. Locate the target artifact from the slug + artifact-type argument, or from a direct path.

Load the artifact. Also load its parent contract for grounding:
- For `acs.md` / `spec.md` / `plan.md` → also load `feature.md` (the outcome the artifact serves)
- For `feature.md` → also load `CHARTER.md`
- For `CHARTER.md` → load it alone

### Step 2 — Identify ambiguities

Read the artifact and flag, **within this one artifact**:
- Language interpretable two different ways
- Underspecified requirements — a behavior named but not pinned down
- Undefined domain terms — a word used as if its meaning is settled when it isn't
- Unclear scope boundaries — is X in or out?
- Internal contradictions — two statements in the same artifact that disagree

Out of scope for clarify: *cross-artifact* contradictions (acs.md disagrees with spec.md) — that's `consistency-check`. clarify works within one artifact.

If no ambiguities are found, say so and stop — don't manufacture questions.

### Step 3 — Resolve ambiguities one at a time

For each ambiguity, present it to the user as a single question:
- **Multiple-choice** (AskUserQuestion) when the ambiguity has bounded resolutions — e.g. "Does 'recent' mean last 24h, last 7 days, or last 30 days?"
- **Open-ended** when it doesn't — e.g. "What should happen when the export is empty?"

One ambiguity per turn. Show where in the artifact it lives (quote the ambiguous line). Iterate until all are resolved or the user stops.

### Step 4 — Edit the artifact in place

As each ambiguity is resolved, edit the **target artifact** to encode the resolution. Show the user the proposed edit (old → new) and confirm before writing.

clarify edits **only the target artifact**. It does not touch any other file.

### Step 5 — Flag downstream staleness (do not cascade)

A resolved ambiguity may invalidate downstream artifacts — e.g. tightening an AC in `acs.md` can make the corresponding `spec.md` scenario stale.

clarify does **not** cascade. It detects and flags:
- After editing, determine which downstream artifacts (if any) likely depend on what changed
- List them in the handoff under "downstream staleness"
- Recommend `/engineer.feature-edit`, which owns intent-driven multi-artifact propagation

This keeps clarify simple and single-purpose; `feature-edit` owns the cascade.

### Step 6 — Emit the handoff summary

```markdown
---
skill: clarify
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: null
artifacts:
  - features/NNN-<slug>/<artifact>     # the single artifact edited
findings_summary: <one line — e.g. "6 ambiguities found, 6 resolved; spec.md may be stale">
human_action_needed: <yes if downstream staleness flagged, else no>
human_action_kind: <decision | none>
recommended_next: <see below>
tracker_update: none
status: complete
---

# clarify — handoff summary

## What I did
Reviewed `<artifact>` for `<title>`. Found <N> ambiguities; resolved <M> with the user; edited the artifact in place to encode the resolutions.

## Artifacts produced
- `features/NNN-<slug>/<artifact>` (edited — <M> resolutions applied)

## Findings
<the ambiguities and how they resolved — one line each>

## Downstream staleness
<list downstream artifacts that may now be inconsistent with the resolved artifact — or "None — no downstream artifacts depend on what changed">

## Human action needed?
<If staleness flagged: "Yes — <downstream artifact(s)> may now be stale. Run /engineer.feature-edit to propagate the change.">
<If none: "No — artifact clarified; no downstream impact.">

## Recommended next step
<If staleness: "invoke /engineer.feature-edit to propagate to <downstream artifacts>">
<If none: "resume the pipeline where you left off">
```

## When NOT to use this skill

- Cross-artifact inconsistency (acs.md vs spec.md disagree) → that's `/engineer.consistency-check`
- You want to change *what the feature does* (not resolve vagueness) → that's `/engineer.feature-edit`
- The artifact needs a resolution that cascades into several files → clarify the source artifact here, then run `/engineer.feature-edit` for the cascade

## Cross-skill orchestration

clarify is standalone and single-artifact. It reads one artifact (+ its parent contract for grounding), edits that one artifact, and flags — but does not perform — downstream propagation.

- Upstream: any artifact-producing skill
- This skill: resolves ambiguity within one artifact
- Downstream: `feature-edit` (if cascade needed); `consistency-check` (for cross-artifact validation)

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — artifact schemas, agentic summary contract
- The DAE methodology page — the Speckit synthesis (clarify as embedded pattern + standalone skill)
