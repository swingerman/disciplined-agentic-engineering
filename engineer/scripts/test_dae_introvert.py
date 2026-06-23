#!/usr/bin/env python3
"""Tests for dae_introvert.classify_source — the introversion heuristic."""
import unittest

import dae_introvert as di


def kinds(src):
    return [f["kind"] for f in di.classify_source(src)]


class ClassifyTests(unittest.TestCase):
    def test_top_level_assert_is_clean(self):
        src = "def test_x():\n    y = sut()\n    assert y == 1\n"
        self.assertEqual(di.classify_source(src), [])

    def test_no_assertion_flagged(self):
        src = "def test_x():\n    sut()\n"
        self.assertEqual(kinds(src), ["no-assertion"])

    def test_assert_only_in_if_flagged(self):
        src = ("def test_x():\n"
               "    y = sut()\n"
               "    if y is not None:\n"
               "        assert y == 1\n")
        self.assertEqual(kinds(src), ["conditional-assertion"])

    def test_assert_only_in_for_flagged(self):
        # the user's case: assertions in a loop that may iterate zero times
        src = ("def test_x():\n"
               "    for row in sut():\n"
               "        assert row.ok\n")
        self.assertEqual(kinds(src), ["conditional-assertion"])

    def test_unittest_method_is_clean(self):
        src = ("class T:\n"
               "    def test_x(self):\n"
               "        self.assertEqual(sut(), 1)\n")
        self.assertEqual(di.classify_source(src), [])

    def test_one_guaranteed_assert_rescues_a_conditional_one(self):
        src = ("def test_x():\n"
               "    y = sut()\n"
               "    assert y is not None\n"
               "    if y:\n"
               "        assert y == 1\n")
        self.assertEqual(di.classify_source(src), [])

    def test_pytest_raises_with_block_is_clean(self):
        src = ("def test_x():\n"
               "    with pytest.raises(ValueError):\n"
               "        sut()\n")
        self.assertEqual(di.classify_source(src), [])

    def test_non_test_function_ignored(self):
        src = "def helper():\n    sut()\n"
        self.assertEqual(di.classify_source(src), [])

    def test_syntax_error_yields_nothing(self):
        self.assertEqual(di.classify_source("def test_x(:\n"), [])


if __name__ == "__main__":
    unittest.main()
