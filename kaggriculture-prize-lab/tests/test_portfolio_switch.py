"""P3 interface/mechanism tests, never a full game or strength estimate.

Six official-engine prefixes stop after action 180, with a live COK opponent.
Other tests replay those legal observations or explicitly labelled selected-state
counterexamples. They do not open the confirmation seeds or write artifacts.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import types
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "scripts"))
from research_cycle import make, engine
from kaggle_environments.agent import get_last_callable

BASE = LAB / "public-baseline-v10/main.py"
OVERLAY = LAB / "experiments/track-portfolio-20260912/portfolio_overlay.py"
BASE_SHA = "1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01"
ENGINE_SHA = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
LEDGERS = ("_FR_STATE", "_META_STATE", "_WEED_STATE", "_COW_ALIGN_STATE", "_ROUTE_STATE")


def source(expert="low"):
    return (BASE.read_text(encoding="utf-8") + "\nP3_EXPERT = " + repr(expert)
            + "\n" + OVERLAY.read_text(encoding="utf-8"))


def load_portfolio(expert="low"):
    module = types.ModuleType("isolated_portfolio")
    exec(compile(source(expert), str(OVERLAY), "exec"), module.__dict__)
    return module


def load_baseline():
    module = types.ModuleType("isolated_cok")
    exec(compile(BASE.read_text(encoding="utf-8"), str(BASE), "exec"), module.__dict__)
    return module


def observation(env, seat):
    # The framework exposes shared step/state to seat 1 here. Its raw stored
    # observation can retain step=0; never feed that private storage directly.
    return copy.deepcopy(env._Environment__get_shared_state(seat).observation)


def gameplay(env):
    return [{k: copy.deepcopy(v) for k, v in observation(env, seat).items()
             if k != "remainingOverageTime"} for seat in (0, 1)]


def ledgers(module, seat):
    return {name: copy.deepcopy(getattr(module, name)[seat]) for name in LEDGERS}


def prefix(expert, seat):
    module = load_baseline() if expert == "baseline" else load_portfolio(expert)
    opponent = load_baseline()
    env = make("kaggriculture", configuration={"seed": 17}, debug=False)
    env.reset(2)
    rows = []
    for step in range(181):
        obs = observation(env, seat)
        before = ledgers(module, seat)
        state_before = gameplay(env)
        tick = time.perf_counter()
        action = module.agent(obs, env.configuration)
        call_ms = (time.perf_counter() - tick) * 1000
        other = opponent.agent(observation(env, 1 - seat), env.configuration)
        actions = [action, other] if seat == 0 else [other, action]
        after = ledgers(module, seat)
        env.step(actions)
        rows.append({"obs": obs, "action": copy.deepcopy(action), "other_action": copy.deepcopy(other),
                     "before": before, "after": after, "game_before": state_before,
                     "game_after": gameplay(env), "status": [s.status for s in env.state], "call_ms": call_ms})
    return {"module": module, "rows": rows, "config": copy.deepcopy(env.configuration)}


class PortfolioSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
            raise AssertionError("COK source is not the audited frozen baseline")
        if hashlib.sha256(Path(engine.__file__).read_bytes()).hexdigest() != ENGINE_SHA:
            raise AssertionError("Installed engine is not the pinned audited engine")
        cls.prefixes = {(variant, seat): prefix(variant, seat)
                        for seat in (0, 1) for variant in ("baseline", "low", "high")}

    def replay(self, module, until, seat=0, variant="low", start=0, skip=(), config=None):
        data = self.prefixes[(variant, seat)]
        cfg = data["config"] if config is None else config
        action = None
        for step in range(start, until + 1):
            if step not in skip:
                action = module.agent(copy.deepcopy(data["rows"][step]["obs"]), cfg)
        return action

    def test_all_twelve_raw_prefixes_and_sales_pairs_match_audit(self):
        m = load_portfolio()
        self.assertIsNone(m._p3_trace_reason())
        tables = [*m._V7_CURRENT_ROUTES.values(), *m._V7_LEGACY_ROUTES.values(),
                  m._V5_LOW_ACTIONS, m._V5_HIGH_ACTIONS]
        self.assertEqual(len(tables), 12)
        for table in tables:
            self.assertEqual(table[:72], m._V5_LOW_ACTIONS[:72])
            sales = m._v7_sales_schedule(table)
            self.assertFalse(set(sales) & (set(range(65, 84)) | set(range(161, 180))))
        self.assertEqual(m._V5_LOW_ACTIONS[:168], m._V5_HIGH_ACTIONS[:168])
        market_diff = next(s for s in range(719) if m._V5_LOW_ACTIONS[s]["market"] != m._V5_HIGH_ACTIONS[s]["market"])
        unit_diff = next(s for s in range(719) if any(m._V5_LOW_ACTIONS[s][k] != m._V5_HIGH_ACTIONS[s][k] for k in ("farmer", "hands")))
        self.assertEqual((market_diff, unit_diff), (168, 179))
        self.assertFalse(m._ENABLE_NINTH_COW)

    def test_official_closed_loop_complete_prefix_parity_both_seats(self):
        for seat in (0, 1):
            baseline = self.prefixes[("baseline", seat)]["rows"]
            low = self.prefixes[("low", seat)]["rows"]
            high = self.prefixes[("high", seat)]["rows"]
            for step in range(72):
                for candidate in (low, high):
                    with self.subTest(seat=seat, step=step):
                        self.assertEqual(candidate[step]["action"], baseline[step]["action"])
                        self.assertEqual(candidate[step]["other_action"], baseline[step]["other_action"])
                        self.assertEqual(candidate[step]["game_after"], baseline[step]["game_after"])
                        self.assertEqual(candidate[step]["after"], baseline[step]["after"])
            for step in range(72, 168):
                self.assertEqual(low[step]["action"], high[step]["action"], (seat, step))
                self.assertEqual(low[step]["game_after"], high[step]["game_after"], (seat, step))
                self.assertEqual(low[step]["after"], high[step]["after"], (seat, step))
            self.assertEqual(low[168]["game_before"], high[168]["game_before"])
            for rows in (baseline, low, high):
                for row in rows:
                    self.assertEqual(row["status"], ["ACTIVE", "ACTIVE"])
                    self.assertEqual(len(row["action"]["hands"]), len(row["obs"]["farms"][seat]["hands"]))

    def test_actual_72_entry_and_168_fixed_paired_expert(self):
        for seat in (0, 1):
            for expert in ("low", "high"):
                m = load_portfolio(expert)
                self.replay(m, 71, seat)
                self.assertFalse(m._P3_HISTORY[seat]["entered"])
                self.replay(m, 72, seat, start=72)
                self.assertTrue(m._ROUTE_STATE[seat]["v5_gate"])
                self.assertIs(m._ACTIONS, m._V5_LOW_ACTIONS)
                self.assertIs(m._META_SALES, m._V5_LOW_META_SALES)
                self.replay(m, 167, seat, start=73)
                self.assertIsNone(m._ROUTE_STATE[seat]["v5_expert"])
                self.assertIs(m._ACTIONS, m._V5_LOW_ACTIONS)
                self.replay(m, 168, seat, start=168)
                self.assertEqual(m._ROUTE_STATE[seat]["v5_expert"], expert)
                self.assertIs(m._ACTIONS, getattr(m, "_V5_" + expert.upper() + "_ACTIONS"))
                self.assertIs(m._META_SALES, getattr(m, "_V5_" + expert.upper() + "_META_SALES"))
                self.assertEqual(m._P3_DIAGNOSTICS["entry_count"], 1)
                self.assertEqual(m._P3_DIAGNOSTICS["expert_decision_count"], 1)
                self.assertEqual(m._P3_DIAGNOSTICS["fallback_count"], 0)
                self.assertEqual(m._P3_DIAGNOSTICS["trace_validation_count"], 3)
                self.assertGreater(m._P3_DIAGNOSTICS["trace_validation_total_ms"], 0)

    def test_152_future_lookahead_catches_premature_high_with_zero_and_nonzero_stock(self):
        m = load_portfolio("high")
        self.replay(m, 151)
        obs = copy.deepcopy(self.prefixes[("low", 0)]["rows"][152]["obs"])
        for stock, expected in ((0, (2, 1)), (1, (1, 0)), (10, (0, 0))):
            obs["private"]["seeds"]["CARROT"] = stock
            amounts = []
            for table in (m._V5_LOW_ACTIONS, m._V5_HIGH_ACTIONS):
                m._ACTIONS = table
                action = m._clip_seed_surplus(copy.deepcopy(table[152]), obs, 152)
                amounts.append(sum(o[2] for o in action["market"] if o[:2] == ["BUY_SEED", "CARROT"]))
            self.assertEqual(tuple(amounts), expected)
        # Full actual observation must restore low via the selector, not retain
        # the deliberately premature high table used in the counterexample.
        actual = self.replay(m, 152, start=152)
        self.assertEqual(actual, self.prefixes[("low", 0)]["rows"][152]["action"])
        self.assertIs(m._ACTIONS, m._V5_LOW_ACTIONS)

    def test_missing_or_skipped_history_never_forces_entry_and_native_fallback_matches(self):
        for start, skipped in ((72, ()), (0, (31,)), (0, (72,))):
            m, native = load_portfolio("high"), load_baseline()
            data = self.prefixes[("baseline", 0)]
            for step in range(start, 75):
                if step in skipped:
                    continue
                obs = copy.deepcopy(data["rows"][step]["obs"])
                self.assertEqual(m.agent(obs, data["config"]), native.agent(obs, data["config"]))
            self.assertEqual(m._P3_DIAGNOSTICS["entry_count"], 0)
            self.assertFalse(m._P3_HISTORY[0]["entered"])

    def test_malformed_observations_reject_forced_gate_without_replacing_native_behavior(self):
        def missing_private(obs):
            del obs["private"]
        def missing_money(obs):
            del obs["farms"][1]["money"]
        def bad_money(obs):
            obs["farms"][0]["money"] = float("nan")
        def bool_money(obs):
            obs["farms"][0]["money"] = True
        def bad_tiles(obs):
            obs["farms"][1]["tiles"][0] = "not a row"
        def bad_shops(obs):
            obs["town"]["unlocked_shops"] = "YARN_STORE"
        def missing_market(obs):
            del obs["market"]["prices"]["MILK"]
        for mutation in (missing_private, missing_money, bad_money, bool_money, bad_tiles, bad_shops, missing_market):
            with self.subTest(mutation=mutation.__name__):
                m, native = load_portfolio("high"), load_baseline()
                self.replay(m, 71, variant="baseline")
                self.replay(native, 71, variant="baseline")
                obs = copy.deepcopy(self.prefixes[("baseline", 0)]["rows"][72]["obs"])
                mutation(obs)
                self.assertEqual(m.agent(obs), native.agent(obs))
                self.assertEqual(m._P3_DIAGNOSTICS["entry_count"], 0)
                self.assertGreater(m._P3_DIAGNOSTICS["fallback_count"], 0)

    def test_nondefault_configuration_and_invalid_flag_delegate_native(self):
        for changed in ({"turnsPerDay": 12}, {"marketParams": {"WHEAT": {"base": 20}}}, {"farmHandCostMult": 2}):
            m, native = load_portfolio("high"), load_baseline()
            self.replay(m, 71, variant="baseline")
            self.replay(native, 71, variant="baseline")
            obs = copy.deepcopy(self.prefixes[("baseline", 0)]["rows"][72]["obs"])
            config = {**self.prefixes[("baseline", 0)]["config"], **changed}
            self.assertEqual(m.agent(obs, config), native.agent(obs, config))
            self.assertEqual(m._P3_DIAGNOSTICS["entry_count"], 0)
        m = load_portfolio("learned-but-not-implemented")
        self.replay(m, 72, variant="baseline")
        self.assertEqual(m._P3_DIAGNOSTICS["entry_count"], 0)

    def test_internal_missing_malformed_or_unpaired_trace_is_not_forced(self):
        for damage in ("missing", "malformed", "unpaired", "prefix"):
            m, native = load_portfolio("high"), load_baseline()
            self.replay(m, 71, variant="baseline")
            self.replay(native, 71, variant="baseline")
            if damage == "missing":
                m._V5_HIGH_ACTIONS = None
            elif damage == "malformed":
                m._V5_HIGH_ACTIONS[300] = None
            elif damage == "unpaired":
                m._V5_HIGH_META_SALES[400] = {"MILK": 999}
            else:
                m._V5_HIGH_ACTIONS[10]["farmer"] = ["PASS"]
            obs = copy.deepcopy(self.prefixes[("baseline", 0)]["rows"][72]["obs"])
            # This selected native case does not itself choose the damaged high
            # table. The overlay cannot repair arbitrary corruption of COK.
            self.assertFalse(native._v10_should_use_v5(obs))
            self.assertEqual(m.agent(obs), native.agent(obs))
            self.assertEqual(m._P3_DIAGNOSTICS["entry_count"], 0)

    def test_missed_168_is_explicit_safe_low_not_late_high_or_old_layout(self):
        m = load_portfolio("high")
        self.replay(m, 167)
        self.replay(m, 169, start=169)
        self.assertTrue(m._ROUTE_STATE[0]["v5_gate"])
        self.assertEqual(m._ROUTE_STATE[0]["v5_expert"], "low")
        self.assertIs(m._ACTIONS, m._V5_LOW_ACTIONS)
        self.assertEqual(m._P3_DIAGNOSTICS["seats"][0]["expert_decision"]["mode"], "safe_low")
        self.replay(m, 180, start=170)
        self.assertIs(m._ACTIONS, m._V5_LOW_ACTIONS)

    def test_gap_before_168_and_late_config_change_preserve_v5(self):
        for kind in ("gap", "configuration"):
            m = load_portfolio("high")
            self.replay(m, 80)
            if kind == "gap":
                self.replay(m, 168, start=82)
            else:
                self.replay(m, 81, start=81, config={"farmHandCostMult": 2})
                self.replay(m, 168, start=82)
            self.assertTrue(m._ROUTE_STATE[0]["v5_gate"])
            self.assertIs(m._ACTIONS, m._V5_LOW_ACTIONS)
            self.assertEqual(m._ROUTE_STATE[0]["v5_expert"], "low")

    def test_fixed_expert_sticky_after_gap_and_new_shops(self):
        m = load_portfolio("high")
        self.replay(m, 168)
        obs = copy.deepcopy(self.prefixes[("low", 0)]["rows"][180]["obs"])
        obs["town"]["unlocked_shops"] = ["ICE_CREAM_SHOP", "YARN_STORE"]
        m.agent(obs)
        self.assertEqual(m._ROUTE_STATE[0]["v5_expert"], "high")
        self.assertIs(m._ACTIONS, m._V5_HIGH_ACTIONS)
        self.assertIs(m._META_SALES, m._V5_HIGH_META_SALES)
        self.assertEqual(m._P3_DIAGNOSTICS["expert_decision_count"], 1)

    def test_identical_retry_is_deepcopy_idempotent_including_step_zero(self):
        m = load_portfolio("high")
        for until in (0, 72, 168):
            self.replay(m, until, start=0 if until == 0 else (1 if until == 72 else 73))
            obs = copy.deepcopy(self.prefixes[("low", 0)]["rows"][until]["obs"])
            saved = ledgers(m, 0)
            counters = (m._P3_DIAGNOSTICS["entry_count"], m._P3_DIAGNOSTICS["expert_decision_count"])
            first = m.agent(obs)
            first["market"].append(["HIRE"])
            obs["remainingOverageTime"] -= 0.5
            second = m.agent(obs)
            self.assertNotEqual(first, second)
            self.assertEqual(saved, ledgers(m, 0))
            self.assertEqual(counters, (m._P3_DIAGNOSTICS["entry_count"], m._P3_DIAGNOSTICS["expert_decision_count"]))

    def test_changed_same_72_retry_can_close_uncommitted_gate_never_reopen(self):
        m = load_portfolio("high")
        self.replay(m, 72)
        obs = copy.deepcopy(self.prefixes[("low", 0)]["rows"][72]["obs"])
        obs["farms"][0]["money"] += 1  # Ensure it is not an identical cache retry.
        obs["farms"][1]["money"] = obs["farms"][0]["money"]
        m.agent(obs)
        self.assertFalse(m._ROUTE_STATE[0]["v5_gate"])
        self.assertFalse(m._P3_HISTORY[0]["entered"])
        self.replay(m, 72, start=72)
        self.assertFalse(m._ROUTE_STATE[0]["v5_gate"])
        self.assertEqual(m._P3_DIAGNOSTICS["entry_count"], 1)

    def test_seat_interleaving_selects_own_pair_and_restart_does_not_wipe_other_seat(self):
        m = load_portfolio("high")
        for step in range(169):
            for seat in (1, 0):
                self.replay(m, step, seat, start=step)
                if step >= 72:
                    self.assertTrue(m._ROUTE_STATE[seat]["v5_gate"])
                expected = m._V5_HIGH_ACTIONS if step >= 168 else m._V5_LOW_ACTIONS
                if step >= 72:
                    self.assertIs(m._ACTIONS, expected)
                    self.assertIs(m._META_SALES, m._V5_HIGH_META_SALES if step >= 168 else m._V5_LOW_META_SALES)
        saved = ledgers(m, 1)
        history1 = copy.deepcopy(m._P3_HISTORY[1])
        self.replay(m, 0, 0)
        self.assertEqual(saved, ledgers(m, 1))
        self.assertEqual(history1, m._P3_HISTORY[1])
        self.assertFalse(m._P3_HISTORY[0]["entered"])
        self.assertIsNone(m._ROUTE_STATE[0]["v5_gate"])
        self.replay(m, 72, 0, start=1)
        self.assertTrue(m._P3_HISTORY[0]["entered"])

    def test_nonzero_backwards_after_entry_does_not_rewind_ledgers(self):
        m = load_portfolio("high")
        self.replay(m, 168)
        saved = ledgers(m, 0)
        obs = copy.deepcopy(self.prefixes[("low", 0)]["rows"][72]["obs"])
        result = m.agent(obs)
        self.assertEqual(saved, ledgers(m, 0))
        self.assertEqual(result["farmer"], ["PASS"])
        self.assertEqual(result["market"], [])
        self.assertEqual(len(result["hands"]), len(obs["farms"][0]["hands"]))
        self.assertEqual(m._ROUTE_STATE[0]["v5_expert"], "high")

    def test_malformed_clock_or_seat_after_entry_cannot_reset_committed_ledgers(self):
        for field, value in (("step", None), ("step", "bad"), ("step", True), ("player", None), ("player", "bad")):
            m = load_portfolio("high")
            self.replay(m, 168)
            saved = {seat: ledgers(m, seat) for seat in (0, 1)}
            obs = copy.deepcopy(self.prefixes[("low", 0)]["rows"][169]["obs"])
            obs[field] = value
            action = m.agent(obs)
            self.assertEqual(saved, {seat: ledgers(m, seat) for seat in (0, 1)})
            self.assertEqual(action["farmer"], ["PASS"])
            self.assertEqual(action["market"], [])
            self.assertIs(m._ACTIONS, m._V5_HIGH_ACTIONS)

    def test_actual_boundary_debts_are_repaid_without_wiping_history(self):
        for seat in (0, 1):
            for expert in ("low", "high"):
                rows = self.prefixes[(expert, seat)]["rows"]
                for step, expected in ((72, 4), (168, 6)):
                    before, after = rows[step]["before"], rows[step]["after"]
                    due = before["_FR_STATE"]["due"]
                    if due.get("FERTILIZER"):
                        self.assertEqual(before["_FR_STATE"]["due_step"], step)
                        self.assertLessEqual(due["FERTILIZER"], expected)
                        self.assertEqual(after["_FR_STATE"]["due"], {})
                        final_sell = sum(o[2] for o in rows[step]["action"]["market"] if o[:2] == ["SELL", "FERTILIZER"])
                        self.assertEqual(final_sell, expected - due["FERTILIZER"])
                    self.assertEqual(after["_META_STATE"]["prev_step"], step)
                    self.assertEqual(after["_META_STATE"]["prev_action"], rows[step]["action"])
                    self.assertEqual(after["_WEED_STATE"]["post_recovery_market_regime"],
                                     before["_WEED_STATE"].get("post_recovery_market_regime", False))
        # Seed 17's unmodified prefixes have no H1 fertilizer debt at these
        # boundaries (inventory arrives at day end). Nonempty repayment is
        # tested separately below, not inferred from empty-ledger parity.

    def test_selected_official_drop_presale_and_boundary_repayment_are_not_empty_ledgers(self):
        for boundary, target in ((72, 4), (168, 6)):
            for expert in ("low", "high"):
                m = load_portfolio(expert)
                self.replay(m, boundary - 2)
                env = make("kaggriculture", configuration={"seed": 17}, debug=False)
                env.reset(2)
                states = copy.deepcopy(self.prefixes[("low", 0)]["rows"][boundary - 2]["game_before"])
                for seat in (0, 1):
                    env.state[seat].observation.update(states[seat])
                env.state[1].observation["farms"] = env.state[0].observation["farms"]
                # Explicit selected legal state: a carrier is at the shed with
                # fertilizer. Only the inventory/position precondition is set;
                # official DROP produces stock, the full agent produces due,
                # and official market actually executes that presale.
                # update() above inserts plain nested dictionaries: access them
                # by key so Struct attribute coercion cannot edit a temporary.
                env.state[0]["observation"]["farms"][0]["farmer"] = [4, 4]
                private = env.state[0]["observation"]["private"]
                private["inventories"][0] = {"FERTILIZER": target}
                private["shed"]["FERTILIZER"] = 0
                env.steps = [env.state] * (boundary - 1)
                passive = {"farmer": ["PASS"], "hands": [], "market": []}
                env.step([{"farmer": ["DROP"], "hands": [], "market": []}, passive])
                before_sale = observation(env, 0)
                self.assertEqual(before_sale["step"], boundary - 1)
                self.assertEqual(before_sale["private"]["shed"]["FERTILIZER"], target)
                sale_action = m.agent(before_sale, env.configuration)
                self.assertEqual(m._FR_STATE[0]["due_step"], boundary)
                self.assertEqual(m._FR_STATE[0]["due"], {"FERTILIZER": target})
                self.assertEqual(sum(o[2] for o in sale_action["market"] if o[:2] == ["SELL", "FERTILIZER"]), target)
                market_before = before_sale["market"]["inventory"]["FERTILIZER"]
                env.step([sale_action, passive])
                boundary_obs = observation(env, 0)
                self.assertEqual(boundary_obs["market"]["inventory"]["FERTILIZER"] - market_before, target)
                result = m.agent(boundary_obs, env.configuration)
                self.assertTrue(m._ROUTE_STATE[0]["v5_gate"])
                self.assertEqual(m._FR_STATE[0]["due"], {})
                self.assertFalse(any(o[:2] == ["SELL", "FERTILIZER"] for o in result["market"]))
                self.assertEqual(m._META_STATE[0]["prev_step"], boundary)
                self.assertEqual(m._META_STATE[0]["prev_action"], result)

    def test_profile_reports_bounded_local_trace_validation_cost(self):
        report = {}
        for (expert, seat), data in self.prefixes.items():
            if expert == "baseline":
                continue
            diag = data["module"]._P3_DIAGNOSTICS
            self.assertEqual(diag["trace_validation_count"], 3)
            self.assertEqual(diag["fallback_count"], 0)
            report[expert + "_seat" + str(seat)] = {
                "trace_validation_count": diag["trace_validation_count"],
                "trace_max_ms": round(diag["trace_validation_max_ms"], 3),
                "max_inner_call_ms": round(max(row["call_ms"] for row in data["rows"]), 3),
            }
        print("P3 prefix timing (local inner call, not official sandbox): " + json.dumps(report, sort_keys=True))

    def test_selected_official_boundary_repairs_clear_active_preserve_market_history(self):
        m = load_portfolio("high")
        self.replay(m, 166)
        obs = copy.deepcopy(self.prefixes[("low", 0)]["rows"][167]["obs"])
        x, y = obs["farms"][0]["farmer"]
        # Selected-state counterexample: a legal WEED on the requested pasture
        # tile. Not a claim that this exact modified board came from seed 17.
        obs["farms"][0]["tiles"][y][x] = {"kind": "WEED"}
        result = m.agent(obs)
        self.assertEqual(result["farmer"], ["DIG"])
        self.assertIn("farmer", m._WEED_STATE[0]["active"])
        env = make("kaggriculture", configuration={"seed": 17}, debug=False)
        env.reset(2)
        env.state[0].observation.update(copy.deepcopy(obs))
        other_obs = copy.deepcopy(self.prefixes[("low", 0)]["rows"][167]["game_before"][1])
        env.state[1].observation.update(other_obs)
        env.state[1].observation["farms"] = env.state[0].observation["farms"]
        # Only align the framework's next recorded index for a selected-state
        # step; this list is not presented as a generated trajectory.
        env.steps = [env.state] * 168
        # Exercise the official unit-work and day reset from this selected state.
        env.step([result, {"farmer": ["PASS"], "hands": [], "market": []}])
        next_obs = copy.deepcopy(env.state[0].observation)
        self.assertEqual(next_obs["hour"], 0)
        self.assertEqual(next_obs["farms"][0]["farmer"], [4, 4])
        # This existing history flag is independent of the active transaction;
        # use a sentinel only for the preservation assertion, not entry/debt.
        m._WEED_STATE[0]["post_recovery_market_regime"] = True
        m.agent(next_obs, env.configuration)
        self.assertEqual(m._WEED_STATE[0]["active"], {})
        self.assertEqual(m._COW_ALIGN_STATE[0]["active"], {})
        self.assertTrue(m._WEED_STATE[0]["post_recovery_market_regime"])
        self.assertIs(m._ACTIONS, m._V5_HIGH_ACTIONS)

    def test_official_loader_uses_unique_final_entrypoint_and_configuration(self):
        entry = get_last_callable(source("high"), path=str(OVERLAY))
        self.assertEqual(entry.__name__, "_p3_portfolio_entrypoint")
        m = load_portfolio("high")
        data = self.prefixes[("low", 0)]
        for step in range(73):
            obs = copy.deepcopy(data["rows"][step]["obs"])
            self.assertEqual(entry(obs, data["config"]), m.agent(obs, data["config"]))
        self.assertEqual(entry.__globals__["_P3_DIAGNOSTICS"]["entry_count"], 1)
        bad_entry = get_last_callable(source("high"), path=str(OVERLAY))
        for row in data["rows"][:73]:
            bad_entry(copy.deepcopy(row["obs"]), {"farmHandCostMult": 2})
        self.assertEqual(bad_entry.__globals__["_P3_DIAGNOSTICS"]["entry_count"], 0)


if __name__ == "__main__":
    unittest.main()
