---
name: progress-log
description: Use to propagate DAE state — turning handoff summaries into visible progress. Triggers — "/engineer.progress-log", "sync progress", "update the tracker", "reconcile the tracker", "refresh feature status".
---

# progress-log

The propagation engine of DAE visibility. Skills emit handoff summaries; `progress-log` turns them into the two visible state layers — `progress.md` (the per-feature glanceable file) and the external tracker.

When the foundations say "the agentic summary contract handles propagation," this skill *is* that propagation. `checkpoint: null`.

## When to use

- **Auto** — invoked after a handoff-emitting skill changes a DAE-managed field (status change, checkpoint completion). Scope = the triggering feature.
- **Manual** — `/engineer.progress-log <slug>` re-syncs one feature; `--project` reconciles all.

**Not for:** changing artifacts (`feature-edit`); validating consistency (`consistency-check`); a session wrap-up (`session-summary`).

## Workflow

1. **Resolve + scope** — find `.engineer/manifest.yml`; resolve `methodology_root` and tracker config. Scope = one feature (auto / `<slug>`) or all (`--project`).
2. **Read new handoffs** — `handoffs/*.md` not yet reflected in `progress.md` (compare timestamps against the last-synced marker).
3. **Update `progress.md`** — per handoff: update the Checkpoints table row (if `checkpoint:` set), append to Verification reports (if a verification skill), append to the Handoff log, recompute the Current stage header.
4. **Recompute tracked state** — derive the `TrackedFeature` record from local truth (`feature.md` + `progress.md`).
5. **Sync the tracker** — driver `upsert(TrackedFeature)`: local-wins on DAE-managed fields, tracker-managed fields (comments, labels) preserved. `local` mode = no-op. Write the result to `progress.md`'s "Tracker sync" line.
6. **(`--project` only) Drift report** — driver `reconcile()`; surface anything unexpected (orphan tracker entry, untracked local feature).

## Handoff exemption

**progress-log does NOT emit a handoff summary** — it is the single exception to the agentic summary contract. It is the mechanism that *processes* handoffs; emitting one would trigger another progress-log run, looping. Its record of work is the `progress.md` "Tracker sync" line. (Documented in the Foundation Design.)

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — `progress.md` schema, agentic summary contract + this exemption (Section 5)
- [Tracker Integration](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — driver interface, `TrackedFeature`, sync triggers, reconciliation
