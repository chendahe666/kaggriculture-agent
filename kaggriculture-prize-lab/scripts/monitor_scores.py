"""Read-only Kaggle snapshot; no upload, strategy changes, or Git publication."""
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LAB = Path(__file__).resolve().parents[1]
OUT = LAB / 'monitoring/snapshots'


def now():
    return datetime.now(timezone.utc).isoformat()


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def band(score):
    if score is None:
        return 'unknown'
    return 'low_<1200' if score < 1200 else 'middle_1200_1599' if score < 1600 else 'high_>=1600'


def outcome(episode, submission):
    if episode.get('type') not in ('PUBLIC', 'EPISODE_TYPE_PUBLIC') or episode.get('state') != 'COMPLETED':
        return None
    agents = episode.get('agents', [])
    own = [a for a in agents if a.get('submissionId') == submission]
    other = [a for a in agents if a.get('submissionId') != submission]
    if len(own) != 1 or len(other) != 1:
        return None
    # Missing reward is unknown, not silently zero (protobuf defaults can be omitted).
    left, right = number(own[0].get('reward')), number(other[0].get('reward'))
    if left is None or right is None:
        return None
    return 'win' if left > right else 'loss' if left < right else 'tie'


def stats(rows, submission):
    result = dict(win=0, tie=0, loss=0, unknown_completed_public=0)
    for row in rows:
        label = outcome(row, submission)
        if label:
            result[label] += 1
        elif row.get('type') in ('PUBLIC', 'EPISODE_TYPE_PUBLIC') and row.get('state') == 'COMPLETED':
            result['unknown_completed_public'] += 1
    result['n'] = sum(result[k] for k in ('win', 'tie', 'loss'))
    result['outcome_rate'] = (result['win'] + .5 * result['tie']) / result['n'] if result['n'] else None
    return result


def safe_error(exc):
    response = getattr(exc, 'response', None)
    return {'type': type(exc).__name__, 'http_status': getattr(response, 'status_code', None),
            'retry_after': response.headers.get('Retry-After') if response is not None else None}


def collect(client):
    previous_paths = sorted(OUT.glob('*.json'))
    previous = json.loads(previous_paths[-1].read_text(encoding='utf-8')) if previous_paths else {}
    result = {'schema_version': 1, 'started_utc': now(), 'previous_snapshot': previous_paths[-1].name if previous_paths else None,
              'source': 'Official authenticated Kaggle SDK read-only endpoints',
              'coverage': 'Up to 100 newest own submissions; latest two episode lists, all returned rows, not guaranteed lifetime-complete',
              'rating_basis': 'collection-time exact submission ID; NOT prematch rating',
              'submissions': [], 'episodes': {}, 'summaries': {}, 'opponent_scores': {}, 'errors': []}
    fields = ('ref', 'date', 'description', 'fileName', 'totalBytes', 'status', 'publicScore')
    raw = [r.to_dict() for r in client.competition_submissions('kaggriculture', page_size=100)]
    result['submissions'] = sorted([{k: r.get(k) for k in fields} for r in raw], key=lambda r: r.get('date') or '', reverse=True)
    result['submission_list_may_be_truncated'] = len(raw) >= 100
    for submission in result['submissions'][:2]:
        sid = submission['ref']
        try:
            rows = [r.to_dict() for r in client.competition_list_episodes(sid)]
            # Whitelist public game metadata; never persist account tokens/upload URLs.
            cleaned = []
            for r in rows:
                item = {k: r.get(k) for k in ('id', 'createTime', 'endTime', 'type', 'state')}
                item['agents'] = [{k: a[k] for k in ('submissionId', 'index', 'reward', 'state', 'teamId', 'teamName') if k in a} for a in r.get('agents', [])]
                cleaned.append(item)
            rows = list({r['id']: r for r in cleaned if r['id'] is not None}.values())
            result['episodes'][str(sid)] = rows
            old_rows = previous.get('episodes', {}).get(str(sid), [])
            # Pending -> completed must count even when the episode ID was already seen.
            old_completed = {r['id'] for r in old_rows if outcome(r, sid) is not None}
            new = [r for r in rows if outcome(r, sid) is not None and r['id'] not in old_completed]
            old_sub = next((r for r in previous.get('submissions', []) if r['ref'] == sid), {})
            old_score, score = number(old_sub.get('publicScore')), number(submission.get('publicScore'))
            result['summaries'][str(sid)] = {'all_returned': stats(rows, sid), 'new_completed': stats(new, sid),
                'new_completed_episode_ids': [r['id'] for r in new], 'score': score,
                'score_change': score - old_score if score is not None and old_score is not None else None,
                'first_observation': str(sid) not in previous.get('episodes', {}), 'rank': None}
        except Exception as exc:
            result['errors'].append({'endpoint': 'episodes', 'submission': sid, **safe_error(exc)})
            if result['errors'][-1]['http_status'] == 429:
                break
    # Recent games first; bounded requests, exact-version joins only.
    own_ids = {s['ref'] for s in result['submissions']}
    teams = list(dict.fromkeys(a['teamId'] for rows in result['episodes'].values()
        for r in sorted(rows, key=lambda r: r.get('endTime') or '', reverse=True)
        if r.get('type') in ('PUBLIC', 'EPISODE_TYPE_PUBLIC') and r.get('state') == 'COMPLETED'
        for a in r['agents'] if a.get('submissionId') not in own_ids and a.get('teamId')))
    for team in teams[:40] if not any(e['http_status'] == 429 for e in result['errors']) else []:
        try:
            acquired = now()
            for obj in client.competition_team_submissions(team):
                row = obj.to_dict()
                if row.get('id') is not None:
                    result['opponent_scores'][str(row['id'])] = {'score': number(row.get('publicScore')), 'observed_utc': acquired, 'team_id': team, 'rank': None}
        except Exception as exc:
            result['errors'].append({'endpoint': 'team_submissions', 'team': team, **safe_error(exc)})
            if result['errors'][-1]['http_status'] == 429:
                break
        time.sleep(4)
    result['team_lookup_cap'] = 40
    for sid, rows in result['episodes'].items():
        slices = {}
        for row in rows:
            if outcome(row, int(sid)) is None:
                continue
            opponent = next(a for a in row['agents'] if a.get('submissionId') != int(sid))
            score = result['opponent_scores'].get(str(opponent.get('submissionId')), {}).get('score')
            slices.setdefault(band(score), []).append(row)
        result['summaries'][sid]['current_opponent_score_bands'] = {k: stats(v, int(sid)) for k, v in slices.items()}
    result['completed_utc'] = now()
    result['completed_local'] = datetime.now(ZoneInfo('America/Chicago')).isoformat()
    result['collector_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    with target.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return target, result


if __name__ == '__main__':
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    path, data = collect(api)
    print(json.dumps({'snapshot': str(path), 'summaries': data['summaries'], 'errors': data['errors']}, ensure_ascii=False))
