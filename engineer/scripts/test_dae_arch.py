#!/usr/bin/env python3
"""Tests for dae_arch — the charter architecture fitness checker.

Run: python3 -m unittest test_dae_arch -v
"""
import os
import shutil
import tempfile
import unittest

import dae_arch as da


class TestGlob(unittest.TestCase):
    def test_star_within_segment(self):
        rx = da._glob_to_regex("src/*.py")
        self.assertTrue(rx.match("src/a.py"))
        self.assertFalse(rx.match("src/sub/a.py"))

    def test_double_star_spans_segments(self):
        rx = da._glob_to_regex("src/**/*.py")
        self.assertTrue(rx.match("src/a.py"))
        self.assertTrue(rx.match("src/x/y/a.py"))
        self.assertFalse(rx.match("lib/a.py"))

    def test_match_any(self):
        globs = da._compile_globs(["src/**", "lib/**"])
        self.assertTrue(da._match_any("src/x/y.py", globs))
        self.assertTrue(da._match_any("lib/z.py", globs))
        self.assertFalse(da._match_any("test/z.py", globs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
