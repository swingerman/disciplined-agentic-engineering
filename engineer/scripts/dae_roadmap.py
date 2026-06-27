#!/usr/bin/env python3
"""dae-roadmap — the `local` roadmap driver.

The roadmap is the strategic feature-list altitude: what the project intends
to build, in what order — not yet broken into tasks. In `local` mode it lives
in `<root>/.engineer/roadmap.md`, inside a DAE-managed block delimited by
`<!-- DAE-ROADMAP -->` / `<!-- /DAE-ROADMAP -->`. Prose outside the markers is
the human's and is never touched (the same discipline doc-hosts use — see
references/roadmap.md).

MCP/CLI/API-backed hosts (notion, confluence, gdoc, github-projects, other)
are NOT handled here — those are driven through the connected channel per
references/roadmap.md. This script is only the `local` driver.

A RoadmapItem:
    id            stable kebab identifier (derived from title if omitted)
    title         one-line feature name
    area          single-token theme / area (or null)
    horizon       now | next | later
    priority      integer, lower = sooner within a horizon
    status        planned | in-progress | shipped | dropped
    feature_slug  back-link to the promoted features/NNN-slug (or null)
    notes         free text (or null)

Usage:
    dae_roadmap.py list [START_DIR]
    dae_roadmap.py read ID [START_DIR]
    dae_roadmap.py next-unstarted [START_DIR]
    dae_roadmap.py upsert [START_DIR]      # RoadmapItem JSON on stdin
    dae_roadmap.py mark ID STATUS [FEATURE_SLUG] [START_DIR]
    dae_roadmap.py init [START_DIR]        # create an empty managed block

Output: JSON — a RoadmapItem array for `list`, one record otherwise
(`next-unstarted` prints `null` when nothing is startable).

Exit codes:
    0  ok
    2  no manifest found, or (read/mark) item not found
    3  usage error
"""

import json
import os
import re
import sys

import dae_resolve

HORIZONS = ("now", "next", "later")
STATUSES = ("planned", "in-progress", "shipped", "dropped")
_HORIZON_RANK = {h: i for i, h in enumerate(HORIZONS)}

OPEN_MARKER = "<!-- DAE-ROADMAP -->"
CLOSE_MARKER = "<!-- /DAE-ROADMAP -->"

_HORIZON_RE = re.compile(r"^##\s+(now|next|later)\s*$", re.IGNORECASE)
_ITEM_RE = re.compile(
    r"^- \[[ x]\] \*\*(?P<title>.+?)\*\* `id:(?P<id>[a-z0-9][a-z0-9-]*)`"
    r"(?P<rest>.*)$"
)
_NONE_TOKENS = {"", "-", "—", "none", "null"}


def roadmap_path(start_dir):
    """Absolute path to the local roadmap file, or None if not onboarded."""
    root, _ = dae_resolve.find_methodology_root(start_dir)
    if root is None:
        return None
    return os.path.join(root, ".engineer", "roadmap.md")


def slugify(text):
    """Kebab-case identifier from a title (stable, ASCII, <=50)."""
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s or "item")[:50].strip("-")


def _token(rest, key):
    m = re.search(r"\b%s:(\S+)" % re.escape(key), rest)
    return m.group(1) if m else None


def _denull(value):
    if value is None or value.strip().lower() in _NONE_TOKENS:
        return None
    return value


def parse_block(text):
    """Parse the managed block out of roadmap.md text -> [RoadmapItem]."""
    if OPEN_MARKER not in text or CLOSE_MARKER not in text:
        return []
    inner = text.split(OPEN_MARKER, 1)[1].split(CLOSE_MARKER, 1)[0]
    items = []
    horizon = "now"
    for raw in inner.splitlines():
        hm = _HORIZON_RE.match(raw.strip())
        if hm:
            horizon = hm.group(1).lower()
            continue
        im = _ITEM_RE.match(raw.strip())
        if im:
            rest = im.group("rest")
            prio = _token(rest, "priority")
            items.append({
                "id": im.group("id"),
                "title": im.group("title").strip(),
                "area": _denull(_token(rest, "area")),
                "horizon": horizon,
                "priority": int(prio) if prio and prio.isdigit() else 99,
                "status": (_token(rest, "status") or "planned"),
                "feature_slug": _denull(_token(rest, "feature")),
                "notes": None,
            })
            continue
        # Continuation line (indented) -> notes for the last item.
        if items and raw.strip() and raw[:1] in (" ", "\t"):
            note = raw.strip()
            items[-1]["notes"] = (
                note if items[-1]["notes"] is None
                else items[-1]["notes"] + " " + note)
    return items


