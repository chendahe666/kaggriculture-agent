"""Validate bounded research claims and freeze evidence bytes, not causal truth.

--freeze creates one immutable evidence snapshot. Normal use is read-only.
No replay execution, strategy modification, network access or holdout opening.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
MEMORY = LAB / 'research-memory.json'
SNAPSHOT = LAB / 'results/macro-20260912-evidence.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounded_path(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError(f'Outside research root: {relative}')
    if not path.is_file():
        raise ValueError(f'Missing evidence: {relative}')
    return path


def validate(memory, root=LAB):
    errors = []
    evidence = memory['evidence']
    track_ids = {t['id'] for t in memory['tracks']}
    rules = memory['rules']
    rule_ids = {r['id'] for r in rules}
    if len(track_ids) != len(memory['tracks']) or len(rule_ids) != len(rules):
        errors.append('Duplicate rule or track ID')
    kinds = {'mechanism', 'counterexample', 'observation', 'policy'}
    for rule in rules:
        if rule['kind'] not in kinds:
            errors.append(f"Unsupported rule kind: {rule['id']}")
        for key in ('claim', 'scope', 'invalidation', 'evidence', 'tracks'):
            if not rule.get(key):
                errors.append(f"Missing {key}: {rule['id']}")
        expected_use = 'workflow_policy' if rule['kind'] == 'policy' else 'guardrail_not_strategy'
        if rule.get('prompt_use') != expected_use:
            errors.append(f"Evidence promoted beyond its scope: {rule['id']}")
        if not set(rule['evidence']) <= evidence.keys() or not set(rule['tracks']) <= track_ids:
            errors.append(f"Unknown reference: {rule['id']}")
    for hypothesis in memory['hypotheses']:
        if hypothesis['status'] != 'unvalidated' or hypothesis['direction_approval'] != 'pending':
            errors.append(f"MR-1 hypothesis status requires explicit versioned review: {hypothesis['id']}")
        if hypothesis['track'] not in track_ids or not set(hypothesis['rules']) <= rule_ids:
            errors.append(f"Unknown hypothesis reference: {hypothesis['id']}")
    for track in memory['tracks']:
        if track['strategy_uplift_validated'] is not False:
            errors.append(f"No MR-1 strategy has passed promotion: {track['id']}")
        if not set(track['depends_on']) <= track_ids:
            errors.append(f"Unknown track dependency: {track['id']}")
        bounded_path(root, track['charter'])
    edges = {t['id']: t['depends_on'] for t in memory['tracks']}

    def visit(node, active):
        if node in active:
            errors.append(f'Track dependency cycle: {node}')
            return
        for dep in edges.get(node, []):
            visit(dep, active | {node})

    for node in edges:
        visit(node, set())
    hashes = {key: digest(bounded_path(root, path)) for key, path in evidence.items()}
    for key in ('baseline', 'engine'):
        if hashes[key] != memory[f'{key}_sha256']:
            errors.append(f'Pinned {key} mismatch')
    loaded = {}
    for assertion in memory['assertions']:
        key = assertion['source']
        if key not in loaded:
            loaded[key] = json.loads(bounded_path(root, evidence[key]).read_text(encoding='utf-8'))
        actual = loaded[key]
        try:
            for part in assertion['pointer']:
                actual = actual[part]
        except (KeyError, IndexError, TypeError):
            errors.append(f'Missing metric: {key}/{assertion["pointer"]}')
            continue
        if actual != assertion['expected'] or isinstance(actual, bool) != isinstance(assertion['expected'], bool):
            errors.append(f'Metric mismatch: {key}/{assertion["pointer"]}')
    index = loaded['p1_index']
    if len(index['files']) != index['completed_simulations']:
        errors.append('P1 result count mismatch')
    for relative, expected in index['files'].items():
        if digest(bounded_path(root, relative)) != expected:
            errors.append(f'P1 result bytes changed: {relative}')
    prose = bounded_path(root, 'MACRO_RESEARCH_RULES.md').read_text(encoding='utf-8')
    for rid in rule_ids:
        if f'### {rid}：' not in prose:
            errors.append(f'Rule missing prose definition: {rid}')
    if errors:
        raise ValueError('\n'.join(errors))
    return {'evidence_sha256': hashes, 'numeric_assertions_checked': len(memory['assertions']),
            'p1_result_hashes_checked': len(index['files']), 'rules': len(rules),
            'tracks': len(track_ids), 'hypotheses': len(memory['hypotheses'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    memory = json.loads(MEMORY.read_text(encoding='utf-8'))
    checks = validate(memory)
    payload = {'version': memory['version'], 'memory_sha256': digest(MEMORY), **checks}
    if args.freeze:
        payload['created_utc'] = datetime.now(timezone.utc).isoformat()
        payload['limits'] = 'Reference/hash/metric checks only; no causal proof or new games'
        with SNAPSHOT.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    else:
        snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        if any(snapshot.get(key) != value for key, value in payload.items()):
            raise SystemExit('Evidence snapshot changed: review, version and preserve prior snapshot; do not silently refreeze.')
    print(json.dumps({'status': 'PASS', **checks}, ensure_ascii=False))


if __name__ == '__main__':
    main()
