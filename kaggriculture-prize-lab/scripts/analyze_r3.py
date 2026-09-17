"""Version-exact current-score joins and paired outcome summaries; no rating model."""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
import monitor_scores as m
ROOT=Path(__file__).resolve().parents[1];IN=ROOT/'inbox/r3-20260917';OUT=ROOT/'results/r3-20260917'
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
snap=json.loads((IN/'snapshot.json').read_text(encoding='utf-8'));scores={}
for f in (IN/'teams').glob('*.json'):
    t=json.loads(f.read_text(encoding='utf-8'))
    for s in t['submissions']:scores[s['id']]=(m.number(s.get('publicScore')),t['completed_utc'])
games=[];online={}
for sid,episodes in snap['episodes'].items():
    sid=int(sid);episodes=list({e['id']:e for e in episodes}.values());slices=defaultdict(list)
    for e in episodes:
        outcome=m.outcome(e,sid)
        if outcome is None:continue
        own=next(a for a in e['agents'] if a.get('submissionId')==sid)
        opp=next(a for a in e['agents'] if a.get('submissionId')!=sid)
        score,at=scores.get(opp['submissionId'],(None,None))
        row=dict(episode_id=e['id'],submission_id=sid,seat=own.get('index',0),outcome=outcome,margin=own['reward']-opp['reward'],opponent_submission_id=opp['submissionId'],opponent_name=opp.get('teamName'),opponent_current_score=score,score_observed_utc=at,opponent_prematch_score=None,opponent_rank=None,game_created_utc=e.get('createTime'),metadata_collected_utc=snap['completed_utc'],score_band=m.band(score))
        games.append(row);slices[m.band(score)].append(e)
    seq=sorted([e for e in episodes if m.outcome(e,sid) is not None],key=lambda e:e.get('createTime',''))
    online[str(sid)]=dict(all=m.stats(episodes,sid),by_current_score_band={k:m.stats(v,sid) for k,v in slices.items()},first20=m.stats(seq[:20],sid),last20=m.stats(seq[-20:],sid))
save('online-games.json',games);save('online-summary.json',dict(snapshot_utc=snap['completed_utc'],submissions=snap['submissions'],results=online,team_snapshots=len(list((IN/'teams').glob('*.json'))),prematch_scores_available=False))
runs=[json.loads(p.read_text(encoding='utf-8')) for p in (OUT/'runs').glob('*.json')]
def summarize(rs):
    n=len(rs);return dict(n=n,wins=sum(r['margin']>0 for r in rs),ties=sum(r['margin']==0 for r in rs),losses=sum(r['margin']<0 for r in rs),outcome_rate=sum((r['margin']>0)+.5*(r['margin']==0) for r in rs)/n if n else None)
league=[r for r in runs if r['kind']=='league'];cand={}
for c in sorted({r['candidate'] for r in league}):
    rs=[r for r in league if r['candidate']==c]
    cand[c]=dict(all=summarize(rs),by_opponent={o:summarize([r for r in rs if r['opponent']==o]) for o in sorted({r['opponent'] for r in rs})},max_call_seconds=max(r['max_call_seconds'][r['seat']] for r in rs),min_overage_seconds=min(r['min_overage_seconds'][r['seat']] for r in rs),sha256=rs[0]['candidate_sha256'])
base={(r['opponent'],r['seed'],r['seat']):r for r in league if r['candidate']=='A'}
pairs=[]
for r in league:
    key=(r['opponent'],r['seed'],r['seat'])
    if r['candidate']=='clean' and key in base:
        b=base[key];bp=(b['margin']>0)+.5*(b['margin']==0);cp=(r['margin']>0)+.5*(r['margin']==0)
        pairs.append(dict(opponent=key[0],seed=key[1],seat=key[2],baseline_margin=b['margin'],candidate_margin=r['margin'],baseline_points=bp,candidate_points=cp,delta=cp-bp,shop_path_same=r['shops']==b['shops'],split='confirmatory' if key[1] in (917401,917402) else 'development'))
save('paired-results.json',pairs)
result=dict(generated_utc=datetime.now(timezone.utc).isoformat(),full_games=len(runs),all_valid=all(r['valid'] for r in runs),candidates=cand,paired_confirmation=[x for x in pairs if x['split']=='confirmatory'],formal_promotion=False,reason='Bounded pilot, not five families x30 seeds; no calibrated Kaggle rating prediction')
save('final-evaluation.json',result)
print(json.dumps(dict(online=online,evaluation=result),ensure_ascii=False))
