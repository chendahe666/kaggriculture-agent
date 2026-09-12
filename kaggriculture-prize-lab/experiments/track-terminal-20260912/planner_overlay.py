# Append to the frozen COK V10 source. This file is not a standalone entry point.
# Public observation only; no engine imports, opponent inventory, seeds, or RNG.
_BASE_TERMINAL_AGENT = agent

TERMINAL_DEPTH = globals().get("TERMINAL_DEPTH", 2)
TERMINAL_MODE = globals().get("TERMINAL_MODE", "planner")
TERMINAL_BEAM_WIDTH = globals().get("TERMINAL_BEAM_WIDTH", 8)
TERMINAL_ENABLE_HARVEST = globals().get("TERMINAL_ENABLE_HARVEST", True)
TERMINAL_ENABLE_FERTILIZER = globals().get("TERMINAL_ENABLE_FERTILIZER", True)
TERMINAL_ENABLE_WATER = globals().get("TERMINAL_ENABLE_WATER", True)
TERMINAL_START = 696
TERMINAL_END = 718

_TERMINAL_PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK",
    "WOOL", "FERTILIZER",
)
_TERMINAL_CROPS = {
    # first harvest age, final water-bonus age, yield cap, ongoing
    "WHEAT": (2, 4, 6, False), "CARROT": (2, 3, 4, False),
    "TOMATO": (8, 8, 4, True), "STRAWBERRY": (10, 10, 4, True),
    "MELON": (10, 12, 6, False),
}
_TERMINAL_ANIMAL_PRODUCT = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}
_TERMINAL_PRICE_PARAMS = {
    "WHEAT": (25, 400, "sqrt", .8, "log", .2),
    "CARROT": (35, 450, "hinge", 1., "sqrt", .7),
    "TOMATO": (60, 200, "hinge", .4, "sqrt", .6),
    "STRAWBERRY": (120, 100, "sqrt", .7, "linear", 1.6),
    "MELON": (250, 300, "log", .2, "sq", 3.6),
    "EGG": (50, 332, "hinge", .4, "log", .2),
    "MILK": (160, 122, "sqrt", .6, "linear", 1.6),
    "WOOL": (200, 105, "log", .2, "sq", 3.2),
    "FERTILIZER": (100, 200, "linear", .4, "linear", .4),
}
_TERMINAL_SHED = ((4, 4), (4, 5), (5, 4), (5, 5))
_TERMINAL_CACHE = {0: None, 1: None}
_TERMINAL_DIAGNOSTICS = {
    "calls": 0, "search_nodes": 0, "tasks": 0, "assigned_workers": 0,
    "harvest_actions": 0, "fertilizer_actions": 0, "water_actions": 0,
    "safe_partial_deposits": 0, "capacity_waits": 0,
}


