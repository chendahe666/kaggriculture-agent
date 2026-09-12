"""Calibrated elite strategy audit: actual flows, not order/action counts alone."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import copy
import hashlib
import json
from pathlib import Path
import statistics

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / 'results/elite-20260912'


def stock(private):
    result = Counter(private['shed'])
    for inv in private['inventories']:
        result.update(inv)
    return result


def audit(path):
    from research_cycle import engine, run_game, tape
    from analyze_online_replays import tile_counts
    payload = json.dumps(path).encode('utf-8') if isinstance(path, dict) else Path(path).read_bytes()
    replay = json.loads(payload)
    metrics = [{k: Counter() for k in ('harvest', 'feed', 'fertilizer_used', 'fertilizer_collected',
               'purchased_units', 'sold_units', 'overflow', 'processed_requests', 'state_changing_actions',
               'purchase_cost', 'sale_revenue')} for _ in range(2)]
    days = [defaultdict(lambda: {'harvest': Counter(), 'feed': 0, 'wheat_bought': 0,
                               'wheat_sold': 0, 'wheat_cost': 0, 'wheat_revenue': 0,
                               'hire_cost': 0, 'labor_requests': 0}) for _ in range(2)]
    cash = [Counter(), Counter()]
    current = {'farms': {}, 'private': {}, 'farmer_calls': 0, 'day': 0}
    names = ('_apply_unit_action', '_commit_unit', '_do_hire', '_do_buy_land', '_drop_inventories_to_shed')
    original = {name: getattr(engine, name) for name in names}

    def apply(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity=100):
        if idx == 0:
            seat = current['farmer_calls'] % 2
            if seat == 0:
                current['farms'].clear()
                current['private'].clear()
            current['farms'][id(farm)] = seat
            current['private'][id(private)] = seat
            current['farmer_calls'] += 1
        seat = current['farms'][id(farm)]
        current['day'] = day
        op = action[0] if isinstance(action, list) and action else 'INVALID'
        metrics[seat]['processed_requests'][op] += 1
        days[seat][day]['labor_requests'] += 1
        pos = engine._farmer_position(farm, idx)
        if pos is None:
            return original['_apply_unit_action'](farm, private, idx, action, board_size, day, turns_per_day, shed_capacity)
        inv = engine._farmer_inventory(private, idx)
        before_inv = Counter(inv)
        before_tile = copy.deepcopy(farm['tiles'][pos[1]][pos[0]])
        before_seeds = dict(private['seeds']) if op == 'PLANT' else None
        before_stock = stock(private) if op == 'DROP' else None
        result = original['_apply_unit_action'](farm, private, idx, action, board_size, day, turns_per_day, shed_capacity)
        after_inv = Counter(inv)
        if (list(pos) != list(engine._farmer_position(farm, idx)) or before_inv != after_inv
                or before_tile != farm['tiles'][pos[1]][pos[0]]
                or (before_seeds is not None and before_seeds != dict(private['seeds']))):
            metrics[seat]['state_changing_actions'][op] += 1
        if op == 'HARVEST':
            gained = after_inv - before_inv
            metrics[seat]['harvest'].update(gained)
            days[seat][day]['harvest'].update(gained)
        if op == 'FEED':
            used = max(0, before_inv['WHEAT'] - after_inv['WHEAT'])
            metrics[seat]['feed']['WHEAT'] += used
            days[seat][day]['feed'] += used
        if op == 'FERTILIZE':
            metrics[seat]['fertilizer_used']['FERTILIZER'] += max(0, before_inv['FERTILIZER'] - after_inv['FERTILIZER'])
        if op == 'COLLECT_FERTILIZER':
            metrics[seat]['fertilizer_collected'].update(after_inv - before_inv)
        if before_stock is not None:
            metrics[seat]['overflow'].update(before_stock - stock(private))
        return result

    def commit(op, item, price, farm, private, market, shed_capacity=100):
        seat = current['farms'][id(farm)]
        before = farm['money']
        ok = original['_commit_unit'](op, item, price, farm, private, market, shed_capacity)
        if ok and op.startswith('BUY'):
            metrics[seat]['purchased_units'][op + ':' + str(item)] += 1
            metrics[seat]['purchase_cost'][op + ':' + str(item)] += before - farm['money']
            if op == 'BUY_PRODUCT' and item == 'WHEAT':
                days[seat][current['day']]['wheat_bought'] += 1
                days[seat][current['day']]['wheat_cost'] += before - farm['money']
        if ok and op == 'SELL':
            metrics[seat]['sold_units'][item] += 1
            metrics[seat]['sale_revenue'][item] += farm['money'] - before
            if item == 'WHEAT':
                days[seat][current['day']]['wheat_sold'] += 1
                days[seat][current['day']]['wheat_revenue'] += farm['money'] - before
        return ok

    def hire(farm, private, board_size, mult=engine.FARM_HAND_COST_MULT):
        before = farm['money']
        result = original['_do_hire'](farm, private, board_size, mult)
        seat = current['farms'][id(farm)]
        cash[seat]['hire_cost'] += before - farm['money']
        days[seat][current['day']]['hire_cost'] += before - farm['money']
        return result

    def land(farm, board_size):
        before = farm['money']
        result = original['_do_buy_land'](farm, board_size)
        cash[current['farms'][id(farm)]]['land_cost'] += before - farm['money']
        return result

    def drop(private, capacity):
        before = stock(private)
        result = original['_drop_inventories_to_shed'](private, capacity)
        metrics[current['private'][id(private)]]['overflow'].update(before - stock(private))
        return result

    wrappers = (apply, commit, hire, land, drop)
    for name, wrapper in zip(names, wrappers):
        setattr(engine, name, wrapper)
    cfg = dict(replay['configuration'], seed=replay['info']['seed'])
    cfg.pop('runTimeout', None)
    try:
        calibration = run_game([tape(replay, 0), tape(replay, 1)], cfg, replay)
    finally:
        for name, function in original.items():
            setattr(engine, name, function)
    players = []
    for seat in range(2):
        m = metrics[seat]
        initial = replay['steps'][0][seat]['observation']
        final = replay['steps'][-1][seat]['observation']
        wheat_in = stock(initial['private'])['WHEAT'] + m['harvest']['WHEAT'] + m['purchased_units']['BUY_PRODUCT:WHEAT']
        wheat_out = m['feed']['WHEAT'] + m['sold_units']['WHEAT'] + m['overflow']['WHEAT'] + stock(final['private'])['WHEAT']
        cash_error = (initial['farms'][seat]['money'] + sum(m['sale_revenue'].values())
                      - sum(m['purchase_cost'].values()) - sum(cash[seat].values()) - replay['rewards'][seat])
        snapshots = {}
        for t in (167, 359, 551, 695, 719):
            if t < len(replay['steps']):
                obs = replay['steps'][t][seat]['observation']
                farm = obs['farms'][seat]
                snapshots[str(t)] = dict(tile_counts(farm), hands=len(farm['hands']), money=farm['money'],
                                         wheat_stock=stock(obs['private'])['WHEAT'], land=len(farm['unlocked_quadrants']))
        animal_days = sum(sum(1 for row in frame[seat]['observation']['farms'][seat]['tiles']
                                   for tile in row if isinstance(tile, dict) and 'animal' in tile)
                          for t, frame in enumerate(replay['steps']) if t % 24 == 23 and t < 719)
        players.append(dict(name=replay['info']['TeamNames'][seat], seat=seat, final_money=replay['rewards'][seat],
                            **m, **cash[seat], wheat_balance_error=wheat_in-wheat_out, cash_balance_error=cash_error,
                            animal_end_of_day_observations=animal_days, final_wheat=stock(final['private'])['WHEAT'],
                            snapshots=snapshots, days=days[seat]))
    valid = (calibration['state_mismatches'] == 0 and calibration['reward_match']
             and calibration['statuses'] == ['DONE', 'DONE'] and calibration['frames'] == 720
             and not calibration['errors'] and all(p['wheat_balance_error'] == 0 and p['cash_balance_error'] == 0 for p in players))
    return {'audit_version': 'elite-flow-v1', 'episode_id': replay['info']['EpisodeId'],
            'replay_sha256': hashlib.sha256(payload).hexdigest(),
            'valid': valid, 'shops': calibration['shops'], 'calibration': calibration, 'players': players}


def audit_and_save(item):
    from collect_elite_corpus import save
    result = audit(LAB / item['path'])
    result['references'] = item['references']
    save(ROOT / item.get('audit_group', 'audits') / f"{item['episode_id']}.json", result)
    return {'episode_id': item['episode_id'], 'valid': result['valid']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--own', action='store_true', help='Audit the previously frozen 20 own games as comparison, not holdout')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'corpus.json').read_text(encoding='utf-8'))
    jobs = [r for r in manifest['episodes'] if r['downloaded'] and (r['screen'] or not args.screen)
            and not (ROOT / 'audits' / f"{r['episode_id']}.json").exists()]
    if args.limit is not None:
        jobs = jobs[:args.limit]
    if args.own:
        old = json.loads((LAB/'results/public-corpus-20260911.json').read_text(encoding='utf-8'))
        jobs = [dict(episode_id=r['episode_id'], path=r['path'], references=[], audit_group='own-audits')
                for r in old['matches'] if r['source'] == 'own_recent'
                and not (ROOT/'own-audits'/f"{r['episode_id']}.json").exists()]
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(audit_and_save, r): r['episode_id'] for r in jobs}
        for future in as_completed(futures):
            print(json.dumps(future.result()), flush=True)


if __name__ == '__main__':
    main()
