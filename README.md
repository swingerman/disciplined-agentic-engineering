# Disciplined Agentic Engineering — methodology marketplace for Claude Code

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code Marketplace](https://img.shields.io/badge/Claude%20Code-Marketplace-blueviolet)](https://github.com/swingerman/atdd)

> ⚠️ **Repo rename pending:** this marketplace is being renamed to `swingerman/disciplined-agentic-engineering`. The current URL (`swingerman/atdd`) will continue to work via GitHub's automatic redirect after the rename.

A Claude Code marketplace hosting the **Disciplined Agentic Engineering (DAE)** methodology kit — skills, agents, hooks, and commands that keep senior engineers in charge of architecture, behavior decisions, and verification while AI agents do the typing.

## What is Disciplined Agentic Engineering?

DAE is a methodology for **engineering-led AI development**. AI agents do the coding; senior engineers stay in charge of architecture, performance, and feature validation. Discipline lives in the contracts at every layer (charter → ACs → specs → plans → verification) and in the loop-aware skills that enforce them.

It's positioned in direct opposition to the failure mode of *loose-boundary, weak-check agentic engineering* — AI tools that produce code with no charter, no behavior contract, and no verification gates. DAE makes the boundaries explicit and the checks continuous.

**The headline outcome: semantic stability.** ATDD + mutation testing together form a *semantic firewall* — code can be refactored, extended, or modified by agents without the system's intended behavior drifting. This is the moat between DAE-built systems and "AI plops code around."

The methodology synthesizes four sources:
- **ATDD** (Robert C. Martin / Uncle Bob) — Given/When/Then specs as the behavior contract
- **Speckit** (GitHub) — Spec-driven agentic development; per-feature folder convention
- **Superpowers** (`spec-writer`) — Interview-driven spec generation
- **[Acceptance Pipeline Specification](https://github.com/unclebob/Acceptance-Pipeline-Specification)** (Uncle Bob, 2026) — Portable acceptance pipeline: Gherkin → JSON IR → generated tests → runner; mutation as IR-level sidecar

DAE sharpens these into a single workflow. The full methodology spec lives in [Notion](https://www.notion.so/3505ecdee0e281b297c8d9c07ec6dad6).

## Plugins in this marketplace

| Plugin | Purpose | Status |
|--------|---------|--------|
| **[`engineer`](engineer/)** | The DAE methodology kit — feature intake, AC discovery, planning, verification | v0.1 — early skills shipping |
| **[`atdd`](./)** | Acceptance Test Driven Development workflow with team orchestration and mutation testing | v0.4 — stable |
| **[`crap-analyzer`](crap-analyzer/)** | Change Risk Anti-Pattern analysis on changed code; part of DAE's Light Verify (Checkpoint 7) | v0.1 — migrated from `swingerman/skills` |

## Install the marketplace

```shell
/plugin marketplace add swingerman/atdd
```

Then install plugins individually:

```shell
/plugin install atdd@swingerman-atdd          # ATDD workflow + mutation testing
/plugin install engineer@swingerman-atdd      # DAE methodology kit
/plugin install crap-analyzer@swingerman-atdd # CRAP risk analysis on changed code
```

Or test locally by cloning:

```bash
git clone https://github.com/swingerman/atdd.git
claude --plugin-dir ./atdd
```

---

## The `engineer` plugin (DAE methodology)

The DAE pipeline operates on **features**. Each feature runs through 8 checkpoints:

```
1.5 Ready (feature.md)  →  2 ACs  →  3 Spec  →  4 Plan  →  5 Implement  →  6 Refactor  →  7 Light Verify  →  8 Hardening (optional)
```

Skills shipped today (v0.1):

| Skill | Command | Role |
|-------|---------|------|
| `discuss` | `/engineer.discuss` | Upstream funnel — divergent brainstorm; outcomes: drop / park / promote |
| `feature-init` | `/engineer.feature-init` | Mechanics — produces `feature.md` (Ready contract), folder, branch, tracker entry |
| `discover-acs` | `/engineer.discover-acs` | AC discovery interview — iterative passes (happy / edge / errors / cross-cutting); output: `acs.md` |

Skills coming next: `prime-context`, `plan`, `simplify`, `clarify`, `consistency-check`, `progress-log`, `feature-edit`, `onboard`.

### How DAE work flows

1. **`/engineer.discuss`** — brainstorm an idea; agent surfaces outcome (drop / park / promote)
2. **`/engineer.feature-init`** (invoked by discuss for park or promote) — creates the feature folder
3. **`/engineer.discover-acs`** — interview to enumerate behaviors; produces `acs.md`
4. **`/atdd:atdd`** (existing atdd plugin) — formalize ACs as Given/When/Then specs
5. *(planning, implementation, verification — design pending)*

Every agentic task ends with a structured handoff summary — the human knows when to re-engage after walking away.

### Methodology references

The full methodology (principles, handoff map, autonomy levels, foundation contracts) lives in Notion:

- **[DAE methodology page](https://www.notion.so/3505ecdee0e281b297c8d9c07ec6dad6)** — overview
- **[Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207)** — schemas, paths, conventions every skill consumes
- **[Discuss & Upstream Funnel Foundation](https://www.notion.so/35a5ecdee0e281eaa35fced0c4e23384)** — on-ramp contracts
- **[Tracker Integration Foundation](https://www.notion.so/35a5ecdee0e28168b1aee324c267fd13)** — driver abstraction, sync direction

---

## The `atdd` plugin (existing)

The original ATDD workflow plugin continues to ship as part of this marketplace. The `engineer` kit and `atdd` plugin are designed to interoperate: `engineer.discover-acs` produces ACs that `atdd:atdd` formalizes as Given/When/Then specs.

> "Specs will be co-authored by the humans and the AI, but with final approval, ferociously defended, by the humans." — Robert C. Martin

**Inspired by [Robert C. Martin's](https://en.wikipedia.org/wiki/Robert_C._Martin) (Uncle Bob) acceptance test approach from [empire-2025](https://github.com/unclebob/empire-2025).** The ideas, methodology, and key insights in the atdd plugin come directly from his work and public writings on Spec Driven Design (SDD) and ATDD.

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

Specs use an opinionated, human-readable Given/When/Then format:

```
;===============================================================
; User can register with email and password.
;===============================================================
GIVEN no registered users.

WHEN a user registers with email "bob@example.com" and password "secret123".

THEN there is 1 registered user.
THEN the user "bob@example.com" can log in.
```

**The Golden Rule:** specs describe what the system does, not how it does it.

| Bad (implementation leakage) | Good (domain language) |
|------------------------------|----------------------|
| `GIVEN the UserService has an empty userRepository.` | `GIVEN there are no registered users.` |
| `WHEN a POST request is sent to /api/users with JSON body.` | `WHEN a new user registers with email "bob@example.com".` |
| `THEN the database contains 1 row in the users table.` | `THEN there is 1 registered user.` |

### Team-based ATDD

For larger features, the `atdd-team` skill orchestrates an agent team — spec-writer, implementer, reviewer — through the ATDD phases. The team setup, prompts, and per-phase instructions are documented inside the skill itself; just say "build [feature] with a team."

The team integrates cleanly with existing teams via three options: extend (add ATDD roles to an existing team), replace (start fresh), or new team (parallel to existing).

### Mutation testing

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

The plugin's preferred approach is to **build a project-specific mutation tool** (small, TDD-built, walks the AST) following the approach in [empire-2025](https://github.com/unclebob/empire-2025/blob/master/docs/plans/2026-02-21-mutation-testing.md). For rapid setup, established frameworks (Stryker, mutmut, PIT, Stryker.NET, cargo-mutants, go-mutesting, mutant, Stryker4s) are also supported.

### atdd plugin components

| Component | Name | Purpose |
|-----------|------|---------|
| Skill | `atdd` | 7-step ATDD workflow: specs → pipeline → red/green → iterate |
| Skill | `atdd-team` | Orchestrates an agent team for ATDD |
| Skill | `atdd-mutate` | Mutation testing workflow |
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
│   ├── marketplace.json    # marketplace manifest (atdd + engineer)
│   └── plugin.json         # legacy single-plugin manifest (atdd at root)
├── agents/                 # atdd plugin agents
├── commands/               # atdd plugin commands
├── hooks/                  # atdd plugin hooks
├── skills/                 # atdd plugin skills (atdd, atdd-team, atdd-mutate)
├── engineer/               # engineer plugin (DAE methodology kit)
│   ├── .claude-plugin/
│   │   └── plugin.json
│   └── skills/
│       ├── discuss/
│       ├── feature-init/
│       └── discover-acs/
└── crap-analyzer/          # crap-analyzer plugin (CRAP risk analysis)
    ├── .claude-plugin/
    │   └── plugin.json
    └── skills/
        └── crap-analyzer/
```

## Attribution

The `atdd` plugin is an implementation of Robert C. Martin's (Uncle Bob) Acceptance Test Driven Development and Spec Driven Design methodology. The approach, insights, and principles come from:

- [empire-2025](https://github.com/unclebob/empire-2025) — Uncle Bob's project where this approach was developed and refined
- [Acceptance Pipeline Specification](https://github.com/unclebob/Acceptance-Pipeline-Specification) — Portable acceptance pipeline spec that DAE adopts
- His public writings and tweets on ATDD, SDD, and AI-assisted development

The `engineer` plugin synthesizes Uncle Bob's ATDD with Speckit's spec-driven structure, Superpowers' interview-driven spec writing, and adds DAE-specific elements (the Ready contract, autonomy levels, verification independence, agentic summary contract).

This marketplace does not contain any code from empire-2025 or other upstream projects. It adapts the methodology for use as Claude Code plugins.

## Contributing

Contributions are welcome! Please open an issue or PR on [GitHub](https://github.com/swingerman/atdd).

## License

[MIT](LICENSE)
