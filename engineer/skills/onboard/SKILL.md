---
name: onboard
description: Use to bring a project into the Disciplined Agentic Engineering (DAE) methodology, or to check an already-onboarded project for gaps. Triggers include "/engineer.onboard", "onboard this project", "set up DAE here", "adopt the methodology", "initialize the engineer plugin", or naturally when a DAE skill fails because no manifest exists. Full onboard creates CHARTER.md and .engineer/manifest.yml through an interview, sets up the tracker, bootstraps features/, migrates any existing spec-shaped work, and detects existing features to formalize. Gap-check mode validates an already-onboarded project and reports what's missing or stale.
---

# onboard

Checkpoint 0 of DAE — the adoption ceremony. Brings a project into the methodology: establishes the charter, the manifest, the storage layout, the tracker, and migrates whatever spec-shaped work already exists.

Project-scope, run once per project. Every other DAE skill depends on what `onboard` produces — they fail with a pointer here when `.engineer/manifest.yml` is absent.

## Mode detection

Walk up from the working directory looking for `.engineer/manifest.yml`:
- **Not found** → **full onboard** (Steps 1–7)
- **Found** → **gap-check mode** (jump to "Gap-check mode" below)

## Full onboard

### Step 1 — Determine the methodology root and repo topology

Ask whether this is single-repo or multi-repo:
- **Single-repo** → `methodology_root` is the project root (`./`)
- **Multi-repo** → ask where the umbrella lives (a dedicated meta repo, or the primary code repo) and which repos participate. This sets `methodology_root` and the `repos[]` list.

### Step 2 — Create the charter (interview)

Interview the user to fill `CHARTER.md`'s seven mandatory sections (per Foundation Design Section 3):

1. **Methodology** — DAE version, default autonomy level, tracker, mutation policy stance
2. **Architecture** — stack, topology, data stores, key integrations (with rationale)
3. **Conventions** — code style, naming, test layout, commit/PR conventions
4. **Scope** — in scope / out of scope / non-goals
5. **Agent team** — the roles (must match `manifest.team.default_roles`)
6. **Quality stance** — the *why* behind the thresholds; path-specific rules
7. **Autonomy stance** — default level + path overrides

For an existing codebase, pre-fill what's inferable (stack, conventions, test layout from reading the repo) and ask the user to confirm/correct rather than answer from scratch. Write `CHARTER.md` at the methodology root.

### Step 3 — Create the manifest (interview)

Fill `.engineer/manifest.yml` (per Foundation Design Section 2):
- `methodology_version`, `methodology_root`, `charter`, `features_root`
- `roadmap` + `tracker` — type and config (see Step 4)
- `team.default_roles` — must include `verifier` if `verification.enforce_independence: true`
- `repos[]` — for multi-repo
- `quality_thresholds` — crap_max, coverage_min, mutation_score_min (+ per-repo overrides)
- `mutation` — scope, cadence, default_per_feature
- `verification` — enforce_independence, apply_to_checkpoints
- `autonomy` — default_level, allowed_levels, path_overrides
- `agentic_summary` — storage, format

### Step 4 — Set up the tracker

Ask which tracker: `notion | github-projects | linear | jira | local`.
- **`notion`** — offer to create the tracker database with the `TrackedFeature` column schema (per Tracker Integration Foundation), or validate an existing one; capture `database_id`. The API key goes in `NOTION_API_KEY` (env var) — instruct the user; never write secrets to the manifest.
- **`local`** — no external setup; the feature folders are themselves the tracker.
- **`github-projects` / `linear` / `jira`** — reserved in v0.1; emit "not yet implemented — use notion or local for now."

### Step 5 — Bootstrap the storage layout

Create `features/` at the methodology root. Create `.engineer/discussions.log` (empty). Ensure `.build/` is in the project `.gitignore`.

### Step 6 — Migrate existing spec-shaped work

Detect the project's current state and migrate accordingly:

