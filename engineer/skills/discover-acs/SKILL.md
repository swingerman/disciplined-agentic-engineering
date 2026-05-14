---
name: discover-acs
description: Use when the user has a Ready feature (status=ready, feature.md exists) and needs to discover the acceptance criteria before atdd:atdd formalizes them as Given/When/Then specs. Triggers include "/engineer.discover-acs", "/engineer.acceptance-criteria", "let's discover ACs for this feature", "what acceptance criteria do we need", "let's figure out what must work for this feature", or any natural request to enumerate behaviors a feature must satisfy. Runs an interactive interview in iterative passes (happy path → edge cases → errors/security → cross-cutting), produces acs.md (Checkpoint 2 artifact), enforces domain language (no implementation leakage), and surfaces scope drift against feature.md outcome. Hands off to atdd:atdd for Given/When/Then formalization.
---

# discover-acs

Discover the acceptance criteria for a Ready feature. ACs are **decisions about what behaviors must work**, expressed in **domain language** — they precede the Given/When/Then formalization that `atdd:atdd` produces. This is Checkpoint 2 of the DAE pipeline.

The methodology's strongest claim about this skill: **separating AC discovery (divergent decisions) from spec formalization (convergent encoding) is what protects domain language from leaking into implementation language.** Skipping this step is what produces "AI that plops code around."

## When this skill runs

The feature must be **Ready** — `feature.md` exists with `status: ready` and `autonomy_level` set. If feature is `parked`, redirect user to `/engineer.discuss <slug>` (promote first). If feature folder doesn't exist, redirect to `/engineer.discuss` or `/engineer.feature-init`.

Two invocation contexts:
- **After `prime-context`** — context is loaded; skill jumps into AC interview
- **Standalone (without prime-context)** — skill loads minimal context itself (feature.md + charter)

## Workflow

### Step 1 — Resolve methodology root and validate

Walk up to find `.engineer/manifest.yml`. Resolve `methodology_root`. Find the target feature:
- If user invoked with a slug: `/engineer.discover-acs <slug>` → load `features/NNN-<slug>/feature.md`
- If no slug: look for `feature.md` in the current branch's matching folder; if ambiguous, ask user to specify

Reject if:
- Feature not found
- `status` is not `ready`
- `acs.md` already exists with content (suggest `/engineer.feature-edit` or pick a different feature)

### Step 2 — Load context

Load:
- `features/NNN-<slug>/feature.md` (the Ready contract: outcome, problem, scope, autonomy_level, source_links, relevant_adrs)
- `CHARTER.md` (architecture rules, conventions, scope context, ADRs)
- `manifest.yml` (autonomy rules, path overrides)
- Any prior handoffs in `features/NNN-<slug>/handoffs/` (especially the discuss handoff if feature came through the funnel)

### Step 3 — Open the interview

Brief context echo to ground the user:
> "Discovering ACs for `<title>`. Outcome: `<outcome>`. Scope: in: <in>, out: <out>.
>
> We'll go in passes: happy path → edge cases → errors/security → cross-cutting. Sound good? Or want to start somewhere else?"

User can override the order if needed; default is the four passes below.

### Step 4 — Pass 1: Happy path

> "What's the most important behavior — the core thing this feature must do for the user to consider it shipped?"

Capture as AC-1. Then:
> "What else must work for the happy path? Walk me through the user's main journey — every behavior the system must satisfy when everything's going right."

