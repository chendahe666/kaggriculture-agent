"""Small explicit Git archive allowlist. No raw replays, private state, or push."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent/'kaggriculture-agent';DEST=REPO/ROOT.name
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args],text=True,encoding='utf-8').strip()
p=argparse.ArgumentParser();p.add_argument('mode',choices=['variant','historical','round']);p.add_argument('--name');a=p.parse_args()
assert git('remote','get-url','origin')=='https://github.com/chendahe666/kaggriculture-agent.git'
dirty=git('status','--porcelain')
if a.mode=='variant':
    assert a.name in ('clean','adaptive')
    paths=[p for p in (ROOT/f'experiments/track-r3-20260917/{a.name}').glob('*') if p.is_file()]
    title=f'research(R3): archive {a.name} opening variant'
    body=(ROOT/f'experiments/track-r3-20260917/{a.name}/VERSION_REPORT.md').read_text(encoding='utf-8')
elif a.mode=='historical':
    assert a.name.isdigit()
    paths=[p for p in (ROOT/f'version-archive/submissions/{a.name}').rglob('*') if p.is_file()]
    manifest=json.loads((ROOT/f'version-archive/submissions/{a.name}/manifest.json').read_text(encoding='utf-8'))
    if manifest.get('baseline_sha256'):paths.append(ROOT/f'version-archive/baselines/{manifest["baseline_sha256"]}/main.py')
    title=f'archive(Kaggle): preserve submission {a.name}'
    body=json.dumps(manifest,ensure_ascii=False,indent=2)
else:
    relatives=['PIPELINE_PROMPT.md','OPTIMIZATION_LOG.md','research-state.json','reports/r3-20260917-plan.md','reports/r3-20260917-report.md','reports/r3-20260917-handoff.md','tests/test_monitoring.py','tests/test_r3.py']
    relatives+=['scripts/'+s for s in ('run_r2.py','run_r3.py','collect_r3.py','extract_r3_sources.py','audit_r3_sources.py','build_r3.py','analyze_r3.py','report_r3_data.py','render_r3_report.py','submit_r3.py','export_r3.py','monitor_scores.py','archive_submission.py')]
    relatives+=['results/r3-20260917/'+s for s in ('final-evaluation.json','paired-results.json','online-summary.json','online-games.json','test-receipt.json','reviewed-report.json')]
    paths=[ROOT/s for s in relatives]
    paths+=list((ROOT/'results/r3-20260917/submissions').glob('*.json'))
    paths+=list((ROOT/'version-archive/pre-submit/r3-clean-20260917').glob('*'))
    title='release(R3): submit56305191 and archive audited research evidence'
    body='One user-authorized trial; A may leave latest2. V46 production retained, no speculation opening.64research executions valid;228tests pass;fresh16games each clean10W6L vsA6W2T8L. Gain onlyone seed; V46development win-to-tie regression. FormalpromotionNOTpassed. COMPLETEinitial600,notconverged. Fullreport:kaggriculture-prize-lab/reports/r3-20260917-report.md. No raw replay/private inventories/credentials included.'
assert paths
if dirty:
    # Resume only our interrupted export of an entirely new variant directory.
    expected=f'?? kaggriculture-prize-lab/experiments/track-r3-20260917/'
    assert a.mode=='variant' and dirty==expected,'Preserve unrelated working edits'
    for existing in (DEST/'experiments/track-r3-20260917').rglob('*'):
        if existing.is_file():
            counterpart=ROOT/existing.relative_to(DEST)
            assert counterpart.is_file() and counterpart.read_bytes()==existing.read_bytes()
targets=[]
for src in paths:
    assert src.is_file() and not src.is_symlink()
    rel=src.relative_to(ROOT);dest=DEST/rel
    assert dest.resolve().is_relative_to(DEST.resolve()) and 'inbox' not in rel.parts
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest()
    targets.append(dest.relative_to(REPO).as_posix())
subprocess.run(['git','-C',str(REPO),'add','--',*targets],check=True)
if git('diff','--cached','--name-only'):
    subprocess.run(['git','-C',str(REPO),'commit','-m',title,'-m',body],check=True,stdout=subprocess.DEVNULL)
print(json.dumps(dict(mode=a.mode,name=a.name,files=len(targets),commit=git('rev-parse','HEAD'))))
