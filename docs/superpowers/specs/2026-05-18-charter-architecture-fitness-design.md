# Charter Architecture Fitness Tool — Design (Spec C)

**Date:** 2026-05-18
**Status:** Draft for review
**Scope:** Make the checkable parts of a project's architectural charter an
independent, test-like tool — a fitness function that runs and passes or fails,
rather than prose an agent is asked to honor.

---

## Background

A recurring complaint about agentic coding: agents build fast but produce code
"never unified by any vision." The fix is guard rails — *independent tools the
AI must satisfy*, not rules it is asked to follow. A rule in a prompt or a
charter is soft; the AI rationalizes past it and it erodes under compaction. A
tool is objective: it runs, it reports pass/fail.

DAE already has strong verification tools (acceptance pipeline, mutation,
`crap-analyzer`, `dae_handoff.py`). But the **architectural vision** —
`CHARTER.md` §2 Architecture and §3 Conventions — is still only prose. The
`plan.md` Charter Check and `consistency-check` assess it by AI judgment, never
by an objective check of the actual code. Spec C closes that gap.

This is the "verified_by: tool" principle (Spec A, Foundation §8) applied to
architecture: turn the charter's checkable rules into a real guard rail.

## Decomposition

Spec C is one coherent feature. It is independent of Spec B (test impact
analysis), which remains a separate cycle.

---

## Component 1 — Machine-readable architecture rules

`CHARTER.md` §2/§3 stay prose — the *why* of the architecture. The
*checkable form* goes in a new **`architecture:` section of `.engineer/manifest.yml`**.
This follows the established DAE pattern: charter §7 autonomy prose has its
machine-readable mirror in `manifest.autonomy.path_overrides`. Architecture gets
the same prose-plus-mirror split.

Four rule kinds:

```yaml
architecture:
  layers:                          # dependency / layering rules
    - name: domain
      paths: ["src/domain/**"]
      may_not_import: [infrastructure, web]
    - name: infrastructure
      paths: ["src/infra/**"]
    - name: web
      paths: ["src/web/**"]
  forbidden_patterns:              # banned regexes, scoped to paths
    - pattern: "console\\.log"
      paths: ["src/**"]
      reason: "use the structured logger"
  naming:                          # filename rules
    - paths: ["src/**"]
      filename_must_match: "^[a-z0-9-]+$"
      reason: "kebab-case file names"
  file_size:                       # line-count caps
    max_lines: 400
    overrides:
      - paths: ["**/generated/**"]
        max_lines: 5000
```

Every key is optional — a project enables only the rule kinds it wants. Paths
are gitignore-style globs (the same syntax already locked for
`autonomy.path_overrides`).

**Foundation §2** gains `architecture:` as a documented top-level key.
`dae_resolve.py`'s manifest reader already parses arbitrary nested maps/lists,
so it reads the section without change; `validate_manifest` gains light
structural validation (each `layers[]` entry has `name` + `paths`; `file_size.max_lines`
is a positive int; regexes compile).

## Component 2 — `dae_arch.py`, the fitness checker

A stdlib-only Python script in `engineer/scripts/`, consistent with the
`dae_*.py` family. It reads the `architecture:` rules (via `dae_resolve`), scans
the project, and reports violations.

**Scope:** diff-scoped by default (changed files vs. the base branch, like
`crap-analyzer`), full-scan on `--full`. A violation in unchanged code is not
this PR's regression; full scan is the audit mode.

**The four checks:**

- **`forbidden_patterns`** — for each pattern, grep matching files (paths glob);
  each hit is a violation `file:line`. Language-agnostic.
- **`naming`** — each file under `paths` whose name fails `filename_must_match`
  is a violation. Language-agnostic.
- **`file_size`** — each file over its `max_lines` (nearest matching override,
  else the default) is a violation. Language-agnostic.
- **`layers`** — the meaty check. For each source file, extract its imports,
  resolve each *project-local* import to a file path, map that path to a layer
  (by `paths` glob), and flag any import whose target layer is in the importing
  layer's `may_not_import`. Bare/package imports (external dependencies) are not
  project layers — skipped.

  Import extraction is language-specific. **v1 ships Python and JS/TS:**
  - Python — `import x`, `from x import y`, and `from . import y`; resolve
    project-rooted (`pkg.mod` → `pkg/mod.py`) and relative imports to paths.
  - JS/TS — `import ... from "..."`, `require("...")`, `export ... from "..."`;
    resolve relative specifiers (`./`, `../`) to paths; skip bare specifiers.

  Other languages: a documented extension point — an unrecognized language is
  skipped for layering (its generic checks still run), exactly like
  `crap-analyzer`'s language table.

**Output:** a violations report grouped by rule kind, each line
`file:line — <rule> — <reason>`. **Exit non-zero** if any violation — `dae_arch.py`
is a gate, like a test. `--format json` for machine consumption.

## Component 3 — the `arch-check` skill

A thin engineer-plugin skill, `arch-check`, in `engineer/skills/`. It runs
`dae_arch.py`, presents the violations grouped and worst-kind-first, and emits a
handoff. It does not auto-fix — it reports; the human/agent decides whether each
violation is a real break or a rule that needs amending.

**Pipeline placement:** Checkpoint 7 (Light Verify), alongside `crap-analyzer`.
Architecture fitness is verification of the built code against the charter — the
same tier as change-risk analysis.

## Component 4 — Foundation + Notion updates

- **Foundation Design §2** — add `architecture:` to the manifest schema with the
  four rule kinds.
- **Foundation Design §8 (Checkpoint Exit Contract)** — Checkpoint 7's exit
  criteria gains an architecture-fitness criterion, `verified_by: tool`
  (`dae_arch.py` exits zero).
- **Foundation Design §3** — a note that the charter's architecture/conventions
  prose has its checkable mirror in `manifest.architecture`, and that the
  `plan.md` Charter Check may cite `dae_arch.py` for architecture rows instead of
  pure judgment.

## Component 5 — Testing

- `dae_arch.py` gets a stdlib `unittest` suite (`test_dae_arch.py`), like the
  other scripts: one cluster per check kind, plus layering tests for both Python
  and JS/TS import forms, plus diff-scoping and exit-code tests.
- The `arch-check` skill is a technique/tool skill — its test is that an agent
  given a project with charter violations runs the tool and reports them
  correctly. A light subagent application check, not a discipline pressure test.

---

## Implementation sequencing

1. **Foundation §2** — lock the `architecture:` manifest schema in Notion.
2. **`dae_arch.py`** — built TDD: the three generic checks first (forbidden
   patterns, naming, file size), then the `layers` check (Python, then JS/TS),
   then diff-scoping + the CLI.
3. **`dae_resolve.py`** — light `validate_manifest` validation of `architecture:`.
4. **`arch-check` skill** + its entry gate / handoff per the Spec A contract.
5. **Foundation §8 + §3** Notion updates; Checkpoint 7 exit criterion.

## Open items

- **Layering for more languages** — v1 is Python + JS/TS. Go, Java, Ruby, etc.
  are a post-v1 extension following `crap-analyzer`'s language-table pattern.
- **Topology rules** (monolith vs. services, allowed cross-service calls) are
  not in v1 — `layers` covers intra-repo layering, which is the bulk of the
  value. Topology can be a later rule kind.

## Out of scope

- **Spec B — test impact analysis.** Separate cycle.
- **Auto-fixing violations.** `dae_arch.py` reports; it never edits code.
- **Inferring rules from charter prose.** Rules are authored in the manifest;
  the tool does not parse English out of `CHARTER.md`.