| Current state | Migration action |
|---|---|
| **Speckit project** (`.specify/`, `constitution.md`, `specs/`) | `constitution.md` → seed `CHARTER.md` (extend with missing DAE sections); `specs/NNN-*/` → `features/NNN-*/`; add missing per-feature artifacts; reverse-engineer `acs.md` from existing `spec.md` |
| **Plain `docs/specs/*.md`** | Move each into a `features/NNN-slug/` folder; split content into `spec.md` + flag missing artifacts |
| **GitHub Issues as specs** | Import each issue into a feature folder (one issue → one slug) |
| **Informal specs in `README.md`** | Surface them to the user; prompt for formalization — do NOT auto-convert |
| **Greenfield (nothing)** | Bootstrap an empty `features/`; no migration needed |

Migration always confirms with the user before moving/creating files.

### Step 7 — Onboarding intake (detect existing features)

Walk the codebase for feature-shaped chunks not yet formalized (coherent modules, recent feature branches, TODO clusters). For each, prompt the user to confirm it's a feature, then invoke `feature-init` to create its folder (`status` set per how complete the work already is). This is the "onboarding intake" path — existing work slotted into the methodology.

### Step 8 — Emit the handoff summary

```markdown
---
skill: onboard
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: 0
artifacts:
  - CHARTER.md
  - .engineer/manifest.yml
findings_summary: <one line — e.g. "project onboarded; Speckit migration, 3 features detected">
human_action_needed: <yes if README specs were surfaced for formalization, else no>
human_action_kind: <review | none>
recommended_next: "Per feature: /engineer.prime-context then /engineer.discover-acs. New ideas: /engineer.discuss."
tracker_update: <tracker_ref or "local — no external tracker">
status: complete
---

# onboard — handoff summary

## What I did
Onboarded the project into DAE. Created CHARTER.md (<N> sections) and .engineer/manifest.yml. Tracker: <type>. Migration: <which current-state path>. Detected <M> existing features and formalized them via feature-init.

## Artifacts produced
- `CHARTER.md`
- `.engineer/manifest.yml`
- `features/` (bootstrapped; <M> feature folders if any were detected)

## Findings
<notable: what was migrated, what was inferred vs confirmed, README specs surfaced for the human, anything the charter interview left as a TODO>

## Human action needed?
<If README specs surfaced: "Yes — informal specs in README need formalization; review and run /engineer.discuss or /engineer.feature-init per real feature.">
<Else: "No — project is onboarded and ready.">

## Recommended next step
For each detected feature → /engineer.prime-context then /engineer.discover-acs. For new ideas → /engineer.discuss.

## Tracker update
<tracker_ref — feature(s) registered | "local mode — feature folders are the tracker">
```

## Gap-check mode

When `.engineer/manifest.yml` already exists, do NOT re-onboard. Instead validate and report:
- `CHARTER.md` present with all 7 mandatory sections
- `manifest.yml` schema-valid; enum values legal; `verifier` role present if independence enforced
- `features/` exists; folder numbering monotonic
- Tracker config resolves
- Charter section 5 roles == `manifest.team.default_roles`

Report gaps with suggested fixes (mirrors `consistency-check` project scope). Do not mutate — recommend the fix skill. Emit a handoff with `checkpoint: 0`, `findings_summary` describing the gaps.

## Key principles encoded

- **Onboarding is a ceremony, not a side effect.** Project setup is deliberate — the charter and manifest are interviewed, not guessed.
- **The manifest is the "I'm onboarded" credential.** Its presence is what every other skill checks.
- **Migration confirms before moving files.** onboard never silently restructures a repo.
- **Existing work is slotted in, not ignored.** Step 7 detects feature-shaped chunks so a project adopting DAE mid-stream doesn't start empty.

## When NOT to use this skill

- Project already onboarded and you want to *change* the charter/manifest → edit them directly or via `feature-edit`-style intent (charter changes are PR'd)
- You want to validate an onboarded project → that's gap-check mode here, or `consistency-check --project`
- You want to start a feature → `/engineer.discuss` or `/engineer.feature-init` (onboard must have run first)

## Cross-skill orchestration

- Upstream: nothing — onboard is the entry point
- This skill: creates CHARTER.md + manifest + features/ + tracker; migrates; detects features
- Invokes: `feature-init` (Step 7, per detected feature)
- Downstream: every other DAE skill — they all depend on the manifest onboard creates

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — charter format (Section 3), manifest schema (Section 2), storage layout (Section 1)
- [DAE Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — methodology_root, onboarding intake
- [DAE Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — tracker setup, Notion database schema, auth pattern
