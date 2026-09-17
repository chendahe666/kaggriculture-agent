"""Bounded G4 read-only metadata and public-source collection; no uploads."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

LAB = Path(__file__).resolve().parents[1]
OUT = LAB / 'inbox/g4-20260917'

def now(): return datetime.now(timezone.utc).isoformat()
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f: json.dump(value, f, ensure_ascii=False, indent=2)

def main():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi(); api.authenticate()
    if not (OUT/'metadata.json').exists():
        start=now()
        fields=('ref','date','description','status','publicScore','fileName','totalBytes')
        submissions=[{k:r.to_dict().get(k) for k in fields} for r in api.competition_submissions('kaggriculture',page_size=100)]
        data=dict(started_utc=start,completed_utc=now(),submissions=submissions,
                  limits=api.competition_get_submission_limits('kaggriculture').to_dict(),
                  pages={name:[p.to_dict() for p in api.competition_list_pages('kaggriculture',name)] for name in ('evaluation','rules','timeline')},
                  kernels=[k.to_dict() for k in api.kernels_list(competition='kaggriculture',page_size=30,sort_by='dateRun')])
        save(OUT/'metadata.json',data)
        print(json.dumps({'submissions':submissions[:3],'limits':data['limits']}),flush=True)
    urls={
        'official/kaggriculture.py':'https://raw.githubusercontent.com/Kaggle/kaggle-environments/master/kaggle_environments/envs/kaggriculture/kaggriculture.py',
        'official/README.md':'https://raw.githubusercontent.com/Kaggle/kaggle-environments/master/kaggle_environments/envs/kaggriculture/README.md',
        'medgm/main.py':'https://raw.githubusercontent.com/MedGm/kaggriculture-agent/master/main.py',
        'medgm/LICENSE':'https://raw.githubusercontent.com/MedGm/kaggriculture-agent/master/LICENSE',
        'medgm/README.md':'https://raw.githubusercontent.com/MedGm/kaggriculture-agent/master/README.md',
    }
    for name,url in urls.items():
        dest=OUT/name
        if dest.exists(): continue
        started=now()
        try:
            with urllib.request.urlopen(url,timeout=30) as response: raw=response.read()
        except Exception as exc:
            print(json.dumps({'name':name,'error_type':type(exc).__name__}),flush=True);continue
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(raw)
        save(dest.with_name(dest.name+'.receipt.json'),dict(url=url,started_utc=started,completed_utc=now(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        print(name,len(raw),flush=True)
    for name,ref in {'v47':'ahmedberatozer/kaggriculture-v47-reactive-market-coordination',
                     'independent':'anhadmahajan06/kaggriculture-autonomous-ai-farming-agent'}.items():
        dest=OUT/'sources'/name
        if (dest/'receipt.json').exists():continue
        start=now();dest.mkdir(parents=True,exist_ok=True)
        api.kernels_pull(ref,str(dest),metadata=True,quiet=True)
        save(dest/'receipt.json',dict(ref=ref,started_utc=start,completed_utc=now(),files=[dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in dest.iterdir() if p.is_file()]))
        print('pulled',ref,flush=True)
    snapshot=LAB/'monitoring/snapshots/20260917T202401204111Z.json'
    if snapshot.exists() and not (OUT/'replay-selection.json').exists():
        data=json.loads(snapshot.read_text(encoding='utf-8'));sid=56305191;rows=[]
        for e in data['episodes'][str(sid)]:
            if e.get('state')!='COMPLETED' or e.get('type')!='EPISODE_TYPE_PUBLIC':continue
            own=next((a for a in e['agents'] if a.get('submissionId')==sid),None)
            other=next((a for a in e['agents'] if a.get('submissionId')!=sid),None)
            if not own or not other or 'reward' not in own or 'reward' not in other:continue
            rows.append(dict(episode_id=e['id'],seat=own.get('index',0),margin=own['reward']-other['reward'],opponent=other,ended_utc=e['endTime'],opponent_collection_rating=data['opponent_scores'].get(str(other['submissionId'])),prematch_rating=None))
        selected=[min((r for r in rows if r['margin']<0),key=lambda r:r['margin']),min((r for r in rows if r['margin']>0),key=lambda r:r['margin'])]
        save(OUT/'replay-selection.json',dict(selected_utc=now(),method='R3 widest loss and closest win; diagnostic not representative',rows=selected))
    if (OUT/'replay-selection.json').exists():
        for row in json.loads((OUT/'replay-selection.json').read_text())['rows']:
            eid=row['episode_id'];dest=OUT/'replays';dest.mkdir(exist_ok=True)
            path=dest/f'episode-{eid}-replay.json';receipt=dest/f'{eid}.receipt.json'
            if receipt.exists():continue
            assert not path.exists(),'Review partial prior acquisition'
            start=now();api.competition_episode_replay(eid,str(dest),quiet=True)
            raw=path.read_bytes();assert json.loads(raw)['info']['EpisodeId']==eid
            save(receipt,dict(**row,started_utc=start,completed_utc=now(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            print('replay',eid,len(raw),flush=True)

if __name__=='__main__':main()
