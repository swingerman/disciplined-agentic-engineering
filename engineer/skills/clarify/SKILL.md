---
name: clarify
description: Use when a single DAE artifact has ambiguities to resolve. Triggers — "/engineer.clarify", "clarify this spec", "resolve ambiguities", "this is vague — tighten it".
---

# clarify

Resolve ambiguities in **one** DAE artifact through an iterative interview. A cross-cutting quality gate — runs on any artifact at any pipeline stage.

The clarify *pattern* is also embedded inside artifact-producing skills for their own in-flight ambiguities; this standalone skill is for ad-hoc cleanup after the fact.

## When to use

On any one of: `feature.md`, `acs.md`, `spec.md`, `plan.md`, `CHARTER.md`. Invoked as `/engineer.clarify <slug> <artifact>` or `/engineer.clarify <path>`.

**Not for:** cross-artifact contradictions (`consistency-check`); changing what a feature does (`feature-edit`); resolutions that cascade across files (clarify the source here, then `feature-edit`).

## Workflow

1. **Resolve + load** — find `.engineer/manifest.yml`; locate the target artifact. Also load its parent contract for grounding (`feature.md` for acs/spec/plan; `CHARTER.md` for feature.md).
2. **Identify ambiguities** — within this one artifact: language interpretable two ways, underspecified requirements, undefined domain terms, unclear scope boundaries, internal contradictions. Cross-*artifact* contradictions are out of scope (→ `consistency-check`). If none found, say so and stop.
3. **Resolve one at a time** — per ambiguity, quote the ambiguous line and ask one question — multiple-choice (AskUserQuestion) when bounded, open-ended otherwise. Iterate until resolved or the user stops.
4. **Edit in place** — encode each resolution into the target artifact; show old→new, confirm before writing. Edit **only** the target artifact.
5. **Flag downstream staleness** — do NOT cascade. Identify downstream artifacts a resolution may have invalidated; list them in the handoff; recommend `feature-edit` (which owns cascade).
6. **Handoff** — emit a summary.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: null`. If downstream staleness flagged: `human_action_needed: yes`, `recommended_next`: "/engineer.feature-edit to propagate".

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — artifact schemas
- The DAE methodology page — clarify as embedded pattern + standalone skill
