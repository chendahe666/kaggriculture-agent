"""Resumable official-CLI read-only acquisition, frozen top-30 version cohort."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / 'results/elite-20260912'
MANIFEST = ROOT / 'corpus.json'
CACHE = LAB / 'inbox/replays'


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    # Windows/OneDrive readers may briefly deny replacing an open manifest.
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.1 * (attempt + 1))


def cli(*args):
    for attempt in range(3):
        try:
            r = subprocess.run([sys.executable, '-m', 'kaggle', 'competitions', *map(str, args)],
                               capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
            if r.returncode == 0:
                return r.stdout
            error = f'CLI failed for {args[0]}, exit {r.returncode}'
        except subprocess.TimeoutExpired:
            error = f'CLI timeout for {args[0]}'
        time.sleep(2 ** attempt)
    raise RuntimeError(error)  # Never print credential-bearing diagnostics.


def api(*args):
    output = cli(*args, '--format', 'json')
    for line in output.splitlines():
        if line.strip().startswith('['):
            return json.JSONDecoder().raw_decode(output[output.index(line):].lstrip())[0]
    raise ValueError('Expected JSON list in CLI response')


def public_completed(rows):
    return sorted((r for r in rows if 'PUBLIC' in str(r.get('type', ''))
                   and 'COMPLETED' in str(r.get('state', ''))),
                  key=lambda r: (r.get('endTime', ''), r['id']), reverse=True)


def team_metadata(team):
    submissions = api('team-submissions', team['teamId'])
    best = max(submissions, key=lambda s: float(s.get('publicScore') or '-inf'))
    rows = public_completed(api('episodes', best['id']))[:20]
    return dict(team, selected_submission=best, episodes=rows,
                selection='highest current score among returned active submissions; latest 20 completed PUBLIC, no outcome filtering')


def plan():
    if MANIFEST.exists():
        raise SystemExit('Cohort already frozen; resume downloads rather than change selection.')
    metadata_path = ROOT / 'team-metadata.json'
    if metadata_path.exists():
        state = json.loads(metadata_path.read_text(encoding='utf-8'))
    else:
        state = {'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'leaderboard': api('leaderboard', 'kaggriculture', '--show', '--page-size', 30),
                 'teams': [], 'errors': []}
        save(metadata_path, state)
    completed = {t['teamId'] for t in state['teams']}
    jobs = [dict(t, rank=i + 1) for i, t in enumerate(state['leaderboard']) if t['teamId'] not in completed]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(team_metadata, t): t for t in jobs}
        for future in as_completed(futures):
            team = futures[future]
            try:
                row = future.result()
                state['teams'].append(row)
                print(json.dumps({'rank': row['rank'], 'team_id': row['teamId'], 'episodes': len(row['episodes'])}), flush=True)
            except Exception as exc:
                state['errors'].append({'team_id': team['teamId'], 'error': str(exc)})
            save(metadata_path, state)
    if len(state['teams']) != len(state['leaderboard']):
        raise SystemExit('Some team metadata unavailable; retained progress, rerun plan to retry.')
    episodes = {}
    for team in sorted(state['teams'], key=lambda t: t['rank']):
        for index, row in enumerate(team['episodes']):
            item = episodes.setdefault(str(row['id']), {'episode_id': row['id'], 'end_time': row['endTime'],
                                      'references': [], 'screen': False, 'split': 'development', 'downloaded': False})
            item['screen'] |= index < 5
            item['references'].append({'team_id': team['teamId'], 'team_name': team['teamName'],
                                      'rank': team['rank'], 'submission_id': team['selected_submission']['id']})
    manifest = {'version': 'elite-corpus-20260912-v1', 'captured_utc': state['captured_utc'],
                'frozen_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'team_count': len(state['teams']), 'reference_count': sum(len(t['episodes']) for t in state['teams']),
                'selection': 'top30 snapshot, one pinned active version each, latest20 public completed, both outcomes',
                'split_policy': 'ALL current selected replays are development. Future test must start after model freeze, use episode-ID disjoint data and report version changes. No holdout has been acquired or evaluated.',
                'episodes': list(episodes.values()), 'errors': []}
    save(MANIFEST, manifest)
    print(json.dumps({'unique_episodes': len(episodes), 'references': manifest['reference_count']}), flush=True)


def download(item):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"episode-{item['episode_id']}-replay.json"
    started = completed = None
    cache_hit = path.exists()
    if not path.exists():
        if shutil.disk_usage(CACHE).free < 8 * 1024 ** 3:
            raise RuntimeError('Disk safety reserve reached (8 GiB); no deletion attempted')
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cli('replay', item['episode_id'], '-p', CACHE)
        completed = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = path.read_bytes()
    replay = json.loads(payload)
    if int(replay['info']['EpisodeId']) != item['episode_id']:
        raise ValueError('Replay episode ID mismatch')
    names = replay['info']['TeamNames']
    references = [dict(ref, seat=names.index(ref['team_name'])) for ref in item['references']]
    return dict(item, downloaded=True, path=path.relative_to(LAB).as_posix(),
                sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), references=references,
                download_started_utc=started, download_completed_utc=completed,
                cache_hit=cache_hit,
                file_written_utc=datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).isoformat(),
                acquisition_time_basis='client_clock' if completed else 'filesystem_mtime_proxy_only',
                registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['plan', 'screen', 'all'])
    args = parser.parse_args()
    if args.mode == 'plan':
        plan()
        return
    state = json.loads(MANIFEST.read_text(encoding='utf-8'))
    rows = {r['episode_id']: r for r in state['episodes']}
    selected = [r for r in rows.values() if not r['downloaded'] and (args.mode == 'all' or r['screen'])]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(download, r): r['episode_id'] for r in selected}
        for future in as_completed(futures):
            episode = futures[future]
            try:
                rows[episode] = future.result()
            except Exception as exc:
                state['errors'].append({'episode_id': episode, 'error': str(exc)})
            state['episodes'] = list(rows.values())
            save(MANIFEST, state)
            print(json.dumps({'episode_id': episode, 'downloaded': sum(r['downloaded'] for r in rows.values()),
                              'total': len(rows)}), flush=True)
    print(json.dumps({'complete': all(r['downloaded'] for r in rows.values() if args.mode == 'all' or r['screen']),
                      'downloaded': sum(r['downloaded'] for r in rows.values()), 'unique': len(rows)}))


if __name__ == '__main__':
    main()
