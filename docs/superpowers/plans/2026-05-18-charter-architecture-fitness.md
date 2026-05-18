# Charter Architecture Fitness Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `dae_arch.py` — an independent, test-like checker for the charter's architectural rules — plus its manifest schema and an `arch-check` skill.

**Architecture:** Machine-readable architecture rules live in a new `architecture:` section of `.engineer/manifest.yml`. A stdlib Python script `dae_arch.py` reads them, scans the project (diff-scoped by default), and reports violations of four rule kinds — forbidden patterns, naming, file size, and dependency layering — exiting non-zero on any violation. A thin `arch-check` skill wraps it at Checkpoint 7.

**Tech Stack:** Python 3 stdlib only (matches the existing `engineer/scripts/` family — no third-party deps), Markdown skill/Notion files.

**Source spec:** `docs/superpowers/specs/2026-05-18-charter-architecture-fitness-design.md`

---

## Orientation for the engineer

- `engineer/scripts/` holds stdlib-only Python scripts, each with a `test_*.py` sibling. Run all tests: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`.
- `dae_resolve.py` resolves the methodology root and parses `.engineer/manifest.yml`. It exposes `resolve(start_dir)` → a result dict with a `"manifest"` key, and `find_methodology_root(start_dir)`.
- A **violation** is the tuple `(file, line, kind, message)` — `file` is repo-relative, `line` is an int (`0` when not line-specific), `kind` is the rule kind, `message` is human-readable.
- Never push. Commit locally per task. Notion edits use the Notion MCP (`notion-fetch`, `notion-update-page`); the Foundation Design page id is `3585ecde-e0e2-811b-bc67-ff4913c03207`.

## File structure

- `engineer/scripts/dae_arch.py` — the checker (one file: glob helpers, scope, four checks, audit, CLI).
- `engineer/scripts/test_dae_arch.py` — its stdlib `unittest` suite.
- `engineer/scripts/dae_resolve.py` — *modified*: `validate_manifest` gains light `architecture:` validation.
- `engineer/skills/arch-check/SKILL.md` — *new* skill.
- Notion: Foundation Design §2, §3, §8.

---

## Phase 1 — Lock the manifest schema (Notion)

### Task 1: Add the `architecture:` section to Foundation Design §2

**Files:**
- Modify (Notion): Foundation Design page `3585ecde-e0e2-811b-bc67-ff4913c03207`, Section 2

- [ ] **Step 1: Fetch the page**

Run (Notion MCP): `notion-fetch` id `3585ecde-e0e2-811b-bc67-ff4913c03207`. Locate Section 2's manifest YAML example and its "Decisions locked" list.

- [ ] **Step 2: Add the `architecture:` block to the manifest example**

In Section 2's manifest YAML example, after the `autonomy:` block and before `# Agentic summary contract`, insert:

```yaml
# Architecture fitness rules (Checkpoint 7; dae_arch.py)
architecture:
  layers:                            # dependency / layering rules
    - name: domain
      paths: ["src/domain/**"]
      may_not_import: [infrastructure, web]
    - name: infrastructure
      paths: ["src/infra/**"]
  forbidden_patterns:                # banned regexes, scoped to paths
    - pattern: "console\\.log"
      paths: ["src/**"]
      reason: "use the structured logger"
  naming:                            # filename rules
    - paths: ["src/**"]
      filename_must_match: "^[a-z0-9-]+$"
      reason: "kebab-case file names"
  file_size:
    max_lines: 400
    overrides:
      - paths: ["**/generated/**"]
        max_lines: 5000
```

- [ ] **Step 3: Add to Section 2 "Decisions locked"**

Append this bullet to Section 2's "Decisions locked" list:

```markdown
- **`architecture:`** is the optional machine-readable mirror of the charter's
  §2/§3 architecture & conventions prose — consumed by `dae_arch.py` at
  Checkpoint 7. Four rule kinds: `layers`, `forbidden_patterns`, `naming`,
  `file_size`. Every key is optional. Paths use the gitignore-style globs.
```

- [ ] **Step 4: Verify**

Run (Notion MCP): `notion-fetch` id `3585ecde-e0e2-811b-bc67-ff4913c03207`. Expected: Section 2 shows the `architecture:` block and the new bullet.

- [ ] **Step 5: No commit** — Notion is not under git. Proceed.

---

## Phase 2 — `dae_arch.py`

