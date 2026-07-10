#!/usr/bin/env python3
"""Tests for dae_release — the plugin release + cache-sync automation.

Run: python3 test_dae_release.py

All filesystem roots are redirected to a tmp fixture; the real ~/.claude is
never touched.
"""
import json
import os
import tempfile
import unittest

import dae_release as dr


def _setup(tmp):
    mk_root = os.path.join(tmp, "marketplaces")
    cache_root = os.path.join(tmp, "cache")
    src = os.path.join(mk_root, "my-mp", "engineer")
    os.makedirs(os.path.join(src, ".claude-plugin"))
    os.makedirs(os.path.join(src, "scripts"))
    with open(os.path.join(src, ".claude-plugin", "plugin.json"), "w") as f:
        f.write('{\n  "name": "engineer",\n  "version": "0.20.0",\n'
                '  "description": "d"\n}\n')
    with open(os.path.join(src, "scripts", "x.py"), "w") as f:
        f.write("print(1)\n")
    installed = os.path.join(tmp, "installed_plugins.json")
    with open(installed, "w") as f:
        json.dump({"version": 1, "plugins": {"engineer@my-mp": [
            {"scope": "user", "installPath": "/old/0.20.0",
             "version": "0.20.0", "lastUpdated": "2026-01-01"}]}}, f, indent=1)
    return mk_root, cache_root, installed, src


class TestPureHelpers(unittest.TestCase):
    def test_bump(self):
        self.assertEqual(dr.bump_version("0.20.0", "patch"), "0.20.1")
        self.assertEqual(dr.bump_version("0.20.3", "minor"), "0.21.0")
        self.assertEqual(dr.bump_version("1.4.9", "major"), "2.0.0")

    def test_bump_bad(self):
        with self.assertRaises(dr.ReleaseError):
            dr.bump_version("nope", "patch")

    def test_set_plugin_version_targeted(self):
        text = '{\n  "name": "x",\n  "version": "0.1.0",\n  "keywords": ["v0.1"]\n}'
        out = dr._set_plugin_version(text, "0.2.0")
        self.assertIn('"version": "0.2.0"', out)
        self.assertIn('"keywords": ["v0.1"]', out)  # only the version field changed


class TestPlan(unittest.TestCase):
    def test_plan_computes_bump_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk, cache, _, _ = _setup(tmp)
            pl = dr.plan_release("engineer", level="minor",
                                 marketplaces=mk, cache=cache)
            self.assertEqual(pl["current_version"], "0.20.0")
            self.assertEqual(pl["new_version"], "0.21.0")
            self.assertTrue(pl["cache_dir"].endswith("engineer/0.21.0"))
            self.assertEqual(pl["installed_key"], "engineer@my-mp")
            self.assertFalse(pl["cache_exists"])

    def test_plan_set_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk, cache, _, _ = _setup(tmp)
            pl = dr.plan_release("engineer", set_version="1.2.3",
                                 marketplaces=mk, cache=cache)
            self.assertEqual(pl["new_version"], "1.2.3")

    def test_unknown_plugin_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk, cache, _, _ = _setup(tmp)
            with self.assertRaises(dr.ReleaseError):
                dr.plan_release("ghost", marketplaces=mk, cache=cache)


class TestApply(unittest.TestCase):
    def test_apply_full_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk, cache, installed, src = _setup(tmp)
            pl = dr.plan_release("engineer", level="patch",
                                 marketplaces=mk, cache=cache)
            res = dr.apply_release(pl, installed_path=installed)

            self.assertTrue(res["verified"])
            self.assertTrue(res["applied"])
            self.assertTrue(res["repointed"])
            # cache dir built with bumped plugin.json + copied content
            cache_pj = os.path.join(pl["cache_dir"], ".claude-plugin", "plugin.json")
            self.assertEqual(json.load(open(cache_pj))["version"], "0.20.1")
            self.assertTrue(os.path.isfile(
                os.path.join(pl["cache_dir"], "scripts", "x.py")))
            # source plugin.json bumped
            self.assertIn('"version": "0.20.1"', open(pl["plugin_json"]).read())
            # install manifest repointed + backed up
            m = json.load(open(installed))
            entry = m["plugins"]["engineer@my-mp"][0]
            self.assertEqual(entry["version"], "0.20.1")
            self.assertTrue(entry["installPath"].endswith("engineer/0.20.1"))
            self.assertTrue(os.path.isfile(installed + ".bak"))

    def test_apply_refuses_existing_cache_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk, cache, installed, _ = _setup(tmp)
            pl = dr.plan_release("engineer", marketplaces=mk, cache=cache)
            os.makedirs(pl["cache_dir"])  # pre-existing
            pl["cache_exists"] = True
            with self.assertRaises(dr.ReleaseError):
                dr.apply_release(pl, installed_path=installed)

    def test_apply_force_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk, cache, installed, _ = _setup(tmp)
            pl = dr.plan_release("engineer", marketplaces=mk, cache=cache)
            os.makedirs(pl["cache_dir"])
            pl["cache_exists"] = True
            res = dr.apply_release(pl, installed_path=installed, force=True)
            self.assertTrue(res["verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
