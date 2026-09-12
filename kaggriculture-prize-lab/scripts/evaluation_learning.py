"""Small, auditable relative Bradley-Terry proxy and time-separated calibration.

Input JSON array: {episode_id, time (ISO UTC), a (version/hash), b, outcome}.
outcome is 1/.5/0 for a. Never use this file in a submitted policy.
Unknown versions receive zero-prior strength, explicitly reported as unknown.
This is NOT Kaggle's rating implementation. Ties use a half-outcome approximation.
"""
import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def sigmoid(x):
    x=max(-30,min(30,x))
    return 1/(1+math.exp(-x))

def fit_bt(rows, regularization=1.0, iterations=3000):
    if not rows or regularization<=0:
        raise ValueError('nonempty matches and positive regularization required')
    names=sorted({r[k] for r in rows for k in ('a','b')})
    strength={n:0.0 for n in names}
    degree=defaultdict(int)
    graph=defaultdict(set)
    for r in rows:
        if r['a']==r['b'] or r['outcome'] not in (0,.5,1):
            raise ValueError('invalid identity/outcome')
        degree[r['a']]+=1; degree[r['b']]+=1
        graph[r['a']].add(r['b']); graph[r['b']].add(r['a'])
    components=[]; seen=set()
    for name in names:
        if name in seen: continue
        todo=[name]; component=[]
        while todo:
            n=todo.pop()
            if n in seen: continue
            seen.add(n); component.append(n); todo.extend(graph[n]-seen)
        components.append(sorted(component))
    # Gradient Lipschitz <= max_degree/2 + regularization.
    rate=1/(max(degree.values())*.5+regularization)
    for _ in range(iterations):
        gradient={n:regularization*strength[n] for n in names}
        for r in rows:
            residual=sigmoid(strength[r['a']]-strength[r['b']])-r['outcome']
            gradient[r['a']]+=residual; gradient[r['b']]-=residual
        if max(map(abs,gradient.values()))<1e-8: break
        strength={n:strength[n]-rate*gradient[n] for n in names}
    return {'strength':strength,'components':components,'regularization':regularization,
            'cross_component_ranking_valid':len(components)==1}

def losses(outcomes, probabilities):
    if not outcomes or len(outcomes)!=len(probabilities):
        raise ValueError('aligned nonempty outcomes required')
    clipped=[max(1e-8,min(1-1e-8,p)) for p in probabilities]
    return {'brier':sum((p-y)**2 for y,p in zip(outcomes,clipped))/len(clipped),
            'log_loss':-sum(y*math.log(p)+(1-y)*math.log(1-p) for y,p in zip(outcomes,clipped))/len(clipped)}

def time_split(train,test):
    if len(train)<20 or len(test)<20:
        raise ValueError('at least 20 train and 20 FUTURE test matches required; still exploratory')
    train_ids={r['episode_id'] for r in train}; test_ids={r['episode_id'] for r in test}
    if train_ids & test_ids:
        raise ValueError('episode leakage across time split')
    if len(train_ids)!=len(train) or len(test_ids)!=len(test):
        raise ValueError('duplicate episodes; choose a unique observation per episode')
    if max(datetime.fromisoformat(r['time']) for r in train)>=min(datetime.fromisoformat(r['time']) for r in test):
        raise ValueError('train must precede test strictly')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--train',required=True,type=Path);p.add_argument('--test',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    train=json.loads(args.train.read_text(encoding='utf-8'));test=json.loads(args.test.read_text(encoding='utf-8'))
    time_split(train,test)
    model=fit_bt(train)
    s=model['strength']; probabilities=[sigmoid(s.get(r['a'],0)-s.get(r['b'],0)) for r in test]
    unknown=sum(r['a'] not in s or r['b'] not in s for r in test)
    result={'metric_version':'bt-proxy-v1','model':model,'test_games':len(test),'unknown_pair_count':unknown,
            'uniform_reference':losses([r['outcome'] for r in test],[.5]*len(test)),
            'future_test':losses([r['outcome'] for r in test],probabilities),
            'automatic_promotion':False,
            'note':'one future batch is evidence, not permission to tune on it or replace official W/T/L objective',
            'train_sha256':hashlib.sha256(args.train.read_bytes()).hexdigest(),
            'test_sha256':hashlib.sha256(args.test.read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
