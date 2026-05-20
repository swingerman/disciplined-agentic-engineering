#!/usr/bin/env python3
"""dae_dup.py — duplicate code detection orchestrator.

Runs a configured duplicate-detection backend (default jscpd) over a project,
normalizes its output to a stable JSON shape, and returns either the findings
or a structured `{"status": "unavailable" | "skipped" | "unsupported", ...}`
payload for graceful degradation. Used by Refine's Step 2 — its output is
passed into the Reuse-lens subagent's prompt.

Backend defaults:
  tool        = jscpd          (npm; user-installed, not auto-installed)
  min_tokens  = 50
  min_lines   = 5

Usage:
  dae_dup.py <project-root>     prints the result payload as JSON
"""
import json
import os
import shutil
import subprocess
import sys

import dae_resolve

DEFAULT_BACKEND = "jscpd"
DEFAULT_MIN_TOKENS = 50
DEFAULT_MIN_LINES = 5
KNOWN_BACKENDS = {"jscpd", "pmd-cpd", "flay", "dupl"}


def is_skipped(manifest):
    """True when manifest's duplication.skip flag is set (project opt-out)."""
    dup = (manifest or {}).get("duplication")
    return isinstance(dup, dict) and dup.get("skip") is True


def resolved_config(manifest):
    """Resolve config from manifest with defaults applied."""
    dup = (manifest or {}).get("duplication")
    if not isinstance(dup, dict):
        dup = {}
    return {
        "tool": dup.get("tool") or DEFAULT_BACKEND,
        "min_tokens": dup.get("min_tokens") or DEFAULT_MIN_TOKENS,
        "min_lines": dup.get("min_lines") or DEFAULT_MIN_LINES,
    }


def normalize_jscpd(raw):
    """jscpd's duplicates array -> the dae_dup normalized list."""
    out = []
    for c in (raw or {}).get("duplicates", []):
        first = c.get("firstFile", {})
        second = c.get("secondFile", {})
        out.append({
            "files": [
                {"path": first.get("name"),
                 "lines": [first.get("start"), first.get("end")]},
                {"path": second.get("name"),
                 "lines": [second.get("start"), second.get("end")]},
            ],
            "tokens": c.get("tokens", 0),
            "lines": c.get("lines", 0),
        })
    return out
