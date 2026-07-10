# Tracker / roadmap driver pre-flight

The tracker and roadmap driver layer (`dae_tracker_local.py`, `dae_roadmap.py`,
and the MCP/CLI/API channels behind them) has assumed capabilities it never
probed — and paid for it every session: a Notion host whose data tools need a
plan tier the workspace doesn't have, a Confluence host chosen on Jira-only
scopes, a Jira source of truth with no driver. Pre-flight fixes the class.

## Rule — probe before you commit a host

Before writing a tracker/roadmap `type:` (host) into `manifest.yml`, **pre-flight
it**: confirm auth, connectivity, AND plan-tier of the specific product, not just
that *an* MCP is connected. If any fails, fall back (to `local`, or a reachable
alternative) and tell the human exactly what to connect to enable the richer host
later — never write a host DAE can't actually drive.

- **Auth + connectivity** — make one cheap read against the exact host (not a
  sibling product). A connected Atlassian MCP with only Jira scopes will 404 /
  deny on Confluence calls; verify the *product you're about to commit*.
- **Plan tier** — some hosts gate features by billing tier (see Notion below).
  Probe the tier-gated call once; if it 400s, record the fallback, don't commit
  the host as if the call worked.

## Known host limitations (codified so they aren't rediscovered)

- **Notion — Business-plan gate.** The Notion data-source / view / SQL-query
  tools return `400 … requires a Business plan` on lower tiers. On a non-Business
  workspace, drive Notion via `notion-search` + page reads instead of the
  data-source query tools. Record `tracker.notion.tier` (or a note) at onboard so
  `progress-log` / `next` don't rediscover the 400 each run.
- **Atlassian — product scope.** `type: confluence` chosen while the OAuth grant
  covers only Jira produces 404s and re-auth prompts. Pick the host that matches
  the granted scope, or request the scope first.
- **Jira — driver reserved.** `dae_roadmap.py` / `dae_tracker_local.py` do not yet
  implement a Jira driver; when Jira is the source of truth, DAE falls back to
  `local` (`.engineer/inbox.md`). This is a **declared limitation, not a bug** —
  the driver is the place to implement it (mirror the local driver's interface).

## Who runs it

- `engineer:onboard` — Steps 5 (tracking) and 5b (roadmap): pre-flight the chosen
  host here, before writing it into the manifest.
- `engineer:onboard` gap-check + `engineer:next` — if a committed host later goes
  unreachable or tier-gated, surface it rather than failing silently.

## References

- `${CLAUDE_PLUGIN_ROOT}/references/tracker.md` — tracker drivers + `TrackedFeature`
- `${CLAUDE_PLUGIN_ROOT}/references/roadmap.md` — roadmap drivers + reachability precondition
