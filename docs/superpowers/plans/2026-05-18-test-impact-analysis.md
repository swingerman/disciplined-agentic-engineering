# Test Impact Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `dae_impact.py` — a portable map+select tool so a code change runs only the acceptance scenarios it affects.

**Architecture:** `dae_impact.py` records, per feature, which source files each scenario's test touches (`.build/impact-map.json`) and selects the scenarios to run for a given `git diff`. It is language-agnostic — coverage collection stays framework-specific in `pipeline-builder`'s generated runner. When the map cannot prove a scenario is safe to skip, selection returns `ALL`.

**Tech Stack:** Python 3 stdlib only (matches `engineer/scripts/`), Markdown skill/Notion files.

**Source spec:** `docs/superpowers/specs/2026-05-18-test-impact-analysis-design.md`

---

## Orientation for the engineer

- `engineer/scripts/` holds stdlib-only Python scripts, each with a `test_*.py` sibling. Run all tests: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`.
- The acceptance IR (`features/NNN-slug/.build/spec.json`, produced by `dae_gherkin.py`) is a dict: `{"name": <feature>, "scenarios": [{"name": <str>, "steps": [...], ...}, ...]}`. A scenario's identity is its `name`.
- A **coverage feed** is a fixed JSON shape — `[{"scenario": "<id>", "files": ["src/a.py", ...]}, ...]` — produced by the project's runner; `dae_impact.py` consumes it without caring how coverage was collected.
- Never push. Commit locally per task. Notion edits use the Notion MCP; the Foundation Design page id is `3585ecde-e0e2-811b-bc67-ff4913c03207`.

## File structure

- `engineer/scripts/dae_impact.py` — the tool (scenario hashing, map build, selection, CLI).
- `engineer/scripts/test_dae_impact.py` — its stdlib `unittest` suite.
- `engineer/scripts/dae_resolve.py` — *modified*: validate the optional `acceptance.impact_analysis` flag.
- `agents/pipeline-builder.md` — *modified*: document the runner's coverage-collection and impact-run modes.
- `skills/atdd/SKILL.md` — *modified*: document the TIA inner loop.
- Notion: Foundation Design §2, §7.

---

## Phase 1 — `dae_impact.py`

### Task 1: Scenario hashing + map build

**Files:**
- Create: `engineer/scripts/dae_impact.py`
- Test: `engineer/scripts/test_dae_impact.py`

- [ ] **Step 1: Write the failing test**

Create `engineer/scripts/test_dae_impact.py`:

```python
#!/usr/bin/env python3
"""Tests for dae_impact — acceptance-scenario test impact analysis.

Run: python3 -m unittest test_dae_impact -v
"""
import unittest

import dae_impact as di

IR_V1 = {"name": "Login", "scenarios": [
    {"name": "valid login", "steps": [{"keyword": "Given", "text": "a user"}]},
    {"name": "bad password", "steps": [{"keyword": "When", "text": "wrong pw"}]},
]}

FEED = [
    {"scenario": "valid login", "files": ["src/auth.py", "src/user.py"]},
    {"scenario": "bad password", "files": ["src/auth.py"]},
]


class TestScenarioHashes(unittest.TestCase):
    def test_one_hash_per_scenario(self):
        h = di.scenario_hashes(IR_V1)
        self.assertEqual(set(h), {"valid login", "bad password"})

    def test_hash_changes_with_steps(self):
        h1 = di.scenario_hashes(IR_V1)
        ir2 = {"name": "Login", "scenarios": [
            {"name": "valid login",
             "steps": [{"keyword": "Given", "text": "a DIFFERENT user"}]},
            {"name": "bad password",
             "steps": [{"keyword": "When", "text": "wrong pw"}]},
        ]}
        h2 = di.scenario_hashes(ir2)
        self.assertNotEqual(h1["valid login"], h2["valid login"])
        self.assertEqual(h1["bad password"], h2["bad password"])


