"""Bounded R2 local games; immutable per-job receipts and source hashes."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

LAB=Path(__file__).resolve().parents[1]
OUT=LAB/'results/r2-20260916'
POLICIES={
 'cok':'public-baseline-v10/main.py',
 'old_ab':'experiments/track-terminal-20260912/depth2-timing-safe-file/main.py',
 'lonespear':'public-lonespear/main.py',
 'deepesh':'public-deepesh-20260912/main.py',
 'maverick':'public-maverick-20260912/main.py',
 'v46':'inbox/r2-20260916/sources/v46/extracted-main.py',
 'tetsutani':'inbox/r2-20260916/sources/tetsutani/extracted-main.py',
 'arlene':'inbox/opponents/strong-source-audit-20260912/lynnsakurai-farming-score-v3/verified-output/main.py',
}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def resolve(name):
    p=LAB/POLICIES.get(name,f'experiments/track-r2-20260916/{name}/main.py')
    assert p.resolve().is_relative_to(LAB.resolve()) and p.is_file()
    return p


def imports():
    # Suppress unrelated optional-environment native C++ registration warnings.
    saved=os.dup(2)
    try:
        with open(os.devnull,'w') as null:
            os.dup2(null.fileno(),2)
            import research_cycle
    finally:
        os.dup2(saved,2);os.close(saved)
    return research_cycle


def job(task):
    rc=imports()
    started=datetime.now(timezone.utc).isoformat(); tick=time.perf_counter()
    dest=OUT/'runs'/f"{task['key']}.json"
    assert not dest.exists()
    if task['kind']=='audit':
        from elite_economics import audit
        row=audit(LAB/f"inbox/r2-20260916/replays/episode-{task['episode_id']}-replay.json")
    else:
        candidate=resolve(task['candidate']);other=resolve(task['opponent']) if task['kind']=='league' else None
        cfg={'seed':task.get('seed',0),'episodeSteps':720}
        if task['kind']=='tape':
            replay=json.loads((LAB/f"inbox/r2-20260916/replays/episode-{task['episode_id']}-replay.json").read_text())
            cfg=dict(replay['configuration']);cfg['seed']=replay['info']['seed'];cfg.pop('runTimeout',None)
            players=[rc.tape(replay,0),rc.tape(replay,1)]
        else:
            players=[str(other),str(other)]
        players[task['seat']]=str(candidate)
        env=rc.make('kaggriculture',configuration=cfg,debug=False)
        frames=env.run(players); final=frames[-1]
        errors=[x.get('stderr') for frame in env.logs for x in frame if x.get('stderr')]
        durations=[[float(frame[i].get('duration',0)) for frame in env.logs if len(frame)==2] for i in (0,1)]
        requested=[]
        for seat in (0,1):
            from collections import Counter
            c=Counter()
            for frame in frames[1:]:
                a=frame[seat].action
                if isinstance(a,dict):
                    for cmd in [a.get('farmer',[]),*(a.get('hands') or [])]:
                        if cmd:c[str(cmd[0])]+=1
            requested.append(dict(c))
        row={'candidate_sha256':sha(candidate),'opponent_sha256':sha(other) if other else None,
             'entrypoint':'actual file path via official loader', 'rewards':[s.reward for s in final],
             'statuses':[s.status for s in final],'frames':len(frames),'errors':errors,
             'max_call_seconds':[max(x or [0]) for x in durations],
             'min_overage_seconds':[min(float(f[i].observation.get('remainingOverageTime',60)) for f in frames) for i in (0,1)],
             'shops':list(final[0].observation.town.unlocked_shops),'requested_actions':requested,
             'opening':[{'step':t,'money':[s.observation.farms[i]['money'] for i,s in enumerate(frames[t])],
                         'market':[s.action.get('market',[]) if isinstance(s.action,dict) else [] for s in frames[t]],
                         'seeds':[dict(s.observation.private.seeds) for s in frames[t]],
                         'shed':[dict(s.observation.private.shed) for s in frames[t]]} for t in (1,2,3,23)],
             'final_farms':[dict(s.observation.farms[i]) for i,s in enumerate(final)],
             'final_private':[dict(s.observation.private) for s in final]}
        row['valid']=row['statuses']==['DONE','DONE'] and len(frames)==720 and not errors
        row['margin']=float(row['rewards'][task['seat']] or 0)-float(row['rewards'][1-task['seat']] or 0)
    row.update(task,started_utc=started,completed_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.perf_counter()-tick,
               engine_sha256=sha(rc.engine.__file__),runner_sha256=sha(__file__))
    save(dest,row)
    return {k:row.get(k) for k in ('key','valid','rewards','margin','wall_seconds')}


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['audit','league','tape']);p.add_argument('--candidates',nargs='+');p.add_argument('--opponents',nargs='+');p.add_argument('--seeds',nargs='+',type=int,default=[916101]);p.add_argument('--episodes',nargs='+',type=int);p.add_argument('--workers',type=int,default=2)
    a=p.parse_args();jobs=[]
    if a.mode=='audit':
        jobs=[dict(kind='audit',episode_id=i,key=f'audit-{i}') for i in a.episodes]
    elif a.mode=='league':
        for c in a.candidates:
            for o in a.opponents:
                for seed in a.seeds:
                    for seat in (0,1):
                        jobs.append(dict(kind='league',candidate=c,opponent=o,seed=seed,seat=seat,key=f'{c}-vs-{o}-{seed}-{seat}'))
    else:
        sel=json.loads((OUT/'replay-selection.json').read_text(encoding='utf-8'))
        for c in a.candidates:
            for i in a.episodes:
                seat=next(r['seat'] for r in sel['rows'] if r['episode_id']==i)
                jobs.append(dict(kind='tape',candidate=c,episode_id=i,seat=seat,key=f'{c}-tape-{i}'))
    (OUT/'runs').mkdir(parents=True,exist_ok=True)
    pending=[]
    for j in jobs:
        dest=OUT/'runs'/f"{j['key']}.json"
        if dest.exists():
            old=json.loads(dest.read_text(encoding='utf-8'))
            if j['kind']!='audit':assert old['candidate_sha256']==sha(resolve(j['candidate']))
        else:pending.append(j)
    assert len(list((OUT/'runs').glob('*.json')))+len(pending)<=96,'R2 full-game cap exceeded'
    save(OUT/f"plan-{time.time_ns()}.json",{'created_utc':datetime.now(timezone.utc).isoformat(),'jobs':pending,
        'hashes':{n:sha(resolve(n)) for j in pending for n in (j.get('candidate'),j.get('opponent')) if n},
        'runner_sha256':sha(__file__),'cap':96})
    with ProcessPoolExecutor(max_workers=a.workers,max_tasks_per_child=1) as pool:
        for f in as_completed([pool.submit(job,j) for j in pending]):print(json.dumps(f.result()),flush=True)


if __name__=='__main__':main()
