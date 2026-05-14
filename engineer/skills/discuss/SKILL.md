---
name: discuss
description: Use when the user wants to brainstorm a new feature idea or revisit a parked one before committing. Triggers include "/engineer.discuss", "/engineer.discuss <slug>", "let's discuss X", "I have an idea about Y", "I'm thinking about Z", "should we build...", or any exploratory thinking-out-loud about possible work. Runs an interactive divergent brainstorm (forked from superpowers:brainstorming) and ends in one of three outcomes: drop (one line in discussions.log), park (invoke feature-init with status=parked), or promote (invoke feature-init with status=ready). Argument continues a parked discussion; bare invocation starts fresh with soft-match for likely continuations.
---

# discuss

The upstream funnel of the DAE methodology. Most ideas die here; some park on the roadmap as `features/NNN-slug/` with `status: parked`; the survivors promote to `status: ready` and feed the pipeline.

This skill is a fork of `superpowers:brainstorming` adapted for divergent feature exploration with three terminal outcomes.

## Invocation modes

- **Fresh:** `/engineer.discuss` (no argument). Starts a new exploratory conversation. After the first prompt, soft-match against parked features for a possible continuation hint.
- **Continue (explicit):** `/engineer.discuss <slug>`. Loads `features/NNN-<slug>/feature.md` and prior `handoffs/*-discuss.md` entries. Resumes the brainstorm with full memory of prior sessions.
- **From a tool/skill that wants to discuss something:** another skill or the user invokes discuss with structured intent in context. Detect and honor.

## Workflow

### Step 1 — Resolve methodology root and load context

Walk up to find `.engineer/manifest.yml`. If no manifest, the project isn't DAE-onboarded — fail with a pointer to `/engineer.onboard`.

Load:
- `CHARTER.md` (for autonomy stance, scope rules, mutation policy, path overrides)
- `manifest.yml` (for autonomy.allowed_levels, autonomy.path_overrides, tracker config)
- Last 20 entries from `<methodology_root>/.engineer/discussions.log` (for "you considered X recently" signals)

If invoked with a slug argument:
- Load `features/NNN-<slug>/feature.md`
- Load all prior `features/NNN-<slug>/handoffs/*-discuss.md` entries (chronological)
- Verify the feature is in `parked` status — if `ready` or `in-progress`, redirect user to `/engineer.feature-edit`; if `done`, hard-reject with a slug-variant suggestion

### Step 2 — Open the conversation

**Fresh mode:**
> "What are you thinking about?"

After the user's first prompt, **soft-match**: scan parked feature titles, outcomes, and `area` tags for a likely match against the user's topic. If a likely match exists (high token overlap or area match), surface ONE prompt:
> "Did you mean to continue `042-customer-export`? It was last discussed N days ago. Or start fresh?"

If user picks the existing parked feature, transition to continue mode (load its files, resume).
If user starts fresh, suppress the prompt for the rest of the session.

**Continue mode (explicit slug or after soft-match):** open with a brief context echo so the user knows the agent loaded prior state:
> "Continuing `042-customer-export` (parked since 2026-05-04). Last session: [one-line summary from prior handoff]. What's new?"

Also surface relevant entries from the recent `discussions.log` if the topic resembles a recent drop:
> "You considered `csv-export-on-mobile` 4 days ago and dropped it because of redundancy with the dashboard export — does that affect this?"

### Step 3 — Brainstorm (divergent mode)

Run the conversation in **divergent** mode — explore intent, scope, alternatives. Unlike convergent skills (`prime-context`, `acceptance-criteria`), don't push for closure. The goal is helping the user think out loud and decide whether this is a real feature.

Patterns inherited from `superpowers:brainstorming`:
- Ask one question at a time
- Multiple choice questions when bounded; open-ended otherwise
- Propose 2–3 framings/angles when the user is stuck
- Surface tradeoffs (scope vs effort, in-scope vs out, dependencies)

Patterns specific to discuss:
- Watch for charter signals (e.g., topic touches `/payments/` → autonomy capped at low; surface this when scope clarifies)
- Watch for ADR connections (existing ADRs might constrain or support; surface them as references)
- Watch for "this is too big" signals — flag potential decomposition early

