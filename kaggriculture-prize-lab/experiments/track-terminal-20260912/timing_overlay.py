# P2b: append to a frozen P2 candidate, then use the unique final entry point.
_P2B_PLANNER_AGENT = agent
TERMINAL_TIMING_ONLY = globals().get("TERMINAL_TIMING_ONLY", False)
_P2B_UNBUYABLE = {"CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"}
_P2B_HISTORY = {0: None, 1: None}
_P2B_DIAGNOSTICS = {
    "calls": 0, "eligible_items": 0, "held_units": 0, "capacity_released_units": 0,
    "finance_released_units": 0, "unreliable_history_calls": 0,
    "purchase_guard_calls": 0, "order_capacity_fallbacks": 0,
    "unresolved_inventory_upper_bound": 0,
}


def _p2b_public_products(obs):
    """A complete public board history is needed to rule out existing cargo."""
    required = ("step", "player", "farms", "private", "market", "town", "day", "hour")
    if any(_get(obs, name, None) is None for name in required):
        return None
    farms = _get(obs, "farms", None)
    if not isinstance(farms, (list, tuple)) or len(farms) != 2:
        return None
    tiles = _get(farms[1 - _seat(obs)], "tiles", None)
    if not isinstance(tiles, (list, tuple)) or len(tiles) != 10:
        return None
    found = set()
    for row in tiles:
        if not isinstance(row, (list, tuple)) or len(row) != 10:
            return None
        for tile in row:
            if tile is None or tile == "LOCKED":
                continue
            if not isinstance(tile, dict) or tile.get("kind") not in {"PLANT", "PASTURE", "COOP", "WEED"}:
                return None
            if tile.get("kind") == "PLANT":
                if tile.get("crop") not in _TERMINAL_CROPS:
                    return None
                found.add(tile["crop"])
            if "animal" in tile:
                if tile["animal"] not in _TERMINAL_ANIMAL_PRODUCT:
                    return None
                found.add(_TERMINAL_ANIMAL_PRODUCT[tile["animal"]])
    return found


def _p2b_observe(obs, config=None):
    seat = _seat(obs)
    raw = _get(obs, "step", None)
    step = int(raw) if isinstance(raw, int) and not isinstance(raw, bool) else -1
    signature = _action_cache_signature(obs)
    state = _P2B_HISTORY[seat]
    if step == 0 or state is None:
        state = {"last_step": -1, "signature": None, "reliable": step == 0,
                 "ever_products": set(), "action": None}
        _P2B_HISTORY[seat] = state
    products = _p2b_public_products(obs)
    complete = products is not None and step >= 0 and _terminal_compatible(obs, config)
    if step != state["last_step"] + 1 or not complete:
        state["reliable"] = False
    if products is not None:
        state["ever_products"].update(products)
    state["last_step"], state["signature"] = step, signature
    return state


def _p2b_remaining_demand(obs, item, step):
    # Consumption after the last sale at 718 cannot benefit a held unit.
    shops = _get(_get(obs, "town", {}), "unlocked_shops", []) or []
    return sum(_meta_town_demand(t, shops, item) for t in range(step, TERMINAL_END))


