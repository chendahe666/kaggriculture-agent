"""Reproducible offline research; never submits or accesses credentials.

Replay opponents are fixed action tapes, NOT live policies. Calibration compares
every public/private game state before any counterfactual evidence is admitted.
"""
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as engine


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_agent(path):
    spec = importlib.util.spec_from_file_location('isolated_policy', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def canonical_observation(obs):
    return {k: v for k, v in obs.items() if k != 'remainingOverageTime'}


def tape(replay, seat):
    def policy(obs):
        return copy.deepcopy(replay['steps'][int(obs['step']) + 1][seat]['action'])
    return policy


def run_game(players, cfg, replay=None):
    durations = [[], []]
    wrapped = []
    for i, policy in enumerate(players):
        if isinstance(policy, str):
            wrapped.append(policy)
            continue
        def measured(index, function):
            def call(obs):
                start = time.perf_counter()
                try:
                    return function(obs)
                finally:
                    durations[index].append(time.perf_counter() - start)
            return call
        wrapped.append(measured(i, policy))
    env = make('kaggriculture', configuration=cfg, debug=False)
    actual_sales = [Counter(), Counter()]
    revenue = [Counter(), Counter()]
    floor_units = [Counter(), Counter()]
    failures = [Counter(), Counter()]
    spending = [Counter(), Counter()]
    original = engine._commit_unit
    original_market = engine._process_market
    current_farms = []
    def process_market(state, environment):
        current_farms[:] = state[0].observation.farms
        return original_market(state, environment)
    def commit(op, item, price, farm, private, market, shed_capacity=100):
        seat = next(i for i, f in enumerate(current_farms) if f is farm)
        before = farm['money']
        ok = original(op, item, price, farm, private, market, shed_capacity)
        if ok and farm['money'] < before:
            spending[seat][op + ':' + str(item)] += before - farm['money']
        if ok and op == 'SELL':
            actual_sales[seat][item] += 1
            revenue[seat][item] += price
            if price == 1:
                floor_units[seat][item] += 1
        elif not ok:
            failures[seat][op + ':' + str(item)] += 1
        return ok
    engine._commit_unit = commit
    engine._process_market = process_market
    try:
        frames = env.run(wrapped)
    finally:
        engine._commit_unit = original
        engine._process_market = original_market
    final = frames[-1]
    errors = [log.get('stderr') for logs in env.logs for log in logs if log.get('stderr')]
    row = {
        'rewards': [float(s.reward or 0) for s in final],
        'statuses': [s.status for s in final], 'frames': len(frames),
        'errors': errors[:5], 'actual_sales': actual_sales, 'sale_revenue': revenue,
        'floor_units': floor_units, 'failed_market_commits': failures,
        'market_spending': spending,
        'max_call_ms': [round(1000 * max(d or [0]), 3) for d in durations],
        'shops': list(final[0].observation.town.unlocked_shops),
        'terminal_stock': [dict(s.observation.private.shed) for s in final],
    }
    if replay is not None:
        mismatch = []
        for t, frame in enumerate(frames):
            for seat, s in enumerate(frame):
                if canonical_observation(s.observation) != canonical_observation(replay['steps'][t][seat]['observation']):
                    mismatch.append([t, seat])
        row['state_mismatches'] = len(mismatch)
        row['first_state_mismatches'] = mismatch[:5]
        row['reward_match'] = row['rewards'] == replay['rewards']
    return row


def replay_evaluation(paths, candidate, our_team='Mike chen666'):
    rows = []
    for path in paths:
        replay = json.loads(path.read_text(encoding='utf-8'))
        seat = replay['info']['TeamNames'].index(our_team) if our_team in replay['info']['TeamNames'] else 0
        cfg = dict(replay['configuration'])
        cfg['seed'] = replay['info']['seed']
        cfg.pop('runTimeout', None)
        if candidate is None:
            players = [tape(replay, 0), tape(replay, 1)]
        else:
            module = load_agent(candidate)
            players = [tape(replay, 0), tape(replay, 1)]
            players[seat] = module.agent
        row = run_game(players, cfg, replay if candidate is None else None)
        row.update(episode_id=replay['info']['EpisodeId'], replay_sha256=sha(path),
                   seat=seat, opponent=replay['info']['TeamNames'][1-seat],
                   evidence='fixed_opponent_tape' if candidate else 'engine_calibration',
                   recorded_margin=replay['rewards'][seat]-replay['rewards'][1-seat])
        row['margin'] = row['rewards'][seat] - row['rewards'][1-seat]
        row['delta'] = row['margin'] - row['recorded_margin']
        if candidate:
            row['shop_path_matches_recording'] = row['shops'] == replay['steps'][-1][0]['observation']['town']['unlocked_shops']
            probe = load_agent(candidate)
            differences = []
            for t in range(len(replay['steps'])-1):
                observation = copy.deepcopy(replay['steps'][t][seat]['observation'])
                # Kaggle serializes shared `step` only on seat 0; agent runner
                # restores it for seat 1. Do not confuse compressed replays with inputs.
                observation['step'] = replay['steps'][t][0]['observation']['step']
                action = probe.agent(observation)
                if action != replay['steps'][t+1][seat]['action']:
                    differences.append(t)
            row['recorded_observation_action_mismatches'] = len(differences)
            row['first_action_mismatches'] = differences[:8]
        rows.append(row)
        print(json.dumps({k:row[k] for k in ('episode_id','margin','delta','statuses')}, ensure_ascii=False), flush=True)
    return rows


def score(rewards, seat):
    return 1.0 if rewards[seat] > rewards[1-seat] else 0.0 if rewards[seat] < rewards[1-seat] else 0.5


def aggregate(rows, resamples=2000):
    groups = defaultdict(list)
    for r in rows:
        groups[r['opponent']].append(r)
    per_opponent = {}
    for name, group in groups.items():
        outcomes = [score(r['rewards'], r['seat']) for r in group]
        margins = [2*r['margin']/max(1,sum(r['rewards'])) for r in group]
        per_opponent[name] = {'games':len(group), 'expected_match_score':statistics.mean(outcomes),
                              'mean_normalized_margin':statistics.mean(margins),
                              'worst_margin':min(r['margin'] for r in group)}
    # Each opponent has equal weight; both seats sharing a seed form one block.
    blocks = defaultdict(list)
    for r in rows:
        blocks[(r['opponent'],r.get('seed',r.get('episode_id')))].append(r)
    buckets = defaultdict(list)
    for (name, _), block in blocks.items():
        buckets[name].append(statistics.mean(score(r['rewards'],r['seat']) for r in block))
    rng = random.Random(91911)
    samples = sorted(statistics.mean(statistics.mean(rng.choices(v,k=len(v))) for v in buckets.values())
                     for _ in range(resamples)) if buckets else []
    interval_ok=bool(samples) and all(len(v)>=4 for v in buckets.values()) and samples[0]!=samples[-1]
    return {'games':len(rows), 'per_opponent':per_opponent,
            'macro_match_score':statistics.mean(p['expected_match_score'] for p in per_opponent.values()) if rows else None,
            'seed_block_bootstrap_95': [samples[int(.025*resamples)],samples[int(.975*resamples)]] if interval_ok else None,
            'uncertainty_available':interval_ok,
            'uncertainty_note':'conditional on fixed opponent pool, not ladder uncertainty; suppressed for small/degenerate empirical samples',
            'all_clean':all(r['statuses']==['DONE','DONE'] and r['frames']==720 and not r['errors'] for r in rows)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['calibrate','replay','league'])
    parser.add_argument('--candidate',type=Path)
    parser.add_argument('--opponent',action='append',default=[])
    parser.add_argument('--seed',type=int,action='append',default=[])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replay-dir',type=Path,default=LAB/'online-replays')
    parser.add_argument('--limit',type=int)
    args=parser.parse_args()
    manifest={'environment_version':version('kaggle-environments'),'engine_sha256':sha(engine.__file__),
              'candidate_sha256':sha(args.candidate) if args.candidate else None,'metric_version':'match-outcome-v1'}
    if args.mode=='calibrate':
        rows=replay_evaluation(sorted(args.replay_dir.glob('episode-*.json'))[:args.limit],None)
    elif args.mode=='replay':
        rows=replay_evaluation(sorted(args.replay_dir.glob('episode-*.json'))[:args.limit],args.candidate)
    else:
        rows=[]
        manifest['opponents']={s.split('=',1)[0]:sha(s.split('=',1)[1]) for s in args.opponent}
        for spec in args.opponent:
            name,path=spec.split('=',1)
            for seed in args.seed:
                for seat in (0,1):
                    ours=load_agent(args.candidate)
                    theirs=load_agent(path)
                    players=[ours.agent,theirs.agent] if seat==0 else [theirs.agent,ours.agent]
                    r=run_game(players,{'seed':seed,'episodeSteps':720})
                    r.update(opponent=name,seed=seed,seat=seat,evidence='closed_loop')
                    r['margin']=r['rewards'][seat]-r['rewards'][1-seat]
                    rows.append(r)
                    dump(args.output,{'manifest':manifest,'matches':rows,'summary':aggregate(rows,200)})
                    print(json.dumps({'opponent':name,'seed':seed,'seat':seat,'margin':r['margin']}),flush=True)
    result={'manifest':manifest,'matches':rows,'summary':aggregate(rows)}
    dump(args.output,result)
    print(json.dumps(result['summary'],ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