### Task 2: Glob matching + file scoping

**Files:**
- Create: `engineer/scripts/dae_arch.py`
- Test: `engineer/scripts/test_dae_arch.py`

- [ ] **Step 1: Write the failing test**

Create `engineer/scripts/test_dae_arch.py`:

```python
#!/usr/bin/env python3
"""Tests for dae_arch — the charter architecture fitness checker.

Run: python3 -m unittest test_dae_arch -v
"""
import os
import shutil
import tempfile
import unittest

import dae_arch as da


class TestGlob(unittest.TestCase):
    def test_star_within_segment(self):
        rx = da._glob_to_regex("src/*.py")
        self.assertTrue(rx.match("src/a.py"))
        self.assertFalse(rx.match("src/sub/a.py"))

    def test_double_star_spans_segments(self):
        rx = da._glob_to_regex("src/**/*.py")
        self.assertTrue(rx.match("src/a.py"))
        self.assertTrue(rx.match("src/x/y/a.py"))
        self.assertFalse(rx.match("lib/a.py"))

    def test_match_any(self):
        globs = da._compile_globs(["src/**", "lib/**"])
        self.assertTrue(da._match_any("src/x/y.py", globs))
        self.assertTrue(da._match_any("lib/z.py", globs))
        self.assertFalse(da._match_any("test/z.py", globs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_arch -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dae_arch'`

- [ ] **Step 3: Write `dae_arch.py` with the glob + scope helpers**

Create `engineer/scripts/dae_arch.py`:

```python
#!/usr/bin/env python3
"""dae_arch.py — charter architecture fitness checker.

Reads the `architecture:` section of .engineer/manifest.yml and checks the
project against it: dependency layering, forbidden patterns, file naming, and
file size. Reports violations and exits non-zero if any are found — it is a
gate, like a test.

Usage:
  dae_arch.py [START_DIR]            check changed files vs. the base branch
  dae_arch.py --full [START_DIR]     check every tracked file
  dae_arch.py --format json [...]    machine-readable output

Exit codes:
    0  no violations
    1  violations found
    2  no manifest / no architecture section
    3  usage error
"""
import json
import os
import re
import subprocess
import sys

import dae_resolve

SOURCE_EXTENSIONS = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


def _glob_to_regex(pattern):
    """Compile a gitignore-style path glob to an anchored regex.

    `**` spans path segments (including zero); `*` and `?` stay within one.
    """
    out = []
    i = 0
    while i < len(pattern):
        if pattern[i:i + 2] == "**":
            out.append(".*")
            i += 2
            if i < len(pattern) and pattern[i] == "/":
                i += 1  # `**/` also matches zero directories
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _compile_globs(patterns):
    """A list of glob strings -> a list of compiled regexes."""
    return [_glob_to_regex(p) for p in patterns]


def _match_any(path, compiled_globs):
    """True if `path` matches any compiled glob (empty list -> matches all)."""
    if not compiled_globs:
        return True
    return any(g.match(path) for g in compiled_globs)


def _git(root, *args):
    """Run a git command in `root`; return stdout text ('' on failure)."""
    try:
        out = subprocess.run(["git", "-C", root, *args],
                             capture_output=True, text=True, check=True)
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def files_in_scope(root, full):
    """Repo-relative source file paths to check.

    full=False -> files changed vs. the base branch's merge-base; full=True ->
    every tracked file. Only SOURCE_EXTENSIONS are returned.
    """
    if full:
        names = _git(root, "ls-files").splitlines()
    else:
        base = (_git(root, "rev-parse", "--abbrev-ref",
                     "origin/HEAD").strip() or "origin/main")
        names = _git(root, "diff", "--name-only", "--merge-base",
                     base).splitlines()
        if not names:
            names = _git(root, "ls-files").splitlines()  # no diff -> full
    return [n for n in names if n.endswith(SOURCE_EXTENSIONS)]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_arch -v`
