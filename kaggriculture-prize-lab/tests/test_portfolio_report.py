"""Pure in-memory JSON fixtures: no strategies, simulations or disk outputs."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import report_portfolio_probes as report


class MemoryStore:
    def __init__(self):
        self.files, self.verified = {}, False

    def put(self, name, value):
        self.files[name] = json.dumps(value, allow_nan=False).encode()

    def read(self, name):
        return self.files[name]

    def get(self, name):
        return json.loads(self.files[name])

    def verify_unchanged(self):
        self.verified = True


class PortfolioReportTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.freeze_path = "results/portfolio-20260912/freeze.json"
        self.result_dir = "results/portfolio-20260912/development"
        source_hashes = {}
        for key, name in report.SOURCE_PATHS.items():
            self.store.files[name] = ("inert audit fixture " + key).encode()
            source_hashes[key] = report.digest_bytes(self.store.files[name])
        self.store.files[report.BASELINE_PATH] = b"inert baseline fixture - never executed"
        base = report.digest_bytes(self.store.files[report.BASELINE_PATH])
        self.constants = patch.multiple(report, BASELINE_HASH=base, ENGINE_HASH=source_hashes["engine_sha256"])
        self.constants.start()
        self.addCleanup(self.constants.stop)
        opponents = {}
        for name in report.OPPONENTS:
            path = report.BASELINE_PATH if name == "cok" else f"fixtures/{name}.txt"
            if name != "cok":
                self.store.files[path] = ("inert " + name).encode()
            opponents[name] = {"path": path, "sha256": report.digest_bytes(self.store.files[path]), "family": report.FAMILIES[name]}
        self.store.put("opponent-pool-p2.json", {"opponents": [dict(v, name=k) for k, v in opponents.items() if k != "arlene"]})
        self.store.put("opponent-pool-p2-stress.json", {"opponents": [dict(opponents["arlene"], name="arlene")]})
        variants = {}
        for arm in report.VARIANTS:
            path = f"experiments/track-portfolio-20260912/{arm}/main.py"
            self.store.files[path] = ("in-memory opaque bytes " + arm).encode()
            variants[arm] = report.digest_bytes(self.store.files[path])
        self.store.put("reports/p3-prefix-audit.json", {"approved": True})
        freeze = {"schema": "portfolio-track-freeze-v1", "split": "development", "seeds": list(report.SEEDS),
                  "max_new_games": 96, "feature_schema_sha256": report.schema_digest(), "opponents": opponents,
                  "variant_hashes": variants, "prefix_audit": {"approved": True, "path": "reports/p3-prefix-audit.json",
                  "sha256": report.digest_bytes(self.store.read("reports/p3-prefix-audit.json"))}, **source_hashes}
        self.store.put(self.freeze_path, freeze)
        self.probes, self.controls = [], []
        for name in report.OPPONENTS:
            for seed in report.SEEDS:
                for seat in (0, 1):
                    control_key = f"{name}-{seed}-{seat}-baseline.json"
                    control_path = f"results/terminal-20260912/development/{control_key}"
                    # Both route-family members lose; all four other families win.
                    score = 0 if name in ("cok", "arlene") else 1
                    rewards = [100.0, 50.0] if (score == 1) == (seat == 0) else [50.0, 100.0]
                    base_row = {"key": control_key, "variant": "baseline", "candidate_path": report.BASELINE_PATH,
                                "candidate_sha256": base, "opponent": name, "opponent_path": opponents[name]["path"],
                                "opponent_sha256": opponents[name]["sha256"], "family": opponents[name]["family"],
                                "seed": seed, "seat": seat, "split": "development", "evidence": "closed_loop",
                                "engine_sha256": report.ENGINE_HASH, "runner_sha256": sorted(report.OLD_RUNNERS)[0],
                                "rewards": rewards, "margin": rewards[seat] - rewards[1 - seat],
                                "statuses": ["DONE", "DONE"], "frames": 720, "errors": [],
                                "actual_sales": [{"WHEAT": 2}, {"WHEAT": 2}], "sale_revenue": [{"WHEAT": 20}, {"WHEAT": 20}],
                                "market_spending": [{"BUY_SEED:WHEAT": 3}, {"BUY_SEED:WHEAT": 3}]}
                    self.store.put(control_path, base_row)
                    self.controls.append(control_path)
                    reference = {"source": "read_only_reused_P2_control", "path": control_path,
                                 "result_sha256": report.digest_bytes(self.store.read(control_path)), "candidate_sha256": base,
                                 "runner_sha256": base_row["runner_sha256"], "entrypoint": "legacy_explicit_module_agent_not_recorded",
                                 "rewards": rewards, "margin": base_row["margin"], "clean": True, "prefix71": None,
                                 "predecision72": None, "prefix_missingness": "not historically recorded",
                                 "comparability_warning": "old callable and timing differ"}
                    for arm in report.VARIANTS:
                        expected = "low" if arm == "v5-low-file" else "high"
                        row = copy.deepcopy(base_row)
                        key = f"{name}-{seed}-{seat}-{arm}.json"
                        row.update(key=key, variant=arm, candidate_path=f"experiments/track-portfolio-20260912/{arm}/main.py",
                                   candidate_sha256=variants[arm], freeze_path=self.freeze_path,
                                   freeze_sha256=report.digest_bytes(self.store.read(self.freeze_path)), **source_hashes,
                                   entrypoint="official_get_last_callable", opponent_entrypoint="official_get_last_callable",
                                   entrypoint_name="_p3_portfolio_entrypoint", candidate_agent_is_entrypoint=False,
                                   opponent_agent_is_entrypoint=True, opponent_entrypoint_name="agent",
                                   opponent_entrypoint_audit={"is_module_agent": True, "known_source_equivalent_forwarder": False},
                                   feature_schema_sha256=report.schema_digest(), feature_schema=report.FEATURE_SCHEMA,
                                   baseline_comparator=reference)
                        snapshot = {"schema": report.SCHEMA, "schema_sha256": report.schema_digest(), "capture_action_step": 72,
                                    "valid": True, "values": {k: 0 for k in report.FEATURE_NAMES}, "error": None}
                        row["predecision72"] = {"phase": "before candidate action-72 decision, after prior turn's town/decay/night",
                                                "feature_snapshot": snapshot, "public_feature_sha256": report.json_digest(snapshot),
                                                "observation_history_contiguous": True, "eligible_selector_input": True}
                        row["observation_history"] = {"first_step": 0, "last_step": 718, "contiguous_from_zero": True}
                        row["prefix71"] = {"raw_sha256": "a" * 64, "gameplay_sha256": "b" * 64,
                                           "phase": "step-71 after market, BEFORE town consumption, decay and end-of-day",
                                           "runtime_overage_seconds": [60, 60]}
                        row["prefix167"] = dict(row["prefix71"], phase="step-167 after market, BEFORE town consumption, decay and end-of-day")
                        row["predecision168"] = {"phase": "before candidate action-168 decision, after prior town/decay/night",
                                                "public_shop_sequence": ["BAKERY", "YARN_STORE"], "public_shops_valid": True,
                                                "observation_history_contiguous": True}
                        row["own_call_profile"] = [{"step": 0, "wall_ms": 10., "cpu_ms": 5.}]
                        row["max_call_ms"] = [11., 11.]
                        diag = {"fallback_count": 0, "fallback_reasons": {}, "seats": {str(seat): {
                            "entry": {"step": 72, "mode": "forced_v5_low"},
                            "expert_decision": {"step": 168, "expert": expected, "mode": "fixed_probe"}}}}
                        row["route_checkpoints"] = {str(s): {"baseline_route_state": {"v5_gate": True, "v5_expert": expected if s == 168 else None},
                                                            "portfolio_diagnostics": copy.deepcopy(diag)} for s in (72, 167, 168)}
                        row["route_diagnostics"] = {"portfolio_diagnostics": diag, "baseline_route_state": {"v5_expert": expected}}
                        row["phase_flows"] = {"opening_0_71": [{"actual_sales": {"WHEAT": 2}, "sale_revenue": {"WHEAT": 20},
                                                               "unit_purchase_spending": {"BUY_SEED:WHEAT": 3}} for _ in (0, 1)]}
                        row["phase_flow_audit"] = {"consistent": True, "residuals": []}
                        path = self.result_dir + "/" + key
                        self.store.put(path, row)
                        self.probes.append(path)

    def run_report(self):
        return report.build_report(self.store, self.freeze_path, self.result_dir)

    def mutate(self, path, function):
        value = self.store.get(path)
        function(value)
        self.store.put(path, value)

    def change_score(self, path, win):
        def edit(row):
            seat = row["seat"]
            row["rewards"] = [0., 0.]
            row["rewards"][seat if win else 1 - seat] = 100.
            row["margin"] = row["rewards"][seat] - row["rewards"][1 - seat]
        self.mutate(path, edit)

    def test_complete_grid_reuses_controls_and_does_not_fabricate_prefix(self):
        result = self.run_report()
        self.assertTrue(result["hard_gates_passed"])
        self.assertEqual((result["new_probe_games"], result["reused_control_games"], result["matched_cases"]), (96, 48, 48))
        self.assertEqual(len(result["counterfactual_dataset"]["rows"]), 48)
        self.assertTrue(self.store.verified)
        self.assertTrue(all(c["baseline_prefix71_equal"] is None for c in result["cases"]))
        self.assertFalse(result["counterfactual_dataset"]["model_trained"])
        self.assertIn("do_not_train", result["decision"])

    def test_route_family_members_share_one_family_weight(self):
        # COK improves; Arlene does not. The combined gain is .5 / 5, not 1 / 6.
        for path in self.probes:
            if path.rsplit("/", 1)[-1].startswith("cok-"):
                self.change_score(path, True)
        result = self.run_report()
        arm = report.VARIANTS[0]
        self.assertAlmostEqual(result["combined_five_family"]["arms"][arm]["family_weighted_score_delta"], .1)
        self.assertAlmostEqual(result["original_five_opponents"]["arms"][arm]["family_weighted_score_delta"], .2)
        self.assertEqual(result["arlene_stress_only"]["arms"][arm]["family_weighted_score_delta"], 0)

    def test_failed_game_retained_in_primary_and_eligible_label_data(self):
        self.mutate(self.probes[0], lambda r: r.update(statuses=["ERROR", "DONE"], frames=100, errors=["failure fixture"]))
        result = self.run_report()
        self.assertFalse(result["hard_gates_passed"])
        self.assertEqual(result["combined_five_family"]["arms"][report.VARIANTS[0]]["unclean_cases"], 1)
        self.assertEqual(len(result["cases"]), 48)
        self.assertEqual(len(result["counterfactual_dataset"]["rows"]), 48)
        self.assertFalse(result["failed_cases_filtered"])

    def test_raw_overage_difference_does_not_remove_valid_gameplay_pair(self):
        self.mutate(self.probes[1], lambda r: r["prefix71"].update(raw_sha256="c" * 64, runtime_overage_seconds=[59.9, 60]))
        result = self.run_report()
        self.assertTrue(result["hard_gates_passed"])
        self.assertEqual(result["coverage"]["equal_raw_prefix_cases"], 47)
        self.assertEqual(result["coverage"]["eligible_counterfactual_cases"], 48)

    def test_gameplay_prefix_mismatch_excludes_dataset_not_primary(self):
        self.mutate(self.probes[1], lambda r: r["prefix71"].update(gameplay_sha256="c" * 64))
        result = self.run_report()
        self.assertFalse(result["hard_gates_passed"])
        self.assertEqual(result["coverage"]["eligible_counterfactual_cases"], 47)
        self.assertEqual(len(result["cases"]), 48)

    def test_feature_mismatch_not_joined_as_same_context(self):
        def edit(row):
            snap = row["predecision72"]["feature_snapshot"]
            snap["values"][report.FEATURE_NAMES[0]] = 1
            row["predecision72"]["public_feature_sha256"] = report.json_digest(snap)
        self.mutate(self.probes[1], edit)
        self.assertEqual(self.run_report()["coverage"]["eligible_counterfactual_cases"], 47)

    def test_feature_leak_rejected_even_with_recomputed_hash(self):
        def edit(row):
            snap = row["predecision72"]["feature_snapshot"]
            snap["values"]["seed"] = 91101
            row["predecision72"]["public_feature_sha256"] = report.json_digest(snap)
        self.mutate(self.probes[0], edit)
        result = self.run_report()
        self.assertFalse(result["hard_gates_passed"])
        self.assertEqual(result["coverage"]["eligible_counterfactual_cases"], 47)
        self.assertNotIn("seed", result["counterfactual_dataset"]["rows"][0]["predictors"])

    def test_feature_hash_corruption_and_invalid_number_exclude(self):
        self.mutate(self.probes[0], lambda r: r["predecision72"].update(public_feature_sha256="0" * 64))
        self.assertEqual(self.run_report()["coverage"]["eligible_counterfactual_cases"], 47)
        self.mutate(self.probes[2], lambda r: r["predecision72"]["feature_snapshot"]["values"].update({report.FEATURE_NAMES[0]: True}))
        self.assertEqual(self.run_report()["coverage"]["eligible_counterfactual_cases"], 46)

    def test_zero_activation_is_untested_not_success(self):
        for path in self.probes:
            self.mutate(path, lambda r: r.update(route_checkpoints={}))
        result = self.run_report()
        self.assertEqual(result["coverage"]["tested_probe_rows"], 0)
        self.assertEqual(result["decision"], "zero_activation_untested_do_not_train")
        self.assertEqual(len(result["cases"]), 48)

    def test_early_high_and_wrong_expert_mark_untested(self):
        self.mutate(self.probes[1], lambda r: r["route_checkpoints"]["167"]["baseline_route_state"].update(v5_expert="high"))
        self.assertEqual(self.run_report()["coverage"]["untested_probe_rows"], 1)

    def test_phase_flow_accounting_is_independent(self):
        self.mutate(self.probes[0], lambda r: r["phase_flows"]["opening_0_71"][0]["actual_sales"].update(WHEAT=3))
        result = self.run_report()
        self.assertFalse(result["hard_gates_passed"])
        self.assertEqual(len(result["cases"]), 48)

    def test_historical_callable_equivalence_is_checked(self):
        self.mutate(self.probes[0], lambda r: r.update(opponent_agent_is_entrypoint=False,
                                                     opponent_entrypoint_audit={"is_module_agent": False, "known_source_equivalent_forwarder": False}))
        result = self.run_report()
        self.assertFalse(result["hard_gates_passed"])
        self.assertEqual(len(result["cases"]), 48)

    def test_action72_eligible_flag_must_have_continuous_recorded_history(self):
        self.mutate(self.probes[0], lambda r: r["observation_history"].update(first_step=72))
        self.assertEqual(self.run_report()["coverage"]["eligible_counterfactual_cases"], 47)

    def test_later_history_failure_does_not_filter_valid72_labels(self):
        self.mutate(self.probes[0], lambda r: r["observation_history"].update(contiguous_from_zero=False))
        result = self.run_report()
        self.assertFalse(result["hard_gates_passed"])
        self.assertEqual(result["coverage"]["eligible_counterfactual_cases"], 48)

    def test_complementarity_oracle_not_an_achievable_gain(self):
        for path in self.probes:
            row = self.store.get(path)
            if row["opponent"] in ("cok", "arlene"):
                self.change_score(path, (row["seed"] % 2 == 1) == (row["variant"] == report.VARIANTS[0]))
        result = self.run_report()
        oracle = result["combined_five_family"]["hindsight_diagnostic"]
        self.assertAlmostEqual(oracle["oracle_minus_best_fixed"], .1)
        self.assertFalse(oracle["achievable_uplift_claim"])
        self.assertFalse(oracle["trained_model"])
        self.assertEqual(result["decision"], "no_observable72_headroom_do_not_train")
        self.assertAlmostEqual(result["counterfactual_dataset"]["feature_cell_oracle_minus_best_fixed"], 0.)
        self.assertGreater(result["counterfactual_dataset"]["identical_feature_cells_with_different_outcome_vectors"], 0)

    def test_observable_complementarity_only_requests_parent_review(self):
        for path in self.probes:
            row = self.store.get(path)
            if row["opponent"] in ("cok", "arlene"):
                self.change_score(path, (row["seed"] % 2 == 1) == (row["variant"] == report.VARIANTS[0]))
            def edit(r):
                snap = r["predecision72"]["feature_snapshot"]
                snap["values"][report.FEATURE_NAMES[0]] = 1 if r["seed"] % 2 else 2
                r["predecision72"]["public_feature_sha256"] = report.json_digest(snap)
            self.mutate(path, edit)
        result = self.run_report()
        self.assertIn("parent_review", result["decision"])
        self.assertFalse(result["promotion"])
        self.assertFalse(result["counterfactual_dataset"]["model_trained"])

    def test_better_fixed_expert_not_rejected_for_zero_oracle_gap(self):
        for path in self.probes:
            if self.store.get(path)["opponent"] in ("cok", "arlene"):
                self.change_score(path, True)
        self.assertEqual(self.run_report()["decision"], "fixed_expert_merits_fresh_evaluation_no_ml_needed")

    def test_native168_secondary_rule_is_not_action72_feature(self):
        result = self.run_report()
        diag = result["secondary_native168_rule"]
        self.assertEqual(diag["eligible_cases"], 48)
        self.assertEqual(diag["selected_counts"], {"v5-high-file": 48})
        self.assertEqual(diag["actual_adaptive_rollouts"], 0)
        self.assertFalse(diag["achievable_uplift_claim"])
        self.assertEqual(set(result["counterfactual_dataset"]["rows"][0]["predictors"]), set(report.FEATURE_NAMES))
        for path in self.probes[:2]:
            self.mutate(path, lambda r: r["predecision168"].update(public_shop_sequence=["ICE_CREAM_SHOP", "YARN_STORE"]))
        self.assertEqual(self.run_report()["secondary_native168_rule"]["selected_counts"], {"v5-low-file": 1, "v5-high-file": 47})

    def test_native168_requires_both_prefixes_and_matching_valid_shops(self):
        self.mutate(self.probes[1], lambda r: r["prefix167"].update(gameplay_sha256="d" * 64))
        self.mutate(self.probes[3], lambda r: r["predecision168"].update(public_shop_sequence=["BAKERY", "PIZZA_SHOP"]))
        self.mutate(self.probes[5], lambda r: r["predecision168"].update(public_shops_valid=False))
        result = self.run_report()
        self.assertEqual(result["secondary_native168_rule"]["eligible_cases"], 45)
        self.assertEqual(result["coverage"]["eligible_counterfactual_cases"], 48)

    def test_resource_totals_and_prefix_budget_not_final_budget(self):
        self.mutate(self.probes[0], lambda r: r.update(own_call_profile=[{"step": 0, "wall_ms": 1200., "cpu_ms": 1100.}], max_call_ms=[1300., 4.]))
        result = self.run_report()
        resources = result["resources_diagnostic"][report.VARIANTS[0]]
        self.assertEqual(resources["max_own_outer_call_ms"], 1300.)
        self.assertEqual(resources["recorded_inner_wall_calls_over_1000ms"], 1)
        self.assertEqual(resources["recorded_inner_cpu_total_ms"], 1100 + 47 * 5)
        self.assertEqual(resources["final_remaining_overage_recorded_rows"], 0)
        self.assertIn("not release", result["hard_gate_scope"])
        self.assertIsNone(result["cases"][0]["resources"][report.VARIANTS[0]]["final_remaining_overage_seconds"])

    def test_changed_capture_phase_cannot_fake_common_prefix(self):
        for path in self.probes[:2]:
            self.mutate(path, lambda r: r["prefix71"].update(phase="before the wrong turn"))
        self.assertEqual(self.run_report()["coverage"]["eligible_counterfactual_cases"], 47)

    def test_identity_corruption_hard_rejected(self):
        for field, bad in (("seed", 91199), ("seat", True), ("engine_sha256", "0" * 64),
                           ("candidate_sha256", "0" * 64), ("opponent", "wrong"),
                           ("family", "sixth_family"), ("freeze_sha256", "0" * 64)):
            with self.subTest(field=field):
                original = self.store.read(self.probes[0])
                self.mutate(self.probes[0], lambda r: r.update({field: bad}))
                with self.assertRaises(ValueError):
                    self.run_report()
                self.store.files[self.probes[0]] = original

    def test_actual_artifact_hash_corruption_rejected(self):
        self.store.files["scripts/run_portfolio_track.py"] += b"changed"
        with self.assertRaisesRegex(ValueError, "Actual file hash mismatch"):
            self.run_report()

    def test_comparator_tampering_rejected(self):
        self.mutate(self.controls[0], lambda r: r.update(margin=123))
        with self.assertRaisesRegex(ValueError, "Actual file hash mismatch"):
            self.run_report()

    def test_fabricated_control_prefix_rejected(self):
        self.mutate(self.probes[0], lambda r: r["baseline_comparator"].update(prefix71={"gameplay_sha256": "a" * 64}))
        with self.assertRaisesRegex(ValueError, "Comparator reference"):
            self.run_report()

    def test_reference_payload_must_match_actual_control(self):
        self.mutate(self.probes[0], lambda r: r["baseline_comparator"].update(clean=False))
        with self.assertRaisesRegex(ValueError, "Comparator payload"):
            self.run_report()

    def test_missing_grid_member_rejected_not_silently_dropped(self):
        del self.store.files[self.probes[-1]]
        with self.assertRaises(KeyError):
            self.run_report()

    def test_strict_json_rejects_duplicates_nan_and_path_escape(self):
        for raw in (b'{"x": 1, "x": 2}', b'{"x": NaN}', b'{"x": Infinity}'):
            with self.assertRaises(ValueError):
                report.strict_json(raw)
        with self.assertRaises(ValueError):
            report.Audit(self.store).raw("../outside.json")


if __name__ == "__main__":
    unittest.main()
