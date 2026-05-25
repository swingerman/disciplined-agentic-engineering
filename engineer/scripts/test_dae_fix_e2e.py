#!/usr/bin/env python3
"""End-to-end scenario tests for dae_fix.py — full lifecycle through all gates."""
import os
import tempfile
import unittest

import dae_fix

_GOOD_HARDEN = {
    "bug_line_mutation_confirmed": True,
    "mutation_score": 0.92,
    "arch_check": "passed",
}

_RED_PIN = lambda feat, spec: {  # noqa: E731
    "feature_refs": [{"feature": feat, "spec_path": spec,
                      "red_run": {"result": "red", "timestamp": "2026-05-25T10:00:00Z"}}]
}


class FixE2EBase(unittest.TestCase):
    def _build_artifact(self, **kwargs) -> str:
        defaults = {"slug": "2026-05-25-test-fix", "title": "Test fix",
                    "severity": "medium", "blocks_user": False,
                    "workaround": "", "status": "investigating",
                    "repro": "steps", "expected": "ok", "actual": "fail"}
        defaults.update(kwargs)
        lines = ["---"]
        for k, v in defaults.items():
            lines.append(f"{k}: {'true' if v is True else ('false' if v is False else v)}")
        lines += ["---", ""]
        return "\n".join(lines)

    def _full_happy_rec(self, slug, feat, blocks_user=False, workaround=""):
        """Walk a fix from investigating to gap-analyzed, all gates green."""
        rec = dae_fix.parse_fix(self._build_artifact(
            slug=slug, title="Fix %s" % slug,
            blocks_user=blocks_user, workaround=workaround))
        rec["feature_refs"] = [feat]
        rec["pin_confirmation"] = _RED_PIN(feat, "features/%s/specs/s.spec.md" % feat)
        rec["fix_commits"] = ["abc"]
        rec["harden_results"] = dict(_GOOD_HARDEN)
        rec["gap_analysis"] = [{"category": "none", "finding": "clean"}]
        rec["followups"] = []
        rec["status"] = "gap-analyzed"
        return rec


class HappyPathScenarios(FixE2EBase):

    def test_scenario_1_auto_detect_happy_path(self):
        """Single-feature auto-match; advisory gap; full cycle to close."""
        rec = dae_fix.parse_fix(self._build_artifact(
            slug="2026-05-25-stale-cache", title="Stale cache on 401",
            severity="high", blocks_user=True, workaround="restart-the-app"))
        # Capture
        self.assertEqual(rec["status"], "investigating")
        self.assertFalse(dae_fix.close_ready(rec))

        # Investigate — auto match
        rec["feature_refs"] = ["042-auth-session"]
        rec["investigation"] = {"match_mode": "auto",
                                "candidates_considered": [{"feature": "042-auth-session",
                                                           "confidence": "strong"}]}
        rec["status"] = "pinned-pending"
        self.assertEqual(rec["investigation"]["match_mode"], "auto")

        # Pin — RED
        rec["pin_confirmation"] = _RED_PIN("042-auth-session",
                                           "features/042-auth-session/specs/cache.spec.md")
        rec["status"] = "pinned"
        self.assertTrue(dae_fix.is_pin_confirmed(rec))
        self.assertFalse(dae_fix.close_ready(rec))  # not hardened yet

        # Fix → Verify
        rec["fix_commits"] = ["deadbeef"]
        rec["status"] = "verified"
        self.assertFalse(dae_fix.close_ready(rec))

        # Harden
        rec["harden_results"] = dict(_GOOD_HARDEN)
        rec["status"] = "hardened"
        self.assertTrue(dae_fix.is_hardened(rec))
        self.assertFalse(dae_fix.close_ready(rec))  # gap_analysis empty

        # Gap analysis — one advisory finding
        rec["gap_analysis"] = [{"category": "missing_ac",
                                 "finding": "AC absent for stale-cache scenario",
                                 "followup": {"action": "Add AC", "target": "acs.md"}}]
        rec["status"] = "gap-analyzed"
        self.assertEqual(dae_fix.blocker_categories(rec), [])
        self.assertFalse(dae_fix.has_unresolved_blockers(rec))
        self.assertTrue(dae_fix.close_ready(rec))

        # Close + consolidation
        rec["status"] = "closed"
        self.assertTrue(dae_fix.close_ready(rec))
        entries = dae_fix.render_consolidation_entries(rec)
        self.assertEqual(len(entries), 1)
        self.assertIn("missing_ac", entries[0])

    def test_scenario_2_confirmed_path(self):
        """Two candidates; user confirms one; match_mode=confirmed; full cycle."""
        rec = dae_fix.parse_fix(self._build_artifact(
            slug="2026-05-25-login-500", title="Login 500 under load",
            severity="critical", blocks_user=False, workaround="retry"))
        # Investigate — manual confirmed
        rec["feature_refs"] = ["055-login-flow"]
        rec["investigation"] = {
            "match_mode": "confirmed",
            "candidates_considered": [{"feature": "055-login-flow", "confidence": "strong"},
                                       {"feature": "021-rate-limiter", "confidence": "weak"}],
        }
        rec["status"] = "pinned-pending"
        self.assertEqual(rec["investigation"]["match_mode"], "confirmed")
        self.assertFalse(dae_fix.is_pin_confirmed(rec))  # no pin yet

        # Pin → Fix → Harden → Gap
        rec["pin_confirmation"] = _RED_PIN("055-login-flow",
                                           "features/055-login-flow/specs/login.spec.md")
        rec["status"] = "pinned"
        self.assertTrue(dae_fix.is_pin_confirmed(rec))
        rec["fix_commits"] = ["cafebabe"]
        rec["harden_results"] = dict(_GOOD_HARDEN)
        rec["gap_analysis"] = [{"category": "none", "finding": "Spec already covered it."}]
        rec["status"] = "gap-analyzed"
        self.assertFalse(dae_fix.has_unresolved_blockers(rec))
        self.assertTrue(dae_fix.close_ready(rec))


