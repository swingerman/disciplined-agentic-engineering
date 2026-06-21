# Tracker drivers

How DAE skills read and write the tracker. The tracker is a **projection** of
local truth — `feature.md` + `progress.md` are authoritative; the tracker lets
collaborators see state without cloning the repo.

`manifest.tracker.type` selects the driver: `local | notion | github-projects | linear | jira`.

## The `TrackedFeature` record

One per feature. DAE-managed fields (the driver writes only these — it never
touches tracker-side comments, labels, assignees, custom views):

`slug`, `title`, `outcome`, `status`, `current_checkpoint`, `autonomy_level`,
`assignee`, `target`, `owner`, `area`, `tracker_ref`.

`assignee` is the **execution target** — `human` | `local` | `cloud` — i.e. who
runs the next checkpoint. It is distinct from any native people-assignee column
the tracker manages (which DAE never touches), and from `owner` (who is
accountable).

Sources: all from `feature.md` frontmatter except `current_checkpoint` (from `progress.md`).

## Two driver forms

- **`local`** — the feature folders *are* the tracker. A small script reads `TrackedFeature` records straight from the repo. No external system.
- **MCP-backed** (`notion`, and later `linear` / `github-projects` / `jira`) — the driver is *this reference*: it maps the driver operations onto the tools of a tracker MCP **the user already has connected**. DAE writes no API client and stores no credentials — the connected MCP owns the API and the auth. If `tracker.type` is MCP-backed and the MCP isn't connected, **fail fast** with a clear message.

## The `local` driver

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dae_tracker_local.py list [START_DIR]
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dae_tracker_local.py read SLUG [START_DIR]
```

`list` → JSON array of `TrackedFeature`; `read SLUG` → one record. `upsert` and
`delete` are **no-ops** in local mode — the feature files are the source of
truth, there is nothing separate to write. Stdlib-only.

## The `notion` driver

Requires a **Notion MCP connected**. The tracker is a Notion database whose ID
is `manifest.tracker.database_id`. Column ↔ field mapping: see the Tracker
Integration Foundation, Section 5.

| Operation | Notion MCP |
|-----------|------------|
| `upsert` (new) | create a page in the tracker data source (`tracker.database_id`); store the returned page URL/ID back into `feature.md` `tracker_ref` |
| `upsert` (existing) | update the page identified by the feature's `tracker_ref` |
| `read` / `list` | fetch / query the tracker data source; match rows by the `Slug` column |
| `delete` | soft — set `Status` to a done/archived value; never destructive |

Exact MCP tool names vary by Notion MCP version (e.g. page-create, page-update,
fetch). Use whatever the connected Notion MCP exposes for those operations.

`onboard` Step 4 creates or validates the tracker database; `feature-init`
upserts a row per new feature; `progress-log` upserts on checkpoint/status change.

## Sync direction — local-wins

Two-way, **local-wins on DAE-managed fields**: if a DAE-managed field differs
between local and tracker, local overwrites the tracker on next sync. Manual
edits to those fields don't survive. Tracker-managed fields (comments, custom
labels, views) are never touched — they survive every sync.

`reconcile()` — read all tracker rows, compare to local, surface drift. Used by
`progress-log --project` and `consistency-check`. Drift is reported, not
auto-merged; the human resolves.

## Tracker-as-intake — untriaged captures

The tracker is normally a *projection* of local truth. The one exception is
**intake**: a human can add a task — a bug or an improvement — directly to the
onboarded tracker, and DAE picks it up.

**Detection.** DAE owns slug assignment, so a human-created row has **no
`Slug`**. That is the contract: *a tracker row with an empty `Slug` is an
untriaged capture.* Optional helpers the human may set — `Type` (`bug | idea |
task`) and `Status: Inbox` — make intent explicit but aren't required; absent
`Type`, `next` infers it from the row's title/notes.

**Surfacing.** `reconcile()` already flags rows with no local feature behind
them. A slug-less orphan is **intake to triage**, not drift to fix — `next`
surfaces it in its TRIAGE bucket; `consistency-check` / `progress-log
--project` must NOT report it as an error.

**Promotion.** Triaging a capture into a unit of work (`feature-init`, `fix`,
or `discuss`) reuses the existing row: set the new feature/fix's `tracker_ref`
to that row and write the assigned `Slug` (+ `Status`) **back to the same row** —
never create a duplicate. Once the row has a slug, normal local-wins projection
resumes.

**Local mode.** There's no external tracker to add a row to, so the equivalent
capture queue is `.engineer/inbox.md` — one freeform line per item
(`- [ ] bug: <title> | blocks_user:yes (YYYY-MM-DD)`), flipped to
`- [x] … → <pointer>` once triaged. `next` reads it the same way. No parser —
it's eyeballed markdown; add one only if the list outgrows that.

## References

- [Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — the full contract, sync triggers, column schema
