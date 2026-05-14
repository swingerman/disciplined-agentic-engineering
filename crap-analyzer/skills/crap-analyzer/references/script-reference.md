# `compute_crap.py` reference

The analyzer is zero-dependency Python — runs on any `python3`.

```bash
python3 <skill-dir>/scripts/compute_crap.py --diff - --repo-root <repo> --threshold <N> --format both
```

## Flags

| Flag | Description |
|---|---|
| `--diff PATH\|-` | Unified diff to analyze. `-` reads stdin. Required. |
| `--repo-root DIR` | Repository root (default: cwd). |
| `--lcov PATH` | Explicit coverage file (any supported format — flag name is historical). Auto-discovered if omitted. |
| `--threshold N` | Minimum CRAP score to report (default: 20). |
| `--format json\|md\|both` | Output format. `both` prints JSON to stdout, markdown to stderr. |

## Supported source extensions

`.ts` `.tsx` `.js` `.jsx` `.mjs` `.cjs` `.py` `.java` `.kt` `.kts` `.go` `.rb` `.cs` `.rs` `.php`

Test files are skipped automatically: `*.spec.*`, `*.test.*`, `test_*.py`, `*_test.go`, `*Test.java`, `*Tests.{cs,java,kt,kts}`, `*Spec.{java,kt,kts}`, `*_spec.rb`, anything under `tests/`, `*.d.ts`.

## Output JSON shape

```json
{
  "threshold": 30.0,
  "coverage_file": "/abs/path/to/lcov.info",
  "coverage_format": "lcov",
  "findings": [
    {
      "file": "src/app/foo.py",
      "name": "do_thing",
      "kind": "function",
      "language": "python",
      "start_line": 42,
      "end_line": 87,
      "complexity": 15,
      "coverage": 0.5,
      "executable_lines": 16,
      "covered_lines": 8,
      "crap": 43.12
    }
  ]
}
```

`findings` is sorted by `crap` descending.

## Accuracy caveats

The script uses regex-based heuristics, not real parsers. That means:

- Decision points inside string interpolations (`${a ?? b}`, f-strings) aren't counted.
- Deeply nested closures/lambdas may confuse function-boundary detection in edge cases.
- Language-specific subtleties (Python decorators with arguments, Kotlin `when` arms, Go type switches) are counted best-effort.
- Generated code, heavy macro usage, and DSL-like code may be miscounted.

Close enough to rank findings. If a specific score looks wrong, read the function and trust your eyes.
