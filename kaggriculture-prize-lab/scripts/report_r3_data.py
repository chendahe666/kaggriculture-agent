"""Bounded reviewed evidence snapshot for the local report app."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/r3-20260917'
online=json.loads((OUT/'online-summary.json').read_text(encoding='utf-8'))
evaluation=json.loads((OUT/'final-evaluation.json').read_text(encoding='utf-8'))
def query(rows,files,detail):
    return dict(rows=rows,source=dict(type='file',name='Kaggriculture R3 verified evidence',files=files,evidenceFlow=[dict(title='Acquisition and transformation',detail=detail)],caveats=['Current opponent ratings are not prematch ratings. Fixed pool and few seeds do not imply leaderboard score.']),methods=[dict(language='python',code='Run scripts/analyze_r3.py against frozen inbox/r3-20260917 and results/r3-20260917/runs; group official completed public episodes; exact submission-ID score join; compare terminal rewards.')])
rows=[dict(submission=s['ref'],score=float(s['publicScore']),**online['results'][str(s['ref'])]['all'],slices=online['results'][str(s['ref'])]['by_current_score_band'],first20=online['results'][str(s['ref'])]['first20'],last20=online['results'][str(s['ref'])]['last20']) for s in online['submissions'] if str(s['ref']) in online['results']]
data=dict(surface='report',title='2000分来自生产底座升级，开局反制仍需取舍',generatedAt=evaluation['generated_utc'],status='observed',buildStatus='creating',filters=[],report=dict(asOf=online['snapshot_utc']),queries={
'online':query(rows,['results/r3-20260917/online-summary.json'],'Official Kaggle SDK competition_submissions(kaggriculture, page_size=100), competition_list_episodes(56294951), competition_list_episodes(56294957). Snapshot '+online['snapshot_utc']+'. All returned unique completed public games; validation games excluded.'),
'confirmation':query(evaluation['paired_confirmation'],['results/r3-20260917/paired-results.json'],'Official kaggle-environments 1.32.7, actual Python file loader, full 720 frames, fresh seeds 917401/917402; immutable source hashes in run receipts.'),
'audits':query([dict(episode=d['episode_id'],seat=p['seat'],money=p['final_money'],harvest_wheat=p['harvest'].get('WHEAT',0),harvest_strawberry=p['harvest'].get('STRAWBERRY',0),harvest_tomato=p['harvest'].get('TOMATO',0),hire_cost=p['hire_cost'],land_cost=p['land_cost']) for f in (OUT/'runs').glob('audit-*.json') for d in [json.loads(f.read_text(encoding='utf-8'))] for p in d['players']],['results/r3-20260917/runs/audit-109959976.json','results/r3-20260917/runs/audit-110011798.json','results/r3-20260917/runs/audit-109934089.json','results/r3-20260917/runs/audit-109953373.json'],'Four diagnostic, non-random replays; exact public/private full-state offline calibration; zero state mismatch and zero cash balance error. No private states included in this report snapshot.')})
runs=[json.loads(f.read_text(encoding='utf-8')) for f in (OUT/'runs').glob('*.json')]
data['queries']['development']=query([{k:r[k] for k in ('candidate','opponent','seed','seat','margin','valid','candidate_sha256','opponent_sha256')} for r in runs if r['kind']=='league' and r['seed']==917301],['results/r3-20260917/runs'],'All development games seed917301, both seats, unchanged official file-loader engine; full record source hashes preserved.')
data['queries']['audits']['rows']=[{k:p[k] for k in ('seat','final_money','harvest','sale_revenue','purchase_cost','hire_cost','land_cost','cash_balance_error','wheat_balance_error')} | {'episode':r['episode_id']} for r in runs if r['kind']=='audit' for p in r['players']]
references=[]
for folder in (ROOT/'inbox/r3-20260917/sources').iterdir():
    if (folder/'acquisition.json').exists():references.append(json.loads((folder/'acquisition.json').read_text(encoding='utf-8')))
for f in (ROOT/'inbox/r3-20260917/official').glob('*.source.json'):references.append(json.loads(f.read_text(encoding='utf-8')))
data['queries']['references']=query(references,['inbox/r3-20260917/sources/*/acquisition.json','inbox/r3-20260917/official/*.source.json'],'Read-only official SDK kernels_pull of four named notebooks; public GitHub raw official engine/docs; acquisition times and exact raw hashes. Kernel download does not establish claimed leaderboard rating.')
if (OUT/'submissions/latest-status.json').exists():
    release=json.loads((OUT/'submissions/latest-status.json').read_text(encoding='utf-8'))
    data['queries']['release']=query([dict(**s,checked_utc=release['checked_utc']) for s in release['submissions'][:3]],['results/r3-20260917/submissions/latest-status.json'],'Official SDK independently re-listed submissions after single upload; COMPLETE distinct from converged rating.')
(OUT/'reviewed-report.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
