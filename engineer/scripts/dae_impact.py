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


def _read_json(path):
    """Parse a JSON file, or None if it is missing/unreadable."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_ir(feature_dir):
    """The acceptance IR for a feature, or None."""
    return _read_json(os.path.join(feature_dir, ".build", "spec.json"))


def load_map(feature_dir):
    """The impact map for a feature, or None if not built yet."""
    return _read_json(os.path.join(feature_dir, ".build", "impact-map.json"))


def _changed_files(start_dir):
    """Repo-relative paths changed vs. the base branch's merge-base."""
    try:
        root = subprocess.run(
            ["git", "-C", start_dir, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True).stdout.strip()
        base = (subprocess.run(
            ["git", "-C", root, "rev-parse", "--abbrev-ref", "origin/HEAD"],
            capture_output=True, text=True).stdout.strip() or "origin/main")
        out = subprocess.run(
            ["git", "-C", root, "diff", "--name-only", "--merge-base", base],
            capture_output=True, text=True, check=True).stdout
        return out.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def _utc_stamp():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M")


def main(argv):
    if len(argv) < 2 or argv[0] not in ("build", "select"):
        sys.stderr.write(__doc__.split("Usage:")[1].split("\n\n")[0])
        return 3
    command, feature_dir = argv[0], argv[1]

    ir = load_ir(feature_dir)
    if ir is None:
        sys.stderr.write("no .build/spec.json in %s — run the parser first\n"
                         % feature_dir)
        return 2

    if command == "build":
        if len(argv) < 3:
            sys.stderr.write("usage: dae_impact.py build <feature-dir> <feed.json>\n")
            return 3
        feed = _read_json(argv[2])
        if feed is None:
            sys.stderr.write("cannot read coverage feed: %s\n" % argv[2])
            return 2
        m = build_map(ir, feed, _utc_stamp())
        out_path = os.path.join(feature_dir, ".build", "impact-map.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2, sort_keys=True)
        sys.stderr.write("impact map written: %s\n" % out_path)
        return 0

    # command == "select"
    fmt = "text"
    if "--format" in argv:
        i = argv.index("--format")
        fmt = argv[i + 1] if i + 1 < len(argv) else "text"
    sel = select_scenarios(ir, load_map(feature_dir), _changed_files(feature_dir))
    if fmt == "json":
        json.dump(sel, sys.stdout)
        sys.stdout.write("\n")
    elif sel == "ALL":
        sys.stdout.write("ALL\n")
    else:
        for sid in sel:
            sys.stdout.write(sid + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
