"""Descriptive paired development outcomes; never labels development as release."""
from collections import defaultdict
import json
from pathlib import Path
import statistics

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB/'results/terminal-20260912'

def points(row):
    margin = row['margin']
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0

def main():
    rows = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'development').glob('*.json')]
    controls = {(r['opponent'], r['seed'], r['seat']): r for r in rows if r['variant'] == 'baseline'}
    grouped = defaultdict(list)
    for r in rows:
        if r['variant'] != 'baseline':
            grouped[r['variant']].append(r)
    summary = {'split': 'development_only', 'total_simulations': len(rows), 'variants': {}}
    for name, group in sorted(grouped.items()):
        paired = [(r, controls[(r['opponent'], r['seed'], r['seat'])]) for r in group
                  if (r['opponent'], r['seed'], r['seat']) in controls]
        family = {}
        for fam in sorted({r['family'] for r, _ in paired}):
            pairs = [(r,b) for r,b in paired if r['family'] == fam]
            family[fam] = {'games': len(pairs), 'baseline_points': sum(points(b) for r,b in pairs),
                           'candidate_points': sum(points(r) for r,b in pairs),
                           'gain': statistics.mean(points(r)-points(b) for r,b in pairs),
                           'mean_margin_gain': statistics.mean(r['margin']-b['margin'] for r,b in pairs)}
        summary['variants'][name] = {
            'candidate_sha256': sorted({r['candidate_sha256'] for r in group}),
            'games': len(group), 'paired': len(paired), 'family': family,
            'macro_gain': statistics.mean(f['gain'] for f in family.values()) if family else None,
            'mean_margin_gain': statistics.mean(r['margin']-b['margin'] for r,b in paired) if paired else None,
            'positive_outcome_flips': sum(points(r)>points(b) for r,b in paired),
            'negative_outcome_flips': sum(points(r)<points(b) for r,b in paired),
            'baseline_points': sum(points(b) for r,b in paired), 'candidate_points': sum(points(r) for r,b in paired),
            'mean_wall_seconds': statistics.mean(r['wall_seconds'] for r in group),
            'max_call_ms': max(r['max_call_ms'][r['seat']] for r in group),
            'mean_search_nodes': statistics.mean(r['terminal_diagnostics'].get('search_nodes',0) for r in group),
            'mean_terminal_cargo': statistics.mean(sum(sum(inv.values()) for inv in r['final_after_market'].get('carried',[[],[]])[r['seat']]) for r in group),
            'all_clean': all(r['statuses']==['DONE','DONE'] and not r['errors'] and r['frames']==720 for r in group),
            'decision': 'DEVELOPMENT_NOT_A_RELEASE_GATE'}
    (ROOT/'development-summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
