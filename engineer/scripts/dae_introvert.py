#!/usr/bin/env python3
"""dae_introvert.py — test-introversion scanner (vacuous-test pre-filter).

Classifies tests by whether their pass/fail can actually depend on the
behaviour of the system under test. A test is "introverted" when it can run
green without any assertion executing on SUT output:

  - no-assertion          the test asserts nothing at all
  - conditional-assertion every assertion is nested inside a conditional
                          (if / for / while / try) and none is guaranteed to
                          run — the test can pass vacuously

This is the cheap, static pre-filter for what mutation testing finds
dynamically: a surviving mutant on a test flagged here is a high-confidence
vacuous test, and the conditional-assertion case is caught even when no mutant
exercises the bypassed path. The "assertion's value traces back to the SUT"
(data-flow / backward-slice from each assertion) classification is intentionally
NOT done here — that is the job of a real introversion backend (e.g. a
`deintroverter`); plug it in via `manifest.introversion.backend` and this script
defers to it.

Used by the harden path (engineer:fix Step 7; the mutation pre-pass). Mirrors
dae_dup.py: configured-backend-first, graceful degradation, stable JSON.

Backend contract: the configured backend is run as `<backend> <root>` and must
print JSON to stdout shaped `{"findings": [ {file, test, line, kind, detail} ]}`
(or a bare list of those objects).

Built-in fallback: a stdlib-`ast` scan of Python test files only. Other
languages → configure a backend, or run an off-the-shelf linter in CI
(eslint-plugin-jest no-conditional-expect / expect-expect, SonarQube S2699,
rubocop-rspec).

Usage:
  dae_introvert.py <start-dir>     prints the result payload as JSON

Exit codes:
    0  ok / advisory (always 0 — this is a signal, not a gate)
    3  usage error
"""
import ast
import json
import os
import shutil
import subprocess
import sys

import dae_resolve  # noqa: E402

EXCLUDE_DIRS = {".git", "node_modules", ".build", "venv", ".venv",
                "__pycache__", "dist", "build", ".tox", ".mypy_cache"}

# Statement types that may skip their body — an assertion nested only inside
# these is not guaranteed to execute.
_CONDITIONAL_STMTS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try)


def is_skipped(manifest):
    """True when manifest's introversion.skip flag is set (project opt-out)."""
    iv = (manifest or {}).get("introversion")
    return isinstance(iv, dict) and iv.get("skip") is True


def configured_backend(manifest):
    """The introversion backend command, or None for the built-in fallback."""
    iv = (manifest or {}).get("introversion")
    if isinstance(iv, dict):
        return iv.get("backend") or None
    return None


def backend_available(tool):
    """True if the backend executable is on PATH."""
    return shutil.which(tool) is not None


def _is_assertion(node):
    """True if an AST node is an assertion: a bare `assert`, or a call whose
    name/attr starts with 'assert' or is a known oracle verb (pytest, unittest,
    hamcrest, BDD `should`/`expect`, `pytest.raises`)."""
    if isinstance(node, ast.Assert):
        return True
    if isinstance(node, ast.Call):
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else (
            func.id if isinstance(func, ast.Name) else None)
        if name:
            low = name.lower()
            return low.startswith("assert") or low in (
                "expect", "should", "fail", "raises")
    return False


def _contains_assertion(node):
    """True if the subtree rooted at node contains any assertion."""
    return any(_is_assertion(child) for child in ast.walk(node))


def _is_test_func(node):
    """A pytest/unittest test function or method: name starts with 'test'."""
    return (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test"))


def classify_source(src, filename="<test>"):
    """Return introversion findings for one Python source string.

    no-assertion          — a test function with zero assertions
    conditional-assertion — a test whose assertions all sit inside a
                            conditional/loop/try, none guaranteed to execute
    """
    findings = []
    try:
        tree = ast.parse(src, filename=filename)
    except SyntaxError:
        return findings
    for node in ast.walk(tree):
        if not _is_test_func(node):
            continue
        if not _contains_assertion(node):
            findings.append({
                "file": filename, "test": node.name, "line": node.lineno,
                "kind": "no-assertion",
                "detail": "test function executes no assertion",
            })
            continue
        # At least one assertion exists. It is "guaranteed" to run only if it is
        # a direct statement of the function body (we do not reason about
        # always-true conditions — this is advisory, not a gate).
        guaranteed = any(
            _contains_assertion(stmt) for stmt in node.body
            if not isinstance(stmt, _CONDITIONAL_STMTS))
        if not guaranteed:
            findings.append({
                "file": filename, "test": node.name, "line": node.lineno,
                "kind": "conditional-assertion",
                "detail": "every assertion is nested in a conditional/loop/try "
                          "— the test can pass without asserting",
            })
    return findings


def _looks_like_test_file(path):
    base = os.path.basename(path)
    if not base.endswith(".py"):
        return False
    if base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py":
        return True
    parts = path.replace("\\", "/").split("/")
    return any(p in ("tests", "test") for p in parts)


def _iter_py_test_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if _looks_like_test_file(full):
                yield full


def _run_builtin(root):
    findings = []
    for path in _iter_py_test_files(root):
        try:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
        except OSError:
            continue
        rel = os.path.relpath(path, root)
        findings.extend(classify_source(src, filename=rel))
    return findings


def _run_backend(backend, root):
    """Run a configured backend; expect JSON findings on stdout.
    Returns the findings list, or None on any failure."""
    try:
        proc = subprocess.run([backend, root], capture_output=True, text=True,
                              check=False)
    except OSError:
        return None
    out = (proc.stdout or "").strip()
    if not out:
        return None
    try:
        data = json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict):
        data = data.get("findings", [])
    return data if isinstance(data, list) else None


def find_introversion(root, manifest):
    """Entry point: returns a structured payload (mirrors dae_dup.py).

    {"status": "ok",          "backend": "...", "findings": [...]}
    {"status": "skipped",     "reason": "...", "findings": []}   — manifest opt-out
    {"status": "unavailable", "reason": "...", "backend": "...", "findings": []}
    {"status": "error",       "reason": "...", "backend": "...", "findings": []}
    """
    if is_skipped(manifest):
        return {"status": "skipped", "reason": "manifest opt-out", "findings": []}
    backend = configured_backend(manifest)
    if backend:
        if not backend_available(backend):
            return {"status": "unavailable",
                    "reason": "%s not on PATH" % backend,
                    "backend": backend, "findings": []}
        result = _run_backend(backend, root)
        if result is None:
            return {"status": "error",
                    "reason": "%s produced no parseable JSON findings" % backend,
                    "backend": backend, "findings": []}
        return {"status": "ok", "backend": backend, "findings": result}
    return {"status": "ok", "backend": "builtin-ast-python",
            "findings": _run_builtin(root)}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    root = argv[0]
    manifest = {}
    _, manifest_path = dae_resolve.find_methodology_root(root)
    if manifest_path and os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            try:
                manifest = dae_resolve.read_manifest(f.read())
            except dae_resolve.ManifestError:
                manifest = {}
    print(json.dumps(find_introversion(root, manifest), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
