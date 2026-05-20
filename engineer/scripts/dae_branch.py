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
import subprocess
import sys

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


def current_branch(cwd):
    """The current git branch name (cwd's repo), or None if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or None


def check(feature_dir, manifest):
    """Return (ok, message). Empty message when ok and silent.
    On mismatch the message names both branches and the `git checkout` fix."""
    if is_manual(manifest):
        return True, ""
    branch = current_branch(feature_dir)
    if branch is None:
        return False, ("could not determine current branch "
                       "(not in a git repo, detached HEAD, or git unavailable) "
                       "-- cannot verify branch")
    want = expected_branch(feature_dir)
    if branch == want:
        return True, ""
    return False, ("on '%s', expected '%s' -- switch with: git checkout %s"
                   % (branch, want, want))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    feature_dir = argv[0]
    manifest = {}
    _, manifest_path = dae_resolve.find_methodology_root(feature_dir)
    if manifest_path and os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            try:
                manifest = dae_resolve.read_manifest(f.read())
            except dae_resolve.ManifestError:
                manifest = {}
    ok, msg = check(feature_dir, manifest)
    if msg:
        print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
