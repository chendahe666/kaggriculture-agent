"""R3 receipts. Actual file-path official loader; full-game cap64."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import run_r2 as r

LAB=Path(__file__).resolve().parents[1];OUT=LAB/'results/r3-20260917'
r.OUT=OUT
r.POLICIES.update({'A':'experiments/track-r2-20260916/route-counter-35/main.py',
 'B':'experiments/track-r2-20260916/reactive-funding/main.py',
 'jaxa':'inbox/r3-20260917/sources/jaxa/main.py','pipe8':'inbox/r3-20260917/sources/pipe8/main.py'})
for n in ('clean','adaptive','counter5','counter15','counter25'):
    r.POLICIES[n]=f'experiments/track-r3-20260917/{n}/main.py'

def run(task):
    if task['kind']=='league':return r.job(task)
    started=datetime.now(timezone.utc).isoformat();r.imports()
    from elite_economics import audit
    row=audit(LAB/f'inbox/r3-20260917/replays/episode-{task["episode_id"]}-replay.json')
    row.update(task,started_utc=started,completed_utc=datetime.now(timezone.utc).isoformat())
    r.save(OUT/'runs'/f'{task["key"]}.json',row)
    return dict(key=task['key'],valid=row['valid'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['league','audit']);p.add_argument('--candidates',nargs='+');p.add_argument('--opponents',nargs='+');p.add_argument('--seeds',nargs='+',type=int,default=[917301]);p.add_argument('--episodes',nargs='+',type=int);p.add_argument('--workers',type=int,default=2);a=p.parse_args()
    if a.mode=='audit':jobs=[dict(kind='audit',episode_id=i,key=f'audit-{i}') for i in a.episodes]
    else:jobs=[dict(kind='league',candidate=c,opponent=o,seed=s,seat=t,key=f'{c}-vs-{o}-{s}-{t}') for c in a.candidates for o in a.opponents for s in a.seeds for t in (0,1)]
    (OUT/'runs').mkdir(parents=True,exist_ok=True);pending=[]
    for j in jobs:
        path=OUT/'runs'/f'{j["key"]}.json'
        if path.exists():
            if j['kind']=='league':
                old=json.loads(path.read_text(encoding='utf-8'));assert old['candidate_sha256']==r.sha(r.resolve(j['candidate'])) and old['opponent_sha256']==r.sha(r.resolve(j['opponent']))
        else:pending.append(j)
    assert len(list((OUT/'runs').glob('*.json')))+len(pending)<=64
    r.save(OUT/f'plan-{time.time_ns()}.json',dict(jobs=pending,cap=64,runner_sha256=r.sha(__file__)))
    with ProcessPoolExecutor(max_workers=a.workers,max_tasks_per_child=1) as pool:
        for f in as_completed([pool.submit(run,j) for j in pending]):print(json.dumps(f.result()),flush=True)
