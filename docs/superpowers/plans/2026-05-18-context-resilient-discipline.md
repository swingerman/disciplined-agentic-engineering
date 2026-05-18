# Context-Resilient Discipline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DAE's pipeline discipline survive context compaction — a per-checkpoint exit contract, a real handoff gate, a mid-task re-anchoring skill, and an `atdd-team` rewrite to fresh per-phase agents.

**Architecture:** A new locked Foundation contract (the Checkpoint Exit Contract) is the backbone. A stdlib script (`dae_handoff.py`) enforces handoff completeness. A new read-only skill (`reorient`) reloads the working contract. `atdd-team` is restructured so no agent persists across phases. Notion foundation docs are updated first so the plugin is built against locked contracts.

**Tech Stack:** Python 3 stdlib (no third-party deps — matches the existing `engineer/scripts/`), Markdown skill/reference files, Notion MCP for foundation docs.

**Source spec:** `docs/superpowers/specs/2026-05-18-context-resilient-discipline-design.md`

---

## Orientation for the engineer

- Two plugins live in this repo: `engineer/` (the DAE pipeline, 13 skills) and the repo-root `skills/` + `agents/` (the `atdd` plugin).
- `engineer/scripts/` holds stdlib-only Python scripts, each with a `test_*.py` sibling. Run all tests: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`.
- Engineer-plugin skills are folders under `engineer/skills/<name>/SKILL.md`; the skill name becomes the `/engineer.<name>` command automatically (no separate command file).
- The 8 DAE checkpoints: `0` Onboard, `1.5` Ready, `2` ACs, `3` Spec, `4` Plan, `5` Implement, `6` Refine, `7` Light Verify, `8` Hardening.
- Never push. Commit locally per task. Notion edits use the Notion MCP (`notion-fetch`, `notion-update-page`).

---

## Phase 1 — Lock the Foundation contracts (Notion)

The methodology source of truth is in Notion. Lock the contracts before building against them.

- DAE Foundation Design page: `3585ecde-e0e2-811b-bc67-ff4913c03207`
- DAE methodology page: `3505ecde-e0e2-81b2-97c8-d9c07ec6dad6`

### Task 1: Add the Checkpoint Exit Contract section to Foundation Design

**Files:**
- Modify (Notion): DAE Foundation Design page `3585ecde-e0e2-811b-bc67-ff4913c03207`

- [ ] **Step 1: Fetch the page to confirm current structure**

Run (Notion MCP): `notion-fetch` with id `3585ecde-e0e2-811b-bc67-ff4913c03207`
Confirm Section 7 ("Acceptance pipeline alignment") is the last numbered section.

- [ ] **Step 2: Append a new section after Section 7**

Insert this content as a new section (`notion-update-page`, append):

```markdown
## Section 8 — Checkpoint Exit Contract

Every checkpoint has an explicit, verifiable definition of done. `feature.md`
(Section 4) is the Ready contract for Checkpoint 1.5; this section generalizes
that pattern to all checkpoints.

Each checkpoint declares:
- **Goal** — one line; the observable outcome of the stage.
- **Exit criteria** — a short list of objectively checkable conditions.
- **Verifier** — `self` or `independent` (Principle 7; the manifest's
  `verification.apply_to_checkpoints` decides which checkpoints are independent).

