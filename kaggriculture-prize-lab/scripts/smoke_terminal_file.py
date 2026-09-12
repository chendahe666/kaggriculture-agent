"""Full-game official Python path-loader smoke; local engine, not Kaggle sandbox."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

LAB = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', required=True)
    parser.add_argument('--seed', type=int, default=91101)
    parser.add_argument('--seat', type=int, choices=[0, 1], action='append')
    args = parser.parse_args()
    from research_cycle import make, engine
    candidate = LAB / f'experiments/track-terminal-20260912/{args.variant}/main.py'
    baseline = LAB / 'public-baseline-v10/main.py'
    for seat in args.seat or [0, 1]:
        destination = LAB / f'results/terminal-20260912/file-smoke/{args.variant}-{args.seed}-{seat}.json'
        if destination.exists():
            raise SystemExit(f'Refusing to overwrite {destination}')
        started = datetime.now(timezone.utc).isoformat()
        clock = time.perf_counter()
        env = make('kaggriculture', configuration={'seed': args.seed, 'episodeSteps': 720}, debug=False)
        players = [str(baseline), str(baseline)]
        players[seat] = str(candidate)
        frames = env.run(players)
        final = frames[-1]
        durations = [[float(frame[i].get('duration', 0)) for frame in env.logs if len(frame) == 2] for i in [0, 1]]
        overage = [[float(frame[i].observation.get('remainingOverageTime', 60)) for frame in frames] for i in [0, 1]]
        errors = [log.get('stderr') for frame in env.logs for log in frame if log.get('stderr')]
        row = {'variant': args.variant, 'seat': seat, 'seed': args.seed,
               'started_utc': started, 'completed_utc': datetime.now(timezone.utc).isoformat(),
               'wall_seconds': time.perf_counter() - clock,
               'candidate_sha256': digest(candidate), 'baseline_sha256': digest(baseline),
               'engine_sha256': digest(Path(engine.__file__)), 'runner_sha256': digest(Path(__file__)),
               'entrypoint': 'env.run with actual Python file paths for BOTH policies',
               'frames': len(frames), 'statuses': [s.status for s in final],
               'rewards': [s.reward for s in final], 'errors': errors,
               'max_framework_call_seconds': [max(x or [0]) for x in durations],
               'min_recorded_overage_seconds': [min(x) for x in overage],
               'configuration': {k: v for k, v in env.configuration.items() if k != '__raw_path__'},
               'scope': 'Development duplicate scenario. Verifies local file loading/configuration/engine completion; not online container CPU/memory guarantee.'}
        league = LAB / f'results/terminal-20260912/development/cok-{args.seed}-{seat}-{args.variant}.json'
        if league.exists():
            reference = json.loads(league.read_text(encoding='utf-8'))
            assert reference['candidate_sha256'] == row['candidate_sha256']
            row['matches_explicit_loader_league'] = row['rewards'] == reference['rewards']
            row['league_reference'] = str(league.relative_to(LAB))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
        if errors or row['statuses'] != ['DONE', 'DONE'] or len(frames) != 720 or row.get('matches_explicit_loader_league') is False:
            raise SystemExit('Raw-file smoke failed; inspect preserved evidence')


if __name__ == '__main__':
    main()
