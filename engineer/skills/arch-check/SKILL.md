---
name: arch-check
description: Use to check a feature's code against the charter's architecture rules — dependency layering, forbidden patterns, file naming, file size. Triggers — "/engineer.arch-check", "architecture check", "check architecture fitness", "does this follow the charter", "check layering".
---

# arch-check

Run the charter architecture fitness check — Checkpoint 7 (Light Verify),
alongside `crap-analyzer`. Turns the charter's architectural vision from prose
into an objective gate: `dae_arch.py` reads the manifest's `architecture:` rules
and reports violations.

Read-only on the codebase — it reports, it does not fix.

## When to use

Checkpoint 7, after the feature's code is implemented and refined. Also useful
as a standalone audit (`--full`) of an existing project.

**Not for:** change-risk analysis (`crap-analyzer`); artifact consistency
(`consistency-check`); fixing violations (that is a human/agent decision per
violation).

## Workflow

### Step 0 — Entry gate

Verify the prior checkpoint is complete: run
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_handoff.py <feature-dir> --through 6`. On a
non-zero exit, **stop** and surface the gap to the human.

### Step 1 — Run the check

Run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_arch.py <methodology-root>` (add `--full`
for a whole-project audit). If it reports "no `architecture:` section", tell the
user the charter has no machine-readable architecture rules yet and stop.

### Step 2 — Present violations

Group the violations by kind (layering first — it is the architectural-vision
core). For each, show `file:line` and the rule. Do not auto-fix.

### Step 3 — Triage with the human

For each violation, the human decides: a real break (fix the code), or a rule
that no longer fits (amend `manifest.architecture` — and the charter prose).
`dae_arch.py` exiting non-zero means Checkpoint 7's architecture-fitness exit
criterion is unmet until the violations are resolved.

### Step 4 — Handoff

Emit a summary per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`.
`checkpoint: 7`; the `exit_criteria` block asserts the architecture-fitness
criterion with `verified_by: tool` and the `dae_arch.py` exit status as evidence.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) —
  the `architecture:` manifest section (§2); the Checkpoint Exit Contract (§8)
