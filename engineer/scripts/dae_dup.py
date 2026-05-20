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

import dae_resolve  # noqa: E402

DEFAULT_BACKEND = "jscpd"
DEFAULT_MIN_TOKENS = 50
DEFAULT_MIN_LINES = 5


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


def backend_available(tool):
    """True if the backend executable is on PATH."""
    return shutil.which(tool) is not None


def _run_jscpd(project_root, min_tokens, min_lines):
    """Run jscpd against project_root. Returns parsed JSON on success
    (possibly with empty duplicates), or None if the scan failed."""
    cmd = ["jscpd", project_root,
           "--reporters", "json",
           "--silent",
           "--min-tokens", str(min_tokens),
           "--min-lines", str(min_lines),
           "--output", os.path.join(project_root, ".build", "jscpd")]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return None
    report_path = os.path.join(project_root, ".build", "jscpd",
                               "jscpd-report.json")
    if not os.path.isfile(report_path):
        return None
    try:
        with open(report_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def find_duplicates(project_root, manifest):
    """Entry point: returns a structured payload.

    {"status": "ok",          "duplicates": [...]}                — backend ran
    {"status": "skipped",     "reason": "...", "duplicates": []}  — manifest opt-out
    {"status": "unavailable", "reason": "...", "install": "...",  — tool missing
                              "duplicates": []}
    {"status": "unsupported", "reason": "...", "duplicates": []}  — backend not in v1
    {"status": "error",       "reason": "...", "duplicates": []}  — scan failed
    """
    if is_skipped(manifest):
        return {"status": "skipped", "reason": "manifest opt-out",
                "duplicates": []}
    cfg = resolved_config(manifest)
    if not backend_available(cfg["tool"]):
        return {"status": "unavailable",
                "reason": "%s not on PATH" % cfg["tool"],
                "install": "npm install -g %s" % cfg["tool"],
                "duplicates": []}
    if cfg["tool"] == "jscpd":
        raw = _run_jscpd(project_root, cfg["min_tokens"], cfg["min_lines"])
        if raw is None:
            return {"status": "error",
                    "reason": "jscpd scan failed (see jscpd output)",
                    "duplicates": []}
        return {"status": "ok", "duplicates": normalize_jscpd(raw)}
    return {"status": "unsupported",
            "reason": "backend %s not implemented in v1" % cfg["tool"],
            "duplicates": []}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    project_root = argv[0]
    manifest = {}
    _, manifest_path = dae_resolve.find_methodology_root(project_root)
    if manifest_path and os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            try:
                manifest = dae_resolve.read_manifest(f.read())
            except dae_resolve.ManifestError:
                manifest = {}
    result = find_duplicates(project_root, manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
