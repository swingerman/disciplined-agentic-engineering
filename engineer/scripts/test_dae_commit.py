#!/usr/bin/env python3
"""Tests for dae_commit — lock-aware commit retry. git is stubbed (offline)."""
import os
import tempfile
import unittest

import dae_commit as dc


class TestLockStale(unittest.TestCase):
    def test_absent_lock_not_stale(self):
        self.assertFalse(dc.lock_is_stale("/nope/index.lock", 8, 1000))

    def test_fresh_lock_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "index.lock")
            open(p, "w").close()
            os.utime(p, (1000, 1000))
            self.assertFalse(dc.lock_is_stale(p, 8, now=1005))  # 5s < 8s

    def test_old_lock_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "index.lock")
            open(p, "w").close()
            os.utime(p, (1000, 1000))
            self.assertTrue(dc.lock_is_stale(p, 8, now=1100))  # 100s >= 8s


class _Runner:
    """Fake _run returning a queued sequence of (rc, out, err)."""
    def __init__(self, seq):
        self.seq = list(seq)
        self.calls = 0

    def __call__(self, cmd, cwd):
        self.calls += 1
        return self.seq.pop(0) if self.seq else (0, "", "")


class TestCommitRetry(unittest.TestCase):
    def test_success_first_try(self):
        run = _Runner([(0, "abc123", "")])
        ok, msg = dc.commit_with_retry("/repo", "m", _run=run)
        self.assertTrue(ok)
        self.assertEqual(run.calls, 1)

    def test_nothing_to_commit_not_retried(self):
        run = _Runner([(1, "", "nothing to commit, working tree clean")])
        ok, msg = dc.commit_with_retry("/repo", "m", _run=run)
        self.assertFalse(ok)
        self.assertEqual(msg, "nothing to commit")
        self.assertEqual(run.calls, 1)

    def test_fresh_lock_waits_then_succeeds(self):
        run = _Runner([
            (1, "", "fatal: Unable to create '.git/index.lock': File exists"),
            (0, "ok", ""),
        ])
        slept = []
        ok, _ = dc.commit_with_retry(
            "/repo", "m", _run=run,
            _sleep=lambda s: slept.append(s),
            _now=lambda: 0.0)  # no real lock file -> not stale -> waits
        self.assertTrue(ok)
        self.assertEqual(len(slept), 1)  # waited once, did not delete anything
        self.assertEqual(run.calls, 2)

    def test_stale_lock_removed_then_succeeds(self):
        with tempfile.TemporaryDirectory() as repo:
            git = os.path.join(repo, ".git")
            os.makedirs(git)
            lock = os.path.join(git, "index.lock")
            open(lock, "w").close()
            os.utime(lock, (0, 0))  # ancient -> stale
            run = _Runner([
                (1, "", "Unable to create '.git/index.lock': File exists"),
                (0, "ok", ""),
            ])
            slept = []
            ok, _ = dc.commit_with_retry(
                repo, "m", stale_after=8, _run=run,
                _sleep=lambda s: slept.append(s), _now=lambda: 1000.0)
            self.assertTrue(ok)
            self.assertFalse(os.path.exists(lock))  # stale lock removed
            self.assertEqual(slept, [])            # removed, not slept
            self.assertEqual(run.calls, 2)

    def test_exhausts_retries(self):
        run = _Runner([(1, "", "index.lock: File exists")] * 3)
        ok, msg = dc.commit_with_retry(
            "/repo", "m", retries=3, _run=run,
            _sleep=lambda s: None, _now=lambda: 0.0)
        self.assertFalse(ok)
        self.assertIn("exhausted", msg)
        self.assertEqual(run.calls, 3)

    def test_other_error_returns_immediately(self):
        run = _Runner([(1, "", "error: pathspec broken")])
        ok, msg = dc.commit_with_retry("/repo", "m", _run=run)
        self.assertFalse(ok)
        self.assertIn("pathspec", msg)
        self.assertEqual(run.calls, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
