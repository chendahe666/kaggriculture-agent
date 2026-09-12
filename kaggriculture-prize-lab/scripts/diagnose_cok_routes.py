"""Trace the unchanged COK selector on recorded legal own observations."""
import copy
import json
from pathlib import Path
from collect_elite_corpus import save
from research_cycle import load_agent, sha

LAB = Path(__file__).resolve().parents[1]


def main():
    corpus = json.loads((LAB/'results/public-corpus-20260911.json').read_text(encoding='utf-8'))
    result = {'source_sha256': sha(LAB/'public-baseline-v10/main.py'),
              'evidence': 'unchanged selector on original recorded observations, not counterfactual strength test', 'games': []}
    for item in corpus['matches']:
        if item['source'] != 'own_recent':
            continue
        replay = json.loads((LAB/item['path']).read_text(encoding='utf-8'))
        seat = replay['info']['TeamNames'].index('Mike chen666')
        module = load_agent(LAB/'public-baseline-v10/main.py')
        identities = {id(v): 'current:'+k for k, v in module._V7_CURRENT_ROUTES.items()}
        identities.update({id(v): 'legacy:'+k for k, v in module._V7_LEGACY_ROUTES.items()})
        identities.update({id(module._V5_LOW_ACTIONS): 'v5:low', id(module._V5_HIGH_ACTIONS): 'v5:high'})
        switches, last = [], None
        checkpoints = {}
        for t, frame in enumerate(replay['steps'][:-1]):
            obs = copy.deepcopy(frame[seat]['observation'])
            obs['step'] = t
            actions, _ = module._select_route(obs, t)
            label = identities[id(actions)]
            if label != last:
                switches.append({'step': t, 'route': label})
                last = label
            if t in (24, 72, 168, 240, 718):
                checkpoints[str(t)] = copy.deepcopy(module._ROUTE_STATE[seat])
        result['games'].append({'episode_id': item['episode_id'], 'switches': switches,
                                'checkpoints': checkpoints, 'shops': replay['steps'][-1][0]['observation']['town']['unlocked_shops']})
    save(LAB/'results/elite-20260912/cok-route-diagnosis.json', result)
    print(json.dumps([{'episode_id': r['episode_id'], 'switches': r['switches'],
                       'v5_gate': r['checkpoints']['72']['v5_gate'], 'shops': r['shops'][:3]} for r in result['games']]))


if __name__ == '__main__':
    main()