def _terminal_compatible(obs, config):
    """This isolated experiment is calibrated only for the default rules."""
    defaults = {
        "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
        "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
        "startingMoney": 3000, "weedSpawnChance": .005,
        "townShopUnlockInterval": 3, "townShopSellInterval": 4,
        "townCenterSellInterval": 24, "farmHandCostMult": 1,
    }
    if any(_get(config, key, value) != value for key, value in defaults.items()):
        return False
    if _get(config, "marketParams", {}) not in ({}, None):
        return False
    farm = _farm(obs, _seat(obs))
    tiles = _get(farm, "tiles", [])
    if len(tiles) != 10 or any(len(row) != 10 for row in tiles):
        return False
    step = int(_get(obs, "step", 0))
    return (
        int(_get(obs, "day", step // 24)) == step // 24
        and int(_get(obs, "hour", step % 24)) == step % 24
    )


def _terminal_price(item, inventory):
    base, scale, below, below_target, above, above_target = _TERMINAL_PRICE_PARAMS[item]

    def shape(name, x):
        x = max(0., x)
        if name == "sqrt":
            return math.sqrt(x)
        if name == "log":
            return math.log1p(x)
        if name == "sq":
            return x * x
        if name == "hinge":
            u = x / scale
            return u + 8 * max(0., u - 1) ** 2
        return x

    name, target, sign = (below, below_target, 1) if inventory < 10000 else (above, above_target, -1)
    value = base + sign * target * base * shape(name, abs(inventory - 10000)) / shape(name, scale)
    return max(1, int(round(value)))


def _terminal_revenue(item, inventory, quantity):
    """Local no-opponent-sale quote; floor sales do not add market inventory."""
    total = 0
    for _ in range(max(0, int(quantity))):
        price = _terminal_price(item, inventory)
        total += price
        inventory += price > 1
    return total


def _terminal_distance(left, right):
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _terminal_shed_target(position):
    return min(_TERMINAL_SHED, key=lambda p: (_terminal_distance(position, p), p))


def _terminal_move(position, target):
    # The official engine permits walking across every in-bounds tile, including
    # locked tiles and occupied plots. No collision or obstacle map is needed.
    if position[0] != target[0]:
        return ["EAST" if position[0] < target[0] else "WEST"]
    if position[1] != target[1]:
        return ["SOUTH" if position[1] < target[1] else "NORTH"]
    return ["PASS"]


def _terminal_decay_count(tile, start, stop):
    """Decay events after actions in [start, stop), before a stop-step action."""
    expiry = int(tile.get("max_lifespan_step", -1))
    if expiry < 0:
        return 0
    first = max(start, expiry)
    first += (first - expiry) % 2
    return max(0, (stop - 1 - first) // 2 + 1)


def _terminal_task_yield(task, now, arrival):
    tile = task["tile"]
    if task["kind"] == "F":
        return 1
    quantity = max(0, int(tile.get("yield_units", 0)))
    if "crop" not in tile:
        return quantity
    lost = _terminal_decay_count(tile, now, arrival)
    # At a decay event zero yield changes the tile to WEED; WATER cannot revive it.
    if lost and quantity <= lost:
        return 0
    quantity -= lost
    if task["kind"] == "WH":
        quantity = min(task["cap"], quantity + task["water_bonus"])
        quantity -= _terminal_decay_count(tile, arrival, arrival + 1)
    return max(0, quantity)


def _terminal_tasks(obs):
    farm = _farm(obs, _seat(obs))
    now = int(_get(obs, "step", 0))
    day = now // 24
    tasks = []
    for y, row in enumerate(_get(farm, "tiles", [])):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict):
                continue
            pos = (x, y)
            if tile.get("animal") in _TERMINAL_ANIMAL_PRODUCT:
                item = _TERMINAL_ANIMAL_PRODUCT[tile["animal"]]
                if TERMINAL_ENABLE_HARVEST and int(tile.get("yield_units", 0)) > 0:
                    tasks.append({"key": ("H", x, y), "pos": pos, "kind": "H",
                                  "item": item, "cost": 1, "tile": tile})
                if TERMINAL_ENABLE_FERTILIZER and tile.get("fertilizer_available", False):
                    tasks.append({"key": ("F", x, y), "pos": pos, "kind": "F",
                                  "item": "FERTILIZER", "cost": 1, "tile": tile})
                continue
            crop = tile.get("crop")
            if tile.get("kind") != "PLANT" or crop not in _TERMINAL_CROPS:
                continue
            first, last_water, cap, ongoing = _TERMINAL_CROPS[crop]
            age = day - int(tile.get("planted_day", day))
            if age < first or not TERMINAL_ENABLE_HARVEST:
                continue
            common = {"key": ("H", x, y), "pos": pos, "item": crop, "tile": tile}
            if int(tile.get("yield_units", 0)) > 0:
                tasks.append(dict(common, kind="H", cost=1))
            if (
                TERMINAL_ENABLE_WATER and not ongoing and not tile.get("watered_today", False)
                and (last_water + 1) // 2 <= age <= last_water
                and int(tile.get("yield_units", 0)) < cap
            ):
                bonus = 2 if int(tile.get("fertilized_until_day", -1)) >= day else 1
                tasks.append(dict(common, kind="WH", cost=2, cap=cap, water_bonus=bonus))
    return tasks


def _terminal_best_plan(position, cargo, tasks, excluded, now, depth, value):
    """Bounded beam over distinct tasks, each suffix including a feasible DROP.

    Score is current-quote liquidation value per action through the return trip.
    It is a heuristic, not an exact game value or an opponent response model.
    """
    home = _terminal_shed_target(position)
    direct_duration = _terminal_distance(position, home) + 1
    cargo_value = sum(value(item, n) for item, n in cargo.items() if item in _TERMINAL_PRODUCTS)
    direct_score = cargo_value / direct_duration if now + direct_duration - 1 <= TERMINAL_END else 0.
    best = {"score": direct_score, "tasks": (), "duration": direct_duration, "keys": frozenset()}
    # state: position, actions spent before return, selected tasks, claimed keys,
    # newly acquired products. Whole product baskets are repriced at each node.
    beam = [(position, 0, (), frozenset(), {})]
    nodes = 0
    for _ in range(max(1, min(3, int(depth)))):
        expanded = []
        for at, elapsed, chosen, keys, acquired in beam:
            for task in tasks:
                if task["key"] in excluded or task["key"] in keys:
                    continue
                arrival = now + elapsed + _terminal_distance(at, task["pos"])
                quantity = _terminal_task_yield(task, now, arrival)
                if quantity <= 0:
                    continue
                spent = arrival - now + task["cost"]
                back = _terminal_distance(task["pos"], _terminal_shed_target(task["pos"]))
                duration = spent + back + 1
                if now + duration - 1 > TERMINAL_END:
                    continue
                nodes += 1
                goods = dict(acquired)
                goods[task["item"]] = goods.get(task["item"], 0) + quantity
                # Ensure a single future DROP can deliver the carried basket.
                # Existing oversized cargo is handled by partial PLACE at home.
                if sum(cargo.values()) + sum(goods.values()) > 100:
                    continue
                score = sum(value(item, cargo.get(item, 0) + goods.get(item, 0))
                            for item in _TERMINAL_PRODUCTS) / duration
                chain = chosen + (task,)
                new_keys = keys | {task["key"]}
                rank = (score, -duration, tuple((t["pos"], t["kind"]) for t in chain))
                expanded.append((rank, task["pos"], spent, chain, new_keys, goods))
                if score > best["score"] + 1e-9:
                    best = {"score": score, "tasks": chain, "duration": duration, "keys": new_keys}
        if not expanded:
            break
        expanded.sort(key=lambda node: node[0], reverse=True)
        beam = [(pos, spent, chain, keys, goods)
                for _, pos, spent, chain, keys, goods in expanded[:TERMINAL_BEAM_WIDTH]]
    best["improvement"] = best["score"] - direct_score
    best["nodes"] = nodes
    return best


def _terminal_deposits(positions, inventories, actions, shed, market_inventory):
    """Allocate shared room before actor-ordered execution; never discard cargo."""
    room = max(0, 100 - sum(shed.values()))
    waiting = [i for i, a in enumerate(actions)
               if a == ["DROP"] and tuple(positions[i]) in _TERMINAL_SHED]
    partial = waits = 0

    def item_value(item, n):
        return _terminal_revenue(item, int(market_inventory.get(item, 10000)), n)

    # Reserve capacity for the most valuable unit among each worker's cargo.
    # Actions still execute in official actor order; reserved quantities sum to room.
    waiting.sort(key=lambda i: (-max((item_value(k, 1) for k, v in inventories[i].items()
                                    if k in _TERMINAL_PRODUCTS and v > 0), default=0), i))
    for index in waiting:
        inv = inventories[index]
        goods = {k: int(v) for k, v in inv.items() if k in _TERMINAL_PRODUCTS and int(v) > 0}
        total = sum(max(0, int(v)) for v in inv.values())
        if not goods or room <= 0:
            actions[index] = ["PASS"]
            waits += bool(goods)
            continue
        if total <= room and sum(goods.values()) == total:
            deposits = goods
        else:
            choices = [(item_value(k, min(v, room)), k, min(v, room)) for k, v in goods.items()]
            _, item, quantity = max(choices)
            actions[index] = ["PLACE", item, quantity]
            deposits = {item: quantity}
            partial += 1
        room -= sum(deposits.values())
        for item, quantity in deposits.items():
            shed[item] = shed.get(item, 0) + quantity
    return partial, waits


def _terminal_plan(obs, baseline, depth=None):
    now = int(_get(obs, "step", 0))
    farm = _farm(obs, _seat(obs))
    private = _get(obs, "private", {})
    positions = [tuple(_get(farm, "farmer")), *map(tuple, _get(farm, "hands", []))]
    raw_inventories = list(_get(private, "inventories", []))
    inventories = [dict(raw_inventories[i]) if i < len(raw_inventories) else {} for i in range(len(positions))]
    shed = {k: max(0, int(v)) for k, v in dict(_get(private, "shed", {})).items()}
    market_inventory = dict(_get(_get(obs, "market", {}), "inventory", {}))
    tasks = _terminal_tasks(obs)
    depth = TERMINAL_DEPTH if depth is None else depth
    value_cache = {}

    def value(item, n):
        key = (item, n)
        if key not in value_cache:
            # Price only legal current market state. No future shops/opponent tape.
            value_cache[key] = _terminal_revenue(item, int(market_inventory.get(item, 10000)), n)
        return value_cache[key]

    excluded, assigned, remaining = set(), {}, set(range(len(positions)))
    search_nodes = 0
    while remaining:
        bids = []
        for index in sorted(remaining):
            plan = _terminal_best_plan(positions[index], inventories[index], tasks,
                                       excluded, now, depth, value)
            search_nodes += plan["nodes"]
            if plan["tasks"]:
                bids.append((plan["improvement"], plan["score"], -index, index, plan))
        if not bids:
            break
        _, _, _, index, plan = max(bids, key=lambda b: b[:3])
        assigned[index] = plan
        excluded.update(plan["keys"])
        remaining.remove(index)

    actions = []
    for index, position in enumerate(positions):
        if index in assigned:
            first = assigned[index]["tasks"][0]
            if position != first["pos"]:
                action = _terminal_move(position, first["pos"])
            else:
                action = [{"H": "HARVEST", "F": "COLLECT_FERTILIZER", "WH": "WATER"}[first["kind"]]]
        elif any(v > 0 and k in _TERMINAL_PRODUCTS for k, v in inventories[index].items()):
            target = _terminal_shed_target(position)
            action = ["DROP"] if position == target else _terminal_move(position, target)
        else:
            action = ["PASS"]
        actions.append(action)

    partial, waits = _terminal_deposits(positions, inventories, actions, shed, market_inventory)
    market = _terminal_market(shed, baseline, market_inventory)
    diagnostics = {
        "search_nodes": search_nodes, "tasks": len(tasks), "assigned_workers": len(assigned),
        "harvest_actions": sum(a == ["HARVEST"] for a in actions),
        "fertilizer_actions": sum(a == ["COLLECT_FERTILIZER"] for a in actions),
        "water_actions": sum(a == ["WATER"] for a in actions),
        "safe_partial_deposits": partial, "capacity_waits": waits,
    }
    return {"farmer": actions[0], "hands": actions[1:], "market": market}, diagnostics


def _terminal_market(shed, baseline, market_inventory):
    # Preserve the frozen route's HIRE count and turn. Reserve its market slots;
    # sale order/quantities are part of this terminal experiment's scope.
    hires = [list(order) for order in baseline.get("market", []) if order and order[0] == "HIRE"][:10]
    sales = []
    for item in _TERMINAL_PRODUCTS:
        quantity = shed.get(item, 0)
        if quantity > 0:
            start = int(market_inventory.get(item, 10000))
            revenue = _terminal_revenue(item, start, quantity)
            # Marginal sensitivity ranks scarce/premium batches ahead of stable
            # floor sales, while total revenue decides which scarce slots to keep.
            later = _terminal_revenue(item, start + quantity, quantity)
            sales.append((revenue, max(0, revenue - later), item, quantity))
    sales.sort(reverse=True)
    selected = sales[:max(0, 10 - len(hires))]
    selected.sort(key=lambda row: (row[1], row[0], row[2]), reverse=True)
    return [["SELL", item, quantity] for _, _, item, quantity in selected] + hires


def _terminal_transport(obs, baseline):
    """Transport ablation: finish every remaining frozen production task first.

    Only a worker whose entire remaining raw suffix consists of travel, PASS,
    and DROP can replace that suffix with a direct return. No baseline harvest,
    water, feed, planting, pickup, or other production operation is deleted.
    """
    now = int(_get(obs, "step", 0))
    farm = _farm(obs, _seat(obs))
    private = _get(obs, "private", {})
    positions = [tuple(_get(farm, "farmer")), *map(tuple, _get(farm, "hands", []))]
    raw_inventories = list(_get(private, "inventories", []))
    inventories = [dict(raw_inventories[i]) if i < len(raw_inventories) else {} for i in range(len(positions))]
    action = _align_hands(baseline, obs)
    actions = [action["farmer"], *action["hands"]]
    safe_suffix_ops = {"NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP"}
    active = 0
    for index, position in enumerate(positions):
        if not any(k in _TERMINAL_PRODUCTS and v > 0 for k, v in inventories[index].items()):
            continue
        actor = "farmer" if index == 0 else index - 1
        if actions[index][0] not in safe_suffix_ops or any(
            _trace_actor_action(t, actor)[0] not in safe_suffix_ops
            for t in range(now, min(TERMINAL_END + 1, len(_ACTIONS)))
        ):
            continue
        target = _terminal_shed_target(position)
        actions[index] = ["DROP"] if position == target else _terminal_move(position, target)
        active += 1
    shed = {k: max(0, int(v)) for k, v in dict(_get(private, "shed", {})).items()}
    market_inventory = dict(_get(_get(obs, "market", {}), "inventory", {}))
    partial, waits = _terminal_deposits(positions, inventories, actions, dict(shed), market_inventory)
    action["farmer"], action["hands"] = actions[0], actions[1:]
    # The ablation can retain baseline PICKUP/PLACE, so use actor-ordered
    # projection for the final sale rather than assuming deposits are the only flow.
    shed = _v5_projected_shed(obs, action)
    action["market"] = _terminal_market(shed, baseline, market_inventory)
    diagnostics = {
        "search_nodes": 0, "tasks": 0, "assigned_workers": active,
        "harvest_actions": sum(a == ["HARVEST"] for a in actions),
        "fertilizer_actions": sum(a == ["COLLECT_FERTILIZER"] for a in actions),
        "water_actions": sum(a == ["WATER"] for a in actions),
        "safe_partial_deposits": partial, "capacity_waits": waits,
    }
    return action, diagnostics


def agent(obs, config=None):
    step = int(_get(obs, "step", 0) or 0)
    if not (TERMINAL_START <= step <= TERMINAL_END) or not _terminal_compatible(obs, config):
        return _BASE_TERMINAL_AGENT(obs, config)
    seat = _seat(obs)
    signature = _action_cache_signature(obs)
    cached = _TERMINAL_CACHE[seat]
    if signature is not None and cached is not None and cached[0] == step and cached[1] == signature:
        return copy.deepcopy(cached[2])
    baseline = _BASE_TERMINAL_AGENT(obs, config)
    if TERMINAL_MODE == "transport":
        action, diagnostics = _terminal_transport(obs, baseline)
    else:
        action, diagnostics = _terminal_plan(obs, baseline)
    _TERMINAL_DIAGNOSTICS["calls"] += 1
    for key, value in diagnostics.items():
        _TERMINAL_DIAGNOSTICS[key] += value
    if signature is not None:
        _TERMINAL_CACHE[seat] = (step, signature, copy.deepcopy(action))
    return action
