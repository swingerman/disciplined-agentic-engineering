#!/usr/bin/env python3
"""dae_progress.py — render the DAE pipeline breadcrumb for a feature.

Reads a feature's progress.md (the Checkpoints table + the CURRENT header) and
prints a compact "you are here" breadcrumb across the nine-stop DAE pipeline.
Advisory and read-only — it produces no artifact and never blocks a skill.

Usage:
  dae_progress.py <feature-dir>     print the pipeline breadcrumb
"""
import os
import re
import sys

import dae_handoff

# The canonical DAE pipeline — the single source of truth for stage order and
# names. CP5 (Implement) and CP8 (Harden) are stops with no dedicated skill.
CHECKPOINTS = [
    (0, "Onboard"), (1.5, "Ready"), (2, "ACs"), (3, "Spec"), (4, "Plan"),
    (5, "Implement"), (6, "Refine"), (7, "Verify"), (8, "Harden"),
]

_HEADER_RE = re.compile(
    r"▶\s*CP(?P<cp>[0-9.]+)\s+(?P<stage>.+?)\s*—\s*"
    r"(?P<met>\d+)\s*/\s*(?P<total>\d+)\s+criteria met"
)


def parse_current_header(text):
    """Parse progress.md's CURRENT header line into a dict, or None if absent.

    Header form (a leading '>' blockquote marker is tolerated):
      > ▶ CP3 Spec — 2/4 criteria met | NEXT: <action> | BLOCKED: <none|reason>
    """
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(">"):
            line = line[1:].strip()
        if "▶" not in line or "CP" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        m = _HEADER_RE.search(parts[0])
        if not m:
            continue
        cp_s = m.group("cp")
        rec = {
            "cp": float(cp_s) if "." in cp_s else int(cp_s),
            "stage": m.group("stage").strip(),
            "met": int(m.group("met")),
            "total": int(m.group("total")),
            "next": None,
            "blocked": None,
        }
        for p in parts[1:]:
            upper = p.upper()
            if upper.startswith("NEXT:"):
                rec["next"] = p[5:].strip()
            elif upper.startswith("BLOCKED:"):
                rec["blocked"] = p[8:].strip()
        return rec
    return None


def render_breadcrumb(feature_name, done, current_cp, detail):
    """Render the breadcrumb string.

    done        - set of checkpoint numbers marked done in the Checkpoints table
    current_cp  - the in-progress checkpoint number, or None
    detail      - the third line (criteria / NEXT / BLOCKED), or "" to omit it
    """
    stops = []
    for num, stage in CHECKPOINTS:
        if num == current_cp:
            marker = "▶"
        elif num in done:
            marker = "✓"
        else:
            marker = "·"
        stops.append("%s%s %s" % (marker, num, stage))
    lines = ["DAE ▸ %s" % feature_name, " · ".join(stops)]
    if detail:
        lines.append(detail)
    return "\n".join(lines)


def breadcrumb(feature_dir):
    """Build the breadcrumb for a feature folder. Never raises on bad input."""
    feature_name = os.path.basename(os.path.normpath(feature_dir))
    progress_path = os.path.join(feature_dir, "progress.md")
    if not os.path.isfile(progress_path):
        return render_breadcrumb(
            feature_name, set(), None,
            "(progress.md not found — feature not yet started)")
    with open(progress_path, encoding="utf-8") as f:
        text = f.read()
    done = {cp for cp, is_done in dae_handoff.read_progress(text).items()
            if is_done}
    header = parse_current_header(text)
    if header is None:
        return render_breadcrumb(
            feature_name, done, None, "(no CURRENT header in progress.md)")
    detail = "CP%s %s — %d/%d criteria met" % (
        header["cp"], header["stage"], header["met"], header["total"])
    if header["next"]:
        detail += " · NEXT: %s" % header["next"]
    if header["blocked"] and header["blocked"].lower() != "none":
        detail += " · BLOCKED: %s" % header["blocked"]
    return render_breadcrumb(feature_name, done, header["cp"], detail)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    print(breadcrumb(argv[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
