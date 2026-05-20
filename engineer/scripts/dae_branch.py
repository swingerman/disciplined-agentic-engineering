#!/usr/bin/env python3
"""dae_branch.py — branch hygiene at the DAE entry gate.

Verifies the agent is on the feature's branch before a checkpoint skill
proceeds. Reads the expected branch from feature.md frontmatter (`branch:`),
or falls back to the folder slug (`features/NNN-<slug>/` -> `<slug>`).
A project-wide opt-out — manifest `git.manual: true` — disables the check.

Usage:
  dae_branch.py <feature-dir>     exit 0 on match, non-zero with a message on mismatch
"""
import os
import re

import dae_resolve

_BRANCH_RE = re.compile(r"^branch:\s*(\S+)\s*$", re.MULTILINE)


def expected_branch(feature_dir):
    """Resolve the feature's expected branch: feature.md frontmatter
    `branch:` (preferred), else the folder slug (basename with leading
    `NNN-` digit prefix stripped)."""
    feature_md = os.path.join(feature_dir, "feature.md")
    if os.path.isfile(feature_md):
        with open(feature_md, encoding="utf-8") as f:
            text = f.read()
        fm = dae_resolve.extract_frontmatter(text)
        if fm:
            m = _BRANCH_RE.search(fm)
            if m:
                return m.group(1)
    name = os.path.basename(os.path.normpath(feature_dir))
    return re.sub(r"^\d+-", "", name)


def is_manual(manifest):
    """True when manifest's git.manual flag is set (project-wide opt-out)."""
    git = (manifest or {}).get("git")
    return isinstance(git, dict) and git.get("manual") is True
