#!/usr/bin/env python3
"""Tests for dae_impact — acceptance-scenario test impact analysis.

Run: python3 -m unittest test_dae_impact -v
"""
import json
import os
import shutil
import tempfile
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


class TestSelect(unittest.TestCase):
    def setUp(self):
        self.m = di.build_map(IR_V1, FEED, "2026-05-18T1530")

    def test_changed_file_selects_its_scenarios(self):
        sel = di.select_scenarios(IR_V1, self.m, ["src/user.py"])
        self.assertEqual(sel, ["valid login"])

    def test_shared_file_selects_all_its_scenarios(self):
        sel = di.select_scenarios(IR_V1, self.m, ["src/auth.py"])
        self.assertEqual(sel, ["bad password", "valid login"])

    def test_spec_changed_scenario_selected_without_file_change(self):
        ir2 = {"name": "Login", "scenarios": [
            {"name": "valid login",
             "steps": [{"keyword": "Given", "text": "a DIFFERENT user"}]},
            {"name": "bad password",
             "steps": [{"keyword": "When", "text": "wrong pw"}]},
        ]}
        sel = di.select_scenarios(ir2, self.m, [])
        self.assertEqual(sel, ["valid login"])

    def test_new_scenario_selected(self):
        ir2 = {"name": "Login", "scenarios": IR_V1["scenarios"] + [
            {"name": "locked out", "steps": [{"keyword": "Given", "text": "x"}]},
        ]}
        sel = di.select_scenarios(ir2, self.m, [])
        self.assertEqual(sel, ["locked out"])

    def test_unmapped_source_file_returns_all(self):
        sel = di.select_scenarios(IR_V1, self.m, ["src/brandnew.py"])
        self.assertEqual(sel, "ALL")

    def test_non_source_change_ignored(self):
        sel = di.select_scenarios(IR_V1, self.m, ["README.md"])
        self.assertEqual(sel, [])

    def test_missing_map_returns_all(self):
        self.assertEqual(di.select_scenarios(IR_V1, None, ["src/user.py"]),
                         "ALL")


def _feature_dir(ir):
    """A temp feature dir with .build/spec.json written. Caller cleans up."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".build"))
    with open(os.path.join(d, ".build", "spec.json"), "w", encoding="utf-8") as f:
        json.dump(ir, f)
    return d


class TestCli(unittest.TestCase):
    def test_build_writes_map(self):
        d = _feature_dir(IR_V1)
        self.addCleanup(shutil.rmtree, d)
        feed_path = os.path.join(d, "feed.json")
        with open(feed_path, "w", encoding="utf-8") as f:
            json.dump(FEED, f)
        rc = di.main(["build", d, feed_path])
        self.assertEqual(rc, 0)
        with open(os.path.join(d, ".build", "impact-map.json")) as f:
            m = json.load(f)
        self.assertIn("src/auth.py", m["file_map"])

    def test_build_missing_ir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        self.assertEqual(di.main(["build", d, "nope.json"]), 2)

    def test_load_map_absent(self):
        d = _feature_dir(IR_V1)
        self.addCleanup(shutil.rmtree, d)
        self.assertIsNone(di.load_map(d))


if __name__ == "__main__":
    unittest.main(verbosity=2)
