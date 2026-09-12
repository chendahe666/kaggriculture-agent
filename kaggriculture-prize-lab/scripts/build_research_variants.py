"""Deterministic mechanical variant generation; original candidate stays frozen."""
from pathlib import Path
import hashlib
import json

LAB = Path(__file__).resolve().parents[1]
source = (LAB / 'candidate/main.py').read_text(encoding='utf-8')

HORIZON = '''
def _future_sells(obs, step):
    actions = _kawa_actions(obs)
    result = {}
    for ahead in range(1, RESEARCH_HORIZON + 1):
        if step + ahead >= len(actions):
            break
        for order in actions[step + ahead].get('market', []):
            if len(order) >= 3 and order[0] == 'SELL' and order[1] in _PREMIUM:
                result[order[1]] = result.get(order[1], 0) + max(0, int(order[2]))
    return result
'''
RERANK = '''
_RESEARCH_BASE = agent
def agent(obs):
    return _rank_sell_slots(obs, _RESEARCH_BASE(obs), None)
'''
variants = {
    'final-rerank': RERANK,
    'horizon4': 'RESEARCH_HORIZON = 4\n' + HORIZON,
    'horizon6': 'RESEARCH_HORIZON = 6\n' + HORIZON,
    'horizon4-rerank': 'RESEARCH_HORIZON = 4\n' + HORIZON + RERANK,
    'horizon4-floor-guard': 'RESEARCH_HORIZON = 4\n_PREEMPT_MIN_PRICE_RATIO = 0.1\n' + HORIZON,
}
manifest = {'source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'variants':{}}
for name, patch in variants.items():
    path = LAB / 'experiments' / 'cycle-20260911' / name / 'main.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source + '\n# Research overlay; not an approved submission.\n' + patch, encoding='utf-8')
    manifest['variants'][name] = {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'patch':patch}
out = LAB / 'experiments/cycle-20260911/manifest.json'
out.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(out)
