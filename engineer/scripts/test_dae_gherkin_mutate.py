#!/usr/bin/env python3
"""Tests for dae_gherkin_mutate — the IR example-value mutator.

Run: python3 test_dae_gherkin_mutate.py
"""

import unittest

import dae_gherkin_mutate as gm


def _rng(path="$.x", original="v"):
    return gm._rng_for(path, original)


class TestValueRules(unittest.TestCase):
    def test_boolean_flips(self):
        self.assertEqual(gm.mutate_value("true", _rng()), "false")
        self.assertEqual(gm.mutate_value("false", _rng()), "true")

    def test_integer_changes_and_stays_integer(self):
        out = gm.mutate_value("20", _rng())
        self.assertNotEqual(out, "20")
        self.assertEqual(out, str(int(out)))

    def test_float_changes(self):
        out = gm.mutate_value("3.14", _rng())
        self.assertNotEqual(out, "3.14")
        float(out)  # still parses as a float

    def test_iso_date_shifts(self):
        out = gm.mutate_value("2026-05-17", _rng())
        self.assertNotEqual(out, "2026-05-17")
        self.assertRegex(out, r"^\d{4}-\d{2}-\d{2}$")

    def test_null_like_becomes_nonempty(self):
        for nullish in ("null", "nil", "none"):
            out = gm.mutate_value(nullish, _rng())
            self.assertTrue(out)
            self.assertNotIn(out.lower(), ("null", "nil", "none"))

    def test_string_dithers(self):
        out = gm.mutate_value("accepted", _rng())
        self.assertNotEqual(out, "accepted")
        self.assertTrue(out)  # non-empty

    def test_comma_list_mutates_one_item(self):
        out = gm.mutate_value("2, 5, 8", _rng())
        self.assertNotEqual(out, "2, 5, 8")
        parts = [p.strip() for p in out.split(",")]
        self.assertEqual(len(parts), 3)
        # exactly one item differs from the original list
        diffs = sum(1 for a, b in zip(parts, ["2", "5", "8"]) if a != b)
        self.assertEqual(diffs, 1)


class TestDeterminism(unittest.TestCase):
    def test_same_path_and_value_give_same_mutation(self):
        a = gm.mutate_value("accepted", gm._rng_for("$.s[0].examples[0].x", "accepted"))
        b = gm.mutate_value("accepted", gm._rng_for("$.s[0].examples[0].x", "accepted"))
        self.assertEqual(a, b)

    def test_enumerate_is_repeatable(self):
        ir = _sample_ir()
        first = gm.enumerate_mutations(ir)
        second = gm.enumerate_mutations(ir)
        self.assertEqual([m["description"] for m in first],
                         [m["description"] for m in second])


def _sample_ir():
    return {
        "name": "Aspect ratios",
        "background": [],
        "scenarios": [
            {
                "name": "Generate",
                "steps": [{"keyword": "Then", "text": "the image is <w> by <h>",
                           "parameters": ["w", "h"]}],
                "examples": [
                    {"w": "1080", "h": "1080"},
                    {"w": "1080", "h": "1350"},
                ],
            }
        ],
    }


class TestEnumerate(unittest.TestCase):
    def setUp(self):
        self.ir = _sample_ir()
        self.mutations = gm.enumerate_mutations(self.ir)

    def test_one_mutation_per_example_cell(self):
        # 2 example rows x 2 keys = 4 cells -> up to 4 mutations
        self.assertLessEqual(len(self.mutations), 4)
        self.assertGreater(len(self.mutations), 0)

    def test_ids_are_sequential(self):
        self.assertEqual([m["id"] for m in self.mutations],
                         ["m%d" % (i + 1) for i in range(len(self.mutations))])

    def test_paths_are_jsonpath(self):
        for m in self.mutations:
            self.assertRegex(m["path"], r"^\$\.scenarios\[\d+\]\.examples\[\d+\]\.\w+$")

    def test_base_ir_not_mutated(self):
        # enumerate deep-copies; the original IR is untouched
        self.assertEqual(self.ir["scenarios"][0]["examples"][0]["w"], "1080")

    def test_each_mutation_changes_exactly_one_cell(self):
        for m in self.mutations:
            mir = m["mutated_ir"]
            diffs = 0
            for si, sc in enumerate(mir["scenarios"]):
                for ei, ex in enumerate(sc["examples"]):
                    for k, v in ex.items():
                        if v != self.ir["scenarios"][si]["examples"][ei][k]:
                            diffs += 1
            self.assertEqual(diffs, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
