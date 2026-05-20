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


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True,
                   capture_output=True, text=True)


def _init_repo(parent, branch="master"):
    os.makedirs(parent, exist_ok=True)
    _git(["init", "-q", "-b", branch], cwd=parent)
    _git(["config", "user.email", "t@t"], cwd=parent)
    _git(["config", "user.name", "t"], cwd=parent)
    open(os.path.join(parent, "init.txt"), "w").close()
    _git(["add", "init.txt"], cwd=parent)
    _git(["commit", "-q", "-m", "init"], cwd=parent)


class CheckTests(unittest.TestCase):
    def test_match_returns_ok_silent(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d, branch="image-formats")
            feat = os.path.join(d, "015-image-formats")
            _write_feature_md(feat, branch="image-formats")
            ok, msg = dae_branch.check(feat, {})
            self.assertTrue(ok)
            self.assertEqual(msg, "")

    def test_mismatch_returns_helpful_message(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d, branch="master")
            feat = os.path.join(d, "015-image-formats")
            _write_feature_md(feat, branch="image-formats")
            ok, msg = dae_branch.check(feat, {})
            self.assertFalse(ok)
            self.assertIn("master", msg)
            self.assertIn("image-formats", msg)
            self.assertIn("git checkout image-formats", msg)

    def test_manual_opt_out_skips_check(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d, branch="master")
            feat = os.path.join(d, "015-image-formats")
            _write_feature_md(feat, branch="image-formats")
            ok, msg = dae_branch.check(feat, {"git": {"manual": True}})
            self.assertTrue(ok)
            self.assertEqual(msg, "")

    def test_not_a_repo_returns_error(self):
        with tempfile.TemporaryDirectory() as d:
            feat = os.path.join(d, "015-image-formats")
            _write_feature_md(feat, branch="image-formats")
            ok, msg = dae_branch.check(feat, {})
            self.assertFalse(ok)
            self.assertIn("not in a git repo", msg)

    def test_slug_fallback_match(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d, branch="payments")
            feat = os.path.join(d, "042-payments")
            os.makedirs(feat)
            ok, msg = dae_branch.check(feat, {})
            self.assertTrue(ok)


class MainTests(unittest.TestCase):
    def test_help_returns_zero(self):
        self.assertEqual(dae_branch.main(["--help"]), 0)

    def test_match_in_real_repo_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d, branch="payments")
            feat = os.path.join(d, "042-payments")
            os.makedirs(feat)
            self.assertEqual(dae_branch.main([feat]), 0)

    def test_mismatch_in_real_repo_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d, branch="master")
            feat = os.path.join(d, "042-payments")
            os.makedirs(feat)
            self.assertEqual(dae_branch.main([feat]), 1)

    def test_broken_manifest_degrades_to_no_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d, branch="payments")
            eng = os.path.join(d, ".engineer")
            os.makedirs(eng)
            with open(os.path.join(eng, "manifest.yml"), "w") as f:
                f.write("  badly indented: true\nduplicate:\nduplicate:\n")
            feat = os.path.join(d, "042-payments")
            os.makedirs(feat)
            # Should not crash; falls back to empty manifest, branch check proceeds normally.
            self.assertEqual(dae_branch.main([feat]), 0)


if __name__ == "__main__":
    unittest.main()
