---
name: discover-acs
description: Use when a Ready feature needs its acceptance criteria discovered before specs are written. Triggers — "/engineer.discover-acs", "/engineer.acceptance-criteria", "discover ACs", "what must this feature do", "figure out acceptance criteria".
---

# discover-acs

Discover a feature's acceptance criteria — Checkpoint 2. ACs are **decisions about what behaviors must work**, in **domain language**. They precede the Given/When/Then formalization that `atdd:atdd` produces.

Separating AC discovery (divergent decisions) from spec formalization (convergent encoding) is what protects domain language from leaking into implementation language.

## When to use

On a feature with `status: ready` and `autonomy_level` set. Produces `acs.md`.

**Not for:** a parked feature (`discuss` to promote first); a feature that already has `acs.md` (`feature-edit`); producing Given/When/Then specs (`atdd:atdd`); deciding whether to build the feature (`discuss`).

## Workflow

1. **Resolve + validate** — find `.engineer/manifest.yml`; locate the feature. Reject if not found, not `ready`, or `acs.md` already exists with content.
2. **Load** — `feature.md`, `CHARTER.md`, `manifest.yml`, prior `handoffs/`.
3. **Interview in four passes** — one question per turn; coverage prompts per pass:
   - **Happy path** — the core journey, every behavior when all goes right
   - **Edge cases** — empty / extreme / boundary / concurrency / partial state
   - **Errors & security** — missing/malformed input, authorization, external failure, abuse
   - **Cross-cutting** — audit, observability, idempotency, data lifecycle, performance
4. **Enforce domain language** — when implementation leaks in ("returns 401", "the endpoint", table/class names), soft-warn and rephrase to the user-observable behavior; user confirms. Don't block — educate.
5. **Handle scope drift** — if a behavior surfaces outside `feature.md`'s outcome, offer three options: broaden `feature.md`, drop as out-of-scope, or park a separate `discuss`. User picks.
6. **Coverage check** — before writing, report ACs captured + which passes were covered; if a pass was skipped, prompt once.
7. **Write `acs.md`** — YAML frontmatter (`ac_count`, `high_priority_count`, `discovered`) + numbered `## AC-N: <name>` sections, each with `Priority`, `Type`, and a domain-language body.
8. **Handoff** — emit a summary.

Re-invoking on a feature with existing `acs.md` is an edit pass (preserve AC IDs). Big restructures → `feature-edit`.

## Handoff

Emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: 2`; `human_action_needed: yes` (review); `recommended_next`: "/atdd:atdd to formalize as Given/When/Then specs".

## References

- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema
- The DAE methodology page — why ACs and specs are separate
