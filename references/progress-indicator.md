# Workflow progress indicator — shared contract

Every atdd skill surfaces *which step you are on* — passively, as it runs —
through the in-skill step tracker. This file is the canonical contract; skills
reference it instead of inlining.

The atdd skills run a whole multi-step workflow in a single invocation, so the
step tracker carries the full picture — there is no separate pipeline
breadcrumb and no progress file.

## The in-skill step tracker

At the **start of the skill**, create **one TodoWrite todo per workflow step
(or phase)**, all at once — the full list up front, so it doubles as a roadmap
of the journey ahead:

- `atdd` — one todo per Step 1–7.
- `atdd-mutate` — one todo per Step 1–6.
- `atdd-team` — one todo per Phase 1–6.

Flip each todo to `in_progress` when its step begins and `completed` when it
ends. The TodoWrite panel is the live position indicator.

A step that spans many turns is split into sub-todos, so a long step shows
visible movement instead of sitting at `in_progress` indefinitely.
