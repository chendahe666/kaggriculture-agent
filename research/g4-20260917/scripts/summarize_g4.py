"""Offline, sanitized G4 receipts. Never runs an agent or publishes replay states."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from archive_submission import save

LAB=Path(__file__).resolve().parents[1]
OUT=LAB/'results/g4-20260917'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    raw=[read(p) for p in sorted((OUT/'runs').glob('*.json'))]
    league=[r for r in raw if r['kind']=='league']
    fields=('key','phase','candidate','opponent','seed','seat','candidate_sha256','opponent_sha256','engine_sha256','valid','margin','rewards','statuses','frames','errors','max_call_seconds','min_overage_seconds','started_utc','completed_utc')
    rows=[{k:r[k] for k in fields} for r in league]
    groups=defaultdict(list)
    for r in rows:groups[(r['phase'],r['candidate'],r['opponent'])].append(r)
    summary=[]
    for (phase,c,o),rs in groups.items():
        summary.append(dict(phase=phase,candidate=c,opponent=o,n=len(rs),seeds=sorted({r['seed'] for r in rs}),wins=sum(r['margin']>0 for r in rs),ties=sum(r['margin']==0 for r in rs),losses=sum(r['margin']<0 for r in rs),mean_margin=sum(r['margin'] for r in rs)/len(rs)))
    index={(r['phase'],r['candidate'],r['opponent'],r['seed'],r['seat']):r for r in rows}
    paired=[]
    for r in rows:
        control='R3' if r['phase']=='noop' else 'C'
        if r['candidate']==control:continue
        c=index.get((r['phase'],control,r['opponent'],r['seed'],r['seat']))
        if not c:continue
        a=read(OUT/'traces'/f"{r['key']}.json")['trace'];b=read(OUT/'traces'/f"{c['key']}.json")['trace']
        first=lambda key:next((i for i,(x,y) in enumerate(zip(a,b)) if x[key]!=y[key]),None)
        paired.append(dict(candidate_key=r['key'],control_key=c['key'],margin_delta=r['margin']-c['margin'],outcome_delta=(r['margin']>0)+.5*(r['margin']==0)-(c['margin']>0)-.5*(c['margin']==0),first_shop_divergence=first('shops'),first_state_divergence=first('states'),first_action_divergence=first('actions')))
    finalhash=sha(LAB/'experiments/track-g4-20260917/public-v47/main.py')
    finalcalls=[];finalover=[]
    for r in rows:
        for seat,h in ((r['seat'],r['candidate_sha256']),(1-r['seat'],r['opponent_sha256'])):
            if h==finalhash:finalcalls.append(r['max_call_seconds'][seat]);finalover.append(r['min_overage_seconds'][seat])
    reservations=sum(len(read(p)['jobs']) for p in OUT.glob('plan-*.json'))
    result=dict(round='G4-20260917',all_valid=all(r['valid'] for r in raw),research_completed=len(raw),research_reserved_attempts=reservations,failed_before_game=reservations-len(raw),full_horizon_test_fixture_executions=6,total_full_executions=len(raw)+6,cap=64,cap_excess=len(raw)+6-64,budget_status='BREACHED: test fixtures omitted from runner reservation; no further simulations',by_phase=dict(Counter(r['phase'] for r in raw)),groups=summary,rows=rows,selected=dict(name='public-v47',sha256=finalhash,max_call_seconds=max(finalcalls),min_overage_seconds=min(finalover),formal_promotion=False,original_strategy_authorship=False,adaptive_selection=True),inference='No rating prediction. Seats clustered by seed; V47 selection reused confirmation results, so those seeds are development for V47. Transfer panel is small and not matched to R3.')
    save(OUT/'final-evaluation.json',result)
    save(OUT/'paired-results.json',paired)
    save(OUT/'test-receipt.json',dict(passed=True,full_suite_passed=253,additional_passed=5,distinct_tests_passed=258,single_258_test_run=False,first_suite='252 passed;1 sandbox temporary-directory error;full suite repeated with approval',additional_first_attempt='4 passed;1 incorrect module import;import corrected;all5 passed',full_horizon_fixture_executions=6,test_sources={p.name:sha(p) for p in (LAB/'tests').glob('test_g4*.py')}))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','groups')},ensure_ascii=False))
    print(json.dumps(summary,ensure_ascii=False))
    print('Shop-divergent paired blocks:',sum(p['first_shop_divergence'] is not None for p in paired),'/',len(paired))

if __name__=='__main__':main()
