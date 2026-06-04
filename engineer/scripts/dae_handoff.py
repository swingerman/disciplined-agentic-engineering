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


def parse_handoff(text):
    """Parse a handoff .md into {checkpoint, status, exit_criteria, skill, agent_id}.

    `met` is normalized to {True, False, "partial", None}. distbute saw a verify
    handoff with met: partial slip through because the parser silently dropped
    'partial' to None — the gate logic then treated it as "not true → fail",
    but feature.md still claimed status: done. Keeping 'partial' as a distinct
    value lets callers report it explicitly instead of confusing it with absent.
    """
    rec = {"checkpoint": None, "status": None, "exit_criteria": [],
           "skill": None, "agent_id": None}
    fm = dae_resolve.extract_frontmatter(text)
    if not fm:
        return rec
    try:
        data = dae_resolve.read_manifest(fm)
    except dae_resolve.ManifestError:
        return rec
    if not isinstance(data, dict):
        return rec
    cp = data.get("checkpoint")
    if cp is not None and cp not in ("", "null", "~"):
        rec["checkpoint"] = cp if isinstance(cp, (int, float)) else _num(str(cp))
    status = data.get("status")
    rec["status"] = status if isinstance(status, str) else None
    skill = data.get("skill")
    rec["skill"] = skill if isinstance(skill, str) else None
    agent_id = data.get("agent_id")
    rec["agent_id"] = agent_id if isinstance(agent_id, str) else None
    raw_criteria = data.get("exit_criteria")
    if isinstance(raw_criteria, list):
        for entry in raw_criteria:
            if isinstance(entry, dict):
                met_raw = entry.get("met")
                if met_raw is True:
                    met = True
                elif met_raw is False:
                    met = False
                elif isinstance(met_raw, str) and met_raw.lower() == "partial":
                    met = "partial"
                else:
                    met = None
                rec["exit_criteria"].append({"met": met})
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


def _all_records(feature_dir):
    """Return [(filename, rec), ...] for all parsed handoffs in feature_dir/handoffs."""
    records = []
    hdir = os.path.join(feature_dir, "handoffs")
    if os.path.isdir(hdir):
        for name in sorted(os.listdir(hdir)):
            if not name.endswith(".md"):
                continue
            with open(os.path.join(hdir, name), encoding="utf-8") as f:
                records.append((name, parse_handoff(f.read())))
    return records


def independence_violations(feature_dir):
    """Return [(verify_filename, implement_agent_id, violator_cp), ...] for every
    case where a verification handoff (CP 6, 7, 8) shares agent_id with the same
    feature's CP5 implement handoff. Principle 7: the verifier must not be the
    implementer.

    A missing agent_id on either side is ignored (no comparison possible).
    """
    records = _all_records(feature_dir)
    implement_agent = None
    for _, rec in records:
        if rec["checkpoint"] == 5 and rec["agent_id"]:
            implement_agent = rec["agent_id"]
            break
    if not implement_agent:
        return []
    violations = []
    for fname, rec in records:
        if rec["checkpoint"] in (6, 7, 8) and rec["agent_id"] == implement_agent:
            violations.append((fname, implement_agent, rec["checkpoint"]))
    return violations


def audit(feature_dir):
    """Audit one feature folder. Returns a dict with complete/claimed/gaps."""
    complete = set()
    for _, rec in _all_records(feature_dir):
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
        "independence_violations": independence_violations(feature_dir),
    }


def gate(feature_dir, through=None):
    """Return (ok, message). ok is False if a checkpoint <= `through` is not
    backed by a complete handoff, or any claimed-done checkpoint has no handoff,
    or any verification handoff shares agent_id with the CP5 implement handoff.
    NON_SKILL_CHECKPOINTS never count as gaps — they carry no skill handoff.
    """
    a = audit(feature_dir)
    real_gaps = [g for g in a["gaps"] if g not in NON_SKILL_CHECKPOINTS]
    if real_gaps:
        return False, "checkpoints marked done with no complete handoff: %s" % real_gaps
    if a["independence_violations"]:
        v = a["independence_violations"][0]
        return False, ("verifier-independence violated: CP%s handoff %s "
                       "shares agent_id %s with the CP5 implement handoff "
                       "(Principle 7)") % (v[2], v[0], v[1])
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