def _sort_key(item):
    return (_HORIZON_RANK.get(item.get("horizon"), 99),
            item.get("priority", 99),
            item.get("id", ""))


def render_block(items):
    """Render [RoadmapItem] into the managed-block body (markers included)."""
    lines = [OPEN_MARKER,
             "# Roadmap",
             "",
             "> DAE-managed strategic feature list. Edit items freely; DAE "
             "reads and writes this block.",
             ""]
    ordered = sorted(items, key=_sort_key)
    for horizon in HORIZONS:
        bucket = [it for it in ordered if it.get("horizon") == horizon]
        if not bucket:
            continue
        lines.append("## %s" % horizon)
        for it in bucket:
            check = "x" if it.get("status") == "shipped" else " "
            feat = it.get("feature_slug") or "—"
            lines.append(
                "- [%s] **%s** `id:%s` priority:%s status:%s area:%s "
                "→ feature:%s" % (
                    check, it.get("title", "").strip(), it["id"],
                    it.get("priority", 99), it.get("status", "planned"),
                    it.get("area") or "—", feat))
            if it.get("notes"):
                lines.append("      %s" % it["notes"].strip())
        lines.append("")
    lines.append(CLOSE_MARKER)
    return "\n".join(lines)


def _splice(text, rendered):
    """Replace the managed block in text (or append it) with rendered."""
    if OPEN_MARKER in text and CLOSE_MARKER in text:
        before = text.split(OPEN_MARKER, 1)[0]
        after = text.split(CLOSE_MARKER, 1)[1]
        return before + rendered + after
    sep = "" if not text or text.endswith("\n") else "\n"
    return text + sep + rendered + "\n"


def load(start_dir):
    """All RoadmapItems from the local roadmap, sorted. None if not onboarded."""
    path = roadmap_path(start_dir)
    if path is None:
        return None
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return sorted(parse_block(fh.read()), key=_sort_key)


def _write(path, items):
    text = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(_splice(text, render_block(items)))


def normalize(item, existing_ids):
    """Fill defaults and assign a unique id; raise ValueError on bad enums."""
    rec = dict(item)
    rec["id"] = rec.get("id") or slugify(rec.get("title", ""))
    if rec["id"] in existing_ids:
        # Caller is updating that id; keep it. Uniqueness is only enforced for
        # brand-new items, which the caller signals by a fresh/blank id.
        pass
    rec.setdefault("title", rec["id"])
    rec.setdefault("horizon", "next")
    rec.setdefault("priority", 99)
    rec.setdefault("status", "planned")
    rec.setdefault("area", None)
    rec.setdefault("feature_slug", None)
    rec.setdefault("notes", None)
    if rec["horizon"] not in HORIZONS:
        raise ValueError("horizon must be one of %s" % (HORIZONS,))
    if rec["status"] not in STATUSES:
        raise ValueError("status must be one of %s" % (STATUSES,))
    return rec


def upsert(start_dir, item):
    """Create or update one RoadmapItem (matched by id). Returns the record."""
    items = load(start_dir)
    if items is None:
        return None
    by_id = {it["id"]: it for it in items}
    rec = normalize(item, set(by_id))
    if rec["id"] in by_id:
        by_id[rec["id"]].update(rec)
        rec = by_id[rec["id"]]
    else:
        items.append(rec)
    _write(roadmap_path(start_dir), items)
    return rec


