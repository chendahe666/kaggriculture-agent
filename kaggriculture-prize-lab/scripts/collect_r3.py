"""R3 bounded official read-only acquisition. No submission calls."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import time
import urllib.request

LAB=Path(__file__).resolve().parents[1]
ROOT=LAB/'inbox/r3-20260917'
OWN=(56294951,56294957)

def now(): return datetime.now(timezone.utc).isoformat()
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a=KaggleApi();a.authenticate();return a

def metadata():
    a=api();p=ROOT/'snapshot.json'
    if not p.exists():
        started=now(); fields=('ref','date','description','fileName','totalBytes','status','publicScore')
        own=[{k:r.to_dict().get(k) for k in fields} for r in a.competition_submissions('kaggriculture',page_size=100)]
        episodes={str(s):[r.to_dict() for r in a.competition_list_episodes(s)] for s in OWN}
        pages=[r.to_dict() for r in a.competition_list_pages('kaggriculture','evaluation')]
        kernels=[r.to_dict() for r in a.kernels_list(competition='kaggriculture',page_size=30,sort_by='dateRun')]
        save(p,dict(started_utc=started,completed_utc=now(),submissions=own,episodes=episodes,evaluation=pages,kernels=kernels,
            source='Official Kaggle SDK. All returned episodes; no lifetime-completeness guarantee. Opponent prematch ratings not exposed.'))
    data=json.loads(p.read_text(encoding='utf-8'))
    teams=list(dict.fromkeys(x['teamId'] for s in OWN for r in data['episodes'][str(s)] for x in r['agents'] if x.get('submissionId') not in OWN))
    for team in teams[:100]:
        dest=ROOT/f'teams/{team}.json'
        if dest.exists():continue
        started=now()
        try:
            rows=[r.to_dict() for r in a.competition_team_submissions(team)]
        except Exception as e:
            response=getattr(e,'response',None)
            save(ROOT/f'errors/{time.time_ns()}.json',dict(team=team,utc=now(),error_type=type(e).__name__,http_status=getattr(response,'status_code',None)))
            raise SystemExit('Team lookup failed; stop rather than bypass retry limits')
        save(dest,dict(team_id=team,started_utc=started,completed_utc=now(),submissions=rows))
        print('team',team,flush=True);time.sleep(4)

def sources():
    a=api()
    refs={'jaxa':'jaxa623/2802-two-identical-agents-90-points-apart',
          'pipe8':'nathanjacob/kaggriculture-pipe-8-clean-opening',
          'microstructure':'haideptry/v46-vs-pipe-8-vs-jaxa-turn-1-microstructure-war',
          'v46':'ahmedberatozer/kaggriculture-v46-first-turn-microstructure-and-s'}
    for name,ref in refs.items():
        dest=ROOT/f'sources/{name}'
        if (dest/'acquisition.json').exists():continue
        dest.mkdir(parents=True,exist_ok=True);started=now();a.kernels_pull(ref,str(dest),metadata=True,quiet=True)
        save(dest/'acquisition.json',dict(ref=ref,started_utc=started,completed_utc=now(),files=[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in dest.iterdir() if p.is_file()]))
        print('source',ref,flush=True)
    dest=ROOT/'official';dest.mkdir(parents=True,exist_ok=True)
    for name in ('kaggriculture.py','README.md','kaggriculture.json','AGENTS.md'):
        path=dest/name
        if path.exists():continue
        url='https://raw.githubusercontent.com/Kaggle/kaggle-environments/master/kaggle_environments/envs/kaggriculture/'+name
        started=now()
        with urllib.request.urlopen(url,timeout=45) as r:raw=r.read()
        path.write_bytes(raw)
        save(dest/(name+'.source.json'),dict(url=url,started_utc=started,completed_utc=now(),sha256=hashlib.sha256(raw).hexdigest()))

def replay():
    a=api();data=json.loads((ROOT/'snapshot.json').read_text(encoding='utf-8'));rows=[]
    for sid,es in data['episodes'].items():
        for r in es:
            agents=r.get('agents',[]);ours=[x for x in agents if x.get('submissionId')==int(sid)]
            if r.get('type')!='EPISODE_TYPE_PUBLIC' or r.get('state')!='COMPLETED' or len(agents)!=2 or len(ours)!=1 or any('reward' not in x for x in agents):continue
            me=ours[0];opp=next(x for x in agents if x is not me);margin=me['reward']-opp['reward']
            rows.append(dict(submission_id=int(sid),episode_id=r['id'],seat=me.get('index',0),margin=margin,opponent=opp,created_utc=r['createTime']))
    selected=[]
    for sid,win,largest in [(OWN[0],False,False),(OWN[0],False,True),(OWN[0],True,False),(OWN[0],True,True),(OWN[1],False,True),(OWN[0],False,False)]:
        pool=[r for r in rows if r['submission_id']==sid and (r['margin']>0)==win and r['margin']!=0 and r['episode_id'] not in {x['episode_id'] for x in selected}]
        if pool:selected.append(sorted(pool,key=lambda r:abs(r['margin']),reverse=largest)[0])
    selection=ROOT/'selection.json'
    if not selection.exists():save(selection,dict(selected_utc=now(),method='A narrow/wide wins and losses plus B wide loss; six diagnostic cases, not prevalence sample',rows=selected))
    else:selected=json.loads(selection.read_text(encoding='utf-8'))['rows']
    for row in selected:
        dest=ROOT/'replays';dest.mkdir(parents=True,exist_ok=True);eid=row['episode_id'];p=dest/f'episode-{eid}-replay.json';receipt=ROOT/f'acquisition/{eid}.json'
        if receipt.exists():continue
        if p.exists():raise RuntimeError('Unreceipted replay: review partial previous download')
        assert shutil.disk_usage(LAB).free>8*1024**3
        started=now();a.competition_episode_replay(eid,str(dest),quiet=True)
        raw=p.read_bytes();assert json.loads(raw)['info']['EpisodeId']==eid
        save(receipt,dict(**row,download_started_utc=started,download_completed_utc=now(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        print('replay',eid,len(raw),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['metadata','sources','replay']);args=p.parse_args()
    globals()[args.mode]()
