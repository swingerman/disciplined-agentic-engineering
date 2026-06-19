#!/usr/bin/env python3
"""dae_delegable.py — per-feature cloud-delegation gate.

Answers ONE question: can the next checkpoint of this feature run on a *cloud*
Claude agent (fresh repo clone, no local state), or must it run locally?

This is the per-feature half of remote-readiness. The account/repo-level
preconditions (GitHub connected to claude.ai, a cloud environment exists) are
one-time human setup verified by `onboard` — NOT re-checked here. They don't
vary per feature and would need CLI/UI access this script doesn't assume.

What blocks cloud delegation (any one => local):
  - autonomy_level: low            ask-first mode; never auto-delegate
  - assignee: human | local        explicit pin off cloud in feature.md
  - declared local infra           manifest infra: services a cloud clone
                                    can't reach (emulators, local DBs)
  - local stdio MCP in .mcp.json    stdio servers don't exist in the cloud VM;
                                    the workflow would break there
  - uncommitted / unpushed branch   the cloud clones from the remote, not your
                                    worktree — local-only state won't be there
  - no git remote                   cloud can't clone what was never pushed

Usage:
    dae_delegable.py <feature-dir> [START_DIR]

Output: JSON {channel, cloud_blockers, assignee, autonomy_level}. `channel` is
"cloud" when cloud_blockers is empty, else "local". The router prefers cloud
when channel is cloud and falls back to local otherwise (see
references/handoff-dispatch.md).

Exit codes:
    0  ok (advisory — a "local" verdict is a normal result, not an error)
    2  no feature.md, or no manifest found
    3  usage error
"""

import json
import os
import subprocess
import sys

import dae_resolve

# infra: keys that are settings, not service definitions.
META_INFRA_KEYS = {"default_teardown"}


def evaluate(fm, manifest, mcp_has_stdio, git_state):
    """Pure gate logic — the testable core.

    fm: feature.md frontmatter dict.
    manifest: manifest dict.
    mcp_has_stdio: bool — repo .mcp.json declares a stdio server.
    git_state: {"remote": bool, "dirty": bool, "pushed": bool}.

    Returns (channel, blockers): channel "cloud" iff blockers is empty.
    """
    blockers = []

    if str(fm.get("autonomy_level", "")).lower() == "low":
        blockers.append("autonomy:low — ask-first mode, never auto-delegate")

    assignee = str(fm.get("assignee", "")).lower()
    if assignee in ("human", "local"):
        blockers.append("assignee:%s — pinned off cloud in feature.md" % assignee)

    infra = manifest.get("infra") or {}
    services = sorted(k for k, v in infra.items()
                      if k not in META_INFRA_KEYS and isinstance(v, dict))
    if services:
        # ponytail: any declared infra service => local. A cloud-reachable
        # service (managed DB, hosted API) could be fine, but we don't model
        # that yet. Refine per-service if it gates real work.
        blockers.append("local-infra:%s — declared services a cloud clone can't reach"
                        % ",".join(services))

    if mcp_has_stdio:
        blockers.append("local-stdio-mcp — .mcp.json declares a stdio server "
                        "absent in the cloud VM")

    if not git_state.get("remote"):
        blockers.append("no-git-remote — cloud can't clone an unpushed repo")
    if git_state.get("dirty"):
        blockers.append("uncommitted-changes — cloud clones the remote, not your worktree")
    if git_state.get("remote") and not git_state.get("pushed"):
        blockers.append("branch-not-pushed — local commits aren't on the remote yet")

    return ("local" if blockers else "cloud"), blockers


def load_frontmatter(feature_dir):
    """feature.md frontmatter as a dict, {} if unparseable, None if absent."""
    path = os.path.join(feature_dir, "feature.md")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        block = dae_resolve.extract_frontmatter(fh.read())
    if block is None:
        return {}
    try:
        return dae_resolve.read_manifest(block)
    except Exception:
        return {}


def mcp_has_stdio(root):
    """True if the repo's committed .mcp.json declares any stdio MCP server.

    A server is stdio if `type: stdio`, or (no type) it has a `command` and no
    `url` — the conventional shape of a local command-launched server.
    """
    path = os.path.join(root, ".mcp.json")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    servers = data.get("mcpServers") or data.get("servers") or {}
    for cfg in servers.values():
        if not isinstance(cfg, dict):
            continue
        t = str(cfg.get("type", "")).lower()
        if t == "stdio":
            return True
        if not t and cfg.get("command") and not cfg.get("url"):
            return True
    return False


def _git(root, *args):
    """Run a git command in root; stdout (stripped) on success, None on failure."""
    try:
        r = subprocess.run(["git", "-C", root, *args],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def git_state(root):
    """{"remote", "dirty", "pushed"} for the repo at root."""
    remote = bool(_git(root, "remote", "get-url", "origin"))
    dirty = bool(_git(root, "status", "--porcelain"))
    # pushed = 0 commits ahead of upstream. No upstream (None) => not pushed.
    ahead = _git(root, "rev-list", "--count", "@{u}..HEAD")
    return {"remote": remote, "dirty": dirty, "pushed": ahead == "0"}


def main(argv):
    if not argv:
        sys.stderr.write("usage: dae_delegable.py <feature-dir> [START_DIR]\n")
        return 3
    feature_dir = argv[0]
    start_dir = argv[1] if len(argv) > 1 else feature_dir

    fm = load_frontmatter(feature_dir)
    if fm is None:
        sys.stderr.write("no feature.md in %s\n" % feature_dir)
        return 2

    resolved = dae_resolve.resolve(start_dir)
    if resolved is None:
        sys.stderr.write("no .engineer/manifest.yml found from %s\n" % start_dir)
        return 2
    manifest = resolved.get("manifest") or {}
    root = resolved["methodology_root"]

    channel, blockers = evaluate(fm, manifest, mcp_has_stdio(root), git_state(root))
    print(json.dumps({
        "channel": channel,
        "cloud_blockers": blockers,
        "assignee": fm.get("assignee"),
        "autonomy_level": fm.get("autonomy_level"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
