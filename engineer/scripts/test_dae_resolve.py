#!/usr/bin/env python3
"""Tests for dae_resolve — the scoped manifest reader, root resolution, validation.

Run: python3 test_dae_resolve.py
"""

import os
import tempfile
import unittest

import dae_resolve as dr


# A complete, valid manifest exercising every construct the reader supports.
VALID_MANIFEST = '''\
# DAE manifest — test fixture
methodology_version: "0.2"
methodology_root: ./
charter: CHARTER.md
features_root: features/

roadmap:
  type: notion
  url: https://www.notion.so/abc123
tracker:
  type: notion
  database_id: abc123

team:
  default_roles:
    - architect
    - implementer
    - reviewer
    - verifier

repos:
  - name: api
    path: ./api
    quality_thresholds:
      coverage_min: 90
  - name: web
    path: ./web

quality_thresholds:
  crap_max: 30
  coverage_min: 80
  mutation_score_min: 70

mutation:
  scope: changed_files
  cadence: on_demand
  default_per_feature: opt_in

verification:
  enforce_independence: true
  apply_to_checkpoints: [7, 8]

autonomy:
  default_level: medium
  allowed_levels: [low, medium, high]
  path_overrides:
    - paths: ["src/payments/**"]
      max_level: low

agentic_summary:
  storage: handoffs/
  format: markdown
'''


class TestScalarParsing(unittest.TestCase):
    def test_types(self):
        self.assertEqual(dr._parse_scalar('"0.2"'), "0.2")
        self.assertEqual(dr._parse_scalar("30"), 30)
        self.assertEqual(dr._parse_scalar("true"), True)
        self.assertEqual(dr._parse_scalar("false"), False)
        self.assertEqual(dr._parse_scalar("null"), None)
        self.assertEqual(dr._parse_scalar("CHARTER.md"), "CHARTER.md")
        self.assertEqual(dr._parse_scalar("changed_files"), "changed_files")

    def test_inline_lists(self):
        self.assertEqual(dr._parse_scalar("[7, 8]"), [7, 8])
        self.assertEqual(dr._parse_scalar("[low, medium, high]"),
                         ["low", "medium", "high"])
        self.assertEqual(dr._parse_scalar('["src/payments/**"]'),
                         ["src/payments/**"])
        self.assertEqual(dr._parse_scalar("[]"), [])

    def test_url_scalar_kept_intact(self):
        self.assertEqual(dr._parse_scalar("https://www.notion.so/abc"),
                         "https://www.notion.so/abc")


class TestCommentStripping(unittest.TestCase):
    def test_whole_line_and_trailing(self):
        self.assertEqual(dr._strip_comment("# whole line").strip(), "")
        self.assertEqual(dr._strip_comment("key: value  # trailing").strip(),
                         "key: value")

    def test_hash_inside_quotes_kept(self):
        self.assertEqual(dr._strip_comment('k: "a#b"').strip(), 'k: "a#b"')


class TestManifestReader(unittest.TestCase):
    def setUp(self):
        self.m = dr.read_manifest(VALID_MANIFEST)

    def test_scalars(self):
        self.assertEqual(self.m["methodology_version"], "0.2")
        self.assertEqual(self.m["charter"], "CHARTER.md")

    def test_nested_map(self):
        self.assertEqual(self.m["roadmap"]["type"], "notion")
        self.assertEqual(self.m["tracker"]["database_id"], "abc123")

    def test_list_of_scalars(self):
        self.assertEqual(self.m["team"]["default_roles"],
                         ["architect", "implementer", "reviewer", "verifier"])

    def test_list_of_maps_with_nested_map(self):
        repos = self.m["repos"]
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["name"], "api")
        self.assertEqual(repos[0]["path"], "./api")
        self.assertEqual(repos[0]["quality_thresholds"]["coverage_min"], 90)
        self.assertEqual(repos[1]["name"], "web")
        self.assertNotIn("quality_thresholds", repos[1])

    def test_inline_list_values(self):
        self.assertEqual(self.m["verification"]["apply_to_checkpoints"], [7, 8])
        self.assertEqual(self.m["autonomy"]["allowed_levels"],
                         ["low", "medium", "high"])

    def test_bool(self):
        self.assertEqual(self.m["verification"]["enforce_independence"], True)

    def test_path_overrides(self):
        ov = self.m["autonomy"]["path_overrides"]
        self.assertEqual(ov[0]["paths"], ["src/payments/**"])
        self.assertEqual(ov[0]["max_level"], "low")

    def test_numbers(self):
        self.assertEqual(self.m["quality_thresholds"]["crap_max"], 30)

    def test_empty_manifest(self):
        self.assertEqual(dr.read_manifest("# only a comment\n"), {})


