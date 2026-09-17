"""G4 exact-engine file-loader experiments, whole-game budget and trace receipts."""
import argparse
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import time
from concurrent.futures import ProcessPoolExecutor,as_completed
import run_r2 as r

LAB=r.LAB
OUT=LAB/'results/g4-20260917'
r.OUT=OUT
r.POLICIES.update({'A':'experiments/track-r2-20260916/route-counter-35/main.py',
 'R3':'experiments/track-r3-20260917/clean/main.py',
 'jaxa':'inbox/r3-20260917/sources/jaxa/main.py',
 'medgm':'inbox/g4-20260917/medgm/main.py',
 'v47':'inbox/g4-20260917/sources/v47/main.py'})
for name in ('C','M','P','MP'):
    r.POLICIES[name]=f'experiments/track-g4-20260917/{name}/main.py'
r.POLICIES['public-v47']='experiments/track-g4-20260917/public-v47/main.py'

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def job(task):
    tick=time.perf_counter();rc=r.imports();loaded=time.perf_counter()
    if task['kind']=='audit':
        from elite_economics import audit
        row=audit(LAB/f'inbox/g4-20260917/replays/episode-{task["episode_id"]}-replay.json')
        row.update(task,runner_sha256=r.sha(__file__),wall_seconds=time.perf_counter()-tick)
        r.save(OUT/'runs'/f'{task["key"]}.json',row)
        return dict(key=task['key'],valid=row['valid'],wall_seconds=row['wall_seconds'])
    original=rc.make;extra={}
    import kaggle_environments.agent as loader
    original_load=loader.get_last_callable;loaded_agents=[]
    def load(*a,**kw):
        result=original_load(*a,**kw);loaded_agents.append(result);return result
    loader.get_last_callable=load
    def make(*a,**kw):
        env=original(*a,**kw);run=env.run
        def traced(players):
            frames=run(players)
            extra['trace']=[dict(step=t,actions=digest([s.action for s in f]),
                states=digest([{k:v for k,v in s.observation.items() if k!='remainingOverageTime'} for s in f]),
                shops=list(f[0].observation.town.unlocked_shops)) for t,f in enumerate(frames)]
            extra['daily']=[dict(step=t,money=[f[i].observation.farms[i]['money'] for i in (0,1)],
                land=[f[i].observation.farms[i]['unlocked_quadrants'] for i in (0,1)],
                animals=[{k:sum(isinstance(tile,dict) and tile.get('animal')==k for row in f[i].observation.farms[i]['tiles'] for tile in row) for k in ('COW','SHEEP','GOOSE')} for i in (0,1)]) for t,f in enumerate(frames) if t%24==0 or t==719]
            extra['telemetry']=[{k:v for k,v in getattr(fn,'__globals__',{}).items() if k in ('_G4_REPORT','_V44Y_REPORT','_Y_REPORT','_PG_REPORT')} for fn in loaded_agents]
            return frames
        env.run=traced;return env
    rc.make=make
    profiler=cProfile.Profile() if task.get('profile') else None
    try:
        if profiler:profiler.enable()
        result=r.job(task)
    finally:
        if profiler:profiler.disable()
        rc.make=original
        loader.get_last_callable=original_load
    done=time.perf_counter()
    if profiler:
        stats=pstats.Stats(profiler)
        extra['profile']=[dict(file=k[0],line=k[1],function=k[2],calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for k,v in sorted(stats.stats.items(),key=lambda x:x[1][3],reverse=True)[:65]]
    extra.update(import_seconds=loaded-tick,worker_total_seconds=done-tick,profiled=bool(profiler),runner_sha256=r.sha(__file__))
    r.save(OUT/'traces'/f"{task['key']}.json",extra)
    return dict(**result,import_seconds=loaded-tick,worker_total_seconds=done-tick)

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidates',nargs='+',default=[]);p.add_argument('--opponents',nargs='+',default=[]);p.add_argument('--seeds',nargs='+',type=int,default=[]);p.add_argument('--audit',nargs='+',type=int);p.add_argument('--seats',nargs='+',type=int,default=[0,1]);p.add_argument('--phase',required=True);p.add_argument('--profile',action='store_true');p.add_argument('--workers',type=int,default=2);a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    lock=OUT/'runner.lock'
    with lock.open('x') as f:f.write(str(os.getpid()))
    try:
        jobs=[dict(kind='league',candidate=c,opponent=o,seed=s,seat=t,profile=a.profile,phase=a.phase,key=f'{a.phase}-{c}-vs-{o}-{s}-{t}') for c in a.candidates for o in a.opponents for s in a.seeds for t in a.seats]
        if a.audit:jobs=[dict(kind='audit',episode_id=e,phase=a.phase,key=f'audit-{e}') for e in a.audit]
        assert jobs
        previous=[j for pth in OUT.glob('plan-*.json') for j in json.loads(pth.read_text())['jobs']]
        keys={j['key'] for j in previous}
        assert not any(j['key'] in keys for j in jobs),'Already attempted; inspect receipts, never rerun silently'
        assert len(previous)+len(jobs)<=64,'Whole-game cap (including attempts) exceeded'
        r.save(OUT/f'plan-{time.time_ns()}.json',dict(jobs=jobs,prior_attempts=len(previous),cap=64,hashes={n:r.sha(r.resolve(n)) for n in a.candidates+a.opponents},runner_sha256=r.sha(__file__)))
        tick=time.perf_counter()
        with ProcessPoolExecutor(max_workers=a.workers,max_tasks_per_child=1) as pool:
            for f in as_completed([pool.submit(job,j) for j in jobs]):print(json.dumps(f.result()),flush=True)
        print(json.dumps(dict(batch_wall_seconds=time.perf_counter()-tick)),flush=True)
    finally:lock.unlink()

if __name__=='__main__':main()
