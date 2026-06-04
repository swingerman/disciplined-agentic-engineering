# AC coverage checklists

Domain-aware checklists for `engineer:discover-acs`. The discover-acs interview formalizes what the human raises — but the human is the bottleneck for "what could go wrong that we haven't thought of?" image-titler shipped a public-site feature with no default OG-image AC; the gap was only spotted manually after release. nexthq took two passes to land the right deploy-model question.

These checklists answer **"for this kind of surface, what's commonly missed?"** Each is a short menu the agent MUST surface during discover-acs Step 3 (the four-pass interview), grouped under the most relevant pass.

## How discover-acs uses these

1. After Step 2 (Load), the agent scans `feature.md` for surface signals (web/HTTP, OAuth/auth, deploy, mobile, data-migration, …).
2. For each matched surface, the agent reads the corresponding checklist file in this directory.
3. During Step 3's interview, the agent surfaces the checklist's items as a *batched opt-in/out* — one `AskUserQuestion` per checklist, listing items, multi-select. The human ticks "yes, this matters" / "no, out of scope".
4. Each ticked item becomes an AC candidate in Step 6 / Step 7.

The checklists do **not** auto-create ACs without confirmation — the human always gets the final say. They prevent the failure mode where a surface has well-known concerns and no one mentioned them.

## Available checklists

| File | Surface signal in `feature.md` |
|---|---|
| `web-seo.md` | Public web pages, HTML output, mention of "site", "page", "marketing" |
| `auth-oauth.md` | Mention of "login", "OAuth", "auth", "session", "token", "SSO" |
| `deploy-model.md` | Mention of "deploy", "staging", "production", "infra", "hosting" |
| `accessibility.md` | UI feature targeting humans (not API-only) |
| `data-migration.md` | Schema change, data backfill, "migrate", "rename column" |

Add new checklists here as patterns recur. Each should be tight — a list of decisions, not prose — so the agent can paste them into AskUserQuestion options without summarization.
