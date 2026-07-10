#!/usr/bin/env python3
"""dae_commit.py — git commit with bounded retry + SAFE stale-lock handling.

DAE checkpoint commits sometimes race `.git/index.lock` — e.g. a `viddy`/`watch`
loop polling `git status` holds it for an instant. Sessions reinvent a blind
`rm -f .git/index.lock` retry loop, which is dangerous: it can delete a lock an
ACTIVE commit is holding and corrupt the index. This helper retries with backoff
and removes the lock ONLY when it is demonstrably stale (older than --stale-after),
so a lock a live commit is holding (always fresh) is never touched.

Usage:
  dae_commit.py <repo-dir> -m "message" [--all] [--retries N] [--stale-after S]

Exit 0 on commit; 1 on failure (reason on stderr). "nothing to commit" is a
non-retryable failure reported as-is.
"""
import os
import subprocess
import sys
import time


def _run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return r.returncode, r.stdout, r.stderr


def lock_is_stale(lock_path, stale_after, now):
    """True when the lock file exists and is older than stale_after seconds.
    A lock a live commit holds is refreshed constantly, so it is never stale."""
    try:
        age = now - os.path.getmtime(lock_path)
    except OSError:
        return False
    return age >= stale_after


def commit_with_retry(repo, message, all=False, retries=5, stale_after=8.0,
                      backoff=1.0, _run=_run, _sleep=time.sleep, _now=time.time):
    """Commit, retrying on index.lock contention. Returns (ok, message).
    Removes the lock only when lock_is_stale() — never a fresh (held) lock."""
    lock_path = os.path.join(repo, ".git", "index.lock")
    cmd = ["git", "commit", "-m", message] + (["-a"] if all else [])
    last = ""
    for _ in range(max(1, retries)):
        rc, out, err = _run(cmd, repo)
        if rc == 0:
            return True, (out.strip() or "committed")
        blob = ((out or "") + (err or "")).lower()
        last = (err or out or "").strip()
        if "nothing to commit" in blob:
            return False, "nothing to commit"
        if "index.lock" in blob or "unable to create" in blob:
            if lock_is_stale(lock_path, stale_after, _now()):
                try:
                    os.remove(lock_path)
                except OSError:
                    pass
                continue  # stale lock cleared — retry immediately
            _sleep(backoff)  # a live commit holds it — wait and retry
            continue
        return False, last or "git commit failed"
    return False, "index.lock contention: exhausted %d retries" % retries


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    repo = argv[0]
    rest = argv[1:]
    if "-m" not in rest:
        sys.stderr.write("usage: dae_commit.py <repo-dir> -m \"message\" "
                         "[--all] [--retries N] [--stale-after S]\n")
        return 2
    message = rest[rest.index("-m") + 1]
    all_flag = "--all" in rest
    retries = int(rest[rest.index("--retries") + 1]) if "--retries" in rest else 5
    stale = float(rest[rest.index("--stale-after") + 1]) if "--stale-after" in rest else 8.0
    ok, msg = commit_with_retry(repo, message, all=all_flag,
                                retries=retries, stale_after=stale)
    (sys.stdout if ok else sys.stderr).write(msg + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