One question per turn (don't batch-prompt). Capture each behavior as the next AC.

When the user signals "that's the happy path," move to Pass 2.

### Step 5 — Pass 2: Edge cases

Coverage prompts (use as needed; don't ask all):
- "What about empty input — empty list, empty string, empty selection?"
- "What about extreme values — very large, very small, very many?"
- "What about boundaries — at the limit, just above, just below?"
- "What about concurrency — same user two clicks; two users same resource?"
- "What about partial state — half-completed, interrupted, resumed?"

When the user signals coverage, move to Pass 3.

### Step 6 — Pass 3: Errors and security

Coverage prompts:
- "What about missing input — required fields not provided?"
- "What about malformed input — wrong type, wrong format?"
- "What about authorization — user without permission, missing auth, expired auth?"
- "What about external failures — dependent service down, timeout, partial data?"
- "What about rate limits, abuse, hostile input?"

When covered, move to Pass 4.

### Step 7 — Pass 4: Cross-cutting

Coverage prompts:
- "What about audit / logging — what must be recorded?"
- "What about observability — what must be measurable?"
- "What about idempotency — can this be retried safely?"
- "What about data lifecycle — retention, deletion, GDPR?"
- "Anything performance-shaped — response time, throughput targets?"

### Step 8 — Coverage check before ending

Before writing `acs.md`, surface coverage:
> "ACs captured: <count>. Coverage: ✅ happy path, ✅ edge cases, ✅ errors, ✅ cross-cutting.
> High-priority: <high-priority count>. Low: <low-priority count>.
> Anything we missed? Want to add anything before I write `acs.md`?"

If user adds, capture and re-check. If user confirms done, write the file (Step 9).

If a coverage area is *not* checked (e.g., user skipped errors entirely), prompt one more time:
> "We didn't talk about errors / security. Worth a pass before we lock this in?"
Honor whatever user says.

### Step 9 — Write `acs.md`

YAML frontmatter + numbered AC sections in fixed order.

```markdown
---
slug: <slug>
ac_count: <total>
high_priority_count: <count>
edge_case_count: <count>
discovered: <today ISO date>
---

# Acceptance Criteria — <feature title>

## AC-1: <one-line behavior name>
**Priority:** high | medium | low
**Type:** happy-path | edge-case | error | security | cross-cutting

<one or two paragraphs in DOMAIN LANGUAGE describing the behavior — what the system must do, what the user observes, what's required to consider this AC satisfied. No implementation details.>

## AC-2: <name>
...
```

Write to `<methodology_root>/features/NNN-<slug>/acs.md`.

### Step 10 — Domain language enforcement

Throughout the interview (not just at end), watch for implementation leakage. Common signals:
- Mentions of API endpoints, HTTP status codes, JSON shape, database tables/columns
- Specific frameworks, libraries, classes, functions
- Specific encoding/protocol details
- "The endpoint", "the controller", "the model", "the route"

When detected, **soft warning + rephrase**:
> "That's an implementation detail (e.g., `returns 401`). Let me reframe as the user-observable behavior: `unauthenticated requests are rejected and the user is told to sign in`. OK to capture this way?"

Don't block. Don't refuse. Educate by rephrasing. User confirms or pushes back. The goal is teaching the methodology one AC at a time.

### Step 11 — Scope drift handling

If during the interview a behavior surfaces that's outside `feature.md`'s `outcome` and `scope`:

> "This sounds outside the feature's outcome ('<outcome>'). Three options:
> - **(a) Update feature.md** to broaden scope — I'll edit it before we capture this AC
> - **(b) Out of scope here** — drop this AC; capture as a known follow-up in feature.md's 'Open questions' section
> - **(c) Park as separate discussion** — invoke /engineer.discuss after we finish here
>
> Which?"

Honor whatever the user picks. Don't auto-execute.

### Step 12 — Emit the agentic handoff summary

Per the agentic summary contract.

```markdown
---
skill: discover-acs
agent_id: <main | subagent-N | team-role>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: 2
artifacts:
  - features/NNN-<slug>/acs.md
findings_summary: <ac_count> ACs discovered, <high_priority_count> high-priority
human_action_needed: yes
human_action_kind: review
recommended_next: "Checkpoint 3 — invoke /atdd.atdd to formalize ACs as Given/When/Then specs"
tracker_update: <tracker_ref> — checkpoint_2: complete
status: complete
---

# discover-acs — handoff summary

## What I did
Ran AC discovery interview for `<title>` across <number> passes (happy path, edge cases, errors/security, cross-cutting). Captured <ac_count> acceptance criteria, <high_priority_count> high-priority.

## Artifacts produced
- `features/NNN-<slug>/acs.md` (<ac_count> ACs)

## Findings
<one or two notable discoveries: e.g., "AC-5 surfaced async generation needs that weren't in the original feature.md scope — feature.md scope was broadened with user agreement", or "AC-7 couples to existing rate-limit middleware — see src/middleware/rate_limit.rs">

## Human action needed?
Yes — review acs.md before I (or you) invoke /atdd.atdd. Specifically: confirm priorities, check the high-priority ACs match the feature's risk profile, look for missed cases.

## Recommended next step
Once ACs approved → invoke /atdd.atdd to formalize as Given/When/Then specs (Checkpoint 3).

## Tracker update
Wrote: <tracker_ref> — checkpoint_2 marked complete.
```

## Multi-stage AC discovery

If the user wants to revisit / refine ACs after a session:
- Re-invoke `/engineer.discover-acs <slug>`
- Skill loads existing `acs.md`, opens with: "Existing acs.md has <count> ACs. Reviewing or extending?"
- Treat as edit pass (insert / modify / remove ACs); preserve existing AC IDs (numbering monotonic per file)
- Each session emits a new handoff entry — chronologically sortable

For substantial restructuring, redirect to `/engineer.feature-edit`.

## Validation (consistency-check hooks)

These invariants are enforced by `consistency-check`:
- `acs.md` slug matches the parent folder name
- AC IDs are unique and sequential within the file
- All ACs are in domain language (heuristic check for implementation-language patterns)
- AC count in frontmatter matches actual count
- ACs collectively cover the feature.md outcome (no AC = unsatisfiable; many ACs but no scope coverage = mismatch)

## When NOT to use this skill

- Feature isn't Ready yet → use `/engineer.discuss` or `/engineer.feature-init` first
- Feature already has `acs.md` and you want a small change → use `/engineer.feature-edit`
- You want Given/When/Then specs (not bare ACs) → use `/atdd.atdd` after this skill
- You're brainstorming whether the feature itself is worth doing → use `/engineer.discuss`

## Cross-skill orchestration

Upstream:
- `feature-init` produced `feature.md`
- (Optional) `prime-context` loaded repo context

This skill:
- Reads `feature.md`, charter, prior handoffs
- Produces `acs.md`

Downstream:
- `atdd:atdd` consumes `acs.md` to produce `spec.md` (Given/When/Then)
- `clarify` may be invoked here for ambiguity (TBD when clarify ships)
- `consistency-check` validates structure later

## References

Foundation contracts (Notion):
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema, agentic summary contract
- [DAE Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — methodology_root resolution

Methodology background (Notion):
- The DAE methodology page covers why ACs and specs are separate (the divergent → convergent split)
