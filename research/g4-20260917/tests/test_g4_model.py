"""Synthetic official-market checks; not independent whole-game samples."""
import copy
import importlib.util
import itertools
from pathlib import Path
import sys
import unittest
LAB=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(LAB/'scripts'))
import run_r2

class MarketModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc=run_r2.imports()
        p=LAB/'experiments/track-g4-20260917/public-v47/main.py'
        spec=importlib.util.spec_from_file_location('v47_test',p)
        cls.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.m)
    def test_actual_file_entrypoint(self):
        from kaggle_environments.agent import get_last_callable
        path=LAB/'experiments/track-g4-20260917/public-v47/main.py'
        self.assertEqual(get_last_callable(path.read_text(encoding='utf-8'),path=str(path)).__name__,'_y_agent_shopherd')
    def test_lockstep_sell_matches_official(self):
        for level in (9900,10000,10100,12000):
            for opp_order in (('WOOL','MILK'),('MILK','WOOL')):
                env=self.rc.make('kaggriculture',configuration={'seed':17},debug=False);env.reset(2)
                for s in env.state:
                    s.observation.private.shed['WOOL']=13;s.observation.private.shed['MILK']=9
                market=env.state[0].observation.market
                for item in ('WOOL','MILK'):market.inventory[item]=level
                inv=dict(market.inventory);stock={'WOOL':13,'MILK':9}
                orders=[['SELL','MILK',9],['SELL','WOOL',13]]
                rival=[['SELL',i,stock[i]] for i in opp_order]
                params=self.m._v44y_params({'market':market})
                expected=self.m._v44y_lockstep(orders,rival,inv,stock,stock,params)
                money=[f.money for f in env.state[0].observation.farms]
                env.step([dict(farmer=['PASS'],market=orders),dict(farmer=['PASS'],market=rival)])
                actual=tuple(f.money-money[i] for i,f in enumerate(env.state[0].observation.farms))
                self.assertEqual(actual,expected)
    def test_factorized_cache_matches_full_sell_model(self):
        params=self.m._R37_MARKET_PARAMS
        stock={k:11 for k in ('MILK','WOOL','STRAWBERRY')};inv={k:10007 for k in stock}
        opp=[['SELL',k,n] for k,n in stock.items()]
        margin=self.m._v44y_factor_margin(opp,inv,stock,params)
        for perm in itertools.permutations(opp):
            a,b=self.m._v44y_lockstep(list(perm),opp,inv,stock,stock,params)
            self.assertEqual(margin(list(perm)),a-b)
    def test_price_curve_engine_boundaries(self):
        for item in self.m._R37_MARKET_PARAMS:
            for inv in (9500,9999,10000,10001,10500,12000):
                self.assertEqual(self.m._v44y_price(item,inv,self.m._R37_MARKET_PARAMS),self.rc.engine.market_price(item,inv))
    def test_herd_decision_uses_current_shops(self):
        m=self.m
        self.assertIsNone(m._y_target('COW',[],m._Y_CFG))
        self.assertEqual(m._y_target('COW',['YARN_STORE'],m._Y_CFG),'SHEEP')
        self.assertEqual(m._y_target('GOOSE',['YARN_STORE'],m._Y_CFG),'SHEEP')

if __name__=='__main__':unittest.main()
