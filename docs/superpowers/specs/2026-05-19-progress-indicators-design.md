# DAE Progress Indicators — Design

**Date:** 2026-05-19
**Status:** Draft for review
**Scope:** Surface "where am I" passively while a skill runs — both the pipeline
checkpoint and the step within the current skill — across the `engineer` and
`atdd` plugins.

---

## Background

DAE *records* position well — `progress.md`'s CURRENT header, the Checkpoints
table, the handoff summaries. But it only *surfaces* position on demand: you
open a file, or you invoke `reorient`. While a skill runs, neither "which
checkpoint of the pipeline" nor "which step of this skill" is visible. You
reconstruct it by asking.

This is the gap users hit: the skills work, but it is easy to lose track of
where you are. The fix is two passive indicators that show up *as you work*,
both derived from state that already exists — no new persistent state, no agent
guesswork.

A persistent terminal statusline was considered and **declined**: it needs a
per-machine `settings.json` edit. Both indicators here are in-conversation only,
zero setup.

## The two structural shapes

The two plugins have different pipeline shapes, and the design respects that.

- **The engineer pipeline spans many separate skill invocations** — each
  checkpoint is its own skill (`onboard`, `feature-init`, `discover-acs`,
  `atdd`, `plan`, `refine`, `arch-check`). Position must survive *across*
  invocations, so it lives in `progress.md` and needs a script to render it.
- **The atdd pipeline is one invocation with many internal steps** — each atdd
  skill (`atdd`, `atdd-mutate`, `atdd-team`) runs its whole workflow in a single
  invocation. Position lives *within* the conversation; it does not need to
  survive across invocations and there is no `progress.md` to read.

So the engineer plugin gets both indicators; the atdd plugin gets the in-skill
one only, and for it that single indicator carries both layers.

---

## Indicator 1 — The pipeline breadcrumb (engineer plugin)

Answers "which checkpoint of the pipeline am I on."

### Component — `dae_progress.py`

A new stdlib-only Python script in `engineer/scripts/`, with a
`test_dae_progress.py` sibling — matching the established
`dae_handoff` / `dae_arch` / `dae_impact` pattern (stdlib only, `test_*.py`
sibling, run via `python3 -m unittest discover -p 'test_*.py'`).

It reads a feature's `progress.md` — the Checkpoints table and the CURRENT
header — and prints a compact breadcrumb against the canonical pipeline:

```
DAE ▸ 015-image-formats
✓0 Onboard · ✓1.5 Ready · ✓2 ACs · ▶3 Spec · ·4 Plan · ·5 Implement · ·6 Refine · ·7 Verify · ·8 Harden
CP3 Spec — 2/4 criteria met · NEXT: write spec.md
```

- The **canonical checkpoint list** — `0 Onboard`, `1.5 Ready`, `2 ACs`,
  `3 Spec`, `4 Plan`, `5 Implement`, `6 Refine`, `7 Verify`, `8 Harden` — is a
  constant in the script. It is the single source of truth for the pipeline
  ordering and stage names; the breadcrumb renders the whole list every time so
  the full journey is always visible.
- Each stop is marked: `✓` done, `▶` current, `·` not yet reached. "Done" is
  derived from the `progress.md` Checkpoints table; "current" from the CURRENT
  header's `CP<N>`.
- The third line restates the CURRENT header's detail: criteria met, NEXT
  action, and BLOCKED reason if any.

**Behaviour:**

- **Deterministic.** Derived entirely from `progress.md`. No formatting drift,
  no agent compliance needed — this is the DAE philosophy: a guard rail is an
  independent tool, not a prompt rule.
- **Advisory, never blocking.** Unlike `dae_handoff.py` (the entry gate), a
  non-zero exit or a missing `progress.md` never stops the calling skill. A
  missing `progress.md` — e.g. at `feature-init`, before the file exists —
  degrades gracefully to a pipeline view with every stop `·` and a short note.
- **Read-only.** It produces no artifact and changes nothing.
- Invocation: `dae_progress.py <feature-dir>`. `--help` supported.

### Where it fires

Every checkpoint-advancing engineer skill calls `dae_progress.py` and shows its
output verbatim, so the *first thing* the user sees when a pipeline skill starts
is "you are here." Placement:

- Skills with a `dae_handoff.py` entry gate (`discover-acs`, `atdd`, `plan`,
  `refine`, `arch-check`) — call the breadcrumb in **Step 0**, immediately after
  the entry gate passes.
- `feature-init` (CP1.5) has no entry gate — call it at the start of the
  workflow. It may have no `progress.md` yet; graceful degradation renders the
  pipeline-ahead view (every stop `·`, a "not yet started" note).
- `onboard` (CP0) is **project-scope** — it has no feature folder, so a
  feature-scoped breadcrumb does not apply. `onboard` gets the in-skill TodoWrite
  tracker (Indicator 2) only, no breadcrumb.

The skill end needs no breadcrumb: the handoff summary plus `progress-log`
already mark the advance, and the *next* skill's Step 0 breadcrumb reflects it.
Showing it once per skill, at the start, keeps it "where it makes sense" rather
than noise.

### Reuse by `reorient`

`reorient` already emits a fuller orientation block. Its Step 2 reads the
current checkpoint; it will call `dae_progress.py` for the breadcrumb line so
the passive Step-0 breadcrumb and the on-demand `reorient` output never
disagree on pipeline position.

---

## Indicator 2 — The in-skill step tracker (both plugins)

Answers "which step of this skill am I on."

Use Claude Code's native **TodoWrite**. Each multi-step skill's `## Workflow` is
already a numbered list; the convention makes the mapping mandatory and
consistent:

- At the start of the skill, create **one TodoWrite todo per workflow step**,
  all at once. The full list is created up front so it doubles as a roadmap —
  the user sees the whole journey before it begins.
