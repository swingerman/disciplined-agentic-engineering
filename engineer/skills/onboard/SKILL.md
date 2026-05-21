---
name: onboard
description: Use to bring a project into the DAE methodology, or to check an onboarded project for gaps. Triggers — "/engineer.onboard", "onboard this project", "set up DAE here", "adopt the methodology", or when a DAE skill fails because no manifest exists.
---

# onboard

Checkpoint 0 — the DAE adoption ceremony. Establishes the charter, manifest, storage layout, and tracker. Project-scope, run once. Every other DAE skill depends on what it produces.

**The goal.** Onboarding a project to DAE succeeds when there is a clear path to **full ATDD coverage of every feature — existing and new.** A new feature is born covered by going through the pipeline. An *existing* feature is covered retroactively.

**Onboarding is discovery and goal-setting — not the ATDD adoption itself.** It discovers what's there (documented *and* undocumented), triages it by importance, assigns each feature a status, and produces a **consolidation backlog**. Bringing any one feature to full ATDD coverage is a *follow-up task per feature* — bounded, automatable, and a good candidate for remote-agent dispatch. Onboarding sets the path; it does not walk it.

A feature is **fully ATDD-covered** when its folder has `feature.md`, `acs.md`, `spec.md` (+ `.build/spec.json` IR), and **generated acceptance tests that pass against the code**.

## When to use