class TestBuildMap(unittest.TestCase):
    def test_file_map_reverse_index(self):
        m = di.build_map(IR_V1, FEED, "2026-05-18T1530")
        self.assertEqual(m["file_map"]["src/auth.py"],
                         ["bad password", "valid login"])
        self.assertEqual(m["file_map"]["src/user.py"], ["valid login"])

    def test_map_carries_hashes_and_timestamp(self):
        m = di.build_map(IR_V1, FEED, "2026-05-18T1530")
        self.assertEqual(m["built_at"], "2026-05-18T1530")
        self.assertEqual(set(m["scenario_hashes"]),
                         {"valid login", "bad password"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_impact -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dae_impact'`

- [ ] **Step 3: Write `dae_impact.py` with hashing + map build**

Create `engineer/scripts/dae_impact.py`:

```python
#!/usr/bin/env python3
"""dae_impact.py — test impact analysis for the DAE acceptance pipeline.

Records which source files each acceptance scenario's test touches, so a code
change runs only the affected scenarios. Language-agnostic: it consumes a
normalized coverage feed produced by the project's runner.

Usage:
  dae_impact.py build <feature-dir> <coverage-feed.json>
      Build features/NNN-slug/.build/impact-map.json from the IR + the feed.
  dae_impact.py select <feature-dir> [--format json]
      Print the scenario ids to run for the current `git diff`, or ALL.

Safety: when the map cannot prove a scenario is safe to skip, select prints
ALL. A false skip is a missed regression; a false run only costs time.

Exit codes:
    0  ok
    2  missing IR / feed / map
    3  usage error
"""
import hashlib
import json
import os
import subprocess
import sys

SOURCE_EXTENSIONS = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
                     ".go", ".rb", ".java", ".kt", ".rs", ".cs", ".php")


def scenario_hashes(ir):
    """Map each scenario name to a content hash of its IR (steps + data)."""
    result = {}
    for sc in ir.get("scenarios", []):
        blob = json.dumps(sc, sort_keys=True).encode("utf-8")
        result[sc["name"]] = hashlib.sha1(blob).hexdigest()[:12]
    return result


def build_map(ir, coverage_feed, built_at):
    """Build the impact map from the IR and a normalized coverage feed.

    coverage_feed: [{"scenario": <id>, "files": [<source file>, ...]}, ...]
    """
    file_map = {}
    for entry in coverage_feed:
        sid = entry["scenario"]
        for f in entry.get("files", []):
            file_map.setdefault(f, [])
            if sid not in file_map[f]:
                file_map[f].append(sid)
    for f in file_map:
        file_map[f].sort()
    return {
        "built_at": built_at,
        "scenario_hashes": scenario_hashes(ir),
        "file_map": file_map,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_impact -v`
Expected: PASS — 4 tests OK

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_impact.py engineer/scripts/test_dae_impact.py
git commit -m "feat: dae_impact.py — scenario hashing + impact-map build"
```

### Task 2: Scenario selection + the safety fallback

**Files:**
- Modify: `engineer/scripts/dae_impact.py`
- Test: `engineer/scripts/test_dae_impact.py`

- [ ] **Step 1: Write the failing test** — add to `test_dae_impact.py` before `if __name__`:

```python
class TestSelect(unittest.TestCase):
    def setUp(self):
        self.m = di.build_map(IR_V1, FEED, "2026-05-18T1530")

    def test_changed_file_selects_its_scenarios(self):
        sel = di.select_scenarios(IR_V1, self.m, ["src/user.py"])
        self.assertEqual(sel, ["valid login"])

    def test_shared_file_selects_all_its_scenarios(self):
        sel = di.select_scenarios(IR_V1, self.m, ["src/auth.py"])
        self.assertEqual(sel, ["bad password", "valid login"])

    def test_spec_changed_scenario_selected_without_file_change(self):
        ir2 = {"name": "Login", "scenarios": [
            {"name": "valid login",
             "steps": [{"keyword": "Given", "text": "a DIFFERENT user"}]},
            {"name": "bad password",
             "steps": [{"keyword": "When", "text": "wrong pw"}]},
        ]}
        sel = di.select_scenarios(ir2, self.m, [])
        self.assertEqual(sel, ["valid login"])

    def test_new_scenario_selected(self):
        ir2 = {"name": "Login", "scenarios": IR_V1["scenarios"] + [
            {"name": "locked out", "steps": [{"keyword": "Given", "text": "x"}]},
        ]}
        sel = di.select_scenarios(ir2, self.m, [])
        self.assertEqual(sel, ["locked out"])

    def test_unmapped_source_file_returns_all(self):
        sel = di.select_scenarios(IR_V1, self.m, ["src/brandnew.py"])
        self.assertEqual(sel, "ALL")

    def test_non_source_change_ignored(self):
        sel = di.select_scenarios(IR_V1, self.m, ["README.md"])
        self.assertEqual(sel, [])

    def test_missing_map_returns_all(self):
        self.assertEqual(di.select_scenarios(IR_V1, None, ["src/user.py"]),
                         "ALL")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_impact -v`
Expected: FAIL — `AttributeError: module 'dae_impact' has no attribute 'select_scenarios'`

- [ ] **Step 3: Add `select_scenarios` to `dae_impact.py`**

Append to `dae_impact.py`:

```python
def _is_source(path):
    """True if `path` looks like a project source file (could host behavior)."""
    return path.endswith(SOURCE_EXTENSIONS) and "/.build/" not in ("/" + path)


def select_scenarios(current_ir, impact_map, changed_files):
    """Scenario ids to run for `changed_files`, or the string 'ALL'.

    Selected = new/spec-changed scenarios (hash differs from the map) + every
    scenario mapped to a changed file. A changed source file absent from the
    map cannot be proven safe -> 'ALL'. A missing map -> 'ALL'.
    """
    if impact_map is None:
        return "ALL"
    current = scenario_hashes(current_ir)
    recorded = impact_map.get("scenario_hashes", {})
    file_map = impact_map.get("file_map", {})

    selected = set()
    for sid, h in current.items():
        if recorded.get(sid) != h:        # new or spec-changed
            selected.add(sid)
    for f in changed_files:
        if f in file_map:
            selected.update(file_map[f])
        elif _is_source(f):               # unmapped source -> not provably safe
            return "ALL"
    return sorted(selected)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd engineer/scripts && python3 -m unittest test_dae_impact -v`
Expected: PASS — 11 tests OK

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_impact.py engineer/scripts/test_dae_impact.py
git commit -m "feat: dae_impact.py — scenario selection + safety fallback"
```

### Task 3: The CLI (`build` + `select`)

**Files:**
- Modify: `engineer/scripts/dae_impact.py`
- Test: `engineer/scripts/test_dae_impact.py`

- [ ] **Step 1: Write the failing test** — add `import os`, `import shutil`, `import tempfile` to the top import block of `test_dae_impact.py` (alongside `import unittest`), then add before `if __name__`:

```python
def _feature_dir(ir):
    """A temp feature dir with .build/spec.json written. Caller cleans up."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".build"))
    with open(os.path.join(d, ".build", "spec.json"), "w", encoding="utf-8") as f:
        json.dump(ir, f)
    return d


class TestCli(unittest.TestCase):
    def test_build_writes_map(self):
        d = _feature_dir(IR_V1)
        self.addCleanup(shutil.rmtree, d)
        feed_path = os.path.join(d, "feed.json")
        with open(feed_path, "w", encoding="utf-8") as f:
            json.dump(FEED, f)
        rc = di.main(["build", d, feed_path])
        self.assertEqual(rc, 0)
        with open(os.path.join(d, ".build", "impact-map.json")) as f:
            m = json.load(f)
        self.assertIn("src/auth.py", m["file_map"])

    def test_build_missing_ir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        self.assertEqual(di.main(["build", d, "nope.json"]), 2)

    def test_load_map_absent(self):
        d = _feature_dir(IR_V1)
        self.addCleanup(shutil.rmtree, d)
        self.assertIsNone(di.load_map(d))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_impact -v`
Expected: FAIL — `AttributeError: module 'dae_impact' has no attribute 'main'`

- [ ] **Step 3: Add the file helpers and `main` to `dae_impact.py`**

Append to `dae_impact.py`:

```python
def _read_json(path):
    """Parse a JSON file, or None if it is missing/unreadable."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_ir(feature_dir):
    """The acceptance IR for a feature, or None."""
    return _read_json(os.path.join(feature_dir, ".build", "spec.json"))


def load_map(feature_dir):
    """The impact map for a feature, or None if not built yet."""
    return _read_json(os.path.join(feature_dir, ".build", "impact-map.json"))


def _changed_files(start_dir):
    """Repo-relative paths changed vs. the base branch's merge-base."""
    try:
        root = subprocess.run(
            ["git", "-C", start_dir, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True).stdout.strip()
        base = (subprocess.run(
            ["git", "-C", root, "rev-parse", "--abbrev-ref", "origin/HEAD"],
            capture_output=True, text=True).stdout.strip() or "origin/main")
        out = subprocess.run(
            ["git", "-C", root, "diff", "--name-only", "--merge-base", base],
            capture_output=True, text=True, check=True).stdout
        return out.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def _utc_stamp():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M")


def main(argv):
    if len(argv) < 2 or argv[0] not in ("build", "select"):
        sys.stderr.write(__doc__.split("Usage:")[1].split("\n\n")[0])
        return 3
    command, feature_dir = argv[0], argv[1]

    ir = load_ir(feature_dir)
    if ir is None:
        sys.stderr.write("no .build/spec.json in %s — run the parser first\n"
                         % feature_dir)
        return 2

    if command == "build":
        if len(argv) < 3:
            sys.stderr.write("usage: dae_impact.py build <feature-dir> <feed.json>\n")
            return 3
        feed = _read_json(argv[2])
        if feed is None:
            sys.stderr.write("cannot read coverage feed: %s\n" % argv[2])
            return 2
        m = build_map(ir, feed, _utc_stamp())
        out_path = os.path.join(feature_dir, ".build", "impact-map.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2, sort_keys=True)
        sys.stderr.write("impact map written: %s\n" % out_path)
        return 0

    # command == "select"
    fmt = "text"
    if "--format" in argv:
        i = argv.index("--format")
        fmt = argv[i + 1] if i + 1 < len(argv) else "text"
    sel = select_scenarios(ir, load_map(feature_dir), _changed_files(feature_dir))
    if fmt == "json":
        json.dump(sel, sys.stdout)
        sys.stdout.write("\n")
    elif sel == "ALL":
        sys.stdout.write("ALL\n")
    else:
        for sid in sel:
            sys.stdout.write(sid + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the full test suite**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — all scripts green, including 14 in `test_dae_impact`.

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_impact.py engineer/scripts/test_dae_impact.py
git commit -m "feat: dae_impact.py — build + select CLI"
```

---

## Phase 2 — Manifest flag

### Task 4: Validate `acceptance.impact_analysis` in `dae_resolve.py`

**Files:**
- Modify: `engineer/scripts/dae_resolve.py`
- Test: `engineer/scripts/test_dae_resolve.py`

- [ ] **Step 1: Write the failing test** — add to `test_dae_resolve.py` before `if __name__`:

```python
class TestImpactAnalysisFlag(unittest.TestCase):
    def test_bad_value_rejected(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "acceptance": {"impact_analysis": "maybe"}}
        errors, _ = dr.validate_manifest(m)
        self.assertTrue(any("impact_analysis" in e for e in errors))

    def test_valid_value_ok(self):
        m = {"methodology_version": "0.2",
             "roadmap": {"type": "local"}, "tracker": {"type": "local"},
             "acceptance": {"impact_analysis": "on"}}
        errors, _ = dr.validate_manifest(m)
        self.assertEqual([e for e in errors if "impact_analysis" in e], [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd engineer/scripts && python3 -m unittest test_dae_resolve -v`
Expected: FAIL — the bad value is not rejected.

- [ ] **Step 3: Add the enum constant and check**

In `dae_resolve.py`, after the `AGENTIC_SUMMARY_FORMATS` constant, add:

```python
IMPACT_ANALYSIS_VALUES = {"on", "off"}
```

Then inside `validate_manifest`, in the "Enums" group (after the existing
`_check_enum` calls), add:

```python
    _check_enum(errors, manifest, "acceptance", "impact_analysis",
                IMPACT_ANALYSIS_VALUES)
```

- [ ] **Step 4: Run the full test suite**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — all green.

- [ ] **Step 5: Commit**

```bash
git add engineer/scripts/dae_resolve.py engineer/scripts/test_dae_resolve.py
git commit -m "feat: dae_resolve validates the acceptance.impact_analysis flag"
```

---

## Phase 3 — Pipeline integration docs

### Task 5: Document the runner modes in `pipeline-builder`

**Files:**
- Modify: `agents/pipeline-builder.md`

- [ ] **Step 1: Read the current file**

Run: `cat agents/pipeline-builder.md`. Find the section that describes what the runner generates (the "Runner" responsibility, around the Core Responsibility / Process section).

- [ ] **Step 2: Add a Test Impact Analysis section**

After the section describing the runner, add:

```markdown
## Test Impact Analysis (optional)

When `manifest.acceptance.impact_analysis` is `on`, the generated runner
gains two modes built on the portable `dae_impact.py`:

- **Coverage-collection mode** — run the acceptance scenarios under the
  project's coverage tool, attribute coverage per scenario, and emit a
  normalized coverage feed: `[{"scenario": "<id>", "files": ["src/a.py", ...]},
  ...]`. Then run `dae_impact.py build <feature-dir> <feed.json>` to refresh
  `features/NNN-slug/.build/impact-map.json`. Do this on every full run.
- **Impact-run mode** — run `dae_impact.py select <feature-dir>`; it prints the
  scenario ids to run, or `ALL`. Run only the generated tests for those
  scenarios (all, on `ALL`).

Coverage attribution is framework-specific — use the project's per-test
coverage contexts, or run one scenario's generated test file at a time under
coverage. `dae_impact.py` itself is language-agnostic; it only consumes the
normalized feed.

Impact-run mode is for the **inner loop** only. The full acceptance run still
happens at the Checkpoint 5 exit gate and in verification.
```

- [ ] **Step 3: Verify**

Run: `grep -n "Test Impact Analysis\|dae_impact" agents/pipeline-builder.md`
Expected: the new section is present.

- [ ] **Step 4: Commit**

```bash
git add agents/pipeline-builder.md
git commit -m "feat: pipeline-builder documents the impact-analysis runner modes"
```

### Task 6: Document the TIA inner loop in the `atdd` skill

**Files:**
- Modify: `skills/atdd/SKILL.md`

- [ ] **Step 1: Read the current file**

Run: `sed -n '127,148p' skills/atdd/SKILL.md`. This is Step 4 (Run Acceptance Tests) and Step 5 (Implement with TDD).

- [ ] **Step 2: Add a TIA note to Step 5**

In `skills/atdd/SKILL.md`, after the Step 5 ("Implement with TDD") numbered list and before the "**Both streams must pass:**" line, insert:

```markdown
**Faster iteration with impact analysis:** if the project has
`acceptance.impact_analysis: on`, the runner's impact-run mode (`dae_impact.py
select`) runs only the scenarios your change affects — use it for the tight
TDD loop. The **full** acceptance run still gates Step 5's completion: do not
mark the feature done until every scenario passes a full run.
```

- [ ] **Step 3: Verify**

Run: `grep -n "impact analysis\|dae_impact" skills/atdd/SKILL.md`
Expected: the new note is present.

- [ ] **Step 4: Commit**

```bash
git add skills/atdd/SKILL.md
git commit -m "feat: atdd skill documents the impact-analysis inner loop"
```

---

## Phase 4 — Foundation update + version bump

### Task 7: Foundation §7/§2 Notion updates, version bump, final verification

**Files:**
- Modify (Notion): Foundation Design page `3585ecde-e0e2-811b-bc67-ff4913c03207`
- Modify: `engineer/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

- [ ] **Step 1: Update Foundation §7 — the `.build/` layout note**

Fetch the page (`notion-fetch` id `3585ecde-e0e2-811b-bc67-ff4913c03207`). In Section 7's "Decisions locked" list, append:

```markdown
- **`.build/impact-map.json`** is a generated artifact (gitignored with the
  rest of `.build/`) — the test-impact map produced by `dae_impact.py`,
  refreshed on every full acceptance run.
```

- [ ] **Step 2: Update Foundation §2 — the `acceptance:` manifest key**

In Section 2's manifest YAML example, after the `architecture:` block and before `# Agentic summary contract`, insert:

```yaml
# Acceptance pipeline options
acceptance:
  impact_analysis: off                 # on | off — run only affected scenarios
```

And append to Section 2's "Decisions locked":

```markdown
- **`acceptance.impact_analysis`** (`on | off`, default `off`) — enables
  test impact analysis: the runner runs only the scenarios a change affects
  during iteration. The full acceptance run still gates Checkpoint 5.
```

- [ ] **Step 3: Verify the Notion edits**

Run (Notion MCP): `notion-fetch` id `3585ecde-e0e2-811b-bc67-ff4913c03207`.
Expected: §7 has the `impact-map.json` bullet; §2 has the `acceptance:` block and bullet.

- [ ] **Step 4: Bump the engineer plugin version**

In `engineer/.claude-plugin/plugin.json`: `"version": "0.4.0"` -> `"version": "0.5.0"`.
In `.claude-plugin/marketplace.json`: the `engineer` plugin entry `"version": "0.4.0"` -> `"version": "0.5.0"` (leave the marketplace `metadata.version` and the other plugins unchanged).

- [ ] **Step 5: Final verification**

Run: `cd engineer/scripts && python3 -m unittest discover -p 'test_*.py'`
Expected: PASS — all green.
Run: `cd engineer/scripts && python3 dae_impact.py 2>&1 | head -1`
Expected: a usage line (exit 3 — no args).

- [ ] **Step 6: Commit**

```bash
git add engineer/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump engineer 0.5.0 — test impact analysis"
```

---

## Self-review notes

- **Spec coverage:** Component 1 (`dae_impact.py`) → Tasks 1–3. Component 2 (pipeline-builder integration) → Task 5. Component 3 (loop placement) → Tasks 5, 6. Component 4 (Foundation/manifest) → Tasks 4, 7. Component 5 (testing) → the TDD steps throughout.
- **Safety fallback** — `select_scenarios` returns `ALL` on a missing map or any unmapped changed source file (Task 2). Over-running is safe; under-running is the forbidden failure.
- **`marketplace.json` `metadata.version`** stays unchanged — only the `engineer` plugin entry bumps.
