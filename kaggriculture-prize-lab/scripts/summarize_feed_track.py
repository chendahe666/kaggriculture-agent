"""Paired outcome and economic/safety regression report; no rating conversion."""
from collections import defaultdict
import json
from pathlib import Path
import statistics
from collect_elite_corpus import save

ROOT = Path(__file__).resolve().parents[1]/'results/feed-20260912'


def points(row):
    return 1 if row['margin'] > 0 else 0 if row['margin'] < 0 else .5


def main():
    report = {}
    for kind in ('own', 'elite', 'elite-top', 'league'):
        pairs = defaultdict(dict)
        for path in sorted((ROOT/kind).glob('*.json')):
            r = json.loads(path.read_text(encoding='utf-8'))
            j = r['job']
            key = (j.get('episode_id'), j.get('opponent'), j.get('seed'), j['seat'])
            pairs[key][j['variant']] = r
        section = {}
        variants = sorted({v for group in pairs.values() for v in group if v != 'baseline'})
        for v in variants:
            comparisons = []
            for key, group in pairs.items():
                if 'baseline' not in group or v not in group:
                    continue
                b, c = group['baseline'], group[v]
                s = c['job']['seat']
                comparisons.append({'key': key, 'baseline_margin': b['margin'], 'candidate_margin': c['margin'],
                    'gain_points': points(c)-points(b), 'delta_margin': c['margin']-b['margin'],
                    'shop_path_changed_vs_baseline': b['shops'] != c['shops'],
                    'safety_delta': {k: c['safety'][s].get(k, 0)-b['safety'][s].get(k, 0)
                                     for k in ('feed_failed_no_wheat', 'escaped_animals', 'overflow_units', 'wheat_overflow')},
                    'wheat_cost_delta': c['market_spending'][s].get('BUY_PRODUCT:WHEAT', 0)-b['market_spending'][s].get('BUY_PRODUCT:WHEAT', 0),
                    'clean': c['statuses'] == ['DONE', 'DONE'] and c['frames'] == 720 and not c['errors'],
                    'max_call_ms': c['max_call_ms'][s]})
            if not comparisons:
                continue
            section[v] = {'paired_games': len(comparisons),
                'baseline_wins': sum(r['baseline_margin'] > 0 for r in comparisons),
                'candidate_wins': sum(r['candidate_margin'] > 0 for r in comparisons),
                'baseline_ties': sum(r['baseline_margin'] == 0 for r in comparisons),
                'candidate_ties': sum(r['candidate_margin'] == 0 for r in comparisons),
                'positive_outcome_flips': sum(r['gain_points'] > 0 for r in comparisons),
                'negative_outcome_flips': sum(r['gain_points'] < 0 for r in comparisons),
                'mean_point_gain': statistics.mean(r['gain_points'] for r in comparisons),
                'mean_margin_gain': statistics.mean(r['delta_margin'] for r in comparisons),
                'mean_wheat_cost_delta': statistics.mean(r['wheat_cost_delta'] for r in comparisons),
                'shop_changed_games': sum(r['shop_path_changed_vs_baseline'] for r in comparisons),
                'more_escapes_games': sum(r['safety_delta']['escaped_animals'] > 0 for r in comparisons),
                'more_failed_feed_games': sum(r['safety_delta']['feed_failed_no_wheat'] > 0 for r in comparisons),
                'more_overflow_games': sum(r['safety_delta']['overflow_units'] > 0 for r in comparisons),
                'all_clean': all(r['clean'] for r in comparisons),
                'max_call_ms': max(r['max_call_ms'] for r in comparisons), 'comparisons': comparisons}
        report[kind] = section
    save(ROOT/'summary.json', report)
    print(json.dumps({kind: {v: {k: val for k, val in record.items() if k != 'comparisons'}
                           for v, record in variants.items()} for kind, variants in report.items()}))


if __name__ == '__main__':
    main()
