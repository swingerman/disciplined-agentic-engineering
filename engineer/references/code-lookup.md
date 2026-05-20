# Code lookup — LSP-first convention

When a DAE skill needs to look up code — find a definition, find references,
survey symbols, check types — it should **prefer LSP** (semantic, language-aware)
over grep or AST parsing **when an LSP capability is available** in the
environment, and **fall back gracefully** when it is not.

## Use LSP for

- **find-references** — who calls this function / uses this symbol?
- **find-definitions** — where is X declared?
- **workspace-symbols** — what symbols exist across the project?
- **document-symbols** — what's in this file?
- **hover / type info** — what is X's signature / type?
- **call-hierarchy** — what calls X (incoming), what does X call (outgoing)?
- **find-implementations** — what implements this interface / abstract method?

## Don't use LSP for

- **Text-pattern matches** — use `grep` / `rg`.
- **Dependency layering, forbidden patterns, file naming, file size** — use
  `dae_arch.py` (already deterministic and language-aware for imports).
- **Cycle detection** — use `dae_arch.py`'s `check_cycles`.
- **Text duplication** — use `dae_dup.py`.
- **Frontmatter / manifest parsing** — use `dae_resolve.py`.

## Detection

At skill-start, check the agent's available tool list for an LSP capability —
an MCP tool whose name or surface exposes language-server-style operations
(e.g. a tool named `LSP`, or one with operations like `findReferences`,
`workspaceSymbols`). If present, note "LSP available"; if absent, note "LSP
unavailable, falling back to grep/AST."

## Fallback ladder

When an operation is needed, use the first option that's available:

1. **LSP** (semantic, language-aware).
2. **Existing `dae_*.py` AST tools** — for the specific operations they cover
   (imports via `dae_arch.extract_imports`, etc.). These remain authoritative
   for the layering/structure use cases.
3. **grep / Read** — text patterns and structural reading.

**Never block on LSP absence.** The LLM lens is always the floor — a subagent
asked to find "missed existing utilities" can still operate via grep + Read if
LSP isn't around, just less precisely.

## Subagent dispatch

When a skill dispatches a subagent that will do code lookup, the dispatch
prompt should pass:

1. The LSP-first preference (so the subagent doesn't default to grep).
2. The parent's detection result — "LSP is available; use it" or "LSP is
   unavailable; fall back to grep + Read."

This prevents the subagent from re-detecting (which may give a different
answer from a fresh context that hasn't loaded the MCP) and from claiming LSP
is unavailable when it just hasn't been told to look.
