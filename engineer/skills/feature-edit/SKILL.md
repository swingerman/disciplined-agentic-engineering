---
name: feature-edit
description: Use when an in-flight feature needs to change — scope shifts, an AC gets refined, the plan evolves, a behavior is added or removed. Triggers include "/engineer.feature-edit", "change feature X to...", "the ACs need updating", "revise the plan for...", "scope changed — update the feature", or any intent describing what should now be true about an existing feature. Takes a natural-language intent, identifies the affected feature and artifact(s), proposes an edit plan (including downstream cascade), and on confirmation performs the edits and re-syncs progress.md + the tracker. Mixed mode: the agent proposes the edit plan, the human confirms before any write.
---

# feature-edit

Intent-driven editing of an in-flight feature. Features are not write-once — plans evolve, ACs get refined, scope shifts. The human describes *what should now be true*; `feature-edit` figures out *which files and tools need touching* and orchestrates the change, including the downstream cascade.

This is the cascade-owning skill. Other skills (`clarify`, `simplify`) deliberately stay single-artifact and route multi-artifact propagation here.

## When this skill runs

Any time an existing feature needs to change. Not a checkpoint (`checkpoint: null`) — it's a lifecycle operation that can touch any pipeline stage's artifact.

## Workflow

### Step 1 — Resolve methodology root and identify the feature

Walk up to `.engineer/manifest.yml`; resolve `methodology_root`. Identify the affected feature:
- Explicit slug in the invocation → use it
- Else infer from the current branch name
- Else search `features/*/feature.md` titles and outcomes against the intent; if ambiguous, ask the user to pick

### Step 2 — Detect "is this actually an edit?"