Expected: PASS — 3 tests OK

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_arch.py engineer/scripts/test_dae_arch.py
git commit -m "feat: dae_arch.py — glob matching + file scoping"
```

### Task 3: The three generic checks

**Files:**
- Modify: `engineer/scripts/dae_arch.py`
- Test: `engineer/scripts/test_dae_arch.py`

- [ ] **Step 1: Write the failing test** — add to `test_dae_arch.py`:

```python
def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class TestGenericChecks(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_forbidden_pattern_hit(self):
        _write(self.root, "src/a.py", "x = 1\nconsole.log(x)\n")
        rules = [{"pattern": r"console\.log", "paths": ["src/**"],
                  "reason": "use the logger"}]
        v = da.check_forbidden(self.root, ["src/a.py"], rules)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][0], "src/a.py")
        self.assertEqual(v[0][1], 2)
        self.assertEqual(v[0][2], "forbidden_patterns")

    def test_forbidden_pattern_out_of_scope(self):
        _write(self.root, "lib/a.py", "console.log(1)\n")
        rules = [{"pattern": r"console\.log", "paths": ["src/**"]}]
        self.assertEqual(da.check_forbidden(self.root, ["lib/a.py"], rules), [])

    def test_naming_violation(self):
        rules = [{"paths": ["src/**"], "filename_must_match": r"^[a-z0-9_]+\.py$",
                  "reason": "snake_case"}]
        v = da.check_naming(["src/BadName.py"], rules)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][2], "naming")

    def test_naming_ok(self):
        rules = [{"paths": ["src/**"], "filename_must_match": r"^[a-z0-9_]+\.py$"}]
        self.assertEqual(da.check_naming(["src/good_name.py"], rules), [])

    def test_file_size_over_cap(self):
        _write(self.root, "src/big.py", "\n".join("x" for _ in range(50)) + "\n")
        cfg = {"max_lines": 10}
        v = da.check_file_size(self.root, ["src/big.py"], cfg)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][2], "file_size")

    def test_file_size_override(self):
        _write(self.root, "src/generated/g.py", "\n".join("x" for _ in range(50)) + "\n")
        cfg = {"max_lines": 10,
               "overrides": [{"paths": ["**/generated/**"], "max_lines": 1000}]}
        self.assertEqual(da.check_file_size(self.root, ["src/generated/g.py"], cfg), [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_arch -v`
Expected: FAIL — `AttributeError: module 'dae_arch' has no attribute 'check_forbidden'`

- [ ] **Step 3: Add the three checks to `dae_arch.py`**

Append to `dae_arch.py`:

```python
def _read_lines(root, rel):
    """Lines of a repo-relative file ([] if unreadable)."""
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except OSError:
        return []


def check_forbidden(root, files, rules):
    """Flag lines matching a forbidden pattern within the rule's path scope."""
    violations = []
    for rule in rules:
        pat = re.compile(rule["pattern"])
        globs = _compile_globs(rule.get("paths", []))
        reason = rule.get("reason", "matches forbidden pattern %r" % rule["pattern"])
        for f in files:
            if not _match_any(f, globs):
                continue
            for n, line in enumerate(_read_lines(root, f), 1):
                if pat.search(line):
                    violations.append((f, n, "forbidden_patterns", reason))
    return violations


def check_naming(files, rules):
    """Flag files whose basename fails the rule's filename regex."""
    violations = []
    for rule in rules:
        globs = _compile_globs(rule.get("paths", []))
        name_re = re.compile(rule["filename_must_match"])
        reason = rule.get("reason",
                          "filename must match %r" % rule["filename_must_match"])
        for f in files:
            if not _match_any(f, globs):
                continue
            if not name_re.search(os.path.basename(f)):
                violations.append((f, 0, "naming", reason))
    return violations


def check_file_size(root, files, cfg):
    """Flag files whose line count exceeds the nearest matching max_lines cap."""
    default = cfg.get("max_lines")
    overrides = [(_compile_globs(ov["paths"]), ov["max_lines"])
                 for ov in cfg.get("overrides", [])]
    violations = []
    for f in files:
        cap = default
        for globs, limit in overrides:
            if _match_any(f, globs):
                cap = limit
        if cap is None:
            continue
        n = len(_read_lines(root, f))
        if n > cap:
            violations.append((f, n, "file_size", "%d lines > max %d" % (n, cap)))
    return violations
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_arch -v`
Expected: PASS — 9 tests OK

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_arch.py engineer/scripts/test_dae_arch.py
git commit -m "feat: dae_arch.py — forbidden-pattern, naming, file-size checks"
```

### Task 4: Import extraction + the layering check

**Files:**
- Modify: `engineer/scripts/dae_arch.py`
- Test: `engineer/scripts/test_dae_arch.py`

- [ ] **Step 1: Write the failing test** — add to `test_dae_arch.py`:

```python
class TestImports(unittest.TestCase):
    def test_python_imports(self):
        text = "import os\nfrom pkg.mod import thing\nfrom .relmod import other\n"
        specs = da.extract_imports("a/b.py", text)
        self.assertIn("os", specs)
        self.assertIn("pkg.mod", specs)
        self.assertIn(".relmod", specs)

    def test_js_imports(self):
        text = ('import x from "./local";\n'
                'const y = require("../up/dep");\n'
                'import "react";\n')
        specs = da.extract_imports("a/b.ts", text)
        self.assertIn("./local", specs)
        self.assertIn("../up/dep", specs)
        self.assertIn("react", specs)


class TestLayers(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_layering_violation_python(self):
        _write(self.root, "src/domain/order.py", "from src.infra.db import save\n")
        _write(self.root, "src/infra/db.py", "def save(): pass\n")
        layers = [
            {"name": "domain", "paths": ["src/domain/**"],
             "may_not_import": ["infra"]},
            {"name": "infra", "paths": ["src/infra/**"]},
        ]
        files = ["src/domain/order.py", "src/infra/db.py"]
        v = da.check_layers(self.root, files, layers, files)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][2], "layers")
        self.assertIn("domain", v[0][3])
        self.assertIn("infra", v[0][3])

    def test_layering_clean(self):
        _write(self.root, "src/domain/order.py", "from src.domain.money import M\n")
        _write(self.root, "src/domain/money.py", "M = 1\n")
        layers = [{"name": "domain", "paths": ["src/domain/**"],
                   "may_not_import": ["infra"]},
                  {"name": "infra", "paths": ["src/infra/**"]}]
        files = ["src/domain/order.py", "src/domain/money.py"]
        self.assertEqual(da.check_layers(self.root, files, layers, files), [])

    def test_layering_violation_js(self):
        _write(self.root, "src/web/page.ts", 'import {db} from "../infra/db";\n')
        _write(self.root, "src/infra/db.ts", "export const db = 1;\n")
        layers = [{"name": "web", "paths": ["src/web/**"],
                   "may_not_import": ["infra"]},
                  {"name": "infra", "paths": ["src/infra/**"]}]
        files = ["src/web/page.ts", "src/infra/db.ts"]
        v = da.check_layers(self.root, files, layers, files)
        self.assertEqual(len(v), 1)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_arch -v`
Expected: FAIL — `AttributeError: module 'dae_arch' has no attribute 'extract_imports'`

- [ ] **Step 3: Add import extraction + the layering check to `dae_arch.py`**

Append to `dae_arch.py`:

```python
_PY_IMPORT = re.compile(r"^\s*(?:from\s+(\.[\w.]*|[\w.]+)\s+import|"
                        r"import\s+([\w.]+))", re.MULTILINE)
_JS_IMPORT = re.compile(r"""(?:from|require\(|import)\s*['"]([^'"]+)['"]""")


def extract_imports(rel_path, text):
    """The import specifiers in a source file (language by extension)."""
    if rel_path.endswith(".py"):
        return [a or b for a, b in _PY_IMPORT.findall(text)]
    return _JS_IMPORT.findall(text)


def _resolve_python(spec, importer, known):
    """Resolve a Python import specifier to a repo-relative file, or None.

    Handles project-rooted dotted modules (`pkg.mod` -> `pkg/mod.py`) and
    relative imports (`.sibling` -> a sibling of the importing file).
    """
    if spec.startswith("."):
        depth = len(spec) - len(spec.lstrip("."))
        base = importer
        for _ in range(depth):
            base = os.path.dirname(base)
        tail = spec.lstrip(".").replace(".", "/")
        stem = os.path.join(base, tail) if tail else base
    else:
        stem = spec.replace(".", "/")
    for cand in (stem + ".py", os.path.join(stem, "__init__.py")):
        norm = os.path.normpath(cand)
        if norm in known:
            return norm
    return None


def _resolve_js(spec, importer, known):
    """Resolve a JS/TS *relative* import to a repo-relative file, or None.

    Bare specifiers (packages) return None — they are not project layers.
    """
    if not spec.startswith("."):
        return None
    stem = os.path.normpath(os.path.join(os.path.dirname(importer), spec))
    exts = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
    cands = [stem + e for e in exts]
    cands += [os.path.join(stem, "index" + e) for e in exts]
    for cand in cands:
        norm = os.path.normpath(cand)
        if norm in known:
            return norm
    return None


def _layer_of(path, layer_globs):
    """The layer name whose globs match `path`, or None."""
    for name, globs in layer_globs:
        if _match_any(path, globs):
            return name
    return None


def check_layers(root, files, layer_rules, all_files):
    """Flag imports that cross a `may_not_import` layer boundary."""
    layer_globs = [(r["name"], _compile_globs(r["paths"])) for r in layer_rules]
    forbidden = {r["name"]: set(r.get("may_not_import", [])) for r in layer_rules}
    known = {os.path.normpath(f) for f in all_files}
    violations = []
    for f in files:
        src_layer = _layer_of(f, layer_globs)
        if src_layer is None or not forbidden.get(src_layer):
            continue
        text = "\n".join(_read_lines(root, f))
        for spec in extract_imports(f, text):
            if f.endswith(".py"):
                target = _resolve_python(spec, f, known)
            else:
                target = _resolve_js(spec, f, known)
            if target is None:
                continue  # external / unresolvable — not a project layer
            tgt_layer = _layer_of(target, layer_globs)
            if tgt_layer in forbidden[src_layer]:
                violations.append((f, 0, "layers",
                                   "%s must not import %s (%s)"
                                   % (src_layer, tgt_layer, target)))
    return violations
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_arch -v`
Expected: PASS — 14 tests OK

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_arch.py engineer/scripts/test_dae_arch.py
git commit -m "feat: dae_arch.py — import extraction + dependency layering check"
```

### Task 5: `audit` + the CLI

**Files:**
- Modify: `engineer/scripts/dae_arch.py`
- Test: `engineer/scripts/test_dae_arch.py`

- [ ] **Step 1: Write the failing test** — add to `test_dae_arch.py`:

```python
class TestAudit(unittest.TestCase):
    def test_audit_collects_all_kinds(self):
        rules = {
            "forbidden_patterns": [{"pattern": "TODO", "paths": ["**"]}],
            "file_size": {"max_lines": 1},
        }
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        _write(root, "src/a.py", "TODO\nx\n")
        v = da.audit_rules(root, ["src/a.py"], rules)
        kinds = sorted(set(x[2] for x in v))
        self.assertEqual(kinds, ["file_size", "forbidden_patterns"])

    def test_audit_empty_rules(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        self.assertEqual(da.audit_rules(root, [], {}), [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_arch -v`
Expected: FAIL — `AttributeError: module 'dae_arch' has no attribute 'audit_rules'`

- [ ] **Step 3: Add `audit_rules`, `audit`, and `main` to `dae_arch.py`**

Append to `dae_arch.py`:

```python
def audit_rules(root, files, rules):
    """Run every configured check over `files`; return all violations."""
    violations = []
    if rules.get("forbidden_patterns"):
        violations += check_forbidden(root, files, rules["forbidden_patterns"])
    if rules.get("naming"):
        violations += check_naming(files, rules["naming"])
    if rules.get("file_size"):
        violations += check_file_size(root, files, rules["file_size"])
    if rules.get("layers"):
        all_files = files_in_scope(root, full=True)
        violations += check_layers(root, files, rules["layers"], all_files)
    return violations


def audit(start_dir, full):
    """Resolve the project, run the checks. Returns (root, rules, violations)
    or (None, None, None) if there is no manifest / no architecture section.
    """
    result = dae_resolve.resolve(start_dir)
    if result is None:
        return None, None, None
    rules = (result["manifest"] or {}).get("architecture")
    if not rules:
        return result["methodology_root"], None, None
    root = result["methodology_root"]
    files = files_in_scope(root, full)
    return root, rules, audit_rules(root, files, rules)


def main(argv):
    args = list(argv)
    fmt = "text"
    if "--format" in args:
        i = args.index("--format")
        fmt = args[i + 1] if i + 1 < len(args) else "text"
        del args[i:i + 2]
    full = False
    if "--full" in args:
        full = True
        args.remove("--full")
    if len(args) > 1:
        sys.stderr.write("usage: dae_arch.py [--full] [--format json] [START_DIR]\n")
        return 3
    start_dir = args[0] if args else os.getcwd()

    root, rules, violations = audit(start_dir, full)
    if root is None:
        sys.stderr.write("no .engineer/manifest.yml found — run /engineer.onboard\n")
        return 2
    if rules is None:
        sys.stderr.write("no `architecture:` section in the manifest — nothing to check\n")
        return 2

    if fmt == "json":
        json.dump([{"file": f, "line": n, "kind": k, "message": m}
                   for f, n, k, m in violations], sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for kind in ("layers", "forbidden_patterns", "naming", "file_size"):
            hits = [v for v in violations if v[2] == kind]
            if hits:
                sys.stdout.write("\n%s (%d):\n" % (kind, len(hits)))
                for f, n, _, m in hits:
                    loc = "%s:%d" % (f, n) if n else f
                    sys.stdout.write("  %s — %s\n" % (loc, m))
        sys.stdout.write("\n%d violation(s)\n" % len(violations))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the full test suite**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — all scripts green, including 16 in `test_dae_arch`.

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_arch.py engineer/scripts/test_dae_arch.py
git commit -m "feat: dae_arch.py — audit + CLI"
```

---

## Phase 3 — Manifest validation

### Task 6: Validate the `architecture:` section in `dae_resolve.py`

**Files:**
- Modify: `engineer/scripts/dae_resolve.py`
- Test: `engineer/scripts/test_dae_resolve.py`

- [ ] **Step 1: Write the failing test** — add to `test_dae_resolve.py` before `if __name__`:

```python
class TestArchitectureValidation(unittest.TestCase):
    def test_layer_missing_name(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "architecture": {"layers": [{"paths": ["src/**"]}]}}
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("architecture.layers" in e for e in errors))

    def test_bad_file_size(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "architecture": {"file_size": {"max_lines": -3}}}
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("file_size" in e for e in errors))

    def test_valid_architecture_ok(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "architecture": {
                 "layers": [{"name": "domain", "paths": ["src/domain/**"]}],
                 "file_size": {"max_lines": 400}}}
        errors, _ = dr.validate_manifest(m)
        self.assertEqual([e for e in errors if "architecture" in e], [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_resolve -v`
Expected: FAIL — the architecture errors are not produced.

- [ ] **Step 3: Add `_validate_architecture` and call it**

In `dae_resolve.py`, add this function just before `validate_manifest`:

```python
def _validate_architecture(errors, manifest):
    """Light structural validation of the optional `architecture:` section."""
    arch = manifest.get("architecture")
    if not isinstance(arch, dict):
        return
    for i, layer in enumerate(arch.get("layers") or []):
        if not isinstance(layer, dict) or not layer.get("name") \
                or not layer.get("paths"):
            errors.append("architecture.layers[%d] must have 'name' and 'paths'" % i)
    fs = arch.get("file_size")
    if isinstance(fs, dict) and "max_lines" in fs:
        ml = fs["max_lines"]
        if not isinstance(ml, int) or ml <= 0:
            errors.append("architecture.file_size.max_lines must be a positive int")
```

Then, inside `validate_manifest`, add a call right before `return errors, warnings`:

```python
    _validate_architecture(errors, manifest)

    return errors, warnings
```

- [ ] **Step 4: Run the full test suite**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — all green.

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_resolve.py engineer/scripts/test_dae_resolve.py
git commit -m "feat: dae_resolve validates the architecture manifest section"
```

---

## Phase 4 — The `arch-check` skill

### Task 7: Write the `arch-check` SKILL.md

**Files:**
- Create: `engineer/skills/arch-check/SKILL.md`

- [ ] **Step 1: Create the skill file**

Create `engineer/skills/arch-check/SKILL.md`:

```markdown
---
name: arch-check
description: Use to check a feature's code against the charter's architecture rules — dependency layering, forbidden patterns, file naming, file size. Triggers — "/engineer.arch-check", "architecture check", "check architecture fitness", "does this follow the charter", "check layering".
---

# arch-check

Run the charter architecture fitness check — Checkpoint 7 (Light Verify),
alongside `crap-analyzer`. Turns the charter's architectural vision from prose
into an objective gate: `dae_arch.py` reads the manifest's `architecture:` rules
and reports violations.

Read-only on the codebase — it reports, it does not fix.

## When to use

Checkpoint 7, after the feature's code is implemented and refined. Also useful
as a standalone audit (`--full`) of an existing project.

**Not for:** change-risk analysis (`crap-analyzer`); artifact consistency
(`consistency-check`); fixing violations (that is a human/agent decision per
violation).

## Workflow

### Step 0 — Entry gate

Verify the prior checkpoint is complete: run
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_handoff.py <feature-dir> --through 6`. On a
non-zero exit, **stop** and surface the gap to the human.

### Step 1 — Run the check

Run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_arch.py <methodology-root>` (add `--full`
for a whole-project audit). If it reports "no `architecture:` section", tell the
user the charter has no machine-readable architecture rules yet and stop.

### Step 2 — Present violations

Group the violations by kind (layering first — it is the architectural-vision
core). For each, show `file:line` and the rule. Do not auto-fix.

### Step 3 — Triage with the human

For each violation, the human decides: a real break (fix the code), or a rule
that no longer fits (amend `manifest.architecture` — and the charter prose).
`dae_arch.py` exiting non-zero means Checkpoint 7's architecture-fitness exit
criterion is unmet until the violations are resolved.

### Step 4 — Handoff

Emit a summary per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`.
`checkpoint: 7`; the `exit_criteria` block asserts the architecture-fitness
criterion with `verified_by: tool` and the `dae_arch.py` exit status as evidence.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) —
  the `architecture:` manifest section (§2); the Checkpoint Exit Contract (§8)
```

- [ ] **Step 2: Verify**

Run: `head -3 engineer/skills/arch-check/SKILL.md`
Expected: the `name: arch-check` frontmatter line is present.

- [ ] **Step 3: Commit**

```bash
git add engineer/skills/arch-check/SKILL.md
git commit -m "feat: add the arch-check skill — charter architecture fitness at CP7"
```

---

## Phase 5 — Foundation updates + version bump

### Task 8: Foundation §8/§3 Notion updates, version bump, final verification

**Files:**
- Modify (Notion): Foundation Design page `3585ecde-e0e2-811b-bc67-ff4913c03207`
- Modify: `engineer/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

- [ ] **Step 1: Update Foundation §8 — Checkpoint 7 exit criteria**

Fetch the page (`notion-fetch` id `3585ecde-e0e2-811b-bc67-ff4913c03207`). In Section 8's checkpoint table, the Checkpoint 7 row's "Exit criteria" cell currently reads `CRAP <= crap_max; coverage >= coverage_min`. Update it to:
`CRAP <= crap_max; coverage >= coverage_min; architecture fitness passes (dae_arch.py exits 0)`

- [ ] **Step 2: Update Foundation §3 — charter/architecture note**

In Section 3, append to the "Decisions locked" list:

```markdown
- **The charter's §2/§3 architecture & conventions prose has a machine-readable
  mirror** in `manifest.architecture` — checked by `dae_arch.py` at Checkpoint 7.
  The `plan.md` Charter Check may cite `dae_arch.py` for architecture rows
  instead of pure judgment.
```

- [ ] **Step 3: Verify the Notion edits**

Run (Notion MCP): `notion-fetch` id `3585ecde-e0e2-811b-bc67-ff4913c03207`.
Expected: §8 Checkpoint 7 mentions architecture fitness; §3 has the new bullet.

- [ ] **Step 4: Bump the engineer plugin version**

In `engineer/.claude-plugin/plugin.json`: `"version": "0.3.0"` -> `"version": "0.4.0"`.
In `.claude-plugin/marketplace.json`: the `engineer` plugin entry `"version": "0.3.0"` -> `"version": "0.4.0"` (leave the marketplace `metadata.version` and the other plugins unchanged).

- [ ] **Step 5: Final verification**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — all green.
Run: `cd engineer/scripts && python3 dae_arch.py --help >/dev/null && echo ok`
Expected: `ok` (the CLI imports cleanly).

- [ ] **Step 6: Commit**

```bash
git add engineer/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump engineer 0.4.0 — charter architecture fitness tool"
```

---

## Self-review notes

- **Spec coverage:** Component 1 (rules schema) → Tasks 1, 6. Component 2 (`dae_arch.py`) → Tasks 2–5. Component 3 (`arch-check` skill) → Task 7. Component 4 (Foundation/Notion) → Tasks 1, 8. Component 5 (testing) → the TDD steps throughout + Task 7's skill.
- **Layering is heuristic by design** — unresolvable and bare/package imports are skipped, not flagged (spec Component 2). A skipped import is a missed check, never a false positive.
- **`files_in_scope` base branch** — derived from `origin/HEAD`, falling back to `origin/main`; if a project's base differs, the `--full` audit is unaffected.
