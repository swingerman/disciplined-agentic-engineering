#!/usr/bin/env python3
"""Tests for dae_reconcile — merged-PR state reconcile.

Run: python3 test_dae_reconcile.py

Merge detection (gh/git subprocess) is stubbed so these run offline.
"""
import os
import tempfile
import unittest
from unittest import mock

import dae_reconcile as dr

FEATURE_MD = """\
---
slug: 042-export
branch: 042-export
status: in-progress
autonomy_level: high
---

# 042 export
Body prose that also mentions status: nowhere-important.
"""

PROGRESS_VERIFIED = """\
| CP | Stage | Status |
|----|--------|--------|
| 6 | Refine | done |
| 7 | Verify | done |
"""

PROGRESS_UNVERIFIED = """\
| CP | Stage | Status |
|----|--------|--------|
| 6 | Refine | done |
| 7 | Verify | pending |
"""


def _mk_feature(tmp, feature_md=FEATURE_MD, progress=None):
    d = os.path.join(tmp, "042-export")
    os.makedirs(d)
    with open(os.path.join(d, "feature.md"), "w", encoding="utf-8") as f:
        f.write(feature_md)
    if progress is not None:
        with open(os.path.join(d, "progress.md"), "w", encoding="utf-8") as f:
            f.write(progress)
    return d


class TestSetStatus(unittest.TestCase):
    def test_replaces_only_frontmatter_status(self):
        out = dr.set_status(FEATURE_MD, "done")
        self.assertIn("status: done", out)
        self.assertNotIn("status: in-progress", out)
        # untouched fields + body preserved
        self.assertIn("branch: 042-export", out)
        self.assertIn("status: nowhere-important", out)  # body line NOT rewritten

    def test_inserts_status_when_missing(self):
        no_status = "---\nslug: x\nbranch: x\n---\nbody\n"
        out = dr.set_status(no_status, "done")
        self.assertIn("status: done", out)

    def test_no_frontmatter_raises(self):
        with self.assertRaises(dr.ReconcileError):
            dr.set_status("no frontmatter here\n", "done")


class TestReads(unittest.TestCase):
    def test_feature_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _mk_feature(tmp)
            self.assertEqual(dr.feature_status(d), "in-progress")

    def test_is_verified_true_when_cp7_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _mk_feature(tmp, progress=PROGRESS_VERIFIED)
            self.assertTrue(dr.is_verified(d))

    def test_is_verified_false_without_cp7(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _mk_feature(tmp, progress=PROGRESS_UNVERIFIED)
            self.assertFalse(dr.is_verified(d))

    def test_is_verified_false_without_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _mk_feature(tmp)
            self.assertFalse(dr.is_verified(d))


def _state(merged, **kw):
    base = {"merged": merged, "state": "MERGED" if merged else "OPEN",
            "pr_number": 7, "pr_url": "http://x/7", "merged_at": None,
            "source": "gh", "branch": "042-export"}
    base.update(kw)
    return base


class TestReconcile(unittest.TestCase):
    def test_applies_and_flips_status_when_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _mk_feature(tmp, progress=PROGRESS_VERIFIED)
            with mock.patch.object(dr, "pr_merge_state", return_value=_state(True)):
                res = dr.reconcile(d, apply=True)
            self.assertTrue(res["needs_reconcile"])
            self.assertTrue(res["applied"])
            self.assertEqual(res["new_status"], "done")
            self.assertIsNone(res["flag"])
            self.assertEqual(dr.feature_status(d), "done")  # persisted

    def test_flags_merged_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _mk_feature(tmp, progress=PROGRESS_UNVERIFIED)
            with mock.patch.object(dr, "pr_merge_state", return_value=_state(True)):
                res = dr.reconcile(d, apply=False)
            self.assertTrue(res["needs_reconcile"])
            self.assertEqual(res["flag"], "merged-unverified")
            self.assertFalse(res["applied"])
            self.assertEqual(dr.feature_status(d), "in-progress")  # dry-run untouched

    def test_noop_when_not_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _mk_feature(tmp, progress=PROGRESS_VERIFIED)
            with mock.patch.object(dr, "pr_merge_state", return_value=_state(False)):
                res = dr.reconcile(d, apply=True)
            self.assertFalse(res["needs_reconcile"])
            self.assertFalse(res["applied"])
            self.assertEqual(dr.feature_status(d), "in-progress")

    def test_noop_when_already_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _mk_feature(tmp, feature_md=FEATURE_MD.replace(
                "status: in-progress", "status: done"))
            with mock.patch.object(dr, "pr_merge_state", return_value=_state(True)):
                res = dr.reconcile(d, apply=True)
            self.assertFalse(res["needs_reconcile"])
            self.assertFalse(res["applied"])

    def test_missing_feature_md_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(dr.ReconcileError):
                dr.reconcile(tmp, apply=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
