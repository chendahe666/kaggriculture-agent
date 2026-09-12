"""P1e: preserve baseline trade plan, only top up imminent planned food deficit."""
def _feed_reserve(action, obs):
    step = int(obs['step'])
    needed = 0
    for t in range(step+1, min(719, step+_feed_procurement_horizon(step)+1, len(_ACTIONS))):
        plan = _ACTIONS[t] or {}
        for a in [plan.get('farmer') or ['PASS'], *(plan.get('hands') or [])]:
            if len(a) >= 2 and a[:2] == ['PICKUP','WHEAT']:
                needed += max(0, int(a[2])) if len(a) >= 3 else 1
    shed = _v5_projected_shed(obs, action)
    available = shed.get('WHEAT', 0)
    for order in action['market']:
        if _feed_is(order, 'SELL'):
            available -= min(available, max(0,int(order[2])))
        elif _feed_is(order, 'BUY_PRODUCT'):
            available += max(0,int(order[2]))
    available += _feed_safe_day_return(obs, action, needed)
    deficit = max(0, needed-available)
    # Appending preserves the exact ordering/amounts of all original orders.
    # This does not guarantee execution: cash/capacity failures are audited.
    if deficit and len(action['market']) < 10:
        action['market'].append(['BUY_PRODUCT','WHEAT',deficit])
        _FEED_DIAGNOSTICS['guard_requested'] += deficit
    elif deficit:
        _FEED_DIAGNOSTICS['no_emergency_slot'] += 1
    return action
