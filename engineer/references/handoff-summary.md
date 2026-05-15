# Agentic handoff summary — shared contract

Every DAE skill ends by emitting a **handoff summary** — the signal that tells the human when to re-engage. This file is the canonical format; skills reference it instead of inlining the template.

(Exception: `progress-log` does NOT emit one — it is the skill that *processes* handoffs. Emitting one would loop.)

## Location and naming

`<methodology_root>/features/NNN-<slug>/handoffs/<ISO-timestamp>-<skill>.md`

Timestamp is compact ISO 8601 `YYYY-MM-DDTHHMM` (no seconds) — chronologically sortable.

## Format

YAML frontmatter + markdown body.

```markdown
---
skill: <skill name>
agent_id: <main | subagent-N | team-role | remote-session-id>
started: <ISO timestamp>
ended: <ISO timestamp>
checkpoint: <number | null>          # the pipeline checkpoint addressed; null if off-pipeline
artifacts:                           # paths produced/changed; [] if none
  - features/NNN-<slug>/<file>
findings_summary: <one line>          # optional
human_action_needed: <yes | no>
human_action_kind: <review | decision | approval | none>   # optional
recommended_next: <next checkpoint / skill / "done">
tracker_update: <tracker_ref + what changed | none>         # optional
status: <complete | interrupted>
---

# <skill> — handoff summary

## What I did
1–2 sentences.

## Artifacts produced
File paths, or "None".

## Findings
Key results / surprises. Optional section.

## Human action needed?
Yes/No, and if yes what kind (decision / review / approval).

## Recommended next step
Next checkpoint, next skill, or done.

## Tracker update
What state was written. Optional section.
```

## Required vs optional

- **Required frontmatter:** `skill`, `agent_id`, `started`, `ended`, `artifacts`, `human_action_needed`, `recommended_next`, `status`
- **Optional frontmatter:** `agent_role`, `checkpoint`, `findings_summary`, `human_action_kind`, `tracker_update`
- **Required body:** What I did, Artifacts produced, Human action needed?, Recommended next step
- **Optional body:** Findings, Tracker update

## Rules

- One summary per skill invocation. Sub-tasks don't emit unless themselves dispatched as a skill.
- On crash/interruption, emit a partial summary with `status: interrupted` capturing what was done.
- `agent_id` enforces verification independence (Principle 7): a verification handoff's `agent_id` must differ from the implementer's for the same feature.
- Writing the summary triggers `progress-log`, which propagates it to `progress.md` and the tracker.

Full schema: [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207), Section 5.
