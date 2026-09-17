"""One explicitly authorized R3 trial, immutable freeze and no blind retry."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from archive_submission import immutable,save
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/r3-20260917/submissions'
EXPECTED='dc3d7927e264e3823578dcb75c07ba95cf8ac94b54f607ae1a7d6284417f1885'
DESC='R3 Clean opening | V46 production retained | dc3d7927'
def now():return datetime.now(timezone.utc).isoformat()
def status(api):
    fields=('ref','date','description','fileName','totalBytes','status','publicScore')
    rows=[{k:s.to_dict().get(k) for k in fields} for s in api.competition_submissions('kaggriculture',page_size=20)]
    record=dict(checked_utc=now(),submissions=rows,limits=api.competition_get_submission_limits('kaggriculture').to_dict())
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'latest-status.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False));return record
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['submit','status']);a=p.parse_args()
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate()
    if a.mode=='status':status(api);return
    assert not (OUT/'attempt.json').exists(),'Potential previous upload: inspect server; do not retry'
    e=json.loads((ROOT/'results/r3-20260917/final-evaluation.json').read_text(encoding='utf-8'))
    assert e['all_valid'] and e['full_games']==64
    c=e['candidates']['clean'];assert c['sha256']==EXPECTED and c['max_call_seconds']<1 and c['min_overage_seconds']>=59
    assert c['by_opponent']['clean']['n']==2
    t=json.loads((ROOT/'results/r3-20260917/test-receipt.json').read_text(encoding='utf-8'));assert t['tests']==228 and t['passed']
    before=status(api);assert before['limits']['numAllowedNow']>=1
    assert not any(s['description']==DESC for s in before['submissions'])
    raw=(ROOT/'experiments/track-r3-20260917/clean/main.py').read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
    archive=ROOT/'version-archive/pre-submit/r3-clean-20260917'
    immutable(archive/'main.py',raw)
    immutable(archive/'NOTES.md',(ROOT/'reports/r3-20260917-report.md').read_bytes())
    save(archive/'manifest.json',dict(name='R3 clean',sha256=EXPECTED,parent_sha256='c4c890f4e73b72dbbcc93edfc22ec1c17f40c9751cd2206214f38351fe227282',pre_submit_verified_utc=now(),submission_id=None,submitted_utc=None,formal_promotion=False,source='experiments/track-r3-20260917/clean/main.py'))
    save(OUT/'attempt.json',dict(started_utc=now(),sha256=EXPECTED,description=DESC,archive=str(archive.relative_to(ROOT)),limits_before=before['limits'],authorization='User explicitly selected ONE optimized submission, accepting A56294951 leaving latest two. No backup submission.',evaluation='64 valid full research executions;228 regression tests;confirmation10W6L vs A6W2T8L;exploratory, not formal promotion'))
    result=api.competition_submit(str(archive/'main.py'),DESC,'kaggriculture',quiet=True).to_dict()
    save(OUT/'receipt.json',dict(completed_utc=now(),sha256=EXPECTED,response=result))
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
