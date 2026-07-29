"""Tests for dae_ontology.py."""
import os
import tempfile
import unittest

import dae_ontology


def _feature(root, name, fm_lines, acs=None, spec=None, handoffs=None):
    """Create features/<name>/ with the given artifacts. Returns its path."""
    d = os.path.join(root, "features", name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "feature.md"), "w", encoding="utf-8") as f:
        f.write("---\n" + "\n".join(fm_lines) + "\n---\n\n# Feature\n")
    if acs is not None:
        with open(os.path.join(d, "acs.md"), "w", encoding="utf-8") as f:
            f.write(acs)
    if spec is not None:
        with open(os.path.join(d, "spec.md"), "w", encoding="utf-8") as f:
            f.write(spec)
    for fname, body in (handoffs or {}).items():
        hdir = os.path.join(d, "handoffs")
        os.makedirs(hdir, exist_ok=True)
        with open(os.path.join(hdir, fname), "w", encoding="utf-8") as f:
            f.write(body)
    return d


def _project(root):
    """Make root a methodology root."""
    os.makedirs(os.path.join(root, ".engineer"), exist_ok=True)
    with open(os.path.join(root, ".engineer", "manifest.yml"), "w",
              encoding="utf-8") as f:
        f.write("methodology_version: '0.2'\nproject_name: t\n")


def _codes(findings):
    return {(f["constraint"], f["severity"]) for f in findings}


def _msgs(findings):
    return " | ".join(f["message"] for f in findings)


OK_FM = ["slug: 010-thing", "status: ready", "autonomy_level: medium"]


class EnumerationTests(unittest.TestCase):
    def test_clean_feature_has_no_findings(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM)
            self.assertEqual(dae_ontology.check_feature(feat), [])

    def test_invented_status_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing",
                            ["slug: 010-thing", "status: probably-shipped",
                             "autonomy_level: medium"])
            out = dae_ontology.check_feature(feat)
        self.assertIn(("enumeration", "error"), _codes(out))
        self.assertIn("probably-shipped", _msgs(out))

    def test_bad_assignee_and_autonomy_are_errors(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing",
                            ["slug: 010-thing", "status: ready",
                             "autonomy_level: extreme", "assignee: robot"])
            out = dae_ontology.check_feature(feat)
        self.assertEqual(
            2, len([f for f in out if f["constraint"] == "enumeration"]))

    def test_merged_unverified_is_a_legal_status(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing",
                            ["slug: 010-thing", "status: merged-unverified",
                             "autonomy_level: high"])
            self.assertEqual(dae_ontology.check_feature(feat), [])

    def test_handoff_checkpoint_must_be_a_pipeline_stop(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM, handoffs={
                "a.md": "---\nskill: plan\ncheckpoint: 9\nstatus: complete\n---\n"})
            out = dae_ontology.check_feature(feat)
        self.assertIn(("enumeration", "error"), _codes(out))