Before planning edits, sanity-check the intent's size:
- If the intent is a **new capability** (not a refinement of the existing feature's outcome) → surface it: "This isn't an edit to `<slug>` — it's a new capability. Run `/engineer.discuss` to explore it as its own feature." Stop.
- If the intent is **too big for one feature** (would balloon scope across competencies) → surface decomposition: "This would significantly expand `<slug>` — consider splitting. Run `/engineer.discuss`." Stop.
- Otherwise → proceed; it's a genuine edit.

### Step 3 — Classify which artifact(s) the intent touches

Determine the **entry artifact** — the highest-level artifact the intent directly changes:
- Outcome / scope / problem / autonomy → `feature.md`
- A behavior added / changed / removed → `acs.md`
- A Given/When/Then formalization detail → `spec.md`
- Architecture / phasing / execution mode → `plan.md`

### Step 4 — Build the edit plan (cascade, downstream only)

From the entry artifact, the cascade flows **strictly downstream**:

```
feature.md  →  acs.md  →  spec.md  →  plan.md
```

Editing an artifact may invalidate the ones derived from it — never the ones above it. (If editing `spec.md` reveals an AC is wrong, that is *surfaced for the human*, not auto-propagated upward.)

For each artifact in the cascade, classify the downstream change by blast radius:
- **Small / mechanical** (one AC reworded, one spec scenario value, one plan phase note) → `feature-edit` edits it directly
- **Substantial** (scope shift needs new/removed ACs; new ACs need full re-formalization; architecture rethink) → `feature-edit` invokes the owning skill in edit-pass mode: `discover-acs`, `atdd:atdd`, or `plan`

Assemble this into an **edit plan**:

```
Edit plan for "<intent>" on feature <slug>:
  Entry artifact: acs.md — AC-3 changes (email validator now allows + signs)
  Direct edit:    acs.md AC-3 — small, feature-edit edits directly
  Cascade:
    - spec.md      — scenario 3 stale (uses the old validation example)
                     → substantial: re-invoke /atdd:atdd in edit-pass mode
    - plan.md      — test strategy references AC-3
                     → small: feature-edit edits directly
  Sync:           progress.md + tracker updated after edits
```

### Step 5 — Present the edit plan; human confirms

Show the full edit plan. The human confirms the *whole plan* before any write. They can:
- Approve → execute
- Adjust (e.g. "don't touch plan.md, I'll handle it") → revise plan
- Reject → stop

No artifact is written before confirmation.

### Step 6 — Execute

In cascade order (upstream artifact first, so each downstream step sees current inputs):
1. Apply the direct edit to the entry artifact
2. For each downstream artifact: edit directly (small) or invoke the owning skill in edit-pass mode (substantial)
3. After spec.md changes, regenerate `.build/spec.json` (the IR must stay current — see Foundation Section 7)
4. Re-run affected test streams if code-bearing artifacts changed and code already exists

If any downstream regeneration surfaces an upstream problem (e.g. re-formalizing reveals AC-3 itself is incoherent), **stop and surface it** — don't auto-edit upward.

### Step 7 — Sync progress.md and the tracker

- Update `progress.md` — the affected checkpoints' rows (an edited artifact may reset a checkpoint's "done" state if its downstream is now stale-and-regenerating)
- Update the tracker via the driver (per the agentic summary contract's `tracker_update`)

### Step 8 — Emit the handoff summary

```markdown
---
skill: feature-edit
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: null
artifacts:
  - <every artifact edited>
findings_summary: <one line — e.g. "intent applied; acs.md + spec.md + plan.md updated">
human_action_needed: <yes if anything was surfaced for the human, else no>
human_action_kind: <decision | review | none>
recommended_next: <see below>
tracker_update: <tracker_ref> — artifacts updated
status: complete
---

# feature-edit — handoff summary

## What I did
Applied the intent "<intent>" to feature `<slug>`. Entry artifact: `<artifact>`. Cascade: <list downstream artifacts touched and how — direct edit vs owning-skill re-invocation>.

## Artifacts produced
- <every artifact edited, with a one-line note on what changed>

## Findings
<anything surfaced for the human — an upstream problem revealed by regeneration, a charter implication, a test that now fails>

## Human action needed?
<If something surfaced: "Yes — <description>; needs your decision.">
<Else: "No — intent applied, downstream cascade complete, progress + tracker synced.">

## Recommended next step
<e.g. "re-run /engineer.consistency-check to confirm the artifacts are back in sync" — or the next pipeline checkpoint if the edit reset one>

## Tracker update
Wrote: <tracker_ref> — <which checkpoints' state changed>.
```

## Key principles encoded

- **The human describes intent; the skill handles bookkeeping.** The user says what should be true — feature-edit determines which files and tools to touch.
- **The cascade is downstream-only.** feature.md → acs.md → spec.md → plan.md. Upstream problems are surfaced, never auto-propagated.
- **Big regenerations route to the owning skill.** feature-edit edits small things directly but invokes `discover-acs` / `atdd:atdd` / `plan` for substantial downstream rework — it does not reimplement them.
- **Nothing is written before the edit plan is confirmed.** The human approves the whole plan, cascade included.
- **An edit is not a new feature.** If the intent is really a new capability or a decomposition, feature-edit redirects to `discuss` rather than force-fitting.

## When NOT to use this skill

- The intent is a brand-new capability → `/engineer.discuss`
- You only need to resolve vagueness in one artifact (no behavior change) → `/engineer.clarify`
- You want to validate consistency, not change anything → `/engineer.consistency-check`
- You want to clean up code (not change behavior) → `/engineer.simplify`

## Cross-skill orchestration

feature-edit is the cascade orchestrator. It performs small edits directly and invokes owning skills for substantial downstream rework.

- Upstream: any artifact-producing skill / the human's intent
- This skill: identifies entry artifact, builds + executes the edit plan downstream, syncs progress + tracker
- Invokes as needed: `discover-acs`, `atdd:atdd`, `plan` (edit-pass mode)
- Downstream: `consistency-check` recommended afterward to confirm artifacts are back in sync

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — artifact schemas, the IR pipeline (Section 7), agentic summary contract
- [DAE Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — when an "edit" is really a new feature
- [DAE Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — tracker sync on artifact change
