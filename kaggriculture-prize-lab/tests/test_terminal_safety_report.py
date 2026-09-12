"""Focused pure-data P2c report tests: no policy or engine imports."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_terminal_safety as report


class TerminalSafetyReportTests(unittest.TestCase):
    def test_legacy_raw_match_does_not_invent_canonical_hash(self):
        old = report.fingerprint_info({"sha256": "same"})
        new = report.fingerprint_info({"sha256": "same", "gameplay_sha256": "canonical"})
        comparison = report.compare_fingerprints(old, new)
        self.assertTrue(comparison["raw_fingerprint_matched"])
        self.assertFalse(comparison["canonical_comparison_available"])
        self.assertIsNone(comparison["canonical_fingerprint_matched"])

    def test_canonical_match_and_raw_mismatch_are_distinct(self):
        left = report.fingerprint_info({"sha256": "raw-a", "gameplay_sha256": "same"})
        right = report.fingerprint_info({"sha256": "raw-b", "gameplay_sha256": "same"})
        comparison = report.compare_fingerprints(left, right)
        self.assertFalse(comparison["raw_fingerprint_matched"])
        self.assertTrue(comparison["canonical_fingerprint_matched"])

    def test_canonical_mismatch_is_unverified_not_filtered(self):
        left = report.fingerprint_info({"sha256": "a", "gameplay_sha256": "a"})
        right = report.fingerprint_info({"sha256": "b", "gameplay_sha256": "b"})
        self.assertEqual(report.compare_fingerprints(left, right)["canonical_status"], "UNVERIFIED_MISMATCH")

    def test_profile_cpu_zero_is_not_missing(self):
        profile = [{"step": step, "wall_ms": 1, "cpu_ms": 0} for step in range(719)]
        profile[700]["wall_ms"] = 1500
        summary = report.profile_summary(profile, clean=True)
        self.assertEqual(summary["windows"]["all"]["cpu_ms"]["sum"], 0)
        self.assertEqual(summary["windows"]["terminal_696_to_718"]["inner_calls_over_1000ms"], 1)
        self.assertEqual(summary["windows"]["all"]["inner_wall_excess_above_1s_seconds_proxy"], .5)
        self.assertEqual(summary["windows"]["all"]["zero_cpu_samples"], 719)

    def test_incomplete_profile_allowed_only_for_unclean_row(self):
        profile = [{"step": 0, "wall_ms": 1, "cpu_ms": 0}]
        self.assertFalse(report.profile_summary(profile, clean=False)["all_719_steps_present"])
        with self.assertRaises(report.parent.EvidenceError):
            report.profile_summary(profile, clean=True)

    def test_duplicate_profile_step_rejected(self):
        with self.assertRaises(report.parent.EvidenceError):
            report.profile_summary([{"step": 0, "wall_ms": 1, "cpu_ms": 0}] * 2, clean=False)

    def test_diagnostics_retain_explicit_zero(self):
        result = report.exact_counts({"guard": 0, "reconciled": 23}, "test")
        self.assertEqual(result, {"guard": 0, "reconciled": 23})
        with self.assertRaises(report.parent.EvidenceError):
            report.exact_counts({"guard": -1}, "test")

    def test_safety_effect_not_confused_with_baseline_effect(self):
        variants = {}
        for label, margin in {"base": 100, "A": 110, "B": 103, "AB": 120, "Bsafe": 104, "ABsafe": 122}.items():
            row = {field: 0 for field in report.parent.SCALARS}
            row.update(margin=margin, own_cash=margin, sale_revenue_total=margin, points=1)
            row["flows"] = {field: {} for field in report.parent.FLOW_FIELDS}
            row["opponent_flows"] = copy.deepcopy(row["flows"])
            variants[label] = row
        effects = {name: report.parent.contrast(variants, weights) for name, weights in report.CONTRASTS.items()}
        self.assertEqual(effects["ABsafe_minus_ABv1"]["margin"], 2)
        self.assertEqual(effects["ABsafe_minus_base"]["margin"], 22)
        self.assertEqual(effects["safe_interaction_ABsafe_minus_A_minus_Bsafe_plus_base"]["margin"], 8)
        self.assertTrue(all(effect["cash_identity_residual"] == 0 for effect in effects.values()))

    def test_final_report_rejects_partial_cases(self):
        with self.assertRaises(report.parent.EvidenceError):
            report.build_report([], {})

    def test_changed_case_detects_opponent_product_mix_with_unchanged_total(self):
        effect = {field: 0 for field in report.parent.SCALARS}
        effect.update(flows={field: {} for field in report.parent.FLOW_FIELDS},
                      opponent_flows={field: {} for field in report.parent.FLOW_FIELDS})
        self.assertFalse(report.economic_effect_changed(effect))
        effect["opponent_flows"]["actual_sale_units"] = {"WHEAT": 1, "MILK": -1}
        self.assertTrue(report.economic_effect_changed(effect))


if __name__ == "__main__":
    unittest.main()
