# Coverage toolchain discovery

When no coverage file exists, introspect the repo to figure out how to generate one. **Prefer the repo's own script over running the test runner directly** — it will be wired up with the right config, paths, and formats.

Before running anything, ask: *"No coverage file found. Want me to run tests with coverage? (This may take a few minutes.)"* Only proceed on yes. If the user declines, run the analyzer with coverage=0% and call out the limitation in the report header.

## Detection signals (quick lookup)

Read the repo root once. The **first match wins**; multiple can coexist in polyglot repos — handle each ecosystem separately for the files it owns.

| Signal | Ecosystem | Runner |
|---|---|---|
| `package.json` with `scripts.coverage` or `scripts["test:coverage"]` | JS/TS | Use that script verbatim |
| `jest.config.*` or `"jest"` key in `package.json` | JS/TS | Jest |
| `vitest.config.*` or `vitest` in `devDependencies` | JS/TS | Vitest |
| `nx.json` | JS/TS monorepo | Nx |
| `karma.conf.*` or `@angular-devkit/build-angular:karma` in `angular.json` | JS/TS (Angular) | Karma |
| `.nycrc*` or `nyc` in `package.json` | JS/TS | nyc/istanbul |
| `pyproject.toml [tool.pytest.*]` / `[tool.coverage.*]`, or `pytest.ini` | Python | pytest + coverage.py |
| `tox.ini` | Python | tox |
| `pom.xml` with JaCoCo plugin | Java | Maven + JaCoCo |
| `build.gradle*` with `jacoco` plugin | Java/Kotlin | Gradle + JaCoCo |
| `go.mod` | Go | `go test -coverprofile=...` |
| `Gemfile` with `rspec` / `simplecov` | Ruby | RSpec + SimpleCov |
| `Cargo.toml` | Rust | `cargo llvm-cov` or `cargo tarpaulin` |
| `*.csproj` with `coverlet.*` | C# | `dotnet test --collect` |
| `composer.json` with `phpunit` | PHP | PHPUnit |
| `Makefile` / `justfile` / `Taskfile.yml` with a `coverage` target | Any | Prefer the repo's own target |

**Always prefer the repo's own coverage script** when it exists — it's the maintainer's canonical command and is likely wired into CI. Per-ecosystem commands are in the sections below.

## Coverage formats the analyzer parses

Auto-discovery walks `coverage/` and the repo root looking for:

| Format | Typical path | Emitted by |
|---|---|---|
| **lcov** (`lcov.info`) | `coverage/lcov.info`, `coverage/<project>/lcov.info` | Jest, Vitest, nyc, Karma, simplecov-lcov, `cargo llvm-cov` |
| **Cobertura XML** | `coverage.xml`, `coverage/cobertura-coverage.xml` | coverage.py, coverlet, phpunit, gocover-cobertura |
| **JaCoCo XML** | `target/site/jacoco/jacoco.xml`, `build/reports/jacoco/test/jacocoTestReport.xml` | Maven, Gradle (Java/Kotlin) |
| **Clover XML** | `coverage.xml`, `clover.xml` | PHPUnit, nyc |
| **Go coverage** | `coverage.out` | `go test -coverprofile=...` |
| **coverage.py JSON** | `coverage.json` | `coverage json` |

Pass `--lcov <path>` to override auto-discovery (flag name is historical — it accepts any supported format).

## The golden order

1. **Read the project's own coverage script.** If one of these exists, use it verbatim — the maintainer has already decided what "coverage" means here:
   - `package.json` → `scripts.coverage`, `scripts["test:coverage"]`, `scripts["test:cov"]`
   - `Makefile` → `coverage`, `test-coverage`, `cov`
   - `justfile` → `coverage`, `cov`
   - `Taskfile.yml` → `coverage` task
   - `pyproject.toml` → `[tool.poetry.scripts]` or `[tool.hatch.envs.*.scripts]` with `cov` / `coverage`
   - Repo README — scan for a section titled "Testing" / "Coverage" / "Running tests"

2. **If no explicit script, detect the test framework and invoke it with the standard coverage flag.** Scope to changed files when the runner supports it.

3. **Emit output in a format the analyzer understands.** If a runner can produce multiple formats, pick lcov or Cobertura XML — the analyzer parses both well.

## By ecosystem

### JavaScript / TypeScript

| Signal | Command | Output |
|---|---|---|
| Jest (`jest.config.*` or `"jest"` in `package.json`) | `npx jest --coverage --coverageReporters=lcov` | `coverage/lcov.info` |
| Jest scoped | `npx jest --coverage --findRelatedTests <files>` | `coverage/lcov.info` |
| Vitest (`vitest.config.*`) | `npx vitest run --coverage --coverage.reporter=lcov` | `coverage/lcov.info` |
| Karma + Angular CLI | `npx ng test --watch=false --code-coverage` | `coverage/<project>/lcov.info` |
| Nx (`nx.json`) | `npx nx test <project> --coverage` | `coverage/<project>/lcov.info` |
| Mocha + nyc | `npx nyc --reporter=lcov mocha` | `coverage/lcov.info` |
| c8 (native V8 coverage) | `npx c8 --reporter=lcov <test-cmd>` | `coverage/lcov.info` |

If `angular.json` specifies `karma` but tests can't be run headlessly (e.g. no Chrome installed), fall back to running the analyzer with coverage=0% and flag it.

### Python

