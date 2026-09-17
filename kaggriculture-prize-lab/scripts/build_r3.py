"""Immutable R3 variants of frozen A; no edits to submitted source."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]
parent=ROOT/'experiments/track-r2-20260916/route-counter-35/main.py'
raw=parent.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c4c890f4e73b72dbbcc93edfc22ec1c17f40c9751cd2206214f38351fe227282'
patches={
'clean':'''\n# R3: non-speculative funded opening. V46 production/advance layers unchanged.
# All inherited Apache-2.0 notices retained. Mechanism inspired by Nathan Jacob pipe-8.
_OPEN_STEP0=[['BUY_PRODUCT','WHEAT',5]]
''',
'adaptive':'''\n# R3: inventory liquidation delayed by exactly one affordable atomic hire.
# All inherited Apache-2.0 notices retained; original wrapper for this project.
_R3_PARENT=agent
_R3_REPORT={'delayed':0,'declined':0}
def _r3_reorder(obs,action,cfg=None):
    standard=cfg is None or all(cfg.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10),('startingMoney',3000),('farmHandCostMult',1)])
    if not standard or int(obs['step'])!=1:return action
    orders=action.get('market',[])
    if len(orders)<2 or orders[1]!=['HIRE'] or orders[0][:2]!=['SELL','WHEAT']:return action
    farm=obs['farms'][int(obs['player'])]
    a,b=1,1
    for _ in range(int(farm.get('hires_today',0))):a,b=b,a+b
    if float(farm['money'])<a:
        _R3_REPORT['declined']+=1
        return action
    _R3_REPORT['delayed']+=1
    return dict(action,market=[orders[1],orders[0]]+orders[2:])
def agent(observation,configuration=None):
    if int(observation['step'])==0:_R3_REPORT.update(delayed=0,declined=0)
    action=_R3_PARENT(observation,configuration)
    return _r3_reorder(observation,action,configuration)
agent=globals().pop('agent')
'''}
for name,patch in patches.items():
    path=ROOT/f'experiments/track-r3-20260917/{name}/main.py';path.parent.mkdir(parents=True,exist_ok=True)
    data=raw+patch.encode()
    if path.exists():assert path.read_bytes()==data
    else:path.write_bytes(data)
    manifest=dict(name=name,parent=str(parent.relative_to(ROOT)),parent_sha256=hashlib.sha256(raw).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),patch=patch)
    (path.parent/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(name,manifest['sha256'])
