"""Research-only wheat overlay on frozen COK; no hidden/future observation input."""
_FEED_ORIGINAL_AGENT = agent
_FEED_CACHE = {0: None, 1: None}
_FEED_DIAGNOSTICS = Counter()


def _feed_is(order, op):
    return len(order) >= 3 and order[:2] == [op, 'WHEAT']


def _feed_netting(action, obs):
    orders = action['market']
    buys = sum(max(0, int(o[2])) for o in orders if _feed_is(o, 'BUY_PRODUCT'))
    sells = sum(max(0, int(o[2])) for o in orders if _feed_is(o, 'SELL'))
    shed = _v5_projected_shed(obs, action)
    # Conservative screen: no reliance on within-turn purchase financing or
    # capacity release. This is NOT proof of identical simultaneous prices.
    if (not buys or not sells or shed.get('WHEAT', 0) < sells
            or sum(shed.values()) + buys > 100
            or _farm(obs, _seat(obs))['money'] < 2000):
        return action
    n = min(buys, sells)
    for operation in ('BUY_PRODUCT', 'SELL'):
        left = n
        for order in orders:
            if _feed_is(order, operation):
                take = min(left, max(0, int(order[2])))
                order[2] -= take
                left -= take
    _FEED_DIAGNOSTICS['netted_units'] += n
    return action


def _feed_reserve(action, obs):
    step = int(obs['step'])
    required = 0
    # Planned own actions are part of the policy, not future game observations.
    for future in range(step + 1, min(719, step + FEED_HORIZON + 1, len(_ACTIONS))):
        planned = _ACTIONS[future] or {}
        for order in [planned.get('farmer') or ['PASS'], *(planned.get('hands') or [])]:
            if _feed_is(order, 'PICKUP'):
                required += max(0, int(order[2]))
    projected = _v5_projected_shed(obs, action)
    available = projected.get('WHEAT', 0)
    buy_slot = None
    # Preserve non-wheat ordering and empty wheat slots (valid zero quantities).
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


def agent(obs, config=None):
    seat, step = int(obs['player']), int(obs['step'])
    signature = _action_cache_signature(obs)
    cached = _FEED_CACHE[seat]
    if step > 0 and cached and cached[0] == signature:
        return copy.deepcopy(cached[1])
    action = _copy_action(_FEED_ORIGINAL_AGENT(obs, config))
    before = copy.deepcopy(action)
    if 72 <= step < 718:
        if FEED_MODE == 'netting':
            action = _feed_netting(action, obs)
        elif FEED_MODE == 'reserve':
            action = _feed_reserve(action, obs)
    _FEED_DIAGNOSTICS['changed_steps'] += action != before
    # The baseline observer must remember actual submitted orders.
    _meta_remember_market(obs, step, action, _META_STATE[seat])
    _FEED_CACHE[seat] = signature, copy.deepcopy(action)
    return action
