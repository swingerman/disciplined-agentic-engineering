#!/usr/bin/env python3
"""Tests for dae_handoff — handoff completeness audit.

Run: python3 -m unittest test_dae_handoff -v
"""
import os
import shutil
import tempfile
import unittest

import dae_handoff as dh

HANDOFF_COMPLETE = """---
skill: discover-acs
agent_id: subagent-1
checkpoint: 2
artifacts:
  - features/001-x/acs.md
exit_criteria:
  - criterion: "acs.md exists"
    met: true
    evidence: "written"
  - criterion: "human approved"
    met: true
    evidence: "approved in review"
status: complete
---

# discover-acs — handoff summary
"""

HANDOFF_UNMET = HANDOFF_COMPLETE.replace(
    'met: true\n    evidence: "approved in review"',
    'met: false\n    evidence: "awaiting review"')

HANDOFF_INTERRUPTED = HANDOFF_COMPLETE.replace(
    "status: complete", "status: interrupted")

HANDOFF_NULL_CP = HANDOFF_COMPLETE.replace("checkpoint: 2", "checkpoint: null")


class TestParseHandoff(unittest.TestCase):
    def test_scalar_fields(self):
        rec = dh.parse_handoff(HANDOFF_COMPLETE)
        self.assertEqual(rec["checkpoint"], 2)
        self.assertEqual(rec["status"], "complete")

    def test_null_checkpoint(self):
        rec = dh.parse_handoff(HANDOFF_NULL_CP)
        self.assertIsNone(rec["checkpoint"])

    def test_exit_criteria_all_met(self):
        rec = dh.parse_handoff(HANDOFF_COMPLETE)
        self.assertEqual(len(rec["exit_criteria"]), 2)
        self.assertTrue(all(c["met"] for c in rec["exit_criteria"]))

    def test_exit_criteria_one_unmet(self):
        rec = dh.parse_handoff(HANDOFF_UNMET)
        self.assertFalse(all(c["met"] for c in rec["exit_criteria"]))


PROGRESS = """# Feature 001: x — Progress

> ▶ CP2 ACs — 2/2 criteria met | NEXT: spec | BLOCKED: none

## Checkpoints
| # | Stage | Status | Artifact |
|---|-------|--------|----------|
| 1.5 | Ready | ✅ done | feature.md |
| 2 | ACs | ✅ done | acs.md |
| 3 | Spec | 🟡 in progress | — |
| 4 | Plan | ⏳ pending | — |
"""


class TestReadProgress(unittest.TestCase):
    def test_done_and_pending(self):
        cps = dh.read_progress(PROGRESS)
        self.assertTrue(cps[1.5])
        self.assertTrue(cps[2])
        self.assertFalse(cps[3])
        self.assertFalse(cps[4])

    def test_header_and_separator_skipped(self):
        cps = dh.read_progress(PROGRESS)
        self.assertEqual(set(cps), {1.5, 2, 3, 4})


class TestRecComplete(unittest.TestCase):
    def test_complete(self):
        self.assertTrue(dh._rec_complete(dh.parse_handoff(HANDOFF_COMPLETE)))

    def test_unmet_criterion_blocks(self):
        self.assertFalse(dh._rec_complete(dh.parse_handoff(HANDOFF_UNMET)))

    def test_interrupted_blocks(self):
        self.assertFalse(dh._rec_complete(dh.parse_handoff(HANDOFF_INTERRUPTED)))

    def test_no_criteria_complete_on_status(self):
        legacy = """---
skill: x
checkpoint: 4
status: complete
---
"""
        self.assertTrue(dh._rec_complete(dh.parse_handoff(legacy)))


def _make_feature(handoffs, progress):
    """Create a temp feature dir; return its path. Caller cleans up."""
    d = tempfile.mkdtemp()
    hd = os.path.join(d, "handoffs")
    os.makedirs(hd)
    for i, text in enumerate(handoffs):
        with open(os.path.join(hd, "h%d.md" % i), "w", encoding="utf-8") as f:
            f.write(text)
    with open(os.path.join(d, "progress.md"), "w", encoding="utf-8") as f:
        f.write(progress)
    return d


class TestAudit(unittest.TestCase):
    def test_clean(self):
        # progress claims 2 done; handoff covers 2 (1.5 is human/feature-init)
        prog = PROGRESS.replace("| 1.5 | Ready | ✅ done", "| 1.5 | Ready | ⏳ pending")
        d = _make_feature([HANDOFF_COMPLETE], prog)
        self.addCleanup(shutil.rmtree, d)
        res = dh.audit(d)
        self.assertEqual(res["gaps"], [])
        self.assertEqual(res["latest_complete"], 2)

    def test_gap_detected(self):
        # progress claims 2 done but the only handoff has an unmet criterion
        d = _make_feature([HANDOFF_UNMET], PROGRESS)
        self.addCleanup(shutil.rmtree, d)
        res = dh.audit(d)
        self.assertIn(2, res["gaps"])


class TestGate(unittest.TestCase):
    def test_through_passes(self):
        prog = PROGRESS.replace("| 1.5 | Ready | ✅ done", "| 1.5 | Ready | ⏳ pending")
        d = _make_feature([HANDOFF_COMPLETE], prog)
        self.addCleanup(shutil.rmtree, d)
        ok, _ = dh.gate(d, through=2)
        self.assertTrue(ok)

    def test_through_fails_when_incomplete(self):
        prog = PROGRESS.replace("| 1.5 | Ready | ✅ done", "| 1.5 | Ready | ⏳ pending")
        d = _make_feature([HANDOFF_COMPLETE], prog)
        self.addCleanup(shutil.rmtree, d)
        ok, msg = dh.gate(d, through=3)
        self.assertFalse(ok)
        self.assertIn("3", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
