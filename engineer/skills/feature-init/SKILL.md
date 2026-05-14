---
name: feature-init
description: Use when the user wants to create a new feature folder for the DAE pipeline, or when invoked by the discuss skill on a park or promote outcome. Triggers include "/engineer.feature-init", "create a feature", "start a new feature", "init a feature", "promote this idea". Performs intake interview (standalone mode) or consumes structured intake from discuss (from-discuss mode); allocates the next sequence number, creates the feature folder with feature.md (Ready contract) plus handoffs/ and .build/ subdirectories, opens a feature branch, creates a tracker entry via the configured driver, and emits the agentic handoff summary.
---

# feature-init

Create a new feature folder for the Disciplined Agentic Engineering (DAE) pipeline. Produces `feature.md` (the Ready contract per the foundation design), the folder structure, a feature branch, and a tracker entry. Emits an agentic handoff summary at completion.

## Invocation modes

Detect mode from conversation context:

- **From-discuss mode** — a structured `feature_intake` payload is in context (passed by the `discuss` skill on park or promote). Skip the interview; mechanics only.
- **Standalone mode** — no payload; user invoked directly. Run the intake interview to gather the same data.

The structured payload schema (when from-discuss):

```yaml
feature_intake:
  title: <string>                      # required
  slug: <string>                       # required (kebab-case)
  outcome: <string>                    # required (one line)
  status: ready | parked               # required
  autonomy_level: low | medium | high  # required when status=ready; null when status=parked
  source_links: [<scheme>:<ref>, ...]  # required, at least one
  scope:
    in: <free-form text>
    out: <free-form text>
    non_goals: <free-form text>
  # optional
  target: <ISO date>
  owner: <string>
  area: <string>
  relevant_adrs: [<ADR-ID>, ...]
  tags: [<string>, ...]
  size: S | M | L
```

## Workflow

### Step 1 — Resolve methodology root and load manifest

Walk up from the current working directory to find `.engineer/manifest.yml`. The manifest's `methodology_root` field (default `./`) is the umbrella for `features/` and other DAE artifacts. All paths below are relative to that root.

If no manifest found, the project isn't DAE-onboarded — fail with a message pointing at `/engineer.onboard`.

### Step 2 — Gather intake data

**From-discuss mode:** read the `feature_intake` payload. Validate it has the required fields (title, slug, outcome, status, source_links, scope; plus autonomy_level if status=ready).

**Standalone mode:** run the interview. Required fields one question per turn; optional fields bundled at the end. Use AskUserQuestion when offering bounded choices (status, autonomy_level, size).

