---
name: progress-log
description: Use to propagate DAE state — turning agentic handoff summaries into visible progress. Triggers include "/engineer.progress-log", "sync progress", "update the tracker", "reconcile the tracker", "refresh feature status", or is auto-invoked by the agentic summary contract after a handoff-emitting skill changes a DAE-managed field. Reads new handoff summaries, updates progress.md (checkpoint table, verification reports, handoff log), and syncs the configured tracker via the driver. Manual --project mode reconciles all features (local wins on DAE-managed fields). This skill is the propagation engine — it is the one skill exempt from emitting its own agentic handoff summary.
---

# progress-log

The propagation engine of DAE visibility. Agentic skills emit handoff summaries; `progress-log` turns those summaries into the two visible state layers — `progress.md` (the per-feature glanceable file) and the external tracker.

When the foundation docs say "the agentic summary contract handles propagation," this skill *is* that propagation.

## When this skill runs

Not a checkpoint (`checkpoint: null`). Two invocation paths:

- **Auto** — invoked by the agentic summary contract after a handoff-emitting skill changes a DAE-managed field (status change, checkpoint completion — the hybrid trigger from the Tracker Integration Foundation). The triggering feature is the scope.
- **Manual** — `/engineer.progress-log <slug>` to re-sync one feature, or `/engineer.progress-log --project` to reconcile all features.

## Workflow

### Step 1 — Resolve and scope

Walk up to `.engineer/manifest.yml`; resolve `methodology_root` and the tracker config (`tracker.type`, `tracker.database_id`).

- Auto / `<slug>` mode → scope is one feature: `features/NNN-<slug>/`
- `--project` mode → scope is every `features/*/`

### Step 2 — Read new handoff summaries

For each feature in scope, read `handoffs/*.md` entries not yet reflected in `progress.md`. (Compare handoff timestamps against `progress.md`'s last-synced marker.)

Each handoff's frontmatter carries what's needed: `skill`, `checkpoint`, `artifacts`, `human_action_needed`, `recommended_next`, `tracker_update`, `agent_id`, `status`.

### Step 3 — Update `progress.md`

For each new handoff, update the per-feature `progress.md` (schema per Foundation Design Section 5):

- **Checkpoints table** — if the handoff has a `checkpoint:` value, update that row's status / artifact / produced-by / produced-at; for verification skills, also fill verified-by / verified-at
- **Verification reports table** — if `skill` is a verification skill (`crap-analyzer`, `atdd:mutate`), append a row
- **Handoff log** — append the handoff (timestamp, skill, human-action-needed flag, file link)
- **Current stage** header — recompute from the furthest in-progress checkpoint
- **Tracker sync** line — updated in Step 5

### Step 4 — Recompute the feature's tracked state

Derive the current `TrackedFeature` record from local truth:
- `status` from `feature.md` frontmatter
- `current_checkpoint` from `progress.md` checkpoints table
- `title`, `outcome`, `autonomy_level`, `target`, `owner`, `area` from `feature.md`

### Step 5 — Sync the tracker

Invoke the configured tracker driver's `upsert(TrackedFeature)`:
- **Local-wins on DAE-managed fields** — local truth overwrites the tracker's DAE-managed fields
- **Tracker-managed fields preserved** — comments, custom labels, assignees, custom views are never touched
- For `local` tracker mode → driver is a no-op (the feature files are themselves the tracker)

Write the sync result to `progress.md`'s "Tracker sync" line: `Last synced: <ISO timestamp> → <tracker> (<ref>)`.

### Step 6 (manual `--project` reconciliation only) — Drift report

In `--project` mode, after syncing, run the driver's `reconcile()`:
- Read all tracker entries, compare against local truth
- Where a DAE-managed field diverged, local already won in Step 5 — note it as resolved drift
- Surface anything unexpected (a tracker entry with no local feature folder; a local feature missing from the tracker) for the human

## Handoff exemption ⚠️

**progress-log does NOT emit an agentic handoff summary.** It is the deliberate, single exception to the agentic summary contract ("every agentic task ends with a structured summary").

Reason: progress-log is the mechanism that *processes* handoff summaries. If it emitted one, that summary would trigger another progress-log run → an infinite loop.

Its record of work is the `progress.md` "Tracker sync" line (timestamp + what was synced). For `--project` reconciliation, the drift report is shown to the user inline but not written as a handoff.

This exemption is documented in the Foundation Design (agentic summary contract section).

## When NOT to use this skill

- You want to change a feature's artifacts → that's `feature-edit`
- You want to validate artifact consistency → that's `consistency-check`
- You want a session wrap-up for the human → that's `session-summary`

## Cross-skill orchestration

progress-log sits at the end of the agentic summary contract's dispatch path.

- Upstream: any handoff-emitting skill (its summary triggers the auto path)
- This skill: reads handoffs → updates `progress.md` → syncs the tracker driver
- It emits no handoff of its own (see exemption above)

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — `progress.md` schema + agentic summary contract (Section 5), incl. the progress-log handoff exemption
- [DAE Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — driver interface, `TrackedFeature` contract, sync triggers, local-wins reconciliation
