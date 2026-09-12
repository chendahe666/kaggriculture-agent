import copy
import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from evaluation_learning import fit_bt,losses,time_split
from research_cycle import load_agent,engine,make,aggregate,run_game

class EvaluationTests(unittest.TestCase):
    def test_bt_symmetry(self):
        rows=[{'a':'a','b':'b','outcome':.5}]*20
        self.assertAlmostEqual(fit_bt(rows)['strength']['a'],0)
    def test_bt_direction_and_disconnected(self):
        rows=[{'a':'a','b':'b','outcome':1}]*20
        self.assertGreater(fit_bt(rows)['strength']['a'],fit_bt(rows)['strength']['b'])
        rows.append({'a':'c','b':'d','outcome':0})
        self.assertFalse(fit_bt(rows)['cross_component_ranking_valid'])
    def test_loss(self):
        self.assertAlmostEqual(losses([0,1],[.5,.5])['brier'],.25)
    def test_split_reject_small(self):
        with self.assertRaises(ValueError):time_split([],[])
    def test_split_reject_leak(self):
        rows=[{'episode_id':i,'time':'2026-09-11T00:00:00+00:00'} for i in range(20)]
        with self.assertRaises(ValueError):time_split(rows,rows)
    def test_small_pool_no_fake_ci(self):
        rows=[{'opponent':'b','episode_id':1,'seat':0,'rewards':[1,0],'margin':1,'statuses':['DONE','DONE'],'frames':720,'errors':[]}]
        self.assertIsNone(aggregate(rows)['seed_block_bootstrap_95'])
    def test_all_wins_no_degenerate_certainty(self):
        rows=[{'opponent':'b','seed':i,'seat':0,'rewards':[1,0],'margin':1,'statuses':['DONE','DONE'],'frames':720,'errors':[]} for i in range(6)]
        self.assertIsNone(aggregate(rows)['seed_block_bootstrap_95'])

class MarketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent=load_agent(ROOT/'experiments/track-market-20260911/integrated/main.py')
    def test_price_parity(self):
        for item in self.agent._TRACK_PREMIUM:
            for inventory in [9500,9999,10000,10001,10050,10200,11000]:
                self.assertEqual(self.agent._track_price(item,inventory),engine.market_price(item,inventory))
    def test_floor_does_not_increase_supply(self):
        revenue,inventory=self.agent._track_revenue('WOOL',11000,20)
        self.assertEqual((revenue,inventory),(20,11000))
    def test_official_floor_commit(self):
        farm={'money':0};private={'shed':{'WOOL':2}};market={'inventory':{'WOOL':11000}}
        engine._commit_unit('SELL','WOOL',1,farm,private,market)
        self.assertEqual((farm['money'],private['shed']['WOOL'],market['inventory']['WOOL']),(1,1,11000))
    def test_buy_rejected_when_full(self):
        farm={'money':100};private={'shed':{'WOOL':100}};market={'inventory':{'WHEAT':10000}}
        self.assertFalse(engine._commit_unit('BUY_PRODUCT','WHEAT',25,farm,private,market))
        self.assertEqual(farm['money'],100)
    def test_audit_counts_actual_spending(self):
        def buy(obs):return {'market':[['BUY_SEED','WHEAT',1]]} if obs['step']==0 else {}
        row=run_game([buy,'pass'],{'seed':8,'episodeSteps':4})
        self.assertEqual(row['market_spending'][0]['BUY_SEED:WHEAT'],10)
    def test_endday_drop_overflow(self):
        private={'shed':{'WOOL':99},'inventories':[{'MILK':3}]}
        engine._drop_inventories_to_shed(private,100)
        self.assertEqual(private,{'shed':{'WOOL':99,'MILK':1},'inventories':[{}]})
    def observation(self,step=125):
        env=make('kaggriculture',configuration={'seed':9},debug=False);env.reset(2)
        obs=copy.deepcopy(env.state[0].observation)
        obs['step']=step
        obs['town']['unlocked_shops']=['YARN_STORE']
        obs['private']['shed']['WOOL']=10
        return obs
    def test_sweep_respects_slot_limit(self):
        obs=self.observation();action={'farmer':['PASS'],'hands':[],'market':[['HIRE'] for _ in range(10)]}
        self.assertEqual(self.agent._track_sweep(copy.deepcopy(action),obs),action)
    def test_sweep_no_feed_or_worker_change(self):
        obs=self.observation();action={'farmer':['PASS'],'hands':[],'market':[['BUY_PRODUCT','WHEAT',2]]}
        out=self.agent._track_sweep(copy.deepcopy(action),obs)
        self.assertEqual(out['farmer'],action['farmer']);self.assertEqual(out['market'][0],action['market'][0])
        self.assertEqual(out['market'][1],['SELL','WOOL',2])
    def test_rank_barriers_preserved(self):
        obs=self.observation();obs['private']['shed']['MILK']=10
        action={'farmer':['PASS'],'hands':[],'market':[['SELL','WOOL',5],['BUY_PRODUCT','WHEAT',3],['SELL','MILK',5],['HIRE']]}
        out=self.agent._track_rank(copy.deepcopy(action),obs)
        self.assertEqual(out['market'][1],action['market'][1]);self.assertEqual(out['market'][3],action['market'][3])
    def test_terminal_sweep_unchanged(self):
        obs=self.observation(717);action={'farmer':['PASS'],'hands':[],'market':[]}
        self.assertEqual(self.agent._track_sweep(copy.deepcopy(action),obs),action)
    def environment(self):
        env=make('kaggriculture',configuration={'seed':19},debug=False);env.reset(2)
        return env
    def test_atomic_seed_demand_includes_nonexistent_hand(self):
        env=self.environment();s=env.state[0]
        s.observation.private.seeds['WHEAT']=1
        x,y=s.observation.farms[0].farmer
        env.step([{'farmer':['PLANT','WHEAT'],'hands':[['PLANT','WHEAT']],'market':[]},{}])
        self.assertIsNone(env.state[0].observation.farms[0].tiles[y][x])
    def test_same_turn_seed_purchase_cannot_retroactively_plant(self):
        env=self.environment();s=env.state[0]
        s.observation.private.seeds['WHEAT']=0
        x,y=s.observation.farms[0].farmer
        env.step([{'farmer':['PLANT','WHEAT'],'market':[['BUY_SEED','WHEAT',1]]},{}])
        self.assertIsNone(env.state[0].observation.farms[0].tiles[y][x])
        self.assertEqual(env.state[0].observation.private.seeds['WHEAT'],1)
    def test_drop_overflow_cannot_be_recovered_by_later_sale(self):
        env=self.environment();s=env.state[0]
        s.observation.farms[0].farmer=[4,4]
        s.observation.private.shed={p:0 for p in engine.PRODUCTS}
        s.observation.private.shed['WOOL']=99
        s.observation.private.inventories=[{'MILK':4}]
        env.step([{'farmer':['DROP'],'market':[['SELL','WOOL',99]]},{}])
        self.assertEqual(env.state[0].observation.private.shed['MILK'],1)
        self.assertEqual(env.state[0].observation.private.inventories[0],{})
    def test_lockstep_equal_quotes_both_seats(self):
        env=self.environment()
        for seat in (0,1):env.state[seat].observation.private.shed['WOOL']=20
        env.state[0].observation.market.inventory['WOOL']=10030
        action={'market':[['SELL','WOOL',20]]}
        env.step([action,copy.deepcopy(action)])
        farms=env.state[0].observation.farms
        self.assertEqual(farms[0].money,farms[1].money)
    def test_care_today_is_banked_after_production(self):
        animal=engine._new_animal('COW',0)
        animal.update(fed_today=True,cared_today=True,pending_care_bonus=2)
        farm={'tiles':[[animal]]}
        engine._daily_refresh_animals(farm,7)
        self.assertEqual(animal['yield_units'],3)
        self.assertEqual(animal['pending_care_bonus'],1)
    def test_last_executable_step(self):
        seen=[]
        def policy(obs):seen.append(obs['step']);return {}
        env=self.environment();frames=env.run([policy,'pass'])
        self.assertEqual(len(frames),720);self.assertEqual(max(seen),718)
    def test_wrapper_retry_idempotence(self):
        module=load_agent(ROOT/'experiments/track-market-20260911/integrated/main.py')
        obs=self.observation()
        self.assertEqual(module.agent(copy.deepcopy(obs)),module.agent(copy.deepcopy(obs)))

if __name__=='__main__':unittest.main()
