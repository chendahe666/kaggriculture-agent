"""Two matched DEVELOPMENT diagnostics; private state is saved only under inbox.

Frozen policies are not changed. Instrumentation records executed material and
cash flows; selected task chains are reconstructed read-only after each decision.
This is an explanation of inspected development results, not new validation.
"""
import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from research_cycle import LAB, engine, load_agent, run_game


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stock(private):
    total = Counter(private['shed'])
    for inv in private['inventories']:
        total.update(inv)
    return total


def difference(after, before):
    return {k: after.get(k, 0) - before.get(k, 0)
            for k in after.keys() | before.keys() if after.get(k, 0) != before.get(k, 0)}


def snapshot(obs, seat):
    farm = obs['farms'][seat]
    return {
        'money': farm['money'], 'positions': copy.deepcopy([farm['farmer'], *farm['hands']]),
        'tiles': copy.deepcopy(farm['tiles']), 'private': copy.deepcopy(obs['private']),
        'market': copy.deepcopy(obs['market']), 'town': copy.deepcopy(obs['town']),
    }


def reconstruct_assignment(module, obs):
    """Same frozen bidding rule; no state mutation and no future replay labels."""
    if not hasattr(module, '_terminal_best_plan') or module.TERMINAL_MODE != 'planner':
        return {}
    now = obs['step']
    farm = obs['farms'][obs['player']]
    positions = [tuple(farm['farmer']), *map(tuple, farm['hands'])]
    inv = obs['private']['inventories']
    tasks = module._terminal_tasks(obs)
    market = obs['market']['inventory']
    cache = {}

    def value(item, n):
        if (item, n) not in cache:
            cache[(item, n)] = module._terminal_revenue(item, market.get(item, 10000), n)
        return cache[(item, n)]

    remaining, excluded, assigned = set(range(len(positions))), set(), {}
    while remaining:
        bids = []
        for index in sorted(remaining):
            plan = module._terminal_best_plan(positions[index], inv[index], tasks, excluded,
                                               now, module.TERMINAL_DEPTH, value)
            if plan['tasks']:
                bids.append((plan['improvement'], plan['score'], -index, index, plan))
        if not bids:
            break
        _, _, _, index, plan = max(bids, key=lambda b: b[:3])
        assigned[index] = {
            'score': plan['score'], 'improvement_over_direct_return': plan['improvement'],
            'planned_drop_step': now + plan['duration'] - 1,
            'chain': [{'position': list(t['pos']), 'kind': t['kind'], 'item': t['item']}
                      for t in plan['tasks']],
        }
        excluded.update(plan['keys'])
        remaining.remove(index)
    return assigned


