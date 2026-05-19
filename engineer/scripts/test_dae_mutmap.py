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


class UpdateTests(unittest.TestCase):
    def test_fresh_entry_for_mutated_function(self):
        manifest = _manifest({})
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        results = {"functions": {"m::f": {"last_mutated": "2026-05-19",
                   "mutants_total": 8, "mutants_killed": 7, "survivors": []}}}
        out = dae_mutmap.update(manifest, feed, results)
        self.assertEqual(out["functions"]["m::f"]["code_hash"], "c1")
        self.assertEqual(out["functions"]["m::f"]["mutants_killed"], 7)
        self.assertEqual(out["rules_hash"], "rules-v1")
        self.assertEqual(out["manifest_version"], 1)

    def test_keeps_cached_entry_for_skipped_function(self):
        manifest = _manifest({"m::f": FN})
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        out = dae_mutmap.update(manifest, feed, {"functions": {}})
        self.assertEqual(out["functions"]["m::f"], FN)

    def test_prunes_orphaned_function(self):
        manifest = _manifest({"m::gone": FN, "m::f": FN})
        feed = _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}})
        out = dae_mutmap.update(manifest, feed, {"functions": {}})
        self.assertNotIn("m::gone", out["functions"])
        self.assertIn("m::f", out["functions"])

    def test_carries_triage_by_line_and_mutation(self):
        old = dict(FN, survivors=[
            {"line": 42, "mutation": ">= -> >", "equivalent": True}])
        manifest = _manifest({"m::f": old})
        feed = _feed({"m::f": {"code_hash": "NEW", "tests_hash": "t1"}})
        results = {"functions": {"m::f": {"last_mutated": "2026-05-19",
                   "mutants_total": 3, "mutants_killed": 2,
                   "survivors": [{"line": 42, "mutation": ">= -> >"}]}}}
        out = dae_mutmap.update(manifest, feed, results)
        self.assertTrue(out["functions"]["m::f"]["survivors"][0]["equivalent"])

    def test_unmatched_survivor_defaults_to_not_equivalent(self):
        old = dict(FN, survivors=[
            {"line": 1, "mutation": "old", "equivalent": True}])
        manifest = _manifest({"m::f": old})
        feed = _feed({"m::f": {"code_hash": "NEW", "tests_hash": "t1"}})
        results = {"functions": {"m::f": {"last_mutated": "2026-05-20",
                   "mutants_total": 1, "mutants_killed": 0,
                   "survivors": [{"line": 99, "mutation": "brand-new"}]}}}
        out = dae_mutmap.update(manifest, feed, results)
        self.assertFalse(out["functions"]["m::f"]["survivors"][0]["equivalent"])


class SerializeTests(unittest.TestCase):
    def test_one_function_per_line(self):
        manifest = _manifest({"m::a": FN, "m::b": FN})
        text = dae_mutmap.serialize(manifest)
        fn_lines = [ln for ln in text.splitlines() if ln.startswith('    "m::')]
        self.assertEqual(len(fn_lines), 2)

    def test_sorted_and_roundtrips(self):
        manifest = _manifest({"m::z": FN, "m::a": FN})
        text = dae_mutmap.serialize(manifest)
        self.assertLess(text.index("m::a"), text.index("m::z"))
        self.assertEqual(json.loads(text), manifest)

    def test_serialize_sorts_survivors(self):
        entry = dict(FN, survivors=[
            {"line": 90, "mutation": "z"}, {"line": 10, "mutation": "a"}])
        manifest = _manifest({"m::f": entry})
        out = json.loads(dae_mutmap.serialize(manifest))
        survivors = out["functions"]["m::f"]["survivors"]
        self.assertEqual([s["line"] for s in survivors], [10, 90])


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


class MainTests(unittest.TestCase):
    def test_help_returns_zero(self):
        self.assertEqual(dae_mutmap.main(["--help"]), 0)

    def test_select_mode_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            mpath, hpath = os.path.join(d, "m.json"), os.path.join(d, "h.json")
            _write(mpath, _manifest({"m::f": FN}))
            _write(hpath, _feed({"m::f": {"code_hash": "NEW", "tests_hash": "t1"}}))
            self.assertEqual(dae_mutmap.main(["select", mpath, hpath]), 0)

    def test_select_mode_handles_missing_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            hpath = os.path.join(d, "h.json")
            _write(hpath, _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}}))
            self.assertEqual(
                dae_mutmap.main(["select", os.path.join(d, "nope.json"), hpath]), 0)

    def test_update_mode_writes_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = os.path.join(d, "m.json")
            hpath = os.path.join(d, "h.json")
            rpath = os.path.join(d, "r.json")
            _write(mpath, _manifest({}))
            _write(hpath, _feed({"m::f": {"code_hash": "c1", "tests_hash": "t1"}}))
            _write(rpath, {"functions": {"m::f": {"last_mutated": "2026-05-19",
                   "mutants_total": 4, "mutants_killed": 4, "survivors": []}}})
            self.assertEqual(dae_mutmap.main(["update", mpath, hpath, rpath]), 0)
            reloaded = dae_mutmap._read_json(mpath)
            self.assertIn("m::f", reloaded["functions"])


if __name__ == "__main__":
    unittest.main()