Required field interview order:
1. **Title** — free text
2. **Slug** — auto-derived from title (kebab-case, lowercase, ASCII, alphanumeric + hyphens, max 50 chars). User confirms or overrides.
3. **Outcome** — one line: what changes when this ships
4. **Source links** — at least one (issue:#NNN, slack:thread/X, doc:URL, etc.)
5. **Status** — ready or parked (default ready)
6. **Autonomy level** — low / medium / high (only if status=ready; must be in `manifest.autonomy.allowed_levels` and respect any `path_overrides`)
7. **Scope** — In scope / Out of scope / Non-goals (free-form, can be brief)

Optional fields bundled prompt at the end: target, owner, area, relevant_adrs, tags, size.

### Step 3 — Validate

Reject before writing anything if:

- Slug doesn't match format constraints (kebab-case, lowercase, ASCII, alphanumeric + hyphens, starts with letter, max 50 chars)
- `autonomy_level` is not in `manifest.autonomy.allowed_levels`
- `autonomy_level` exceeds a `manifest.autonomy.path_overrides[].max_level` for the relevant path
- `status: ready` without `autonomy_level` set
- `relevant_adrs` reference ADRs that don't exist (in `CHARTER.md` or `docs/adr/`)

**Slug collision handling:**
- If `features/NNN-<slug>/` already exists with `status: parked` → offer to flip to `ready` (the **promote-from-parked path**). Skill becomes a status-flip operation: update feature.md frontmatter (status, autonomy_level if newly required), preserve all existing handoffs, emit a new handoff for the promotion.
- If existing is `ready` or `in-progress` → suggest `/engineer.feature-edit` instead. Reject creating a new one.
- If existing is `done` → reject; suggest a slug variant.

**Decomposition check (inline at intake):**
If the scope spans multiple competencies (frontend + backend + infra), or the user describes work that sounds like multiple PRs, surface: "This looks too big to ship as one feature — split into sub-features?" The user can:
- Proceed as one (acknowledge size)
- Split: end this invocation; user re-invokes feature-init per sub-feature with `parent_feature: <this-slug>` set on each child

### Step 4 — Allocate the next sequence number

Scan `<methodology_root>/features/` for all entries matching `NNN-*`. Take the max NNN, increment by 1. Format 3-digit zero-padded.

**Caveat:** parallel feature-init runs may race. In solo work this is rare; document it as a known limitation. Add a `.engineer/features.lock` mutex only if collisions become real.

### Step 5 — Create the folder and files

```
<methodology_root>/features/NNN-<slug>/
├── feature.md              # populated from intake (the Ready contract)
├── handoffs/               # empty; populated in Step 8
└── .build/                 # empty; gitignored
```

Per the foundation design, `progress.md`, `acs.md`, `spec.md`, `plan.md`, `session-log.md` are **NOT** created at init. They're produced by downstream skills as the pipeline progresses.

Add `.build/` to the project's `.gitignore` if not already present.

### `feature.md` content

YAML frontmatter populated from intake; markdown body with mandatory sections in fixed order.

```markdown
---
slug: <slug>
title: <title>
outcome: <outcome>
autonomy_level: <level | null>
status: <ready | parked>
tracker_ref: <set in Step 7>
source_links:
  - <link>
relevant_adrs: [<adr ids if any>]
parent_feature: <null | parent-slug>
child_features: []
created: <today ISO date>
target: <if provided>
owner: <if provided>
size: <if provided>
tags: [<if provided>]
area: <if provided>
---

# <title>

## Outcome
<outcome — expanded if needed>

## Problem statement
<why now>

## Scope

### In scope
- <items>

### Out of scope
- <items>

### Non-goals
- <items>

## Related code / design pointers
<optional; populated if intake mentioned any>

## Open questions before pipeline starts
<optional>
```

### Step 6 — Open the feature branch

Default: auto-create `git checkout -b <slug>` in the current repo.

Honor charter override: if `CHARTER.md` declares a manual git policy (look for "branch_policy: manual" or equivalent in section 3 / conventions), skip and instead emit a recommendation in the handoff.

For multi-repo projects: branch happens in the *current* repo where invoked; cross-repo branching is the user's responsibility (declare which repos in `plan.md` later).

### Step 7 — Create the tracker entry

Invoke the configured tracker driver (`manifest.tracker.type`). Upsert a `TrackedFeature` with:
- `slug`, `title`, `outcome`, `status`, `current_checkpoint=1.5` (Ready), `autonomy_level`, `target`, `owner`, `area`

Capture the tracker's URL/ID and write it back to `feature.md`'s `tracker_ref` field.

For `local` mode: driver is a no-op; `tracker_ref` set to `local://<slug>`.

### Step 8 — Emit the agentic handoff summary

Per the agentic summary contract (foundation design Section 5). Write to:
`<methodology_root>/features/NNN-<slug>/handoffs/<ISO-timestamp>-feature-init.md`

Format:

```markdown
---
skill: feature-init
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: 1.5
artifacts:
  - features/NNN-<slug>/feature.md
human_action_needed: <yes | no>
human_action_kind: <review | decision | approval | none>
recommended_next: <see below>
tracker_update: <tracker_ref> — feature created, status: <status>
status: complete
---

# feature-init — handoff summary

## What I did
Created feature folder `features/NNN-<slug>/`, populated `feature.md` (status: <status>, autonomy: <level>), opened branch `<slug>`, registered the feature in <tracker> as <tracker_ref>.

## Artifacts produced
- `features/NNN-<slug>/feature.md`

## Human action needed?
<For status=ready, from-discuss promote: "No — feature is Ready; invoke /engineer.acceptance-criteria when ready to start the pipeline.">
<For status=ready, standalone: "Review feature.md to confirm intake captured the intent, then invoke /engineer.acceptance-criteria.">
<For status=parked: "No — feature is parked; resume with /engineer.discuss <slug> when ready to advance.">

## Recommended next step
<Ready: "invoke /engineer.acceptance-criteria for AC discovery (Checkpoint 2)">
<Parked: "no action; will resume on user request via /engineer.discuss <slug>">

## Tracker update
Wrote: <tracker_ref> — feature created, status: <status>, autonomy: <level>, checkpoint: 1.5.
```

## Error handling

If the folder + feature.md write succeed but Step 6 (branch) or Step 7 (tracker) fails:
- Folder + feature.md remain
- Emit the handoff with `status: interrupted`, listing what succeeded and what failed
- User can re-invoke (will detect existing folder via the slug collision logic) or manually complete the missing step

## Validation (consistency-check hooks)

These invariants are enforced by `consistency-check`:
- `feature.md` slug matches the parent folder name
- `autonomy_level` is consistent with manifest and charter rules
- `tracker_ref` resolves on the configured tracker
- `relevant_adrs` reference real ADRs

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema (Section 4), storage layout (Section 1), naming (Section 6)
- [DAE Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — invocation contract from discuss
- [DAE Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — tracker driver interface (Section 1), TrackedFeature contract (Section 2), sync triggers (Section 4)
