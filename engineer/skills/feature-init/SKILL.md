---
name: feature-init
description: Use when a new feature folder must be created for the DAE pipeline, or when discuss promotes/parks an idea. Triggers — "/engineer.feature-init", "create a feature", "start a new feature", "init a feature".
---

# feature-init

Create a feature folder for the DAE pipeline — `feature.md` (the Ready contract), the folder, a branch, and a tracker entry. Checkpoint 1.5.

## When to use

Two paths:
- **From `discuss`** — receives a `feature_intake` payload in context (park or promote outcome). No interview.
- **Standalone** — no payload; run the intake interview.

Detect the mode from whether a `feature_intake` payload is present.

**Not for:** brand-new ideas worth exploring first (`discuss`), or editing an existing feature (`feature-edit`).

## Workflow

1. **Resolve** — find `.engineer/manifest.yml`; resolve `methodology_root`. No manifest → point to `/engineer.onboard`.
2. **Gather intake** — from-discuss: read the payload. Standalone: interview — required fields one per turn (`title`, `slug`, `outcome`, `source_links`, `status`, `autonomy_level` if `status: ready`, `scope`), optional fields (`target`, `owner`, `area`, `relevant_adrs`, `tags`, `size`) bundled at the end.
3. **Validate** — slug format (kebab-case, lowercase, ASCII, ≤50, leading letter); `autonomy_level` ∈ `manifest.autonomy.allowed_levels` and within path overrides; `status: ready` requires `autonomy_level`; `relevant_adrs` exist. Slug collision: if existing feature is `parked` → offer promote-from-parked (flip status, keep handoffs); if `ready`/`in-progress` → redirect to `feature-edit`; if `done` → reject.
4. **Decomposition check** — if scope spans multiple competencies or sounds like several PRs, surface it; user proceeds as one feature or re-invokes per sub-feature with `parent_feature` set.
5. **Allocate number** — scan `features/` for max `NNN`, +1, 3-digit zero-padded. (Parallel runs may race — solo work won't hit it.)
6. **Create** — `features/NNN-<slug>/` with `feature.md` (per the Foundation Design feature.md schema), empty `handoffs/`, empty `.build/`. Add `.build/` to `.gitignore`. Do NOT create `progress.md`/`acs.md`/`spec.md`/`plan.md`/`session-log.md` — downstream skills produce those.
7. **Branch** — auto-create `git checkout -b <slug>` unless `CHARTER.md` declares a manual git policy.
8. **Tracker** — upsert a `TrackedFeature` via the driver (`local` mode = no-op); write the returned ref to `feature.md` `tracker_ref`.
9. **Handoff** — emit a summary.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: 1.5`; `recommended_next`: ready → "/engineer.prime-context then /engineer.discover-acs"; parked → "resume via /engineer.discuss <slug>".

If folder + `feature.md` succeed but branch or tracker fails, emit `status: interrupted` noting what's incomplete.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema, storage layout, naming
- [Discuss & Upstream Funnel](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — the `feature_intake` contract from discuss
- [Tracker Integration](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — driver interface