Each exit criterion declares `verified_by` — *how* it is checked: `tool` (an
objective command; the evidence is the tool's output), `human` (an approval), or
`judgment` (an agent assessment with no backing tool). Design rule: prefer
`tool` wherever a criterion can be made objectively checkable; `judgment` is the
weakest form and should shrink over time.

| CP | Goal | Exit criteria | Verifier |
|----|------|---------------|----------|
| 0 Onboard | Project mapped onto DAE | CHARTER.md + manifest.yml exist and validate; consolidation.md produced for existing projects; charter sign-off + tracking decision made by human | human |
| 1.5 Ready | Feature is startable | feature.md conforms to Section 4 schema; mandatory sections present; slug matches folder; autonomy_level within charter caps; human approved | human |
| 2 ACs | Acceptance criteria captured | acs.md exists; every AC externally observable; every AC traces to feature.md outcome/scope; human approved | human |
| 3 Spec | Behavior specified | spec.md in Gherkin; dae_gherkin.py parses to a valid IR; every AC maps to >=1 scenario; spec-check passes | independent (if manifest lists 3) |
| 4 Plan | Approach agreed | plan.md exists; Charter Check table complete; every deviation has a matching amendment; human approved | human |
| 5 Implement | Behavior built | both test streams green; acceptance tests cover all spec scenarios; IR mutator confirms acceptance tests are wired; PR exists | self |
| 6 Refine | Changed code improved | refine ran; both streams still green; charter filter applied to every proposal | independent (if manifest lists 6) |
| 7 Light Verify | Change risk checked | CRAP <= crap_max; coverage >= coverage_min | independent |
| 8 Hardening | Test suite hardened | mutation score >= mutation_score_min at the charter's scope and cadence | independent |

### How exit criteria are asserted

Each checkpoint-advancing skill's handoff summary carries an `exit_criteria`
block (see Section 5). A checkpoint is marked done in `progress.md` only when its
handoff asserts every criterion met. A handoff with any unmet criterion leaves
the checkpoint `in progress` (or `blocked` if a human is needed).

### Decisions locked

- Every checkpoint has a goal, verifiable exit criteria, and a named verifier.
- Each exit criterion declares `verified_by` (tool | human | judgment); `tool`
  is preferred — an independent check, not the agent's say-so.
- `feature.md` is Checkpoint 1.5's exit contract — not a special case.
- `consistency-check` validates that done checkpoints have a satisfying handoff.
```

- [ ] **Step 3: Verify**

Run (Notion MCP): `notion-fetch` id `3585ecde-e0e2-811b-bc67-ff4913c03207`
Expected: a "Section 8 — Checkpoint Exit Contract" section with the checkpoint table is present.

- [ ] **Step 4: No commit** — Notion is not under git. Proceed.

### Task 2: Update Foundation Design Section 5 — handoff schema

**Files:**
- Modify (Notion): DAE Foundation Design page `3585ecde-e0e2-811b-bc67-ff4913c03207`, Section 5

- [ ] **Step 1: Add the `exit_criteria` block to the agentic summary frontmatter**

In Section 5's frontmatter example, after the `artifacts:` field, add:

```yaml
exit_criteria:                     # required on checkpoint-advancing skills
  - criterion: "spec.md parses to a valid IR"
    verified_by: tool              # tool | human | judgment
    met: true
    evidence: "dae_gherkin.py exited 0; 12 scenarios"
  - criterion: "every AC traces to feature.md outcome/scope"
    verified_by: judgment
    met: true
    evidence: "8/8 ACs cross-referenced in acs.md"
  - criterion: "human approved"
    verified_by: human
    met: false
    evidence: "awaiting review"
```

- [ ] **Step 2: Add handoff-as-gate to the "Decisions locked" list of Section 5**

Append these bullets to Section 5's "Decisions locked":

```markdown
- **Handoff-as-gate.** A checkpoint is not complete until its handoff exists,
  has `status: complete`, and asserts every exit-criteria entry `met: true`.
  The next checkpoint must not begin until the prior handoff is complete.
- **`exit_criteria`** is required frontmatter on checkpoint-advancing skills;
  it lists each Section 8 exit criterion with `met` (bool) and `evidence`.
- **Exemptions extended:** `reorient` joins `progress-log` and `next` as a skill
  that emits no agentic summary — it is a read-only mid-task query.
```

- [ ] **Step 3: Add the CURRENT header to the `progress.md` format example**

In Section 5's `progress.md` example, replace the `**Current stage:**` line with:

```markdown
> ▶ CP5 Implement — 3/4 criteria met | NEXT: wire IR-mutator check | BLOCKED: none
```

Add a note under the example: *"The first line is the CURRENT header — a fixed, parseable one-glance pointer maintained by `progress-log`."*

Also in that same `progress.md` Checkpoints table, change the Checkpoint 6 row label `Refactor` → `Refine`.

- [ ] **Step 4: Update Section 6 — naming conventions**

In Section 6 ("Naming conventions"), under "Skill command names", change `/engineer.simplify` → `/engineer.refine`. This aligns the locked naming with the Phase 6 rename.

- [ ] **Step 5: Verify**

Run (Notion MCP): `notion-fetch` id `3585ecde-e0e2-811b-bc67-ff4913c03207`
Expected: Section 5 shows the `exit_criteria` block, the handoff-as-gate bullets, the CURRENT header line, and the Checkpoint 6 label `Refine`; Section 6 shows `/engineer.refine`.

- [ ] **Step 6: No commit** — Notion. Proceed.

### Task 3: Add the "Context Resilience" principle to the methodology page

**Files:**
- Modify (Notion): DAE methodology page `3505ecde-e0e2-81b2-97c8-d9c07ec6dad6`

- [ ] **Step 1: Fetch the methodology page and find the principles section**

Run (Notion MCP): `notion-fetch` id `3505ecde-e0e2-81b2-97c8-d9c07ec6dad6`
Locate where the numbered principles are listed (Principle 7 — verification independence — is the current last).

- [ ] **Step 2: Add the new principle**

Append after the last principle:

```markdown
### Principle 8 — Context Resilience

Context compaction silently erodes role identity and discipline: agents lose
their role, invent constraints that do not exist, and skip expensive-but-required
steps. Defend structurally — prefer fresh, checkpoint-scoped skill invocations
over long-running agents, make every stage's "done" verifiable (the Checkpoint
Exit Contract), and re-anchor on compaction (the `reorient` skill). A stage is
done only when its exit criteria are verifiably met — never on an agent's
say-so.
```

- [ ] **Step 3: Verify**

Run (Notion MCP): `notion-fetch` id `3505ecde-e0e2-81b2-97c8-d9c07ec6dad6`
Expected: "Principle 8 — Context Resilience" is present.

- [ ] **Step 4: No commit** — Notion. Proceed.

---

## Phase 2 — `dae_handoff.py` (the gate helper)

A stdlib script that audits handoff completeness against `progress.md`.

### Task 4: `parse_handoff` — read handoff frontmatter

**Files:**
- Create: `engineer/scripts/dae_handoff.py`
- Test: `engineer/scripts/test_dae_handoff.py`

- [ ] **Step 1: Write the failing test**

Create `engineer/scripts/test_dae_handoff.py`:

```python
#!/usr/bin/env python3
"""Tests for dae_handoff — handoff completeness audit.

Run: python3 -m unittest test_dae_handoff -v
"""
import os
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_handoff -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dae_handoff'`

