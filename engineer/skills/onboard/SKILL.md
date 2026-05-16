---
name: onboard
description: Use to bring a project into the DAE methodology, or to check an onboarded project for gaps. Triggers — "/engineer.onboard", "onboard this project", "set up DAE here", "adopt the methodology", or when a DAE skill fails because no manifest exists.
---

# onboard

Checkpoint 0 — the DAE adoption ceremony. Establishes the charter, manifest, storage layout, and tracker, and migrates any existing spec-shaped work. Project-scope, run once. Every other DAE skill depends on what it produces.

## When to use

- **No `.engineer/manifest.yml`** → full onboard (Steps 1–8)
- **Manifest exists** → gap-check mode (validate, report gaps, don't re-onboard)

**Not for:** starting a feature (`discuss` / `feature-init`, after onboard); changing an existing charter (edit it directly, PR'd).

## Human-decision checkpoints

Onboarding is a **ceremony**, not a mechanical scaffold. Two of its outputs are *design decisions* reserved for the human — the agent drafts, the human decides:

- **The charter** (Step 2) — architecture, conventions, scope, quality and autonomy stance.
- **The tracking decision** (Step 4) — which tracker the project uses.

Pre-filling from an existing codebase is encouraged. **Rubber-stamping is not.** Onboarding does NOT complete until the human has explicitly signed off on the charter and chosen the tracker — exactly as `plan` does for architecture (agent proposes, human confirms before proceeding). If the human is not available to decide, stop and emit a handoff with `human_action_needed: decision` — do not auto-decide and move on.

## Workflow (full onboard)

1. **Repo topology** — ask single- vs multi-repo. Set `methodology_root` (and `repos[]` for multi-repo).
2. **Draft the charter, get sign-off** — draft `CHARTER.md`'s 7 mandatory sections (methodology, architecture, conventions, scope, agent team, quality stance, autonomy stance). For an existing codebase, pre-fill what's inferable from the repo. Then present it and get the human's explicit confirmation — section by section for the judgment-heavy ones (scope, quality stance, autonomy stance + path overrides). Do not proceed to Step 3 until the charter is signed off.
3. **Create the manifest** — fill `.engineer/manifest.yml` (paths, roadmap/tracker, team, repos, quality thresholds, mutation, verification, autonomy, agentic_summary).
4. **Tracking decision** — this is a human decision, not an agent default. Surface what the project appears to use (e.g. a repo full of Notion links → Notion) and ask the human to choose: `notion | github-projects | linear | jira | local`. `notion`: offer to create the tracker database (the `TrackedFeature` schema) or validate an existing one; API key via env var, never the manifest. `local`: feature folders are the tracker. Others: reserved — emit "not yet implemented". Never silently default to `local` to keep things moving.
5. **Bootstrap layout** — create `features/`, empty `.engineer/discussions.log`; ensure `.build/` is gitignored.
6. **Migrate existing work** — by current state: Speckit project (`.specify/` → `CHARTER.md` + `.engineer/`, `specs/NNN-slug/` → `features/NNN-slug/` with numbers inherited); plain `docs/specs/*.md` (move + split); GitHub Issues as specs (import one per slug); informal README specs (surface, prompt — don't auto-convert); greenfield (nothing). Always confirm before moving files.
7. **Onboarding intake** — walk the repo for feature-shaped chunks not yet formalized; per confirmed one, invoke `feature-init` (onboarding-intake mode).
8. **Handoff** — emit a summary.

## Gap-check mode

Manifest exists → don't re-onboard. Validate: `CHARTER.md` has all 7 sections; `manifest.yml` schema-valid; `features/` numbering monotonic; tracker config resolves; charter roles == `manifest.team.default_roles`. Report gaps with suggested fixes (mirrors `consistency-check --project`). Read-only.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. onboard is project-scope — its handoff goes to `.engineer/handoffs/` (no feature folder exists). `checkpoint: 0`; `artifacts`: `CHARTER.md`, `.engineer/manifest.yml`. `recommended_next`: "per feature, /engineer.prime-context then /engineer.discover-acs; new ideas, /engineer.discuss".

If onboarding stopped because the human wasn't available to sign off the charter or choose the tracker, emit `status: interrupted` with `human_action_needed: decision` — naming exactly which decisions are outstanding.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — charter format (§3), manifest schema (§2), storage layout (§1)
- [Discuss & Upstream Funnel](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — methodology_root, onboarding intake
- [Tracker Integration](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — tracker setup, Notion schema, auth