class GateRejectionScenarios(FixE2EBase):

    def test_scenario_3_pin_gate_rejects_green_spec(self):
        """pin_confirmation result=green → is_pin_confirmed False; close_ready False."""
        rec = dae_fix.parse_fix(self._build_artifact(
            slug="2026-05-25-flaky-token", title="Flaky token refresh"))
        rec["feature_refs"] = ["033-token-service"]
        rec["pin_confirmation"] = {"feature_refs": [{
            "feature": "033-token-service", "spec_path": "s.spec.md",
            "red_run": {"result": "green", "timestamp": "2026-05-25T11:00:00Z"}}]}
        rec["status"] = "pinned"
        self.assertFalse(dae_fix.is_pin_confirmed(rec))

        # Even with all other gates green, close_ready must be False
        rec["harden_results"] = dict(_GOOD_HARDEN)
        rec["gap_analysis"] = [{"category": "none", "finding": "trivial"}]
        rec["status"] = "gap-analyzed"
        self.assertFalse(dae_fix.close_ready(rec))

    def test_scenario_4_multi_feature_pin_per_feature(self):
        """Two feature_refs; partial RED → False; both RED → True; full cycle."""
        rec = dae_fix.parse_fix(self._build_artifact(
            slug="2026-05-25-auth-race", title="Auth-session race",
            blocks_user=True, workaround="none"))
        rec["feature_refs"] = ["011-auth", "022-session"]
        rec["status"] = "pinned-pending"
        self.assertFalse(dae_fix.is_pin_confirmed(rec))

        # Partial: auth RED, session GREEN → still False
        rec["pin_confirmation"] = {"feature_refs": [
            {"feature": "011-auth", "spec_path": "auth.spec.md",
             "red_run": {"result": "red", "timestamp": "2026-05-25T10:00:00Z"}},
            {"feature": "022-session", "spec_path": "session.spec.md",
             "red_run": {"result": "green", "timestamp": "2026-05-25T10:05:00Z"}},
        ]}
        self.assertFalse(dae_fix.is_pin_confirmed(rec))

        # Fix session to RED → both confirmed
        rec["pin_confirmation"]["feature_refs"][1]["red_run"]["result"] = "red"
        rec["status"] = "pinned"
        self.assertTrue(dae_fix.is_pin_confirmed(rec))

        # Harden + gap analysis (one finding per feature; blocks_user+none → all blockers)
        rec["harden_results"] = dict(_GOOD_HARDEN)
        rec["gap_analysis"] = [
            {"category": "incomplete_spec", "finding": "Race coverage missing in auth",
             "followup": {"action": "Add race scenario", "target": "auth.spec.md"}},
            {"category": "missing_ac", "finding": "Session concurrency AC missing",
             "followup": {"action": "Add AC", "target": "session-acs.md"}},
        ]
        rec["status"] = "gap-analyzed"
        blockers = dae_fix.blocker_categories(rec)
        self.assertIn("incomplete_spec", blockers)
        self.assertIn("missing_ac", blockers)
        self.assertTrue(dae_fix.has_unresolved_blockers(rec))
        self.assertFalse(dae_fix.close_ready(rec))

        # Apply all blocker followups → close_ready True
        rec["followups"] = [{"category": "incomplete_spec", "status": "applied"},
                            {"category": "missing_ac", "status": "applied"}]
        self.assertFalse(dae_fix.has_unresolved_blockers(rec))
        self.assertTrue(dae_fix.close_ready(rec))

    def test_scenario_9_bug_line_mutation_gate_rejects(self):
        """bug_line_mutation_confirmed=False → is_hardened False; flip → True."""
        rec = dae_fix.parse_fix(self._build_artifact(
            slug="2026-05-25-null-deref", title="Null deref in profile"))
        rec["feature_refs"] = ["077-profile"]
        rec["pin_confirmation"] = _RED_PIN("077-profile", "profile.spec.md")
        rec["status"] = "pinned"
        self.assertTrue(dae_fix.is_pin_confirmed(rec))

        # Harden with mutation gate failing
        rec["harden_results"] = {"bug_line_mutation_confirmed": False,
                                 "mutation_score": 0.88, "arch_check": "passed"}
        rec["status"] = "hardened"
        self.assertFalse(dae_fix.is_hardened(rec))

        rec["gap_analysis"] = [{"category": "none", "finding": "trivial"}]
        rec["status"] = "gap-analyzed"
        self.assertFalse(dae_fix.close_ready(rec))

        # Fix mutation gate
        rec["harden_results"]["bug_line_mutation_confirmed"] = True
        self.assertTrue(dae_fix.is_hardened(rec))
        self.assertTrue(dae_fix.close_ready(rec))


