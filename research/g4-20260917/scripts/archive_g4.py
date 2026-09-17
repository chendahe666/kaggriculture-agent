"""Whitelist-only local archives and per-version commits; never uploads or pushes."""
import json
import subprocess
from pathlib import Path
from archive_submission import immutable,save

LAB=Path(__file__).resolve().parents[1]
REPO=LAB/'version-history/g4-20260917'
OUT=LAB/'results/g4-20260917'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args],text=True,encoding='utf-8').strip()
def main():
    assert git('status','--porcelain')==''
    git('checkout','-b','research/g4-20260917')
    base=REPO/'research/g4-20260917';commits=[]
    e=read(OUT/'final-evaluation.json')
    decisions={'C':'No-op control;one seed double-seat720state parity to R3;not a new strategy.',
      'M':'Market sell ordering;no outcome improvement in confirmation4W4L;DO NOT RELEASE.',
      'P':'Conservative animal substitution;zero whole-game activation;UNVALIDATED, DO NOT RELEASE.',
      'MP':'Combined probe;P unactivated;interaction not identified;DO NOT RELEASE.',
      'public-v47':'Public Ahmed Berat Ozer V47 byte-identical;selected exploratory submission56313428;not original authorship,not formal promotion.'}
    for name,decision in decisions.items():
        source=LAB/f'experiments/track-g4-20260917/{name}'
        for filename in ('main.py','manifest.json'):
            immutable(base/'versions'/name/filename,(source/filename).read_bytes())
        note=f'# G4 {name}\n\n{decision}\n\nFull round methodology: ../../reports/g4-20260917-report.md\n\n'
        note+='```json\n'+json.dumps([g for g in e['groups'] if g['candidate']==name],indent=2)+'\n```\n'
        immutable(source/'REPORT.md',note.encode())
        immutable(base/'versions'/name/'REPORT.md',note.encode())
        git('add','--',f'research/g4-20260917/versions/{name}')
        git('commit','-m',f'G4 {name}: {decision}')
        commits.append(dict(version=name,commit=git('rev-parse','HEAD')))
    whitelisted=['reports/g4-20260917-plan.md','reports/g4-20260917-report.md','reports/g4-20260917-submission.md',
       'results/g4-20260917/final-evaluation.json','results/g4-20260917/paired-results.json','results/g4-20260917/test-receipt.json',
       'scripts/collect_g4.py','scripts/extract_g4.py','scripts/audit_g4_sources.py','scripts/run_g4.py','scripts/g4_overlay.py','scripts/build_g4.py','scripts/summarize_g4.py','scripts/submit_g4.py','scripts/archive_g4.py','tests/test_g4.py','tests/test_g4_model.py']
    for rel in whitelisted:immutable(base/rel,(LAB/rel).read_bytes())
    for p in (OUT/'submissions').glob('*.json'):
        if p.name.startswith('status-') or p.name in ('attempt.json','receipt.json'):
            immutable(base/'receipts'/p.name,p.read_bytes())
    git('add','--','research/g4-20260917')
    git('commit','-m','G4 evidence:63research+6fixture runs;258tests;one V47 trial56313428;report budget breach')
    save(OUT/'git-local-receipt.json',dict(repository=str(REPO),branch='research/g4-20260917',versions=commits,head=git('rev-parse','HEAD'),pushed=False,original_repository_untouched=True))
    archive=LAB/'version-archive/submissions/56313428'
    for name in ('main.py','baseline.py','NOTES.md'):
        immutable(archive/name,(LAB/'version-archive/pre-submit/g4-public-v47-20260917'/name).read_bytes())
    save(archive/'manifest.json',dict(submission_id=56313428,submitted_utc='2026-09-17T20:48:09.047Z',sha256=e['selected']['sha256'],pre_submit_archive='version-archive/pre-submit/g4-public-v47-20260917',source='Public Ahmed Berat Ozer V47, embedded notices retained',formal_promotion=False))
    print(json.dumps(dict(commits=commits,head=git('rev-parse','HEAD')),ensure_ascii=False))

if __name__=='__main__':main()
