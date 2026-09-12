"""Read-only Kaggle corpus acquisition. No submission/account mutation commands."""
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]

def cli(*args):
    result = subprocess.run([sys.executable, '-m', 'kaggle', 'competitions', *map(str,args)],
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr[-1200:])
    return result.stdout

def api(*args):
    return json.JSONDecoder().raw_decode(cli(*args, '--format', 'json').lstrip())[0]

def main():
    destination = LAB / 'inbox/replays'
    destination.mkdir(parents=True, exist_ok=True)
    snapshot = {'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'selection':'20 latest completed public own episodes plus 2 per top-five best active submission; not filtered on outcome',
                'own_submission':56156204,'matches':[]}
    jobs=[]
    own=api('episodes',56156204)
    # CLI may include enum-qualified strings. Never include validation episodes.
    def public(rows):
        return [r for r in rows if 'PUBLIC' in str(r.get('type','')) and 'COMPLETED' in str(r.get('state',''))]
    for r in public(own)[:20]:
        jobs.append({'episode_id':r['id'],'source':'own_recent','submission':56156204,'episode_metadata':r})
    teams=[16718819,16732403,16730612,16640510,16621799]
    for team in teams:
        submissions=api('team-submissions',team)
        best=max(submissions,key=lambda r:float(r.get('publicScore') or '-inf'))
        for r in public(api('episodes',best['id']))[:2]:
            jobs.append({'episode_id':r['id'],'source':'top5_public','team_id':team,
                         'submission':best['id'],'rating_snapshot':best['publicScore'],'episode_metadata':r})
    for job in jobs:
        path=destination / ('episode-'+str(job['episode_id'])+'-replay.json')
        if not path.exists():
            cli('replay',job['episode_id'],'-p',destination)
        payload=path.read_bytes()
        replay=json.loads(payload)
        if int(replay['info']['EpisodeId']) != int(job['episode_id']):
            raise ValueError('download ID mismatch')
        job['sha256']=hashlib.sha256(payload).hexdigest()
        job['path']=str(path.relative_to(LAB))
        snapshot['matches'].append(job)
        (LAB/'results/public-corpus-20260911.json').write_text(json.dumps(snapshot,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps({'downloaded':job['episode_id'],'source':job['source']},ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
