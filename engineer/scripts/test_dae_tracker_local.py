#!/usr/bin/env python3
"""Tests for dae_tracker_local — the local tracker driver.

Run: python3 test_dae_tracker_local.py
"""

import os
import tempfile
import unittest

import dae_tracker_local as tl

MANIFEST = '''\
methodology_version: "0.2"
roadmap:
  type: local
tracker:
  type: local
'''

FEATURE_ALPHA = '''\
---
slug: alpha
title: Alpha Feature
outcome: The alpha capability ships.
autonomy_level: medium
status: in-progress
tracker_ref: local://alpha
owner: miklos
area: api
---

# Alpha Feature

## Outcome
The alpha capability ships.
'''

FEATURE_BETA = '''\
---
slug: beta
title: Beta Feature
outcome: The beta capability ships.
autonomy_level: low
status: ready
tracker_ref: local://beta
---

# Beta Feature
'''

PROGRESS_ALPHA = '''\
# Feature 001: alpha — Progress

**Current stage:** Checkpoint 5 — Implement (in progress)
**Autonomy level:** medium
'''


def _make_project(tmp):
    os.makedirs(os.path.join(tmp, ".engineer"))
    with open(os.path.join(tmp, ".engineer", "manifest.yml"), "w") as fh:
        fh.write(MANIFEST)
    a = os.path.join(tmp, "features", "001-alpha")
    b = os.path.join(tmp, "features", "002-beta")
    os.makedirs(a)
    os.makedirs(b)
    with open(os.path.join(a, "feature.md"), "w") as fh:
        fh.write(FEATURE_ALPHA)
    with open(os.path.join(a, "progress.md"), "w") as fh:
        fh.write(PROGRESS_ALPHA)
    with open(os.path.join(b, "feature.md"), "w") as fh:
        fh.write(FEATURE_BETA)


class TestCheckpoint(unittest.TestCase):
    def test_reads_current_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "progress.md"), "w") as fh:
                fh.write(PROGRESS_ALPHA)
            self.assertEqual(tl.read_checkpoint(tmp),
                             "Checkpoint 5 — Implement (in progress)")

    def test_no_progress_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(tl.read_checkpoint(tmp))


class TestLocalDriver(unittest.TestCase):
    def test_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp)
            records = tl.list_features(tmp)
            self.assertEqual(len(records), 2)
            slugs = sorted(r["slug"] for r in records)
            self.assertEqual(slugs, ["alpha", "beta"])

    def test_list_tracked_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp)
            alpha = tl.read_feature(tmp, "alpha")
            self.assertEqual(alpha["title"], "Alpha Feature")
            self.assertEqual(alpha["status"], "in-progress")
            self.assertEqual(alpha["autonomy_level"], "medium")
            self.assertEqual(alpha["owner"], "miklos")
            self.assertEqual(alpha["tracker_ref"], "local://alpha")

    def test_checkpoint_from_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp)
            alpha = tl.read_feature(tmp, "alpha")
            self.assertEqual(alpha["current_checkpoint"],
                             "Checkpoint 5 — Implement (in progress)")

    def test_checkpoint_none_without_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp)
            beta = tl.read_feature(tmp, "beta")  # no progress.md
            self.assertIsNone(beta["current_checkpoint"])

    def test_read_resolves_from_deep_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp)
            deep = os.path.join(tmp, "features", "001-alpha")
            self.assertEqual(tl.read_feature(deep, "beta")["slug"], "beta")

    def test_read_unknown_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp)
            self.assertIsNone(tl.read_feature(tmp, "nonexistent"))

    def test_no_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(tl.list_features(tmp))


if __name__ == "__main__":
    unittest.main(verbosity=2)
