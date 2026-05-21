# Twitter / X threads — Disciplined Agentic Engineering

Two threads for promotion. Each tweet ≤280 characters (URLs count as 23 via t.co).
- **Thread A — "What + why"** (11 tweets): the methodology pitch end-to-end.
- **Thread B — "Feature tour"** (12 tweets): what shipped across v1.0 → v1.3.

Post one per launch wave; combine into a single longer thread if needed.

---

## Thread A — What + Why (11 tweets)

**1/**
```
Disciplined Agentic Engineering (DAE) hit v1.3 — a Claude Code methodology for engineers who want AI's speed without losing the system's coherence.

A short thread on what it is and why it matters. 🧵
```

**2/**
```
The problem it addresses: vibe coding.

Loose prompts. Accept what comes back. Patch when something feels off.

Fast at first. Brittle over time. The codebase drifts. Tests pass without proving anything. Regressions surface as users find them.
```

**3/**
```
DAE is the deliberate opposite.

Every feature has a charter to obey. ACs in domain language. A Gherkin spec the human approves. An architecture plan. Two test streams that both must go green. Mutation testing as the test-quality firewall.
```

**4/**
```
The premise: discipline that lives in a prompt erodes.

Discipline that lives in independent scripts the agent has to run and pass doesn't.

Every checkpoint in the DAE pipeline is gated by a tool the agent can't talk its way past.
```

**5/**
```
A historical angle.

Programming has always climbed the abstraction ladder.

Binary → assembly → high-level → frameworks → and now, with capable LLMs, spec and behavior description as the next rung.
```

**6/**
```
Nobody hand-writes opcodes anymore.
Nobody audits the assembly a compiler emits.

The rung below is trusted because the generator is rigorous AND the inputs are checked.

AI-generated code earns that same trust the same way.
```

**7/**
```
What never shifts is engineering discipline.

A good engineer in 1975 cared about correctness, structure, maintainability, verification.

So does a good engineer in 2026 — even though the artifact has changed from PDP-11 assembly to a Gherkin spec.
```

**8/**
```
DAE is for software engineers.

People who know what acceptance tests are. Why mutation testing matters. Why architectural layering matters.

Not for "build an app without code" audiences. The decisions DAE puts in front of you are engineering decisions.
```

**9/**
```
Three Claude Code plugins:

• engineer — the DAE pipeline (16 skills, 10 guardrail scripts, 214 stdlib-only tests)
• atdd — acceptance test driven workflow + differential mutation testing
• crap-analyzer — change-risk analysis on touched code
```

**10/**
```
ATDD itself is older — XP / FIT / Fitnesse lineage (Kent Beck, Ward Cunningham, and others).

Robert C. Martin's recent agent-swarm experiments on empire-2025 surfaced its application as a discipline against AI agentic drift.

DAE packages that approach for Claude Code.
```

**11/**
```
Install:

/plugin marketplace add swingerman/disciplined-agentic-engineering

Methodology + repo:
github.com/swingerman/disciplined-agentic-engineering
```

---

## Thread B — Feature tour (12 tweets)

**1/**
```
Disciplined Agentic Engineering shipped four major features between v1.0 and v1.3.

A short tour of what each one adds and the bug it fixes. 🧵
```

**2/**
```
v1.0 — Context-Resilient Discipline.

Handoff-as-gate: a checkpoint isn't done until its handoff exists with every exit criterion met.

Plus a `reorient` skill for mid-task re-anchoring after compaction. Plus fresh-per-phase agent teams. No more eroded identities.
```

**3/**
```
v1.0 — Charter Architecture Fitness.

dae_arch.py checks your CHARTER's layering / forbidden patterns / naming / file size rules like a test.

Architecture violations get caught at Checkpoint 7 — not in code review three weeks later.
```

**4/**
```
v1.0 — Test Impact Analysis.

dae_impact.py: change a source file, run only the acceptance scenarios it affects.

Full suite still runs at the gate. Inner-loop speedup, never a false skip.
```

**5/**
```
v1.0 — Progress Indicators.

Pipeline breadcrumb at every Step 0 (dae_progress.py).

Plus a TodoWrite step-tracker convention so you can see where you are in the 8-checkpoint pipeline at a glance.
```

**6/**
```
v1.1 — Differential Mutation Testing.

dae_mutmap.py: re-mutate only functions whose code, covering tests, OR mutation operator set changed.

Hash triple guarantees the cache is safe to commit and share — CI, fresh clones, every dev benefits.
```

**7/**
```
v1.2 — Branch Hygiene.

dae_branch.py at every checkpoint's Step 0 verifies you're on the feature's branch.

Catches a real silent-failure mode: an agent on master writing the feature's commits to the wrong place.
```

**8/**
```
v1.3 — Code Hygiene, part 1: cycle detection.

dae_arch.py gains Tarjan's SCC over the import graph it already builds.

Circular dependencies surface as a new violation kind alongside layering. Multi-language for free.
```

**9/**
```
v1.3 — Code Hygiene, part 2: project-wide duplicate detection.

dae_dup.py (jscpd by default) feeds Refine's Reuse subagent.

The LLM lens used to be blind to duplicates outside the changed scope. Now it isn't. One triage pass, not two.
```

**10/**
```
v1.3 — LSP-first Code Lookup.

Skills doing semantic code lookup (find-references, definitions, workspace-symbols) prefer the LSP MCP when available, falling back to AST tools or grep.

Sharper "missed existing utilities" detection in Refine.
```

**11/**
```
Every feature shipped TDD. Code review often caught real bugs in a fix-loop before merge.

214 stdlib-only unit tests across the guardrail scripts. Zero plugin dependencies beyond stdlib + jscpd (optional).
```

**12/**
```
Install:

/plugin marketplace add swingerman/disciplined-agentic-engineering

Methodology + repo:
github.com/swingerman/disciplined-agentic-engineering
```
