# Disciplined Agentic Engineering — a Claude Code methodology marketplace

*Spec-driven, test-driven, charter-bound AI coding for Claude Code. ATDD + mutation testing + deterministic guardrails. Three plugins: `engineer`, `atdd`, `crap-analyzer`.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code Marketplace](https://img.shields.io/badge/Claude%20Code-Marketplace-blueviolet)](https://github.com/swingerman/disciplined-agentic-engineering)

> ℹ️ **Repo renamed:** this marketplace was previously `swingerman/atdd`. Existing `swingerman/atdd` URLs continue to work via GitHub's automatic redirect — no action needed unless you want to update local remotes (`git remote set-url origin https://github.com/swingerman/disciplined-agentic-engineering.git`).

A Claude Code marketplace hosting the **Disciplined Agentic Engineering (DAE)** methodology kit — skills, agents, hooks, slash commands, and deterministic guardrail tools that keep software engineers in charge of architecture, behavior decisions, and verification while AI agents do the typing. Built around **Acceptance Test Driven Development (ATDD)**, **mutation testing**, and the **iterative, layered specification** pattern of [GitHub's Speckit](https://github.com/github/spec-kit).

## What is Disciplined Agentic Engineering?

DAE is a methodology for **engineering-led AI development**. AI agents do the coding; software engineers stay in charge of architecture, performance, and feature validation. Discipline lives in the contracts at every layer (charter → ACs → specs → plans → verification) and in **deterministic guardrail tools** that gate every checkpoint — not in prompt rules that erode over long agent runs.

It's positioned in direct opposition to **vibe coding** — the loose-prompt, weak-check style of agentic development where AI produces code with no charter, no behavior contract, and no verification gates. DAE makes the boundaries explicit and the checks continuous.

**The headline outcome: semantic stability.** ATDD + mutation testing together form a *semantic firewall* — code can be refactored, extended, or modified by agents without the system's intended behavior drifting. This is the moat between DAE-built systems and "AI plops code around."

### Who is this for?

DAE is **for software engineers** — people who already know what acceptance tests are, why mutation testing matters, why architectural layering matters, why naming matters, why the difference between a behavior contract and an implementation detail matters. The methodology assumes you can read a `plan.md` and tell whether the proposed architecture is sound; that you can read a Gherkin spec and tell whether the behavior contract captures intent; that you know when a charter rule should be enforced vs. amended.

**It is not for non-programmers.** "Build an app without code" tools target a different audience and a different problem. DAE keeps the engineer in charge precisely because the decisions DAE puts in front of you — architecture, behavior contracts, charter rules, verification thresholds, autonomy levels — are *engineering* decisions, and they need engineering judgment.

If you are a software engineer who wants AI's speed without losing the system's coherence, DAE is built for you.

### DAE vs. vibe coding

**Vibe coding** is the rising practice of prompting an AI agent loosely — *"build me a thing that does X"* — accepting whatever comes back, running it, patching when something feels off. No charter to obey, no behavior contract to satisfy, no verification gates to pass. Fast at first; brittle over time. The codebase drifts; tests pass without proving anything; regressions surface as users find them.

**DAE is the deliberate opposite.** Every feature has a charter to obey, a Ready contract for what's being built, ACs in domain language, a Gherkin spec the human can read and defend, an architecture plan the human approves before code is written, two test streams that must both go green, mutation testing that proves the tests catch bugs, and deterministic guardrail tools that gate every transition. The human stays the engineer; the agent stays the typist.

| | Vibe coding | Disciplined Agentic Engineering |
|---|---|---|
| **Architecture** | emerges from prompts | engineered upfront; `CHARTER.md` enforced by `arch-check` (layering, cycles, forbidden patterns, naming, file size) |
| **Behavior contract** | "what the agent built" | ACs + Gherkin specs, human-approved, leakage-checked by `spec-guardian` |
| **Verification** | run it, see if it works | two test streams (acceptance + unit) + change-risk (`crap-analyzer`) + mutation testing |
| **Gates** | none | `dae_handoff.py` (handoff-as-gate), `dae_branch.py` (branch hygiene), `dae_arch.py`, `dae_dup.py`, exit criteria per checkpoint |
| **Refactoring safety** | tests may not catch regressions | mutation-tested test suite = *semantic firewall* |
| **Autonomy** | implicit; drifts | explicit per-feature level, manifest-constrained, charter-bound |
| **Discipline lives in…** | a prompt (and erodes) | independent tools the agent runs (and can't talk itself out of) |
| **Pace** | fast initially | steady; sustainable across long horizons |

If you're shipping something quick and disposable, vibe coding is fine. If you're building something you intend to maintain and evolve — and you want AI agents helping without eroding what they touch — DAE is the discipline that keeps the system coherent.

### A historical angle — abstraction climbs; discipline endures

Programming has always been a climb up the abstraction ladder. Toggling binary on a front panel → punch cards → assembly → high-level languages → garbage collection → frameworks → managed runtimes — and now, with capable LLMs, **specification and behavior description as the next rung**. At every step the rung below fades from daily concern: nobody hand-writes opcodes anymore; nobody audits the assembly a compiler emits. The artifact a human authors shifts upward, and the rung below is *trusted as generated output*.

What never shifts is **engineering discipline**. A good engineer in 1975 cared about correctness, structure, maintainability, separation of concerns, verification — and so does a good engineer in 2026, even though the artifact has changed from PDP-11 assembly to a Gherkin spec and a charter. The compiler-generated assembly was trusted because the compiler was rigorous *and the inputs were checked*. AI-generated code earns that same trust the same way: the input artifact (specs, ACs, plans, charter) is rigorous, and the output is checked (two test streams + mutation testing + arch-fitness + change-risk + duplicate detection + cycle detection).

**DAE is the discipline layer for the spec-as-source-code era.** It treats specifications, acceptance criteria, and architecture as the artifacts engineers author and review with care; it lets AI agents handle the keystrokes the way compilers handle opcodes. The pipeline, the verification gates, the handoff-as-gate transitions, the two test streams, the mutation firewall — those *are* the discipline, instantiated as independent tools the agent has to satisfy. The methodology adapts to the new abstraction; the engineering values are the same as they have always been.

If the artifact you author changes but you stop checking the output, you don't get speed — you get a faster path to a brittle, drifting system. DAE's premise is that **the new abstraction needs the same discipline the old ones did** — and the right place to instantiate that discipline is in tools the methodology hands you, not in good intentions.

DAE synthesizes four sources:

- **ATDD** — Acceptance Test Driven Development. An established testing practice from the XP / FIT / Fitnesse lineage (Kent Beck, Ward Cunningham, and others). Robert C. Martin's recent experiments in [empire-2025](https://github.com/unclebob/empire-2025) demonstrated ATDD's particular power as a constraint on **agentic** AI development — two test streams (acceptance + unit) the AI cannot talk its way past, plus mutation testing as the test-quality firewall. The `atdd` plugin in this marketplace packages that agentic-coding approach for Claude Code.
- **[Speckit](https://github.com/github/spec-kit)** — Spec-driven agentic development. DAE adopts Speckit's central insight that **specification is iterative and layered, not a one-shot document**. Each DAE feature evolves through a sequence of progressively-sharper specs: `feature.md` (intent — the Ready contract) → `acs.md` (behavior in domain language) → `spec.md` (Gherkin — executable) → `plan.md` (architecture). Each layer is reviewed and approved before the next is written; each constrains and informs the layers below. The per-feature folder is the workspace that holds these layers (and the `handoffs/` + `.build/` they accumulate) together.
- **[Acceptance Pipeline Specification](https://github.com/unclebob/Acceptance-Pipeline-Specification)** (Uncle Bob, 2026) — Portable acceptance pipeline: Gherkin → JSON IR → generated tests → runner; mutation as IR-level sidecar.
- **Claude Code's stock `/simplify`** — The three-subagent parallel review pattern (Reuse / Quality / Efficiency). DAE's `refine` (Checkpoint 6) is modeled on this skill, adding two layers on top: charter validation of every proposal (charter-violating proposals are rejected internally, never shown) and graceful breaking-change classification.

DAE sharpens these into a single workflow. The full methodology spec lives in [Notion](https://www.notion.so/3505ecdee0e281b297c8d9c07ec6dad6).

## Plugins in this marketplace

| Plugin | Purpose | Status |
|--------|---------|--------|
| **[`engineer`](engineer/)** | The DAE methodology kit — feature intake, AC discovery, spec writing, planning, refinement, verification, hardening. Ships the deterministic guardrail scripts (`dae_*.py`) every checkpoint depends on. | v0.10 — pipeline shipped |
| **[`atdd`](./)** | Acceptance Test Driven Development workflow with team orchestration, **differential mutation testing**, and the portable Gherkin pipeline. | v0.8 — stable |
| **[`crap-analyzer`](crap-analyzer/)** | Change Risk Anti-Pattern analysis on changed code; part of DAE's Light Verify (Checkpoint 7). | v0.1 |

## Install the marketplace

```shell
/plugin marketplace add swingerman/disciplined-agentic-engineering
```

Then install plugins individually:

```shell
/plugin install atdd@disciplined-agentic-engineering          # ATDD workflow + differential mutation testing
/plugin install engineer@disciplined-agentic-engineering      # DAE methodology kit
/plugin install crap-analyzer@disciplined-agentic-engineering # CRAP risk analysis on changed code
```

Or test locally by cloning:

```bash
git clone https://github.com/swingerman/disciplined-agentic-engineering.git
claude --plugin-dir ./disciplined-agentic-engineering
```

---

## The `engineer` plugin (DAE methodology)

The DAE pipeline operates on **features** — each a numbered folder accumulating an iterative stack of specs (feature → ACs → Gherkin spec → plan), Speckit-style. Each feature runs through 8 checkpoints:

```
0 Onboard → 1.5 Ready (feature.md) → 2 ACs → 3 Spec → 4 Plan → 5 Implement → 6 Refine → 7 Light Verify → 8 Hardening (optional)
```

### The 8 checkpoints in brief

| # | Stage | Skill / Tool | What happens |
|---|-------|--------------|--------------|
| **0** | **Onboard** | `onboard` | Project bootstrap. The human signs off the **charter** (architecture, conventions, scope, quality stance, autonomy stance) and picks the tracker. Manifest, `features/` layout, and consolidation backlog produced. One-time per project. |
| **1.5** | **Ready** | `feature-init` | A feature becomes Ready: `feature.md` records the outcome, scope, owner, autonomy level, and the branch. The contract for "what we're building." |
| **2** | **ACs** | `discover-acs` | Acceptance Criteria discovered via four-pass interview — happy path, edge cases, errors & security, cross-cutting. Output: `acs.md` in domain language (no implementation leakage). |
| **3** | **Spec** | `engineer.atdd` → `atdd:atdd` | Formalize ACs as standard Gherkin in `spec.md`; generate the project-specific test pipeline (parser → IR → tests). Spec leakage caught by `spec-guardian`. |
| **4** | **Plan** | `plan` | Architecture plan + structured **Charter Check** (one row per charter rule, plus auto-rows for autonomy, verification independence, mutation policy). The human confirms the Architecture section before the rest drafts. |
| **5** | **Implement** | `atdd:atdd-team` | A fresh-per-phase agent team implements against the specs. **Two test streams** (acceptance + unit) must go green together; neither alone is sufficient. |
| **6** | **Refine** | `refine` | Three-subagent parallel review (Reuse / Quality / Efficiency, modeled on Claude Code's `/simplify`), fed deterministic project-wide duplicate findings from `dae_dup.py`, filtered through the charter, with graceful breaking-change handling. |
| **7** | **Light Verify** | `arch-check` + `crap-analyzer` | Charter architecture fitness (layering, **cycles**, forbidden patterns, naming, file size) plus Change Risk Anti-Pattern analysis on the changed code. |
| **8** | **Hardening** *(optional)* | `atdd:atdd-mutate` | **Differential mutation testing** verifies the unit tests actually catch bugs. Re-mutates only the functions whose code, covering tests, or mutation operator set changed. |

**Every checkpoint is gated by deterministic guardrail tools — not by prompt rules.** At every checkpoint-advancing skill's Step 0:

- **Entry gate** (`dae_handoff.py`) — the prior checkpoint's handoff must exist, `status: complete`, every exit criterion met.
- **Branch hygiene** (`dae_branch.py`) — the agent must be on the feature's branch (`git.manual: true` opts out project-wide).
- **Pipeline breadcrumb** (`dae_progress.py`) — passive "you are here" surfacing.

### Skills

| Skill | Command | Role |
|-------|---------|------|
| `onboard` | `/engineer.onboard` | Project bootstrap — charter, manifest, tracker, migration (Checkpoint 0) |
| `discuss` | `/engineer.discuss` | Upstream funnel — divergent brainstorm; outcomes: drop / park / promote |
| `feature-init` | `/engineer.feature-init` | Mechanics — produces `feature.md` (Ready contract), folder, branch, tracker entry (Checkpoint 1.5) |
| `prime-context` | `/engineer.prime-context` | Convergent load — orient on a Ready feature before AC discovery |
| `discover-acs` | `/engineer.discover-acs` | AC discovery interview — iterative passes (happy / edge / errors / cross-cutting); output: `acs.md` (Checkpoint 2) |
| `atdd` (engineer namespace) | `/engineer.atdd` | Checkpoint 3 entry point — bridges into `atdd:atdd` for Given/When/Then specs + project-specific test pipeline |
| `plan` | `/engineer.plan` | Architecture plan + structured Charter Check; output: `plan.md` (Checkpoint 4) |
| `refine` | `/engineer.refine` | Three-subagent review (reuse / quality / efficiency) fed by `dae_dup.py` deterministic duplicate findings + charter filter (Checkpoint 6) |
| `arch-check` | `/engineer.arch-check` | Charter architecture fitness — dependency layering, **cycles**, forbidden patterns, naming, file size (Checkpoint 7) |
| `reorient` | `/engineer.reorient` | Mid-task re-anchoring after context compaction or long agent runs |
| `clarify` | `/engineer.clarify` | Single-artifact ambiguity resolution |
| `consistency-check` | `/engineer.consistency-check` | Cross-artifact validation, read-only — errors + warnings |
| `feature-edit` | `/engineer.feature-edit` | Intent-driven edits with downstream cascade orchestration |
| `progress-log` | `/engineer.progress-log` | Propagation engine — handoffs → `progress.md` + tracker sync |
| `session-summary` | `/engineer.session-summary` | Per-session `session-log.md` entry — pick up cleanly next session |
| `next` | `/engineer.next` | Session-start advisory — surveys all state, recommends what to pick up next |

Interoperates with the `atdd` plugin: `atdd:atdd` (Checkpoint 3 — Given/When/Then specs), `atdd:atdd-team` (Checkpoint 5 — implementation), `atdd:mutate` + `atdd:kill-mutants` (Checkpoint 8 — hardening); and `crap-analyzer` (Checkpoint 7 — Light Verify, alongside `arch-check`).

### How DAE work flows

1. **`/engineer.onboard`** — one-time: charter, manifest, tracker, `features/` (Checkpoint 0)
2. **`/engineer.discuss`** — brainstorm an idea; agent surfaces outcome (drop / park / promote)
3. **`/engineer.feature-init`** (invoked by discuss for park or promote) — creates the feature folder and branch
4. **`/engineer.prime-context`** — load working memory on the Ready feature
5. **`/engineer.discover-acs`** — interview to enumerate behaviors; produces `acs.md` (Checkpoint 2)
6. **`/engineer.atdd`** (bridges into `atdd:atdd`) — formalize ACs as Given/When/Then specs (Checkpoint 3)
7. **`/engineer.plan`** — architecture plan + Charter Check (Checkpoint 4)
8. **`/atdd:atdd-team`** — implement against the specs with a fresh-per-phase agent team (Checkpoint 5)
9. **`/engineer.refine`** — charter-bound clean-up; consumes deterministic duplicate findings from `dae_dup.py` (Checkpoint 6)
10. **`/engineer.arch-check`** + **`crap-analyzer`** — Light Verify (Checkpoint 7)
11. **`/atdd:mutate`** — optional Hardening with differential mutation testing (Checkpoint 8)

Cross-cutting throughout: `clarify`, `consistency-check`, `feature-edit`, `progress-log`, `reorient`, `session-summary`, `next`.

Every agentic task ends with a structured handoff summary (frontmatter + body) carrying its checkpoint, artifacts, exit-criteria assertions, and `recommended_next` — the human knows when to re-engage after walking away, and the next checkpoint's entry gate uses the handoff to decide whether it can proceed.

### Example: a feature, end to end

A walkthrough of building "feature 015 — image upload":

```text
# Session 1 — From idea to spec

$ /engineer.discuss
[divergent brainstorm: "add image upload to user profile"]
→ Promote to feature (autonomy: medium)

[discuss invokes feature-init automatically]
Created features/015-image-upload/
  ├── feature.md          ← Ready contract (outcome, scope, autonomy, branch)
  ├── handoffs/
  └── .build/
Created branch image-upload

$ /engineer.discover-acs
[four-pass interview: happy / edge / errors & security / cross-cutting]
Wrote features/015-image-upload/acs.md  (8 ACs, domain language)
Handoff → human review

$ /engineer.atdd     # bridges into atdd:atdd
Wrote features/015-image-upload/spec.md   (4 scenarios, standard Gherkin)
Generated .build/spec.json (IR)
Generated project-specific test pipeline

# Session 2 — Plan + implement

$ /engineer.plan
[agent proposes Architecture; human confirms]
[agent drafts Phasing, Performance budgets, Charter Check]
Wrote features/015-image-upload/plan.md   (Charter Check: 0 deviations)

$ /atdd:atdd-team
[Phase 1–2: spec writing + review — passed]
[Phase 3: pipeline generation — already done]
[Phase 4: implementation — fresh agent; both test streams green]
[Phase 5: refine — Reuse/Quality/Efficiency + dae_dup.py findings]
[Phase 6: verify & harden — arch-check + crap-analyzer + differential mutation]

# Session 3 — Wrap

$ /engineer.session-summary
Wrote features/015-image-upload/session-log.md
Next-tasks: open the PR
```

Every step ends with a handoff. The next step's entry gate (`dae_handoff.py`) verifies the prior handoff is complete with every exit criterion met before it proceeds; `dae_branch.py` verifies you're on `image-upload`; `dae_progress.py` shows the pipeline breadcrumb so you always know where you are.

### Tunable autonomy

Every feature carries an explicit **autonomy level** — how much the agent decides on its own vs. asking for human sign-off. The level is chosen at `feature-init` time and recorded in `feature.md`. The project constrains valid levels in `.engineer/manifest.yml` under `autonomy.allowed_levels`, and the CHARTER's "autonomy stance" section explains the philosophy in prose. Sensitive paths (security, billing) get tighter levels via **path overrides** in the manifest.

Skills consult the autonomy level to decide how much to ask vs. proceed. `plan` always asks the human to confirm the Architecture section — charter-decision territory — regardless of level; but at higher autonomy the rest of the plan drafts straight through. At lower autonomy, more decisions pause for human approval and surface in the handoff's `human_action_needed` field, so the orchestrator (`next`) knows what's blocked.

The autonomy dial is what makes the methodology workable across a spectrum from "I want to review every line" to "agent, go cook." See [Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) for the level schema and path-override rules.

### Infrastructure — the deterministic guardrails

Stdlib-only Python scripts in `engineer/scripts/` that enforce the methodology contracts. Each has a `test_*.py` sibling; ~214 tests total at the time of the v1.3.0 release.

| Script | Purpose |
|--------|---------|
| `dae_resolve.py` | Methodology-root + manifest resolver; central manifest schema validation |
| `dae_handoff.py` | Handoff-as-gate: a checkpoint isn't done until its handoff exists, `status: complete`, every exit criterion met |
| `dae_branch.py` | Branch hygiene at every checkpoint entry; honors `git.manual: true` opt-out |
| `dae_progress.py` | Pipeline breadcrumb rendered at each skill's Step 0 |
| `dae_arch.py` | Charter architecture fitness — layering, **cycles** (Tarjan's SCC), forbidden patterns, naming, file size |
| `dae_impact.py` | Test Impact Analysis — when code changes, run only the acceptance scenarios it affects |
| `dae_mutmap.py` | Differential Mutation Testing — re-mutate only functions whose code, covering tests, or mutation operator set changed |
| `dae_dup.py` | Duplicate-code detection (`jscpd` by default, configurable) fed into Refine's Reuse lens |
| `dae_gherkin.py` | Portable Gherkin → IR parser for the acceptance pipeline |
| `dae_tracker_local.py` | The local tracker driver (feature folders as the source of truth) |

### Methodology references

The full methodology (principles, handoff map, autonomy levels, foundation contracts) lives in Notion:

- **[DAE methodology page](https://www.notion.so/3505ecdee0e281b297c8d9c07ec6dad6)** — overview
- **[Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207)** — schemas, paths, conventions every skill consumes
- **[Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384)** — on-ramp contracts
- **[Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13)** — driver abstraction, sync direction

---

## The `atdd` plugin — Acceptance Test Driven Development for Claude Code

The original ATDD workflow plugin continues to ship as part of this marketplace. The `engineer` kit and `atdd` plugin interoperate: `engineer.discover-acs` produces ACs that `engineer.atdd` (bridging into `atdd:atdd`) formalizes as Given/When/Then specs.

> "Specs will be co-authored by the humans and the AI, but with final approval, ferociously defended, by the humans." — Robert C. Martin

**Packages [Robert C. Martin's](https://en.wikipedia.org/wiki/Robert_C._Martin) (Uncle Bob) approach to applying ATDD to agentic AI coding** — as developed in [empire-2025](https://github.com/unclebob/empire-2025) and his public writings on Spec-Driven Design (SDD) for AI agents. ATDD itself is an older testing practice (XP / FIT / Fitnesse lineage); Uncle Bob's contribution is *how to wield it as a discipline against AI agents that "willy-nilly plop code around."* This plugin turns that approach into Claude Code skills, agents, hooks, and commands.

### Why ATDD with AI?

When using AI to write code, two problems emerge:

1. **AI writes code without constraints** — without acceptance tests anchoring behavior, AI can "willy-nilly plop code around" and write unit tests that pass but don't verify the right behavior.
2. **Implementation details leak into specs** — AI naturally tries to fill Given/When/Then statements with class names, API endpoints, and database tables instead of domain language.

This plugin solves both by enforcing the ATDD workflow and guarding against implementation leakage. The result: **two test streams** (acceptance + unit) that constrain AI development.

> "The two different streams of tests cause Claude to think much more deeply about the structure of the code. It can't just willy-nilly plop code around and write a unit test for it. It is also constrained by the structure of the acceptance tests." — Robert C. Martin

### Quick start

```
/atdd:atdd Add user authentication with email and password
```

Claude will guide you through writing acceptance specs, generating a project-specific test pipeline, and implementing with TDD.

```
/atdd:spec-check     # audit specs for implementation leakage
/atdd:mutate         # mutation testing (verify tests catch bugs)
/atdd:kill-mutants   # write tests targeting surviving mutants
```

### How the ATDD workflow works

```
1. Write Given/When/Then specs (natural language, domain-only)
                    ↓
2. Generate test pipeline (parser → IR → test generator)
   Pipeline has DEEP knowledge of your codebase internals
                    ↓
3. Run acceptance tests → they FAIL (red)
                    ↓
4. Implement with TDD (unit tests + code) until BOTH streams pass
                    ↓
5. Review specs for implementation leakage
                    ↓
6. Mutation testing → verify tests actually catch bugs
                    ↓
7. Iterate — next feature, back to step 1
```

The generated pipeline is NOT like Cucumber. It's "a strange hybrid of Cucumber and the test fixtures" (Uncle Bob) — the parser/generator has **deep knowledge of your system's internals** and produces complete, runnable tests. No manual fixture code needed.

### GWT spec format

Specs are **standard Gherkin** in `spec.md` (the DAE methodology's acceptance-pipeline format — Foundation §7):

```gherkin
Feature: User registration

Scenario: User can register with email and password
  Given no registered users
  When a user registers with email "bob@example.com" and password "secret123"
  Then there is 1 registered user
  And the user "bob@example.com" can log in
```

> **Migrating from the legacy `;=== .txt` format?** Run
> `dae_gherkin_convert.py specs/feature.txt features/NNN-slug/spec.md` (in the
> `engineer` plugin's `scripts/`). The `.txt` format is deprecated.

**The Golden Rule:** specs describe what the system does, not how it does it.

| Bad (implementation leakage) | Good (domain language) |
|------------------------------|----------------------|
| `Given the UserService has an empty userRepository` | `Given there are no registered users` |
| `When a POST request is sent to /api/users with JSON body` | `When a new user registers with email "bob@example.com"` |
| `Then the database contains 1 row in the users table` | `Then there is 1 registered user` |

### Team-based ATDD

For larger features, the `atdd-team` skill orchestrates a six-phase ATDD workflow — spec writing, spec review, pipeline generation, implementation, refine, verify & harden — spawning a **fresh agent per phase** so no agent erodes across a long-running feature. Each phase ends with a durable handoff and is gated on the prior checkpoint's exit criteria.

The team integrates cleanly with existing teams via three options: extend (add ATDD roles to an existing team), replace (start fresh), or new team (parallel to existing).

### Mutation testing — with differential re-runs

Mutation testing adds a **third validation layer**: after acceptance tests verify WHAT and unit tests verify HOW, mutation testing verifies that your tests **actually catch bugs**.

```
1. Acceptance tests  → verify WHAT (external behavior)
2. Unit tests        → verify HOW  (internal structure)
3. Mutation testing  → verify REAL? (do tests catch bugs?)
```

```
/atdd:mutate                    # run mutation testing
/atdd:mutate src/auth/          # target specific module
/atdd:kill-mutants              # write tests to kill survivors
```

**Differential Mutation Testing** (shipped in v1.1). `dae_mutmap.py` maintains a committed `mutation-manifest.json` keyed by function. A function is re-mutated only when its **code**, its **covering tests**, or the **mutation operator set** changed; cached results survive across runs. The hash triple guarantees the cache is safe to share — CI, fresh clones, and every developer benefit without burning compute on unchanged code. See `references/differential-mutation.md`.

The plugin's preferred approach is to **build a project-specific mutation tool** (small, TDD-built, walks the AST) following the approach in [empire-2025](https://github.com/unclebob/empire-2025/blob/master/docs/plans/2026-02-21-mutation-testing.md). For rapid setup, established frameworks (Stryker, mutmut, PIT, Stryker.NET, cargo-mutants, go-mutesting, mutant, Stryker4s) are also supported — most have native incremental modes that compose with the differential-mutation contract.

### atdd plugin components

| Component | Name | Purpose |
|-----------|------|---------|
| Skill | `atdd` | 7-step ATDD workflow: specs → pipeline → red/green → iterate |
| Skill | `atdd-team` | Orchestrates a fresh-per-phase agent team for ATDD |
| Skill | `atdd-mutate` | Mutation testing workflow with differential re-runs (`dae_mutmap.py`) |
| Agent | `spec-guardian` | Catches implementation leakage in Given/When/Then |
| Agent | `pipeline-builder` | Generates bespoke parser → IR → test generator |
| Command | `/atdd:atdd` | Start the ATDD workflow |
| Command | `/atdd:spec-check` | Audit specs for implementation leakage |
| Command | `/atdd:mutate` | Run mutation testing |
| Command | `/atdd:kill-mutants` | Analyze surviving mutants |
| Hook | PreToolUse | Soft warning when writing code without acceptance specs |
| Hook | Stop | Reminder to verify both test streams pass |

---

## Repo layout

```
.
├── .claude-plugin/
│   ├── marketplace.json    # marketplace manifest (atdd + engineer + crap-analyzer)
│   └── plugin.json         # atdd plugin manifest (the atdd plugin's root is the repo root)
├── agents/                 # atdd plugin agents (spec-guardian, pipeline-builder)
├── commands/               # atdd plugin commands (/atdd:atdd, /atdd:mutate, …)
├── hooks/                  # atdd plugin hooks
├── references/             # atdd plugin references (progress-indicator.md,
│                           # differential-mutation.md)
├── skills/                 # atdd plugin skills (atdd, atdd-team, atdd-mutate)
├── engineer/               # engineer plugin (DAE methodology kit)
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── references/         # shared methodology references (handoff-summary.md,
│   │                       # progress-indicator.md, code-lookup.md, …)
│   ├── scripts/            # dae_*.py guardrail scripts + their unit tests
│   └── skills/             # the 16 engineer skills
└── crap-analyzer/          # crap-analyzer plugin (CRAP risk analysis)
    ├── .claude-plugin/
    │   └── plugin.json
    └── skills/
        └── crap-analyzer/
```

## Attribution

The `atdd` plugin packages **Robert C. Martin's (Uncle Bob) approach to applying ATDD to agentic AI coding** into Claude Code skills, agents, hooks, and commands. ATDD itself is an older testing practice from the XP / FIT / Fitnesse lineage (Kent Beck, Ward Cunningham, and others); Uncle Bob's distinct contribution is its disciplined application against AI agents — the two-test-stream constraint, the spec-leakage rule, the project-specific test pipeline, the differential-mutation insight. The approach, insights, and surrounding practices come from:

- [empire-2025](https://github.com/unclebob/empire-2025) — Uncle Bob's project where this approach was developed and refined
- [Acceptance Pipeline Specification](https://github.com/unclebob/Acceptance-Pipeline-Specification) — Portable acceptance pipeline spec that DAE adopts
- His public writings and tweets on ATDD, SDD, and AI-assisted development — including the swarm-failure observations that drove DAE's deterministic-guardrail philosophy and the differential-mutation post that shaped `dae_mutmap.py`

The `engineer` plugin synthesizes Uncle Bob's ATDD-for-agents approach with **[Speckit](https://github.com/github/spec-kit)'s iterative, layered specification pattern** — every feature progresses through a stack of progressively-sharper spec artifacts (intent → ACs → Gherkin → plan), each approved before the next — and adds DAE-specific elements: the Ready contract, autonomy levels, verification independence, the structured handoff / exit-criteria contract, the deterministic guardrail tools (`dae_*.py`), and integration with `crap-analyzer` for change-risk analysis.

This marketplace does not contain any code from empire-2025 or other upstream projects. It adapts the methodology for use as Claude Code plugins.

## Contributing

Contributions are welcome! Please open an issue or PR on [GitHub](https://github.com/swingerman/disciplined-agentic-engineering).

## License

[MIT](LICENSE)
