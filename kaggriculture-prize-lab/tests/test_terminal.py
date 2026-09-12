"""Mechanism tests for the isolated last-day planner, using official transitions."""
import copy
from pathlib import Path
import sys
import types
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / 'scripts'))
from research_cycle import engine, make


def load_terminal(**parameters):
    module = types.ModuleType('terminal_mechanism_test')
    module.__dict__.update(parameters)
    baseline = (LAB / 'public-baseline-v10/main.py').read_text(encoding='utf-8')
    overlay = (LAB / 'experiments/track-terminal-20260912/planner_overlay.py').read_text(encoding='utf-8')
    exec(compile(baseline + '\n' + overlay, 'terminal_candidate', 'exec'), module.__dict__)
    return module


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.module = load_terminal()
        self.env = make('kaggriculture', configuration={'seed': 91212}, debug=False)
        self.env.reset(2)
        self.obs = copy.deepcopy(self.env.state[0].observation)
        self.obs['step'], self.obs['day'], self.obs['hour'] = 710, 29, 14
        farm = self.obs['farms'][0]
        farm['tiles'] = [[None for _ in range(10)] for _ in range(10)]
        farm['unlocked_quadrants'] = ['NW', 'NE', 'SW', 'SE']
        farm['farmer'], farm['hands'] = [4, 4], []
        self.obs['private']['shed'] = {p: 0 for p in engine.PRODUCTS}
        self.obs['private']['inventories'] = [{}]
        self.base = {'farmer': ['PASS'], 'hands': [], 'market': []}

    def plant(self, x, y, crop='WHEAT', planted=27, quantity=1):
        tile = engine._new_plant(crop, planted, 24)
        tile['yield_units'] = quantity
        self.obs['farms'][0]['tiles'][y][x] = tile
        return tile

    def plan(self, depth=2):
        return self.module._terminal_plan(self.obs, self.base, depth)[0]

    def units(self, action):
        return [action['farmer'], *action['hands']]

    def execute_units(self, action):
        farm = self.obs['farms'][0]
        private = self.obs['private']
        for index, unit in enumerate(self.units(action)):
            engine._apply_unit_action(farm, private, index, unit, 10, 29, 24, 100)

    def test_exact_price_and_floor_parity(self):
        for item in engine.PRODUCTS:
            for inventory in (8000, 9500, 9999, 10000, 10001, 10200, 12000):
                self.assertEqual(self.module._terminal_price(item, inventory), engine.market_price(item, inventory))
        self.assertEqual(self.module._terminal_revenue('WOOL', 12000, 9), 9)

    def test_before_window_and_nondefault_configuration_use_original(self):
        sentinel = {'farmer': ['EAST'], 'hands': [], 'market': [['SELL', 'WOOL', 1]]}
        calls = []
        self.module._BASE_TERMINAL_AGENT = lambda obs, config=None: calls.append(obs['step']) or copy.deepcopy(sentinel)
        self.obs['step'] = 695
        self.assertEqual(self.module.agent(self.obs), sentinel)
        self.obs['step'] = 710
        self.assertEqual(self.module.agent(self.obs, {'shedCapacity': 99}), sentinel)
        self.assertEqual(self.module.agent(self.obs, {'marketParams': {'WHEAT': {'base': 99}}}), sentinel)
        self.assertEqual(calls, [695, 710, 710])

    def test_exact_final_arrival_collects_observed_strawberries(self):
        self.obs['step'], self.obs['hour'] = 709, 13
        self.obs['farms'][0]['farmer'] = [0, 9]
        self.plant(0, 9, 'STRAWBERRY', 13, 2)
        self.assertEqual(self.plan()['farmer'], ['HARVEST'])
        self.obs['step'], self.obs['hour'] = 710, 14
        self.assertNotEqual(self.plan()['farmer'], ['HARVEST'])

    def test_final_step_deposits_and_sells_same_turn(self):
        self.obs['step'], self.obs['hour'] = 718, 22
        self.obs['private']['inventories'] = [{'MILK': 4, 'WOOL': 2}]
        action = self.plan()
        self.assertEqual(action['farmer'], ['DROP'])
        self.execute_units(action)
        for op, item, n in action['market']:
            for _ in range(n):
                price = engine.market_price(item, self.obs['market']['inventory'][item])
                self.assertTrue(engine._commit_unit(op, item, price, self.obs['farms'][0],
                                                    self.obs['private'], self.obs['market'], 100))
        self.assertFalse(any(self.obs['private']['shed'].values()))
        self.assertEqual(self.obs['private']['inventories'], [{}])

    def test_water_bonus_is_same_day_and_harvest_is_reserved(self):
        self.plant(4, 4)
        self.assertEqual(self.plan()['farmer'], ['WATER'])
        self.execute_units(self.plan())
        self.assertEqual(self.obs['farms'][0]['tiles'][4][4]['yield_units'], 2)
        self.obs['step'] += 1
        self.obs['hour'] += 1
        self.assertEqual(self.plan()['farmer'], ['HARVEST'])

    def test_no_future_value_for_ongoing_water_or_immature_crop(self):
        self.plant(4, 4, 'STRAWBERRY', 13, 0)
        self.plant(4, 3, 'WHEAT', 28, 1)
        self.assertEqual(self.plan()['farmer'], ['PASS'])
        self.assertEqual(self.module._terminal_tasks(self.obs), [])

    def test_decay_before_arrival_is_not_harvestable(self):
        tile = self.plant(0, 0, 'STRAWBERRY', 13, 1)
        tile['max_lifespan_step'] = 710
        self.assertEqual(self.plan()['farmer'], ['PASS'])

    def test_fertilizer_collects_without_feed_or_care(self):
        animal = engine._new_animal('COW', 0)
        animal.update(yield_units=0, fertilizer_available=True)
        self.obs['farms'][0]['tiles'][4][4] = animal
        self.assertEqual(self.plan()['farmer'], ['COLLECT_FERTILIZER'])
        self.execute_units(self.plan())
        self.assertEqual(self.obs['private']['inventories'][0], {'FERTILIZER': 1})

    def test_joint_assignment_does_not_double_book_harvest(self):
        self.obs['farms'][0]['hands'] = [[4, 4]]
        self.obs['private']['inventories'] = [{}, {}]
        self.plant(4, 4, 'STRAWBERRY', 13, 4)
        self.assertEqual(self.units(self.plan()).count(['HARVEST']), 1)

    def test_two_harvest_modes_share_one_claim(self):
        self.obs['farms'][0]['hands'] = [[4, 4]]
        self.obs['private']['inventories'] = [{}, {}]
        self.plant(4, 4)
        actions = self.units(self.plan())
        self.assertEqual(sum(a[0] in ('HARVEST', 'WATER') for a in actions), 1)

    def test_shared_capacity_uses_place_and_keeps_leftover_cargo(self):
        self.obs['step'], self.obs['hour'] = 718, 22
        self.obs['farms'][0]['hands'] = [[4, 5]]
        self.obs['private']['inventories'] = [{'WHEAT': 10}, {'WOOL': 6}]
        self.obs['private']['shed']['CARROT'] = 92
        action = self.plan()
        self.assertEqual(action['farmer'], ['PLACE', 'WHEAT', 2])
        self.assertEqual(action['hands'], [['DROP']])
        self.execute_units(action)
        self.assertEqual(sum(self.obs['private']['shed'].values()), 100)
        self.assertEqual(self.obs['private']['inventories'][0], {'WHEAT': 8})

    def test_full_shed_does_not_discard_cargo_before_market(self):
        self.obs['private']['shed']['WHEAT'] = 100
        self.obs['private']['inventories'] = [{'MILK': 5}]
        action = self.plan()
        self.assertEqual(action['farmer'], ['PASS'])
        self.assertIn(['SELL', 'WHEAT', 100], action['market'])
        self.execute_units(action)
        self.assertEqual(self.obs['private']['inventories'], [{'MILK': 5}])

    def test_preserves_hires_and_respects_market_slots(self):
        self.base['market'] = [['HIRE'] for _ in range(5)]
        self.obs['private']['shed'] = {p: 1 for p in engine.PRODUCTS}
        market = self.plan()['market']
        self.assertEqual(sum(a == ['HIRE'] for a in market), 5)
        self.assertEqual(len(market), 10)

    def test_repeat_observation_does_not_accumulate_diagnostics(self):
        self.module._BASE_TERMINAL_AGENT = lambda obs, config=None: copy.deepcopy(self.base)
        self.plant(4, 4)
        first = self.module.agent(self.obs)
        diagnostics = dict(self.module._TERMINAL_DIAGNOSTICS)
        self.assertEqual(self.module.agent(copy.deepcopy(self.obs)), first)
        self.assertEqual(self.module._TERMINAL_DIAGNOSTICS, diagnostics)

    def test_depth_controls_bounded_node_expansion(self):
        for x, y in ((4, 4), (4, 3), (3, 4), (5, 3)):
            self.plant(x, y, 'STRAWBERRY', 13, 2)
        nodes = [self.module._terminal_plan(self.obs, self.base, depth)[1]['search_nodes']
                 for depth in (1, 2, 3)]
        self.assertGreater(nodes[1], nodes[0])
        self.assertGreater(nodes[2], nodes[1])

    def test_build_parameters_are_not_overwritten_by_overlay(self):
        for depth in (1, 2, 3):
            module = load_terminal(TERMINAL_DEPTH=depth, TERMINAL_MODE='transport')
            self.assertEqual(module.TERMINAL_DEPTH, depth)
            self.assertEqual(module.TERMINAL_MODE, 'transport')

    def test_transport_preserves_future_production_before_returning(self):
        self.module._ACTIONS = [copy.deepcopy(self.base) for _ in range(719)]
        self.obs['farms'][0]['farmer'] = [0, 0]
        self.obs['private']['inventories'] = [{'MILK': 2}]
        self.module._ACTIONS[712]['farmer'] = ['HARVEST']
        action, _ = self.module._terminal_transport(self.obs, self.base)
        self.assertEqual(action['farmer'], ['PASS'])
        self.module._ACTIONS[712]['farmer'] = ['PASS']
        action, _ = self.module._terminal_transport(self.obs, self.base)
        self.assertEqual(action['farmer'], ['EAST'])

    def test_transport_preserves_current_water_and_harvest(self):
        for operation in ('WATER', 'HARVEST'):
            self.base['farmer'] = [operation]
            self.obs['private']['inventories'] = [{'MILK': 2}]
            self.module._ACTIONS = [copy.deepcopy(self.base) for _ in range(719)]
            action, _ = self.module._terminal_transport(self.obs, self.base)
            self.assertEqual(action['farmer'], [operation])

    def test_remote_drop_is_not_projected_as_shed_inventory(self):
        self.obs['farms'][0]['farmer'] = [0, 0]
        self.obs['private']['inventories'] = [{'MILK': 2}]
        self.base['farmer'] = ['DROP']
        self.module._ACTIONS = [copy.deepcopy(self.base) for _ in range(719)]
        self.module._ACTIONS[711]['farmer'] = ['HARVEST']
        action, _ = self.module._terminal_transport(self.obs, self.base)
        self.assertEqual(action['farmer'], ['DROP'])
        self.assertEqual(action['market'], [])


if __name__ == '__main__':
    unittest.main()
