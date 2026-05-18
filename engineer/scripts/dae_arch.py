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