- Flip each todo to `in_progress` when its step starts and `completed` when it
  ends. The todo panel *is* the live step indicator.
- **Steps that span many turns get sub-todos.** An interview-style step — e.g.
  `discover-acs`'s four-pass AC interview — becomes one todo per pass, so a long
  step does not sit at "in progress" for ten turns with no visible movement.

No new mechanism: this makes the existing TodoWrite behaviour mandatory and
uniform across the pipeline skills.

### For the atdd plugin, this one indicator carries both layers

The atdd skills have no checkpoints and no `progress.md`. Their workflows are:

- `atdd:atdd` — 7 steps (Understand → Specs → Pipeline → Red → Implement →
  Leakage → Iterate)
- `atdd:atdd-mutate` — 6 steps
- `atdd:atdd-team` — 6 phases

Creating the full TodoWrite list up front gives the atdd user the roadmap
("here is the 7-stage journey") *and* the live position ("Step 3/7 in
progress") in a single move. For atdd, that is the whole indicator — there is
no separate breadcrumb and no `dae_progress.py`.

### Composition

When atdd runs inside a DAE feature via `/engineer.atdd`, the engineer
breadcrumb shows the outer position (`CP3 Spec`) and atdd's 7 todos nest inside
it — outer checkpoint plus inner detail, no duplication.

---

## Where the convention is defined

Each plugin is self-contained — separate `${CLAUDE_PLUGIN_ROOT}`, no
cross-plugin file references — so each gets its own reference file. They follow
the existing `engineer/references/handoff-summary.md` pattern: skills reference
the file instead of inlining the convention.

- **`engineer/references/progress-indicator.md`** (new) — defines the canonical
  checkpoint list, the breadcrumb contract (call `dae_progress.py` at Step 0,
  show the output verbatim, advisory/never-blocking), and the TodoWrite step
  convention.
- **`references/progress-indicator.md`** (new) — the atdd-scoped sibling. The
  atdd plugin's root is the repo root (`marketplace.json` source `"./"`), so its
  references directory is `<repo-root>/references/`, which does not exist yet —
  this creates it. It defines the TodoWrite roadmap-and-step convention only (no
  breadcrumb, no script). It is a separate file with genuinely different
  content, not a copy.

## Skills touched

**Engineer plugin.** Six feature-scoped checkpoint skills get the full Step 0
addition — breadcrumb *and* TodoWrite tracker — pointing to
`engineer/references/progress-indicator.md`:

`feature-init` (CP1.5), `discover-acs` (CP2), `atdd` (CP3), `plan` (CP4),
`refine` (CP6), `arch-check` (CP7).

`onboard` (CP0) is project-scope — no feature folder — so it gets the TodoWrite
step tracker only, no breadcrumb.

`reorient` gets a one-line change to call `dae_progress.py` for its breadcrumb
line. Advisory and cross-cutting engineer skills (`next`, `clarify`,
`consistency-check`, `discuss`, `feature-edit`, `prime-context`, `progress-log`,
`session-summary`) are not touched — they do not occupy a checkpoint.

The breadcrumb renders all nine canonical stops, but `CP5 Implement` and
`CP8 Harden` have no dedicated engineer skill — CP5 runs through plan execution,
CP8 through hardening/verification. They appear in the breadcrumb (rendered by
the adjacent skills' Step 0 calls) but no skill emits the breadcrumb *from*
them. That is expected, not a gap.

**Atdd plugin — 3 skills** get a Step 0 addition pointing to
`atdd/references/progress-indicator.md` (TodoWrite convention only):

`atdd`, `atdd-mutate`, `atdd-team`.

## Testing

`dae_progress.py` gets a stdlib `unittest` suite (`test_dae_progress.py`):
breadcrumb rendering from a populated `progress.md`, the done/current/not-reached
marking derived from the Checkpoints table and CURRENT header, the CURRENT-header
detail line, and graceful degradation on a missing or unparseable `progress.md`.

## Versioning

New feature in both plugins → minor bump. `engineer` 0.6.0 → 0.7.0, `atdd`
0.6.0 → 0.7.0, in each `plugin.json` and in the `marketplace.json` entries.

---

## Implementation sequencing

1. **`dae_progress.py`** — built TDD: `progress.md` parsing (Checkpoints table +
   CURRENT header) first, then breadcrumb rendering against the canonical list,
   then graceful degradation, then the CLI.
2. **`engineer/references/progress-indicator.md`** — the engineer convention.
3. **Wire Step 0** into the 6 feature-scoped engineer checkpoint skills (and the
   TodoWrite tracker into `onboard`); update `reorient` to call the script.
4. **`atdd/references/progress-indicator.md`** — the atdd convention.
5. **Wire Step 0** into the 3 atdd skills.
6. **Version bumps** — both `plugin.json` files and the `marketplace.json`
   entries to 0.7.0.

## Open items

- **Canonical list maintenance.** The checkpoint list is duplicated as knowledge
  between `dae_progress.py`, the Foundation Design §8, and the reference file.
  The script is the runtime source of truth; the design accepts the small
  duplication rather than introducing a shared config file for nine constants.

## Out of scope

- **A terminal statusline.** Declined — needs a per-machine `settings.json`
  edit. Both indicators here are in-conversation only.
- **A new `/engineer.progress` skill.** `reorient` (on-demand, fuller) and the
  always-on Step 0 breadcrumb (passive) already cover both access patterns.
- **Inferring atdd position from on-disk artifacts** (`spec.md` → past Step 2,
  `.build/` → past Step 3). That is a resume engine, not an indicator — a
  possible follow-on, not this design.
- **Changes to the `progress.md` schema.** The breadcrumb reads the existing
  Checkpoints table and CURRENT header as-is.
