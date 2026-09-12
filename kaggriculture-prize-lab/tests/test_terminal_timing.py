"""Mechanism tests for P2b; no full matches or hidden-opponent features."""
import copy
from pathlib import Path
import sys
import types
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / 'scripts'))
from research_cycle import engine, make


def load_timing(**parameters):
    module = types.ModuleType('terminal_timing_test')
    module.__dict__.update(parameters)
    paths = [LAB / 'public-baseline-v10/main.py',
             LAB / 'experiments/track-terminal-20260912/planner_overlay.py',
             LAB / 'experiments/track-terminal-20260912/timing_overlay.py']
    exec(compile('\n'.join(p.read_text(encoding='utf-8') for p in paths),
                 'terminal_timing_candidate', 'exec'), module.__dict__)
    return module


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.module = load_timing()
        env = make('kaggriculture', configuration={'seed': 17}, debug=False)
        env.reset(2)
        self.obs = copy.deepcopy(env.state[0].observation)
        for farm in self.obs['farms']:
            farm['tiles'] = [[None for _ in range(10)] for _ in range(10)]
            farm['hands'] = []
        self.obs['private']['shed'] = {item: 0 for item in engine.PRODUCTS}
        self.obs['private']['inventories'] = [{}]
        self.obs['town']['unlocked_shops'] = ['SMOOTHIE_SHOP']
        self.action = {'farmer': ['PASS'], 'hands': [], 'market': []}
        self.module._ACTIONS = [copy.deepcopy(self.action) for _ in range(719)]

    def at(self, step):
        self.obs['step'], self.obs['day'], self.obs['hour'] = step, step // 24, step % 24

    def history(self, until=696, producer=None):
        for step in range(until + 1):
            self.at(step)
            if producer and step == 24:
                self.obs['farms'][1]['tiles'][0][0] = engine._new_animal(producer, 0)
            if producer and step == 48:
                self.obs['farms'][1]['tiles'][0][0] = None
            state = self.module._p2b_observe(self.obs)
        return state

    def apply(self, state):
        return self.module._p2b_apply(self.obs, self.action, state)

    def sell_quantity(self, action, item):
        return sum(o[2] for o in action['market'] if len(o) >= 3 and o[:2] == ['SELL', item])

    def test_full_history_absence_and_future_demand_allow_hold(self):
        state = self.history()
        self.obs['private']['shed']['MILK'] = 10
        self.action['market'] = [['SELL', 'MILK', 10]]
        result, info = self.apply(state)
        self.assertTrue(state['reliable'])
        self.assertEqual(self.sell_quantity(result, 'MILK'), 0)
        self.assertEqual(info['held_units'], 10)

    def test_old_removed_cow_still_rules_out_absence(self):
        state = self.history(producer='COW')
        self.obs['private']['shed']['MILK'] = 10
        self.action['market'] = [['SELL', 'MILK', 10]]
        self.assertIn('MILK', state['ever_products'])
        self.assertEqual(self.apply(state)[0], self.action)

    def test_gap_or_missing_board_disables_hold_until_new_game(self):
        self.at(0)
        self.module._p2b_observe(self.obs)
        self.at(696)
        state = self.module._p2b_observe(self.obs)
        self.assertFalse(state['reliable'])
        self.at(697)
        self.assertFalse(self.module._p2b_observe(self.obs)['reliable'])
        self.at(0)
        self.assertTrue(self.module._p2b_observe(self.obs)['reliable'])
        self.at(1)
        self.obs['farms'][1]['tiles'] = []
        self.assertFalse(self.module._p2b_observe(self.obs)['reliable'])

    def test_current_empty_board_at_late_first_call_is_not_proof(self):
        self.at(700)
        state = self.module._p2b_observe(self.obs)
        self.obs['private']['shed']['MILK'] = 10
        self.action['market'] = [['SELL', 'MILK', 10]]
        result, info = self.apply(state)
        self.assertEqual(result, self.action)
        self.assertEqual(info['unreliable_history_calls'], 1)

    def test_buyable_wheat_and_fertilizer_never_held(self):
        state = self.history()
        self.obs['town']['unlocked_shops'] = ['PIZZA_SHOP']
        self.obs['private']['shed'].update(WHEAT=10, FERTILIZER=10)
        self.action['market'] = [['SELL', 'WHEAT', 10], ['SELL', 'FERTILIZER', 10]]
        self.assertEqual(self.apply(state)[0], self.action)

    def test_last_consumption_is_716_not_after_terminal_sale(self):
        state = self.history(until=716)
        self.obs['private']['shed']['MILK'] = 10
        self.action['market'] = [['SELL', 'MILK', 10]]
        self.assertGreater(self.module._p2b_remaining_demand(self.obs, 'MILK', 716), 0)
        self.assertEqual(self.sell_quantity(self.apply(state)[0], 'MILK'), 0)
        self.at(717)
        self.assertEqual(self.module._p2b_remaining_demand(self.obs, 'MILK', 717), 0)
        self.assertEqual(self.apply(state)[0], self.action)

    def test_no_current_shop_demand_does_not_hold(self):
        # At 696 the town center itself still consumes one milk. Start after it.
        state = self.history(until=697)
        self.obs['town']['unlocked_shops'] = ['PET_CAFE']
        self.obs['private']['shed']['MILK'] = 10
        self.action['market'] = [['SELL', 'MILK', 10]]
        self.assertEqual(self.apply(state)[0], self.action)

    def test_reused_zero_slot_does_not_overwrite_a_retained_product(self):
        orders = [['SELL', 'WOOL', 5]] + [['HIRE'] for _ in range(9)]
        self.assertIsNone(self.module._p2b_set_sales(orders, {'CARROT': 2, 'WOOL': 3}))
        result = self.module._p2b_set_sales(orders, {'CARROT': 2, 'WOOL': 0})
        self.assertEqual(result[0], ['SELL', 'CARROT', 2])

    def test_inventory_upper_bound_counts_each_source_once(self):
        self.at(696)
        self.obs['private']['shed']['MILK'] = 10
        self.obs['private']['inventories'] = [{'WOOL': 5}]
        wheat = engine._new_plant('WHEAT', 27, 24)
        wheat['yield_units'] = 1
        self.obs['farms'][0]['tiles'][0][0] = wheat
        cow = engine._new_animal('COW', 0)
        cow.update(yield_units=3, fertilizer_available=True)
        self.obs['farms'][0]['tiles'][0][1] = cow
        self.assertEqual(self.module._p2b_inventory_upper_bound(self.obs), 10 + 5 + 3 + 3 + 1)

    def test_capacity_forces_only_necessary_release(self):
        state = self.history()
        self.obs['private']['shed']['MILK'] = 80
        self.obs['private']['inventories'] = [{'WOOL': 40}]
        self.action['market'] = [['SELL', 'MILK', 80]]
        result, info = self.apply(state)
        self.assertEqual(self.sell_quantity(result, 'MILK'), 20)
        self.assertEqual(info['capacity_released_units'], 20)
        self.assertEqual(info['held_units'], 60)

    def test_fixed_sales_already_release_capacity(self):
        state = self.history()
        self.obs['private']['shed'].update(MILK=50, WHEAT=50)
        self.obs['private']['inventories'] = [{'WOOL': 20}]
        self.action['market'] = [['SELL', 'WHEAT', 50], ['SELL', 'MILK', 50]]
        result, _ = self.apply(state)
        self.assertEqual(self.sell_quantity(result, 'WHEAT'), 50)
        self.assertEqual(self.sell_quantity(result, 'MILK'), 0)

    def test_full_remaining_hire_cost_is_reserved_at_696(self):
        state = self.history()
        self.obs['farms'][0]['money'] = 0
        self.obs['private']['shed']['MILK'] = 10
        self.action['market'] = [['SELL', 'MILK', 10]] + [['HIRE'] for _ in range(5)]
        self.module._ACTIONS[697]['market'] = [['HIRE'] for _ in range(3)]
        scheduled = self.module._p2b_scheduled_orders(self.action, 696)
        self.assertEqual(self.module._p2b_hiring_reserve(self.obs, scheduled), 54)
        result, info = self.apply(state)
        self.assertGreaterEqual(self.module._terminal_revenue('MILK', 10000, self.sell_quantity(result, 'MILK')), 54)
        self.assertEqual(result['market'][0][0], 'SELL')
        self.assertEqual(sum(o == ['HIRE'] for o in result['market']), 5)
        self.assertEqual(info['finance_released_units'], 1)

    def test_remaining_purchase_program_is_preserved(self):
        state = self.history()
        self.obs['private']['shed']['MILK'] = 10
        self.action['market'] = [['SELL', 'MILK', 10]]
        self.module._ACTIONS[700]['market'] = [['BUY_SEED', 'WHEAT', 2]]
        result, info = self.apply(state)
        self.assertEqual(result, self.action)
        self.assertEqual(info['purchase_guard_calls'], 1)

    def test_final_drop_is_projected_once_and_all_products_sold(self):
        state = self.history(until=718)
        self.obs['private']['shed']['MILK'] = 10
        self.obs['private']['inventories'] = [{'MILK': 2, 'WOOL': 4}]
        self.action['farmer'] = ['DROP']
        result, _ = self.apply(state)
        self.assertEqual(self.sell_quantity(result, 'MILK'), 12)
        self.assertEqual(self.sell_quantity(result, 'WOOL'), 4)
        self.assertEqual(result['farmer'], ['DROP'])

    def test_timing_only_uses_original_work_and_joint_uses_planner(self):
        self.module._BASE_TERMINAL_AGENT = lambda obs, config=None: {'farmer': ['NORTH'], 'hands': [], 'market': []}
        self.module._P2B_PLANNER_AGENT = lambda obs, config=None: {'farmer': ['SOUTH'], 'hands': [], 'market': []}
        self.at(0)
        self.module.TERMINAL_TIMING_ONLY = True
        self.assertEqual(self.module.agent(self.obs)['farmer'], ['NORTH'])
        self.at(1)
        self.module.TERMINAL_TIMING_ONLY = False
        self.assertEqual(self.module.agent(self.obs)['farmer'], ['SOUTH'])

    def test_repeat_observation_is_idempotent_and_does_not_break_history(self):
        self.module._P2B_PLANNER_AGENT = lambda obs, config=None: copy.deepcopy(self.action)
        self.at(0)
        first = self.module.agent(self.obs)
        self.assertEqual(self.module.agent(copy.deepcopy(self.obs)), first)
        self.assertTrue(self.module._P2B_HISTORY[0]['reliable'])
        self.at(1)
        self.module.agent(self.obs)
        self.assertTrue(self.module._P2B_HISTORY[0]['reliable'])

    def test_last_callable_is_unique_submission_entrypoint(self):
        callables = [(k, v) for k, v in self.module.__dict__.items() if callable(v)]
        self.assertEqual(callables[-1][0], '_p2b_submission_entrypoint')
        self.assertIs(callables[-1][1], self.module._p2b_submission_entrypoint)


if __name__ == '__main__':
    unittest.main()