class FunctionalTests(unittest.TestCase):
    def test_non_parked_requires_autonomy_level(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", ["slug: 010-thing", "status: ready"])
            out = dae_ontology.check_feature(feat)
        self.assertIn(("functional", "error"), _codes(out))

    def test_parked_needs_no_autonomy_level(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", ["slug: 010-thing", "status: parked"])
            self.assertEqual(dae_ontology.check_feature(feat), [])

    def test_slug_must_match_folder(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing",
                            ["slug: 011-other", "status: ready",
                             "autonomy_level: low"])
            out = dae_ontology.check_feature(feat)
        self.assertIn(("functional", "error"), _codes(out))

    def test_ac_count_must_match_acs_md(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM + ["ac_count: 5"],
                            acs="## AC-1: a\n\n## AC-2: b\n")
            out = dae_ontology.check_feature(feat)
        self.assertIn("ac_count: 5 but acs.md declares 2", _msgs(out))

    def test_branch_claimed_by_two_features(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "010-a", ["slug: 010-a", "status: ready",
                                  "autonomy_level: low", "branch: shared"])
            _feature(d, "011-b", ["slug: 011-b", "status: ready",
                                  "autonomy_level: low", "branch: shared"])
            out = dae_ontology.check_project(d)
        self.assertIn("branch 'shared' is claimed by 2 features", _msgs(out))

    def test_roadmap_item_claimed_twice(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "010-a", ["slug: 010-a", "status: ready",
                                  "autonomy_level: low", "roadmap_ref: export"])
            _feature(d, "011-b", ["slug: 011-b", "status: ready",
                                  "autonomy_level: low", "roadmap_ref: export"])
            out = dae_ontology.check_project(d)
        self.assertIn("roadmap item 'export' is claimed by 2", _msgs(out))


class ClosureTests(unittest.TestCase):
    SPEC = ("Feature: t\n\n  @AC-1 @x\n  Scenario: one\n    Given a\n\n"
            "  @AC-2\n  Scenario: two\n    Given b\n")

    def test_full_coverage_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM + ["ac_count: 2"],
                            acs="## AC-1: a\n\n## AC-2: b\n", spec=self.SPEC)
            self.assertEqual(dae_ontology.check_feature(feat), [])

    def test_uncovered_ac_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM + ["ac_count: 3"],
                            acs="## AC-1: a\n\n## AC-2: b\n\n## AC-3: c\n",
                            spec=self.SPEC)
            out = dae_ontology.check_feature(feat)
        self.assertIn(("closure", "error"), _codes(out))
        self.assertIn("AC-3", _msgs(out))

    def test_dangling_spec_tag_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM + ["ac_count: 1"],
                            acs="## AC-1: a\n", spec=self.SPEC)
            out = dae_ontology.check_feature(feat)
        self.assertIn("does not define: AC-2", _msgs(out))

    def test_no_spec_yet_is_not_a_coverage_error(self):
        # CP2 output with no CP3 spec yet must not be flagged.
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM + ["ac_count: 2"],
                            acs="## AC-1: a\n\n## AC-2: b\n")
            self.assertEqual(dae_ontology.check_feature(feat), [])

    def test_untagged_spec_warns_once_not_per_ac(self):
        # A project not using the @AC-N convention gets one warning, not N
        # errors — non-adoption is a choice, partial adoption is a gap.
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM + ["ac_count: 3"],
                            acs="## AC-1: a\n\n## AC-2: b\n\n## AC-3: c\n",
                            spec="Feature: t\n\n  Scenario: one\n    Given a\n")
            out = dae_ontology.check_feature(feat)
        self.assertEqual(1, len(out))
        self.assertEqual("warning", out[0]["severity"])
        self.assertIn("no @AC-N tags", out[0]["message"])

    def test_long_uncovered_list_is_abbreviated(self):
        acs = "\n\n".join("## AC-%d: x" % n for n in range(1, 21))
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM + ["ac_count: 20"], acs=acs,
                            spec="Feature: t\n\n  @AC-1\n  Scenario: one\n"
                                 "    Given a\n")
            out = dae_ontology.check_feature(feat)
        self.assertIn("(+11 more)", _msgs(out))

    def test_bare_slug_still_matches_folder(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "012-washer-tracking",
                            ["slug: washer-tracking", "status: ready",
                             "autonomy_level: low"])
            self.assertEqual(dae_ontology.check_feature(feat), [])


class InverseAndTransitiveTests(unittest.TestCase):
    def test_agreeing_parent_child_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "007-parent", ["slug: 007-parent", "status: ready",
                                       "autonomy_level: low",
                                       "child_features:", "  - 008-child"])
            _feature(d, "008-child", ["slug: 008-child", "status: ready",
                                      "autonomy_level: low",
                                      "parent_feature: 007-parent"])
            self.assertEqual(dae_ontology.check_project(d), [])

    def test_half_linked_parent_is_a_warning(self):
        # The link exists and resolves; only the back-reference is missing.
        # Real repos accumulate these, and nothing downstream breaks.
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "007-parent", ["slug: 007-parent", "status: ready",
                                       "autonomy_level: low"])
            _feature(d, "008-child", ["slug: 008-child", "status: ready",
                                      "autonomy_level: low",
                                      "parent_feature: 007-parent"])
            out = dae_ontology.check_project(d)
        self.assertIn(("inverse", "warning"), _codes(out))
        self.assertFalse([f for f in out if f["severity"] == "error"])

    def test_parent_pointing_at_missing_feature_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "008-child", ["slug: 008-child", "status: ready",
                                      "autonomy_level: low",
                                      "parent_feature: 999-ghost"])
            out = dae_ontology.check_project(d)
        self.assertIn(("inverse", "error"), _codes(out))
        self.assertIn("does not resolve", _msgs(out))

    def test_bare_slug_references_resolve(self):
        # `parent_feature: parent` and folder `007-parent` are the same feature.
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "007-parent", ["slug: parent", "status: ready",
                                       "autonomy_level: low",
                                       "child_features:", "  - child"])
            _feature(d, "008-child", ["slug: child", "status: ready",
                                      "autonomy_level: low",
                                      "parent_feature: parent"])
            self.assertEqual(dae_ontology.check_project(d), [])

    def test_cycle_detected_through_bare_slugs(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "010-a", ["slug: a", "status: ready",
                                  "autonomy_level: low", "parent_feature: b",
                                  "child_features:", "  - b"])
            _feature(d, "011-b", ["slug: b", "status: ready",
                                  "autonomy_level: low", "parent_feature: a",
                                  "child_features:", "  - a"])
            out = dae_ontology.check_project(d)
        self.assertIn(("transitive", "error"), _codes(out))


