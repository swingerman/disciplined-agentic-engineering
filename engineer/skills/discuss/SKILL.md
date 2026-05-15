---
name: discuss
description: Use when exploring a feature idea before committing, or revisiting a parked one. Triggers — "/engineer.discuss", "/engineer.discuss <slug>", "I have an idea about", "should we build", "let's think about".
---

# discuss

The upstream funnel of DAE — a divergent brainstorm (forked from `superpowers:brainstorming`) that ends in one of three outcomes: **drop**, **park**, or **promote**. Most ideas die here; some park as `features/NNN-slug/` with `status: parked`; survivors promote to `status: ready`.

## When to use

- **Fresh** — `/engineer.discuss`, no argument. New exploration.
- **Continue** — `/engineer.discuss <slug>`. Resume a parked feature.

**Not for:** feature-work prep on an already-Ready feature (`prime-context`), or editing a committed feature (`feature-edit`).

## Workflow

1. **Resolve + load** — find `.engineer/manifest.yml`; resolve `methodology_root`. Load `CHARTER.md`, `manifest.yml`, and the last ~20 lines of `.engineer/discussions.log`. With a slug arg: also load that feature's `feature.md` + prior `handoffs/*-discuss.md`; reject if its status is `ready`/`in-progress` (→ `feature-edit`) or `done`.
2. **Open** — fresh: "What are you thinking about?" After the first prompt, soft-match the topic against parked feature titles/areas; if a likely match, offer once to continue it. Continue mode: echo prior state in one line, then resume.
3. **Brainstorm (divergent)** — explore intent, scope, alternatives; one question per turn. Surface charter signals (e.g. payment paths cap autonomy), ADR connections, and "too big — decompose?" flags as they arise.
4. **Surface the outcome** — at a natural inflection, recommend an outcome (promote / park / drop); the user confirms. Never auto-execute. If the user says "drop" but there's a concrete reason it's worth parking, ask once.
5. **Execute the outcome:**
   - **Drop** — append one line to `.engineer/discussions.log`: `<ISO-timestamp> | <slug> | dropped | <one-line why>`. Draft the "why" from context; user confirms/edits.
   - **Park** — invoke `feature-init` with `feature_intake { status: parked, autonomy_level: null, ... }`.
   - **Promote** — first resolve `autonomy_level` (low/medium/high, charter caps surfaced); if the user can't decide, fall back to park. Then invoke `feature-init` with `status: ready`.
6. **Handoff** — for park/promote, write a `<timestamp>-discuss.md` handoff into the new feature folder. For drop, the log line is the record — no handoff.

**Continuing a parked feature:** each session appends a new discuss handoff; `feature.md` is refined in place. Promoting a continued feature flips status to `ready` directly — `feature-init` is not re-invoked.

## Handoff

For park/promote, emit per `${CLAUDE_PLUGIN_ROOT}/references/handoff-summary.md`. `checkpoint: null`. Drop emits no handoff.

## References

- [Discuss & Upstream Funnel](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384) — funnel, drop-log format, park/promote paths
- [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — feature.md schema, autonomy levels
- Sister skill: `feature-init` (invoked for park/promote).
