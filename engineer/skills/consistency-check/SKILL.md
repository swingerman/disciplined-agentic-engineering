---
name: consistency-check
description: Use to validate DAE artifacts for schema correctness and cross-artifact consistency. Triggers — "/engineer.consistency-check", "check consistency", "validate the artifacts", "are the specs and ACs in sync", "audit this feature".
---

# consistency-check

Cross-artifact validation for DAE — the methodology's take on Speckit's `/analyze`. **Read-only**: reports inconsistencies and suggests fixes; never mutates. Any agent may run it (mechanical validation, not judgment-heavy verification). `checkpoint: null`.

## When to use

Before major pipeline transitions and as a CI gate.

- **Feature scope** — `/engineer.consistency-check <slug>` — one feature's artifacts
- **Project scope** — `/engineer.consistency-check --project` — project-wide invariants

**Not for:** fixing inconsistencies (run the suggested fix skill); within-one-artifact ambiguity (`clarify`); code risk (`crap-analyzer`).

## Workflow

1. **Resolve + load** — find `.engineer/manifest.yml`; resolve `methodology_root`. Feature scope: load every artifact in `features/NNN-<slug>/` + `CHARTER.md` + `manifest.yml`. Project scope: load `CHARTER.md`, `manifest.yml`, every `feature.md` frontmatter.
2. **Run the checks** (below).
3. **Report** — errors first, then warnings; each with location + a suggested fix (which skill to run). Do not apply fixes.
4. **Handoff** — emit a summary.

### Feature-scope checks

| Check | Severity |
|-------|----------|
| `feature.md` slug matches folder name | error |
| `feature.md` mandatory frontmatter present; `status: ready` ⇒ `autonomy_level` set | error |
| `acs.md` AC IDs unique + sequential; `ac_count` matches actual | error |
| `acs.md` ACs in domain language (implementation-leakage heuristic) | warning |
| `acs.md` ACs cover the `feature.md` outcome | warning |
| `relevant_adrs` reference ADRs that exist | error |
| `spec.md` and `.build/spec.json` agree | error |
| `plan.md` Charter Check: every ⚠️ deviation has a matching amendment | error |
| Verification handoffs: `agent_id` ≠ implementer's (Principle 7) | error |
| `tracker_ref` resolves on the configured tracker | warning |
| `progress.md` checkpoint table consistent with `handoffs/` | warning |
| `parent_feature` set ⇒ parent exists and lists this in `child_features` | error |

### Project-scope checks

| Check | Severity |
|-------|----------|
| `CHARTER.md` section 5 roles == `manifest.team.default_roles` | error |
| `manifest.yml` schema valid; enum values legal | error |
| Feature folder numbering monotonic; no reuse | error |
| ADR not referenced by any feature in N months (N from manifest, default 6) | warning |
| Every `features/*/` has a non-empty `feature.md` | warning |
| `team.default_roles` includes `verifier` when independence enforced | error |

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: null`; `artifacts: []`. Any errors → `human_action_needed: yes`. `recommended_next`: resolve via `clarify` / `feature-edit` / `plan`, then re-run.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — every schema checked here
- [Tracker Integration](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — `tracker_ref` resolution
