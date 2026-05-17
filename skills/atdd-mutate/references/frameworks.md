# Mutation Testing Reference

## Preferred Approach: Custom Mutation Tool

The preferred approach is to build a project-specific mutation tool that
walks the AST/source tree, applies one mutation at a time, runs targeted
tests, and reports survivors. This follows the methodology Uncle Bob
developed for [empire-2025](https://github.com/unclebob/empire-2025/blob/master/docs/plans/2026-02-21-mutation-testing.md).

### Architecture

Three modules:

1. **Mutations module** — a rules table mapping original constructs to
   mutants (e.g., `+` → `-`, `true` → `false`, `>=` → `>`), plus
   matching logic that walks the AST/form tree
2. **Runner module** — source-to-test mapping (e.g., `src/foo.ext` →
   `test/foo_test.ext`), executes tests, captures pass/fail
3. **Core module** — orchestration: read source → discover mutation
   sites → apply one at a time → run tests → restore original → report

### Core Mutation Categories

Apply these regardless of language:

| Category | Examples |
|----------|----------|
| Arithmetic | `+` ↔ `-`, `*` ↔ `/`, `++` ↔ `--` |
| Comparison | `>` ↔ `>=`, `<` ↔ `<=` |
| Equality | `==` ↔ `!=` |
| Boolean | `true` ↔ `false`, `&&` ↔ `\|\|` |
| Conditional | `if` ↔ `if-not`, negate conditions |
| Constant | `0` ↔ `1`, `""` ↔ `"mutant"` |
| Return value | return `true` → return `false`, return `null` |
| Void method | remove method call entirely |

**Position-aware matching:** Arithmetic, comparison, and conditional
mutations apply only in operator/function position. Boolean and constant
mutations apply anywhere.

### Building the Tool with TDD

Build the custom mutation tool using the same TDD discipline as the rest
of the ATDD workflow:

1. Write failing tests for the rules table and matching logic
2. Implement rules and matching
3. Write failing tests for source-to-test mapping
4. Implement the runner
5. Write failing tests for orchestration (apply mutation, run, restore)
6. Implement the core module
7. Integration test against a real source file

### Safety

- Hold original file content in memory, restore in `try/finally`
- Run in a worktree or on a clean working tree
- `git checkout` recovers from interruptions

### When Custom is Especially Valuable

- Lisps and homoiconic languages (tree walking is natural)
- Projects with custom or uncommon test runners
- Languages without established mutation frameworks
- When you need targeted test execution (run only affected tests per mutant)

---

## Alternative: Existing Frameworks

When rapid setup matters more than tight integration, use an established
framework. These are secondary options — prefer the custom approach above.

> **Note:** Version numbers below are as of February 2026. Check each
> framework's website for the latest versions before installing.

---

## JavaScript / TypeScript — Stryker

**Website:** https://stryker-mutator.io/

### Install

```bash
npm init stryker@latest
```

Interactive wizard configures the project. Creates `stryker.config.mjs`.

### Configure

```javascript
// stryker.config.mjs
export default {
  mutate: [
    'src/**/*.ts',
    '!src/**/*.spec.ts',
    '!src/**/*.test.ts',
    '!**/.build/**',
    '!acceptance/**'
  ],
  testRunner: 'jest',        // or 'mocha', 'karma', 'vitest'
  reporters: ['html', 'clear-text', 'progress'],
  coverageAnalysis: 'perTest',
  thresholds: { high: 90, low: 70, break: null }
};
```

### Run

```bash
npx stryker run
```

### Key flags

- `--concurrency 4` — parallel mutant workers
- `--logLevel trace` — debug output
- `--mutate "src/auth/**/*.ts"` — target specific files

### Mutation operators

Stryker supports: arithmetic, boolean, conditional, equality, logical,
string literal, array declaration, block statement, optional chaining,
and more.

---

## Python — mutmut

**Website:** https://github.com/boxed/mutmut

### Install

```bash
pip install mutmut
```

### Configure

```ini
# setup.cfg
[mutmut]
paths_to_mutate=src/
tests_dir=tests/
runner=python -m pytest -x
```

Or `pyproject.toml`:

```toml
[tool.mutmut]
paths_to_mutate = "src/"
tests_dir = "tests/"
runner = "python -m pytest -x --tb=no -q"
```

### Run

```bash
mutmut run
```

### Inspect results

```bash
mutmut results              # summary
mutmut show <id>            # show specific surviving mutant
mutmut html                 # generate HTML report
```

### Key flags

- `--paths-to-mutate src/auth/` — target specific directory
- `--runner "pytest -x"` — custom test runner
- `--use-coverage` — only mutate covered lines (faster)

---

## Java — PIT (pitest)

**Website:** https://pitest.org/

### Install (Maven)

```xml
<plugin>
  <groupId>org.pitest</groupId>
  <artifactId>pitest-maven</artifactId>
  <version>1.15.3</version>
  <configuration>
    <targetClasses>
      <param>com.example.*</param>
    </targetClasses>
    <targetTests>
      <param>com.example.*</param>
    </targetTests>
    <excludedClasses>
      <param>com.example.generated.*</param>
    </excludedClasses>
  </configuration>
</plugin>
```

### Install (Gradle)

```groovy
plugins {
    id 'info.solidsoft.pitest' version '1.15.0'
}

pitest {
    targetClasses = ['com.example.*']
    targetTests = ['com.example.*']
    excludedClasses = ['com.example.generated.*']
    mutators = ['DEFAULTS']
    outputFormats = ['HTML']
}
```

### Run

```bash
mvn pitest:mutationCoverage
# or
gradle pitest
```

### Mutation operators

PIT supports: conditionals boundary, increments, invert negatives,
math, negate conditionals, void method calls, return values, and more.

---

## C# — Stryker.NET

**Website:** https://stryker-mutator.io/docs/stryker-net/introduction/

### Install

```bash
dotnet tool install -g dotnet-stryker
```

### Configure

```json
// stryker-config.json
{
  "stryker-config": {
    "project": "MyApp.csproj",
    "test-projects": ["MyApp.Tests.csproj"],
    "mutate": [
      "src/**/*.cs",
      "!src/**/Generated/**"
    ],
    "reporters": ["html", "progress"],
    "thresholds": { "high": 90, "low": 70, "break": 0 }
  }
}
```

### Run

```bash
dotnet stryker
```

---

## Rust — cargo-mutants

**Website:** https://github.com/sourcefrog/cargo-mutants

### Install

```bash
cargo install cargo-mutants
```

### Run

```bash
cargo mutants
```

### Key flags

- `--file src/auth.rs` — target specific file
- `--jobs 4` — parallel workers
- `-d target/mutants` — output directory
- `--exclude "generated_*"` — exclude patterns

### Interpret results

```bash
cargo mutants --list          # preview mutations without running
```

---

## Go — go-mutesting

**Website:** https://github.com/zimmski/go-mutesting

### Install

```bash
go install github.com/zimmski/go-mutesting/cmd/go-mutesting@latest
```

### Run

```bash
go-mutesting ./...
```

### Key flags

- `--do-not-remove-tmp-folder` — keep mutations for inspection
- `--match "auth"` — target specific packages

---

## Ruby — mutant

**Website:** https://github.com/mbj/mutant

### Install

```bash
gem install mutant
# or add to Gemfile
gem 'mutant-rspec'
```

### Run

```bash
bundle exec mutant run --include lib --require my_app --use rspec 'MyApp*'
```

### Key flags

- `--since main` — only mutate changes since branch
- `--jobs 4` — parallel workers
- `--fail-fast` — stop on first surviving mutant

---

## Scala — Stryker4s

**Website:** https://stryker-mutator.io/docs/stryker4s/getting-started/

### Install (sbt)

```scala
// project/plugins.sbt
addSbtPlugin("io.stryker-mutator" % "sbt-stryker4s" % "0.16.1")
```

### Configure

```scala
// stryker4s.conf
stryker4s {
  mutate = ["src/main/scala/**/*.scala"]
  test-filter = ["com.example.*"]
}
```

### Run

```bash
sbt stryker
```

---

## Clojure — Custom or pitest

Clojure projects have two options:

### Option A: Custom Mutation Tool (Uncle Bob's Approach)

Build a project-specific mutation tool that walks Clojure form trees using
`postwalk`, applies mutations one at a time, and runs targeted specs. This
is the approach Uncle Bob uses in [empire-2025](https://github.com/unclebob/empire-2025/blob/master/docs/plans/2026-02-21-mutation-testing.md).

**When to use:** When the project uses Speclj or another Clojure-native
test framework, and you want tight integration with the source structure.

Architecture (3 namespaces):
- `mutations` — rules table + matching logic
- `runner` — shell execution + source-to-spec mapping
- `core` — orchestration + CLI entry point

Core mutation rules:

| Category | Original | Mutant |
|----------|----------|--------|
| Arithmetic | `+` `-` `*` `inc` `dec` | swapped counterparts |
| Comparison | `>` `>=` `<` `<=` | boundary shifts |
| Equality | `=` `not=` | swapped |
| Boolean | `true` `false` | swapped |
| Conditional | `if`/`if-not` `when`/`when-not` | swapped |
| Constant | `0` `1` | swapped |

**Important:** Position-aware matching — arithmetic/comparison/conditional
mutations apply only in function position (first element of a list).
Boolean and constant mutations apply anywhere.

### Option B: pitest via lein-pitest

```clojure
;; project.clj
:plugins [[lein-pitest "0.1.1"]]
:pitest {:target-classes ["empire.*"]
         :target-tests  ["empire.*-spec"]}
```

```bash
lein with-profile +pitest pitest
```

---

## General Configuration Tips

### Exclude patterns

Always exclude from mutation:

- `.build/` — generated tests and IR (pipeline output)
- `acceptance/` — the project-specific generator and step handlers
- Test files themselves
- Configuration files
- Migration files

### Performance

Mutation testing is slow. Optimization strategies:

1. **Use coverage data** — only mutate lines covered by tests
2. **Target specific files** — mutate changed files, not the whole project
3. **Incremental runs** — some frameworks cache previous results
4. **Parallel execution** — use available CPU cores

### CI Integration

For continuous integration, consider:

- Running full mutation testing nightly (slow)
- Running incremental mutations on PRs (fast, changed files only)
- Setting a threshold that fails the build if mutation score drops
