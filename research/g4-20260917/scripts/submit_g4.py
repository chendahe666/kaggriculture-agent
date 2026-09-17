"""One user-authorized G4 upload. Freeze first; never blindly retry."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from archive_submission import immutable,save

LAB=Path(__file__).resolve().parents[1]
OUT=LAB/'results/g4-20260917/submissions'
EXPECTED='f4ecd4876fde93a14e3381993283f3b6a1afa023b48dd57217f4d90794d39842'
DESC='G4 Public V47 integrated trial | Ahmed Berat Ozer credit | f4ecd487'
def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def status(api):
    fields=('ref','date','description','fileName','totalBytes','status','publicScore')
    rows=[{k:s.to_dict().get(k) for k in fields} for s in api.competition_submissions('kaggriculture',page_size=20)]
    data=dict(checked_utc=now(),submissions=rows,limits=api.competition_get_submission_limits('kaggriculture').to_dict())
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    save(OUT/f'status-{stamp}.json',data)
    print(json.dumps(data,ensure_ascii=False));return data

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['submit','status']);a=parser.parse_args()
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate()
    if a.mode=='status':status(api);return
    assert not (OUT/'attempt.json').exists(),'Prior attempt exists: inspect server, do not retry'
    e=read(LAB/'results/g4-20260917/final-evaluation.json');t=read(LAB/'results/g4-20260917/test-receipt.json')
    assert e['all_valid'] and e['research_completed']==63 and e['total_full_executions']==69
    assert e['selected']['sha256']==EXPECTED and e['selected']['max_call_seconds']<1 and e['selected']['min_overage_seconds']>=59
    assert t['passed'] and t['distinct_tests_passed']==258
    before=status(api);assert before['limits']['numAllowedNow']>=1
    latest=sorted(before['submissions'],key=lambda r:r['date'],reverse=True)[:2]
    assert [int(r['ref']) for r in latest]==[56305191,56294957],'Latest pair changed: reassess before upload'
    assert not any(r['description']==DESC for r in before['submissions'])
    pages={n:[p.to_dict() for p in api.competition_list_pages('kaggriculture',n)] for n in ('evaluation','rules','timeline')}
    save(OUT/'official-pages-before-upload.json',dict(checked_utc=now(),pages=pages))
    raw=(LAB/'experiments/track-g4-20260917/public-v47/main.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==EXPECTED
    archive=LAB/'version-archive/pre-submit/g4-public-v47-20260917'
    immutable(archive/'main.py',raw)
    immutable(archive/'baseline.py',(LAB/'experiments/track-r3-20260917/clean/main.py').read_bytes())
    immutable(archive/'NOTES.md',(LAB/'reports/g4-20260917-report.md').read_bytes())
    save(archive/'manifest.json',dict(name='G4 public V47',sha256=EXPECTED,pre_submit_verified_utc=now(),submission_id=None,submitted_utc=None,formal_promotion=False,original_strategy_authorship=False,source='https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v47-reactive-market-coordination',baseline_sha256='dc3d7927e264e3823578dcb75c07ba95cf8ac94b54f607ae1a7d6284417f1885'))
    save(OUT/'attempt.json',dict(started_utc=now(),sha256=EXPECTED,description=DESC,archive=str(archive.relative_to(LAB)),limits_before=before['limits'],authorization='Latest user explicitly requested optimization followed by latest version submission. Exactly one exploratory upload; retains R3, B leaves latest two.',evaluation='63 valid research executions;258 distinct tests passed;4 wins vs C in2seeds;2 transfer wins;2 valid selfplay ties;not formal promotion',budget_deviation='69 total full executions including6 unit fixtures;5 over64 cap;reported and all further simulations stopped'))
    response=api.competition_submit(str(archive/'main.py'),DESC,'kaggriculture',quiet=True).to_dict()
    safe={k:response[k] for k in ('ref','message','errorDescription','errorCode') if k in response}
    save(OUT/'receipt.json',dict(completed_utc=now(),sha256=EXPECTED,response=safe))
    print(json.dumps(safe,ensure_ascii=False))

if __name__=='__main__':main()
