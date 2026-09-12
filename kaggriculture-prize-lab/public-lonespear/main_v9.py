"""Kaggriculture agent — v2: adds a goose operation to the v1 crop engine.

Why geese (verified against kaggriculture.py, not just the README):

  * `_daily_refresh_animals` sets `fertilizer_available = True` for every
    animal that survives the day, unconditionally (line ~809). Fertilizer's
    base price is $100 — one action for ~$100 of product.
  * Scheduled production adds `base = 1` regardless of `fed_today`; only the
    CARE bonus is gated on feeding (line ~802-805). So an animal still lays.
  * `consecutive_unfed` resets to 0 on any fed day and only kills at >= 2, so
    feeding every OTHER day keeps a goose alive forever at half the wheat.
  * Eggs sit on a log glut curve (target 0.20): ~$38 even after 1000 sold.

Net: ~1.75 actions/goose/day for an egg + a fertilizer ≈ $60/action, against
~$13/action for a wheat tile. Geese are the primary engine; wheat exists
mostly to feed them.
"""

# `maxday` is the age we intend to harvest at. `wcap` is the yield reachable by
# watering alone by that age.
#
# The watering bonus fires inside the WATER handler when
#   (max_yield_day + 1)//2 <= age <= max_yield_day
# and a plant starts at yield_units = 1. Source values for max_yield_day are
# WHEAT 4, CARROT 3, MELON 12 (the README's "time to max yield" of 10 for melon
# is the age the CAP is reached, not the end of the window).
#
#   WHEAT   window 2..4,  water at 2,3,4      -> 1+3 = 4
#   CARROT  window 2..3,  water at 2,3        -> 1+2 = 3
#   MELON   window 6..12, water at 6..10      -> 1+5 = 6  (max_yield caps at 6)
#
# Watering must therefore run through `maxday` INCLUSIVE. Excluding that final
# day cost exactly one unit per tile per cycle on every one-time crop.
CROP_INFO = {
    "WHEAT": {"seed": 10, "first": 2, "maxday": 4, "wcap": 4, "ongoing": False},
    "CARROT": {"seed": 20, "first": 2, "maxday": 3, "wcap": 3, "ongoing": False},
    "MELON": {"seed": 80, "first": 10, "maxday": 10, "wcap": 6, "ongoing": False},
    "TOMATO": {"seed": 50, "first": 8, "maxday": 11, "wcap": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first": 10, "maxday": 16, "wcap": 4, "ongoing": True},
}

STABLE_PRODUCTS = {"WHEAT", "EGG"}

BASE_PRICE = {
    "WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
    "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100,
}

DRIP_LIMIT = {"MELON": 2, "STRAWBERRY": 1, "MILK": 1, "WOOL": 1,
              "TOMATO": 3, "CARROT": 4, "FERTILIZER": 8}

LAND_COSTS = [1000, 2000, 4000]
SHED_CAP = 100
GOOSE_COST = 300

# --- Tunables (swept by tune.py) ------------------------------------------
GOOSE_FRACTION = 0.30   # share of unlocked tiles targeted for coops. Measured
                        # on one quadrant: 0.30 = 41.8k, 0.45 = 40.6k,
                        # 0.75 = 37.4k, 0.60 = 33.9k.
MIN_HANDS = 4           # floor on the daily hire target
HAND_DIVISOR = 2        # hands = workload // this. Measured: 2 = 48.0k,
                        # 4 = 46.7k, 6 = 41.8k, 8 = 41.8k. More labour is
                        # strictly better on one quadrant; at divisor 2 the
                        # MAX_HANDS cap becomes the binding control instead.
GOOSE_MAX = 34          # hard cap; fertilizer revenue peaks near 500 units
MELON_MAX = 17          # melon tiles. Measured: 0 = 24.2k, 4 = 33.2k,
                        # 12 = 41.8k, 17 = 48.7k, 24 = 48.1k. Melon is the
                        # single biggest lever, but the curve flattens past
                        # ~17 as sales start walking the price down.
LAST_GOOSE_DAY = 21     # a goose needs ~4 days to first yield + payback
CASH_BUFFER = 700       # never spend below this: hands and seeds come first
MAX_HANDS = 9           # Interacts strongly with MELON_MAX: at 12 melon tiles
                        # more hands HURT (11 -> 41.1k), but at 17 they help
                        # (6 = 49.9k, 7 = 51.5k, 8 = 52.3k, 9 = 54.0k) — more
                        # melon means more watering to cover, so tune together.
MAX_QUADRANTS = 1       # Land to own, incl. the free NW quadrant. Measured:
                        # 1 quadrant = 40.6k, 2 = 39.3k, 3 = 39.3k, 4 = 35.7k.
                        # Buying land LOSES money — we are labour-limited, not
                        # land-limited (tiles already sit idle), so extra land
                        # only adds travel between tasks.

# Task priorities — lower is more urgent.
P_RESCUE = 0    # dies tonight without action
P_HARVEST = 1
P_WATER = 2
P_PLACE = 3
P_FERT = 4
P_PLANT = 5
P_BUILD = 6
P_DIG = 7

# Share of the workforce any one priority tier may claim in a single turn.
#
# Strict priority ordering does not work here. Every morning ~24 animals each
# offer a COLLECT_FERTILIZER task; with only ~9 units, a strict ordering sent
# every unit chasing fertilizer all day, so nothing was ever planted or
# watered (v3: 86 seeds unplanted, 60 tiles idle, crops rotting into weeds).
# Capping each tier keeps a slice of the workforce on the compounding work.
TIER_CAP = {
    P_RESCUE: 1.00,   # something dies tonight otherwise — never throttle
    P_HARVEST: 0.50,
    P_WATER: 0.60,
    P_PLACE: 0.25,
    P_FERT: 0.35,
    P_PLANT: 0.45,    # planting compounds; it must not be starved
    P_BUILD: 0.20,
    P_DIG: 0.15,
}


def _unlocked_cells(tiles):
    return [(x, y) for y, row in enumerate(tiles)
            for x, t in enumerate(row) if t != "LOCKED"]


def _step_toward(ux, uy, tx, ty):
    if ux < tx:
        return "EAST"
    if ux > tx:
        return "WEST"
    if uy < ty:
        return "SOUTH"
    return "NORTH"


def _survey(tiles, day):
    """Single pass over the farm collecting everything the planner needs."""
    s = {"empty": [], "coops_empty": [], "geese": 0, "coops": 0,
         "melon": 0, "plants": 0}
    for (x, y) in _unlocked_cells(tiles):
        t = tiles[y][x]
        if t is None:
            s["empty"].append((x, y))
        elif isinstance(t, dict):
            k = t.get("kind")
            if k == "COOP":
                s["coops"] += 1
                if "animal" in t:
                    s["geese"] += 1
                else:
                    s["coops_empty"].append((x, y))
            elif k == "PLANT":
                s["plants"] += 1
                if t.get("crop") == "MELON":
                    s["melon"] += 1
    return s


def _build_tasks(obs, me, priv, surv, goose_target, coop_target):
    """[(priority, (x,y), op, required_item_or_None)]"""
    tiles = me["tiles"]
    day = obs["day"]
    days_left = 30 - day
    tasks = []

    for (x, y) in _unlocked_cells(tiles):
        t = tiles[y][x]
        if not isinstance(t, dict):
            continue
        kind = t.get("kind")

        if kind == "WEED":
            tasks.append((P_DIG, (x, y), ["DIG"], None))

        elif kind == "PLANT":
            crop = t.get("crop")
            info = CROP_INFO.get(crop, CROP_INFO["WHEAT"])
            age = day - t.get("planted_day", day)
            units = t.get("yield_units", 0)
            # Wait for the final watering to land before harvesting: at age
            # `maxday` the plant is still one unit short until it is watered
            # that day. `age > maxday` is the fallback for a plant that missed
            # a watering and will never reach the cap.
            if info["ongoing"]:
                ready = units > 0
            else:
                ready = units >= info["wcap"] or (units > 0 and age > info["maxday"])
            if ready:
                tasks.append((P_HARVEST, (x, y), ["HARVEST"], None))
            if not t.get("watered_today", False) and (
                    info["ongoing"] or age <= info["maxday"]):
                pri = P_RESCUE if t.get("consecutive_unwatered", 0) >= 1 else P_WATER
                tasks.append((pri, (x, y), ["WATER"], None))

        elif kind in ("COOP", "PASTURE"):
            if "animal" not in t:
                # An empty structure is dead space unless we fill it.
                if surv["geese"] < goose_target:
                    tasks.append((P_PLACE, (x, y), ["PLACE", "GOOSE"], "GOOSE"))
                continue
            # Feeding every other day is enough: consecutive_unfed resets on
            # any fed day and only kills at 2. Feed exactly when it hits 1.
            if t.get("consecutive_unfed", 0) >= 1 and not t.get("fed_today"):
                tasks.append((P_RESCUE, (x, y), ["FEED"], "WHEAT"))
            if t.get("fertilizer_available"):
                tasks.append((P_FERT, (x, y), ["COLLECT_FERTILIZER"], None))
            # max_held is 4; harvest in batches to save actions, but clear the
            # tile before the season ends so nothing is stranded.
            units = t.get("yield_units", 0)
            if units >= 3 or (units > 0 and days_left <= 2):
                tasks.append((P_HARVEST, (x, y), ["HARVEST"], None))

    # --- Empty tiles: coops first (better $/action), then crops.
    seeds = dict(priv.get("seeds", {}) or {})
    coops_planned = surv["coops"]
    melon_planned = surv["melon"]
    for (x, y) in surv["empty"]:
        # Build coops just-in-time. An empty coop is dead land, so never get
        # more than a couple ahead of the birds we actually own.
        if (coops_planned < coop_target and day <= LAST_GOOSE_DAY):
            tasks.append((P_BUILD, (x, y), ["BUILD_COOP"], None))
            coops_planned += 1
            continue
        if (melon_planned < MELON_MAX and seeds.get("MELON", 0) > 0
                and days_left > CROP_INFO["MELON"]["maxday"] + 1):
            crop = "MELON"
            melon_planned += 1
        elif seeds.get("WHEAT", 0) > 0 and days_left > CROP_INFO["WHEAT"]["maxday"]:
            crop = "WHEAT"
        else:
            continue
        seeds[crop] = seeds.get(crop, 0) - 1
        tasks.append((P_PLANT, (x, y), ["PLANT", crop], None))

    tasks.sort(key=lambda r: r[0])
    return tasks


def _assign(units, tasks, shed_adj, inventories, shed, needs):
    """Greedy nearest-unit assignment, honouring per-task carry requirements."""
    n = len(units)
    actions = [None] * n
    free = set(range(n))

    def inv_of(i):
        return (inventories[i] if i < len(inventories) else {}) or {}

    # --- Shed logistics. Units standing next to the shed restock the carried
    # items the field tasks need, or dump produce so it can be sold.
    for i in list(free):
        ux, uy = units[i]
        if (ux, uy) not in shed_adj:
            continue
        inv = inv_of(i)
        carried = sum(inv.values())
        if carried >= 10:
            actions[i] = ["DROP"]
            free.discard(i)
        elif needs["goose"] > 0 and shed.get("GOOSE", 0) > 0 and not inv.get("GOOSE"):
            actions[i] = ["PICKUP", "GOOSE", min(2, needs["goose"])]
            needs["goose"] -= min(2, needs["goose"])
            free.discard(i)
        elif needs["wheat"] > 0 and shed.get("WHEAT", 0) > 0 and inv.get("WHEAT", 0) < 2:
            take = min(6, shed.get("WHEAT", 0), needs["wheat"])
            actions[i] = ["PICKUP", "WHEAT", take]
            needs["wheat"] -= take
            free.discard(i)

    # Units far from the shed but loaded with produce head back to drop it.
    for i in list(free):
        if sum(inv_of(i).values()) >= 14:
            ux, uy = units[i]
            tx, ty = min(shed_adj, key=lambda c: abs(c[0] - ux) + abs(c[1] - uy))
            actions[i] = [_step_toward(ux, uy, tx, ty)]
            free.discard(i)

    used = {}
    claimed = set()
    for pri, cell, op, req in tasks:
        if not free:
            break
        if cell in claimed:
            continue
        cap = max(1, int(round(n * TIER_CAP.get(pri, 0.3))))
        if used.get(pri, 0) >= cap:
            continue
        cands = [u for u in free if req is None or inv_of(u).get(req, 0) > 0]
        if not cands:
            continue
        tx, ty = cell
        i = min(cands, key=lambda u: abs(units[u][0] - tx) + abs(units[u][1] - ty))
        ux, uy = units[i]
        actions[i] = list(op) if (ux, uy) == (tx, ty) else [_step_toward(ux, uy, tx, ty)]
        free.discard(i)
        used[pri] = used.get(pri, 0) + 1
        claimed.add(cell)

    # Any unit still idle after the caps takes the nearest unclaimed task,
    # so capping throttles competition for labour without wasting it.
    if free:
        for pri, cell, op, req in tasks:
            if not free:
                break
            if cell in claimed:
                continue
            cands = [u for u in free if req is None or inv_of(u).get(req, 0) > 0]
            if not cands:
                continue
            tx, ty = cell
            i = min(cands, key=lambda u: abs(units[u][0] - tx) + abs(units[u][1] - ty))
            ux, uy = units[i]
            actions[i] = list(op) if (ux, uy) == (tx, ty) else [_step_toward(ux, uy, tx, ty)]
            free.discard(i)
            claimed.add(cell)

    for i in free:
        actions[i] = ["PASS"]
    return actions


def _market_orders(obs, me, priv, surv, goose_target, geese_pending):
    orders = []
    day, hour = obs["day"], obs["hour"]
    money = me["money"]
    tiles = me["tiles"]
    n_unlocked = len(_unlocked_cells(tiles))
    prices = dict(obs.get("market", {}).get("prices", {}) or {})
    shed = dict(priv.get("shed", {}) or {})
    shed_total = sum(v for v in shed.values() if v > 0)

    # --- Hands first, always. Six hands cost ~$20 total (fib pricing) and each
    # adds 24 actions/day. Nothing else in the game converts cash to output
    # this efficiently, so this must never be gated behind a big balance --
    # doing so caused a death spiral: broke -> no hands -> crops die -> broke.
    # Cumulative fib cost: 10 hands = $143/day, 12 = $376, 13 = $609, 15 =
    # $1596. Twelve is the knee of the curve — past that each hand roughly
    # doubles the marginal cost for the same 24 actions.
    workload = surv["plants"] + int(surv["geese"] * 1.6) + len(surv["empty"]) // 2
    if hour <= 1:
        target = min(MAX_HANDS, max(MIN_HANDS, workload // HAND_DIVISOR))
        have = len(me.get("hands", []) or [])
        if me.get("hires_today", 0) < target and money > 40:
            for _ in range(min(target - have, 6)):
                orders.append(["HIRE"])

    # --- Land. Worth far more than it costs, but not at the price of the
    # opening bankroll: wait until the farm is actually running.
    owned = len(me.get("unlocked_quadrants", []) or [])
    if owned < MAX_QUADRANTS and 3 <= day <= 22:
        idx = owned - 1
        if 0 <= idx < len(LAND_COSTS) and money >= LAND_COSTS[idx] + 1500:
            orders.append(["BUY_LAND"])

    # --- Geese. `geese_pending` includes birds sitting in unit inventories;
    # omitting those made v2 re-buy the same goose every turn until broke.
    if day <= LAST_GOOSE_DAY:
        have = surv["geese"] + shed.get("GOOSE", 0) + geese_pending
        # Capped at coops+2, so the flock can only grow as fast as we build and
        # staff housing for it. Bought birds hit the shed the same turn, so
        # counting shed + in-transit is enough to stop runaway ordering.
        want = min(goose_target, surv["coops"] + 2) - have
        if (want > 0 and money >= GOOSE_COST + CASH_BUFFER
                and shed_total < SHED_CAP - 5):
            orders.append(["BUY_ANIMAL", "GOOSE", min(want, 2)])

    # --- Seeds.
    empties = len(surv["empty"])
    seeds = priv.get("seeds", {}) or {}
    days_left = 30 - day
    if empties > 0:
        want_melon = max(0, MELON_MAX - surv["melon"] - seeds.get("MELON", 0))
        if want_melon > 0 and days_left > 11 and money > 1500:
            orders.append(["BUY_SEED", "MELON", min(want_melon, 4)])
        want_wheat = empties - seeds.get("WHEAT", 0)
        if want_wheat > 0 and days_left > 4 and money > 200:
            orders.append(["BUY_SEED", "WHEAT", min(want_wheat, 20)])

    # --- Feed reserve. Each goose eats ~0.5 wheat/day and starving one loses a
    # $300 bird plus ~$145/day of output, so almost any wheat price is worth
    # paying. v3 capped this at $45; wheat drifted to $48 (partly from our own
    # buying) and the flock collapsed from 24 birds to 2. Keep several days of
    # buffer, not the bare daily requirement.
    need_feed = int(surv["geese"] * 1.5) + 3
    if surv["geese"] > 0 and shed.get("WHEAT", 0) < need_feed and money > 600:
        px = prices.get("WHEAT", 25)
        if px <= 140:
            short = need_feed - shed.get("WHEAT", 0)
            orders.append(["BUY_PRODUCT", "WHEAT", min(short, 12)])

    # --- Sales.
    pressure = shed_total > 0.7 * SHED_CAP
    # Hold back feed stock even under shed pressure — a sold-off reserve costs
    # the whole flock, which is worth far more than the shed slot.
    wheat_reserve = need_feed if surv["geese"] > 0 else 0
    for item, qty in sorted(shed.items(), key=lambda kv: -BASE_PRICE.get(kv[0], 0)):
        if qty <= 0 or item not in BASE_PRICE:
            continue
        if len(orders) >= 10:
            break
        if item == "WHEAT":
            # Hold back enough wheat to keep the flock alive.
            sellable = qty - wheat_reserve
            if sellable > 0:
                orders.append(["SELL", "WHEAT", sellable])
            continue
        if item in STABLE_PRODUCTS:
            orders.append(["SELL", item, qty])
            continue
        price = prices.get(item, BASE_PRICE[item])
        if pressure or day >= 29:
            orders.append(["SELL", item, qty])
        elif price >= 0.55 * BASE_PRICE[item]:
            orders.append(["SELL", item, min(qty, DRIP_LIMIT.get(item, 2))])

    return orders[:10]


def agent(obs):
    player = obs["player"]
    me = obs["farms"][player]
    priv = obs["private"]
    tiles = me["tiles"]

    half = len(tiles) // 2
    shed_adj = [(half - 1, half - 1), (half, half - 1),
                (half - 1, half), (half, half)]
    usable = [c for c in shed_adj if tiles[c[1]][c[0]] != "LOCKED"] or shed_adj

    surv = _survey(tiles, obs["day"])
    n_unlocked = len(_unlocked_cells(tiles))
    goose_target = min(GOOSE_MAX, int(n_unlocked * GOOSE_FRACTION))

    units = [tuple(me["farmer"])] + [tuple(h) for h in (me.get("hands", []) or [])]
    inventories = list(priv.get("inventories", []) or [])
    shed = dict(priv.get("shed", {}) or {})

    # Birds already bought and being carried to a coop. Counting these is what
    # stops the buy loop from ordering the same goose over and over.
    geese_pending = sum((iv or {}).get("GOOSE", 0) for iv in inventories)

    # A coop costs one action on a tile that is otherwise sitting idle, so once
    # there is spare land it is worth running ahead of the flock — v4 tied the
    # coop count to current birds and the flock stalled at 16 for 15 days.
    # Only ration coops when land is genuinely scarce.
    owned = surv["geese"] + shed.get("GOOSE", 0) + geese_pending
    if len(surv["empty"]) > 12:
        coop_target = goose_target
    else:
        coop_target = min(goose_target, owned + 2)

    tasks = _build_tasks(obs, me, priv, surv, goose_target, coop_target)
    needs = {
        "wheat": sum(1 for t in tasks if t[3] == "WHEAT"),
        "goose": sum(1 for t in tasks if t[3] == "GOOSE"),
    }
    acts = _assign(units, tasks, usable, inventories, shed, needs)
    market = _market_orders(obs, me, priv, surv, goose_target, geese_pending)

    return {"farmer": acts[0], "hands": acts[1:], "market": market}