def _p2b_inventory_upper_bound(obs):
    """Upper bound on all goods that could reach storage during the final day.

    Count pre-work shed + carried exactly once, plus visible mature production.
    H and WH are alternatives, not additive. A two-unit water bonus is a safe
    upper bound even when no fertilizer is currently being applied. Ignoring
    travel and decay deliberately makes this conservative.
    """
    farm = _farm(obs, _seat(obs))
    private = _get(obs, "private", {})
    total = sum(max(0, int(v)) for v in _get(private, "shed", {}).values())
    total += sum(max(0, int(v)) for inv in _get(private, "inventories", []) for v in inv.values())
    day = int(_get(obs, "step", 0)) // 24
    for row in _get(farm, "tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            quantity = max(0, int(tile.get("yield_units", 0)))
            if tile.get("animal") in _TERMINAL_ANIMAL_PRODUCT:
                total += quantity + int(bool(tile.get("fertilizer_available", False)))
                continue
            crop = tile.get("crop")
            if tile.get("kind") != "PLANT" or crop not in _TERMINAL_CROPS:
                continue
            first, last_water, cap, ongoing = _TERMINAL_CROPS[crop]
            age = day - int(tile.get("planted_day", day))
            if age < first:
                continue
            if not ongoing and not tile.get("watered_today", False) and (last_water + 1) // 2 <= age <= last_water:
                quantity = min(cap, quantity + 2)
            total += quantity
    return total


def _p2b_scheduled_orders(action, step):
    orders = [list(o) for o in action.get("market", []) if o]
    for future in range(step + 1, min(TERMINAL_END + 1, len(_ACTIONS))):
        orders.extend(list(o) for o in (_ACTIONS[future] or {}).get("market", []) if o)
    return orders


def _p2b_hiring_reserve(obs, scheduled):
    hires = sum(o[0] == "HIRE" for o in scheduled)
    hired = max(0, int(_get(_farm(obs, _seat(obs)), "hires_today", 0)))
    a, b = 1, 1
    reserve = 0
    for index in range(hired + hires):
        if index >= hired:
            reserve += a
        a, b = b, a + b
    return reserve


def _p2b_effective_sales(orders, projected):
    sold = Counter()
    for order in orders:
        if len(order) >= 3 and order[0] == "SELL" and order[1] in _TERMINAL_PRODUCTS:
            item = order[1]
            quantity = min(max(0, int(order[2])), max(0, projected.get(item, 0) - sold[item]))
            sold[item] += quantity
    return sold


def _p2b_set_sales(orders, quantities):
    """Rewrite only requested products, preserving all other order contents."""
    orders = [list(order) for order in orders]
    first = {}
    for index, order in enumerate(orders):
        if len(order) >= 3 and order[0] == "SELL" and order[1] in quantities:
            first.setdefault(order[1], index)
            order[2] = 0
    # Fill every existing item's retained quantity before reusing zero slots.
    # Otherwise a later item could overwrite an earlier new item through the
    # old first-index map, changing both product identity and quantity.
    for item, quantity in quantities.items():
        if item in first:
            orders[first[item]][2] = quantity
    for item, quantity in quantities.items():
        if item not in first and quantity > 0:
            if len(orders) >= 10:
                # A zeroed eligible sell is an available slot; fixed orders stay.
                slot = next((i for i, o in enumerate(orders)
                             if len(o) >= 3 and o[0] == "SELL" and o[1] in quantities and o[2] == 0), None)
                if slot is None:
                    return None
                orders[slot] = ["SELL", item, quantity]
            else:
                orders.append(["SELL", item, quantity])
    return orders


def _p2b_apply(obs, action, state):
    step = int(_get(obs, "step", 0))
    result = _copy_action(action)
    orders = result["market"]
    projected = _v5_projected_shed(obs, result)
    info = {key: 0 for key in _P2B_DIAGNOSTICS if key != "calls"}
    if step == TERMINAL_END:
        # The standard A/B sources have at most nine sale products and no final
        # purchase orders. Keep any fixed orders rather than silently deleting them.
        sold = _p2b_effective_sales(orders, projected)
        quantities = {item: max(sold[item], projected.get(item, 0)) for item in _TERMINAL_PRODUCTS}
        final = _p2b_set_sales(orders, quantities)
        if final is not None:
            result["market"] = final
        else:
            info["order_capacity_fallbacks"] = 1
        return result, info
    if not state["reliable"]:
        info["unreliable_history_calls"] = 1
        return result, info
    scheduled = _p2b_scheduled_orders(result, step)
    if any(o[0] not in {"SELL", "HIRE"} for o in scheduled):
        # Preserve a remaining procurement program and its original financing.
        info["purchase_guard_calls"] = 1
        return result, info
    eligible = {item for item in _P2B_UNBUYABLE
                if item not in state["ever_products"] and _p2b_remaining_demand(obs, item, step) > 0}
    info["eligible_items"] = len(eligible)
    if not eligible:
        return result, info
    fixed = [o for o in orders if not (len(o) >= 3 and o[0] == "SELL" and o[1] in eligible)]
    fixed_sold = _p2b_effective_sales(fixed, projected)
    release = {item: 0 for item in sorted(eligible)}
    market = _get(_get(obs, "market", {}), "inventory", {})
    available = {item: max(0, projected.get(item, 0)) for item in eligible}
    upper = _p2b_inventory_upper_bound(obs)
    required_units = max(0, upper - 100 - sum(fixed_sold.values()))
    reserve = _p2b_hiring_reserve(obs, scheduled)
    money = float(_get(_farm(obs, _seat(obs)), "money", 0))
    # Ungated commodities can face opponent sales: credit only the price floor.
    guaranteed_fixed_income = sum(fixed_sold.values())
    financial_shortfall = max(0., reserve - money - guaranteed_fixed_income)

    def credit():
        return sum(_terminal_revenue(item, int(market.get(item, 10000)), n) for item, n in release.items())

    # Release high-value units first to secure the known HIRE program with as
    # few units as possible. No opponent can trade these gated commodities.
    while credit() < financial_shortfall:
        choices = [( _terminal_price(item, int(market.get(item, 10000)) + release[item]), item)
                   for item in eligible if release[item] < available[item]]
        if not choices:
            break
        _, item = max(choices)
        release[item] += 1
        info["finance_released_units"] += 1
    while sum(release.values()) < required_units:
        choices = [(_terminal_price(item, int(market.get(item, 10000)) + release[item]), item)
                   for item in eligible if release[item] < available[item]]
        if not choices:
            break
        _, item = max(choices)
        release[item] += 1
        info["capacity_released_units"] += 1
    if credit() < financial_shortfall or sum(release.values()) < required_units:
        # If current storage cannot reduce the conservative global bound, no
        # new hold is allowed. The original action remains the feasible fallback.
        info["unresolved_inventory_upper_bound"] = max(0, required_units - sum(release.values()))
        return result, info
    rewritten = _p2b_set_sales(orders, release)
    if rewritten is None:
        info["order_capacity_fallbacks"] = 1
        return result, info
    if financial_shortfall > 0:
        # Financing sales must precede HIRE, including when the old source did
        # not contain this particular sale. Fixed orders keep their relative order.
        funding = [o for o in rewritten if len(o) >= 3 and o[0] == "SELL" and o[1] in eligible and o[2] > 0]
        rewritten = funding + [o for o in rewritten if not (len(o) >= 3 and o[0] == "SELL" and o[1] in eligible and o[2] > 0)]
    result["market"] = rewritten
    info["held_units"] = sum(available[item] - release[item] for item in eligible)
    return result, info


def agent(obs, config=None):
    seat = _seat(obs)
    step = _get(obs, "step", -1)
    signature = _action_cache_signature(obs)
    previous = _P2B_HISTORY[seat]
    if (previous is not None and previous["last_step"] == step and signature is not None
            and previous["signature"] == signature and previous["action"] is not None):
        return copy.deepcopy(previous["action"])
    state = _p2b_observe(obs, config)
    source = _BASE_TERMINAL_AGENT if TERMINAL_TIMING_ONLY else _P2B_PLANNER_AGENT
    action = source(obs, config)
    if (isinstance(step, int) and TERMINAL_START <= step <= TERMINAL_END
            and _terminal_compatible(obs, config)):
        action, info = _p2b_apply(obs, action, state)
        _P2B_DIAGNOSTICS["calls"] += 1
        for key, value in info.items():
            _P2B_DIAGNOSTICS[key] += value
    state["action"] = copy.deepcopy(action)
    return action


def _p2b_submission_entrypoint(obs, config=None):
    """A genuinely new last callable key for Kaggle's file loader."""
    return agent(obs, config)
