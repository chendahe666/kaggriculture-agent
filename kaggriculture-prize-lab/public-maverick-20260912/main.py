"""
Kaggriculture agent — "Melon Rush, Wheat Backbone".

Reasoning behind the strategy (all of it derived from the environment source,
see the accompanying notebook):

  * ACTIONS are the binding constraint, not land and not cash. So the ranking
    that matters is revenue per unit-action, and melon wins it by ~5x.
  * But melon's glut curve is quadratic: the first 100 melons earn $21.7k, and
    by 130 the price is at the $1 floor. So melon acreage is capped and sales
    are metered against a price floor.
  * WHEAT and EGG are the only goods with a logarithmic glut curve — they
    never crash. Wheat is therefore the unbounded backbone.
  * Every plant spawns with consecutive_unwatered = 1, so an unwatered plant
    dies on the day it is planted. Plant and water must be paired.
  * Hired hands cost fib(n) — but the 15th hand costs 610/day, so labour is
    cheap, not free. Hiring past ~14 measurably loses money.
"""
from collections import deque

# Tuned by grid search over 4 seeds vs the built-in `starter` agent.
P = dict(
    MELON_TILES=36,    # melon has the best value-per-action, but the market
                       # only absorbs ~250 units a season, so cap the acreage
    WHEAT_TILES=60,    # wheat never crashes -> unbounded revenue stream
    GOOSE_MAX=0,       # animals lose money here: see notebook section 6
    RESERVE=100,       # hard cash floor; going broke stalls hiring entirely
    HIRE_MAX=15, HIRE_K=0.125,
    MELON_FLOOR=0.5, LAND_BUF=2000, COOP_LEAD=3,
)

