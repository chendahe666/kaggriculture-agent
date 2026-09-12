"""P1d: use only otherwise-idle end-of-day labor to deliver premium cargo."""
_DELIVERY_ORIGINAL = agent
_DELIVERY_CACHE = {0: None, 1: None}
_FEED_DIAGNOSTICS = Counter()
_DELIVERY_PRODUCTS = ('MILK', 'WOOL', 'STRAWBERRY', 'MELON')


def _delivery_is_idle(index, step):
    end = min(719, (step // 24 + 1) * 24, len(_ACTIONS))
    for t in range(step, end):
        p = _ACTIONS[t] or {}
        a = p.get('farmer') or ['PASS'] if index == 0 else (p.get('hands') or [])[index-1:index]
        if index != 0:
            a = a[0] if a else ['PASS']
        if a != ['PASS']:
            return False
    return True


def _delivery_apply(obs, action):
    step = int(obs['step'])
    if step % 24 < 12 or step >= 718:
        return action
    private = obs['private']
    total = sum(private['shed'].values()) + sum(sum(i.values()) for i in private['inventories'])
    if total < 80:
        return action
    farm = obs['farms'][int(obs['player'])]
    positions = [farm['farmer'], *farm['hands']]
    units = [action['farmer'], *action['hands']]
    board = len(farm['tiles'])
    half = board // 2
    access = [(half-1,half-1), (half,half-1), (half-1,half), (half,half)]
    for i, pos in enumerate(positions):
        if i >= len(units) or units[i] != ['PASS'] or not _delivery_is_idle(i, step):
            continue
        inv = private['inventories'][i]
        items = [item for item in _DELIVERY_PRODUCTS if inv.get(item, 0) > 0]
        if not items:
            continue
        item = max(items, key=lambda x: (obs['market']['prices'][x]*inv[x], x))
        target = min(access, key=lambda p: (abs(p[0]-pos[0])+abs(p[1]-pos[1]), p))
        distance = abs(target[0]-pos[0])+abs(target[1]-pos[1])
        if distance+1 > 24-step % 24:
            continue
        if distance:
            op = 'EAST' if pos[0] < target[0] else 'WEST' if pos[0] > target[0] else 'SOUTH' if pos[1] < target[1] else 'NORTH'
            units[i] = [op]
            _FEED_DIAGNOSTICS['idle_moves'] += 1
        else:
            before = _v5_projected_shed(obs, action)
            quantity = min(inv[item], max(0, 100-sum(before.values())))
            if quantity <= 0:
                continue
            existing = next((o for o in action['market'] if len(o) >= 3 and o[:2] == ['SELL',item]), None)
            if existing is None and len(action['market']) >= 10:
                continue
            units[i] = ['PLACE', item, quantity]
            action['farmer'], action['hands'] = units[0], units[1:]
            after = _v5_projected_shed(obs, action)
            added = max(0, after.get(item, 0)-before.get(item, 0))
            requested = sum(max(0,int(o[2])) for o in action['market'] if len(o) >= 3 and o[:2] == ['SELL',item])
            extra = min(added, max(0, after.get(item, 0)-requested))
            if extra and existing is not None:
                existing[2] += extra
            elif extra:
                action['market'].append(['SELL',item,extra])
            _FEED_DIAGNOSTICS['premium_delivered'] += added
        action['farmer'], action['hands'] = units[0], units[1:]
    return action


def agent(obs, config=None):
    seat, step = int(obs['player']), int(obs['step'])
    signature = _action_cache_signature(obs)
    cached = _DELIVERY_CACHE[seat]
    if step > 0 and cached and cached[0] == signature:
        return copy.deepcopy(cached[1])
    action = _copy_action(_DELIVERY_ORIGINAL(obs, config))
    before = copy.deepcopy(action)
    action = _delivery_apply(obs, action)
    _FEED_DIAGNOSTICS['changed_steps'] += action != before
    _meta_remember_market(obs, step, action, _META_STATE[seat])
    _DELIVERY_CACHE[seat] = signature, copy.deepcopy(action)
    return action