class BranchTests(unittest.TestCase):
    def test_shared_trunk_is_not_flagged(self):
        # A multi-repo umbrella runs every feature off master.
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            for n in ("010-a", "011-b", "012-c"):
                _feature(d, n, ["slug: %s" % n, "status: ready",
                                "autonomy_level: low", "branch: master"])
            self.assertEqual(dae_ontology.check_project(d), [])

    def test_shared_feature_branch_is_a_warning(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "010-a", ["slug: 010-a", "status: ready",
                                  "autonomy_level: low", "branch: design/x"])
            _feature(d, "011-b", ["slug: 011-b", "status: ready",
                                  "autonomy_level: low", "branch: design/x"])
            out = dae_ontology.check_project(d)
        self.assertIn(("functional", "warning"), _codes(out))
        self.assertFalse([f for f in out if f["severity"] == "error"])

    def test_parent_cycle_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "010-a", ["slug: 010-a", "status: ready",
                                  "autonomy_level: low",
                                  "parent_feature: 011-b",
                                  "child_features:", "  - 011-b"])
            _feature(d, "011-b", ["slug: 011-b", "status: ready",
                                  "autonomy_level: low",
                                  "parent_feature: 010-a",
                                  "child_features:", "  - 010-a"])
            out = dae_ontology.check_project(d)
        self.assertIn(("transitive", "error"), _codes(out))

    def test_reused_feature_number_is_a_warning(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "010-a", ["slug: 010-a", "status: ready",
                                  "autonomy_level: low"])
            _feature(d, "010-b", ["slug: 010-b", "status: ready",
                                  "autonomy_level: low"])
            out = dae_ontology.check_project(d)
        self.assertIn(("functional", "warning"), _codes(out))
        self.assertFalse([f for f in out if f["severity"] == "error"])


class DisjointTests(unittest.TestCase):
    def test_self_verification_is_flagged(self):
        impl = ("---\nskill: implement\ncheckpoint: 5\nagent_id: subagent-1\n"
                "status: complete\n---\n")
        ver = ("---\nskill: verify\ncheckpoint: 7\nagent_id: subagent-1\n"
               "status: complete\n---\n")
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM,
                            handoffs={"a-impl.md": impl, "b-ver.md": ver})
            out = dae_ontology.check_feature(feat)
        self.assertIn(("disjoint", "error"), _codes(out))
        self.assertIn("same agent", _msgs(out))


class MainTests(unittest.TestCase):
    def test_help_returns_zero(self):
        self.assertEqual(dae_ontology.main(["--help"]), 0)

    def test_no_args_returns_zero(self):
        self.assertEqual(dae_ontology.main([]), 0)

    def test_missing_target_returns_two(self):
        self.assertEqual(dae_ontology.main(["/nonexistent/xyz"]), 2)

    def test_clean_feature_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing", OK_FM)
            self.assertEqual(dae_ontology.main([feat]), 0)

    def test_violation_exits_one(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _feature(d, "010-thing",
                            ["slug: 010-thing", "status: bogus"])
            self.assertEqual(dae_ontology.main([feat, "--json"]), 1)

    def test_project_scope_runs(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "010-a", ["slug: 010-a", "status: ready",
                                  "autonomy_level: low"])
            self.assertEqual(dae_ontology.main(["--project", d]), 0)

    def test_warning_only_still_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            _project(d)
            _feature(d, "010-a", ["slug: 010-a", "status: ready",
                                  "autonomy_level: low"])
            _feature(d, "010-b", ["slug: 010-b", "status: ready",
                                  "autonomy_level: low"])
            self.assertEqual(dae_ontology.main(["--project", d]), 0)


if __name__ == "__main__":
    unittest.main()
