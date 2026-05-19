# Differential mutation testing — the manifest contract

Mutation testing re-runs the suite once per mutant, per function. Differential
mutation testing re-mutates only the functions whose **code**, **covering
tests**, or **mutation operator set** changed since the last run — reusing
cached results for everything else. It is the mutation-testing sibling of
`dae_impact.py` (test impact analysis).

This contract covers the **custom-tool path**. The framework path (Stryker,
PIT, mutmut) uses the framework's own native incremental mode instead — see the
`atdd-mutate` skill.

## The manifest — `mutation-manifest.json`

A committed file beside the project's custom mutation tool (not in `.build/`).
Committing it means the saving reaches CI, fresh clones, and every developer —
not just one machine. It is safe to commit: `select` always compares current
hashes against it, so a stale or badly-merged entry is simply re-mutated, never
wrongly skipped.

    {
      "manifest_version": 1,
      "rules_hash": "<hash of the active mutation operator set>",
      "functions": {
        "src/pricing.py::apply_discount": {
          "code_hash": "<AST-level hash of the function>",
          "tests_hash": "<hash of the function's covering unit tests>",
          "last_mutated": "2026-05-19",
          "mutants_total": 12,
          "mutants_killed": 11,
          "survivors": [{"line": 42, "mutation": ">= -> >", "equivalent": false}]
        }
      }
    }

The manifest is a **result cache**, not just a skip-list — a skipped function's
score and survivors come straight from it, so the report is always complete. It
also carries equivalent-mutant triage (`equivalent: true`), so a human's
"ignore this one" decision survives across runs.

## Re-mutate when any of three things changed

1. **code_hash** — the function's code, hashed at the AST level so comments and
   formatting do not count.
2. **tests_hash** — the unit tests covering the function. A weakened or deleted
   test can resurrect a killed mutant; hashing only the function would miss it.
   Default granularity is module-level.
3. **rules_hash** — the mutation operator set. New operators invalidate every
   cached result; a `rules_hash` mismatch forces a full re-mutation.

When differential analysis cannot prove a function safe to skip — no manifest,
unknown function, `manifest_version` or `rules_hash` mismatch — it mutates it. A
false skip hides a test-quality regression; a false mutate only costs time.

## `dae_mutmap.py` — the portable select/update logic

The custom tool supplies function extraction, hashing, and mutation execution
(language-specific). `dae_mutmap.py` owns the manifest format and the decision
logic (generic). Run `dae_mutmap.py --help` for the CLI.

- **`select <manifest> <hashes-feed>`** — prints the function IDs to mutate, one
  per line, or the token `ALL`. `--full` forces `ALL`.
- **`update <manifest> <hashes-feed> <results-feed>`** — rewrites the manifest:
  fresh entries for re-mutated functions, cached entries for skipped ones,
  orphaned IDs pruned. Serialization is deterministic — function IDs sorted,
  dict keys sorted, survivors within an entry sorted by `(line, mutation)`, one
  function per line — so independent updates merge without conflict.

The **hashes feed** is `{"rules_hash": "...", "functions": {id: {"code_hash":
..., "tests_hash": ...}}}` for every current function. The **results feed** is
`{"functions": {id: {"last_mutated": ..., "mutants_total": ...,
"mutants_killed": ..., "survivors": [...]}}}` for the functions actually mutated
this run.

## The 4th module

The custom tool's architecture gains a **Hashing/Selection module** alongside
Mutations, Runner, and Core: it hashes each function (AST-level) and its
covering tests (from the Runner's source-to-test map), calls `dae_mutmap.py
select` before the run, and `dae_mutmap.py update` after.
