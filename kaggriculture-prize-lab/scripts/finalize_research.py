"""Rebuild summaries from immutable result JSON; no leaderboard claims."""
import hashlib,json,statistics
from collections import defaultdict
from pathlib import Path
LAB=Path(__file__).resolve().parents[1]
def read(name):return json.loads((LAB/name).read_text(encoding='utf-8'))
def points(row):
    a,b=row['rewards'][row['seat']],row['rewards'][1-row['seat']]
    return 1 if a>b else .5 if a==b else 0
def describe(rows):
    outcomes=[points(r) for r in rows]
    return {'games':len(rows),'wins':outcomes.count(1),'ties':outcomes.count(.5),'losses':outcomes.count(0),
            'mean_margin':statistics.mean(r['margin'] for r in rows) if rows else None,
            'all_clean':all(r['statuses']==['DONE','DONE'] and not r['errors'] for r in rows),
            'max_measured_call_ms':max((max(r['max_call_ms']) for r in rows),default=0)}
profiles={r['episode_id']:r for r in read('results/current-strategy-profiles.json')}
pool={r['sha256']:r for r in read('opponent-pool.json')['opponents']}
calibration=read('results/current-corpus-calibration-v2.json')
economics=[]
for r in calibration['matches']:
    profile=profiles[r['episode_id']]
    if profile['source']!='own_recent':continue
    players=[]
    for seat in (0,1):
        sale=sum(r['sale_revenue'][seat].values())
        purchases=sum(r['market_spending'][seat].values())
        quadrants=len(profile['players'][seat]['snapshots']['719']['quadrants'])
        land=[0,0,1000,3000,7000][quadrants]
        # For verified default startingMoney=3000, money changes only through
        # market sales/purchases, land and hires. Exact accounting identity.
        hire=3000+sale-purchases-land-r['rewards'][seat]
        players.append({'name':profile['players'][seat]['name'],'sale_revenue':sale,'purchase_cost':purchases,
                        'land_cost':land,'hire_cost_by_accounting_identity':hire,'final_money':r['rewards'][seat]})
    economics.append({'episode_id':r['episode_id'],'players':players})
report={'calibration_games':len(calibration['matches']),
        'state_mismatches':sum(r['state_mismatches'] for r in calibration['matches']),
        'own_recent_economics':economics,'experiments':{}}
names=['cok-current-replay','track-integrated-current-corpus','track-integrated-dev',
       'track-rank-screen','track-sweep-screen','track-sweep-rank-screen',
       'cok-diverse-dev','track-gated-current-own','track-gated-validation-v1','cok-validation-v1']
base={r['episode_id']:r for r in read('results/cok-current-replay.json')['matches']}
for name in names:
    path=LAB/f'results/{name}.json'
    if not path.exists():continue
    result=json.loads(path.read_text(encoding='utf-8'));rows=result['matches']
    entry={'file':str(path.relative_to(LAB)),'result_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
           'total':describe(rows),'per_opponent':result['summary'].get('per_opponent')}
    if rows[0].get('evidence')=='closed_loop':
        family_opponents=defaultdict(dict)
        for opponent,summary in entry['per_opponent'].items():
            identity=result['manifest'].get('opponents',{}).get(opponent)
            family=pool.get(identity,{}).get('family','unclassified:'+opponent)
            family_opponents[family][opponent]=summary['expected_match_score']
        entry['family_scores']={family:statistics.mean(v.values()) for family,v in family_opponents.items()}
        entry['family_macro_match_score']=statistics.mean(entry['family_scores'].values())
        entry['family_count']=len(family_opponents)
        entry['family_gate_pass']=entry['family_count']>=5
    if 'episode_id' in rows[0]:
        own=[r for r in rows if r['episode_id'] in base]
        entry['own_recent_only']=describe(own)
        if own:
            entry['paired_mean_margin_change']=statistics.mean(r['margin']-base[r['episode_id']]['margin'] for r in own)
            entry['win_to_loss']=[r['episode_id'] for r in own if points(base[r['episode_id']])==1 and points(r)==0]
            entry['improved_margins']=sum(r['margin']>base[r['episode_id']]['margin'] for r in own)
            entry['regressed_margins']=sum(r['margin']<base[r['episode_id']]['margin'] for r in own)
    report['experiments'][name]=entry
out=LAB/'results/research-report-20260911.json'
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
for e in economics:
    if e['episode_id'] in (107903783,107942319,107872505,107958155):print(json.dumps(e,ensure_ascii=False))
for name,r in report['experiments'].items():
    print(name,json.dumps(r.get('own_recent_only',r['total']),ensure_ascii=False),r.get('paired_mean_margin_change'))