CROPS = {
    "WHEAT":  {"seed": 10, "first": 2, "maxday": 4, "maxy": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first": 2, "maxday": 3, "maxy": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first": 8, "maxday": 8, "maxy": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first": 10, "maxday": 10, "maxy": 4, "ongoing": True},
    "MELON":  {"seed": 80, "first": 10, "maxday": 12, "maxy": 6, "ongoing": False},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
I0 = 10000
MP = {
    "WHEAT": (25, 400, "sqrt", .80, "log", .20), "CARROT": (35, 450, "log", .20, "sqrt", .70),
    "TOMATO": (60, 200, "linear", .40, "sqrt", .60), "STRAWBERRY": (120, 100, "sqrt", .70, "linear", 1.6),
    "MELON": (250, 300, "log", .20, "sq", 3.6), "EGG": (50, 332, "linear", .40, "log", .20),
    "MILK": (160, 122, "sqrt", .60, "linear", 1.6), "WOOL": (200, 105, "log", .20, "sq", 3.2),
    "FERTILIZER": (100, 200, "linear", .40, "linear", .40),
}
LAND = [1000, 2000, 4000]
DIRS = (("NORTH", 0, -1), ("SOUTH", 0, 1), ("EAST", 1, 0), ("WEST", -1, 0))
_S = {"day": -1, "jobs": {}}


def _f(fn, x):
    import math
    x = max(0.0, x)
    return {"linear": x, "sq": x * x, "sqrt": math.sqrt(x), "log": math.log(1 + x)}.get(fn, x)


def price_of(it, inv):
    b, T, bf, bt, af, at = MP[it]
    p = b + (bt * b / _f(bf, T)) * _f(bf, I0 - inv) if inv < I0 else b - (at * b / _f(af, T)) * _f(af, inv - I0)
    return max(1, int(round(p)))


def bfs(tiles, tx, ty, N):
    d = [[-1] * N for _ in range(N)]
    d[ty][tx] = 0
    dq = deque([(tx, ty)])
    while dq:
        x, y = dq.popleft()
        nd = d[y][x] + 1
        for _, dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < N and 0 <= ny < N and d[ny][nx] < 0 and tiles[ny][nx] != "LOCKED":
                d[ny][nx] = nd
                dq.append((nx, ny))
    return d


def agent(obs, config=None):
    day, hour, me = obs.get("day", 0), obs.get("hour", 0), obs.get("player", 0)
    farms = obs.get("farms", [])
    if not farms or me >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    farm = farms[me]
    priv = obs.get("private", {}) or {}
    shed = dict(priv.get("shed", {}) or {})
    seeds = dict(priv.get("seeds", {}) or {})
    invs = [dict(i or {}) for i in (priv.get("inventories") or [{}])]
    tiles, N = farm["tiles"], len(farm["tiles"])
    money = farm["money"]
    mkt = dict((obs.get("market", {}) or {}).get("inventory", {}) or {})
    hands = farm.get("hands", [])
    nu = 1 + len(hands)
    pos = [tuple(farm["farmer"])] + [tuple(p) for p in hands]
    while len(invs) < nu:
        invs.append({})
    half, last_hour, days_left = N // 2, 23, 29 - day
    sheds = [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]
    shedset = set(sheds)
    if _S["day"] != day:
        _S["day"], _S["jobs"] = day, {}
    jobs = _S["jobs"]

    cnt, empties, unlocked = {}, [], 0
    for y in range(N):
        for x in range(N):
            t = tiles[y][x]
            if t == "LOCKED":
                continue
            unlocked += 1
            if t is None:
                empties.append((x, y))
            elif t.get("kind") == "PLANT":
                cnt[t["crop"]] = cnt.get(t["crop"], 0) + 1
            elif "animal" in t:
                cnt["GOOSE"] = cnt.get("GOOSE", 0) + 1
            elif t.get("kind") == "COOP":
                cnt["COOP"] = cnt.get("COOP", 0) + 1
    n_geese, n_coop = cnt.get("GOOSE", 0), cnt.get("COOP", 0)
    feed_reserve = (n_geese * 2 + 4) if n_geese else 0

    melon_ok = days_left >= 11 and price_of("MELON", mkt.get("MELON", I0)) >= 160
    melon_target = P["MELON_TILES"] if melon_ok else 0
    coop_target = 0
    if days_left >= 9 and P["GOOSE_MAX"] > 0:
        coop_target = min(P["GOOSE_MAX"], n_geese + P["COOP_LEAD"])
    wheat_target = P["WHEAT_TILES"] if days_left >= 5 else 0

    def next_role():
        if cnt.get("MELON", 0) < melon_target and seeds.get("MELON", 0) > 0:
            return ("PLANT", "MELON")
        if n_coop + n_geese < coop_target:
            return ("BUILD_COOP",)
        if cnt.get("WHEAT", 0) < wheat_target and seeds.get("WHEAT", 0) > 0:
            return ("PLANT", "WHEAT")
        if days_left >= 4 and seeds.get("CARROT", 0) > 0:
            return ("PLANT", "CARROT")
        if days_left >= 5 and seeds.get("WHEAT", 0) > 0:
            return ("PLANT", "WHEAT")
        return None

    tasks, wheat_need = [], 0
    for y in range(N):
        for x in range(N):
            t = tiles[y][x]
            if t == "LOCKED" or t is None:
                continue
            k = t.get("kind")
            if k == "WEED":
                tasks.append((52, x, y, ["DIG"], None))
            elif k == "PLANT":
                cd = CROPS[t["crop"]]
                age, yu = day - t["planted_day"], t.get("yield_units", 0)
                cu, wt = t.get("consecutive_unwatered", 0), t.get("watered_today", False)
                prem = t["crop"] == "MELON"
                if not cd["ongoing"]:
                    if age >= cd["first"] and (age >= cd["maxday"] or yu >= cd["maxy"]):
                        tasks.append((96, x, y, ["HARVEST"], None))
                        continue
                elif age >= cd["first"] and yu > 0:
                    tasks.append((72, x, y, ["HARVEST"], None))
                if not wt:
                    win = (not cd["ongoing"]) and ((cd["maxday"] + 1) // 2) <= age <= cd["maxday"] and yu < cd["maxy"]
                    if cu >= 1:
                        tasks.append((99 if (win or prem) else 92, x, y, ["WATER"], None))
                    elif win or cd["ongoing"]:
                        tasks.append((70 if prem else 65, x, y, ["WATER"], None))
            elif "animal" in t:
                if not t.get("fed_today"):
                    tasks.append((97 if t.get("consecutive_unfed", 0) >= 1 else 84, x, y, ["FEED"], "WHEAT"))
                    wheat_need += 1
                if t.get("yield_units", 0) > 0:
                    tasks.append((78, x, y, ["HARVEST"], None))
                if not t.get("cared_today"):
                    tasks.append((56, x, y, ["CARE"], None))
                if t.get("fertilizer_available"):
                    tasks.append((60, x, y, ["COLLECT_FERTILIZER"], None))
            elif k == "COOP" and shed.get("GOOSE", 0) + sum(i.get("GOOSE", 0) for i in invs) > 0:
                tasks.append((88, x, y, ["PLACE", "GOOSE"], "GOOSE"))

    if hour < last_hour:
        empties.sort(key=lambda p: abs(p[0] - half) + abs(p[1] - half))
        budget = {}
        for j in jobs.values():
            if j["op"][0] == "PLANT":
                budget[j["op"][1]] = budget.get(j["op"][1], 0) + 1
        for (x, y) in empties:
            r = next_role()
            if r is None:
                break
            if r[0] == "BUILD_COOP":
                n_coop += 1
                tasks.append((45, x, y, ["BUILD_COOP"], None))
            else:
                c = r[1]
                if budget.get(c, 0) >= seeds.get(c, 0):
                    continue
                budget[c] = budget.get(c, 0) + 1
                cnt[c] = cnt.get(c, 0) + 1
                tasks.append((50 if c == "MELON" else 46, x, y, ["PLANT", c], None))

    def valid(j):
        x, y, op = j["x"], j["y"], j["op"]
        t, o = tiles[y][x], j["op"][0]
        if o == "PICKUP":
            return shed.get(op[1], 0) > 0
        if t == "LOCKED":
            return False
        if o == "PLANT":
            return t is None and seeds.get(op[1], 0) > 0
        if o == "BUILD_COOP":
            return t is None
        if not isinstance(t, dict):
            return False
        return {"DIG": t.get("kind") == "WEED",
                "WATER": t.get("kind") == "PLANT" and not t.get("watered_today"),
                "HARVEST": t.get("yield_units", 0) > 0,
                "FEED": "animal" in t and not t.get("fed_today"),
                "CARE": "animal" in t and not t.get("cared_today"),
                "COLLECT_FERTILIZER": "animal" in t and t.get("fertilizer_available"),
                "PLACE": t.get("kind") == "COOP" and "animal" not in t}.get(o, False)

    claimed = set()
    for u in list(jobs):
        if u >= nu or not valid(jobs[u]):
            jobs.pop(u, None)
        else:
            claimed.add((jobs[u]["x"], jobs[u]["y"], jobs[u]["op"][0]))

    order = []
    for y in range(N):
        for x in (range(N) if y % 2 == 0 else range(N - 1, -1, -1)):
            if tiles[y][x] != "LOCKED":
                order.append((x, y))
    chunk = max(1, (len(order) + nu - 1) // nu)
    zone = {xy: min(i // chunk, nu - 1) for i, xy in enumerate(order)}

    free = [u for u in range(nu) if u not in jobs]
    for lo, hi in ((90, 1000), (55, 90), (0, 55)):
        band = [t for t in tasks if lo <= t[0] < hi and (t[1], t[2], t[3][0]) not in claimed]
        while band and free:
            best = None
            for ti, (pri, tx, ty, op, carry) in enumerate(band):
                z = zone.get((tx, ty), -1)
                for u in free:
                    d = abs(pos[u][0] - tx) + abs(pos[u][1] - ty) + (0 if z == u else 12)
                    if best is None or d < best[0]:
                        best = (d, ti, u)
            _, ti, u = best
            pri, tx, ty, op, carry = band.pop(ti)
            jobs[u] = {"x": tx, "y": ty, "op": op, "carry": carry}
            claimed.add((tx, ty, op[0]))
            free.remove(u)
    for u in list(free):
        if wheat_need > 0 and shed.get("WHEAT", 0) > 0 and invs[u].get("WHEAT", 0) == 0:
            sx, sy = min(sheds, key=lambda p: abs(pos[u][0] - p[0]) + abs(pos[u][1] - p[1]))
            jobs[u] = {"x": sx, "y": sy, "op": ["PICKUP", "WHEAT", 4], "carry": None}
            free.remove(u)

    acts = [["PASS"] for _ in range(nu)]
    dc = {}
    for u, j in jobs.items():
        x, y = pos[u]
        tx, ty, op, carry = j["x"], j["y"], j["op"], j["carry"]
        if carry and invs[u].get(carry, 0) <= 0:
            if (x, y) in shedset:
                if shed.get(carry, 0) > 0:
                    acts[u] = ["PICKUP", carry, 4 if carry == "WHEAT" else 1]
                    shed[carry] -= 1
                    invs[u][carry] = invs[u].get(carry, 0) + 1
                continue
            tx, ty = min(sheds, key=lambda p: abs(x - p[0]) + abs(y - p[1]))
            op = None
        if (x, y) == (tx, ty):
            acts[u] = op if op else ["PASS"]
            continue
        if (tx, ty) not in dc:
            dc[(tx, ty)] = bfs(tiles, tx, ty, N)
        d = dc[(tx, ty)]
        cur, mv = d[y][x], None
        if cur > 0:
            for name, dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < N and 0 <= ny < N and d[ny][nx] == cur - 1:
                    mv = name
                    break
        acts[u] = [mv] if mv else ["PASS"]

    used = {}
    for u in range(nu):
        if acts[u] and acts[u][0] == "PLANT":
            c = acts[u][1]
            used[c] = used.get(c, 0) + 1
            if used[c] > seeds.get(c, 0):
                acts[u] = ["PASS"]
                jobs.pop(u, None)

    # ---------------- market: strict spend priority against a cash floor -----
    orders, slots, R = [], 10, P["RESERVE"]

    # 1. sell first so the rest of the turn's budget is real money
    total_shed = sum(shed.values())
    desperate = total_shed >= 86
    floors = {"MELON": P["MELON_FLOOR"]}
    sellable = sorted([(i, q) for i, q in shed.items() if i in PRODUCTS and q > 0],
                      key=lambda kv: -price_of(kv[0], mkt.get(kv[0], I0)) * kv[1])
    for it, have in sellable:
        if slots <= 3:
            break
        if it == "WHEAT" and not desperate:
            have -= min(have, feed_reserve)
            if have <= 0:
                continue
        fl = 1 if desperate else max(2, int(MP[it][0] * floors.get(it, 0.5)))
        inv, q = mkt.get(it, I0), 0
        while q < have:
            p = price_of(it, inv)
            if p < fl:
                break
            money += p
            q += 1
            if p > 1:
                inv += 1
        if q:
            orders.append(["SELL", it, q])
            mkt[it] = inv
            slots -= 1

    # 2. hands — the cheapest multiplier in the game (fib: 1,1,2,3,5,8,...)
    if hour <= 1 and slots > 0:
        pending = len([t for t in tasks if t[0] >= 40])
        want = max(6, min(P["HIRE_MAX"], int(pending * P["HIRE_K"]) + 4))
        a, b, n = 1, 1, 0
        for _ in range(farm.get("hires_today", 0)):
            a, b = b, a + b
        while farm.get("hires_today", 0) + n < want and n < slots and money - a >= R:
            money -= a
            a, b = b, a + b
            n += 1
        orders += [["HIRE"]] * n
        slots -= n

    # 3. feed — an unfed goose escapes after two days and is gone for good
    if slots > 0 and n_geese > 0:
        wp = price_of("WHEAT", mkt.get("WHEAT", I0))
        d = feed_reserve - shed.get("WHEAT", 0)
        if d > 0 and money - d * wp >= R:
            orders.append(["BUY_PRODUCT", "WHEAT", d])
            money -= d * wp
            slots -= 1

    # 4. seeds
    need = []
    if melon_ok:
        need.append(("MELON", min(melon_target - cnt.get("MELON", 0), 8) - seeds.get("MELON", 0)))
    if days_left >= 5:
        need.append(("WHEAT", min(max(0, wheat_target - cnt.get("WHEAT", 0)), 16) - seeds.get("WHEAT", 0)))
    if days_left >= 4:
        need.append(("CARROT", min(len(empties) + 3, 20) - seeds.get("CARROT", 0)))
    for crop, q in need:
        if slots <= 0:
            break
        if q <= 0:
            continue
        sc = CROPS[crop]["seed"]
        q = min(q, int(max(0, money - R) // sc))
        if q > 0:
            orders.append(["BUY_SEED", crop, q])
            money -= q * sc
            slots -= 1

    # 5. geese, then land — both only from genuine surplus
    if slots > 0 and days_left >= 9 and P["GOOSE_MAX"] > 0:
        room = min(n_coop - n_geese, P["GOOSE_MAX"] - n_geese) - shed.get("GOOSE", 0)
        if room > 0 and money - 300 >= R + 300:
            q = min(room, int((money - R - 300) // 300), 4)
            if q > 0:
                orders.append(["BUY_ANIMAL", "GOOSE", q])
                money -= q * 300
                slots -= 1
    nx = len(farm.get("unlocked_quadrants", ["NW"])) - 1
    if slots > 0 and nx < 3 and days_left >= 7 and money - LAND[nx] >= R + P["LAND_BUF"]:
        orders.append(["BUY_LAND"])
        slots -= 1

    return {"farmer": acts[0], "hands": acts[1:], "market": orders}