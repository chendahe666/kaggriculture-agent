"""No-game tests for P3 feature privacy, recorder semantics and execution gates."""
import copy
from collections import Counter
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import portfolio_features as features
import run_portfolio_track as runner


def observation():
    farm = {"money": 1000, "farmer": [4, 4], "hands": [[3, 4]], "hires_today": 1,
            "unlocked_quadrants": ["NW"], "tiles": [[None if x < 5 and y < 5 else "LOCKED" for x in range(10)] for y in range(10)]}
    other = copy.deepcopy(farm)
    other["money"] = 900
    return {"step": 72, "player": 0, "day": 3, "hour": 0, "farms": [farm, other],
            "market": {"inventory": {p: 10000 for p in features.PRODUCTS}, "prices": {p: 10 for p in features.PRODUCTS}},
            "town": {"unlocked_shops": ["YARN_STORE", "YARN_STORE"]}, "private": {"inventories": [{"secret": 999}]}}


class FeatureTests(unittest.TestCase):
    def test_schema_complete_unique_and_numeric(self):
        result = features.extract_public72(observation())
        self.assertTrue(result["valid"])
        self.assertEqual(set(result["values"]), set(features.FEATURE_NAMES))
        self.assertEqual(len(features.FEATURE_NAMES), len(set(features.FEATURE_NAMES)))
        self.assertEqual(result["values"]["town.shop_count.YARN_STORE"], 2)
        self.assertTrue(all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in result["values"].values()))

    def test_forbidden_and_unknown_fields_do_not_affect_features(self):
        original = observation()
        altered = copy.deepcopy(original)
        altered.update(seed=987654, opponent_name="SECRET IDENTITY", rewards=[123, 456], remainingOverageTime=3,
                       future_shops=["BAKERY"], private={"shed": {"MILK": 123456}}, opponent_private={"MILK": 999})
        altered["farms"][1].update(private={"secret": 777}, opponent_id="HIDDEN NAME")
        altered["market"]["future_inventory"] = {"WHEAT": 123}
        self.assertEqual(features.extract_public72(original), features.extract_public72(altered))

    def test_private_field_is_never_accessed(self):
        class NoPrivate(dict):
            def __getitem__(self, key):
                if key == "private":
                    raise AssertionError("Private field accessed")
                return super().__getitem__(key)
        self.assertTrue(features.extract_public72(NoPrivate(observation()))["valid"])

    def test_seat_is_orientation_not_predictor(self):
        first = observation()
        second = copy.deepcopy(first)
        second["player"] = 1
        second["farms"].reverse()
        self.assertEqual(features.extract_public72(first), features.extract_public72(second))
        self.assertFalse(any("seat" in name or "player" in name for name in features.FEATURE_NAMES))

    def test_current_crop_animal_public_summaries(self):
        obs = observation()
        obs["farms"][0]["tiles"][0][0] = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 1, "yield_units": 4, "watered_today": True}
        obs["farms"][1]["tiles"][0][0] = {"kind": "PASTURE", "animal": "COW", "placed_day": 0, "yield_units": 3,
                                                  "fed_today": True, "cared_today": False, "fertilizer_available": True}
        result = features.extract_public72(obs)
        self.assertTrue(result["valid"])
        self.assertEqual(result["values"]["own.crop.WHEAT.age_days_sum"], 2)
        self.assertEqual(result["values"]["own.crop.WHEAT.yield_units"], 4)
        self.assertEqual(result["values"]["opponent.animal.COW.fertilizer_available_count"], 1)

    def test_missing_public_data_is_invalid_not_zero(self):
        obs = observation()
        del obs["market"]["inventory"]["WHEAT"]
        result = features.extract_public72(obs)
        self.assertFalse(result["valid"])
        self.assertIsNone(result["values"])

    def test_wrong_step_invalid_and_unknown_values_not_leaked(self):
        obs = observation()
        obs["step"] = 71
        self.assertFalse(features.extract_public72(obs)["valid"])
        obs["step"] = 72
        obs["farms"][0]["tiles"][0][0] = {"kind": "secret payload"}
        result = features.extract_public72(obs)
        self.assertFalse(result["valid"])
        self.assertNotIn("secret payload", json.dumps(result))

    def test_nan_and_invalid_bool_rejected(self):
        for value in (float("nan"), float("inf"), True, -1):
            obs = observation()
            obs["farms"][1]["money"] = value
            self.assertFalse(features.extract_public72(obs)["valid"])


