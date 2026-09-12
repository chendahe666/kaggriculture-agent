"""Resumable paired development experiments; process-isolated engine hooks."""
import argparse
import datetime
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB/'results/feed-20260912'
POLICIES = {'baseline': 'public-baseline-v10/main.py',
            'netting': 'experiments/track-feed-20260912/netting/main.py',
            'reserve6': 'experiments/track-feed-20260912/reserve6/main.py',
            'jit1': 'experiments/track-feed-20260912/jit1/main.py'}
POLICIES.update({name: f'experiments/track-feed-20260912/{name}/main.py' for name in ('jit-busy', 'jit-return', 'jit-aware')})
POLICIES['idle-delivery'] = 'experiments/track-feed-20260912/idle-delivery/main.py'
POLICIES.update({name: f'experiments/track-feed-20260912/{name}/main.py' for name in ('delivery-early', 'feed-guard')})
OPPONENTS = {'cok': 'public-baseline-v10/main.py', 'seyam': 'public-seyam-v21/main.py',
             'lonespear': 'public-lonespear/main.py'}


def run_job(job):
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    from research_cycle import load_agent, run_game, tape, engine, sha
    from collect_elite_corpus import save
    from elite_economics import stock
    policy = load_agent(LAB/POLICIES[job['variant']])
    seat = job['seat']
    cfg = {'seed': job.get('seed', 0), 'episodeSteps': 720}
    if job['kind'] in ('own', 'elite', 'elite-top'):
        path = LAB/job['path']
        replay = json.loads(path.read_bytes())
        cfg = dict(replay['configuration'], seed=replay['info']['seed'])
        cfg.pop('runTimeout', None)
        players = [tape(replay, 0), tape(replay, 1)]
        players[seat] = policy.agent
        source_hash = sha(path)
        recorded_shops = replay['steps'][-1][0]['observation']['town']['unlocked_shops']
    else:
        opponent = load_agent(LAB/OPPONENTS[job['opponent']])
        players = [policy.agent, opponent.agent] if seat == 0 else [opponent.agent, policy.agent]
        source_hash = sha(LAB/OPPONENTS[job['opponent']])
        recorded_shops = None
    metrics = [Counter(), Counter()]
    mapping, private_mapping = {}, {}
    count = 0
    original = {name: getattr(engine, name) for name in
                ('_apply_unit_action', '_daily_refresh_animals', '_drop_inventories_to_shed')}

    def apply(farm, private, idx, action, *args, **kwargs):
        nonlocal count
        if idx == 0:
            current_seat = count % 2
            if current_seat == 0:
                mapping.clear()
                private_mapping.clear()
            mapping[id(farm)] = current_seat
            private_mapping[id(private)] = current_seat
            count += 1
        s = mapping[id(farm)]
        pos = engine._farmer_position(farm, idx)
        if pos is None:
            return original['_apply_unit_action'](farm, private, idx, action, *args, **kwargs)
        op = action[0] if isinstance(action, list) and action else ''
        tile = farm['tiles'][pos[1]][pos[0]]
        inv = engine._farmer_inventory(private, idx)
        feed_due = op == 'FEED' and isinstance(tile, dict) and 'animal' in tile and not tile['fed_today']
        before_wheat = inv.get('WHEAT', 0)
        before_stock = stock(private) if op == 'DROP' else None
        result = original['_apply_unit_action'](farm, private, idx, action, *args, **kwargs)
        if feed_due:
            metrics[s]['feed_success' if tile['fed_today'] else 'feed_failed_no_wheat'] += 1
        if op == 'HARVEST':
            metrics[s]['wheat_harvest'] += max(0, inv.get('WHEAT', 0) - before_wheat)
        if before_stock is not None:
            lost = before_stock - stock(private)
            metrics[s]['overflow_units'] += sum(lost.values())
            metrics[s]['wheat_overflow'] += lost['WHEAT']
        return result

    def animals(farm, day):
        s = mapping[id(farm)]
        tiles = [t for row in farm['tiles'] for t in row if isinstance(t, dict) and 'animal' in t]
        metrics[s]['unfed_animal_days'] += sum(not t['fed_today'] for t in tiles)
        metrics[s]['escaped_animals'] += sum(not t['fed_today'] and t['consecutive_unfed'] >= 1 for t in tiles)
        return original['_daily_refresh_animals'](farm, day)

    def drop(private, capacity):
        before = stock(private)
        result = original['_drop_inventories_to_shed'](private, capacity)
        lost = before - stock(private)
        s = private_mapping[id(private)]
        metrics[s]['overflow_units'] += sum(lost.values())
        metrics[s]['wheat_overflow'] += lost['WHEAT']
        return result

    for name, wrapper in zip(original, (apply, animals, drop)):
        setattr(engine, name, wrapper)
    try:
        result = run_game(players, cfg)
    finally:
        for name, function in original.items():
            setattr(engine, name, function)
    result.update(job=job, candidate_sha256=sha(LAB/POLICIES[job['variant']]),
                  started_utc=started_utc, completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  runner_sha256=sha(__file__),
                  source_sha256=source_hash, engine_sha256=sha(engine.__file__),
                  evidence='closed_loop_development' if job['kind'] == 'league' else 'fixed_opponent_tape_development',
                  safety=metrics, policy_diagnostics=dict(getattr(policy, '_FEED_DIAGNOSTICS', {})),
                  margin=result['rewards'][seat]-result['rewards'][1-seat],
                  shop_path_matches_recording=recorded_shops == result['shops'] if recorded_shops is not None else None)
    save(ROOT/job['key'], result)
    return {'key': job['key'], 'margin': result['margin'], 'safety': metrics[seat],
            'changed': result['policy_diagnostics'].get('changed_steps', 0)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['own', 'elite', 'elite-top', 'league'])
    parser.add_argument('--limit', type=int)
    parser.add_argument('--variant', action='append')
    args = parser.parse_args()
    variants = args.variant or list(POLICIES)
    jobs = []
    if args.kind == 'own':
        source = json.loads((LAB/'results/public-corpus-20260911.json').read_text(encoding='utf-8'))
        rows = [r for r in source['matches'] if r['source'] == 'own_recent']
        for r in rows[:args.limit]:
            audited = json.loads((LAB/f"results/elite-20260912/own-audits/{r['episode_id']}.json").read_text(encoding='utf-8'))
            seat = next(p['seat'] for p in audited['players'] if p['name'] == 'Mike chen666')
            for v in variants:
                jobs.append(dict(kind='own', variant=v, episode_id=r['episode_id'], path=r['path'], seat=seat,
                                 key=f"own/{r['episode_id']}-{v}.json"))
    elif args.kind == 'elite-top':
        source = json.loads((LAB/'results/elite-20260912/corpus.json').read_text(encoding='utf-8'))
        metadata = json.loads((LAB/'results/elite-20260912/team-metadata.json').read_text(encoding='utf-8'))
        by_id = {r['episode_id']: r for r in source['episodes']}
        for team in sorted(metadata['teams'], key=lambda t: t['rank'])[:args.limit]:
            r = by_id[team['episodes'][0]['id']]
            ref = next(ref for ref in r['references'] if ref['team_id'] == team['teamId'])
            seat = 1-ref['seat']  # Preserve the selected top player's actions.
            for v in variants:
                jobs.append(dict(kind='elite-top', variant=v, episode_id=r['episode_id'], path=r['path'], seat=seat,
                                 opponent_team_id=team['teamId'], opponent_name=team['teamName'],
                                 opponent_rank_snapshot=team['rank'], opponent_submission=ref['submission_id'],
                                 key=f"elite-top/{r['episode_id']}-{seat}-{v}.json"))
    elif args.kind == 'elite':
        source = json.loads((LAB/'results/elite-20260912/corpus.json').read_text(encoding='utf-8'))
        metadata = json.loads((LAB/'results/elite-20260912/team-metadata.json').read_text(encoding='utf-8'))
        selected_ids = {t['teamId']: {r['id'] for r in t['episodes'][:2]} for t in metadata['teams']}
        selected = []
        for r in source['episodes']:
            refs = [ref for ref in r['references'] if r['episode_id'] in selected_ids[ref['team_id']]]
            if refs:
                ref = refs[0]
                selected.append((r, ref['seat']))
        for r, seat in selected[:args.limit]:
            for v in variants:
                jobs.append(dict(kind='elite', variant=v, episode_id=r['episode_id'], path=r['path'], seat=seat,
                                 key=f"elite/{r['episode_id']}-{seat}-{v}.json"))
    else:
        for name in OPPONENTS:
            for seed in [91101, 91102]:
                for seat in (0, 1):
                    for v in variants:
                        jobs.append(dict(kind='league', variant=v, opponent=name, seed=seed, seat=seat,
                                         key=f'league/{name}-{seed}-{seat}-{v}.json'))
    jobs = [j for j in jobs if not (ROOT/j['key']).exists()]
    print(json.dumps({'jobs': len(jobs)}), flush=True)
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_job, j) for j in jobs]
        for f in as_completed(futures):
            print(json.dumps(f.result()), flush=True)


if __name__ == '__main__':
    main()
