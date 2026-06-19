#!/usr/bin/env python3
"""Tests for dae_delegable — the per-feature cloud-delegation gate.

Run: python3 test_dae_delegable.py
"""

import unittest

import dae_delegable as d

CLEAN_GIT = {"remote": True, "dirty": False, "pushed": True}


class TestEvaluate(unittest.TestCase):
    def test_clean_high_autonomy_is_cloud(self):
        ch, blockers = d.evaluate({"autonomy_level": "high"}, {}, False, CLEAN_GIT)
        self.assertEqual(ch, "cloud")
        self.assertEqual(blockers, [])

    def test_low_autonomy_blocks(self):
        ch, blockers = d.evaluate({"autonomy_level": "low"}, {}, False, CLEAN_GIT)
        self.assertEqual(ch, "local")
        self.assertTrue(any("autonomy:low" in b for b in blockers))

    def test_assignee_human_blocks(self):
        ch, _ = d.evaluate({"autonomy_level": "high", "assignee": "human"},
                           {}, False, CLEAN_GIT)
        self.assertEqual(ch, "local")

    def test_assignee_cloud_does_not_override_hard_blocker(self):
        # Explicit cloud request still loses to a stdio-MCP blocker.
        ch, blockers = d.evaluate({"autonomy_level": "high", "assignee": "cloud"},
                                  {}, True, CLEAN_GIT)
        self.assertEqual(ch, "local")
        self.assertTrue(any("stdio" in b for b in blockers))

    def test_local_infra_blocks_and_ignores_meta_key(self):
        manifest = {"infra": {"default_teardown": "leave-running",
                              "emulator": {"start": "x"}}}
        ch, blockers = d.evaluate({"autonomy_level": "medium"}, manifest, False, CLEAN_GIT)
        self.assertEqual(ch, "local")
        self.assertTrue(any("local-infra:emulator" in b for b in blockers))
        self.assertFalse(any("default_teardown" in b for b in blockers))

    def test_unpushed_branch_blocks(self):
        ch, blockers = d.evaluate({"autonomy_level": "high"}, {}, False,
                                  {"remote": True, "dirty": False, "pushed": False})
        self.assertEqual(ch, "local")
        self.assertTrue(any("branch-not-pushed" in b for b in blockers))

    def test_no_remote_blocks(self):
        ch, blockers = d.evaluate({"autonomy_level": "high"}, {}, False,
                                  {"remote": False, "dirty": False, "pushed": False})
        self.assertTrue(any("no-git-remote" in b for b in blockers))


if __name__ == "__main__":
    unittest.main(verbosity=2)
