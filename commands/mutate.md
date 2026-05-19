---
name: mutate
description: Run mutation testing to verify test quality. Builds a custom mutation tool or uses an existing framework, runs mutations, and reports the mutation score with surviving mutants.
arguments:
  - name: ARGUMENTS
    description: Optional target path or flags (e.g., "src/auth/" to mutate only auth module)
    required: false
---

Run mutation testing on this project.

## Instructions

1. Check that both test streams are green before proceeding:
   - Run the unit tests
   - Run acceptance tests if a pipeline exists (`./run-acceptance-tests.sh`)
   - If either fails, report the failure and stop — do not mutate against a red baseline

2. Detect the project language and check if a mutation tool exists in the project.
   - **Preferred:** Build a custom mutation tool using TDD — a project-specific
     module that walks the AST, applies mutations one at a time, runs targeted
     tests, and reports survivors. See the `atdd-mutate` skill for the 4-module
     architecture (mutations, runner, core, hashing/selection) and mutation
     categories.
   - **Alternative:** If the user requests a faster setup, install an existing
     framework (Stryker, mutmut, PIT, etc. — see the `atdd-mutate` skill).

3. Configure the tool to:
   - Target source code only (not tests, specs, generated files, or pipeline code)
   - Exclude `generated-acceptance-tests/`, `acceptance-pipeline/`, and `specs/`
   - If `$ARGUMENTS` is provided, scope mutations to that path

4. Run the mutation tool. On the custom-tool path, run `dae_mutmap.py select`
   first and mutate only the changed functions it returns (differential
   mutation testing — see the `atdd-mutate` skill); on the framework path,
   enable the framework's incremental flag.

5. Report results:
   - Mutation score (percentage)
   - Total mutants, killed, survived
   - List each surviving mutant with: file, line, mutation description
   - Assessment: strong (90%+), moderate (70-89%), or weak (<70%)
   - On the custom-tool path, run `dae_mutmap.py update` to refresh
     `mutation-manifest.json`; combine fresh results with cached entries for
     unchanged functions

6. Ask whether to proceed with killing surviving mutants (invoke `/atdd:kill-mutants`)
