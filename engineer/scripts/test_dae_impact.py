#!/usr/bin/env python3
"""Tests for dae_impact — acceptance-scenario test impact analysis.

Run: python3 -m unittest test_dae_impact -v
"""
import unittest

import dae_impact as di

IR_V1 = {"name": "Login", "scenarios": [
    {"name": "valid login", "steps": [{"keyword": "Given", "text": "a user"}]},
    {"name": "bad password", "steps": [{"keyword": "When", "text": "wrong pw"}]},
]}

FEED = [
    {"scenario": "valid login", "files": ["src/auth.py", "src/user.py"]},
    {"scenario": "bad password", "files": ["src/auth.py"]},
]


class TestScenarioHashes(unittest.TestCase):
    def test_one_hash_per_scenario(self):
        h = di.scenario_hashes(IR_V1)
        self.assertEqual(set(h), {"valid login", "bad password"})

    def test_hash_changes_with_steps(self):
        h1 = di.scenario_hashes(IR_V1)
        ir2 = {"name": "Login", "scenarios": [
            {"name": "valid login",
             "steps": [{"keyword": "Given", "text": "a DIFFERENT user"}]},
            {"name": "bad password",
             "steps": [{"keyword": "When", "text": "wrong pw"}]},
        ]}
        h2 = di.scenario_hashes(ir2)
        self.assertNotEqual(h1["valid login"], h2["valid login"])
        self.assertEqual(h1["bad password"], h2["bad password"])


class TestBuildMap(unittest.TestCase):
    def test_file_map_reverse_index(self):
        m = di.build_map(IR_V1, FEED, "2026-05-18T1530")
        self.assertEqual(m["file_map"]["src/auth.py"],
                         ["bad password", "valid login"])
        self.assertEqual(m["file_map"]["src/user.py"], ["valid login"])

    def test_map_carries_hashes_and_timestamp(self):
        m = di.build_map(IR_V1, FEED, "2026-05-18T1530")
        self.assertEqual(m["built_at"], "2026-05-18T1530")
        self.assertEqual(set(m["scenario_hashes"]),
                         {"valid login", "bad password"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