### Step 4 — Detect outcome inflection and suggest outcome

When the conversation reaches a natural inflection — clear scope + intent + decision pressure — the agent surfaces an outcome recommendation:

- **Promote signal:** scope is bounded, ACs feel clear in the user's head, user is energized and unblocked
  > "This sounds ready to promote — want to start the pipeline now?"
- **Park signal:** scope is real but user is busy / not ready / dependencies unresolved
  > "This feels real but not now — want to park it for later?"
- **Drop signal:** user expresses doubt, or the idea collides with prior decisions, or scope balloons unmanageably
  > "Sounds like this isn't worth pursuing right now — drop it?"

User confirms or pushes back. Never auto-execute the outcome; always wait for confirmation.

**Park-vs-drop nudge:** if user says "drop" but the agent has a *concrete* reason to think it's worth parking (e.g., "this connects to ADR-007 you mentioned earlier" or "two prior dropped discussions hint at recurring need"), ask once:
> "Worth parking instead? [reason]"
Honor whatever user decides. Never push a second time.

### Step 5 — Execute the chosen outcome

#### Drop path

Append one line to `<methodology_root>/.engineer/discussions.log`:

```
<ISO-timestamp> | <suggested-slug> | dropped | <one-line why>
```

Process:
1. Derive the suggested slug from the conversation (kebab-case, lowercase, ASCII, max 50). User confirms or overrides.
2. Draft the "why dropped" line from the conversation context (one sentence, reason-focused).
3. Show user the line: "Logging this — edit if needed: `<line>`"
4. User confirms or edits, then write to log.

The slug is **not reserved** — a future feature may use it.

Skip to Step 6.

#### Park path

Invoke `feature-init` with a structured `feature_intake` payload (status: parked):

```yaml
feature_intake:
  title: <title>
  slug: <slug>
  outcome: <one-line outcome>
  status: parked
  autonomy_level: null              # not decided at park; will be set on promotion
  source_links: [<links from discussion>]
  scope:
    in: <captured from discussion>
    out: <captured from discussion>
    non_goals: <captured from discussion>
  # optional fields populated if discussed
  target: <if mentioned>
  area: <if mentioned>
  relevant_adrs: [<if any surfaced>]
  tags: [<if any>]
```

`feature-init` handles folder creation, branch (or skip for parked — defer to promotion), tracker entry (status=parked), and emits its own handoff.

Discuss then emits its own handoff (Step 6) referencing the resulting feature.

#### Promote path

Same as park, but **first** resolve the autonomy decision:

> "Promoting now requires picking autonomy level: **low** / **medium** / **high**.
> - low: human reviews every commit; per-AC validation; no mutation
> - medium (default): human approves at plan + verify checkpoints; mutation optional
> - high: human pre-declares constraints; mandatory mutation; verifier role required
>
> [If charter has path override: "This feature touches `<path>` so charter caps at <level>."]
>
> Pick?"

If user can't decide → fall back to **park instead** (defer the autonomy question to a future promotion). Never default-pick autonomy on promote.

Once decided, invoke `feature-init` with `status: ready` and `autonomy_level: <picked>`.

### Step 6 — Emit the agentic handoff summary

Per the agentic summary contract (foundation design Section 5).

**For drop:** write to `<methodology_root>/.engineer/handoffs-orphan/<ISO-timestamp>-discuss.md` (no feature folder exists; orphan handoffs live at the methodology root).

Wait — re-think. The agentic summary contract assumes summaries live in `features/NNN-slug/handoffs/`. For drop, no folder exists. Options:
- a) Put orphan handoffs in `.engineer/handoffs-orphan/`
- b) Skip the handoff for drop (the log line IS the artifact)
- c) Put it in a special "discussions" folder

For now: **skip the handoff for drop**. The discussions.log line is the audit artifact; a handoff summary would be redundant. (If this needs revisiting, surface it.)

