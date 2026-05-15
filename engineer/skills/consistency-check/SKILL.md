---
name: consistency-check
description: Use when DAE artifacts should be validated for schema correctness and cross-artifact consistency before downstream work depends on them. Triggers include "/engineer.consistency-check", "check consistency", "validate the artifacts", "are the specs and ACs in sync", "audit this feature's artifacts", or naturally before a pipeline transition or as a CI gate. Reads all artifacts for a feature (or project-wide), reports inconsistencies, gaps, and conflicts at two severity levels — errors (block) and warnings (smell). Read-only: it reports and suggests fixes; it does not mutate artifacts.
---

# consistency-check

Cross-artifact validation for DAE — the methodology's richer take on Speckit's `/analyze`. Reads the artifacts, reports what's wrong, suggests fixes. **Read-only** — it never mutates; applying fixes is `clarify` / `feature-edit` territory.

Not a checkpoint (`checkpoint: null`). Cross-cutting — run it any time, especially before major pipeline transitions and as a CI gate. It is mechanical schema/consistency validation, not judgment-heavy verification, so verification independence does not apply — any agent may run it.

## Modes

- **Feature scope** — `/engineer.consistency-check <slug>` — validates one feature's artifacts
- **Project scope** — `/engineer.consistency-check --project` — validates project-wide invariants

Default with no argument: infer the feature from the current branch; if none, fall back to project scope.

## Workflow

### Step 1 — Resolve and load

Walk up to `.engineer/manifest.yml`; resolve `methodology_root`.

**Feature scope:** load every artifact in `features/NNN-<slug>/` — `feature.md`, `progress.md`, `acs.md`, `spec.md`, `.build/spec.json`, `plan.md`, `session-log.md`, all `handoffs/*.md` — plus `CHARTER.md` and `manifest.yml` for cross-reference.

**Project scope:** load `CHARTER.md`, `manifest.yml`, and the frontmatter of every `features/*/feature.md`.

### Step 2 — Run the checks

#### Feature-scope checks

| # | Check | Severity if violated |
|---|-------|----------------------|
| 1 | `feature.md` `slug` matches the parent folder name | error |
| 2 | `feature.md` mandatory frontmatter fields all present; `status: ready` implies `autonomy_level` set | error |
| 3 | `acs.md` AC IDs unique and sequential; `ac_count` frontmatter matches actual count | error |
| 4 | `acs.md` ACs use domain language (implementation-leakage heuristic — API/endpoint/table/class terms) | warning |
| 5 | `acs.md` ACs collectively cover the `feature.md` outcome (no orphan outcome, no AC outside scope) | warning |
| 6 | `feature.md` `relevant_adrs` reference ADRs that exist (in `CHARTER.md` or `docs/adr/`) | error |
| 7 | `spec.md` and `.build/spec.json` agree (the IR is current with the markdown source) | error |
| 8 | `plan.md` Charter Check: every ⚠️ deviation row has a matching amendment in the Amendments section | error |
| 9 | Verification handoffs (`crap-analyzer`, `atdd:mutate`) have `agent_id` ≠ the implementer's `agent_id` for this feature (Principle 7) | error |
| 10 | `feature.md` `tracker_ref` resolves on the configured tracker | warning |
| 11 | `progress.md` checkpoint table is consistent with the handoffs actually present in `handoffs/` | warning |
| 12 | If `parent_feature` set, the parent exists and lists this feature in its `child_features` | error |

#### Project-scope checks

| # | Check | Severity if violated |
|---|-------|----------------------|
| P1 | `CHARTER.md` section 5 (agent team) roles == `manifest.team.default_roles` | error |
| P2 | `manifest.yml` schema valid; all enum values legal; required fields present | error |
| P3 | Feature folder numbering monotonic; no number reused after deletion | error |
| P4 | ADR ↔ feature linkage staleness — ADR not referenced by any feature in N months (N from manifest, default 6) | warning |
| P5 | Every `features/*/` folder has a non-empty `feature.md` (no orphan folders) | warning |
| P6 | `manifest.team.default_roles` includes `verifier` when `verification.enforce_independence: true` | error |

### Step 3 — Report

Produce a structured report — errors first, then warnings. For each finding: the check, the location (file + line/section), what's wrong, and a **suggested fix** (which skill to run, what to change). Do not apply the fix.

```
consistency-check — customer-export
========================================
ERRORS (2) — these block downstream work
  [3]  acs.md: ac_count frontmatter says 8, found 9 ACs
       fix: correct frontmatter, or run /engineer.clarify if an AC is malformed
  [8]  plan.md: Charter Check row "Architecture: monolith" marked ⚠️ deviation
       but no matching amendment in the Amendments section
       fix: run /engineer.plan to add amendment ADR, or revise the plan

WARNINGS (1) — review, non-blocking
  [4]  acs.md AC-7: "the endpoint returns 401" — implementation language
       fix: run /engineer.clarify on acs.md to reframe in domain language

Summary: 2 errors, 1 warning. NOT consistent — resolve errors before proceeding.
```

If everything passes: `Summary: 0 errors, 0 warnings. Consistent.`

### Step 4 — Emit the handoff summary

```markdown
---
skill: consistency-check
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: null
artifacts: []
findings_summary: <one line — e.g. "2 errors, 1 warning across customer-export artifacts">
human_action_needed: <yes if any errors, else no>
human_action_kind: <decision | none>
recommended_next: <see below>
tracker_update: none
status: complete
---

# consistency-check — handoff summary

## What I did
Validated <feature scope: "the artifacts for `<title>`" | project scope: "project-wide invariants">. Ran <N> checks.

## Artifacts produced
None — consistency-check is read-only.

## Findings
<the full report — errors then warnings, each with location + suggested fix>

## Human action needed?
<If errors: "Yes — <N> errors block downstream work. See suggested fixes.">
<If only warnings: "No — <N> warnings to review; none blocking.">
<If clean: "No — artifacts are consistent.">

## Recommended next step
<If errors: "Resolve the errors (suggested fixes above use /engineer.clarify, /engineer.feature-edit, /engineer.plan), then re-run consistency-check.">
<If clean: "Artifacts consistent — resume the pipeline.">
```

## Read-only contract

consistency-check **never mutates an artifact.** It reports and suggests. Resolution routes to:
- `clarify` — ambiguity / domain-language fixes within one artifact
- `feature-edit` — changes that cascade across artifacts
- `plan` — Charter Check amendments
- manual — frontmatter count corrections, folder renames

## When NOT to use this skill

- You want to *fix* an inconsistency, not just find it → run the suggested fix skill
- You want within-one-artifact ambiguity resolution → that's `clarify`
- You want code risk analysis → that's `crap-analyzer`

## Cross-skill orchestration

consistency-check is read-only and cross-cutting. It reads everything, validates, reports. Downstream resolution is the user's call via `clarify` / `feature-edit` / `plan`.

## References

Foundation contracts (Notion) — the source of every invariant checked here:
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md / acs.md / spec.md / agentic summary schemas, Charter Check, naming, IR pipeline
- [DAE Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — methodology_root, decomposition
- [DAE Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — tracker_ref resolution
