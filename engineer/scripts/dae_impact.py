#!/usr/bin/env python3
"""dae_impact.py — test impact analysis for the DAE acceptance pipeline.

Records which source files each acceptance scenario's test touches, so a code
change runs only the affected scenarios. Language-agnostic: it consumes a
normalized coverage feed produced by the project's runner.

Usage:
  dae_impact.py build <feature-dir> <coverage-feed.json>
      Build features/NNN-slug/.build/impact-map.json from the IR + the feed.
  dae_impact.py select <feature-dir> [--format json]
      Print the scenario ids to run for the current `git diff`, or ALL.

Safety: when the map cannot prove a scenario is safe to skip, select prints
ALL. A false skip is a missed regression; a false run only costs time.

Exit codes:
    0  ok
    2  missing IR / feed / map
    3  usage error
"""
import hashlib
import json
import os
import subprocess
import sys

SOURCE_EXTENSIONS = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
                     ".go", ".rb", ".java", ".kt", ".rs", ".cs", ".php")


def scenario_hashes(ir):
    """Map each scenario name to a content hash of its IR (steps + data)."""
    result = {}
    for sc in ir.get("scenarios", []):
        blob = json.dumps(sc, sort_keys=True).encode("utf-8")
        result[sc["name"]] = hashlib.sha1(blob).hexdigest()[:12]
    return result


def build_map(ir, coverage_feed, built_at):
    """Build the impact map from the IR and a normalized coverage feed.

    coverage_feed: [{"scenario": <id>, "files": [<source file>, ...]}, ...]
    """
    file_map = {}
    for entry in coverage_feed:
        sid = entry["scenario"]
        for f in entry.get("files", []):
            file_map.setdefault(f, [])
            if sid not in file_map[f]:
                file_map[f].append(sid)
    for f in file_map:
        file_map[f].sort()
    return {
        "built_at": built_at,
        "scenario_hashes": scenario_hashes(ir),
        "file_map": file_map,
    }


def _is_source(path):
    """True if `path` looks like a project source file (could host behavior)."""
    return path.endswith(SOURCE_EXTENSIONS) and "/.build/" not in ("/" + path)


def select_scenarios(current_ir, impact_map, changed_files):
    """Scenario ids to run for `changed_files`, or the string 'ALL'.

    Selected = new/spec-changed scenarios (hash differs from the map) + every
    scenario mapped to a changed file. A changed source file absent from the
    map cannot be proven safe -> 'ALL'. A missing map -> 'ALL'.
    """
    if impact_map is None:
        return "ALL"
    current = scenario_hashes(current_ir)
    recorded = impact_map.get("scenario_hashes", {})
    file_map = impact_map.get("file_map", {})

    selected = set()
    for sid, h in current.items():
        if recorded.get(sid) != h:        # new or spec-changed
            selected.add(sid)
    for f in changed_files:
        if f in file_map:
            selected.update(file_map[f])
        elif _is_source(f):               # unmapped source -> not provably safe
            return "ALL"
    return sorted(selected)
