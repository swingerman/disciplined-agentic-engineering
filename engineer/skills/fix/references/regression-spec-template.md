# Regression Spec Template

Used in **Step 3 (Pin)** of the fix workflow. Write one spec file per `feature_refs` entry — not a shared spec across features.

Place at: `features/<slug>/fixes/<fix-slug>.spec.md` (or alongside the feature's existing spec stream).

---

## Template

```gherkin
# Regression spec for fix: <fix-slug>
# Feature: <feature-slug>
# Written: <date>
# Status on current code (pre-fix): RED — confirmed <YYYY-MM-DD>

Feature: <feature name>

  # This scenario pins the defect. It MUST fail (RED) on current code before
  # the fix is applied. Record the red-run output in pin_confirmation.

  Scenario: <concise description of the broken behavior>
    Given <system state that sets up the defect>
    When  <the action that triggers the bug>
    Then  <the behavior that should occur but does not>
```

---

## Minimal example

```gherkin
# Regression spec for fix: 2026-05-25-login-redirect-loop
# Feature: features/031-auth-session
# Written: 2026-05-25
# Status on current code (pre-fix): RED — confirmed 2026-05-25

Feature: Auth session management

  Scenario: Expired token does not cause redirect loop
    Given a user's session token has expired
    When  the user navigates to /dashboard
    Then  the user is redirected to /login exactly once
    And   the browser does not loop between /login and /dashboard
```

---

## RED-confirmation requirement

Before Step 3 (Pin) is complete, you MUST:

1. Run the spec against the current (un-fixed) code.
2. Confirm the test output shows a failure.
3. Record in `pin_confirmation.feature_refs[*].red_run`:
   - `result: red`
   - `command:` the exact command run
   - `output:` the failure line(s) from the test runner

If the spec passes (GREEN) on current code, it does not pin the bug. Redraft the scenario until RED before proceeding.
