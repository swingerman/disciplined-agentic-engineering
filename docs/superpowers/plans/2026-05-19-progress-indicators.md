# DAE Progress Indicators — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface "where am I" passively while a DAE skill runs — both the pipeline checkpoint and the step within the current skill — across the `engineer` and `atdd` plugins.

**Architecture:** A new stdlib-only script, `dae_progress.py`, reads a feature's `progress.md` and prints a nine-stop pipeline breadcrumb; it is advisory and never blocks. Each checkpoint-advancing engineer skill calls it at Step 0. Both plugins also adopt a TodoWrite step-tracker convention — the full workflow-step list created up front as a roadmap. Two new reference files (one per plugin) hold the conventions; skills reference them instead of inlining.

**Tech Stack:** Python 3 stdlib only (`os`, `re`, `sys`, `unittest`); existing DAE scripts in `engineer/scripts/`; Markdown skill + reference files.

**Spec:** `docs/superpowers/specs/2026-05-19-progress-indicators-design.md`

---

## File Structure

- **Create** `engineer/scripts/dae_progress.py` — breadcrumb renderer. Parses `progress.md`, renders the breadcrumb against the canonical checkpoint list. Reuses `dae_handoff.read_progress` for the Checkpoints table.
- **Create** `engineer/scripts/test_dae_progress.py` — its `unittest` suite.
- **Create** `engineer/references/progress-indicator.md` — engineer-plugin convention (breadcrumb + TodoWrite).
- **Create** `atdd/references/progress-indicator.md` — atdd-plugin convention (TodoWrite only). Creates the atdd `references/` directory.
- **Modify** 5 gated engineer skills, `feature-init`, `onboard`, `reorient` — Step 0 wiring.
- **Modify** 3 atdd skills — Step 0 wiring.
- **Modify** `engineer/.claude-plugin/plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — version bumps to 0.7.0.

All shell steps run from the repo root `/Users/miklos/projects/atdd` unless noted.

---

## Task 1: `dae_progress.py` — parse the CURRENT header

**Files:**
- Create: `engineer/scripts/test_dae_progress.py`
- Create: `engineer/scripts/dae_progress.py`

- [ ] **Step 1: Write the failing test**

Create `engineer/scripts/test_dae_progress.py`:

```python
"""Tests for dae_progress.py."""
import os
import tempfile
import unittest

import dae_progress

# A representative progress.md CURRENT header (with the '>' blockquote marker).
CURRENT = "> ▶ CP3 Spec — 2/4 criteria met | NEXT: write spec.md | BLOCKED: none\n"

# A representative Checkpoints table: CP 0, 1.5, 2 done; CP 3 in progress.
TABLE = (
    "## Checkpoints\n"
    "| CP | Stage | Status |\n"
    "|----|-------|--------|\n"
    "| 0 | Onboard | done |\n"
    "| 1.5 | Ready | done |\n"
    "| 2 | ACs | done |\n"
    "| 3 | Spec | in progress |\n"
)


