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
