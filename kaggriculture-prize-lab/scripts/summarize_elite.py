"""Descriptive, version-bound player dossiers; no causal/rating claims."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
from collect_elite_corpus import save

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / 'results/elite-20260912'
REPORTS = LAB / 'reports/elite-20260912'


def feature(p):
    wheat_cost = p['purchase_cost'].get('BUY_PRODUCT:WHEAT', 0)
    wheat_sales = p['sale_revenue'].get('WHEAT', 0)
    return {'money': p['final_money'], 'wheat_harvest': p['harvest'].get('WHEAT', 0),
            'wheat_feed': p['feed'].get('WHEAT', 0),
            'wheat_bought': p['purchased_units'].get('BUY_PRODUCT:WHEAT', 0),
            'wheat_sold': p['sold_units'].get('WHEAT', 0), 'wheat_buy_cost': wheat_cost,
            'wheat_net_trade_cash': wheat_sales-wheat_cost,
            'wheat_seed_cost': p['purchase_cost'].get('BUY_SEED:WHEAT', 0),
            'hire_cost': p.get('hire_cost', 0), 'land_cost': p.get('land_cost', 0),
            'sale_revenue': sum(p['sale_revenue'].values()), 'purchase_cost': sum(p['purchase_cost'].values()),
            'overflow_units': sum(p['overflow'].values()), 'wheat_overflow': p['overflow'].get('WHEAT', 0),
            'milk_harvest': p['harvest'].get('MILK', 0), 'wool_harvest': p['harvest'].get('WOOL', 0),
            'strawberry_harvest': p['harvest'].get('STRAWBERRY', 0),
            'fertilizer_bought': p['purchased_units'].get('BUY_PRODUCT:FERTILIZER', 0),
            'fertilizer_used': p['fertilizer_used'].get('FERTILIZER', 0),
            'labor_requests': sum(p['processed_requests'].values()),
            'same_day_buy_sell_days': sum(d['wheat_bought'] > 0 and d['wheat_sold'] > 0 for d in p['days'].values())}


def describe(p):
    late = p['snapshots']['551']
    a = late['animals']
    c, s, g = (a.get(k, 0) for k in ('COW', 'SHEEP', 'GOOSE'))
    mode = '偏牛' if c >= 2*max(1, s) else '偏羊' if s >= 2*max(1, c) else '牛羊混合'
    if c+s == 0:
        mode = '无牛羊'
    return mode, f"牛{c}/羊{s}/鹅{g};工人{late['hands']};地块{late['land']}"


def stats(rows):
    keys = feature(rows[0]).keys()
    return {k: {'median': statistics.median(feature(r)[k] for r in rows),
                'min': min(feature(r)[k] for r in rows), 'max': max(feature(r)[k] for r in rows)} for k in keys}


def main():
    metadata = json.loads((ROOT/'team-metadata.json').read_text(encoding='utf-8'))
    manifest = json.loads((ROOT/'corpus.json').read_text(encoding='utf-8'))
    by_team = defaultdict(list)
    valid, invalid = [], []
    for path in sorted((ROOT/'audits').glob('*.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        (valid if row['valid'] else invalid).append(row)
        if not row['valid']:
            continue
        for ref in row['references']:
            player = row['players'][ref['seat']]
            opponent = row['players'][1-ref['seat']]
            by_team[ref['team_id']].append({'episode_id': row['episode_id'], 'player': player,
                'opponent': opponent['name'], 'shops': row['shops'],
                'outcome': 1 if player['final_money'] > opponent['final_money'] else
                           0 if player['final_money'] < opponent['final_money'] else .5})
    summary = {'scope': 'development-only observational census, no causal gains or leaderboard prediction',
               'selected_references': manifest['reference_count'], 'unique_selected': len(manifest['episodes']),
               'downloaded': sum(r['downloaded'] for r in manifest['episodes']),
               'audited_unique': len(valid)+len(invalid), 'valid_unique': len(valid),
               'invalid_ids': [r['episode_id'] for r in invalid], 'teams': []}
    REPORTS.mkdir(parents=True, exist_ok=True)
    index = ['# 前 30 名策略档案', '', '本批全部为开发资料；当前排名选择存在幸存者/匹配偏差。对局可跨选手共用，600 条记录不是 600 个独立比赛。',
             '', '|快照名次|选手|已分析/目标|胜/平/负|小麦收获中位数|买麦成本中位数|雇佣成本中位数|', '|---|---|---|---|---|---|---|']
    for team in sorted(metadata['teams'], key=lambda t: t['rank']):
        matches = by_team[team['teamId']]
        if not matches:
            continue
        players = [r['player'] for r in matches]
        measures = stats(players)
        modes = Counter(describe(p)[0] for p in players)
        configurations = Counter(describe(p)[1] for p in players)
        outcomes = Counter(r['outcome'] for r in matches)
        shops = defaultdict(list)
        for match in matches:
            shops[' / '.join(match['shops'][:3])].append(match)
        record = {'team_id': team['teamId'], 'name': team['teamName'], 'rank_snapshot': team['rank'],
                  'submission_id': team['selected_submission']['id'], 'games': len(matches),
                  'wins': outcomes[1], 'ties': outcomes[.5], 'losses': outcomes[0],
                  'metrics': measures, 'late_behavior_groups': dict(modes),
                  'late_configurations': dict(configurations),
                  'shop_prefix_count': len(shops), 'episode_ids': [r['episode_id'] for r in matches],
                  'shop_prefixes': {k: {'n': len(v), 'metrics': stats([m['player'] for m in v])} for k, v in shops.items()}}
        summary['teams'].append(record)
        slug = str(team['teamId'])
        index.append(f"|{team['rank']}|[{team['teamName']}]({slug}.md)|{len(matches)}/20|{outcomes[1]}/{outcomes[.5]}/{outcomes[0]}|{measures['wheat_harvest']['median']}|{measures['wheat_buy_cost']['median']}|{measures['hire_cost']['median']}|")
        lines = [f"# {team['teamName']} — 策略观察档案", '',
                 f"快照名次 {team['rank']}；固定提交 {team['selected_submission']['id']}；当前已分析 {len(matches)} 场。",
                 f"观察结果 {outcomes[1]} 胜/{outcomes[.5]} 平/{outcomes[0]} 负；覆盖 {len(shops)} 种前三商店组合。不是对本方的预测胜率。", '',
                 '## 经济与生产', '', '|指标|中位数|范围|', '|---|---|---|']
        for key, measure in measures.items():
            lines.append(f"|{key}|{measure['median']}|{measure['min']}–{measure['max']}|")
        lines += ['', '## 第 551 状态的生产配置', '',
                  '这是同一时点的可观察行为分组，不代表源码家族或完整策略。', '']
        lines += [f'- {key}：{n} 场' for key, n in configurations.most_common()]
        lines += ['', '## 学习与反证问题', '',
                  '- 比较同选手不同商店下牛羊/工人数变化，避免把偶然布局当固定路线。',
                  '- 小麦收获、饲喂和买卖应联合看；net_trade_cash 未扣种子、劳动、地块机会成本，不等于种麦利润。',
                  '- 同日买卖次数仅是周转线索，不能证明无效倒卖；须结合当时价格、库存、饲料缺口和仓容做反事实。',
                  '- 少雇工不自动更好；必须比较对应劳动带来的实际产出、商品结构和对手供给。',
                  '- 高胜率受匹配和当前排名筛选影响；用新时段和未见策略家族检验重建策略。', '',
                  '## 可追溯对局', '', '|Episode|结果|对手|前三商店|', '|---|---|---|---|']
        for match in matches:
            lines.append(f"|{match['episode_id']}|{match['outcome']}|{match['opponent']}|{' / '.join(match['shops'][:3])}|")
        (REPORTS/f'{slug}.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    save(ROOT/'summary.json', summary)
    own = [p for file in sorted((ROOT/'own-audits').glob('*.json'))
           for row in [json.loads(file.read_text(encoding='utf-8'))] if row['valid']
           for p in row['players'] if p['name'] == 'Mike chen666']
    if own:
        comparison = {'note': 'unmatched historical own sample vs current elite cohort; descriptive, not causal',
                      'own_games': len(own), 'own_metrics': stats(own),
                      'elite_completed_teams': sum(t['games'] == 20 for t in summary['teams']),
                      'elite_equal_team_median': {k: statistics.median(t['metrics'][k]['median'] for t in summary['teams'])
                                                 for k in feature(own[0])},
                      'elite_teams': len(summary['teams'])}
        save(ROOT/'own-comparison.json', comparison)
    (REPORTS/'README.md').write_text('\n'.join(index)+'\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('downloaded', 'audited_unique', 'valid_unique', 'invalid_ids')}))
    for team in summary['teams']:
        print(json.dumps({'rank': team['rank_snapshot'], 'name': team['name'], 'n': team['games'],
                          'wheat': team['metrics']['wheat_harvest']['median'],
                          'buy_cost': team['metrics']['wheat_buy_cost']['median'],
                          'hire': team['metrics']['hire_cost']['median'], 'types': team['late_behavior_groups']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
