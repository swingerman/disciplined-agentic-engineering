"""Tests for dae_branch.py."""
import os
import subprocess
import tempfile
import unittest

import dae_branch


def _write_feature_md(feature_dir, branch=None):
    os.makedirs(feature_dir, exist_ok=True)
    fm = "---\nslug: x\n"
    if branch:
        fm += "branch: %s\n" % branch
    fm += "---\n\n# Feature\n"
    with open(os.path.join(feature_dir, "feature.md"), "w", encoding="utf-8") as f:
        f.write(fm)


class ExpectedBranchTests(unittest.TestCase):
    def test_reads_branch_from_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            feat = os.path.join(d, "015-image-formats")
            _write_feature_md(feat, branch="015-image-formats")
            self.assertEqual(
                dae_branch.expected_branch(feat), "015-image-formats")

    def test_falls_back_to_slug_when_no_branch_field(self):
        with tempfile.TemporaryDirectory() as d:
            feat = os.path.join(d, "015-image-formats")
            _write_feature_md(feat)  # no branch:
            self.assertEqual(dae_branch.expected_branch(feat), "image-formats")

    def test_falls_back_to_slug_when_no_feature_md(self):
        with tempfile.TemporaryDirectory() as d:
            feat = os.path.join(d, "042-payments")
            os.makedirs(feat)
            self.assertEqual(dae_branch.expected_branch(feat), "payments")


class IsManualTests(unittest.TestCase):
    def test_true_when_set(self):
        self.assertTrue(dae_branch.is_manual({"git": {"manual": True}}))

    def test_false_when_unset(self):
        self.assertFalse(dae_branch.is_manual({}))
        self.assertFalse(dae_branch.is_manual({"git": {}}))
        self.assertFalse(dae_branch.is_manual({"git": {"manual": False}}))

    def test_handles_none_manifest(self):
        self.assertFalse(dae_branch.is_manual(None))

    def test_handles_non_dict_git(self):
        # A malformed manifest where `git:` is a scalar, not a map.
        self.assertFalse(dae_branch.is_manual({"git": "yes"}))
        self.assertFalse(dae_branch.is_manual({"git": True}))


if __name__ == "__main__":
    unittest.main()
