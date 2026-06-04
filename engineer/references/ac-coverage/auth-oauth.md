# Auth / OAuth coverage checklist

Use when a feature touches authentication, OAuth flows, sessions, tokens, or SSO. Surface as a batched opt-in/out during discover-acs Step 3 (errors-and-security + cross-cutting passes).

## Happy path

- [ ] **Sign-in succeeds for valid credentials / valid OAuth grant.**
- [ ] **Session persists** across page reloads / app restarts within the configured TTL.
- [ ] **Sign-out** clears session state and forces re-auth on protected routes.

## Edge / error

- [ ] **Expired token mid-session** — graceful re-auth prompt, no data loss in the active form.
- [ ] **Expired refresh token** — clean redirect to sign-in, no infinite refresh loop.
- [ ] **Concurrent sign-in attempts** from two tabs / two devices — defined behavior (both work / second invalidates first / etc).
- [ ] **OAuth callback with `error=access_denied`** — user-friendly message, return to sign-in.
- [ ] **OAuth callback with mismatched `state`** — rejected as a CSRF attempt.
- [ ] **Invalid / tampered session cookie** — rejected, forced re-auth.
- [ ] **Network failure during OAuth callback** — retry path, no half-authenticated state.

## Security

- [ ] **Cookies are `Secure`, `HttpOnly`, `SameSite=Lax`/`Strict`** as appropriate.
- [ ] **No tokens in URL query strings** that get logged (server access logs, browser history).
- [ ] **CSRF protection** on all state-changing requests.
- [ ] **Rate limiting** on sign-in attempts (brute-force protection).
- [ ] **Account enumeration** — error messages don't reveal whether an email is registered.
- [ ] **OAuth scope minimization** — request only the scopes actually used.

## Cross-cutting

- [ ] **Audit log** for sign-in, sign-out, failed-attempt, scope-grant events.
- [ ] **Session inactivity timeout** behavior is explicit (slide / hard cutoff / silent refresh).
- [ ] **Multiple OAuth providers** — account-linking rules if a user signs in via different providers with the same email.
- [ ] **OAuth provider downtime** — graceful degradation message ("X is unavailable, try again or use Y").
- [ ] **Token refresh** is silent and doesn't interrupt active requests.

## When NOT to use this checklist

- API-key authentication only (no user sessions).
- Service-to-service auth with mTLS or signed requests.
