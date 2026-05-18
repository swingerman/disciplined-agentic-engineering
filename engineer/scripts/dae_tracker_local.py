#!/usr/bin/env python3
"""dae-tracker-local — the `local` tracker driver.

In `local` mode the feature folders ARE the tracker. This driver reads
TrackedFeature records straight from `feature.md` frontmatter (plus
`progress.md` for the current checkpoint). `upsert` / `delete` are no-ops —
the local files are the source of truth; there is nothing separate to write.

MCP-backed trackers (notion, linear, ...) are NOT handled here — those are
driven by a connected tracker MCP, per references/tracker.md. This script is
only the `local` driver.

Usage:
    dae_tracker_local.py list [START_DIR]
    dae_tracker_local.py read SLUG [START_DIR]

Output: JSON — a TrackedFeature array for `list`, one record for `read`.

Exit codes:
    0  ok
    2  no manifest found, or (read) feature not found
    3  usage error
"""

import glob
import json
import os
import sys

import dae_resolve

# TrackedFeature fields sourced from feature.md frontmatter (Tracker
# Integration Foundation, Section 2). current_checkpoint comes from
# progress.md and is added separately.
FRONTMATTER_FIELDS = (
    "slug", "title", "outcome", "status",
    "autonomy_level", "target", "owner", "area", "tracker_ref",
)


def read_checkpoint(feature_dir):
    """Pull the current checkpoint from progress.md, or None if absent."""
    path = os.path.join(feature_dir, "progress.md")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            # Format: "**Current stage:** Checkpoint 5 — Implement (...)"
            if stripped.lower().startswith("**current stage:**"):
                return stripped.split("**", 2)[-1].strip()
    return None


def tracked_feature(feature_dir):
    """Build a TrackedFeature record from one features/NNN-slug/ folder."""
    fm_path = os.path.join(feature_dir, "feature.md")
    if not os.path.isfile(fm_path):
        return None
    with open(fm_path, "r", encoding="utf-8") as fh:
        block = dae_resolve.extract_frontmatter(fh.read())
    if block is None:
        return None
    try:
        fm = dae_resolve.read_manifest(block)
    except dae_resolve.ManifestError:
        return None
    record = {field: fm.get(field) for field in FRONTMATTER_FIELDS}
    record["current_checkpoint"] = read_checkpoint(feature_dir)
    return record


def list_features(start_dir):
    """All TrackedFeature records under the resolved methodology root."""
    root, _ = dae_resolve.find_methodology_root(start_dir)
    if root is None:
        return None
    features_dir = os.path.join(root, "features")
    records = []
    for fm_path in sorted(glob.glob(os.path.join(features_dir, "*", "feature.md"))):
        record = tracked_feature(os.path.dirname(fm_path))
        if record is not None:
            records.append(record)
    return records


def read_feature(start_dir, slug):
    """The TrackedFeature for one slug, or None if not found."""
    records = list_features(start_dir)
    if records is None:
        return None
    for record in records:
        if record.get("slug") == slug:
            return record
    return None


def main(argv):
    args = argv[1:]
    if not args or args[0] not in ("list", "read"):
        sys.stderr.write(__doc__.split("Usage:")[1].split("\n\n")[0])
        return 3
    command = args[0]

    if command == "list":
        start_dir = args[1] if len(args) > 1 else os.getcwd()
        records = list_features(start_dir)
        if records is None:
            sys.stderr.write("no .engineer/manifest.yml found — run /engineer.onboard\n")
            return 2
        json.dump(records, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    # command == "read"
    if len(args) < 2:
        sys.stderr.write("usage: dae_tracker_local.py read SLUG [START_DIR]\n")
        return 3
    slug = args[1]
    start_dir = args[2] if len(args) > 2 else os.getcwd()
    record = read_feature(start_dir, slug)
    if record is None:
        sys.stderr.write("feature %r not found (or project not onboarded)\n" % slug)
        return 2
    json.dump(record, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
