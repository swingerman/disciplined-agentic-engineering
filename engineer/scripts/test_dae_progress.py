"""Tests for dae_progress.py."""
import os
import tempfile
import unittest

import dae_progress

# A representative progress.md CURRENT header (with the '>' blockquote marker).
CURRENT = "> ▶ CP3 Spec — 2/4 criteria met | NEXT: write spec.md | BLOCKED: none\n"

# A representative Checkpoints table: CP 0, 1.5, 2 done; CP 3 in progress.
TABLE = (
    "## Checkpoints\n"
    "| CP | Stage | Status |\n"
    "|----|-------|--------|\n"
    "| 0 | Onboard | done |\n"
    "| 1.5 | Ready | done |\n"
    "| 2 | ACs | done |\n"
    "| 3 | Spec | in progress |\n"
)


class ParseCurrentHeaderTests(unittest.TestCase):
    def test_extracts_all_fields(self):
        h = dae_progress.parse_current_header(CURRENT)
        self.assertEqual(h["cp"], 3)
        self.assertEqual(h["stage"], "Spec")
        self.assertEqual(h["met"], 2)
        self.assertEqual(h["total"], 4)
        self.assertEqual(h["next"], "write spec.md")
        self.assertEqual(h["blocked"], "none")

    def test_blocked_reason_is_captured(self):
        line = "> ▶ CP4 Plan — 1/3 criteria met | NEXT: revise | BLOCKED: awaiting ADR-012\n"
        h = dae_progress.parse_current_header(line)
        self.assertEqual(h["blocked"], "awaiting ADR-012")

    def test_half_checkpoint_number(self):
        line = "▶ CP1.5 Ready — 1/1 criteria met | NEXT: discover ACs\n"
        h = dae_progress.parse_current_header(line)
        self.assertEqual(h["cp"], 1.5)
        self.assertIsNone(h["blocked"])

    def test_absent_header_returns_none(self):
        self.assertIsNone(
            dae_progress.parse_current_header("# progress\n\nno header here\n"))


class RenderBreadcrumbTests(unittest.TestCase):
    def test_marks_done_current_and_pending(self):
        out = dae_progress.render_breadcrumb(
            "015-image-formats", {0, 1.5, 2}, 3, "CP3 Spec — 2/4 criteria met")
        self.assertIn("DAE ▸ 015-image-formats", out)
        self.assertIn("✓0 Onboard", out)
        self.assertIn("✓1.5 Ready", out)
        self.assertIn("✓2 ACs", out)
        self.assertIn("▶3 Spec", out)
        self.assertIn("·4 Plan", out)
        self.assertIn("·5 Implement", out)
        self.assertIn("·8 Harden", out)
        self.assertIn("CP3 Spec — 2/4 criteria met", out)

    def test_renders_all_nine_stops(self):
        out = dae_progress.render_breadcrumb("x", set(), None, "")
        for stage in ("Onboard", "Ready", "ACs", "Spec", "Plan",
                      "Implement", "Refine", "Verify", "Harden"):
            self.assertIn(stage, out)

    def test_empty_detail_is_omitted(self):
        out = dae_progress.render_breadcrumb("x", set(), None, "")
        self.assertEqual(len(out.splitlines()), 2)


def _write_feature(parent, name, contents):
    """Create parent/name/ and, if contents is not None, parent/name/progress.md."""
    feat = os.path.join(parent, name)
    os.makedirs(feat)
    if contents is not None:
        with open(os.path.join(feat, "progress.md"), "w", encoding="utf-8") as f:
            f.write(contents)
    return feat


class BreadcrumbTests(unittest.TestCase):
    def test_full_progress_file(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "015-image-formats", CURRENT + "\n" + TABLE)
            out = dae_progress.breadcrumb(feat)
        self.assertIn("DAE ▸ 015-image-formats", out)
        self.assertIn("✓2 ACs", out)
        self.assertIn("▶3 Spec", out)
        self.assertIn("NEXT: write spec.md", out)
        self.assertNotIn("BLOCKED", out)  # blocked: none is omitted

    def test_blocked_reason_shown(self):
        header = "> ▶ CP4 Plan — 1/3 criteria met | NEXT: revise | BLOCKED: awaiting ADR-012\n"
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "042-export", header + "\n" + TABLE)
            out = dae_progress.breadcrumb(feat)
        self.assertIn("BLOCKED: awaiting ADR-012", out)

    def test_missing_progress_degrades(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "099-new", None)
            out = dae_progress.breadcrumb(feat)
        self.assertIn("099-new", out)
        self.assertIn("not yet started", out)
        self.assertIn("·0 Onboard", out)

    def test_no_header_degrades(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "022-x", TABLE)  # table only, no header
            out = dae_progress.breadcrumb(feat)
        self.assertIn("✓2 ACs", out)
        self.assertIn("no CURRENT header", out)


class MainTests(unittest.TestCase):
    def test_help_returns_zero(self):
        self.assertEqual(dae_progress.main(["--help"]), 0)

    def test_no_args_returns_zero(self):
        self.assertEqual(dae_progress.main([]), 0)

    def test_run_on_feature_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "015-x", CURRENT + "\n" + TABLE)
            self.assertEqual(dae_progress.main([feat]), 0)


if __name__ == "__main__":
    unittest.main()
