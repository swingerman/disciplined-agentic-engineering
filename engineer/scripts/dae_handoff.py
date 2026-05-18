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

import dae_resolve

# Checkpoints 0 (Onboard) and 1.5 (Ready) are human/feature-init gated — they
# carry no skill handoff, so they never count as a gate failure.
NON_SKILL_CHECKPOINTS = (0, 1.5)


def _num(val):
    """Parse a checkpoint number ('2' -> 2, '1.5' -> 1.5); None if not numeric."""
    try:
        return float(val) if "." in val else int(val)
    except (ValueError, TypeError):
        return None


def _frontmatter(text):
    """The YAML frontmatter block as a list of lines ([] if none)."""
    return (dae_resolve.extract_frontmatter(text) or "").splitlines()


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


def read_progress(text):
    """Parse the progress.md Checkpoints table -> {checkpoint: done_bool}."""
    result = {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        cp = _num(cells[0])
        if cp is None:
            continue  # header or separator row
        result[cp] = "done" in cells[2].lower()
    return result


def _rec_complete(rec):
    """True if a handoff record means its checkpoint is genuinely done."""
    if rec["status"] != "complete":
        return False
    return all(c["met"] is True for c in rec["exit_criteria"])


def audit(feature_dir):
    """Audit one feature folder. Returns a dict with complete/claimed/gaps."""
    complete = set()
    hdir = os.path.join(feature_dir, "handoffs")
    if os.path.isdir(hdir):
        for name in sorted(os.listdir(hdir)):
            if not name.endswith(".md"):
                continue
            with open(os.path.join(hdir, name), encoding="utf-8") as f:
                rec = parse_handoff(f.read())
            if rec["checkpoint"] is not None and _rec_complete(rec):
                complete.add(rec["checkpoint"])
    claimed_done = set()
    progress_path = os.path.join(feature_dir, "progress.md")
    if os.path.isfile(progress_path):
        with open(progress_path, encoding="utf-8") as f:
            for cp, done in read_progress(f.read()).items():
                if done:
                    claimed_done.add(cp)
    return {
        "complete": complete,
        "claimed_done": claimed_done,
        "gaps": sorted(claimed_done - complete),
        "latest_complete": max(complete) if complete else None,
    }


def gate(feature_dir, through=None):
    """Return (ok, message). ok is False if a checkpoint <= `through` is not
    backed by a complete handoff, or any claimed-done checkpoint has no handoff.
    NON_SKILL_CHECKPOINTS never count as gaps — they carry no skill handoff.
    """
    a = audit(feature_dir)
    real_gaps = [g for g in a["gaps"] if g not in NON_SKILL_CHECKPOINTS]
    if real_gaps:
        return False, "checkpoints marked done with no complete handoff: %s" % real_gaps
    if through is not None and through not in NON_SKILL_CHECKPOINTS \
            and through not in a["complete"]:
        return False, "checkpoint %s is not complete -- cannot advance past it" % through
    return True, "ok -- latest complete checkpoint: %s" % a["latest_complete"]


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    feature_dir = argv[0]
    through = None
    if "--through" in argv:
        through = _num(argv[argv.index("--through") + 1])
    ok, msg = gate(feature_dir, through)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
