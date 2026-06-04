---
name: prime-context
description: Use before starting pipeline work on a Ready feature the agent hasn't worked yet. Triggers — "/engineer.prime-context", "prime context", "load context before we start", "get up to speed on feature X".
---

# prime-context

Load working memory before pipeline work on a Ready feature — the convergent counterpart to `discuss`. Forked from `superpowers:brainstorming` but inverted: no exploration, just loading and orienting. Produces no artifact.

## When to use

A prep step (not a checkpoint) between `feature-init` and `discover-acs`, on any feature the agent hasn't already worked this session.

**Skip when:** the agent just created the feature this session (context already warm). **Not for:** exploring whether a feature is worth doing (`discuss`).

## Workflow

1. **Resolve + locate** — resolve the methodology root + manifest via `${CLAUDE_PLUGIN_ROOT}/scripts/dae_resolve.py` (see `references/resolving.md`); locate the feature (slug arg or branch name). Reject if no folder / no `feature.md`.
2. **Silent batch load** — without narrating: `feature.md`, `CHARTER.md`, `manifest.yml`, prior `handoffs/` (especially the originating `*-discuss.md`), and the files named in `feature.md`'s "Related code / design pointers".
3. **Orient** — give a concise summary: outcome, scope, autonomy level (+ charter cap), key prior decisions, related code, relevant ADRs.
4. **One prompt** — ask exactly one question: anything else to load? If the user names a new code pointer, load it and offer to add it to `feature.md`. Then stop — prime-context orients, it does not interview.
5. **Breadcrumb handoff** — emit a tiny handoff recording what was loaded.

Re-invocation re-loads fresh (no incremental diffing).

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: null`; `artifacts: []`; `human_action_needed: no`; `recommended_next`: "/engineer.discover-acs".

**Always emit a breadcrumb.** Earlier versions produced no handoff because prime-context creates no artifact. Users expect a breadcrumb after every skill invocation (distbute Jun 4: *"emit the handoff"*) — surprising them with "no artifact by design" breaks the agentic-summary contract. The breadcrumb records: which feature was primed, what files were loaded, any new pointer added to `feature.md`, and the next recommended skill. Body can be one paragraph — frontmatter is the load-bearing part for `progress-log` propagation.

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema
- [Discuss & Upstream Funnel](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — methodology_root resolution
