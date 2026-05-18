# Test Impact Analysis — Design (Spec B)

**Date:** 2026-05-18
**Status:** Draft for review
**Scope:** Speed the acceptance-pipeline inner loop — when code changes, run
only the scenarios the change affects, not the whole suite.

---

## Background

Uncle Bob, running a multi-agent swarm: *"As the number of testing scenarios
has increased, the testing procedures have gotten quite slow. The continual
retesting is very inefficient. I'm going to have to implement impact analysis
to drive the tests so that only the things that have changed are tested."*

The DAE acceptance pipeline is `spec.md` → `dae_gherkin.py` → IR
(`.build/spec.json`) → a project-specific generator → one generated test per
scenario → run. Today every change re-runs every scenario. Test impact analysis
(TIA) maps changed source files to the scenarios that exercise them and runs
only those — during iteration. The full suite still runs at the gate.

**The safety property — non-negotiable:** TIA must never *skip* a scenario a
change actually affects. When the analysis cannot prove a scenario is safe to
skip, it runs everything. A false "skip" is a missed regression; a false "run"
only costs time.

## Decomposition

Spec B is one coherent feature, independent of Spec A and Spec C.

---

## Component 1 — `dae_impact.py`, the map + selector

A stdlib-only Python script in `engineer/scripts/`, shipped and portable like
`dae_gherkin.py` — **language-agnostic**. It owns the impact map and the
selection logic; it never collects coverage itself (that is framework-specific —
Component 2).

**The map — `features/NNN-slug/.build/impact-map.json`:**

```json
{
  "built_at": "2026-05-18T1530",
  "scenario_hashes": { "<scenario id>": "<hash of the scenario's IR>" },
  "file_map": { "<source file>": ["<scenario id>", ...] }
}
```

- `scenario id` — the scenario's name from the IR (one `spec.md` = one feature,
  so scenario names are unique within it).
- `scenario_hashes` — a content hash of each scenario's IR (steps + examples).
  Lets `select` detect new and spec-changed scenarios precisely.
- `file_map` — the reverse index: source file → scenarios whose test touched it.

**Two modes:**

- **`build <feature-dir> <coverage-feed.json>`** — reads the IR
  (`.build/spec.json`) to compute `scenario_hashes`, reads a normalized coverage
  feed to build `file_map`, writes `impact-map.json`. The coverage feed is a
  fixed JSON shape — `[{"scenario": "<id>", "files": ["src/a.py", ...]}, ...]` —
  produced by the project's runner (Component 2). `dae_impact.py` does not care
  how coverage was collected.
- **`select <feature-dir>`** — reads `impact-map.json`, the current IR, and
  `git diff` changed files. Outputs the scenario IDs to run:
  - **new / spec-changed scenarios** — current IR scenario whose hash is absent
    from or differs from `scenario_hashes` → always selected.
  - **code-impacted scenarios** — for each changed source file present in
    `file_map`, its mapped scenarios.
  - **safety fallback** — a missing/unreadable map, **or** a changed source file
    absent from `file_map` (a new file, or a stale map) → output the token
    `ALL`. Better to run everything than risk skipping a regression.
  Output: a newline list of scenario IDs, or `ALL`. `--format json` available.

## Component 2 — pipeline-builder integration

The *framework-specific* half — coverage attribution differs per test framework,
so it belongs to the project-specific generator, consistent with the post-Spec-A
division of labor (`pipeline-builder` builds the project-specific pipeline;
`dae_gherkin.py`/`dae_impact.py` are the portable shipped front end).

`pipeline-builder` gains two responsibilities for the generated runner:

- **coverage-collection mode** — run the acceptance scenarios under the
  project's coverage tool, attribute coverage per scenario, and emit the
  normalized coverage feed for `dae_impact.py build`. (Most frameworks support
  per-test coverage contexts; otherwise run each scenario's generated test file
  under coverage and snapshot the covered files.)
- **impact-run mode** — call `dae_impact.py select`, then run only the selected
  generated tests (or all, on `ALL`).

`pipeline-builder`'s instructions and the `atdd` skill's pipeline section
document these modes.

## Component 3 — loop placement

TIA accelerates the **inner development loop** — Checkpoint 5, the TDD
iteration, where the same scenarios are run repeatedly. It is an optimization
with a safe full-run fallback.

The **full** acceptance run is unchanged at: the Checkpoint 5 *exit gate* (its
exit criterion is "acceptance tests cover all spec scenarios" — that means a
full green run), and all verification (Checkpoints 7–8). TIA never replaces the
gate; it speeds the iteration between gates. The map is rebuilt as a side effect
of each full run.

## Component 4 — Foundation + manifest

- **Foundation §7** — a note that `.build/impact-map.json` is a generated
  artifact (gitignored with the rest of `.build/`), and that the impact map is
  rebuilt on every full acceptance run.
- **Manifest** — an optional `acceptance.impact_analysis: on | off` flag
  (default `off` — TIA is opt-in; small projects do not need it). `dae_resolve`
  reads it; the generated runner consults it.

## Component 5 — testing

`dae_impact.py` gets a stdlib `unittest` suite (`test_dae_impact.py`): map build
from a coverage feed, selection by changed file, new-scenario detection,
spec-changed (hash mismatch) detection, the stale-map / unmapped-file `ALL`
fallback.

---

## Implementation sequencing

1. **`dae_impact.py`** — built TDD: the scenario-hash + map-build first, then
   `select` with the safety fallback, then the CLI.
2. **`dae_resolve.py`** — read the optional `acceptance.impact_analysis` flag
   (light validation: enum `on | off`).
3. **`pipeline-builder` agent** — document the coverage-collection and
   impact-run runner modes.
4. **`atdd` skill** — document the TIA inner-loop in the pipeline section.
5. **Foundation §7** Notion note; optional manifest flag in §2.

## Open items

- **Per-scenario coverage granularity** — v1 attributes coverage at scenario
  granularity. If a framework only gives file-level test coverage, the runner
  runs one scenario's test file at a time to build the feed; slower map-build,
  same selection precision.
- **Multi-feature selection** — v1 is per-feature (`select <feature-dir>`).
  A project-wide impact run across feature folders is a post-v1 extension.

## Out of scope

- **Collecting coverage itself.** `dae_impact.py` consumes a normalized feed;
  per-framework coverage attribution is `pipeline-builder`'s generated runner.
- **Unit-test impact analysis.** Spec B is the acceptance pipeline. Unit-test
  selection is the project test runner's concern.
- **Replacing the full-run gate.** TIA is an inner-loop optimization only.