class RunnerTests(unittest.TestCase):
    def test_configuration_and_predecision_capture_precede_policy_mutation(self):
        received = []
        configuration = {"boardSize": 17}
        def candidate(obs, config):
            received.append(config)
            obs["farms"][0]["money"] = 999999
            return {"farmer": ["PASS"], "hands": [], "market": []}
        profile, capture, requested = [], {}, Counter()
        wrapped = runner.instrument_candidate(candidate, 0, profile, capture, requested)
        for step in range(73):
            obs = observation()
            obs["step"] = step
            wrapped(obs, configuration)
        self.assertTrue(all(c is configuration for c in received))
        self.assertEqual(capture["predecision72"]["feature_snapshot"]["values"]["own.money"], 1000)
        self.assertTrue(capture["predecision72"]["eligible_selector_input"])
        self.assertEqual(len(profile), 73)
        self.assertEqual(requested["PASS"], 73)

    def test_discontinuous_history_cannot_be_training_input(self):
        def candidate(obs, config):
            return {"farmer": ["PASS"]}
        capture = {}
        runner.instrument_candidate(candidate, 0, [], capture, Counter())(observation(), {})
        self.assertTrue(capture["predecision72"]["feature_snapshot"]["valid"])
        self.assertFalse(capture["predecision72"]["eligible_selector_input"])

    def test_168_shop_sequence_captured_before_action_and_separate_from_72(self):
        def candidate(obs, config):
            if obs["step"] == 168:
                obs["town"]["unlocked_shops"].append("BAKERY")
            return {"farmer": ["PASS"]}
        capture = {}
        wrapped = runner.instrument_candidate(candidate, 0, [], capture, Counter())
        for step in range(169):
            obs = observation()
            obs["step"] = step
            wrapped(obs, {})
        self.assertEqual(capture["predecision168"]["public_shop_sequence"], ["YARN_STORE", "YARN_STORE"])
        self.assertTrue(capture["predecision168"]["observation_history_contiguous"])
        self.assertEqual(capture["predecision72"]["feature_snapshot"]["values"]["town.shop_count.BAKERY"], 0)
        self.assertNotIn("predecision168", capture["predecision72"])

    def test_snapshot_raw_budget_difference_not_gameplay_difference(self):
        first = [observation(), observation()]
        second = copy.deepcopy(first)
        first[0]["remainingOverageTime"], second[0]["remainingOverageTime"] = 60, 59
        a, b = (runner.snapshot_hashes(v, "phase") for v in (first, second))
        self.assertNotEqual(a["raw_sha256"], b["raw_sha256"])
        self.assertEqual(a["gameplay_sha256"], b["gameplay_sha256"])
        self.assertNotIn("private", a)

    def test_only_development_is_supported(self):
        with self.assertRaisesRegex(ValueError, "confirmation remains unopened"):
            runner.validate_freeze({}, {}, [], [], "confirmation", {})

    def test_cumulative_budget_does_not_reset_on_resume(self):
        runner.validate_budget(20, 76, 96, 76)
        with self.assertRaisesRegex(ValueError, "cumulative"):
            runner.validate_budget(21, 76, 96, 76)
        with self.assertRaisesRegex(ValueError, "pilot cap"):
            runner.validate_budget(20, 0, 96, 240)

    def test_freeze_requires_approved_audit(self):
        sources = {"engine_sha256": runner.ENGINE_HASH}
        freeze = {"schema": "portfolio-track-freeze-v1", "split": "development", "seeds": [1],
                  "engine_sha256": runner.ENGINE_HASH, "feature_schema_sha256": features.schema_digest(), "max_new_games": 96}
        with self.assertRaisesRegex(ValueError, "audit not approved"):
            runner.validate_freeze(freeze, {}, [], [1], "development", sources)

    def test_resume_requires_exact_identity_but_preserves_unclean_game(self):
        keys = ("key", "variant", "candidate_path", "candidate_sha256", "opponent", "opponent_path", "opponent_sha256",
                "family", "seed", "seat", "split", "freeze_sha256", "runner_sha256", "features_sha256", "research_cycle_sha256", "engine_sha256", "feature_schema_sha256")
        job = {key: key for key in keys}
        job["baseline_comparator"] = None
        row = {**job, "entrypoint": "official_get_last_callable", "statuses": ["ERROR", "DONE"]}
        runner.validate_existing(row, job)
        row["candidate_sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "candidate_sha256"):
            runner.validate_existing(row, job)

    def test_phase_flow_reconciliation_and_negative_residual(self):
        row = {"actual_sales": [{"MILK": 2}, {}], "sale_revenue": [{"MILK": 30}, {}], "market_spending": [{}, {"BUY_PRODUCT:WHEAT": 5}]}
        phase = {"opening_0_71": [{"actual_sales": {"MILK": 2}, "sale_revenue": {"MILK": 30}, "unit_purchase_spending": {}},
                                 {"actual_sales": {}, "sale_revenue": {}, "unit_purchase_spending": {"BUY_PRODUCT:WHEAT": 5}}]}
        self.assertTrue(runner.phase_flow_audit(row, phase)["consistent"])
        phase["opening_0_71"][0]["sale_revenue"]["MILK"] = 31
        audit = runner.phase_flow_audit(row, phase)
        self.assertFalse(audit["consistent"])
        self.assertEqual(audit["residuals"][0]["global_minus_phase"], {"MILK": -1})

    def test_exclusive_result_write_preserves_existing(self):
        # Python 3.13's restrictive Windows tempfile ACL can exclude this host's
        # sandbox token; inherit workspace ACLs in a unique, bounded test folder.
        folder = runner.LAB / "inbox" / ("p3-runner-test-" + uuid.uuid4().hex)
        folder.mkdir()
        path = folder / "result.json"
        try:
            runner.write_new_result(path, {"a": 1})
            with self.assertRaises(FileExistsError):
                runner.write_new_result(path, {"a": 2})
            self.assertEqual(json.loads(path.read_text()), {"a": 1})
        finally:
            path.unlink(missing_ok=True)
            folder.rmdir()

    def test_invalid_variant_path_rejected(self):
        with self.assertRaises(ValueError):
            runner.candidate_path("../frozen")
        self.assertEqual(runner.candidate_path("v5-low-file"), "experiments/track-portfolio-20260912/v5-low-file/main.py")

    def test_real_configuration_through_recorder_one_arg_opponent_and_commits(self):
        seen, config = [], {"startingMoney": 4321, "boardSize": 11}
        farms = [{"money": 100}, {"money": 200}]
        engine = SimpleNamespace()
        def unit(op, item, price, farm, private, market, shed_capacity=100):
            if op == "SELL":
                farm["money"] += price
                return True
            return False
        def market(states, env):
            engine._commit_unit("SELL", "MILK", 10, farms[0], {}, {})
            engine._commit_unit("BUY_PRODUCT", "WHEAT", 5, farms[1], {}, {})
        engine._commit_unit, engine._process_market = unit, market
        def ours(obs, official_config):
            seen.append(official_config)
            return {"farmer": ["PASS"]}
        def other(obs):
            return {"farmer": ["PASS"]}
        class FakeEnvironment:
            logs = []
            def run(self, policies):
                for policy in policies:
                    policy({"step": 0}, config)
                observation_obj = SimpleNamespace(farms=farms, town=SimpleNamespace(unlocked_shops=[]), private=SimpleNamespace(shed={}))
                states = [SimpleNamespace(observation=observation_obj, reward=0, status="DONE") for _ in range(2)]
                engine._process_market(states, self)
                for index, state in enumerate(states):
                    state.reward = farms[index]["money"]
                return [states]
        row = runner.run_game_configured([ours, other], {"seed": 1}, engine, lambda *a, **k: FakeEnvironment())
        self.assertIs(seen[0], config)
        self.assertEqual(row["actual_sales"][0], {"MILK": 1})
        self.assertEqual(row["sale_revenue"][0], {"MILK": 10})
        self.assertEqual(row["failed_market_commits"][1], {"BUY_PRODUCT:WHEAT": 1})
        self.assertEqual(row["market_spending"][1], {})
        self.assertIs(engine._commit_unit, unit)
        self.assertIs(engine._process_market, market)

    def test_exception_restores_engine_hooks_without_silent_fallback(self):
        original_market, original_commit = lambda *a: None, lambda *a: True
        engine = SimpleNamespace(_process_market=original_market, _commit_unit=original_commit)
        def candidate(obs, config):
            raise RuntimeError("deliberate policy failure")
        class FakeEnvironment:
            def run(self, policies):
                policies[0]({}, {})
        with self.assertRaisesRegex(RuntimeError, "deliberate policy failure"):
            runner.run_game_configured([candidate, candidate], {}, engine, lambda *a, **k: FakeEnvironment())
        self.assertIs(engine._process_market, original_market)
        self.assertIs(engine._commit_unit, original_commit)

    def test_short_official_environment_nested_counters_and_configuration(self):
        # Owner-approved four-frame smoke, not a 720-frame experiment. No result
        # files or opponent private observations are exported.
        from research_cycle import engine
        from kaggle_environments import make
        configs, phases, current_farms = [], {}, []
        old_market, old_commit = engine._process_market, engine._commit_unit
        def phase_market(state, env):
            current_farms[:] = state[0].observation.farms
            return old_market(state, env)
        def phase_commit(op, item, price, farm, private, market, shed_capacity=100):
            before = farm["money"]
            ok = old_commit(op, item, price, farm, private, market, shed_capacity)
            if ok:
                seat = next(i for i, f in enumerate(current_farms) if f is farm)
                bucket = phases.setdefault("opening_0_71", [{"actual_sales": Counter(), "sale_revenue": Counter(), "unit_purchase_spending": Counter()} for _ in range(2)])[seat]
                if op == "SELL":
                    bucket["actual_sales"][item] += 1
                    bucket["sale_revenue"][item] += price
                elif farm["money"] < before:
                    bucket["unit_purchase_spending"][op + ":" + str(item)] += before - farm["money"]
            return ok
        def policy(obs, config):
            configs.append(config)
            step = int(obs["step"])
            orders = [["BUY_PRODUCT", "WHEAT", 1]] if step == 0 else [["SELL", "WHEAT", 1]] if step == 1 else []
            return {"farmer": ["PASS"], "hands": [], "market": orders}
        def passive(obs):
            return {"farmer": ["PASS"], "hands": [], "market": []}
        profile, capture = [], {}
        wrapped = runner.instrument_candidate(policy, 0, profile, capture, Counter())
        engine._process_market, engine._commit_unit = phase_market, phase_commit
        try:
            row = runner.run_game_configured([wrapped, passive], {"seed": 91101, "episodeSteps": 4, "startingMoney": 4321}, engine, make)
        finally:
            engine._process_market, engine._commit_unit = old_market, old_commit
        self.assertEqual(row["frames"], 4)
        self.assertEqual(row["statuses"], ["DONE", "DONE"])
        self.assertFalse(row["errors"])
        self.assertTrue(all(config.startingMoney == 4321 and config.episodeSteps == 4 for config in configs))
        self.assertEqual(row["actual_sales"][0]["WHEAT"], 1)
        self.assertGreater(row["market_spending"][0]["BUY_PRODUCT:WHEAT"], 0)
        self.assertTrue(runner.phase_flow_audit(row, phases)["consistent"])
        self.assertNotIn("predecision72", capture)


if __name__ == "__main__":
    unittest.main()
