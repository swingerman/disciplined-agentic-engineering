#!/usr/bin/env python3
"""dae_mutmap.py — differential mutation testing: the manifest select/update logic.

Owns mutation-manifest.json — a per-function result cache for mutation testing.
A function is re-mutated only when its code, its covering tests, or the mutation
operator set changed; otherwise its cached result is reused. The portable,
language-agnostic half of Differential Mutation Testing — the project's custom
mutation tool supplies function extraction, hashing, and execution.

Usage:
  dae_mutmap.py select <manifest> <hashes-feed>         function IDs to mutate
  dae_mutmap.py select --full <manifest> <hashes-feed>  force ALL (cold rebuild)
  dae_mutmap.py update <manifest> <hashes-feed> <results-feed>  rewrite manifest

select prints one function ID per line, or the token ALL.
"""
import json
import sys

MANIFEST_VERSION = 1


def _read_json(path):
    """Parse a JSON file; None on a missing or unreadable/invalid file."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def select(manifest, hashes_feed, full=False):
    """Return the list of function IDs to mutate, or the string "ALL".

    manifest     - the parsed mutation-manifest.json, or None if absent
    hashes_feed  - {"rules_hash": str,
                    "functions": {id: {"code_hash": .., "tests_hash": ..}}}
    full         - True forces ALL (cold rebuild)
    """
    if full or manifest is None:
        return "ALL"
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        return "ALL"
    if manifest.get("rules_hash") != hashes_feed.get("rules_hash"):
        return "ALL"
    cached = manifest.get("functions", {})
    selected = []
    for fid, h in hashes_feed.get("functions", {}).items():
        prev = cached.get(fid)
        if (prev is None
                or prev.get("code_hash") != h.get("code_hash")
                or prev.get("tests_hash") != h.get("tests_hash")):
            selected.append(fid)
    return sorted(selected)


def _carry_triage(old_survivors, new_survivors):
    """Carry the `equivalent` flag forward for survivors that match a prior
    survivor by (line, mutation). An equivalent flag already set in
    new_survivors is left untouched; unmatched survivors default to False.
    """
    prior = {(s.get("line"), s.get("mutation")): s.get("equivalent")
             for s in old_survivors}
    out = []
    for s in new_survivors:
        s = dict(s)
        if s.get("equivalent") is None:
            carried = prior.get((s.get("line"), s.get("mutation")))
            s["equivalent"] = bool(carried) if carried is not None else False
        out.append(s)
    return out


def update(manifest, hashes_feed, results_feed):
    """Build the new manifest: fresh entries for mutated functions, cached
    entries kept for skipped ones, orphaned IDs (renamed/deleted) pruned.

    results_feed - {"functions": {id: {"last_mutated": .., "mutants_total": ..,
                   "mutants_killed": .., "survivors": [..]}}} for functions
                   actually mutated this run.
    """
    old_fns = (manifest or {}).get("functions", {})
    results = results_feed.get("functions", {})
    new_fns = {}
    for fid, h in hashes_feed.get("functions", {}).items():
        if fid in results:
            r = results[fid]
            new_fns[fid] = {
                "code_hash": h.get("code_hash"),
                "tests_hash": h.get("tests_hash"),
                "last_mutated": r.get("last_mutated"),
                "mutants_total": r.get("mutants_total"),
                "mutants_killed": r.get("mutants_killed"),
                "survivors": _carry_triage(
                    (old_fns.get(fid) or {}).get("survivors", []),
                    r.get("survivors", [])),
            }
        elif fid in old_fns:
            new_fns[fid] = dict(old_fns[fid])  # skipped — keep a copy of the cached entry
        # a function new this run but absent from results is omitted; the next
        # select picks it up (it has no cached result to report yet).
    return {
        "manifest_version": MANIFEST_VERSION,
        "rules_hash": hashes_feed.get("rules_hash"),
        "functions": new_fns,
    }


def serialize(manifest):
    """Serialize the manifest deterministically — function IDs sorted, dict
    keys sorted, and survivors within an entry sorted by (line, mutation) — so
    independent updates merge without conflict.
    """
    lines = ["{",
             '  "manifest_version": %s,'
             % json.dumps(manifest.get("manifest_version", MANIFEST_VERSION)),
             '  "rules_hash": %s,' % json.dumps(manifest.get("rules_hash")),
             '  "functions": {']
    ids = sorted(manifest.get("functions", {}))
    for i, fid in enumerate(ids):
        entry = dict(manifest["functions"][fid])
        if "survivors" in entry:
            entry["survivors"] = sorted(
                entry["survivors"],
                key=lambda s: (s.get("line") or 0, s.get("mutation") or ""))
        text = json.dumps(entry, sort_keys=True, separators=(", ", ": "))
        tail = "," if i < len(ids) - 1 else ""
        lines.append("    %s: %s%s" % (json.dumps(fid), text, tail))
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    mode, rest = argv[0], argv[1:]
    full = "--full" in rest
    rest = [a for a in rest if a != "--full"]
    if mode == "select":
        if len(rest) < 2:
            print("usage: dae_mutmap.py select [--full] <manifest> <hashes-feed>")
            return 2
        result = select(_read_json(rest[0]), _read_json(rest[1]) or {}, full=full)
        if result == "ALL":
            print("ALL")
        else:
            for fid in result:
                print(fid)
        return 0
    if mode == "update":
        if len(rest) < 3:
            print("usage: dae_mutmap.py update <manifest> "
                  "<hashes-feed> <results-feed>")
            return 2
        new_manifest = update(_read_json(rest[0]), _read_json(rest[1]) or {},
                              _read_json(rest[2]) or {})
        with open(rest[0], "w", encoding="utf-8") as f:
            f.write(serialize(new_manifest))
        print("updated %s -- %d functions"
              % (rest[0], len(new_manifest["functions"])))
        return 0
    print("unknown mode: %s" % mode)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
