"""Resumable, process-isolated P2 full-game paired comparisons. Never submits."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB/'results/terminal-20260912'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run_job(job):
    from research_cycle import load_agent, run_game, engine, dump
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    ours = load_agent(LAB/job['candidate_path'])
    theirs = load_agent(LAB/job['opponent_path'])
    our_function = ours.agent
    entrypoint = 'explicit_module_agent'
    if job['variant'].endswith('-file') or job.get('official_loader'):
        from kaggle_environments.agent import get_last_callable
        candidate_file = LAB/job['candidate_path']
        our_function = get_last_callable(candidate_file.read_text(encoding='utf-8'), path=str(candidate_file))
        entrypoint = 'official_get_last_callable'
    seat = job['seat']
    module_metrics = {}
    stock_end = {}
    start_snapshot = {}
    original = engine._process_market
    def market(state, env):
        result = original(state, env)
        step = int(state[0].observation['step'])
        if step == 695:
            start_snapshot['sha256'] = hashlib.sha256(json.dumps([dict(s.observation) for s in state], sort_keys=True).encode()).hexdigest()
        if step >= 696:
            stock_end['step'] = step
            stock_end['shed'] = [dict(s.observation.private['shed']) for s in state]
            stock_end['carried'] = [[dict(v) for v in s.observation.private['inventories']] for s in state]
        return result
    engine._process_market = market
    try:
        players = [our_function, theirs.agent] if seat == 0 else [theirs.agent, our_function]
        row = run_game(players, {'seed': job['seed'], 'episodeSteps': 720})
    finally:
        engine._process_market = original
    module_metrics.update(dict(our_function.__globals__.get('_TERMINAL_DIAGNOSTICS', {})))
    row.update(job)
    row.update(started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
               wall_seconds=time.perf_counter()-clock, engine_sha256=digest(engine.__file__),
               runner_sha256=digest(__file__), candidate_sha256=digest(LAB/job['candidate_path']),
               opponent_sha256=digest(LAB/job['opponent_path']), evidence='closed_loop',
               margin=row['rewards'][seat]-row['rewards'][1-seat], terminal_diagnostics=module_metrics,
               final_after_market=stock_end, terminal_start=start_snapshot, entrypoint=entrypoint)
    path = ROOT/job['split']/job['key']
    if path.exists():
        raise RuntimeError(f'Refusing overwrite {path}')
    dump(path, row)
    return {'key': job['key'], 'margin': row['margin'], 'seconds': round(row['wall_seconds'], 2),
            'diagnostics': module_metrics, 'clean': not row['errors'] and row['statuses'] == ['DONE','DONE']}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--variant', action='append', required=True)
    p.add_argument('--seed', type=int, action='append', required=True)
    p.add_argument('--opponent', action='append')
    p.add_argument('--pool', type=Path, default=LAB/'opponent-pool.json')
    p.add_argument('--split', choices=['development', 'confirmation'], default='development')
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--freeze', type=Path)
    args = p.parse_args()
    pool = json.loads(args.pool.read_text(encoding='utf-8'))['opponents']
    selected = [r for r in pool if r['name'] in (args.opponent or ['cok','seyam','lonespear'])]
    if args.opponent and set(args.opponent) != {r['name'] for r in selected}:
        raise ValueError('Missing selected opponent')
    freeze = json.loads(args.freeze.read_text(encoding='utf-8')) if args.freeze else None
    if args.split == 'confirmation' and freeze is None:
        raise ValueError('Confirmation needs a frozen pre-registration')
    jobs = []
    for name in args.variant:
        path = 'public-baseline-v10/main.py' if name == 'baseline' else f'experiments/track-terminal-20260912/{name}/main.py'
        for opponent in selected:
            assert digest(LAB/opponent['path']) == opponent['sha256'], 'Changed opponent bytes'
            for seed in args.seed:
                for seat in (0, 1):
                    job = {'variant': name, 'candidate_path': path, 'opponent_path': opponent['path'],
                           'opponent': opponent['name'], 'family': opponent['family'], 'seed': seed, 'seat': seat,
                           'split': args.split, 'key': f"{opponent['name']}-{seed}-{seat}-{name}.json"}
                    if freeze:
                        assert seed in freeze['seeds']
                        assert digest(LAB/path) == freeze['variant_hashes'][name]
                        assert opponent['sha256'] == freeze['opponents'][opponent['name']]['sha256']
                    existing = ROOT/args.split/job['key']
                    if existing.exists():
                        old = json.loads(existing.read_text(encoding='utf-8'))
                        assert old['candidate_sha256'] == digest(LAB/path), 'Existing result is a different candidate'
                        assert old['opponent_sha256'] == opponent['sha256'], 'Existing result is a different opponent'
                    else:
                        jobs.append(job)
    print(json.dumps({'pending_games': len(jobs), 'split': args.split, 'workers': args.workers}), flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        pending = [executor.submit(run_job, job) for job in jobs]
        for f in as_completed(pending):
            print(json.dumps(f.result()), flush=True)

if __name__ == '__main__':
    main()
