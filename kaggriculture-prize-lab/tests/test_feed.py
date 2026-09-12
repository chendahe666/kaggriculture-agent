import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from research_cycle import LAB, load_agent, make


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.module = load_agent(LAB/'experiments/track-feed-20260912/reserve6/main.py')
        env = make('kaggriculture', configuration={'seed': 12}, debug=False)
        env.reset(2)
        self.obs = copy.deepcopy(env.state[0].observation)
        self.obs['step'] = 100
        self.obs['private']['shed'] = {'WHEAT': 20}
        self.obs['farms'][0]['money'] = 5000
        self.module._ACTIONS = [{'farmer': ['PASS'], 'hands': [], 'market': []} for _ in range(720)]

    def test_netting_preserves_slots_and_other_orders(self):
        action = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL','WHEAT',10], ['HIRE'], ['BUY_PRODUCT','WHEAT',10]]}
        out = self.module._feed_netting(copy.deepcopy(action), self.obs)
        self.assertEqual(out['market'], [['SELL','WHEAT',0], ['HIRE'], ['BUY_PRODUCT','WHEAT',0]])

    def test_netting_does_not_assume_intra_turn_financing(self):
        self.obs['private']['shed']['WHEAT'] = 0
        action = {'farmer':['PASS'], 'hands':[], 'market':[['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',10]]}
        self.assertEqual(self.module._feed_netting(copy.deepcopy(action), self.obs), action)

    def test_reserve_uses_next_pickups(self):
        self.module._ACTIONS[101]['farmer'] = ['PICKUP','WHEAT',8]
        self.module._ACTIONS[106]['farmer'] = ['PICKUP','WHEAT',5]
        self.module._ACTIONS[107]['farmer'] = ['PICKUP','WHEAT',99]
        action = {'farmer':['PASS'], 'hands':[], 'market':[['SELL','WHEAT',20],['BUY_PRODUCT','WHEAT',20]]}
        out = self.module._feed_reserve(action, self.obs)
        self.assertEqual(out['market'], [['SELL','WHEAT',7],['BUY_PRODUCT','WHEAT',0]])

    def test_reserve_accounts_current_pickup_before_market(self):
        self.module._ACTIONS[101]['farmer'] = ['PICKUP','WHEAT',8]
        action = {'farmer':['PICKUP','WHEAT',17], 'hands':[], 'market':[]}
        out = self.module._feed_reserve(action, self.obs)
        self.assertEqual(out['market'], [['BUY_PRODUCT','WHEAT',5]])

    def test_emergency_order_never_exceeds_ten_slots(self):
        self.module._ACTIONS[101]['farmer'] = ['PICKUP','WHEAT',50]
        action = {'farmer':['PASS'], 'hands':[], 'market':[['HIRE'] for _ in range(10)]}
        self.assertEqual(len(self.module._feed_reserve(action, self.obs)['market']), 10)

    def test_zero_quantity_is_engine_noop(self):
        env = make('kaggriculture', configuration={'seed': 1}, debug=False)
        env.reset(2)
        env.step([{'market':[['SELL','WHEAT',0],['BUY_PRODUCT','WHEAT',0]]}, {}])
        self.assertEqual(env.state[0].observation.farms[0]['money'], 3000)

    def aware(self):
        module = load_agent(LAB/'experiments/track-feed-20260912/jit-aware/main.py')
        module._ACTIONS = copy.deepcopy(self.module._ACTIONS)
        return module

    def test_busy_market_requires_two_turn_preparation(self):
        module = self.aware()
        module._ACTIONS[101]['market'] = [['HIRE'] for _ in range(10)]
        module._ACTIONS[101]['farmer'] = ['PICKUP','WHEAT',6]
        module._ACTIONS[102]['farmer'] = ['PICKUP','WHEAT',18]
        self.obs['private']['shed']['WHEAT'] = 0
        action = {'farmer':['PASS'], 'hands':[], 'market':[]}
        self.assertEqual(module._feed_reserve(action, self.obs)['market'], [['BUY_PRODUCT','WHEAT',24]])

    def test_day_return_credit_with_capacity(self):
        module = self.aware()
        self.obs['step'] = 119
        self.obs['private']['inventories'] = [{'WHEAT':6}]
        action = {'farmer':['PASS'], 'hands':[], 'market':[]}
        self.assertEqual(module._feed_safe_day_return(self.obs, action, 10), 6)
        self.obs['private']['shed']['WOOL'] = 80
        self.assertEqual(module._feed_safe_day_return(self.obs, action, 10), 0)

    def test_no_credit_for_unmodelled_cargo_change(self):
        module = self.aware()
        self.obs['step'] = 119
        self.obs['private']['inventories'] = [{'WHEAT':6}]
        action = {'farmer':['HARVEST'], 'hands':[], 'market':[]}
        self.assertEqual(module._feed_safe_day_return(self.obs, action, 10), 0)

    def test_repeat_observation_does_not_update_twice(self):
        module = self.aware()
        a = module.agent(self.obs)
        before = dict(module._FEED_DIAGNOSTICS)
        b = module.agent(copy.deepcopy(self.obs))
        self.assertEqual(a, b)
        self.assertEqual(before, dict(module._FEED_DIAGNOSTICS))

    def delivery(self):
        m = load_agent(LAB/'experiments/track-feed-20260912/idle-delivery/main.py')
        m._ACTIONS = copy.deepcopy(self.module._ACTIONS)
        self.obs['step'] = 116
        self.obs['private']['shed'] = {'WHEAT':80}
        self.obs['private']['inventories'] = [{'MILK':4}]
        return m

    def test_idle_delivery_places_only_non_feed_goods(self):
        m = self.delivery()
        action = {'farmer':['PASS'], 'hands':[], 'market':[]}
        out = m._delivery_apply(self.obs, action)
        self.assertEqual(out['farmer'], ['PLACE','MILK',4])
        self.assertEqual(out['market'], [['SELL','MILK',4]])

    def test_delivery_never_replaces_later_production(self):
        m = self.delivery()
        m._ACTIONS[118]['farmer'] = ['FEED']
        action = {'farmer':['PASS'], 'hands':[], 'market':[]}
        self.assertEqual(m._delivery_apply(self.obs, copy.deepcopy(action)), action)

    def test_delivery_respects_market_slot_and_shed_capacity(self):
        m = self.delivery()
        action = {'farmer':['PASS'], 'hands':[], 'market':[['HIRE'] for _ in range(10)]}
        self.assertEqual(m._delivery_apply(self.obs, copy.deepcopy(action)), action)
        self.obs['private']['shed']['WHEAT'] = 100
        action['market'] = []
        self.assertEqual(m._delivery_apply(self.obs, copy.deepcopy(action)), action)

    def test_delivery_requires_time_to_arrive_and_place(self):
        m = self.delivery()
        self.obs['step'] = 119
        self.obs['farms'][0]['farmer'] = [0,0]
        action = {'farmer':['PASS'], 'hands':[], 'market':[]}
        self.assertEqual(m._delivery_apply(self.obs, copy.deepcopy(action)), action)

    def test_guard_preserves_original_orders(self):
        m = load_agent(LAB/'experiments/track-feed-20260912/feed-guard/main.py')
        m._ACTIONS = copy.deepcopy(self.module._ACTIONS)
        m._ACTIONS[101]['farmer'] = ['PICKUP','WHEAT',10]
        action = {'farmer':['PASS'], 'hands':[], 'market':[['SELL','WHEAT',20],['HIRE']]}
        prefix = copy.deepcopy(action['market'])
        out = m._feed_reserve(action, self.obs)
        self.assertEqual(out['market'][:2], prefix)
        self.assertEqual(out['market'][2], ['BUY_PRODUCT','WHEAT',10])

    def test_guard_accounts_original_purchase(self):
        m = load_agent(LAB/'experiments/track-feed-20260912/feed-guard/main.py')
        m._ACTIONS = copy.deepcopy(self.module._ACTIONS)
        m._ACTIONS[101]['farmer'] = ['PICKUP','WHEAT',10]
        action = {'farmer':['PASS'], 'hands':[], 'market':[['SELL','WHEAT',20],['BUY_PRODUCT','WHEAT',10]]}
        self.assertEqual(m._feed_reserve(copy.deepcopy(action), self.obs), action)


if __name__ == '__main__':
    unittest.main()
