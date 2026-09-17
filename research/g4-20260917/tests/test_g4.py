import copy
import importlib.util
from pathlib import Path
import unittest

LAB=Path(__file__).resolve().parents[1]
def load(name):
    s=importlib.util.spec_from_file_location('g4_'+name,LAB/f'experiments/track-g4-20260917/{name}/main.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class IntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=load('MP')
    def setUp(self):
        self.obs={'step':192,'player':0,'farms':[dict(money=3000,hires_today=0,unlocked_quadrants=['NW','NE'],farmer=[4,4],hands=[],tiles=[[None]*10 for _ in range(10)])],
                  'private':dict(shed={'COW':0,'SHEEP':0,'WOOL':0},seeds={},inventories=[{}]),
                  'market':dict(inventory={k:10000 for k in self.m._R37_MARKET_PARAMS},prices={k:100 for k in self.m._R37_MARKET_PARAMS}),
                  'town':dict(unlocked_shops=['YARN_STORE'])}
        self.a=dict(farmer=['PASS'],hands=[],market=[['BUY_ANIMAL','COW',1]])
        self.st=self.m._g4_state(self.obs)
        self.project=self.m.projected_shed;self.view=self.m.FarmView
        self.m.FarmView=lambda o:o
        self.m.projected_shed=lambda a,o:dict(o['private']['shed'])
    def tearDown(self):self.m.projected_shed=self.project;self.m.FarmView=self.view
    def intent(self):return dict(kind='purchase',slot=0,precondition=True,expected=['BUY_ANIMAL','COW',1],replacement=['BUY_ANIMAL','SHEEP',1])
    def test_purchase_admission_input_immutable(self):
        before=copy.deepcopy(self.a);out,yes=self.m._g4_resolve(self.obs,self.a,[self.intent()])
        self.assertEqual(out['market'],[['BUY_ANIMAL','SHEEP',1]]);self.assertEqual(len(yes),1);self.assertEqual(before,self.a)
    def test_cash_decline(self):
        self.obs['farms'][0]['money']=599
        out,yes=self.m._g4_resolve(self.obs,self.a,[self.intent()]);self.assertEqual(out,self.a);self.assertFalse(yes)
    def test_cash_boundary(self):
        self.obs['farms'][0]['money']=600
        self.assertEqual(len(self.m._g4_resolve(self.obs,self.a,[self.intent()])[1]),1)
    def test_no_double_claim(self):self.assertEqual(len(self.m._g4_resolve(self.obs,self.a,[self.intent(),self.intent()])[1]),1)
    def test_native_obligation_included(self):
        self.a['market'].append(['BUY_LAND']);self.obs['farms'][0]['money']=2500
        self.assertFalse(self.m._g4_resolve(self.obs,self.a,[self.intent()])[1])
    def test_sale_not_assumed_financing(self):
        self.a['market'].append(['SELL','WOOL',100]);self.obs['farms'][0]['money']=500
        self.assertFalse(self.m._g4_resolve(self.obs,self.a,[self.intent()])[1])
    def test_ordering_second_intent_reuses_interface(self):
        self.a['market']=[['SELL','MILK',3],['SELL','WOOL',4]]
        out,yes=self.m._g4_resolve(self.obs,self.a,[dict(kind='ordering',slot=-1,precondition=True,orders=list(reversed(self.a['market'])))])
        self.assertEqual(len(yes),1);self.assertEqual(out['market'][0][1],'WOOL')
    def test_reorder_barrier(self):
        self.a['market']=[['HIRE'],['SELL','WOOL',4]]
        self.assertFalse(self.m._g4_resolve(self.obs,self.a,[dict(kind='ordering',slot=-1,precondition=True,orders=list(reversed(self.a['market'])))])[1])
    def test_ordering_cannot_change_quantity(self):
        self.a['market']=[['SELL','WOOL',4]]
        self.assertFalse(self.m._g4_resolve(self.obs,self.a,[dict(kind='ordering',slot=-1,precondition=True,orders=[['SELL','WOOL',5]])])[1])
    def test_receipt_not_request(self):
        self.m._g4_herd(self.obs,self.a,self.st);self.assertEqual(self.st['credit'],0)
        self.obs['step']+=1;self.m._g4_herd(self.obs,dict(self.a,market=[]),self.st)
        self.assertEqual(self.st['credit'],0);self.assertEqual(self.m._G4_REPORT['partial'],1)
    def test_partial_receipt(self):
        self.a['market'][0][2]=2;self.m._g4_herd(self.obs,self.a,self.st)
        self.obs['step']+=1;self.obs['private']['shed']['SHEEP']=1
        self.m._g4_herd(self.obs,dict(self.a,market=[]),self.st)
        self.assertEqual(self.st['credit'],1);self.assertEqual(self.m._G4_REPORT['partial'],1)
    def test_pickup_physical_confirmation(self):
        self.st['credit']=1;self.obs['private']['shed']['SHEEP']=1
        a=dict(self.a,farmer=['PICKUP','COW',1],market=[])
        out=self.m._g4_herd(self.obs,a,self.st)
        self.assertEqual(out['farmer'],['PICKUP','SHEEP',1]);self.assertEqual(self.st['credit'],1)
        self.obs['private']['shed']['SHEEP']=0;self.obs['private']['inventories'][0]['SHEEP']=1
        self.m._g4_herd(self.obs,dict(a,farmer=['PASS']),self.st);self.assertEqual(self.st['credit'],0)
    def test_place_only_empty_pasture(self):
        self.obs['private']['inventories'][0]['SHEEP']=1
        a=dict(self.a,farmer=['PLACE','COW',1],market=[])
        self.assertEqual(self.m._g4_herd(self.obs,a,self.st)['farmer'],a['farmer'])
        self.obs['farms'][0]['tiles'][4][4]=dict(kind='PASTURE',animal=None)
        self.assertEqual(self.m._g4_herd(self.obs,a,self.st)['farmer'],['PLACE','SHEEP',1])
    def test_no_yarn_no_purchase_change(self):
        self.obs['town']['unlocked_shops']=[]
        self.assertEqual(self.m._g4_herd(self.obs,self.a,self.st),self.a)
    def test_outside_purchase_window(self):
        self.obs['step']=12*24
        self.assertEqual(self.m._g4_herd(self.obs,self.a,self.st),self.a)
    def test_new_game_resets_commitments(self):
        self.st['credit']=4;self.assertEqual(self.m._g4_state(self.obs)['credit'],0)
    def test_market_purchase_lists_untouched(self):
        old=self.m._v44y_clone_gate;self.m._v44y_clone_gate=lambda obs:True
        try:
            self.obs['step']=400;self.assertEqual(self.m._g4_market(self.obs,self.a),self.a)
        finally:self.m._v44y_clone_gate=old
    def test_entrypoint(self):
        self.assertEqual([v for v in vars(self.m).values() if callable(v)][-1].__name__,'g4_agent')

if __name__=='__main__':unittest.main()
