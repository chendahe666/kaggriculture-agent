"""Build a traceable derived-statistics dataset, excluding raw replays/actions."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
from importlib.metadata import version
from collect_elite_corpus import save
from summarize_elite import feature

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / 'results/elite-20260912'
DEST = LAB / 'datasets/elite-20260912-v0.1.0'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_rows(name, rows):
    text = ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False, sort_keys=True)+'\n' for row in rows)
    (DEST/name).write_text(text, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT/'corpus.json').read_text(encoding='utf-8'))
    metadata = json.loads((ROOT/'team-metadata.json').read_text(encoding='utf-8'))
    teams = {t['teamId']: t for t in metadata['teams']}
    cohort = []
    for team in sorted(teams.values(), key=lambda t: t['rank']):
        cohort.append({'dataset_version': '0.1.0', 'team_id': team['teamId'], 'team_name': team['teamName'],
                       'rank_at_batch_snapshot': team['rank'], 'leaderboard_score_at_batch_snapshot': float(team['score']),
                       'batch_snapshot_started_utc': manifest['captured_utc'],
                       'selected_submission_id': team['selected_submission']['id'],
                       'selected_submission_score_during_metadata_collection': float(team['selected_submission']['publicScore']),
                       'submission_date_raw': team['selected_submission']['dateSubmitted'],
                       'selected_episode_count': len(team['episodes'])})
    episodes, players, daily = [], [], []
    absent, invalid = [], []
    for item in sorted(manifest['episodes'], key=lambda r: r['episode_id']):
        replay_path = LAB / item['path']
        artifact = ROOT/'audits'/f"{item['episode_id']}.json"
        audit = json.loads(artifact.read_text(encoding='utf-8')) if artifact.exists() else None
        if audit is None:
            absent.append(item['episode_id'])
        elif not audit['valid'] or audit['replay_sha256'] != item['sha256']:
            invalid.append(item['episode_id'])
        file_written = item.get('file_written_utc') or datetime.datetime.fromtimestamp(
            replay_path.stat().st_mtime, datetime.timezone.utc).isoformat()
        episodes.append({'episode_id': item['episode_id'], 'batch_id': manifest['version'],
                         'batch_snapshot_started_utc': manifest['captured_utc'],
                         'cohort_frozen_utc': manifest['frozen_utc'], 'episode_end_time_raw': item['end_time'],
                         'episode_source_timezone_assumption': 'UTC (CLI timestamps omit offset)',
                         'download_started_utc': item.get('download_started_utc'),
                         'download_completed_utc': item.get('download_completed_utc'),
                         'file_written_utc': file_written,
                         'acquisition_time_basis': item.get('acquisition_time_basis', 'filesystem_mtime_proxy_only'),
                         'registered_utc': item.get('registered_utc'),
                         'cache_hit_at_registration': item.get('cache_hit'),
                         'replay_sha256': item['sha256'], 'replay_bytes': item['bytes'],
                         'source': 'Kaggle official competitions replay CLI; public completed episode',
                         'reacquire_command': f"kaggle competitions replay {item['episode_id']} -p LOCAL_REPLAY_DIRECTORY",
                         'source_submission_ids': sorted({r['submission_id'] for r in item['references']}),
                         'selected_reference_count': len(item['references']),
                         'split': 'development', 'audit_status': 'not_run' if audit is None else 'fail' if item['episode_id'] in invalid else 'pass',
                         'state_mismatches': audit['calibration']['state_mismatches'] if audit else None,
                         'rewards_match': audit['calibration']['reward_match'] if audit else None,
                         'raw_replay_redistributed': False})
        if audit is None or item['episode_id'] in invalid:
            continue
        for ref in sorted(item['references'], key=lambda r: r['seat']):
            p = audit['players'][ref['seat']]
            opponent = audit['players'][1-ref['seat']]
            team = teams[ref['team_id']]
            outcome = 1.0 if p['final_money'] > opponent['final_money'] else 0.0 if p['final_money'] < opponent['final_money'] else .5
            players.append({'episode_id': item['episode_id'], 'seat': ref['seat'], 'team_id': ref['team_id'],
                            'team_name': p['name'], 'submission_id': ref['submission_id'],
                            'rank_at_batch_snapshot': team['rank'], 'leaderboard_score_at_batch_snapshot': float(team['score']),
                            'rank_before_episode': None, 'rating_before_episode': None,
                            'opponent_name': opponent['name'], 'opponent_final_coins': opponent['final_money'],
                            'final_coins': p['final_money'], 'outcome_points': outcome,
                            'final_coin_margin': p['final_money']-opponent['final_money'],
                            'shops_in_unlock_order': audit['shops'],
                            'metrics': feature(p), 'harvest_units': p['harvest'], 'feed_units': p['feed'],
                            'purchased_units': p['purchased_units'], 'sold_units': p['sold_units'],
                            'purchase_cost_by_order_item': p['purchase_cost'], 'sale_revenue_by_item': p['sale_revenue'],
                            'overflow_units_by_item': p['overflow'], 'cash_balance_error': p['cash_balance_error'],
                            'wheat_balance_error': p['wheat_balance_error'], 'audit_version': audit['audit_version']})
            for day, flows in sorted(p['days'].items(), key=lambda pair: int(pair[0])):
                daily.append({'episode_id': item['episode_id'], 'seat': ref['seat'], 'team_id': ref['team_id'],
                              'day_index': int(day), **flows})
    quality = {'cohort_teams': len(cohort), 'unique_episodes': len(episodes), 'selected_references': manifest['reference_count'],
               'audited_player_rows': len(players), 'daily_rows': len(daily), 'missing_audit_ids': absent,
               'invalid_audit_ids': invalid, 'complete': not absent and not invalid and len(players) == manifest['reference_count'],
               'duplicate_player_keys': len(players)-len({(r['episode_id'],r['seat']) for r in players}),
               'client_clock_acquisition_times': sum(r['download_completed_utc'] is not None for r in episodes),
               'mtime_proxy_acquisition_times': sum(r['download_completed_utc'] is None for r in episodes),
               'raw_bytes_kept_local': sum(r['replay_bytes'] for r in episodes)}
    if args.require_complete and (not quality['complete'] or quality['duplicate_player_keys']):
        raise SystemExit(json.dumps(quality))
    for name, rows in [('cohort.jsonl', cohort), ('episodes.jsonl', episodes),
                       ('players.jsonl', players), ('daily_economics.jsonl', daily)]:
        write_rows(name, rows)
    save(DEST/'quality.json', quality)
    from zoneinfo import ZoneInfo
    captured = datetime.datetime.fromisoformat(manifest['captured_utc'])
    lines = ['# 标准采集记录 / Collection record', '',
             f"批次：{manifest['version']}；数据版本：0.1.0。",
             f"开始采样：{captured.isoformat()}（UTC）；{captured.astimezone(ZoneInfo('America/Chicago')).isoformat()}（America/Chicago）。",
             f"清单冻结完成：{manifest['frozen_utc']}。", '',
             '时间口径：下面排名和评分来自批次榜单快照，不是比赛当时的排名或金币。逐局结束时间、文件写入近似时间及来源哈希见 episodes.jsonl。', '',
             f"覆盖：{len(cohort)} 队，{len(episodes)} 个独立对局，{len(players)} 条已审计选手记录，{len(daily)} 条日记录。",
             f"精确下载完成时间 {quality['client_clock_acquisition_times']} 场；仅文件时间近似 {quality['mtime_proxy_acquisition_times']} 场。",
             f"文件写入时间范围（不是精确下载窗口）：{min(r['file_written_utc'] for r in episodes)} 至 {max(r['file_written_utc'] for r in episodes)}。", '',
             '|快照名次|公开队名|榜单快照评分|固定提交 ID|选取局数|', '|---|---|---:|---|---:|']
    for row in cohort:
        name = row['team_name'].replace('|', '\\|').replace('\n', ' ')
        lines.append(f"|{row['rank_at_batch_snapshot']}|{name}|{row['leaderboard_score_at_batch_snapshot']}|{row['selected_submission_id']}|{row['selected_episode_count']}|")
    lines += ['', '不根据胜负筛选；同一比赛出现两名入选选手时保留两个席位，但独立比赛只算一次。',
              '赛前排名和评分未知，相关字段保持 null。全部为开发资料，没有独立测试集。',
              '客户端中断后复用了已下载文件；重新登记时间不等于首次下载时间。原始回放未纳入公开包。', '']
    (DEST/'COLLECTION_RECORD.md').write_text('\n'.join(lines), encoding='utf-8')
    source_files = ['collect_elite_corpus.py', 'elite_economics.py', 'summarize_elite.py',
                    'build_elite_dataset.py', 'validate_elite_dataset.py', 'research_cycle.py', 'analyze_online_replays.py']
    save(DEST/'analysis-run.json', {'run_id': 'elite-20260912-v0.1.0',
         'exported_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'local_date_convention': 'America/Chicago: 2026-09-11; UTC date: 2026-09-12',
         'python': platform.python_version(), 'kaggle_environments': version('kaggle-environments'),
         'engine_sha256': digest(LAB/'official/installed-1.32.7/kaggriculture.py'),
         'manifest_sha256': digest(ROOT/'corpus.json'), 'team_metadata_sha256': digest(ROOT/'team-metadata.json'),
         'analysis_source_sha256': {f: digest(LAB/'scripts'/f) for f in source_files},
         'method': 'official-engine state-by-state calibration plus instrumented successful transaction and unit-action accounting',
         'unit_of_analysis': 'episode/seat; cluster by episode and strategy family, not by frame',
         'split': 'development only; prospective holdout must be acquired after model freeze',
         'publication_state': 'draft; licensing approval and final QA required',
         'quality': quality})
    save(DEST/'checksums.json', {p.name: digest(p) for p in sorted(DEST.iterdir()) if p.is_file() and p.name != 'checksums.json'})
    print(json.dumps(quality))


if __name__ == '__main__':
    main()
