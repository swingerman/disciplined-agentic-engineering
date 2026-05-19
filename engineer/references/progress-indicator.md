# Pipeline progress indicator — shared contract

Every checkpoint-advancing engineer skill surfaces *where you are* — passively,
as it runs — through two indicators. This file is the canonical contract;
skills reference it instead of inlining.

## Indicator 1 — the pipeline breadcrumb

At **Step 0**, after the entry gate passes (or, for `feature-init`, at the
start of the workflow), run:

    ${CLAUDE_PLUGIN_ROOT}/scripts/dae_progress.py <feature-dir>

and show its output to the human verbatim. It renders the feature's position
across the nine-stop DAE pipeline:

    DAE ▸ 015-image-formats
    ✓0 Onboard · ✓1.5 Ready · ✓2 ACs · ▶3 Spec · ·4 Plan · ·5 Implement · ·6 Refine · ·7 Verify · ·8 Harden
    CP3 Spec — 2/4 criteria met · NEXT: write spec.md

**Advisory, never blocking.** Unlike the `dae_handoff.py` entry gate, a
non-zero exit or a missing `progress.md` never stops the skill — the breadcrumb
is orientation, not a gate. Show whatever it prints and continue.

`onboard` (Checkpoint 0) is project-scope — it has no feature folder — so it
does NOT call the breadcrumb. It uses Indicator 2 only.

## Indicator 2 — the in-skill step tracker

At the start of the skill, create **one TodoWrite todo per workflow step**, all
at once — the full list up front, so it doubles as a roadmap of the journey
ahead. Flip each todo to `in_progress` when its step begins and `completed`
when it ends. The TodoWrite panel is the live position indicator.

A step that spans many turns — an interview-style step such as the four-pass
AC interview — is split into **one sub-todo per pass**, so a long step shows
visible movement instead of sitting at `in_progress` for ten turns.

## The canonical pipeline

`0 Onboard · 1.5 Ready · 2 ACs · 3 Spec · 4 Plan · 5 Implement · 6 Refine ·
7 Verify · 8 Harden`. `dae_progress.py` holds this list as its source of truth;
`5 Implement` and `8 Harden` are pipeline stops with no dedicated skill.