class TestValidation(unittest.TestCase):
    def test_valid_manifest_passes(self):
        errors, warnings = dr.validate_manifest(dr.read_manifest(VALID_MANIFEST))
        self.assertEqual(errors, [])

    def test_missing_required_field(self):
        m = dr.read_manifest(VALID_MANIFEST)
        del m["methodology_version"]
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("methodology_version" in e for e in errors))

    def test_missing_tracker_type(self):
        m = dr.read_manifest(VALID_MANIFEST)
        del m["tracker"]["type"]
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("tracker.type" in e for e in errors))

    def test_bad_enum(self):
        m = dr.read_manifest(VALID_MANIFEST)
        m["tracker"]["type"] = "trello"
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("tracker.type" in e for e in errors))

    def test_bad_autonomy_level(self):
        m = dr.read_manifest(VALID_MANIFEST)
        m["autonomy"]["default_level"] = "extreme"
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("autonomy.default_level" in e for e in errors))

    def test_quality_threshold_out_of_range(self):
        m = dr.read_manifest(VALID_MANIFEST)
        m["quality_thresholds"]["coverage_min"] = 150
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("coverage_min" in e for e in errors))

    def test_verifier_role_required_when_independence_enforced(self):
        m = dr.read_manifest(VALID_MANIFEST)
        m["team"]["default_roles"] = ["architect", "implementer", "reviewer"]
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("verifier" in e for e in errors))

    def test_unknown_version_warns_not_errors(self):
        m = dr.read_manifest(VALID_MANIFEST)
        m["methodology_version"] = "9.9"
        errors, warnings = dr.validate_manifest(m)
        self.assertEqual(errors, [])
        self.assertTrue(any("9.9" in w for w in warnings))


class TestResolution(unittest.TestCase):
    def test_finds_manifest_walking_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".engineer"))
            with open(os.path.join(tmp, ".engineer", "manifest.yml"), "w") as fh:
                fh.write(VALID_MANIFEST)
            deep = os.path.join(tmp, "packages", "api", "src")
            os.makedirs(deep)
            root, path = dr.find_methodology_root(deep)
            self.assertEqual(os.path.realpath(root), os.path.realpath(tmp))
            self.assertTrue(path.endswith(".engineer/manifest.yml"))

    def test_no_manifest_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, path = dr.find_methodology_root(tmp)
            self.assertIsNone(root)
            self.assertIsNone(path)

    def test_resolve_full_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".engineer"))
            with open(os.path.join(tmp, ".engineer", "manifest.yml"), "w") as fh:
                fh.write(VALID_MANIFEST)
            result = dr.resolve(tmp)
            self.assertTrue(result["valid"])
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["manifest"]["tracker"]["type"], "notion")


class TestExtractFrontmatter(unittest.TestCase):
    def test_extract(self):
        block = dr.extract_frontmatter("---\nslug: alpha\n---\n\n# Heading\n")
        self.assertIn("slug: alpha", block)
        self.assertNotIn("# Heading", block)

    def test_no_frontmatter(self):
        self.assertIsNone(dr.extract_frontmatter("# Just a heading\n"))

    def test_unterminated(self):
        self.assertIsNone(dr.extract_frontmatter("---\nslug: alpha\n"))


class TestArchitectureValidation(unittest.TestCase):
    def test_layer_missing_name(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "architecture": {"layers": [{"paths": ["src/**"]}]}}
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("architecture.layers" in e for e in errors))

    def test_bad_file_size(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "architecture": {"file_size": {"max_lines": -3}}}
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("file_size" in e for e in errors))

    def test_valid_architecture_ok(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "architecture": {
                 "layers": [{"name": "domain", "paths": ["src/domain/**"]}],
                 "file_size": {"max_lines": 400}}}
        errors, _ = dr.validate_manifest(m)
        self.assertEqual([e for e in errors if "architecture" in e], [])


class TestImpactAnalysisFlag(unittest.TestCase):
    def test_bad_value_rejected(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "acceptance": {"impact_analysis": "maybe"}}
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("impact_analysis" in e for e in errors))

    def test_valid_value_ok(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "acceptance": {"impact_analysis": "on"}}
        errors, _ = dr.validate_manifest(m)
        self.assertEqual([e for e in errors if "impact_analysis" in e], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
