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
