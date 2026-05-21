---
name: feature-init
description: Use when a new feature folder must be created for the DAE pipeline, or when discuss promotes/parks an idea. Triggers — "/engineer.feature-init", "create a feature", "start a new feature", "init a feature".
---

# feature-init

Create a feature folder for the DAE pipeline — `feature.md` (the Ready contract), the folder, a branch, and a tracker entry. Checkpoint 1.5.

## When to use

Three paths:
- **From `discuss`** — receives a `feature_intake` payload in context (park or promote outcome). No interview.
- **Standalone** — no payload; run the intake interview.
- **Onboarding intake** — invoked by `onboard` (or directly) to formalize work that *already exists* in the codebase. The feature folder is reverse-engineered from an existing spec / branch / implementation. Enters at `status: in-progress` or `done`, not `ready`.

Detect from-discuss vs standalone by whether a `feature_intake` payload is present; onboarding intake is signalled by `onboard` (or an explicit "formalize existing feature" request).

**Not for:** brand-new ideas worth exploring first (`discuss`), or editing an existing feature (`feature-edit`).

## Workflow

Before the steps below, create one TodoWrite todo per workflow step (the full
list up front, as a roadmap). After Step 6 creates the feature folder, show the
**pipeline breadcrumb**: run
`${CLAUDE_PLUGIN_ROOT}/scripts/dae_progress.py <feature-dir>` and present its
output — for a just-initialized feature (no `progress.md` yet) it renders the
pipeline ahead. The breadcrumb is advisory and never blocks. See
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`.

1. **Resolve** — resolve the methodology root + manifest via `${CLAUDE_PLUGIN_ROOT}/scripts/dae_resolve.py` (see `references/resolving.md`). Exit 2 (no manifest) → point to `/engineer.onboard`.
2. **Gather intake** — from-discuss: read the payload. Standalone: interview — required fields one per turn (`title`, `slug`, `outcome`, `source_links`, `status`, `autonomy_level` if `status` is `ready`/`in-progress`/`done`, `scope`), optional fields (`target`, `owner`, `area`, `relevant_adrs`, `tags`, `size`, `validation_method`) bundled at the end. **`validation_method`** is a one-line description of how this feature will be validated beyond the default (passing acceptance + unit + mutation); examples: "manual smoke in staging", "canary 5% prod for 24h, watch dashboard X", "feature flag `new_checkout`, internal users for 1 week". A high `autonomy_level` should be matched by an explicit non-default `validation_method`. Onboarding intake: reverse-engineer the fields from the existing spec / branch / commits; set `status` to `in-progress` or `done` per how complete the work is.
3. **Validate** — slug format (kebab-case, lowercase, ASCII, ≤50, leading letter); `autonomy_level` ∈ `manifest.autonomy.allowed_levels` and within path overrides; any `status` other than `parked` requires `autonomy_level`; `relevant_adrs` exist. Slug collision: if existing feature is `parked` → offer promote-from-parked (flip status, keep handoffs); if `ready`/`in-progress` → redirect to `feature-edit`; if `done` → reject.
4. **Decomposition check** — if scope spans multiple competencies or sounds like several PRs, surface it; user proceeds as one feature or re-invokes per sub-feature with `parent_feature` set.
5. **Allocate number** — scan `features/` for max `NNN`, +1, 3-digit zero-padded. (Parallel runs may race — solo work won't hit it.) **Onboarding intake exception:** inherit the existing number — a feature migrated from a Speckit `specs/NNN-slug/` keeps its `NNN`; do not renumber.
6. **Create** — `features/NNN-<slug>/` with `feature.md` (per the Foundation Design feature.md schema), empty `handoffs/`, empty `.build/`. Add `.build/` to `.gitignore`. Include `branch: <name>` in `feature.md` frontmatter — the slug for greenfield; the adopted branch for onboarding intake. This is read by `${CLAUDE_PLUGIN_ROOT}/scripts/dae_branch.py` at every later checkpoint's Step 0 to enforce branch hygiene. If a `validation_method` was provided in the intake, include it in the frontmatter too — downstream skills (`plan`, `consistency-check`) consume it. Do NOT create `progress.md`/`acs.md`/`spec.md`/`plan.md`/`session-log.md` — downstream skills produce those.
7. **Branch** — auto-create `git checkout -b <slug>` unless `CHARTER.md` declares a manual git policy. **If the branch already exists** (common in onboarding intake — the feature's work is already on a branch) → use it, don't recreate.
8. **LSP language note** — if the feature touches a language not present in `manifest.validation.lsp.servers`, surface a one-line note ("this feature is mostly Rust — no LSP server recorded for Rust; LSP-backed lookup will fall back to grep+AST"). Inform-only; never blocks. Skip if `manifest.validation.lsp.servers` is absent (the project hasn't done the LSP probe yet — `onboard`'s gap-check will catch it).
9. **Tracker** — upsert a `TrackedFeature` via the driver per `references/tracker.md` (`local` = the `dae_tracker_local.py` no-op; `notion` = the connected Notion MCP); write the returned ref to `feature.md` `tracker_ref`.
10. **Handoff** — emit a summary.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: 1.5`; `recommended_next`: ready → "/engineer.prime-context then /engineer.discover-acs"; parked → "resume via /engineer.discuss <slug>"; onboarding intake → "/engineer.discover-acs (reverse-engineer mode)".

If folder + `feature.md` succeed but branch or tracker fails, emit `status: interrupted` noting what's incomplete.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema, storage layout, naming
- [Discuss & Upstream Funnel](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — the `feature_intake` contract from discuss
- `references/tracker.md` — the tracker drivers (local + Notion)
