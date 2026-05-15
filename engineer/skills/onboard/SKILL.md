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

## Workflow (full onboard)

1. **Repo topology** — ask single- vs multi-repo. Set `methodology_root` (and `repos[]` for multi-repo).
2. **Create the charter** — interview to fill `CHARTER.md`'s 7 mandatory sections (methodology, architecture, conventions, scope, agent team, quality stance, autonomy stance). For an existing codebase, pre-fill what's inferable and have the user confirm.
3. **Create the manifest** — fill `.engineer/manifest.yml` (paths, roadmap/tracker, team, repos, quality thresholds, mutation, verification, autonomy, agentic_summary).
4. **Tracker setup** — ask which tracker. `notion`: offer to create the tracker database (the `TrackedFeature` schema) or validate an existing one; API key via env var, never the manifest. `local`: no setup. Others: reserved — emit "not yet implemented".
5. **Bootstrap layout** — create `features/`, empty `.engineer/discussions.log`; ensure `.build/` is gitignored.
6. **Migrate existing work** — by current state: Speckit project (`.specify/` → `CHARTER.md` + `.engineer/`, `specs/` → `features/`); plain `docs/specs/*.md` (move + split); GitHub Issues as specs (import one per slug); informal README specs (surface, prompt — don't auto-convert); greenfield (nothing). Always confirm before moving files.
7. **Onboarding intake** — walk the repo for feature-shaped chunks not yet formalized; per confirmed one, invoke `feature-init`.
8. **Handoff** — emit a summary.

## Gap-check mode

Manifest exists → don't re-onboard. Validate: `CHARTER.md` has all 7 sections; `manifest.yml` schema-valid; `features/` numbering monotonic; tracker config resolves; charter roles == `manifest.team.default_roles`. Report gaps with suggested fixes (mirrors `consistency-check --project`). Read-only.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: 0`; `artifacts`: `CHARTER.md`, `.engineer/manifest.yml`. `recommended_next`: "per feature, /engineer.prime-context then /engineer.discover-acs; new ideas, /engineer.discuss".

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — charter format (§3), manifest schema (§2), storage layout (§1)
- [Discuss & Upstream Funnel](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — methodology_root, onboarding intake
- [Tracker Integration](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — tracker setup, Notion schema, auth
