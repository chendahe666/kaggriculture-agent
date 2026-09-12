"""P1c: explicit purchasing opportunities and conservative day-end wheat return."""
def _feed_procurement_horizon(step):
    horizon = 1
    if FEED_BUSY:
        # Need food before the next PICKUP, not after that turn's unit work.
        while horizon < 6 and step + horizon < 718:
            orders = (_ACTIONS[step + horizon] or {}).get('market') or []
            if len(orders) < 10 or any(_feed_is(o, 'BUY_PRODUCT') for o in orders):
                break
            horizon += 1
    return horizon


def _feed_safe_day_return(obs, action, required):
    if not FEED_DAY_RETURN or int(obs['step']) % 24 != 23:
        return 0
    # On these actions neither cargo nor shed changes. Any other action falls
    # back to no credit, rather than assuming that a harvest or drop succeeds.
    static_cargo_ops = {'PASS', 'NORTH', 'SOUTH', 'EAST', 'WEST', 'WATER', 'CARE', 'DIG', 'BUILD_COOP', 'BUILD_PASTURE', 'PLANT'}
    if any(not a or a[0] not in static_cargo_ops for a in [action['farmer'], *action['hands']]):
        return 0
    private = obs['private']
    incoming = sum(i.get('WHEAT', 0) for i in private['inventories'])
    all_stock = sum(private['shed'].values()) + sum(sum(i.values()) for i in private['inventories'])
    non_wheat_buys = sum(max(0, int(o[2])) for o in action['market']
                        if len(o) >= 3 and o[0] in ('BUY_PRODUCT', 'BUY_ANIMAL') and o[1] != 'WHEAT')
    # Do not credit cargo if any item could fill the shed ahead of it. Future
    # sales are ignored in this bound, deliberately conservative.
    if all_stock + non_wheat_buys + required > 100:
        return 0
    return incoming


def _feed_reserve(action, obs):
    step = int(obs['step'])
    required = 0
    for future in range(step + 1, min(719, step + _feed_procurement_horizon(step) + 1, len(_ACTIONS))):
        plan = _ACTIONS[future] or {}
        for order in [plan.get('farmer') or ['PASS'], *(plan.get('hands') or [])]:
            if len(order) >= 2 and order[:2] == ['PICKUP', 'WHEAT']:
                required += max(0, int(order[2])) if len(order) >= 3 else 1
    required = max(0, required - _feed_safe_day_return(obs, action, required))
    available = _v5_projected_shed(obs, action).get('WHEAT', 0)
    buy_slot = None
    for i, order in enumerate(action['market']):
        if _feed_is(order, 'SELL'):
            order[2] = min(max(0, int(order[2])), max(0, available - required))
            available -= order[2]
        elif _feed_is(order, 'BUY_PRODUCT'):
            if buy_slot is None:
                buy_slot = i
            order[2] = 0
    deficit = max(0, required - available)
    if buy_slot is not None:
        action['market'][buy_slot][2] = deficit
    elif deficit and len(action['market']) < 10:
        action['market'].append(['BUY_PRODUCT', 'WHEAT', deficit])
    elif deficit:
        _FEED_DIAGNOSTICS['no_emergency_slot'] += 1
    return action
