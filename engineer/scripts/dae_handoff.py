#!/usr/bin/env python3
"""dae_handoff.py — audit handoff completeness against progress.md.

A checkpoint is "complete" only when its handoff exists, has status: complete,
and (if it carries an exit_criteria block) every criterion is met. This is the
enforcement helper for handoff-as-gate (DAE Foundation Design, Sections 5 + 8).

Usage:
  dae_handoff.py <feature-dir>               report; exit 0 if consistent
  dae_handoff.py <feature-dir> --through N   exit non-zero unless checkpoint N
                                             is complete and there are no gaps
"""
import os
import re
import sys


def _num(val):
    """Parse a checkpoint number ('2' -> 2, '1.5' -> 1.5); None if not numeric."""
    try:
        return float(val) if "." in val else int(val)
    except (ValueError, TypeError):
        return None


def _frontmatter(text):
    """Return the lines between the first pair of --- fences ([] if none)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    out = []
    for line in lines[1:]:
        if line.strip() == "---":
            return out
        out.append(line)
    return []  # unterminated -> treat as no frontmatter


def _parse_criteria(lines, start):
    """Parse a YAML `exit_criteria:` list-of-dicts block beginning at `start`.

    Returns (next_index, [{"met": bool|None}, ...]).
    """
    out = []
    i = start
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        if not (line.startswith(" ") or line.startswith("\t")):
            break  # an unindented key ends the block
        stripped = line.strip()
        if stripped.startswith("- "):
            out.append({"met": None})
            stripped = stripped[2:].strip()
        m = re.match(r"(\w+):\s*(.*)$", stripped)
        if m and m.group(1) == "met" and out:
            out[-1]["met"] = m.group(2).strip().lower() == "true"
        i += 1
    return i, out


def parse_handoff(text):
    """Parse a handoff .md into {checkpoint, status, exit_criteria}."""
    fm = _frontmatter(text)
    rec = {"checkpoint": None, "status": None, "exit_criteria": []}
    i = 0
    while i < len(fm):
        m = re.match(r"(\w+):\s*(.*)$", fm[i])
        if m and m.group(1) == "checkpoint":
            val = m.group(2).strip()
            rec["checkpoint"] = None if val in ("", "null", "~") else _num(val)
        elif m and m.group(1) == "status":
            rec["status"] = m.group(2).strip()
        elif m and m.group(1) == "exit_criteria":
            i, rec["exit_criteria"] = _parse_criteria(fm, i + 1)
            continue
        i += 1
    return rec