**For park / promote:** the handoff lives in the new feature folder, written by feature-init. Discuss does NOT write its own handoff in this case — feature-init's handoff captures the creation event. Discuss's contribution to the brainstorm is preserved as a separate `<ISO-timestamp>-discuss.md` handoff inside the new folder, written by discuss before exiting:

```markdown
---
skill: discuss
agent_id: <main | subagent-N | team-role>
started: <ISO-timestamp>
ended: <ISO-timestamp>
checkpoint: null
artifacts:
  - features/NNN-<slug>/feature.md   # created by feature-init invocation
findings_summary: <one-line summary of what was decided>
human_action_needed: <yes if promote and review wanted; no if park>
human_action_kind: <review | none>
recommended_next: <see below>
tracker_update: <set by feature-init's invocation>
status: complete
---

# discuss — handoff summary

## What I did
Brainstormed `<topic>`. Outcome: <park | promote>. <one-paragraph summary of the conversation: scope clarified, alternatives considered, key tradeoffs surfaced.>

## Artifacts produced
- `features/NNN-<slug>/feature.md` (via feature-init)

## Findings
<key insights from the brainstorm — alternatives considered, ADRs touched, decompositions flagged, etc.>

## Human action needed?
<For promote: "Optional — review feature.md to confirm intake matches discussion intent, then invoke /engineer.acceptance-criteria.">
<For park: "No — feature is parked; resume with /engineer.discuss <slug> when ready to advance.">

## Recommended next step
<Promote: "invoke /engineer.acceptance-criteria for AC discovery">
<Park: "no action; feature is shelved">
```

For multi-stage discussions on a continued slug: each session emits its own discuss handoff in the same folder — they're chronologically sortable by timestamp and `feature-init` is NOT invoked again (the folder already exists). Just append the handoff and update `feature.md` if scope/outcome was refined.

## Multi-stage discussion notes

When continuing an existing parked feature:
- The previous handoffs in `features/NNN-<slug>/handoffs/` are loaded as context (they capture prior thinking)
- `feature.md` is updated incrementally if scope/outcome refines (skill writes the changes; doesn't ask user to re-state from scratch)
- Each session writes a new handoff entry — no rolling artifact
- If the user decides to promote in this continued session, autonomy gets resolved here (Step 5 promote path), and `feature.md` flips to `status: ready` (no separate feature-init invocation needed for the existing folder; just edit + emit handoffs)

## Validation

Reject before any write if:
- Slug doesn't match format constraints (kebab-case, lowercase, ASCII, max 50)
- Continuing a feature with `status: ready/in-progress/done` (redirect to `feature-edit`)
- Promote path attempted without autonomy_level set

## Cross-skill invocation summary

```
discuss
  ├─ drop    → write discussions.log line; no feature-init
  ├─ park    → invoke feature-init { status: parked, autonomy_level: null, ... }
  └─ promote → invoke feature-init { status: ready, autonomy_level: <picked>, ... }
```

For continued (already-parked) features:
```
discuss <slug>
  ├─ drop    → append discussions.log line about why this parked feature is being abandoned (also flip feature.md status to dropped? — see open question below)
  ├─ park    → just append a new discuss handoff; feature.md remains parked, refine fields if scope shifted
  └─ promote → flip feature.md to status=ready, set autonomy_level, append handoff (feature-init NOT re-invoked; folder exists)
```

**Open question to revisit:** dropping an already-parked feature — should the feature.md folder be removed, or status flipped to a new `dropped` enum? Foundation said `status` enum is `ready | in-progress | done | parked`. Adding `dropped` is a foundation change. For now: keep folder, append a new handoff explaining the drop, leave status as `parked`. User can manually delete the folder if desired.

## References

Foundation contracts (Notion):
- [DAE Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — funnel structure, drop log format, park/promote paths, methodology_root resolution
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema, agentic summary contract, autonomy levels
- [DAE Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13) — tracker upsert via driver

Sister skills:
- `feature-init` (sibling) — invoked by discuss for park/promote; handles folder/file/branch/tracker mechanics
- `prime-context` (downstream) — runs on a Ready feature to load context for AC discovery
- `acceptance-criteria` (downstream) — runs after prime-context to discover ACs
