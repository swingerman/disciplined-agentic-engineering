# crap-analyzer

Claude Code plugin that analyzes recently-changed code for **Change Risk Anti-Patterns (CRAP)** and proposes fixes.

```
CRAP(m) = comp(m)² × (1 − cov(m))³ + comp(m)
```

High CRAP = complex **and** under-tested. This plugin flags the worst offenders in a diff, then offers refactors and test stubs one at a time.

## What it does

1. **Scopes to a diff.** Any diff — `gh pr diff`, `git diff --merge-base main`, staged changes, or a named file list.
2. **Auto-discovers coverage.** Reads the repo's own `coverage` script (`package.json`, `pyproject.toml`, `Makefile`, etc.) or detects the framework (Jest, Vitest, pytest, JaCoCo, Go, RSpec, cargo-llvm-cov, coverlet, PHPUnit…). Parses lcov, Cobertura XML, JaCoCo XML, Clover XML, Go `coverage.out`, or coverage.py JSON.
3. **Ranks findings worst-first** with a markdown report.
4. **Proposes fixes** per finding: extract-method / guard-clause refactors as unified diffs, plus framework-appropriate test stubs.
5. **Safe refactors** (no behavior change) can be auto-applied one at a time after confirmation.

## Supported languages

TypeScript, JavaScript, Python, Java, Kotlin, Go, Ruby, C#, Rust, PHP.

## Usage

Trigger with any of:

- `analyze CRAP`
- `check code risk on this branch`
- `run /crap-analyzer`
- `find risky methods in this PR`

The plugin will prompt before running any tests or applying any edits.

## Config

Optional `.crap-analyzer.json` at repo root:

```json
{ "threshold": 20 }
```

Default threshold is 20 — functions below that score don't get reported.
