---
name: prime-context
description: Use when about to start pipeline work on a Ready feature and the agent needs to load working memory first — the feature.md contract, the charter, prior handoffs, and the code the feature touches. Triggers include "/engineer.prime-context", "prime context for this feature", "load context before we start", "get up to speed on feature X", or naturally before invoking discover-acs on a feature the agent hasn't worked yet. Forked from superpowers:brainstorming in convergent mode — it loads and orients, it does not explore. Produces no artifact; emits a handoff summary noting what was loaded.
---

# prime-context

Load working memory before pipeline work on a Ready feature. This is the convergent counterpart to `discuss` — where `discuss` explores divergently to decide *whether* a feature is real, `prime-context` converges on an existing Ready feature to get the agent deeply oriented before AC discovery, spec writing, or planning begins.

It is forked from `superpowers:brainstorming` but inverts the mode: **no exploration, no proposing — just loading and orienting.**

## When this skill runs

Between `feature-init` (Checkpoint 1.5) and `discover-acs` (Checkpoint 2), on any feature the agent has not already worked in the current session. It's a *prep step*, not a checkpoint — it produces no durable artifact and gates no human decision.

Skip it when context is already loaded (the agent just ran `discuss` → `feature-init` on this feature in the same session — the context is already warm).

## Workflow

### Step 1 — Resolve methodology root and locate the feature

Walk up to find `.engineer/manifest.yml`. Resolve `methodology_root`. Locate the target feature:
- If invoked with a slug: `/engineer.prime-context <slug>` → `features/NNN-<slug>/`
- If no slug: infer from the current branch name (branch == slug per naming conventions); if ambiguous, ask

Reject if the feature folder doesn't exist or `feature.md` is missing.

### Step 2 — Silent batch load (the standard surface)

Load all of the following into working memory without narrating each step:

1. **`feature.md`** — the Ready contract: outcome, problem, scope (in/out/non-goals), autonomy_level, source_links, relevant_adrs, related code pointers
2. **`CHARTER.md`** — architecture, conventions, scope, quality stance, autonomy stance, ADRs
3. **`manifest.yml`** — autonomy rules, path overrides, tracker config, quality thresholds
4. **Prior handoffs** in `features/NNN-<slug>/handoffs/` — especially the originating `*-discuss.md` if the feature came through the funnel (it carries the brainstorm reasoning, alternatives considered, scope decisions)
5. **Related code** — read the files/directories listed in `feature.md`'s "Related code / design pointers" section. These are the parts of the codebase the feature will touch or couple to.

### Step 3 — Orient and summarize

Produce a concise orientation summary for the user:

> **Primed on `<title>`.**
> - **Outcome:** <outcome>
> - **Scope:** in: <in>; out: <out>
> - **Autonomy:** <level> <(charter cap note if any)>
> - **Prior decisions:** <key points from the discuss handoff — alternatives considered, scope calls made>
> - **Related code:** <one line per pointer — what's there, how it likely couples>
> - **Relevant ADRs:** <ADR-N: title — one line on the constraint it imposes>
>
> Anything else I should pull in before we start AC discovery?

### Step 4 — One prompt for extra context

After the orientation summary, ask exactly one question (Step 3's closing line): does the user want anything else loaded?

- If the user names additional files / docs / issues → load them.
- If the user surfaces a *new* code pointer not in `feature.md` → load it AND offer to add it to `feature.md`'s "Related code / design pointers" section (small, useful refinement; user confirms).
- If the user says "nothing else" / "go" → proceed to Step 5.

Do not ask more than this one question. prime-context orients; it does not interview.

### Step 5 — Emit the handoff summary

Per the agentic summary contract. prime-context produces **no artifact** — the handoff is the only record.

```markdown
---
skill: prime-context
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: null
artifacts: []
findings_summary: <one line — e.g. "primed on customer-export; 3 code pointers loaded, 1 ADR constraint noted">
human_action_needed: no
human_action_kind: none
recommended_next: "Checkpoint 2 — invoke /engineer.discover-acs to discover acceptance criteria"
tracker_update: none
status: complete
---

# prime-context — handoff summary

## What I did
Loaded working memory for `<title>`: feature.md, charter, manifest, <N> prior handoffs, <M> related-code pointers<, plus extra context the user requested>.

## Artifacts produced
None — prime-context loads context; it does not write artifacts. (If a new code pointer was added to feature.md at the user's request, note it here.)

## Findings
<key orientation points: prior decisions from the discuss handoff, ADR constraints, how the feature couples to existing code, anything surprising>

## Human action needed?
No — context is loaded. Ready for AC discovery.

## Recommended next step
Invoke /engineer.discover-acs to discover acceptance criteria (Checkpoint 2).
```

## Re-invocation

Re-invoking prime-context on the same feature re-loads everything fresh (no incremental diffing, no skip). Re-priming is rare; making it simple and correct beats cleverness.

## When NOT to use this skill

- Feature isn't Ready (`status: parked` / no folder) → use `/engineer.discuss` or `/engineer.feature-init`
- The agent just created the feature this session and context is already warm → skip; go straight to `discover-acs`
- You want to *explore whether* a feature is worth doing → that's `discuss` (divergent), not prime-context (convergent)

## Cross-skill orchestration

Upstream: `feature-init` produced `feature.md`; optionally `discuss` left a handoff.
This skill: reads feature.md + charter + manifest + handoffs + related code; loads working memory.
Downstream: `discover-acs` runs with a fully-oriented agent.

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema, agentic summary contract
- [DAE Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — methodology_root resolution, discuss handoff format