- **No `.engineer/manifest.yml`** → full onboard (Steps 1–11)
- **Manifest exists** → gap-check mode (validate, report gaps, don't re-onboard)

**Not for:** starting a feature (`discuss` / `feature-init`, after onboard); changing an existing charter (edit it directly, PR'd).

## Human-decision checkpoints

Onboarding is a **ceremony**, not a mechanical scaffold. Two of its outputs are *design decisions* reserved for the human — the agent drafts, the human decides:

- **The charter** (Step 3) — architecture, conventions, scope, quality and autonomy stance.
- **The tracking decision** (Step 5) — which tracker the project uses.

Pre-filling from an existing codebase is encouraged. **Rubber-stamping is not.** Onboarding does NOT complete until the human has explicitly signed off on the charter and chosen the tracker — exactly as `plan` does for architecture (agent proposes, human confirms before proceeding). If the human is not available to decide, stop and emit a handoff with `human_action_needed: decision` — do not auto-decide and move on.

## Workflow (full onboard)

Before the steps below, create one TodoWrite todo per workflow step (the full
list up front, as a roadmap) — see
`${CLAUDE_PLUGIN_ROOT}/references/progress-indicator.md`, Indicator 2. `onboard`
is project-scope and has no feature folder, so it does not show the pipeline
breadcrumb.

1. **Repo topology** — ask single- vs multi-repo. Set `methodology_root` (and `repos[]` for multi-repo).
2. **Discover validation infrastructure.** Before drafting the charter, probe what's available — the findings inform the autonomy stance.
   - **LSP probe.** Walk the repo for language signals (file extensions; package files: `requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml`, `*.csproj`, …). Aggregate primary languages. Inspect the agent's available tool list for an LSP capability (per `${CLAUDE_PLUGIN_ROOT}/references/code-lookup.md`). Report per-language: LSP backing reachable? For absent ones, suggest the standard install (`pyright`, `gopls`, `typescript-language-server`, `rust-analyzer`, etc.). Inform-only — never blocks. Record the per-language map in `manifest.validation.lsp.servers` (languages the user skips are omitted; the fallback ladder handles them).
   - **Environments interview** (all optional, batched in one `AskUserQuestion`): staging URL + deploy process; prod URL + deploy process + monitoring dashboards + alerting; feature-flag tool (`launchdarkly | unleash | flagsmith | growthbook | other`) + rollout policy. Record in `manifest.validation.{staging, prod, feature_flags}`. "Not yet" / "n/a" is a valid answer that omits the field.
   - **Autonomy proposal** for Step 3's charter draft, based on what was found:
     - staging + monitoring + feature flags → "high autonomy is well-supported by the validation infrastructure"
     - staging + monitoring, no feature flags → "medium-to-high; pre-declare rollout paths in plans"
     - staging only, no monitoring → "medium; add monitoring to expand the ceiling"
     - none of the above → "low-to-medium until validation surface grows; recommend setting up staging + monitoring as an upstream backlog item"

     The proposal is a recommendation — the human signs off (or overrides) at Step 3.
3. **Draft the charter, get sign-off** — draft `CHARTER.md`'s 7 mandatory sections (methodology, architecture, conventions, scope, agent team, quality stance, autonomy stance). For an existing codebase, pre-fill what's inferable from the repo. Then present it and get the human's explicit confirmation — section by section for the judgment-heavy ones (scope, quality stance, autonomy stance + path overrides). Do not proceed to Step 4 until the charter is signed off.
4. **Create the manifest** — fill `.engineer/manifest.yml` (paths, roadmap/tracker, team, repos, quality thresholds, mutation, verification, autonomy, agentic_summary).
5. **Tracking decision** — this is a human decision, not an agent default. Surface what the project appears to use (e.g. a repo full of Notion links → Notion) and ask the human to choose: `notion | github-projects | linear | jira | local`. `notion`: requires a connected Notion MCP — use it to create the tracker database (the `TrackedFeature` schema) or validate an existing one; DAE stores no API key (the MCP owns auth). `local`: feature folders are the tracker. Others: reserved — emit "not yet implemented". Never silently default to `local` to keep things moving. See `references/tracker.md`.
6. **Bootstrap layout** — create `features/`, empty `.engineer/discussions.log`; ensure `.build/` is gitignored.
7. **Discover features** — walk the repo (read-only) for every feature-shaped chunk, **documented and undocumented**:
   - *Documented* — Speckit `specs/NNN-slug/`, feature branches, `docs/specs/*.md`, GitHub Issues used as specs, informal README specs.
   - *Undocumented* — feature-shaped code with no spec at all: scan the packages/modules for coherent capabilities (a route group, a service, a UI surface) that no document covers.
   For each, record: source (or "code-only"), slug, state (spec-only / in-progress / shipped / merged), **code co-locations** (which packages/dirs the code lives in), and current DAE coverage (which of `feature.md` / `acs.md` / `spec.md` / acceptance tests exist — usually none). Greenfield project → discovery is empty; skip to Step 11.
8. **Triage** — with the human, rank the discovered features by importance to the project, and assign each a status (`done` shipped / `in-progress` / `ready` spec-only / `parked` dormant). Triage order drives the consolidation backlog's priority and which features get formalized first. Importance is a human judgement — surface a proposed ranking, let the human reorder.
9. **Write the consolidation backlog + seed the tracker** — two views of the triaged inventory:
   - `.engineer/consolidation.md`: the inventory as a **coverage table** (one row per feature, a column per coverage artifact) plus consolidation tasks in triage-priority order. Goal stated at the top: every row all-✅. Each task — "bring feature X to full ATDD coverage" — is bounded and **dispatchable to a remote agent**; note the suggested execution mode per task.
   - **Seed the tracker** — upsert a `TrackedFeature` row for *every* discovered feature (driver per `references/tracker.md`), not just the formalized ones, so the tracker shows the whole consolidation effort at a glance from day one. `status` from triage; `checkpoint` blank for features not yet in the DAE pipeline (`consolidation.md` tracks their coverage until they enter it).
10. **Formalize the starting features** — with the human, pick the 1–2 highest-triage features and run `feature-init` (onboarding-intake mode) on each now, so the project leaves onboarding with momentum. The rest stay as backlog tasks — do NOT formalize all of them in one onboard run.
11. **Handoff** — emit a summary; `recommended_next` points at the top consolidation-backlog task.

**Migration is not done inside `onboard`.** Moving `specs/NNN-slug/` → `features/NNN-slug/`, backfilling `acs.md`/`spec.md`, and generating acceptance tests are *consolidation tasks* — worked down feature by feature after onboarding, via the pipeline (`feature-init` → `discover-acs` reverse-engineer mode → `atdd:atdd` → pipeline generation), and dispatchable to remote agents. `onboard` only discovers, triages, and plans.

## Gap-check mode

Manifest exists → don't re-onboard. Validate: `CHARTER.md` has all 7 sections; `manifest.yml` schema-valid; `features/` numbering monotonic; tracker config resolves; charter roles == `manifest.team.default_roles`. Report gaps with suggested fixes (mirrors `consistency-check --project`). Read-only.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. onboard is project-scope — its handoff goes to `.engineer/handoffs/` (no feature folder exists). `checkpoint: 0`; `artifacts`: `CHARTER.md`, `.engineer/manifest.yml`. `recommended_next`: "per feature, /engineer.prime-context then /engineer.discover-acs; new ideas, /engineer.discuss".

If onboarding stopped because the human wasn't available to sign off the charter or choose the tracker, emit `status: interrupted` with `human_action_needed: decision` — naming exactly which decisions are outstanding.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — charter format (§3), manifest schema (§2), storage layout (§1)
- [Discuss & Upstream Funnel](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — methodology_root, onboarding intake
- `references/tracker.md` — the tracker drivers, setup, the Notion mapping
- [Tracker Integration](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — the full contract
