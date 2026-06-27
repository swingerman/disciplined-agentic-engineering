#!/usr/bin/env python3
"""Tests for dae_roadmap — the local roadmap driver.

Run: python3 test_dae_roadmap.py
"""

import os
import tempfile
import unittest

import dae_roadmap as rm


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


MANIFEST = '''\
methodology_version: "0.2"
roadmap:
  type: local
tracker:
  type: local
'''

SEEDED_ROADMAP = '''\
Some human prose above the managed block — DAE must not touch this.

<!-- DAE-ROADMAP -->
# Roadmap

## now
- [ ] **Bulk export** `id:bulk-export` priority:1 status:planned area:exports → feature:—
      Admins export all records as CSV.
- [x] **SSO login** `id:sso-login` priority:2 status:shipped area:auth → feature:012-sso-login

## next
- [ ] **Dark mode** `id:dark-mode` priority:1 status:planned area:ui → feature:—

## later
- [ ] **Audit log** `id:audit-log` priority:3 status:planned area:platform → feature:—
<!-- /DAE-ROADMAP -->

Human prose below the block, also preserved.
'''


def _make_project(tmp, roadmap_text=None):
    os.makedirs(os.path.join(tmp, ".engineer"))
    with open(os.path.join(tmp, ".engineer", "manifest.yml"), "w") as fh:
        fh.write(MANIFEST)
    if roadmap_text is not None:
        with open(os.path.join(tmp, ".engineer", "roadmap.md"), "w") as fh:
            fh.write(roadmap_text)


class TestParseRender(unittest.TestCase):
    def test_parse_items(self):
        items = rm.parse_block(SEEDED_ROADMAP)
        by_id = {it["id"]: it for it in items}
        self.assertEqual(set(by_id), {
            "bulk-export", "sso-login", "dark-mode", "audit-log"})
        self.assertEqual(by_id["bulk-export"]["horizon"], "now")
        self.assertEqual(by_id["bulk-export"]["priority"], 1)
        self.assertEqual(by_id["bulk-export"]["area"], "exports")
        self.assertIsNone(by_id["bulk-export"]["feature_slug"])
        self.assertEqual(by_id["bulk-export"]["notes"],
                         "Admins export all records as CSV.")
        self.assertEqual(by_id["sso-login"]["status"], "shipped")
        self.assertEqual(by_id["sso-login"]["feature_slug"], "012-sso-login")
        self.assertEqual(by_id["dark-mode"]["horizon"], "next")
        self.assertEqual(by_id["audit-log"]["horizon"], "later")

    def test_no_block_is_empty(self):
        self.assertEqual(rm.parse_block("# just prose\n"), [])

    def test_render_roundtrips(self):
        items = rm.parse_block(SEEDED_ROADMAP)
        reparsed = rm.parse_block(rm.render_block(items))
        self.assertEqual({i["id"] for i in reparsed},
                         {i["id"] for i in items})
        a = {i["id"]: i for i in items}["sso-login"]
        b = {i["id"]: i for i in reparsed}["sso-login"]
        self.assertEqual(a, b)

    def test_slugify(self):
        self.assertEqual(rm.slugify("Bulk Export!"), "bulk-export")
        self.assertEqual(rm.slugify(""), "item")


class TestLoadSort(unittest.TestCase):
    def test_load_sorted_by_horizon_then_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            ids = [it["id"] for it in rm.load(tmp)]
            # now(1,2) -> next(1) -> later(3)
            self.assertEqual(
                ids, ["bulk-export", "sso-login", "dark-mode", "audit-log"])

    def test_load_missing_file_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp)
            self.assertEqual(rm.load(tmp), [])

    def test_load_no_manifest_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(rm.load(tmp))


class TestNextUnstarted(unittest.TestCase):
    def test_skips_shipped_and_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            nxt = rm.next_unstarted(tmp)
            # sso-login is shipped, bulk-export is planned & unpromoted, now/p1
            self.assertEqual(nxt["id"], "bulk-export")

    def test_none_when_all_started(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            rm.mark(tmp, "bulk-export", "in-progress", "030-bulk-export")
            rm.mark(tmp, "dark-mode", "in-progress", "031-dark-mode")
            rm.mark(tmp, "audit-log", "dropped")
            self.assertIsNone(rm.next_unstarted(tmp))


class TestUpsertMark(unittest.TestCase):
    def test_upsert_new_preserves_human_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            rec = rm.upsert(tmp, {"title": "Webhooks", "horizon": "next",
                                  "priority": 2, "area": "integrations"})
            self.assertEqual(rec["id"], "webhooks")
            text = _read(os.path.join(tmp, ".engineer", "roadmap.md"))
            self.assertIn("human prose above", text)
            self.assertIn("Human prose below", text)
            self.assertIn("webhooks", text)
            ids = {it["id"] for it in rm.load(tmp)}
            self.assertIn("webhooks", ids)

    def test_upsert_existing_updates_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            rm.upsert(tmp, {"id": "dark-mode", "title": "Dark mode",
                            "horizon": "now", "priority": 1,
                            "status": "planned", "area": "ui"})
            items = {it["id"]: it for it in rm.load(tmp)}
            self.assertEqual(items["dark-mode"]["horizon"], "now")
            self.assertEqual(len([i for i in rm.load(tmp)
                                  if i["id"] == "dark-mode"]), 1)

    def test_upsert_rejects_bad_enum(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            with self.assertRaises(ValueError):
                rm.upsert(tmp, {"title": "X", "horizon": "someday"})

    def test_mark_sets_status_and_backlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            rec = rm.mark(tmp, "bulk-export", "in-progress", "030-bulk-export")
            self.assertEqual(rec["status"], "in-progress")
            self.assertEqual(rec["feature_slug"], "030-bulk-export")
            reloaded = {it["id"]: it for it in rm.load(tmp)}["bulk-export"]
            self.assertEqual(reloaded["feature_slug"], "030-bulk-export")

    def test_mark_unknown_item_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            self.assertIsNone(rm.mark(tmp, "nope", "shipped"))

    def test_init_creates_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp)
            path = rm.init(tmp)
            self.assertTrue(os.path.isfile(path))
            with open(path) as _fh:
                self.assertIn(rm.OPEN_MARKER, _fh.read())


class TestCli(unittest.TestCase):
    def test_mark_cli_distinguishes_slug_from_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_project(tmp, SEEDED_ROADMAP)
            # single trailing arg that is NOT a dir -> treated as feature slug
            rc = rm.main(["dae_roadmap.py", "mark", "bulk-export",
                          "in-progress", "030-bulk-export", tmp])
            self.assertEqual(rc, 0)
            reloaded = {it["id"]: it for it in rm.load(tmp)}["bulk-export"]
            self.assertEqual(reloaded["feature_slug"], "030-bulk-export")

    def test_bad_command_usage_error(self):
        self.assertEqual(rm.main(["dae_roadmap.py", "bogus"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
