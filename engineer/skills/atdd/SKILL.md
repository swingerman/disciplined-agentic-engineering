---
name: atdd
description: Use to write a feature's acceptance specs and generate its test pipeline — Checkpoint 3 of the DAE pipeline. The engineer-namespace entry point into the atdd plugin's acceptance workflow. Triggers — "/engineer.atdd", "write the spec", "Checkpoint 3", "formalize the ACs as specs", "generate the test pipeline".
---

# atdd

The DAE pipeline's Checkpoint 3 (Spec) entry point. AC discovery (Checkpoint 2,
`discover-acs`) decided *what behaviors must work*; this step formalizes them as
a standard-Gherkin `spec.md` and generates the project-specific test pipeline.

This skill is a **thin bridge**: the acceptance workflow itself lives in the
`atdd` plugin (`atdd:atdd`). `engineer.atdd` wraps it with the DAE checkpoint
contract — the entry gate in, the handoff out — so the acceptance pipeline is a
first-class checkpoint of the engineer pipeline rather than a separate detour.

**Requires the `atdd` plugin.** If it is not installed, tell the user to run
`/plugin install atdd@disciplined-agentic-engineering` and stop.

## When to use

Checkpoint 3, after `discover-acs` (Checkpoint 2) has produced an approved
`acs.md`. Produces `spec.md` + the feature's `.build/` pipeline.

**Not for:** AC discovery (`discover-acs`); planning (`plan`); using the
acceptance workflow outside a DAE feature folder (invoke `atdd:atdd` directly).

## Workflow

### Step 0 — Entry gate

Verify the prior checkpoint is complete: run
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_handoff.py <feature-dir> --through 2`. On a
non-zero exit, **stop** and surface the gap to the human.

Verify branch hygiene: run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_branch.py <feature-dir>`.
On a non-zero exit, **stop** and surface the message to the human — switch
branches and re-invoke. The check honors the `git.manual: true` manifest
opt-out.

After the gate passes, show the **pipeline breadcrumb**: run
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_progress.py <feature-dir>` and present its
output to the human — it shows where this checkpoint sits in the DAE pipeline.
The breadcrumb is advisory: a non-zero exit or a missing `progress.md` never
blocks the skill. Then create one TodoWrite todo per workflow step below. See
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`.

### Step 1 — Run the acceptance workflow

Invoke the `atdd:atdd` skill, scoped to this feature: write the feature's
`spec.md` in standard Gherkin from `acs.md`, then generate the test pipeline
(the `pipeline-builder` agent + the portable `dae_gherkin.py` parser). Present
`spec.md` to the human for approval — specs are the human's contract.

### Step 2 — Handoff

Emit a summary per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`.
`checkpoint: 3`; the `exit_criteria` block asserts Checkpoint 3's criteria
(Foundation Design Section 8) — `spec.md` parses to a valid IR, every AC maps to
≥1 scenario, spec-check passes — each with `verified_by` and evidence.
`recommended_next`: "/engineer.plan".

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) —
  the Checkpoint Exit Contract (Section 8)
- `atdd:atdd` — the acceptance workflow this skill bridges to
