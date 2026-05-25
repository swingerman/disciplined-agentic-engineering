# Gap Analysis Categories

Closed vocabulary for Step 8 ("why didn't we catch it?") of the fix workflow. Use exactly these strings in `gap_analysis[*].category`. Each finding gets one category.

---

## Blocker rule

A finding **blocks close** when:

1. `category: architecture_violation` — always a blocker, regardless of severity or workaround.
2. The fix has `blocks_user: true` AND `workaround: "none"` — ALL findings on this fix are promoted to blockers.

Otherwise, findings are advisory. Advisory followups land in `.engineer/consolidation.md` tagged with the fix slug.

---

## Categories

### `missing_ac`
The behavior that broke was never captured as an acceptance criterion. The feature's `acs.md` has no AC covering this scenario. **Phase leaked: discover-acs (CP2).** Typical followup: `amend_ac` — add the missing AC to `acs.md` and propagate downstream. Advisory unless promoted by the blocker rule.

### `unspecced_ac`
The AC exists in `acs.md` but was never turned into a Given/When/Then scenario in `spec.md`. The behavior was acknowledged but not formally tested. **Phase leaked: atdd (CP3).** Typical followup: `extend_spec` — add the missing scenario to `spec.md`. Advisory unless promoted.

### `incomplete_spec`
A spec scenario exists but it was too coarse to catch the defect — wrong boundary, missing step, or an assumption baked in that masked the failure. **Phase leaked: atdd (CP3).** Typical followup: `extend_spec` or `tighten_spec`. Advisory unless promoted.

### `inadequate_verification`
The spec and ACs were sufficient, but the test or CI check was not run, was skipped, or was configured in a way that let the defect pass. **Phase leaked: verify (CP7) or harden (CP8).** Typical followup: `add_verification` — add the missing test run to the pipeline or fix the CI configuration. Advisory unless promoted.

### `architecture_violation`
The defect was caused by code that violated a constraint in `CHARTER.md` or the feature's `plan.md` — the architecture was right, the implementation departed from it. **Phase leaked: plan (CP4) or implement (CP5).** Typical followup: `tighten_arch_check` — amend the arch-check criteria so future deviations are caught. **Always a blocker.** Must be resolved inline before close.

### `external_dependency`
The bug originated in a third-party library, platform change, or environment shift outside the feature's control. DAE methodology did not and could not have caught it. **No phase leaked.** Typical followup: add a monitoring or alerting note. Advisory; no methodology amendment needed.

### `no_feature`
The broken code does not belong to any tracked DAE feature — it predates the methodology or lives outside the pipeline. No gap in the feature pipeline; consider onboarding the code area. **No phase leaked.** Typical followup: `onboard` — create a feature to bring the code area under coverage. Advisory.

### `none`
No gap found — the methodology worked correctly, but the bug slipped through due to an unforeseeable combination or environment-only issue. Record this explicitly rather than leaving `gap_analysis` empty: `{category: none, finding: "No methodology gap identified — <reason>."}`. The close gate requires `gap_analysis` to be non-empty; `none` satisfies it.
