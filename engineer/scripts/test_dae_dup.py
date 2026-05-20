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


class BackendAvailableTests(unittest.TestCase):
    def test_true_when_on_path(self):
        with mock.patch("shutil.which", return_value="/usr/bin/jscpd"):
            self.assertTrue(dae_dup.backend_available("jscpd"))

    def test_false_when_not_on_path(self):
        with mock.patch("shutil.which", return_value=None):
            self.assertFalse(dae_dup.backend_available("jscpd"))


class FindDuplicatesTests(unittest.TestCase):
    def test_skip_short_circuits(self):
        result = dae_dup.find_duplicates(
            "/tmp/proj", {"duplication": {"skip": True}})
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["duplicates"], [])

    def test_unavailable_when_tool_missing(self):
        with mock.patch("shutil.which", return_value=None):
            result = dae_dup.find_duplicates("/tmp/proj", {})
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("jscpd", result.get("reason", ""))
        self.assertIn("npm install", result.get("install", ""))
        self.assertEqual(result["duplicates"], [])

    def test_unsupported_backend(self):
        with mock.patch("shutil.which", return_value="/x/pmd-cpd"):
            result = dae_dup.find_duplicates(
                "/tmp/proj", {"duplication": {"tool": "pmd-cpd"}})
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["duplicates"], [])

    def test_jscpd_path_runs_and_normalizes(self):
        # Real jscpd writes its report to <output>/jscpd-report.json with
        # --silent --reporters json. Simulate by pre-creating that file.
        with tempfile.TemporaryDirectory() as d:
            report_dir = os.path.join(d, ".build", "jscpd")
            os.makedirs(report_dir)
            with open(os.path.join(report_dir, "jscpd-report.json"), "w") as f:
                json.dump(JSCPD_RAW, f)
            fake_run = mock.MagicMock(
                return_value=mock.MagicMock(returncode=0, stdout="", stderr=""))
            with mock.patch("shutil.which", return_value="/x/jscpd"), \
                 mock.patch("subprocess.run", fake_run):
                result = dae_dup.find_duplicates(d, {})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["duplicates"]), 2)
        self.assertEqual(result["duplicates"][0]["tokens"], 75)

    def test_error_when_subprocess_fails(self):
        # OSError on subprocess.run (e.g. permission denied) should surface
        # as status: error, not silently empty status: ok.
        with mock.patch("shutil.which", return_value="/x/jscpd"), \
             mock.patch("subprocess.run", side_effect=OSError("permission denied")):
            result = dae_dup.find_duplicates("/tmp/proj", {})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["duplicates"], [])

    def test_error_when_report_missing(self):
        # Subprocess returns 0 but produces no report file.
        with tempfile.TemporaryDirectory() as d:
            fake_run = mock.MagicMock(
                return_value=mock.MagicMock(returncode=0, stdout="", stderr=""))
            with mock.patch("shutil.which", return_value="/x/jscpd"), \
                 mock.patch("subprocess.run", fake_run):
                result = dae_dup.find_duplicates(d, {})
        self.assertEqual(result["status"], "error")


class MainTests(unittest.TestCase):
    def test_help_returns_zero(self):
        self.assertEqual(dae_dup.main(["--help"]), 0)

    def test_no_args_returns_zero(self):
        self.assertEqual(dae_dup.main([]), 0)


if __name__ == "__main__":
    unittest.main()
