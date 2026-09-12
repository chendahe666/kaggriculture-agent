"""Small engine/interface checks; no full matches or external source execution."""
import copy
from pathlib import Path
import sys
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "scripts"))
sys.path.insert(0, str(LAB / "tests"))
from research_cycle import engine, make
from test_terminal_timing import load_timing


def load_safety(**parameters):
    module = load_timing(**parameters)
    path = LAB / "experiments/track-terminal-20260912/safety_overlay.py"
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


class TimingSafetyTests(unittest.TestCase):
    def setUp(self):
        self.module = load_safety(TERMINAL_TIMING_ONLY=True)
        env = make("kaggriculture", configuration={"seed": 17}, debug=False)
        env.reset(2)
        self.obs = copy.deepcopy(env.state[0].observation)
        self.obs["town"]["unlocked_shops"] = ["SMOOTHIE_SHOP"]
        self.action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.trace = [copy.deepcopy(self.action) for _ in range(719)]
        self.module._ACTIONS = self.trace
        self.module._select_route = lambda obs, step: (self.trace, self.module._META_SALES)
        self.module._META_SALES = {}

    def at(self, step):
        self.obs["step"], self.obs["day"], self.obs["hour"] = step, step // 24, step % 24

    def history(self, until):
        for step in range(until + 1):
            self.at(step)
            self.module._p2b_observe(self.obs)

    def market_result(self, action):
        # Invoke the official market phase only, not env.run/step/full games.
        env = make("kaggriculture", configuration={"seed": 17}, debug=False)
        env.reset(2)
        state = env.state
        state[0].observation.farms[0]["money"] = 0
        state[0].observation.private["shed"].update(MILK=10, WHEAT=1)
        state[0].action = copy.deepcopy(action)
        state[1].action = copy.deepcopy(self.action)
        engine._process_market(state, env)
        return state[0].observation.farms[0]["hires_today"]

    def test_old_counterexample_loses_hire_repair_preserves_it(self):
        self.at(696)
        self.obs["farms"][0]["money"] = 0
        self.obs["private"]["shed"].update(MILK=10, WHEAT=1)
        original = {"farmer": ["PASS"], "hands": [],
                    "market": [["SELL", "MILK", 10], ["HIRE"], ["SELL", "WHEAT", 1]]}
        state = {"reliable": True, "ever_products": set()}
        old, _ = self.module._P2S_ORIGINAL_APPLY(self.obs, original, state)
        repaired, _ = self.module._p2b_apply(self.obs, original, state)
        self.assertEqual(self.market_result(original), 1)
        self.assertEqual(self.market_result(old), 0)
        self.assertEqual(self.market_result(repaired), 1)
        self.assertEqual(repaired, original)
        self.assertEqual(self.module._P2S_DIAGNOSTICS["cash_guard_fallbacks"], 1)

    def test_cash_guard_reserves_all_future_hires_without_sales_credit(self):
        self.at(696)
        self.obs["farms"][0]["money"] = 3
        self.obs["private"]["shed"]["MILK"] = 50
        self.trace[697]["market"] = [["HIRE"] for _ in range(4)]
        original = {**self.action, "market": [["SELL", "MILK", 50]]}
        repaired, _ = self.module._p2b_apply(self.obs, original, {"reliable": True, "ever_products": set()})
        self.assertEqual(repaired, original)
        self.obs["farms"][0]["money"] = 7
        repaired, info = self.module._p2b_apply(self.obs, original, {"reliable": True, "ever_products": set()})
        self.assertEqual(self.module._meta_sell_qty(repaired, "MILK"), 0)
        self.assertEqual(info["held_units"], 50)

    def test_cancelled_new_fr_and_h5_do_not_cancel_next_observation_sales(self):
        self.history(696)
        self.at(697)
        self.obs["private"]["shed"]["MILK"] = 10
        self.trace[698]["market"] = [["SELL", "MILK", 4]]
        self.module._META_SALES = {704: {"MILK": 3}}
        meta = self.module._META_STATE[0]
        meta.update(last_step=696, h4_active=True, clone_confidence=5,
                    h5_due={699: {"WOOL": 2}})
        # Confirm this is a real old-interface failure, not only a fabricated
        # ledger: the unchanged COK/timing composition creates phantom debts.
        old = load_timing(TERMINAL_TIMING_ONLY=True)
        old._ACTIONS = copy.deepcopy(self.trace)
        old._META_SALES = copy.deepcopy(self.module._META_SALES)
        old._select_route = lambda obs, step: (old._ACTIONS, old._META_SALES)
        old._META_STATE[0] = copy.deepcopy(meta)
        old_obs = copy.deepcopy(self.obs)
        for step in range(697):
            old_obs["step"], old_obs["day"], old_obs["hour"] = step, step // 24, step % 24
            old._p2b_observe(old_obs)
        old_final = old.agent(self.obs)
        self.assertEqual(old._meta_sell_qty(old_final, "MILK"), 0)
        self.assertEqual(old._FR_STATE[0]["due"], {"MILK": 4})
        self.assertEqual(old._META_STATE[0]["h5_due"][704], {"MILK": 3})
        self.assertEqual(old._meta_sell_qty(old._META_STATE[0]["prev_action"], "MILK"), 7)
        final = self.module.agent(self.obs)
        self.assertEqual(self.module._meta_sell_qty(final, "MILK"), 0)
        self.assertEqual(self.module._FR_STATE[0]["due"], {})
        self.assertEqual(meta["h5_due"], {699: {"WOOL": 2}})
        self.assertEqual(meta["prev_action"], final)
        self.assertTrue(meta["h4_active"])
        self.assertEqual(meta["clone_confidence"], 5)
        self.assertEqual(self.module._P2S_DIAGNOSTICS["cancelled_new_fr_units"], 4)
        self.assertEqual(self.module._P2S_DIAGNOSTICS["cancelled_new_h5_units"], 3)
        # On the next observation, inspect COK before an outer timing decision:
        # the cancelled prepayment must not erase its legitimate route sale.
        self.at(698)
        next_source = self.module._BASE_TERMINAL_AGENT(self.obs)
        self.assertEqual(self.module._meta_sell_qty(next_source, "MILK"), 4)
        self.assertEqual(meta["h5_due"], {699: {"WOOL": 2}})

    def test_incoming_preterminal_debts_are_consumed_normally_not_wiped(self):
        self.history(695)
        self.at(696)
        self.obs["private"]["shed"]["MILK"] = 10
        self.trace[696]["market"] = [["SELL", "MILK", 5]]
        self.module._FR_STATE[0] = {"last_step": 695, "due_step": 696, "due": {"MILK": 2}}
        self.module._META_STATE[0].update(last_step=695, h5_due={696: {"MILK": 1}, 699: {"WOOL": 2}})
        # Insufficient cash for an unrelated future hire disables holding, so
        # the original source action reveals repayment of both incoming debts.
        self.obs["farms"][0]["money"] = 0
        self.trace[699]["market"] = [["HIRE"]]
        final = self.module.agent(self.obs)
        self.assertEqual(self.module._meta_sell_qty(final, "MILK"), 2)
        self.assertEqual(self.module._FR_STATE[0]["due"], {})
        self.assertEqual(self.module._META_STATE[0]["h5_due"], {699: {"WOOL": 2}})
        self.assertEqual(self.module._P2S_DIAGNOSTICS["cancelled_new_fr_units"], 0)
        self.assertEqual(self.module._P2S_DIAGNOSTICS["cancelled_new_h5_units"], 0)

    def test_partial_cancellation_preserves_existing_future_debt(self):
        self.at(697)
        self.obs["private"]["shed"]["MILK"] = 10
        self.module._META_STATE[0]["h5_due"] = {704: {"MILK": 2}}
        before = self.module._p2s_ledger_snapshot(0)
        self.module._FR_STATE[0].update(due_step=698, due={"MILK": 5})
        self.module._META_STATE[0]["h5_due"][704]["MILK"] += 3
        source = {**self.action, "market": [["SELL", "MILK", 10]]}
        final = {**self.action, "market": [["SELL", "MILK", 6]]}
        self.module._p2s_reconcile(self.obs, 697, before, source, final)
        self.assertEqual(self.module._FR_STATE[0]["due"], {"MILK": 4})
        self.assertEqual(self.module._META_STATE[0]["h5_due"], {704: {"MILK": 2}})

    def test_previous_supply_uses_final_action_and_post_work_shed(self):
        self.at(718)
        self.obs["private"]["shed"]["MILK"] = 1
        self.obs["private"]["inventories"] = [{"MILK": 4}]
        before = self.module._p2s_ledger_snapshot(0)
        final = {"farmer": ["DROP"], "hands": [], "market": [["SELL", "MILK", 5]]}
        self.module._p2s_reconcile(self.obs, 718, before, self.action, final)
        meta = self.module._META_STATE[0]
        self.assertEqual(meta["prev_shed"]["MILK"], 5)
        self.assertEqual(meta["prev_action"], final)
        self.assertEqual(min(meta["prev_shed"]["MILK"], self.module._meta_sell_qty(meta["prev_action"], "MILK")), 5)

    def test_repeated_observation_and_other_seat_are_unchanged(self):
        self.history(695)
        self.at(696)
        self.obs["private"]["shed"]["MILK"] = 10
        self.trace[696]["market"] = [["SELL", "MILK", 10]]
        other_before = self.module._p2s_ledger_snapshot(1)
        action = self.module.agent(self.obs)
        ledgers = self.module._p2s_ledger_snapshot(0)
        diagnostics = dict(self.module._P2S_DIAGNOSTICS)
        self.assertEqual(self.module.agent(copy.deepcopy(self.obs)), action)
        self.assertEqual(self.module._p2s_ledger_snapshot(0), ledgers)
        self.assertEqual(self.module._P2S_DIAGNOSTICS, diagnostics)
        self.assertEqual(self.module._p2s_ledger_snapshot(1), other_before)

    def test_unique_last_callable_and_preterminal_delegation(self):
        callables = [(k, v) for k, v in self.module.__dict__.items() if callable(v)]
        self.assertEqual(callables[-1][0], "_p2s_submission_entrypoint")
        self.at(695)
        before = self.module._p2s_ledger_snapshot(0)
        expected = {**self.action, "market": [["SELL", "MILK", 1]]}
        self.module._P2S_TIMING_AGENT = lambda obs, config=None: copy.deepcopy(expected)
        self.assertEqual(self.module.agent(self.obs), expected)
        self.assertEqual(self.module._p2s_ledger_snapshot(0), before)
        self.assertEqual(self.module._P2S_DIAGNOSTICS["ledger_reconciliations"], 0)


if __name__ == "__main__":
    unittest.main()
