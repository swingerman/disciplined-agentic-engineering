"""Tests for dae_dup.py."""
import json
import os
import tempfile
import unittest
from unittest import mock

import dae_dup


# A captured jscpd JSON output fragment — two duplicate blocks across two files.
JSCPD_RAW = {
    "duplicates": [
        {
            "firstFile": {"name": "src/a.py", "start": 10, "end": 30},
            "secondFile": {"name": "src/b.py", "start": 50, "end": 70},
            "tokens": 75,
            "lines": 20,
        },
        {
            "firstFile": {"name": "src/c.py", "start": 1, "end": 8},
            "secondFile": {"name": "src/d.py", "start": 100, "end": 107},
            "tokens": 60,
            "lines": 7,
        },
    ]
}


class IsSkippedTests(unittest.TestCase):
    def test_true_when_set(self):
        self.assertTrue(dae_dup.is_skipped({"duplication": {"skip": True}}))

    def test_false_when_unset(self):
        self.assertFalse(dae_dup.is_skipped({}))
        self.assertFalse(dae_dup.is_skipped({"duplication": {}}))
        self.assertFalse(dae_dup.is_skipped({"duplication": {"skip": False}}))

    def test_handles_none_manifest(self):
        self.assertFalse(dae_dup.is_skipped(None))

    def test_handles_non_dict_section(self):
        self.assertFalse(dae_dup.is_skipped({"duplication": "yes"}))


class ResolvedConfigTests(unittest.TestCase):
    def test_defaults(self):
        cfg = dae_dup.resolved_config({})
        self.assertEqual(cfg["tool"], "jscpd")
        self.assertEqual(cfg["min_tokens"], 50)
        self.assertEqual(cfg["min_lines"], 5)

    def test_overrides_from_manifest(self):
        m = {"duplication": {"tool": "pmd-cpd", "min_tokens": 100, "min_lines": 10}}
        cfg = dae_dup.resolved_config(m)
        self.assertEqual(cfg["tool"], "pmd-cpd")
        self.assertEqual(cfg["min_tokens"], 100)
        self.assertEqual(cfg["min_lines"], 10)


class NormalizeJscpdTests(unittest.TestCase):
    def test_shape(self):
        out = dae_dup.normalize_jscpd(JSCPD_RAW)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["tokens"], 75)
        self.assertEqual(out[0]["lines"], 20)
        self.assertEqual(out[0]["files"][0], {"path": "src/a.py", "lines": [10, 30]})
        self.assertEqual(out[0]["files"][1], {"path": "src/b.py", "lines": [50, 70]})

    def test_empty(self):
        self.assertEqual(dae_dup.normalize_jscpd({"duplicates": []}), [])
        self.assertEqual(dae_dup.normalize_jscpd({}), [])


if __name__ == "__main__":
    unittest.main()
