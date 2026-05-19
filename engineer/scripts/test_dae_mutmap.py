"""Tests for dae_mutmap.py."""
import json
import os
import tempfile
import unittest

import dae_mutmap


def _manifest(functions, rules_hash="rules-v1"):
    return {"manifest_version": 1, "rules_hash": rules_hash, "functions": functions}


def _feed(functions, rules_hash="rules-v1"):
    return {"rules_hash": rules_hash, "functions": functions}


# A representative cached manifest entry for function m::f.
FN = {"code_hash": "c1", "tests_hash": "t1", "last_mutated": "2026-05-01",
      "mutants_total": 5, "mutants_killed": 5, "survivors": []}


class SelectTests(unittest.TestCase):
    def test_selects_new_function(self):
        manifest = _manifest({})
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        self.assertEqual(dae_mutmap.select(manifest, feed), ["m::f"])

    def test_selects_code_changed(self):
        manifest = _manifest({"m::f": dict(FN, code_hash="OLD")})
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        self.assertEqual(dae_mutmap.select(manifest, feed), ["m::f"])

    def test_selects_tests_changed(self):
        manifest = _manifest({"m::f": dict(FN, tests_hash="OLD")})
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        self.assertEqual(dae_mutmap.select(manifest, feed), ["m::f"])

    def test_skips_unchanged(self):
        manifest = _manifest({"m::f": FN})
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        self.assertEqual(dae_mutmap.select(manifest, feed), [])

    def test_missing_manifest_returns_all(self):
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        self.assertEqual(dae_mutmap.select(None, feed), "ALL")

    def test_version_mismatch_returns_all(self):
        manifest = _manifest({"m::f": FN})
        manifest["manifest_version"] = 999
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        self.assertEqual(dae_mutmap.select(manifest, feed), "ALL")

    def test_rules_hash_mismatch_returns_all(self):
        manifest = _manifest({"m::f": FN}, rules_hash="rules-v1")
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}},
                     rules_hash="rules-v2")
        self.assertEqual(dae_mutmap.select(manifest, feed), "ALL")

    def test_full_returns_all(self):
        manifest = _manifest({"m::f": FN})
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        self.assertEqual(dae_mutmap.select(manifest, feed, full=True), "ALL")


if __name__ == "__main__":
    unittest.main()