class BlockerRuleScenarios(FixE2EBase):

    def test_scenario_5_loose_fix_no_feature(self):
        """Empty feature_refs → is_pin_confirmed True; no_feature gap; list_open_fixes works."""
        artifact_text = self._build_artifact(
            slug="2026-05-25-orphan-js-error", title="Orphan JS error",
            severity="low", blocks_user=False, workaround="refresh")
        rec = dae_fix.parse_fix(artifact_text)
        rec["feature_refs"] = []
        rec["investigation"] = {"match_mode": "none", "candidates_considered": []}
        rec["status"] = "pinned-pending"
        # Empty feature_refs → auto-passes pin gate
        rec["status"] = "pinned"
        self.assertTrue(dae_fix.is_pin_confirmed(rec))

        rec["fix_commits"] = ["abcdef00"]
        rec["harden_results"] = dict(_GOOD_HARDEN)
        rec["gap_analysis"] = [{"category": "no_feature",
                                 "finding": "Code is unassigned to any feature.",
                                 "followup": {"action": "Create feature",
                                              "target": ".engineer/features/"}}]
        rec["status"] = "gap-analyzed"
        self.assertEqual(dae_fix.blocker_categories(rec), [])
        self.assertFalse(dae_fix.has_unresolved_blockers(rec))
        self.assertTrue(dae_fix.close_ready(rec))

        # list_open_fixes: appears while open; disappears when closed
        with tempfile.TemporaryDirectory() as tmpdir:
            fixes_dir = os.path.join(tmpdir, ".engineer", "fixes")
            os.makedirs(fixes_dir)
            fix_path = os.path.join(fixes_dir, "2026-05-25-orphan-js-error.md")
            with open(fix_path, "w") as f:
                f.write(artifact_text)
            open_list = dae_fix.list_open_fixes(tmpdir)
            self.assertIn("2026-05-25-orphan-js-error", [r["slug"] for r in open_list])
            # overwrite as closed
            with open(fix_path, "w") as f:
                f.write(artifact_text.replace("status: investigating", "status: closed"))
            self.assertNotIn("2026-05-25-orphan-js-error",
                             [r["slug"] for r in dae_fix.list_open_fixes(tmpdir)])

    def test_scenario_6_blocker_finding_blocks_close(self):
        """architecture_violation with open followup → close False; applied → True."""
        rec = self._full_happy_rec("2026-05-25-cross-layer", "058-cache")
        rec["gap_analysis"] = [{"category": "architecture_violation",
                                 "finding": "Cache imports auth client directly",
                                 "followup": {"action": "Forbid cross-layer", "target": "charter.md"}}]
        rec["followups"] = [{"category": "architecture_violation", "status": "open"}]
        self.assertTrue(dae_fix.is_pin_confirmed(rec))
        self.assertTrue(dae_fix.is_hardened(rec))
        self.assertIn("architecture_violation", dae_fix.blocker_categories(rec))
        self.assertTrue(dae_fix.has_unresolved_blockers(rec))
        self.assertFalse(dae_fix.close_ready(rec))

        rec["followups"][0]["status"] = "applied"
        self.assertFalse(dae_fix.has_unresolved_blockers(rec))
        self.assertTrue(dae_fix.close_ready(rec))

    def test_scenario_7_user_blocking_promotes_advisory_to_blocker(self):
        """blocks_user=True+workaround=none promotes inadequate_verification to blocker."""
        rec = self._full_happy_rec("2026-05-25-checkout-broken", "099-checkout",
                                   blocks_user=True, workaround="none")
        rec["gap_analysis"] = [{"category": "inadequate_verification",
                                 "finding": "E2E suite missed full checkout",
                                 "followup": {"action": "Add E2E scenario",
                                              "target": "checkout.spec.md"}}]
        # blocks_user+none → inadequate_verification is a blocker
        self.assertIn("inadequate_verification", dae_fix.blocker_categories(rec))
        self.assertTrue(dae_fix.has_unresolved_blockers(rec))
        self.assertFalse(dae_fix.close_ready(rec))

        rec["followups"] = [{"category": "inadequate_verification", "status": "applied"}]
        self.assertFalse(dae_fix.has_unresolved_blockers(rec))
        self.assertTrue(dae_fix.close_ready(rec))

        # Contrast: same gap but WITH a workaround → inadequate_verification is advisory only
        rec2 = self._full_happy_rec("2026-05-25-checkout-broken", "099-checkout",
                                    blocks_user=True, workaround="use safari")
        rec2["gap_analysis"] = [
            {"category": "inadequate_verification", "finding": "E2E gap"},
            {"category": "architecture_violation", "finding": "Layer breach"},
        ]
        blockers2 = dae_fix.blocker_categories(rec2)
        self.assertNotIn("inadequate_verification", blockers2)
        self.assertIn("architecture_violation", blockers2)

    def test_scenario_8_trivial_fix(self):
        """gap_analysis=[{category:none}]; all gates green; close_ready True."""
        rec = dae_fix.parse_fix(self._build_artifact(
            slug="2026-05-25-typo-error-msg", title="Typo in payment error",
            severity="low", blocks_user=False, workaround="ignore"))
        # No feature ownership needed for trivial text fix
        rec["feature_refs"] = []
        rec["status"] = "pinned"
        self.assertTrue(dae_fix.is_pin_confirmed(rec))  # empty refs → auto-pass

        rec["fix_commits"] = ["textfix01"]
        rec["harden_results"] = dict(_GOOD_HARDEN)
        rec["status"] = "hardened"
        self.assertTrue(dae_fix.is_hardened(rec))

        rec["gap_analysis"] = [{"category": "none",
                                 "finding": "Trivial typo; no methodology gap."}]
        rec["status"] = "gap-analyzed"
        self.assertEqual(dae_fix.blocker_categories(rec), [])
        self.assertFalse(dae_fix.has_unresolved_blockers(rec))
        self.assertTrue(dae_fix.close_ready(rec))

        # category=none is "explicitly nothing to learn" — no consolidation entry
        entries = dae_fix.render_consolidation_entries(rec)
        self.assertEqual(entries, [])

        # Closure render sanity
        closure = dae_fix.render_fix_closure_entry(rec, {"advisory": 0, "blocker_applied": 0})
        self.assertIn("2026-05-25-typo-error-msg", closure)
        self.assertIn("user-blocking: no", closure)


if __name__ == "__main__":
    unittest.main()
