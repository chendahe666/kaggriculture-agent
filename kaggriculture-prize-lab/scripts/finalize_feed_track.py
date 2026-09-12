"""Write per-candidate factual reports and a checksummed experiment index."""
import datetime
import hashlib
import json
from pathlib import Path
from collect_elite_corpus import save

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB/'results/feed-20260912'
DESCRIPTIONS = {
    'netting': ('取消可执行同回合重叠小麦买卖，保持槽位', 'HOLD：没有胜负提升，未通过发布门禁'),
    'reserve6': ('按未来六回合取麦需求重写买卖', 'REJECT：20场胜率和溢出显著退化'),
    'jit1': ('只保留下一回合取麦需求', 'REJECT：20场新增缺麦及胜转负'),
    'jit-busy': ('一步库存加满订单槽位前瞻消融', 'REJECT：修复缺麦但首4场仍丢失胜局/增加溢出'),
    'jit-return': ('一步库存加保守日终返仓抵扣消融', 'REJECT：未解决满槽导致的缺麦，首4场退化'),
    'jit-aware': ('满槽前瞻与日终返仓组合', 'REJECT：首4场退化；闭环无胜局提升且分差下降'),
    'idle-delivery': ('高库存时只调度当日后续全PASS工人配送非饲料商品', 'HOLD / NO-OP：首4场没有触发，不是改善'),
    'delivery-early': ('移除高库存阈值的空闲配送对照', 'REJECT：首4场仅少量触发、分差下降、未减少溢出'),
    'feed-guard': ('保留所有原订单，末尾补足可预见缺麦', 'REJECT：首4场修复缺麦但新增溢出、丢失胜局'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary = json.loads((ROOT/'summary.json').read_text(encoding='utf-8'))
    manifest = json.loads((LAB/'experiments/track-feed-20260912/manifest.json').read_text(encoding='utf-8'))
    files = sorted(p for folder in ('own','elite','elite-top','league') for p in (ROOT/folder).glob('*.json'))
    errors = []
    cohort = json.loads((LAB/'results/elite-20260912/corpus.json').read_text(encoding='utf-8'))
    by_id = {r['episode_id']: r for r in cohort['episodes']}
    if len(files) != 296:
        errors.append(f'Expected 296 frozen P1 simulations, found {len(files)}')
    for p in files:
        r = json.loads(p.read_text(encoding='utf-8'))
        v = r['job']['variant']
        expected = manifest['baseline_sha256'] if v == 'baseline' else manifest['variants'][v]['sha256']
        if r['candidate_sha256'] != expected or r['statuses'] != ['DONE','DONE'] or r['frames'] != 720 or r['errors']:
            errors.append(p.relative_to(LAB).as_posix())
        if r['job']['kind'] == 'elite-top':
            j = r['job']
            source = by_id[j['episode_id']]
            if r['source_sha256'] != source['sha256'] or not any(
                    ref['seat'] == 1-j['seat'] and ref['team_id'] == j['opponent_team_id']
                    and ref['submission_id'] == j['opponent_submission'] and ref['team_name'] == j['opponent_name']
                    for ref in source['references']):
                errors.append('Top-opponent seat/source mismatch: '+p.name)
    calibrated = 0
    for p in (ROOT/'own').glob('*-baseline.json'):
        r = json.loads(p.read_text(encoding='utf-8'))
        old = json.loads((LAB/f"results/elite-20260912/own-audits/{r['job']['episode_id']}.json").read_text(encoding='utf-8'))
        if r['rewards'] != [p['final_money'] for p in old['players']]:
            errors.append('own baseline rewards differ: '+p.name)
        for seat in (0,1):
            if r['safety'][seat].get('feed_success',0) != old['players'][seat]['feed'].get('WHEAT',0):
                errors.append('feed count differs: '+p.name)
            if r['safety'][seat].get('overflow_units',0) != sum(old['players'][seat]['overflow'].values()):
                errors.append('overflow count differs: '+p.name)
        calibrated += 1
    index = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'baseline_sha256': manifest['baseline_sha256'], 'candidate_count': len(DESCRIPTIONS),
             'completed_simulations': len(files), 'own_baseline_crosschecks': calibrated,
             'errors': errors, 'new_holdout_opened': False, 'kaggle_submitted': False,
             'test_result': '45 unittest tests passed (run separately)',
             'files': {p.relative_to(LAB).as_posix(): sha(p) for p in files},
             'analysis_source_sha256': {name: sha(LAB/'scripts'/name) for name in
                 ('run_feed_track.py','summarize_feed_track.py','build_feed_track.py','finalize_feed_track.py')}}
    save(ROOT/'experiment-index.json', index)
    for v, (method, decision) in DESCRIPTIONS.items():
        lines = [f'# P1 / {v}', '', f'结论：{decision}。不是 Kaggle 发布版本。', '',
                 '## 思路和实现', '', method+'。基于冻结 COK，保留原始来源声明。',
                 f"代码：experiments/track-feed-20260912/{v}/main.py；SHA256 `{manifest['variants'][v]['sha256']}`。",
                 f"基线 SHA256 `{manifest['baseline_sha256']}`。", '',
                 '## 评估方式与实测', '', '同对手/配置/席位配对；主目标胜平负，金币差和支出只是诊断。所有样本为开发资料，没有新的时间留出。', '',
                 '|集合|配对数|基线胜/平/负|候选胜/平/负|新增胜局/丢失胜局|平均分差变化|新增溢出场数|',
                 '|---|---:|---|---|---|---:|---:|']
        for kind, label in [('own','本方旧20场/前4场'),('league','三个来源家族代表闭环'),('elite-top','固定前30名本人动作'),('elite','替换入选席位探索，非保证前30对手')]:
            r = summary.get(kind, {}).get(v)
            if not r:
                continue
            n, bw, cw, bt, ct = (r[k] for k in ('paired_games','baseline_wins','candidate_wins','baseline_ties','candidate_ties'))
            lines.append(f"|{label}|{n}|{bw}/{bt}/{n-bw-bt}|{cw}/{ct}/{n-cw-ct}|{r['positive_outcome_flips']}/{r['negative_outcome_flips']}|{r['mean_margin_gain']:.3f}|{r['more_overflow_games']}|")
        lines += ['', '完整逐局结果/候选哈希/资源/饲喂/逃跑/溢出/商店分支见 results/feed-20260912/summary.json 和各集合目录；未列集合未运行。', '',
                  '## 耦合与局限', '',
                  '交易量抵消不保证双人定价同步等价；保留库存会占仓；市场买入晚于当回合工人动作；满槽可能阻断补货；返仓发生在市场之后。修复动物饲喂还会改变产品供给及之后收益。工人位置变化可能影响原有修复器和对手反应。',
                  '固定动作带不会响应新布局/市场，不得用于声称真实强手胜率。闭环公开版本比当前强手弱；少数种子不提供发布级泛化置信度。没有换算 Kaggle rating。', '',
                  '复现：先构建冻结候选，再使用 run_feed_track.py 的相应集合与 --variant；已有结果会跳过。只在独立工作副本清空对应结果目录后重算，不覆盖发布原件。',
                  'Git 每候选独立记录；本机认证若不可用，保留本地提交并报告未推送。完整报告见 reports/p1-20260912-report.md。', '']
        (LAB/f'reports/versions/feed-{v}.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k: v for k,v in index.items() if k not in ('files','analysis_source_sha256')}))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
