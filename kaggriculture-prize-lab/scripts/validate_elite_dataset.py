"""Validate schema essentials, joins, temporal labels, daily sums and checksums."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / 'datasets/elite-20260912-v0.1.0'


def validate_records(cohort, episodes, players, daily):
    errors = []
    teams = {r['team_id']: r for r in cohort}
    episode_map = {r['episode_id']: r for r in episodes}
    keys = {(p['episode_id'], p['seat']) for p in players}
    if len(teams) != len(cohort) or len(episode_map) != len(episodes) or len(keys) != len(players):
        errors.append('duplicate primary key')
    counts = Counter(p['team_id'] for p in players)
    for team in cohort:
        if counts[team['team_id']] != team['selected_episode_count']:
            errors.append(f"incomplete selected player rows: {team['team_id']}")
    for row in episodes:
        if row['download_completed_utc'] is None and row['acquisition_time_basis'] != 'filesystem_mtime_proxy_only':
            errors.append('unknown acquisition time must be labelled a proxy')
        if row['audit_status'] != 'pass' or row['state_mismatches'] != 0 or row['rewards_match'] is not True:
            errors.append(f"episode failed audit: {row['episode_id']}")
        if row['split'] != 'development' or row['raw_replay_redistributed'] is not False:
            errors.append('unexpected release/split classification')
    day_keys = set()
    grouped = defaultdict(list)
    for row in daily:
        key = row['episode_id'], row['seat']
        day_key = (*key, row['day_index'])
        if key not in keys or day_key in day_keys:
            errors.append('bad daily foreign key or duplicate')
        day_keys.add(day_key)
        grouped[key].append(row)
    for p in players:
        t = teams.get(p['team_id'])
        if t is None or p['episode_id'] not in episode_map:
            errors.append('unknown team or episode foreign key')
            continue
        if (p['rank_at_batch_snapshot'] != t['rank_at_batch_snapshot']
                or p['leaderboard_score_at_batch_snapshot'] != t['leaderboard_score_at_batch_snapshot']
                or p['submission_id'] != t['selected_submission_id']):
            errors.append('cohort snapshot/version mismatch')
        if p['rank_before_episode'] is not None or p['rating_before_episode'] is not None:
            errors.append('unsupported pregame rating')
        margin = p['final_coins']-p['opponent_final_coins']
        if p['final_coin_margin'] != margin or p['outcome_points'] != (1 if margin > 0 else 0 if margin < 0 else .5):
            errors.append('inconsistent outcome')
        if p['cash_balance_error'] != 0 or p['wheat_balance_error'] != 0:
            errors.append('nonzero accounting residual')
        ds = grouped[p['episode_id'], p['seat']]
        if sorted(d['day_index'] for d in ds) != list(range(30)):
            errors.append('missing or unexpected day')
        for field, total in [('feed', p['feed_units'].get('WHEAT', 0)),
                             ('wheat_bought', p['metrics']['wheat_bought']),
                             ('wheat_sold', p['metrics']['wheat_sold']),
                             ('wheat_cost', p['metrics']['wheat_buy_cost']),
                             ('hire_cost', p['metrics']['hire_cost']),
                             ('labor_requests', p['metrics']['labor_requests'])]:
            if sum(d[field] for d in ds) != total:
                errors.append(f'daily sum mismatch: {field}')
        harvest = Counter()
        for d in ds:
            harvest.update(d['harvest'])
        if dict(harvest) != p['harvest_units']:
            errors.append('daily harvest mismatch')
    return errors


def main():
    tables = [[json.loads(line) for line in (DEST/f).read_text(encoding='utf-8').splitlines()]
              for f in ('cohort.jsonl', 'episodes.jsonl', 'players.jsonl', 'daily_economics.jsonl')]
    errors = validate_records(*tables)
    hashes = json.loads((DEST/'checksums.json').read_text(encoding='utf-8'))
    for name, expected in hashes.items():
        if hashlib.sha256((DEST/name).read_bytes()).hexdigest() != expected:
            errors.append('checksum mismatch: '+name)
    print(json.dumps({'valid': not errors, 'errors': errors[:20], 'counts': [len(t) for t in tables]}))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