class ParseCurrentHeaderTests(unittest.TestCase):
    def test_extracts_all_fields(self):
        h = dae_progress.parse_current_header(CURRENT)
        self.assertEqual(h["cp"], 3)
        self.assertEqual(h["stage"], "Spec")
        self.assertEqual(h["met"], 2)
        self.assertEqual(h["total"], 4)
        self.assertEqual(h["next"], "write spec.md")
        self.assertEqual(h["blocked"], "none")

    def test_blocked_reason_is_captured(self):
        line = "> ▶ CP4 Plan — 1/3 criteria met | NEXT: revise | BLOCKED: awaiting ADR-012\n"
        h = dae_progress.parse_current_header(line)
        self.assertEqual(h["blocked"], "awaiting ADR-012")

    def test_half_checkpoint_number(self):
        line = "▶ CP1.5 Ready — 1/1 criteria met | NEXT: discover ACs\n"
        h = dae_progress.parse_current_header(line)
        self.assertEqual(h["cp"], 1.5)
        self.assertIsNone(h["blocked"])

    def test_absent_header_returns_none(self):
        self.assertIsNone(
            dae_progress.parse_current_header("# progress\n\nno header here\n"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_progress -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dae_progress'`.

- [ ] **Step 3: Write the minimal implementation**

Create `engineer/scripts/dae_progress.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_progress -v`
Expected: PASS — 4 tests in `ParseCurrentHeaderTests`.

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_progress.py engineer/scripts/test_dae_progress.py
git commit -m "feat: dae_progress.py — parse the progress.md CURRENT header"
```

---

## Task 2: `dae_progress.py` — render the breadcrumb

**Files:**
- Modify: `engineer/scripts/dae_progress.py`
- Modify: `engineer/scripts/test_dae_progress.py`

- [ ] **Step 1: Write the failing test**

Append to `engineer/scripts/test_dae_progress.py`, before the `if __name__` line:

```python
class RenderBreadcrumbTests(unittest.TestCase):
    def test_marks_done_current_and_pending(self):
        out = dae_progress.render_breadcrumb(
            "015-image-formats", {0, 1.5, 2}, 3, "CP3 Spec — 2/4 criteria met")
        self.assertIn("DAE ▸ 015-image-formats", out)
        self.assertIn("✓0 Onboard", out)
        self.assertIn("✓1.5 Ready", out)
        self.assertIn("✓2 ACs", out)
        self.assertIn("▶3 Spec", out)
        self.assertIn("·4 Plan", out)
        self.assertIn("·5 Implement", out)
        self.assertIn("·8 Harden", out)
        self.assertIn("CP3 Spec — 2/4 criteria met", out)

    def test_renders_all_nine_stops(self):
        out = dae_progress.render_breadcrumb("x", set(), None, "")
        for stage in ("Onboard", "Ready", "ACs", "Spec", "Plan",
                      "Implement", "Refine", "Verify", "Harden"):
            self.assertIn(stage, out)

    def test_empty_detail_is_omitted(self):
        out = dae_progress.render_breadcrumb("x", set(), None, "")
        self.assertEqual(len(out.splitlines()), 2)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_progress.RenderBreadcrumbTests -v`
Expected: FAIL — `AttributeError: module 'dae_progress' has no attribute 'render_breadcrumb'`.

- [ ] **Step 3: Write the minimal implementation**

In `engineer/scripts/dae_progress.py`, add the `CHECKPOINTS` constant immediately after the `import dae_handoff` line:

```python

# The canonical DAE pipeline — the single source of truth for stage order and
# names. CP5 (Implement) and CP8 (Harden) are stops with no dedicated skill.
CHECKPOINTS = [
    (0, "Onboard"), (1.5, "Ready"), (2, "ACs"), (3, "Spec"), (4, "Plan"),
    (5, "Implement"), (6, "Refine"), (7, "Verify"), (8, "Harden"),
]
```

Then add `render_breadcrumb` after `parse_current_header`:

```python


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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_progress -v`
Expected: PASS — 7 tests (`ParseCurrentHeaderTests` + `RenderBreadcrumbTests`).

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_progress.py engineer/scripts/test_dae_progress.py
git commit -m "feat: dae_progress.py — render the nine-stop pipeline breadcrumb"
```

---

## Task 3: `dae_progress.py` — `breadcrumb()` orchestrator + CLI

**Files:**
- Modify: `engineer/scripts/dae_progress.py`
- Modify: `engineer/scripts/test_dae_progress.py`

- [ ] **Step 1: Write the failing test**

Append to `engineer/scripts/test_dae_progress.py`, before the `if __name__` line:

```python
def _write_feature(parent, name, contents):
    """Create parent/name/ and, if contents is not None, parent/name/progress.md."""
    feat = os.path.join(parent, name)
    os.makedirs(feat)
    if contents is not None:
        with open(os.path.join(feat, "progress.md"), "w", encoding="utf-8") as f:
            f.write(contents)
    return feat


class BreadcrumbTests(unittest.TestCase):
    def test_full_progress_file(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "015-image-formats", CURRENT + "\n" + TABLE)
            out = dae_progress.breadcrumb(feat)
        self.assertIn("DAE ▸ 015-image-formats", out)
        self.assertIn("✓2 ACs", out)
        self.assertIn("▶3 Spec", out)
        self.assertIn("NEXT: write spec.md", out)
        self.assertNotIn("BLOCKED", out)  # blocked: none is omitted

    def test_blocked_reason_shown(self):
        header = "> ▶ CP4 Plan — 1/3 criteria met | NEXT: revise | BLOCKED: awaiting ADR-012\n"
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "042-export", header + "\n" + TABLE)
            out = dae_progress.breadcrumb(feat)
        self.assertIn("BLOCKED: awaiting ADR-012", out)

    def test_missing_progress_degrades(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "099-new", None)
            out = dae_progress.breadcrumb(feat)
        self.assertIn("099-new", out)
        self.assertIn("not yet started", out)
        self.assertIn("·0 Onboard", out)

    def test_no_header_degrades(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "022-x", TABLE)  # table only, no header
            out = dae_progress.breadcrumb(feat)
        self.assertIn("✓2 ACs", out)
        self.assertIn("no CURRENT header", out)


class MainTests(unittest.TestCase):
    def test_help_returns_zero(self):
        self.assertEqual(dae_progress.main(["--help"]), 0)

    def test_no_args_returns_zero(self):
        self.assertEqual(dae_progress.main([]), 0)

    def test_run_on_feature_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            feat = _write_feature(d, "015-x", CURRENT + "\n" + TABLE)
            self.assertEqual(dae_progress.main([feat]), 0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_progress.BreadcrumbTests -v`
Expected: FAIL — `AttributeError: module 'dae_progress' has no attribute 'breadcrumb'`.

- [ ] **Step 3: Write the minimal implementation**

In `engineer/scripts/dae_progress.py`, add `breadcrumb` and `main` after `render_breadcrumb`, then the `__main__` guard:

```python


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
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — every DAE script test, including the 14 new `test_dae_progress` tests. (The pre-existing suite was 128 tests; expect 142.)

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_progress.py engineer/scripts/test_dae_progress.py
git commit -m "feat: dae_progress.py — breadcrumb orchestrator + CLI"
```

---

## Task 4: `engineer/references/progress-indicator.md`

**Files:**
- Create: `engineer/references/progress-indicator.md`

- [ ] **Step 1: Create the reference file**

Create `engineer/references/progress-indicator.md` with exactly this content:

```markdown
# Pipeline progress indicator — shared contract

Every checkpoint-advancing engineer skill surfaces *where you are* — passively,
as it runs — through two indicators. This file is the canonical contract;
skills reference it instead of inlining.

## Indicator 1 — the pipeline breadcrumb

At **Step 0**, after the entry gate passes (or, for `feature-init`, at the
start of the workflow), run:

    ${CLAUDE_PLUGIN_ROOT}/scripts/dae_progress.py <feature-dir>

and show its output to the human verbatim. It renders the feature's position
across the nine-stop DAE pipeline:

    DAE ▸ 015-image-formats
    ✓0 Onboard · ✓1.5 Ready · ✓2 ACs · ▶3 Spec · ·4 Plan · ·5 Implement · ·6 Refine · ·7 Verify · ·8 Harden
    CP3 Spec — 2/4 criteria met · NEXT: write spec.md

**Advisory, never blocking.** Unlike the `dae_handoff.py` entry gate, a
non-zero exit or a missing `progress.md` never stops the skill — the breadcrumb
is orientation, not a gate. Show whatever it prints and continue.

`onboard` (Checkpoint 0) is project-scope — it has no feature folder — so it
does NOT call the breadcrumb. It uses Indicator 2 only.

## Indicator 2 — the in-skill step tracker

At the start of the skill, create **one TodoWrite todo per workflow step**, all
at once — the full list up front, so it doubles as a roadmap of the journey
ahead. Flip each todo to `in_progress` when its step begins and `completed`
when it ends. The TodoWrite panel is the live position indicator.

A step that spans many turns — an interview-style step such as the four-pass
AC interview — is split into **one sub-todo per pass**, so a long step shows
visible movement instead of sitting at `in_progress` for ten turns.

## The canonical pipeline

`0 Onboard · 1.5 Ready · 2 ACs · 3 Spec · 4 Plan · 5 Implement · 6 Refine ·
7 Verify · 8 Harden`. `dae_progress.py` holds this list as its source of truth;
`5 Implement` and `8 Harden` are pipeline stops with no dedicated skill.
```

- [ ] **Step 2: Commit**

```bash
git add engineer/references/progress-indicator.md
git commit -m "docs: add engineer progress-indicator reference"
```

---

## Task 5: Wire Step 0 into the 5 gated engineer skills

The five skills with a `dae_handoff.py … --through` entry gate each get the
same paragraph appended to their **Step 0** block.

**Files:**
- Modify: `engineer/skills/discover-acs/SKILL.md`
- Modify: `engineer/skills/atdd/SKILL.md`
- Modify: `engineer/skills/plan/SKILL.md`
- Modify: `engineer/skills/refine/SKILL.md`
- Modify: `engineer/skills/arch-check/SKILL.md`

- [ ] **Step 1: Append the breadcrumb paragraph to each skill's Step 0**

For each of the five files: Read the file, locate the Step 0 entry-gate text
(the sentence containing `dae_handoff.py` and `--through`), and immediately
after that sentence — still inside the Step 0 block — insert this paragraph:

```markdown

After the gate passes, show the **pipeline breadcrumb**: run
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_progress.py <feature-dir>` and present its
output to the human — it shows where this checkpoint sits in the DAE pipeline.
The breadcrumb is advisory: a non-zero exit or a missing `progress.md` never
blocks the skill. Then create one TodoWrite todo per workflow step below. See
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`.
```

- [ ] **Step 2: Verify the wiring landed in all five files**

Run: `grep -l 'dae_progress.py' engineer/skills/*/SKILL.md`
Expected: lists `discover-acs`, `atdd`, `plan`, `refine`, `arch-check`.

- [ ] **Step 3: Commit**

```bash
git add engineer/skills/discover-acs/SKILL.md engineer/skills/atdd/SKILL.md \
        engineer/skills/plan/SKILL.md engineer/skills/refine/SKILL.md \
        engineer/skills/arch-check/SKILL.md
git commit -m "feat: wire pipeline breadcrumb into the gated engineer skills"
```

---

## Task 6: Wire `feature-init`, `onboard`, and `reorient`

**Files:**
- Modify: `engineer/skills/feature-init/SKILL.md`
- Modify: `engineer/skills/onboard/SKILL.md`
- Modify: `engineer/skills/reorient/SKILL.md`

- [ ] **Step 1: `feature-init` — breadcrumb at the start of the workflow**

`feature-init` has no entry gate. Read `engineer/skills/feature-init/SKILL.md`,
locate the `## Workflow` heading, and insert this paragraph immediately after it
(before the numbered steps):

```markdown
Before the steps below, create one TodoWrite todo per workflow step (the full
list up front, as a roadmap). At the end, once `progress.md` exists, show the
**pipeline breadcrumb**: run
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_progress.py <feature-dir>` and present its
output — for a just-initialized feature it renders the pipeline ahead. The
breadcrumb is advisory and never blocks. See
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`.

```

- [ ] **Step 2: `onboard` — TodoWrite tracker only (no breadcrumb)**

`onboard` is project-scope (no feature folder). Read
`engineer/skills/onboard/SKILL.md`, locate the `## Workflow` heading, and insert
this paragraph immediately after it:

```markdown
Before the steps below, create one TodoWrite todo per workflow step (the full
list up front, as a roadmap) — see `${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`,
Indicator 2. `onboard` is project-scope and has no feature folder, so it does
not show the pipeline breadcrumb.

```

- [ ] **Step 3: `reorient` — call `dae_progress.py` for the breadcrumb line**

Read `engineer/skills/reorient/SKILL.md`. In Step 2, locate item 2
(`**Current checkpoint + exit criteria**`). Append this sentence to that item:

```markdown
 Run `${CLAUDE_PLUGIN_ROOT}/scripts/dae_progress.py <feature-dir>` and show its breadcrumb — the same pipeline-position line the checkpoint skills surface at Step 0.
```

- [ ] **Step 4: Verify**

Run: `grep -c 'dae_progress.py' engineer/skills/feature-init/SKILL.md engineer/skills/reorient/SKILL.md`
Expected: each file reports `1` (or more). `onboard` intentionally has none.

- [ ] **Step 5: Commit**

```bash
git add engineer/skills/feature-init/SKILL.md engineer/skills/onboard/SKILL.md \
        engineer/skills/reorient/SKILL.md
git commit -m "feat: wire progress indicators into feature-init, onboard, reorient"
```

---

## Task 7: `atdd/references/progress-indicator.md`

**Files:**
- Create: `atdd/references/progress-indicator.md` (creates the `atdd/references/` directory)

- [ ] **Step 1: Create the reference file**

Create `atdd/references/progress-indicator.md` with exactly this content:

```markdown
# Workflow progress indicator — shared contract

Every atdd skill surfaces *which step you are on* — passively, as it runs —
through the in-skill step tracker. This file is the canonical contract; skills
reference it instead of inlining.

The atdd skills run a whole multi-step workflow in a single invocation, so the
step tracker carries the full picture — there is no separate pipeline
breadcrumb and no progress file.

## The in-skill step tracker

At the **start of the skill**, create **one TodoWrite todo per workflow step
(or phase)**, all at once — the full list up front, so it doubles as a roadmap
of the journey ahead:

- `atdd` — one todo per Step 1–7.
- `atdd-mutate` — one todo per Step 1–6.
- `atdd-team` — one todo per Phase 1–6.

Flip each todo to `in_progress` when its step begins and `completed` when it
ends. The TodoWrite panel is the live position indicator.

A step that spans many turns is split into sub-todos, so a long step shows
visible movement instead of sitting at `in_progress` indefinitely.
```

- [ ] **Step 2: Commit**

```bash
git add atdd/references/progress-indicator.md
git commit -m "docs: add atdd progress-indicator reference"
```

---

## Task 8: Wire Step 0 into the 3 atdd skills

**Files:**
- Modify: `skills/atdd/SKILL.md`
- Modify: `skills/atdd-mutate/SKILL.md`
- Modify: `skills/atdd-team/SKILL.md`

- [ ] **Step 1: `atdd` — insert the step-tracker note**

Read `skills/atdd/SKILL.md`. Locate the `## Workflow` heading, and immediately
after it (before `### Step 1`) insert:

```markdown
Before Step 1, create one TodoWrite todo per step of this workflow (Steps 1–7),
all at once — the full list up front, as a roadmap. Flip each todo to
`in_progress` / `completed` as you go. See
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`.

```

- [ ] **Step 2: `atdd-mutate` — insert the step-tracker note**

Read `skills/atdd-mutate/SKILL.md`. Locate the `## Workflow` heading, and
immediately after it (before `### Step 1`) insert:

```markdown
Before Step 1, create one TodoWrite todo per step of this workflow (Steps 1–6),
all at once — the full list up front, as a roadmap. Flip each todo to
`in_progress` / `completed` as you go. See
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`.

```

- [ ] **Step 3: `atdd-team` — insert the step-tracker note**

Read `skills/atdd-team/SKILL.md`. Locate the `## Workflow Phases` heading, and
immediately after it (before `### Phase 1`) insert:

```markdown
Before Phase 1, create one TodoWrite todo per phase of this workflow
(Phases 1–6), all at once — the full list up front, as a roadmap. Flip each
todo to `in_progress` / `completed` as you go. See
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`.

```

- [ ] **Step 4: Verify**

Run: `grep -l 'progress-indicator.md' skills/*/SKILL.md`
Expected: lists `atdd`, `atdd-mutate`, `atdd-team`.

- [ ] **Step 5: Commit**

```bash
git add skills/atdd/SKILL.md skills/atdd-mutate/SKILL.md skills/atdd-team/SKILL.md
git commit -m "feat: wire in-skill step tracker into the atdd skills"
```

---

## Task 9: Version bumps to 0.7.0

**Files:**
- Modify: `engineer/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Bump the engineer plugin**

In `engineer/.claude-plugin/plugin.json`, change the `"version"` field from
`"0.6.0"` to `"0.7.0"`.

- [ ] **Step 2: Bump the atdd plugin**

In `.claude-plugin/plugin.json`, change the `"version"` field from `"0.6.0"` to
`"0.7.0"`.

- [ ] **Step 3: Bump both marketplace entries**

In `.claude-plugin/marketplace.json`, change the `"version"` field to `"0.7.0"`
in **both** the `"atdd"` plugin entry and the `"engineer"` plugin entry. (The
`crap-analyzer` entry stays at `0.1.0`.)

- [ ] **Step 4: Verify JSON validity and the full test suite**

Run:
```bash
python3 -c "import json; [json.load(open(p)) for p in ['engineer/.claude-plugin/plugin.json', '.claude-plugin/plugin.json', '.claude-plugin/marketplace.json']]" && echo "JSON OK"
cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'
```
Expected: `JSON OK`, then the full suite passes (142 tests).

- [ ] **Step 5: Commit**

```bash
git add engineer/.claude-plugin/plugin.json .claude-plugin/plugin.json \
        .claude-plugin/marketplace.json
git commit -m "chore: bump engineer and atdd plugins to 0.7.0"
```

---

## Self-review notes

- **Spec coverage:** Indicator 1 (`dae_progress.py` + wiring) → Tasks 1–6;
  Indicator 2 (TodoWrite convention) → Tasks 4–8; engineer reference → Task 4;
  atdd reference → Task 7; versioning → Task 9. `reorient` reuse → Task 6.
- **`onboard`** correctly gets the TodoWrite tracker only (project-scope, no
  feature folder) — Task 6 Step 2.
- **Graceful degradation** (missing `progress.md`, missing CURRENT header) is
  covered by `test_missing_progress_degrades` and `test_no_header_degrades`
  in Task 3.
- The atdd plugin's skills live at the repo-root `skills/` directory; the
  engineer plugin's skills live at `engineer/skills/`. Task 5/6 paths use
  `engineer/skills/…`; Task 8 paths use `skills/…`.
