"""Local-only short inventory contexts around failed FEED; not exported."""
import copy
import argparse
import json
from research_cycle import LAB, load_agent, make, tape, engine
from elite_economics import stock
from collect_elite_corpus import save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', default='jit1')
    parser.add_argument('--episode', type=int, default=107942319)
    args = parser.parse_args()
    episode = args.episode
    replay = json.loads((LAB/f'inbox/replays/episode-{episode}-replay.json').read_bytes())
    seat = replay['info']['TeamNames'].index('Mike chen666')
    path = LAB/'public-baseline-v10/main.py' if args.variant == 'baseline' else LAB/f'experiments/track-feed-20260912/{args.variant}/main.py'
    policy = load_agent(path)
    trace, failures = [], []
    def ours(obs):
        action = policy.agent(obs)
        farm, private = obs['farms'][seat], obs['private']
        positions = [farm['farmer'], *farm['hands']]
        units = [action['farmer'], *action['hands']]
        for idx, a in enumerate(units):
            if idx < len(positions) and a == ['FEED']:
                x, y = positions[idx]
                tile = farm['tiles'][y][x]
                if isinstance(tile, dict) and 'animal' in tile and not tile['fed_today'] and not private['inventories'][idx].get('WHEAT', 0):
                    failures.append({'step': obs['step'], 'actor': idx})
        trace.append({'step': obs['step'], 'shed_wheat': private['shed'].get('WHEAT', 0),
                      'shed_total': sum(private['shed'].values()), 'carried_wheat': [i.get('WHEAT', 0) for i in private['inventories']],
                      'projected_wheat': policy._v5_projected_shed(obs, action).get('WHEAT', 0),
                      'unit_ops': units, 'market': copy.deepcopy(action['market'])})
        return action
    cfg = dict(replay['configuration'], seed=replay['info']['seed'])
    cfg.pop('runTimeout', None)
    env = make('kaggriculture', configuration=cfg, debug=False)
    players = [tape(replay, 0), tape(replay, 1)]
    players[seat] = ours
    original = engine._drop_inventories_to_shed
    drops = []
    calls = 0
    def drop(private, capacity):
        nonlocal calls
        current_seat = calls % 2
        calls += 1
        before = stock(private)
        shed = dict(private['shed'])
        result = original(private, capacity)
        lost = before-stock(private)
        if current_seat == seat and lost:
            drops.append({'step': trace[-1]['step'], 'lost': dict(lost), 'shed_before': shed})
        return result
    engine._drop_inventories_to_shed = drop
    try:
        env.run(players)
    finally:
        engine._drop_inventories_to_shed = original
    contexts = [dict(f, preceding=trace[max(0, f['step']-9):f['step']+1]) for f in failures]
    save(LAB/f'inbox/diagnostics/{args.variant}-feed-failures.json', contexts)
    save(LAB/f'inbox/diagnostics/{args.variant}-endday-losses.json', drops)
    print(json.dumps({'failures': failures, 'endday_losses': drops, 'contexts_saved_local_only': True}))


if __name__ == '__main__':
    main()
