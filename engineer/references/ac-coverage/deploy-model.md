# Deploy model coverage checklist

Use when a feature touches how the app gets deployed — staging environment, production, infra, hosting choice, CI/CD. Surface as a batched opt-in/out during discover-acs Step 3 (cross-cutting pass). nexthq took two passes to settle the right deploy-model question; this checklist makes the decisions explicit upfront.

## Hosting target

- [ ] **Decided: which platform** (Cloud Run / App Engine / Firebase Hosting / Vercel / Fly / bare VM / Kubernetes). Document the rationale (cost, scaling needs, latency, team familiarity).
- [ ] **Multi-region or single-region** — if multi, what's the failover model?
- [ ] **CDN in front** — yes/no; if yes, what's cached and what's pass-through?

## Environment topology

- [ ] **Environments exist:** local-dev, staging, production. (Add preview/PR-deploy if applicable.)
- [ ] **Environment isolation:** separate cloud projects / accounts / databases — not shared.
- [ ] **Staging is production-like** in topology (same components, smaller scale) so deploy-time bugs surface before prod.
- [ ] **Secrets per environment** — no shared secrets between staging and prod.

## Deploy mechanics

- [ ] **CI/CD pipeline:** GitHub Actions / GitLab CI / Cloud Build / Jenkins. Pipeline defined-as-code in the repo.
- [ ] **Build artifact** is immutable and traceable to a commit SHA.
- [ ] **Deploy is automated** on merge to main (continuous deploy) OR gated on manual approval — decide which.
- [ ] **Rollback path:** automatic (failed health check) and manual (deploy previous artifact). Time-to-rollback measured.
- [ ] **Database migrations** run as part of deploy or separately — decide. If separately, define the ordering rule (migrate-before-deploy or migrate-after).

## Validation method

- [ ] **Post-deploy health check** — what makes it green/red? (HTTP 200 on a specific path / synthetic transaction / dashboard metric.)
- [ ] **Canary or progressive rollout** for production — `5% for 24h, watch dashboard X` style. If not, document that deploys are all-or-nothing.
- [ ] **Smoke tests** run against the deployed environment (not just the build).
- [ ] **Acceptance test suite** runs against staging on every deploy — or is staging-deploy itself blocked by it.

## Observability

- [ ] **Logging** centralized; can a developer find the logs for a request by trace ID within 5 minutes?
- [ ] **Metrics:** request rate, latency, error rate dashboards exist before launch.
- [ ] **Alerting** on error-rate spike and latency-p99 regression, routed to a channel that someone watches.
- [ ] **Tracing** end-to-end if the system has more than 3 services.

## Cost / quotas

- [ ] **Cost ceiling per environment** documented; billing alerts configured.
- [ ] **Rate limits / quotas** for external services (Stripe, SendGrid, OAuth providers) — what happens when hit?

## When NOT to use this checklist

- Feature is a pure refactor with no deploy-surface change (the existing deploy model already handles it).
- Library / SDK release — different distribution model.