def audit(expected):
    ours = load_agent(LAB / expected['candidate_path'])
    opponent = load_agent(LAB / expected['opponent_path'])
    seat = expected['seat']
    turns = {}
    active = {'step': -1, 'farmer_calls': 0, 'farms': {}}
    totals = {k: Counter() for k in (
        'harvest', 'fertilizer_collected', 'deposited', 'picked_up', 'work_loss',
        'consumed', 'purchased_products', 'sold', 'sale_revenue', 'water_bonus',
    )}
    start_stock = {}
    end_stock = {}
    start_cash = final_cash = 0
    names = ('_apply_unit_action', '_commit_unit', '_process_market')
    original = {name: getattr(engine, name) for name in names}

    def ours_observed(obs):
        nonlocal start_cash
        action = ours.agent(obs)
        step = int(obs['step'])
        active['step'] = step
        if step >= 696:
            turns[step] = {'step': step, 'before': snapshot(obs, seat),
                           'action': copy.deepcopy(action), 'units': [], 'sales': [],
                           'assignment': reconstruct_assignment(ours, obs)}
            if step == 696:
                start_stock.update(stock(obs['private']))
                start_cash = obs['farms'][seat]['money']
        return action

    def apply(farm, private, index, action, board_size, day, turns_per_day, shed_capacity=100):
        if index == 0:
            player = active['farmer_calls'] % 2
            if player == 0:
                active['farms'].clear()
            active['farms'][id(farm)] = player
            active['farmer_calls'] += 1
        player = active['farms'][id(farm)]
        step = active['step']
        if player != seat or step < 696:
            return original['_apply_unit_action'](farm, private, index, action, board_size,
                                                   day, turns_per_day, shed_capacity)
        pos = engine._farmer_position(farm, index)
        if pos is None:
            return original['_apply_unit_action'](farm, private, index, action, board_size,
                                                   day, turns_per_day, shed_capacity)
        position = list(pos)
        tile_before = copy.deepcopy(farm['tiles'][pos[1]][pos[0]])
        inv_before = Counter(engine._farmer_inventory(private, index))
        shed_before = Counter(private['shed'])
        stock_before = stock(private)
        result = original['_apply_unit_action'](farm, private, index, action, board_size,
                                                day, turns_per_day, shed_capacity)
        inv_after = Counter(engine._farmer_inventory(private, index))
        tile_after = farm['tiles'][position[1]][position[0]]
        op = action[0] if action else 'PASS'
        acquired = inv_after - inv_before if op in ('HARVEST', 'COLLECT_FERTILIZER') else Counter()
        if op == 'HARVEST':
            totals['harvest'].update(acquired)
        elif op == 'COLLECT_FERTILIZER':
            totals['fertilizer_collected'].update(acquired)
        elif op in ('FEED', 'FERTILIZE'):
            totals['consumed'].update(inv_before - inv_after)
        if op in ('DROP', 'PLACE'):
            totals['deposited'].update(Counter(private['shed']) - shed_before)
        elif op == 'PICKUP':
            totals['picked_up'].update(shed_before - Counter(private['shed']))
        lost = stock_before - stock(private) if op == 'DROP' else Counter()
        totals['work_loss'].update(lost)
        if op == 'WATER' and isinstance(tile_before, dict) and isinstance(tile_after, dict):
            bonus = max(0, tile_after.get('yield_units', 0) - tile_before.get('yield_units', 0))
            if bonus:
                totals['water_bonus'][tile_before['crop']] += bonus
        turns[step]['units'].append({
            'actor': index, 'position': position, 'action': list(action),
            'position_after': list(engine._farmer_position(farm, index)),
            'tile_before': tile_before, 'tile_after': copy.deepcopy(tile_after),
            'inventory_before': dict(inv_before), 'inventory_after': dict(inv_after),
            'acquired': dict(acquired), 'shed_delta': difference(Counter(private['shed']), shed_before),
            'lost': dict(lost),
        })
        return result

    def commit(op, item, price, farm, private, market, shed_capacity=100):
        before = farm['money']
        ok = original['_commit_unit'](op, item, price, farm, private, market, shed_capacity)
        if active['step'] >= 696 and active['farms'][id(farm)] == seat and ok:
            if op == 'SELL':
                totals['sold'][item] += 1
                totals['sale_revenue'][item] += farm['money'] - before
                turns[active['step']]['sales'].append({'item': item, 'price': price})
            elif op in ('BUY_PRODUCT', 'BUY_ANIMAL'):
                totals['purchased_products'][item] += 1
        return ok

    def market(state, environment):
        nonlocal final_cash
        step = int(state[0].observation.step)
        money_before = state[0].observation.farms[seat]['money']
        result = original['_process_market'](state, environment)
        if step >= 696:
            current = turns[step]
            current['after_market'] = snapshot(state[seat].observation, seat)
            current['market_cash_change'] = state[0].observation.farms[seat]['money'] - money_before
            current['total_spending'] = sum(s['price'] for s in current['sales']) - current['market_cash_change']
            if step == 718:
                final_cash = state[0].observation.farms[seat]['money']
                end_stock.update(stock(state[seat].observation.private))
        return result

    for name, function in zip(names, (apply, commit, market)):
        setattr(engine, name, function)
    try:
        players = [ours_observed, opponent.agent] if seat == 0 else [opponent.agent, ours_observed]
        row = run_game(players, {'seed': expected['seed'], 'episodeSteps': 720})
    finally:
        for name, function in original.items():
            setattr(engine, name, function)
    spending = sum(turn['total_spending'] for turn in turns.values())
    balance = {}
    for item in set(start_stock) | set(end_stock) | set(totals['sold']):
        residual = (start_stock.get(item, 0) + totals['harvest'][item]
                    + totals['fertilizer_collected'][item] + totals['purchased_products'][item]
                    - totals['sold'][item] - totals['consumed'][item] - totals['work_loss'][item]
                    - end_stock.get(item, 0))
        if residual:
            balance[item] = residual
    cash_residual = start_cash + sum(totals['sale_revenue'].values()) - spending - final_cash
    reproduced = (row['rewards'] == expected['rewards'] and row['actual_sales'] == expected['actual_sales']
                  and row['sale_revenue'] == expected['sale_revenue'])
    leftover = []
    for y, tile_row in enumerate(turns[718]['after_market']['tiles']):
        for x, tile in enumerate(tile_row):
            if isinstance(tile, dict) and tile.get('yield_units', 0) > 0:
                leftover.append({'position': [x, y], 'item': tile.get('crop') or tile.get('animal'),
                                 'yield_units': tile['yield_units']})
    summary = {
        'variant': expected['variant'], 'opponent': expected['opponent'], 'seed': expected['seed'],
        'seat': seat, 'development_only': True, 'reproduced_existing_result': reproduced,
        'candidate_sha256': digest(LAB / expected['candidate_path']),
        'opponent_sha256': digest(LAB / expected['opponent_path']),
        'engine_sha256': digest(engine.__file__), 'diagnostic_sha256': digest(__file__),
        'initial_stock': start_stock, 'terminal_stock': end_stock,
        'terminal_start_cash': start_cash, 'final_cash': final_cash,
        'final_window_spending': spending, 'flows': totals, 'material_balance_residual': balance,
        'cash_balance_residual': cash_residual, 'unharvested_plots': leftover,
        'note': 'Instrumented timings are not comparable with uninstrumented resource benchmarks.',
    }
    if not reproduced or balance or cash_residual:
        raise AssertionError(f'Diagnostic did not reconcile: {summary}')
    return {'summary': summary, 'turns': list(turns.values())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--opponent', required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--seat', type=int, choices=[0, 1], required=True)
    parser.add_argument('--variant', choices=['depth1', 'depth2', 'depth3', 'transport'], required=True)
    args = parser.parse_args()
    out = LAB / 'inbox/diagnostics/terminal-20260912'
    out.mkdir(parents=True, exist_ok=True)
    # Exactly two sequential games. Existing audits are reused, never overwritten.
    for variant in ('baseline', args.variant):
        key = f'{args.opponent}-{args.seed}-{args.seat}-{variant}.json'
        path = out / key
        if path.exists():
            print(json.dumps({'reused': str(path)}), flush=True)
            continue
        expected = json.loads((LAB / 'results/terminal-20260912/development' / key).read_bytes())
        started = datetime.now(timezone.utc).isoformat()
        start_time = time.perf_counter()
        result = audit(expected)
        result.update(started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
                      wall_seconds=time.perf_counter() - start_time)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result['summary'], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