| Signal | Command | Output |
|---|---|---|
| pytest (`pyproject.toml [tool.pytest.*]` / `pytest.ini`) | `pytest --cov=<pkg> --cov-report=xml` | `coverage.xml` (Cobertura) |
| pytest + scoped | `pytest --cov=<pkg> --cov-report=xml tests/test_changed.py` | `coverage.xml` |
| coverage.py standalone | `coverage run -m <module> && coverage xml` | `coverage.xml` |
| JSON output | `coverage json` | `coverage.json` |
| tox | `tox -e coverage` (if defined) | depends on env |

When in doubt, prefer Cobertura XML (`--cov-report=xml`) — most universal, the analyzer parses it directly.

### Java / Kotlin

| Signal | Command | Output |
|---|---|---|
| Maven + JaCoCo plugin (`pom.xml`) | `mvn test` (JaCoCo binds to `test` phase by default) | `target/site/jacoco/jacoco.xml` |
| Gradle + jacoco plugin | `./gradlew test jacocoTestReport` | `build/reports/jacoco/test/jacocoTestReport.xml` |
| Kotlin + Kover | `./gradlew koverXmlReport` | `build/reports/kover/report.xml` (Cobertura-like) |

JaCoCo reports are per-module in multi-module projects; the analyzer auto-picks one match but for polyglot/multi-module repos you may need to pass `--lcov` (flag name is historical — accepts any format) explicitly.

### Go

| Signal | Command | Output |
|---|---|---|
| `go.mod` | `go test -coverprofile=coverage.out ./...` | `coverage.out` (Go's native text format) |
| Scoped | `go test -coverprofile=coverage.out ./pkg/affected/...` | `coverage.out` |

The analyzer reads `coverage.out` natively.

### Ruby

| Signal | Command | Output |
|---|---|---|
| RSpec + simplecov (in `Gemfile`) | `bundle exec rspec` (SimpleCov auto-loads via `spec_helper.rb`) | `coverage/.resultset.json` + `coverage/coverage.json` |
| simplecov-lcov | `bundle exec rspec` with `SimpleCov::Formatter::LcovFormatter` | `coverage/lcov/lcov.info` |

For the analyzer, prefer the `simplecov-lcov` formatter. If the repo doesn't have it, install temporarily or emit `coverage.json` (the script parses coverage.py JSON — SimpleCov's JSON is close but not identical; lcov is the safer bet).

### Rust

| Signal | Command | Output |
|---|---|---|
| `Cargo.toml` + `cargo-llvm-cov` | `cargo llvm-cov --lcov --output-path coverage/lcov.info` | `coverage/lcov.info` |
| `cargo-tarpaulin` | `cargo tarpaulin --out Xml` | `cobertura.xml` |

If neither tool is installed, suggest `cargo install cargo-llvm-cov` (preferred — it uses LLVM source-based coverage, more accurate).

### C# / .NET

| Signal | Command | Output |
|---|---|---|
| `*.csproj` with `coverlet.*` | `dotnet test --collect:"XPlat Code Coverage"` | `TestResults/<guid>/coverage.cobertura.xml` |
| Scoped | `dotnet test <Project.csproj> --collect:"XPlat Code Coverage" --filter FullyQualifiedName~<ClassName>` | same |

The output path has a GUID; pass it explicitly via `--lcov` after finding it: `find TestResults -name coverage.cobertura.xml | head -1`.

### PHP

| Signal | Command | Output |
|---|---|---|
| PHPUnit (`phpunit.xml*`) + Xdebug or PCOV | `vendor/bin/phpunit --coverage-clover=clover.xml` | `clover.xml` |
| Cobertura | `vendor/bin/phpunit --coverage-cobertura=coverage.xml` | `coverage.xml` |

Coverage requires either the Xdebug or PCOV PHP extension; if neither is loaded, surface that — `phpunit --coverage-*` will fail with "No code coverage driver available".

## Scoping to changed files

Scoping reduces runtime but isn't always worth it. A 30-second unscoped suite beats a 5-minute argument about which projects are affected.

| Runner | Scoping approach | Quality |
|---|---|---|
| Jest / Vitest | `--findRelatedTests <files>` | Good — walks import graph |
| Nx | `nx affected --target=test --coverage` | Good — uses project graph |
| pytest | Pass changed test file paths, or use `--lf` (last-failed) | Manual |
| Go | Pass affected package paths (`./pkg/a/... ./pkg/b/...`) | Good |
| JaCoCo (Maven/Gradle) | `-pl <module>` for multi-module | Module-level only |
| Karma | Not really — runs all specs in the project | Poor |
| RSpec | Pass changed `*_spec.rb` files | Manual |

## When running tests fails

- Missing dependency or runner (`command not found`) → surface the exact install command and stop.
- Tests fail before producing coverage → show the failures first. CRAP analysis on broken tests is noise; address the failures first.
- External services required (DB, cache, message queue) that aren't running → surface this, don't try to start them.
- Runtime > 10 minutes → ask user to confirm continuation or fall back to coverage=0%.

## When to skip running tests entirely

- User declined.
- No test configuration found.
- Coverage tooling missing (e.g. PHP without Xdebug/PCOV, Rust without cargo-llvm-cov) and installing would require root / a long toolchain setup.
- The changed files are all in test directories (nothing to measure).

In all these cases, run the analyzer with coverage=0% and call out the limitation in the report header.