def mark(start_dir, item_id, status, feature_slug=None):
    """Flip an item's status (and optionally its feature back-link)."""
    items = load(start_dir)
    if items is None:
        return None
    for it in items:
        if it["id"] == item_id:
            if status not in STATUSES:
                raise ValueError("status must be one of %s" % (STATUSES,))
            it["status"] = status
            if feature_slug is not None:
                it["feature_slug"] = feature_slug or None
            _write(roadmap_path(start_dir), items)
            return it
    return None


def next_unstarted(start_dir):
    """Top startable item: planned, no feature yet, by horizon then priority."""
    items = load(start_dir)
    if not items:
        return None
    startable = [it for it in items
                 if it.get("status") == "planned"
                 and not it.get("feature_slug")]
    return startable[0] if startable else None


def init(start_dir):
    """Ensure the roadmap file exists with an (empty) managed block."""
    path = roadmap_path(start_dir)
    if path is None:
        return None
    has_block = False
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            has_block = OPEN_MARKER in fh.read()
    if not has_block:
        _write(path, load(start_dir) or [])
    return path


def _emit(value, missing_msg):
    if value is None:
        sys.stderr.write(missing_msg)
        return 2
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


_NO_MANIFEST = "no .engineer/manifest.yml found — run /engineer.onboard\n"


def main(argv):
    args = argv[1:]
    cmds = ("list", "read", "next-unstarted", "upsert", "mark", "init")
    if not args or args[0] not in cmds:
        sys.stderr.write(__doc__.split("Usage:")[1].split("\n\n")[0])
        return 3
    command = args[0]

    if command == "list":
        start_dir = args[1] if len(args) > 1 else os.getcwd()
        return _emit(load(start_dir), _NO_MANIFEST)

    if command == "next-unstarted":
        start_dir = args[1] if len(args) > 1 else os.getcwd()
        if roadmap_path(start_dir) is None:
            sys.stderr.write(_NO_MANIFEST)
            return 2
        # `null` (nothing startable) is a valid, non-error answer.
        json.dump(next_unstarted(start_dir), sys.stdout, indent=2,
                  sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if command == "init":
        start_dir = args[1] if len(args) > 1 else os.getcwd()
        path = init(start_dir)
        if path is None:
            sys.stderr.write(_NO_MANIFEST)
            return 2
        sys.stdout.write(path + "\n")
        return 0

    if command == "read":
        if len(args) < 2:
            sys.stderr.write("usage: dae_roadmap.py read ID [START_DIR]\n")
            return 3
        item_id, start_dir = args[1], (args[2] if len(args) > 2 else os.getcwd())
        items = load(start_dir)
        if items is None:
            sys.stderr.write(_NO_MANIFEST)
            return 2
        match = next((it for it in items if it["id"] == item_id), None)
        return _emit(match, "roadmap item %r not found\n" % item_id)

    if command == "upsert":
        start_dir = args[1] if len(args) > 1 else os.getcwd()
        try:
            item = json.load(sys.stdin)
        except (ValueError, json.JSONDecodeError) as exc:
            sys.stderr.write("upsert: invalid JSON on stdin: %s\n" % exc)
            return 3
        try:
            rec = upsert(start_dir, item)
        except ValueError as exc:
            sys.stderr.write("upsert: %s\n" % exc)
            return 3
        return _emit(rec, _NO_MANIFEST)

    # command == "mark"
    if len(args) < 3:
        sys.stderr.write(
            "usage: dae_roadmap.py mark ID STATUS [FEATURE_SLUG] [START_DIR]\n")
        return 3
    item_id, status = args[1], args[2]
    feature_slug, start_dir = None, os.getcwd()
    extra = args[3:]
    if len(extra) == 1:
        # Ambiguous single trailing arg: a path if it resolves, else a slug.
        if os.path.isdir(extra[0]):
            start_dir = extra[0]
        else:
            feature_slug = extra[0]
    elif len(extra) >= 2:
        feature_slug, start_dir = extra[0], extra[1]
    try:
        rec = mark(start_dir, item_id, status, feature_slug)
    except ValueError as exc:
        sys.stderr.write("mark: %s\n" % exc)
        return 3
    return _emit(rec, "roadmap item %r not found\n" % item_id)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
