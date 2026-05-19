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


if __name__ == "__main__":
    unittest.main()
