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
