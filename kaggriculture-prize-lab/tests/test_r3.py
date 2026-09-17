import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    s=importlib.util.spec_from_file_location('r3_'+name,ROOT/f'experiments/track-r3-20260917/{name}/main.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class OpeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=load('adaptive');cls.clean=load('clean')
    def setUp(self):
        self.obs=dict(step=1,player=0,farms=[dict(money=1952,hires_today=0)])
        self.action=dict(farmer=['PASS'],hands=[],market=[['SELL','WHEAT',30],['HIRE'],['HIRE'],['BUY_ANIMAL','COW',2]])
    def test_order_and_no_mutation(self):
        before=copy.deepcopy(self.action);a=self.m._r3_reorder(self.obs,self.action)
        self.assertEqual(a['market'][:2],[['HIRE'],['SELL','WHEAT',30]])
        self.assertEqual(a['market'][2:],before['market'][2:]);self.assertEqual(self.action,before)
        self.assertEqual(a['farmer'],before['farmer'])
    def test_cash_boundary(self):
        for cash,changed in [(0,False),(.99,False),(1,True)]:
            self.obs['farms'][0]['money']=cash
            self.assertEqual(self.m._r3_reorder(self.obs,self.action)!=self.action,changed)
    def test_fibonacci_guard(self):
        self.obs['farms'][0].update(money=4,hires_today=4)
        self.assertEqual(self.m._r3_reorder(self.obs,self.action),self.action)
    def test_configuration_guard(self):
        for cfg in ({'farmHandCostMult':2},{'startingMoney':1000},{'maxMarketOrdersPerTurn':1}):self.assertEqual(self.m._r3_reorder(self.obs,self.action,cfg),self.action)
    def test_other_steps_unchanged(self):
        for t in (0,2,23,718):
            self.obs['step']=t;self.assertEqual(self.m._r3_reorder(self.obs,self.action),self.action)
    def test_no_excess_combination_noop(self):
        a=dict(self.action,market=[['HIRE'],['BUY_ANIMAL','COW',2]])
        self.assertEqual(self.m._r3_reorder(self.obs,a),a)
    def test_clean_parameters(self):
        self.assertEqual(self.clean._OPEN_STEP0,[['BUY_PRODUCT','WHEAT',5]])
        self.assertEqual(self.clean._OPEN_ATTACK,0)

if __name__=='__main__':unittest.main()
