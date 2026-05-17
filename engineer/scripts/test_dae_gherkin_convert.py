#!/usr/bin/env python3
"""Tests for dae_gherkin_convert — legacy atdd .txt -> standard Gherkin.

Run: python3 test_dae_gherkin_convert.py
"""

import unittest

import dae_gherkin_convert as gc
import dae_gherkin as dg

LEGACY = ''';===============================================================
; User can register with email and password.
;===============================================================
GIVEN no registered users.

WHEN a user registers with email "bob@example.com".

THEN there is 1 registered user.
THEN the user "bob@example.com" can log in.

;===============================================================
; Duplicate registration is rejected.
;===============================================================
GIVEN a registered user "bob@example.com".
WHEN a user registers with email "bob@example.com".
THEN the registration is rejected.
'''


class TestConvert(unittest.TestCase):
    def setUp(self):
        self.out = gc.convert(LEGACY, "User Registration")

    def test_has_feature(self):
        self.assertTrue(self.out.startswith("Feature: User Registration"))

    def test_two_scenarios(self):
        self.assertEqual(self.out.count("Scenario:"), 2)
        self.assertIn("Scenario: User can register with email and password", self.out)
        self.assertIn("Scenario: Duplicate registration is rejected", self.out)

    def test_keywords_titlecased(self):
        self.assertIn("  Given no registered users", self.out)
        self.assertIn('  When a user registers with email "bob@example.com"', self.out)
        self.assertIn("  Then there is 1 registered user", self.out)

    def test_repeated_keyword_becomes_and(self):
        # the second THEN in scenario 1 -> And
        self.assertIn('  And the user "bob@example.com" can log in', self.out)

    def test_trailing_periods_stripped(self):
        for line in self.out.splitlines():
            if line.startswith("  "):
                self.assertFalse(line.rstrip().endswith("."),
                                 "step still has trailing period: %r" % line)

    def test_output_parses_as_gherkin(self):
        # the whole point — converter output is valid dae_gherkin input
        ir = dg.parse_spec(self.out)
        self.assertEqual(ir["name"], "User Registration")
        self.assertEqual(len(ir["scenarios"]), 2)
        steps = ir["scenarios"][0]["steps"]
        self.assertEqual([s["keyword"] for s in steps],
                         ["Given", "When", "Then", "And"])


class TestFeatureName(unittest.TestCase):
    def test_from_filename(self):
        self.assertEqual(gc._feature_name("specs/001-core-image-generation.txt"),
                         "001 Core Image Generation")
        self.assertEqual(gc._feature_name("user_registration.txt"),
                         "User Registration")


class TestEdgeCases(unittest.TestCase):
    def test_steps_before_any_name_block(self):
        out = gc.convert("GIVEN a thing.\nWHEN it happens.\nTHEN ok.\n", "F")
        self.assertIn("Scenario:", out)
        ir = dg.parse_spec(out)
        self.assertEqual(len(ir["scenarios"][0]["steps"]), 3)

    def test_explicit_and_keyword(self):
        out = gc.convert("; S\nGIVEN x.\nAND y.\nWHEN z.\nTHEN ok.\n", "F")
        self.assertIn("  And y", out)

    def test_empty_input_returns_none(self):
        self.assertIsNone(gc.convert("", "F"))
        self.assertIsNone(gc.convert("just prose, no spec\n", "F"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
