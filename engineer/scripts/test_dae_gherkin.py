#!/usr/bin/env python3
"""Tests for dae_gherkin — the spec.md -> JSON IR parser.

Run: python3 test_dae_gherkin.py
"""

import unittest

import dae_gherkin as dg


BASIC = '''\
# Some markdown title — ignored as prose

Feature: Customer data export

A paragraph of description. Also ignored.

Scenario: Customer exports their data
  Given there are no registered users
  When a user registers with email "bob@example.com"
  Then there is 1 registered user
  And the user "bob@example.com" can log in
'''

WITH_BACKGROUND = '''\
Feature: Tokens

Background:
  Given a configured project

Scenario: Create a token
  When the user creates a token
  Then 1 token exists
'''

OUTLINE = '''\
Feature: Aspect ratios

## Scenario: Generate at an aspect

  Given a background image
  When the caller generates with aspect <aspect>
  Then the image is <width> by <height>

  Examples:
    | aspect  | width | height |
    | square  | 1080  | 1080   |
    | portrait| 1080  | 1350   |
'''

REPEATED_PARAMS = '''\
Feature: F
Scenario: S
  Then <x> equals <x> plus <y>
'''


class TestBasic(unittest.TestCase):
    def setUp(self):
        self.ir = dg.parse_spec(BASIC)

    def test_feature_name(self):
        self.assertEqual(self.ir["name"], "Customer data export")

    def test_prose_and_markdown_ignored(self):
        self.assertEqual(len(self.ir["scenarios"]), 1)

    def test_steps(self):
        steps = self.ir["scenarios"][0]["steps"]
        self.assertEqual(len(steps), 4)
        self.assertEqual(steps[0]["keyword"], "Given")
        self.assertEqual(steps[1]["keyword"], "When")
        self.assertEqual(steps[3]["keyword"], "And")
        self.assertEqual(steps[2]["text"], "there is 1 registered user")

    def test_empty_background_when_none(self):
        self.assertEqual(self.ir["background"], [])

    def test_no_examples(self):
        self.assertEqual(self.ir["scenarios"][0]["examples"], [])


class TestBackground(unittest.TestCase):
    def test_background_steps_collected(self):
        ir = dg.parse_spec(WITH_BACKGROUND)
        self.assertEqual(len(ir["background"]), 1)
        self.assertEqual(ir["background"][0]["text"], "a configured project")
        self.assertEqual(len(ir["scenarios"][0]["steps"]), 2)


class TestOutlineAndExamples(unittest.TestCase):
    def setUp(self):
        self.ir = dg.parse_spec(OUTLINE)

    def test_markdown_heading_keyword(self):
        # `## Scenario:` is recognised after stripping the heading marker
        self.assertEqual(len(self.ir["scenarios"]), 1)
        self.assertEqual(self.ir["scenarios"][0]["name"], "Generate at an aspect")

    def test_examples_rows(self):
        examples = self.ir["scenarios"][0]["examples"]
        self.assertEqual(len(examples), 2)
        self.assertEqual(examples[0], {"aspect": "square", "width": "1080",
                                       "height": "1080"})
        self.assertEqual(examples[1]["aspect"], "portrait")

    def test_example_values_are_strings(self):
        for ex in self.ir["scenarios"][0]["examples"]:
            for v in ex.values():
                self.assertIsInstance(v, str)

    def test_parameters_extracted(self):
        steps = self.ir["scenarios"][0]["steps"]
        self.assertEqual(steps[1]["parameters"], ["aspect"])
        self.assertEqual(steps[2]["parameters"], ["width", "height"])


class TestParameters(unittest.TestCase):
    def test_repeated_params_preserved_in_order(self):
        ir = dg.parse_spec(REPEATED_PARAMS)
        self.assertEqual(ir["scenarios"][0]["steps"][0]["parameters"],
                         ["x", "x", "y"])


class TestErrors(unittest.TestCase):
    def test_no_feature(self):
        with self.assertRaises(dg.GherkinError):
            dg.parse_spec("Scenario: orphan\n  Given x\n")

    def test_examples_outside_scenario(self):
        with self.assertRaises(dg.GherkinError):
            dg.parse_spec("Feature: F\nExamples:\n  | a |\n  | 1 |\n")

    def test_table_row_width_mismatch(self):
        bad = ("Feature: F\nScenario: S\n  Then <a>\n"
               "  Examples:\n    | a | b |\n    | 1 |\n")
        with self.assertRaises(dg.GherkinError):
            dg.parse_spec(bad)

    def test_step_outside_scenario(self):
        with self.assertRaises(dg.GherkinError):
            dg.parse_spec("Feature: F\n  Given a step with no scenario\n")


class TestIRShape(unittest.TestCase):
    def test_top_level_keys(self):
        ir = dg.parse_spec(BASIC)
        self.assertEqual(set(ir.keys()), {"name", "background", "scenarios"})

    def test_step_keys(self):
        step = dg.parse_spec(BASIC)["scenarios"][0]["steps"][0]
        self.assertEqual(set(step.keys()), {"keyword", "text", "parameters"})

    def test_scenario_keys(self):
        sc = dg.parse_spec(BASIC)["scenarios"][0]
        self.assertEqual(set(sc.keys()), {"name", "steps", "examples"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