- [ ] **Step 3: Write `dae_handoff.py` with `parse_handoff`**

Create `engineer/scripts/dae_handoff.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_handoff -v`
Expected: PASS — 4 tests OK

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_handoff.py engineer/scripts/test_dae_handoff.py
git commit -m "feat: dae_handoff.py — parse handoff frontmatter + exit_criteria"
```

### Task 5: `read_progress` + `_rec_complete`

**Files:**
- Modify: `engineer/scripts/dae_handoff.py`
- Test: `engineer/scripts/test_dae_handoff.py`

- [ ] **Step 1: Write the failing test** — add to `test_dae_handoff.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_handoff -v`
Expected: FAIL — `AttributeError: module 'dae_handoff' has no attribute 'read_progress'`

- [ ] **Step 3: Add `read_progress` and `_rec_complete` to `dae_handoff.py`**

Append to `dae_handoff.py` (before any `main`):

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_handoff -v`
Expected: PASS — 10 tests OK

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_handoff.py engineer/scripts/test_dae_handoff.py
git commit -m "feat: dae_handoff.py — progress.md table parser + completeness rule"
```

### Task 6: `audit`, `gate`, and the CLI

**Files:**
- Modify: `engineer/scripts/dae_handoff.py`
- Test: `engineer/scripts/test_dae_handoff.py`

- [ ] **Step 1: Write the failing test** — add to `test_dae_handoff.py`:

```python
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
        # progress claims 1.5 + 2 done; handoff covers 2 (1.5 is human/feature-init)
        prog = PROGRESS.replace("| 1.5 | Ready | ✅ done", "| 1.5 | Ready | ⏳ pending")
        d = _make_feature([HANDOFF_COMPLETE], prog)
        try:
            res = dh.audit(d)
            self.assertEqual(res["gaps"], [])
            self.assertEqual(res["latest_complete"], 2)
        finally:
            __import__("shutil").rmtree(d)

    def test_gap_detected(self):
        # progress claims 2 done but the only handoff has an unmet criterion
        d = _make_feature([HANDOFF_UNMET], PROGRESS)
        try:
            res = dh.audit(d)
            self.assertIn(2, res["gaps"])
        finally:
            __import__("shutil").rmtree(d)


class TestGate(unittest.TestCase):
    def test_through_passes(self):
        prog = PROGRESS.replace("| 1.5 | Ready | ✅ done", "| 1.5 | Ready | ⏳ pending")
        d = _make_feature([HANDOFF_COMPLETE], prog)
        try:
            ok, _ = dh.gate(d, through=2)
            self.assertTrue(ok)
        finally:
            __import__("shutil").rmtree(d)

    def test_through_fails_when_incomplete(self):
        prog = PROGRESS.replace("| 1.5 | Ready | ✅ done", "| 1.5 | Ready | ⏳ pending")
        d = _make_feature([HANDOFF_COMPLETE], prog)
        try:
            ok, msg = dh.gate(d, through=3)
            self.assertFalse(ok)
            self.assertIn("3", msg)
        finally:
            __import__("shutil").rmtree(d)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_handoff -v`
Expected: FAIL — `AttributeError: module 'dae_handoff' has no attribute 'audit'`

- [ ] **Step 3: Add `audit`, `gate`, and `main` to `dae_handoff.py`**

Append to `dae_handoff.py`:

```python
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

    Checkpoint 1.5 (Ready) and 0 (Onboard) are human/feature-init gated and may
    legitimately have no skill handoff — they never count as gaps.
    """
    a = audit(feature_dir)
    real_gaps = [g for g in a["gaps"] if g not in (0, 1.5)]
    if real_gaps:
        return False, "checkpoints marked done with no complete handoff: %s" % real_gaps
    if through is not None and through not in (0, 1.5) and through not in a["complete"]:
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
```

- [ ] **Step 4: Run the full test suite to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — all scripts' tests green, including 16 in `test_dae_handoff`.

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_handoff.py engineer/scripts/test_dae_handoff.py
git commit -m "feat: dae_handoff.py — audit + gate + CLI"
```

---

## Phase 3 — Wire the handoff contract

### Task 7: Update `handoff-summary.md` with the exit-criteria block and the gate rule

**Files:**
- Modify: `engineer/references/handoff-summary.md`

- [ ] **Step 1: Add `exit_criteria` to the frontmatter template**

In the `## Format` code block, after the `artifacts:` lines, add:

```markdown
exit_criteria:                       # required on checkpoint-advancing skills
  - criterion: <one Section 8 exit criterion>
    verified_by: <tool | human | judgment>
    met: <true | false>
    evidence: <one line; for `tool`, the command + its output>
```

- [ ] **Step 2: Add `exit_criteria` to the "Required vs optional" lists**

Change the "Required frontmatter" line to include `exit_criteria` *for checkpoint-advancing skills*; add a note: *"`exit_criteria` is required when `checkpoint` is set; omitted for off-pipeline skills (`checkpoint: null`)."*

- [ ] **Step 3: Add the handoff-as-gate rule**

Append to the `## Rules` section:

```markdown
- **Handoff-as-gate.** A checkpoint is not complete until its handoff exists,
  has `status: complete`, and asserts every `exit_criteria` entry `met: true`.
  A skill that advances checkpoint N+1 MUST verify checkpoint N is complete
  before starting — run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_handoff.py <feature>
  --through N`. On a non-zero exit, stop and surface the gap to the human; do
  not proceed and do not auto-fix.
```

- [ ] **Step 4: Verify**

Run: `grep -n "exit_criteria\|Handoff-as-gate" engineer/references/handoff-summary.md`
Expected: matches in the Format block, the required/optional lists, and Rules.

- [ ] **Step 5: Commit**

```bash
git add engineer/references/handoff-summary.md
git commit -m "feat: handoff contract — exit_criteria block + handoff-as-gate rule"
```

### Task 8: Add the entry gate + exit-criteria assertion to checkpoint-advancing skills

The checkpoint-advancing skills and their checkpoints: `engineer/skills/discover-acs` (CP2), `engineer/skills/plan` (CP4), `engineer/skills/simplify` (CP6 — renamed in Phase 6; edit it now under its current name), `engineer/skills/crap-analyzer` is in the `crap-analyzer` plugin (CP7), `skills/atdd` (CP3 + CP5), `skills/atdd-mutate` (CP8). `atdd-team` is handled in Phase 7.

**Files:**
- Modify: `engineer/skills/discover-acs/SKILL.md`
- Modify: `engineer/skills/plan/SKILL.md`
- Modify: `engineer/skills/simplify/SKILL.md`
- Modify: `crap-analyzer/skills/crap-analyzer/SKILL.md` (confirm exact path with `find . -name SKILL.md -path '*crap*'`)
- Modify: `skills/atdd/SKILL.md`
- Modify: `skills/atdd-mutate/SKILL.md`

- [ ] **Step 1: Confirm the crap-analyzer skill path**

Run: `find . -name SKILL.md -path '*crap*'`
Expected: one path; use it in Step 2.

- [ ] **Step 2: Add an entry-gate step to each skill's Workflow**

In each skill above, as the **first** workflow step (renumber the rest), insert this, substituting `<N-1>` with the checkpoint immediately before the one the skill produces (discover-acs: prior = 1.5; plan: prior = 3; simplify: prior = 5; crap-analyzer: prior = 6; atdd: prior = 2; atdd-mutate: prior = 7):

```markdown
### Step 0 — Entry gate

Verify the prior checkpoint is complete before starting. Run:
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_handoff.py <feature-dir> --through <N-1>`
(engineer-plugin skills) or the equivalent path to `dae_handoff.py` for
atdd-plugin skills. On a non-zero exit, **stop** and surface the gap to the
human — do not proceed.
```

For atdd-plugin skills (`skills/atdd`, `skills/atdd-mutate`), the script lives in the engineer plugin; reference it as: *"the engineer plugin's `scripts/dae_handoff.py`"* and note the human may need to supply the path if the engineer plugin is not installed.

- [ ] **Step 3: Add the exit-criteria assertion to each skill's Handoff section**

In each skill's `## Handoff` section, add:

```markdown
The handoff MUST include the `exit_criteria` block asserting each of this
checkpoint's exit criteria (Foundation Design Section 8) with `verified_by`,
`met`, and `evidence`. For `verified_by: tool` criteria, the evidence MUST be the
tool's actual output. The checkpoint is marked done only when every criterion is met.
```

- [ ] **Step 4: Verify**

Run: `grep -rl "Entry gate" engineer/skills skills crap-analyzer`
Expected: all six skill files listed.

- [ ] **Step 5: Commit**

```bash
git add engineer/skills/discover-acs/SKILL.md engineer/skills/plan/SKILL.md engineer/skills/simplify/SKILL.md skills/atdd/SKILL.md skills/atdd-mutate/SKILL.md crap-analyzer/skills/crap-analyzer/SKILL.md
git commit -m "feat: entry gate + exit_criteria assertion in checkpoint-advancing skills"
```

---

## Phase 4 — the `reorient` skill

### Task 9: Write the `reorient` SKILL.md

**Files:**
- Create: `engineer/skills/reorient/SKILL.md`

- [ ] **Step 1: Create the skill file**

Create `engineer/skills/reorient/SKILL.md`:

```markdown
---
name: reorient
description: Use mid-task when the working thread is lost — after a context compaction, a long agent run, or coming back to a feature unsure of the role, the current checkpoint, or the next action. Triggers — "/engineer.reorient", "reorient", "re-anchor", "what should I be doing right now", "I lost track", "where was I".
---

# reorient

Restore the working contract mid-task. After a context compaction or a long
run, an agent loses role identity, invents constraints that do not exist, skips
required steps, and loses the task thread. `reorient` reloads the durable state
that should have survived — the discipline contract first, the task pointer
second.

Read-only and advisory. It changes nothing, produces no artifact, and emits
**no handoff** — like `next`, the orientation block is the whole output; a
handoff would only restate it. The third skill exempt from the agentic summary
contract.

`reorient` is the mid-task, feature-scoped counterpart to `next` (project-scoped,
session-start).

## When to use

- Right after a context compaction (a `SessionStart` hook can auto-invoke it).
- Mid-task, when unsure of the role, the current checkpoint, or the next action.
- Returning to a feature after an interruption.

**Not for:** session-start "what should I pick up across the project" (`next`);
loading a feature not yet started (`prime-context`); validating artifacts
(`consistency-check`).

## Workflow

### Step 1 — Resolve and locate

Resolve the methodology root + manifest via
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_resolve.py` (see `references/resolving.md`).
Locate the feature (slug arg or branch name). If no feature is in scope, say so
and suggest `next` instead.

### Step 2 — Reload the discipline contract, then the task pointer

Read, read-only, in this order:

1. **Role + autonomy** — `CHARTER.md` + manifest: the autonomy level in force,
   and what the agent may and may not decide. Counters invented constraints.
2. **Current checkpoint + exit criteria** — the Checkpoint Exit Contract
   (Foundation Design Section 8) for the checkpoint `progress.md` shows in
   progress: its goal, its exit criteria, and which are already met.
3. **Non-negotiables** — verification independence and charter-mandated
   mutation: steps that must not be skipped regardless of cost.
4. **Current task + next action** — the `progress.md` CURRENT header.
5. **Feature contract** — `feature.md` outcome + scope. Counters goal drift.

Also run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_handoff.py <feature-dir>` — report any
checkpoint marked done without a complete handoff as a discipline gap.

### Step 3 — Emit the orientation block

Output one tight block, nothing else:

\`\`\`
You are <role> at autonomy <level>.
Feature NNN-slug — Checkpoint N (<goal>).
Exit criteria: <m>/<n> met — unmet: <list>.
Current task: <task> -> next action: <action>.
Must not skip: <non-negotiables>.
Constraints: <charter / autonomy limits>.
\`\`\`

### Step 4 — Stop

`reorient` orients; it does not act. The human resumes the work. No handoff.

## Optional: auto-invoke on compaction

A project may add a `SessionStart` hook (`source: compact`) that nudges
`/engineer.reorient` after every compaction. See
`${CLAUDE_PLUGIN_ROOT}/examples/session-start-reorient.md`. The hook is optional
project config, not part of this skill.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) —
  the Checkpoint Exit Contract (Section 8); agentic summary exemptions (Section 5)
- Sister skill: `next` — the project-scoped, session-start counterpart
```

- [ ] **Step 2: Verify the skill is discoverable**

Run: `cat engineer/skills/reorient/SKILL.md | head -3`
Expected: the frontmatter `name: reorient` line is present.

- [ ] **Step 3: Commit**

```bash
git add engineer/skills/reorient/SKILL.md
git commit -m "feat: add the reorient skill — mid-task re-anchoring"
```

### Task 10: Add the example SessionStart hook

**Files:**
- Create: `engineer/examples/session-start-reorient.md`

- [ ] **Step 1: Create the example file**

Create `engineer/examples/session-start-reorient.md`:

````markdown
# Example: auto-reorient on context compaction

Optional project config. When Claude Code compacts the context, this hook nudges
the agent to run `/engineer.reorient` before continuing feature work.

Add to the project's `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": ".claude/hooks/reorient-nudge.sh" }
        ]
      }
    ]
  }
}
```

Create `.claude/hooks/reorient-nudge.sh` (make it executable — `chmod +x`):

```sh
#!/bin/sh
# SessionStart hook — on a context compaction, nudge a DAE re-anchor.
input=$(cat)
case "$input" in
  *'"source":"compact"'*)
    printf '%s' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Context was compacted. Run /engineer.reorient before continuing feature work — restore role, current checkpoint, exit criteria, and the next action."}}'
    ;;
esac
```

The hook script checks the `source` field itself, so it stays silent on normal
startup/resume and only fires after a compaction.
````

- [ ] **Step 2: Verify**

Run: `cat engineer/examples/session-start-reorient.md | head -5`
Expected: the file exists with the heading.

- [ ] **Step 3: Commit**

```bash
git add engineer/examples/session-start-reorient.md
git commit -m "feat: example SessionStart hook for auto-reorient on compaction"
```

### Task 11: Pressure-test `reorient` and the handoff gate

These are writing-skills RED-GREEN checks, not code tests. REQUIRED BACKGROUND: superpowers:testing-skills-with-subagents.

**Files:** none modified unless a test reveals a gap.

#### reorient

- [ ] **Step 1: Baseline (RED)**

Dispatch a subagent with a simulated post-compaction scenario: give it a DAE feature folder where `progress.md` shows CP5 in progress with one unmet exit criterion (mutation not run), and a charter that mandates mutation. Prompt: "continue the feature." Do NOT mention `reorient`. Record whether it skips mutation, invents constraints, or loses the task.

- [ ] **Step 2: GREEN**

Repeat the scenario, this time instructing the subagent it may use `/engineer.reorient`. Confirm it re-anchors: identifies the role, the current checkpoint + unmet criteria, and that mutation must not be skipped.

- [ ] **Step 3: REFACTOR**

If the subagent still rationalizes skipping a non-negotiable or drifts, add an explicit counter to `reorient`'s "Non-negotiables" step (Step 2 item 3). Re-run Step 2 until it complies.

#### handoff gate

- [ ] **Step 4: Baseline (RED)**

Dispatch a subagent following a checkpoint-advancing skill (e.g. `plan`) for a feature whose prior checkpoint's handoff is missing. Do NOT mention the entry gate. Record whether it proceeds anyway.

- [ ] **Step 5: GREEN**

Repeat with the skill's Step 0 entry gate present (Task 8). Confirm the subagent runs `dae_handoff.py`, sees the non-zero exit, and stops + surfaces the gap rather than proceeding.

- [ ] **Step 6: REFACTOR**

If the subagent rationalizes past the gate ("the handoff is probably fine", "I'll write it after"), strengthen the entry-gate wording in Task 8's snippet and the affected SKILL.md files. Re-run Step 5 until it complies.

- [ ] **Step 7: Commit (only if a skill was edited)**

```bash
git add engineer/skills/reorient/SKILL.md engineer/skills/plan/SKILL.md
git commit -m "test: harden reorient and the handoff gate against rationalization"
```

---

## Phase 5 — the `progress.md` CURRENT header

### Task 12: Teach `progress-log` to maintain the CURRENT header

**Files:**
- Modify: `engineer/skills/progress-log/SKILL.md`

- [ ] **Step 1: Update the workflow step that recomputes the header**

In `engineer/skills/progress-log/SKILL.md`, in Workflow step 3, replace `recompute the Current stage header` with:

```markdown
recompute the **CURRENT header** — the fixed, parseable first line of
`progress.md`:
`> ▶ CP<N> <Stage> — <m>/<n> criteria met | NEXT: <action> | BLOCKED: <none|reason>`
Derive `<m>/<n>` from the latest handoff's `exit_criteria` block for the current
checkpoint; `NEXT` from that handoff's `recommended_next`; `BLOCKED` from any
unmet criterion that needs a human (else `none`).
```

- [ ] **Step 2: Verify**

Run: `grep -n "CURRENT header" engineer/skills/progress-log/SKILL.md`
Expected: the new text is present.

- [ ] **Step 3: Commit**

```bash
git add engineer/skills/progress-log/SKILL.md
git commit -m "feat: progress-log maintains the parseable CURRENT header"
```

---

## Phase 6 — rename `simplify` → `refine`

### Task 13: Rename the skill

**Files:**
- Rename: `engineer/skills/simplify/` → `engineer/skills/refine/`
- Modify: `engineer/skills/refine/SKILL.md`
- Modify: `engineer/skills/feature-edit/SKILL.md`

- [ ] **Step 1: Move the directory**

```bash
git mv engineer/skills/simplify engineer/skills/refine
```

- [ ] **Step 2: Update the skill's own name and references**

In `engineer/skills/refine/SKILL.md`:
- frontmatter: `name: simplify` → `name: refine`
- the H1 and prose: replace `simplify` → `refine` (the skill body, `/engineer.simplify` trigger, "Modeled on Claude Code's stock `/simplify`" stays as a factual reference to the stock skill — keep that one mention of the stock `/simplify`).

Run to find every occurrence: `grep -n "simplify" engineer/skills/refine/SKILL.md`
Replace all DAE-skill references; keep the single reference to Claude Code's stock `/simplify`.

- [ ] **Step 3: Update the cross-reference in `feature-edit`**

Run: `grep -n "simplify" engineer/skills/feature-edit/SKILL.md`
Replace `simplify` → `refine` in that reference.

- [ ] **Step 4: Verify no stray DAE-skill references remain**

Run: `grep -rn "engineer.simplify\|\`simplify\`" engineer/ skills/ agents/ --include='*.md'`
Expected: no matches except the deliberate stock-`/simplify` mention in `refine/SKILL.md`.

- [ ] **Step 5: Commit**

```bash
git add engineer/skills/refine engineer/skills/feature-edit/SKILL.md
git commit -m "refactor: rename the simplify skill to refine"
```

---

## Phase 7 — `atdd-team` rewrite

### Task 14: Rewrite `atdd-team/SKILL.md` for fresh per-phase agents

**Files:**
- Modify: `skills/atdd-team/SKILL.md`

- [ ] **Step 1: Read the current file**

Run: `cat skills/atdd-team/SKILL.md`
Note the current structure (Team Detection, Roles, 6 Workflow Phases, etc.).

- [ ] **Step 2: Replace the "Roles" section**

Replace the Roles table with five roles and the fresh-per-phase model:

```markdown
## Roles

Each phase is run by a **fresh agent invocation** scoped to that phase — no
agent persists across phases. Persistent agents erode (lose role identity,
invent constraints, skip steps) as their context compacts; a fresh per-phase
agent reloads its instructions clean. The "team" exists for parallelism across
features, not for long-lived agents.

| Role | Maps to | Owns phase |
|------|---------|-----------|
| `spec-writer` | discuss, discover-acs, atdd spec step | 1 Spec Writing |
| `reviewer` | spec-guardian agent | 2 Spec Review |
| `implementer` | atdd impl, pipeline-builder | 3 Pipeline Gen, 4 Implementation |
| `refiner` | the engineer plugin's `refine` skill | 5 Refine |
| `architect` | consistency-check, crap-analyzer, atdd-mutate | 6 Verify & Harden |

The **team lead** owns the workflow, approves all work, and verifies the
`agent_id` independence binding (below). The team lead never delegates approval.
```

- [ ] **Step 3: Add the durable-handoff + agent_id + role-boundary rules**

After the Roles section, add:

```markdown
## Coordination rules

- **Durable handoffs, not chat.** Each phase ends by writing a handoff summary
  to `features/NNN-slug/handoffs/` (the engineer plugin's handoff contract, with
  the `exit_criteria` block). The next phase's fresh agent reads the prior
  handoff for context — coordination survives a context compaction.
- **Phase gate = checkpoint exit criteria.** A phase is done only when its
  handoff asserts every exit criterion met (Foundation Design Section 8). Run
  `dae_handoff.py <feature> --through <prior-cp>` before starting a phase.
- **`agent_id` independence (Principle 7).** The `architect`'s `agent_id` must
  differ from both the `implementer`'s and the `refiner`'s — the verifier
  verifies neither its own code nor its own refinement. The team lead checks it.
- **Role boundary.** The `implementer` takes the code to green only — it does
  NOT do deep refactoring; that is the `refiner`'s phase. Every phase handoff
  states explicitly what was NOT done and what is left for the next role.
- **Per-phase anchor.** Each phase agent's spawn prompt embeds a `reorient`-style
  anchor: role, autonomy level, the prior handoff, the phase's exit criteria,
  and the non-negotiables.
```

- [ ] **Step 4: Update Phase 5 and Phase 6**

Replace the old Phase 5 ("Post-Implementation Review") and Phase 6 ("Mutation Testing (Optional)") with:

```markdown
### Phase 5 — Refine

**Assign to:** a fresh `refiner` agent.

After both test streams are green, the refiner runs the engineer plugin's
`refine` skill — the post-green code-improvement pass (reuse, quality,
efficiency lenses; charter-filtered).

**Gate:** Checkpoint 6 exit criteria met — refine ran, both streams still green,
charter filter applied. Handoff written.

### Phase 6 — Verify & Harden

**Assign to:** a fresh `architect` agent — `agent_id` MUST differ from the
implementer's and the refiner's.

Independent verification and hardening:
1. `consistency-check` — artifacts agree
2. `crap-analyzer` — CRAP + coverage (Checkpoint 7)
3. mutation testing — **driven by the charter's mutation policy**, not agent
   discretion. If the charter mandates mutation, it runs; the architect does not
   skip it because it is slow. (Checkpoint 8)

**Gate:** Checkpoints 7 + 8 exit criteria met. Handoff written.
```

- [ ] **Step 5: Update the Phases overview / any phase list to 6 phases**

Ensure the workflow lists exactly: 1 Spec Writing, 2 Spec Review, 3 Pipeline Generation, 4 Implementation, 5 Refine, 6 Verify & Harden. Update Phase 3/4 descriptions to note each is run by a fresh `implementer` invocation.

- [ ] **Step 6: Verify**

Run: `grep -n "fresh\|refiner\|architect\|agent_id\|Verify & Harden" skills/atdd-team/SKILL.md`
Expected: matches for the new roles, the fresh-per-phase rule, and the renamed phases.

- [ ] **Step 7: Commit**

```bash
git add skills/atdd-team/SKILL.md
git commit -m "feat: atdd-team — fresh per-phase agents, 5 roles, exit-criteria gates"
```

### Task 15: Rewrite `atdd-team/references/prompts.md`

**Files:**
- Modify: `skills/atdd-team/references/prompts.md`

- [ ] **Step 1: Read the current file**

Run: `cat skills/atdd-team/references/prompts.md`

- [ ] **Step 2: Replace "Team Creation" with per-phase spawn prompts**

The team is no longer created once with three standing members. Replace the "Team Creation" section with guidance that each phase **spawns a fresh agent**. For each phase, the spawn prompt MUST embed the anchor block:

```markdown
## Per-phase agent spawn

Each phase spawns a fresh agent. Every spawn prompt begins with this anchor:

  You are the <role> for feature NNN-slug, at autonomy <level>.
  Phase <n> — <phase name>. This checkpoint's goal: <goal>.
  Exit criteria you must satisfy: <list>.
  Prior phase handoff: features/NNN-slug/handoffs/<file>.
  Non-negotiables: <verification independence; charter mutation policy>.
  Constraints: <charter / autonomy limits>.

Then the phase-specific instructions follow.
```

- [ ] **Step 3: Update each phase prompt**

For Phases 1–6, keep the existing phase-specific instructions but: (a) prepend the anchor block, (b) require the phase to end by writing a handoff with the `exit_criteria` block, (c) for Phase 5 use the `refiner` running `refine`, (d) for Phase 6 use the `architect` and state mutation is charter-driven. Remove any "send specs back as a message" wording — replace with "write the handoff."

- [ ] **Step 4: Update the Shutdown section**

Since agents are fresh per phase, there is no standing team to shut down. Replace the shutdown prompt with a one-line note: each phase agent ends when its handoff is written.

- [ ] **Step 5: Verify**

Run: `grep -n "anchor\|handoff\|refiner\|architect" skills/atdd-team/references/prompts.md`
Expected: the anchor block and handoff-ending wording are present; no "standing team" language remains.

Manually trace one phase transition in the rewritten prompts: confirm Phase N's prompt ends by writing a handoff to `handoffs/`, and Phase N+1's spawn prompt reads that handoff path as its context. Confirm the `architect` spawn prompt states its `agent_id` must differ from the implementer's and the refiner's.

- [ ] **Step 6: Commit**

```bash
git add skills/atdd-team/references/prompts.md
git commit -m "feat: atdd-team prompts — per-phase spawn anchors + durable handoffs"
```

---

## Phase 8 — `consistency-check` sweep + version bumps

### Task 16: Add the missing-handoff sweep to `consistency-check`

**Files:**
- Modify: `engineer/skills/consistency-check/SKILL.md`

- [ ] **Step 1: Read the current file**

Run: `cat engineer/skills/consistency-check/SKILL.md`
Find where it lists the validations it performs.

- [ ] **Step 2: Add the handoff-gap validation**

Add a validation item:

```markdown
- **Handoff completeness.** For each feature, run
  `${CLAUDE_PLUGIN_ROOT}/scripts/dae_handoff.py <feature-dir>`. Flag any
  checkpoint marked done in `progress.md` that has no complete handoff (missing,
  `interrupted`, or with an unmet `exit_criteria` entry). This is the
  after-the-fact sweep for handoff-as-gate (Foundation Design Section 5).
```

- [ ] **Step 3: Verify**

Run: `grep -n "Handoff completeness\|dae_handoff" engineer/skills/consistency-check/SKILL.md`
Expected: the new validation is present.

- [ ] **Step 4: Commit**

```bash
git add engineer/skills/consistency-check/SKILL.md
git commit -m "feat: consistency-check sweeps for missing/incomplete handoffs"
```

### Task 17: Version bumps

**Files:**
- Modify: `engineer/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `skills/atdd/SKILL.md`, `skills/atdd-team/SKILL.md`, `skills/atdd-mutate/SKILL.md`

- [ ] **Step 1: Bump the engineer plugin 0.2.0 → 0.3.0**

In `engineer/.claude-plugin/plugin.json`: `"version": "0.2.0"` → `"version": "0.3.0"`.
In `.claude-plugin/marketplace.json`: the `engineer` plugin entry `"version": "0.2.0"` → `"version": "0.3.0"`.

- [ ] **Step 2: Bump the atdd plugin 0.5.0 → 0.6.0**

In `.claude-plugin/plugin.json`: `"version": "0.5.0"` → `"version": "0.6.0"`.
In `.claude-plugin/marketplace.json`: the `atdd` plugin entry → `"0.6.0"` (leave the top-level marketplace `metadata.version` unchanged).
In `skills/atdd/SKILL.md`, `skills/atdd-team/SKILL.md`, `skills/atdd-mutate/SKILL.md`: `version: 0.5.0` → `version: 0.6.0`.

- [ ] **Step 3: Verify**

Run: `grep -rn '"version"\|^version:' .claude-plugin engineer/.claude-plugin skills/atdd/SKILL.md skills/atdd-team/SKILL.md skills/atdd-mutate/SKILL.md`
Expected: engineer = 0.3.0, atdd = 0.6.0 everywhere, marketplace `metadata.version` unchanged.

- [ ] **Step 4: Run the full script test suite**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — all tests green (including `test_dae_handoff`).

- [ ] **Step 5: Commit**

```bash
git add engineer/.claude-plugin/plugin.json .claude-plugin/plugin.json .claude-plugin/marketplace.json skills/atdd/SKILL.md skills/atdd-team/SKILL.md skills/atdd-mutate/SKILL.md
git commit -m "chore: bump engineer 0.3.0, atdd 0.6.0 — context-resilient discipline"
```

---

## Final verification

- [ ] **All script tests pass:** `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
- [ ] **No stray `simplify` DAE-skill references:** `grep -rn "engineer.simplify" engineer/ skills/ agents/`
- [ ] **The `reorient` skill exists:** `test -f engineer/skills/reorient/SKILL.md`
- [ ] **Notion:** Foundation Design has Section 8; Section 5 has the `exit_criteria` block; the methodology page has Principle 8.
- [ ] **Report** to the human: do not push — the human decides when to push.

---

## Notes for the executor

- **Spec coverage:** Component 1 → Tasks 1, 7, 8. Component 2 → Tasks 4–8, 16. Component 3 → Tasks 9–11. Component 4 → Tasks 2, 12. Component 5 → Tasks 14, 15. Component 6 → Tasks 2, 13. Component 7 → Tasks 1–3. Component 8 → Tasks 4–6, 11, 15.
- **Open item carried from the spec:** `reviewer` is kept as a separate 5th role. If the reviewer of this plan wants four roles, fold `reviewer` into the `spec-writer`'s phase and adjust Task 14's role table.
- **Exit criteria are a working draft** (Task 1's table). If executing reveals a criterion that an owning skill cannot actually verify, report it rather than weakening the skill.
