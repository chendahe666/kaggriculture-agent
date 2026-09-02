"""Submission entry point for the Kaggriculture V4.2 paced-sale agent.

The agent intentionally uses only the Python standard library and defaults to
silent, submission-safe behavior. Set KAGGRICULTURE_DEBUG=1 locally for compact
per-turn stdout diagnostics.
"""

import os
import traceback


DEBUG = os.environ.get("KAGGRICULTURE_DEBUG", "0").lower() in {"1", "true", "yes"}
DEBUG_VERBOSE = os.environ.get("KAGGRICULTURE_DEBUG_VERBOSE", "0").lower() in {
    "1",
    "true",
    "yes",
}

LAST_GAME_DAY = 29
ENDGAME_BUFFER_DAYS = 0
LAST_CYCLE_TILE_COUNT = 6
CROP_MODE = "WHEAT"
SELL_MODE = "THRESHOLD"
MAX_NORMAL_SALE_BATCH = 16
MIX_CARROT_TILES = 1
CROP_DATA = {
    "WHEAT": {"seed_cost": 10, "max_yield_day": 4, "max_yield": 6},
    "CARROT": {"seed_cost": 20, "max_yield_day": 3, "max_yield": 4},
}
DESIRED_HANDS = 1
TARGET_TILES_PER_UNIT = 5
TARGET_TILE_COUNT = 6

_LAST_DECISION = {"reason": "agent has not been called"}
_LAST_ERROR = None
_RUNTIME_STATS = {"calls": 0, "exceptions": 0}


def _get(value, key, default):
    getter = getattr(value, "get", None)
    return getter(key, default) if callable(getter) else default


def _hand_count(obs):
    try:
        farms = _get(obs, "farms", [])
        player = int(_get(obs, "player", 0))
        if not isinstance(farms, (list, tuple)) or not (0 <= player < len(farms)):
            return 0
        hands = _get(farms[player], "hands", [])
        return len(hands) if isinstance(hands, (list, tuple)) else 0
    except (TypeError, ValueError, IndexError):
        return 0


def _fallback_action(obs):
    """Return the verified Kaggriculture no-op shape."""
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in range(_hand_count(obs))],
        "market": [],
    }


def _as_nonnegative_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _can_finish_crop_planted_on(crop, day):
    crop_data = CROP_DATA.get(crop)
    return bool(crop_data) and day + crop_data["max_yield_day"] <= (
        LAST_GAME_DAY - ENDGAME_BUFFER_DAYS
    )


def _replacement_seed_can_finish(tile, day, desired_crop, target_index):
    """Whether one newly bought seed can still become sold wheat this episode."""
    if tile is None:
        candidate_day = day
        can_finish = _can_finish_crop_planted_on(desired_crop, candidate_day)
        return can_finish and not (
            candidate_day + CROP_DATA[desired_crop]["max_yield_day"] == LAST_GAME_DAY
            and target_index >= LAST_CYCLE_TILE_COUNT
        )
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        planted_crop = tile.get("crop")
        crop_data = CROP_DATA.get(planted_crop)
        if crop_data:
            planted_day = _as_nonnegative_int(tile.get("planted_day", day))
            next_plant_day = planted_day + crop_data["max_yield_day"]
            can_finish = _can_finish_crop_planted_on(desired_crop, next_plant_day)
            return can_finish and not (
                next_plant_day + CROP_DATA[desired_crop]["max_yield_day"]
                == LAST_GAME_DAY
                and target_index >= LAST_CYCLE_TILE_COUNT
            )
    return _can_finish_crop_planted_on(desired_crop, day)


def _tile_at(tiles, position):
    x, y = position
    if not isinstance(tiles, (list, tuple)) or not (0 <= y < len(tiles)):
        return "LOCKED"
    row = tiles[y]
    if not isinstance(row, (list, tuple)) or not (0 <= x < len(row)):
        return "LOCKED"
    return row[x]


def _target_positions(tiles):
    """Return a shed-outward snake through the initially owned NW field."""
    if not isinstance(tiles, (list, tuple)) or not tiles:
        return []
    first_row = tiles[0]
    if not isinstance(first_row, (list, tuple)) or not first_row:
        return []
    board_size = min(len(tiles), len(first_row))
    origin = max(0, board_size // 2 - 1)
    positions = []
    for y in range(origin, -1, -1):
        positions.extend((x, y) for x in range(origin, -1, -1))
    return positions[:TARGET_TILE_COUNT]


def _shop_demand(town, crop):
    shops = _get(town, "unlocked_shops", []) or []
    products = {
        "BAKERY": ("WHEAT",),
        "PIZZA_SHOP": ("WHEAT",),
        "BRUNCH_SPOT": ("WHEAT",),
        "ICE_CREAM_SHOP": ("WHEAT",),
        "PET_CAFE": ("CARROT", "CARROT"),
        "FARMERS_MARKET": ("WHEAT", "CARROT"),
    }
    return sum(products.get(shop, ()).count(crop) for shop in shops)


def _preferred_crop(prices, town):
    """Choose on current economics; shop demand is a conservative tie-break."""
    scored = []
    for crop, data in CROP_DATA.items():
        price = _as_nonnegative_int(_get(prices, crop, 0))
        actions = data["max_yield_day"] + 2  # plant + daily water + harvest
        margin_per_action = (data["max_yield"] * price - data["seed_cost"]) / actions
        scored.append((margin_per_action, _shop_demand(town, crop), crop))
    return max(scored)[2]


def _target_crops(tiles, targets, prices, town, seed_counts):
    if CROP_MODE == "CARROT":
        return ["CARROT" for _ in targets], True
    if CROP_MODE == "MIX":
        split = max(0, len(targets) - MIX_CARROT_TILES)
        crops = ["WHEAT" if index < split else "CARROT" for index in range(len(targets))]
        return crops, True
    if CROP_MODE == "ADAPTIVE":
        crop = _preferred_crop(prices, town)
        return [crop for _ in targets], True
    return ["WHEAT" for _ in targets], True


def _future_seed_slots(tiles, targets, target_crops, day, allow_plant):
    slots = {crop: 0 for crop in CROP_DATA}
    if not allow_plant:
        return slots
    for index, (position, crop) in enumerate(zip(targets, target_crops)):
        tile = _tile_at(tiles, position)
        if _replacement_seed_can_finish(tile, day, crop, index):
            slots[crop] += 1
    return slots


def _task_for_tile(tile, day, available_seeds, desired_crop):
    """Return (priority, action, reason) for one managed tile, if actionable."""
    if tile is None:
        if available_seeds > 0 and _can_finish_crop_planted_on(desired_crop, day):
            return 3, ["PLANT", desired_crop], f"plant managed {desired_crop}"
        return None
    if not isinstance(tile, dict):
        return None

    kind = tile.get("kind")
    if kind == "PLANT":
        crop = tile.get("crop")
        if not bool(tile.get("watered_today", False)):
            return 0, ["WATER"], f"water managed {crop or 'plant'} before other work"
        planted_day = _as_nonnegative_int(tile.get("planted_day", day))
        age = max(0, day - planted_day)
        yield_units = _as_nonnegative_int(tile.get("yield_units", 0))
        crop_data = CROP_DATA.get(crop)
        if crop_data and age >= crop_data["max_yield_day"] and yield_units > 0:
            return 1, ["HARVEST"], f"harvest mature managed {crop}"
        if not crop_data and yield_units > 0:
            return 1, ["HARVEST"], "harvest unexpected crop from managed tile"
        return None
    if kind == "WEED":
        return 2, ["DIG"], "clear weed from managed tile"
    if kind in {"COOP", "PASTURE"} and "animal" not in tile:
        return 2, ["DIG"], "clear unexpected empty structure from managed tile"
    return None


def _move_toward(position, target):
    x, y = position
    tx, ty = target
    if tx < x:
        return ["WEST"]
    if tx > x:
        return ["EAST"]
    if ty < y:
        return ["NORTH"]
    if ty > y:
        return ["SOUTH"]
    return ["PASS"]


def _decide(obs):
    """Choose the next action in a conservative three-tile wheat schedule."""
    fallback = _fallback_action(obs)
    farms = _get(obs, "farms", [])
    player = int(_get(obs, "player", 0))
    if not isinstance(farms, (list, tuple)) or not (0 <= player < len(farms)):
        return fallback, "farm state unavailable; safe PASS"

    farm = farms[player]
    position = _get(farm, "farmer", [])
    tiles = _get(farm, "tiles", [])
    if not isinstance(position, (list, tuple)) or len(position) < 2:
        return fallback, "farmer position unavailable; safe PASS"

    x, y = int(position[0]), int(position[1])
    if not isinstance(tiles, (list, tuple)) or not (0 <= y < len(tiles)):
        return fallback, "tile grid unavailable; safe PASS"
    row = tiles[y]
    if not isinstance(row, (list, tuple)) or not (0 <= x < len(row)):
        return fallback, "farmer position is outside tile grid; safe PASS"

    tile = row[x]
    targets = _target_positions(tiles)
    if not targets:
        return fallback, "managed tile set unavailable; safe PASS"
    private = _get(obs, "private", {}) or {}
    seeds = _get(private, "seeds", {}) or {}
    shed = _get(private, "shed", {}) or {}
    seed_counts = {
        crop: _as_nonnegative_int(_get(seeds, crop, 0)) for crop in CROP_DATA
    }
    shed_counts = {
        crop: _as_nonnegative_int(_get(shed, crop, 0)) for crop in CROP_DATA
    }
    day = _as_nonnegative_int(_get(obs, "day", 0))
    hour = _as_nonnegative_int(_get(obs, "hour", 0))
    inventories = _get(private, "inventories", []) or []
    farmer_inventory = inventories[0] if isinstance(inventories, (list, tuple)) and inventories else {}
    money = _get(farm, "money", 0)
    try:
        money = float(money)
    except (TypeError, ValueError):
        money = 0.0

    hands = _get(farm, "hands", [])
    if not isinstance(hands, (list, tuple)):
        hands = []
    market = []
    if day < LAST_GAME_DAY:
        for _ in range(max(0, DESIRED_HANDS - len(hands))):
            market.append(["HIRE"])
    market_state = _get(obs, "market", {}) or {}
    prices = _get(market_state, "prices", {}) or {}
    town = _get(obs, "town", {}) or {}
    target_crops, allow_plant = _target_crops(
        tiles, targets, prices, town, seed_counts
    )
    for crop, amount in shed_counts.items():
        price = _as_nonnegative_int(_get(prices, crop, 0))
        should_sell = SELL_MODE == "IMMEDIATE" or day == LAST_GAME_DAY or price >= {
            "WHEAT": 25,
            "CARROT": 35,
        }[crop]
        if amount > 0 and should_sell:
            sell_amount = (
                amount
                if day == LAST_GAME_DAY or MAX_NORMAL_SALE_BATCH <= 0
                else min(amount, MAX_NORMAL_SALE_BATCH)
            )
            market.append(["SELL", crop, sell_amount])
    wanted_seeds = _future_seed_slots(
        tiles, targets, target_crops, day, allow_plant
    )
    buy_counts = {crop: 0 for crop in CROP_DATA}
    remaining_money = money
    for crop, seed_cost in (("WHEAT", 10), ("CARROT", 20)):
        missing_seeds = max(0, wanted_seeds[crop] - seed_counts[crop])
        affordable_seeds = max(0, int(remaining_money // seed_cost))
        buy_counts[crop] = min(missing_seeds, affordable_seeds)
        if buy_counts[crop] > 0:
            market.append(["BUY_SEED", crop, buy_counts[crop]])
            remaining_money -= buy_counts[crop] * seed_cost

    shed_position = targets[0]
    remaining_calls = max(0, 23 - hour) if day == LAST_GAME_DAY else 24
    unit_positions = [(x, y)]
    for position_value in hands:
        if isinstance(position_value, (list, tuple)) and len(position_value) >= 2:
            unit_positions.append((int(position_value[0]), int(position_value[1])))
        else:
            unit_positions.append((x, y))

    unit_actions = []
    unit_reasons = []
    claimed_targets = set()
    plant_actions = {crop: 0 for crop in CROP_DATA}
    for unit_index, (ux, uy) in enumerate(unit_positions):
        candidates = []
        for index, target in enumerate(targets):
            if target in claimed_targets:
                continue
            desired_crop = target_crops[index]
            available_seeds = (
                max(0, seed_counts[desired_crop] - plant_actions[desired_crop])
                if allow_plant
                else 0
            )
            if (
                _tile_at(tiles, target) is None
                and day + CROP_DATA[desired_crop]["max_yield_day"] == LAST_GAME_DAY
                and index >= LAST_CYCLE_TILE_COUNT
            ):
                available_seeds = 0
            task = _task_for_tile(
                _tile_at(tiles, target), day, available_seeds, desired_crop
            )
            if task is None:
                continue
            priority, task_action, task_reason = task
            distance = abs(target[0] - ux) + abs(target[1] - uy)
            if day == LAST_GAME_DAY and task_action[0] == "HARVEST":
                return_distance = abs(target[0] - shed_position[0]) + abs(
                    target[1] - shed_position[1]
                )
                if distance + 1 + return_distance + 1 > remaining_calls:
                    continue
            candidates.append((priority, distance, index, target, task_action, task_reason))

        inventory = inventories[unit_index] if unit_index < len(inventories) else {}
        unit_crop_total = sum(
            _as_nonnegative_int(_get(inventory, crop, 0)) for crop in CROP_DATA
        )
        cashout_distance = abs(shed_position[0] - ux) + abs(shed_position[1] - uy)
        cashout_due = (
            day == LAST_GAME_DAY
            and unit_crop_total > 0
            and (not candidates or remaining_calls <= cashout_distance + 1)
        )
        if cashout_due and cashout_distance == 0:
            unit_action = ["DROP"]
            unit_reason = "final-day cashout at shed access"
        elif cashout_due:
            unit_action = _move_toward((ux, uy), shed_position)
            unit_reason = f"final-day return to shed access {list(shed_position)}"
        elif candidates:
            _, distance, _, target, task_action, task_reason = min(candidates)
            claimed_targets.add(target)
            if distance == 0:
                unit_action = task_action
                unit_reason = f"{task_reason} at {list(target)}"
                if task_action[0] == "PLANT":
                    plant_actions[task_action[1]] += 1
            else:
                unit_action = _move_toward((ux, uy), target)
                unit_reason = f"move toward {list(target)} to {task_reason}"
        else:
            unit_action = ["PASS"]
            unit_reason = "no unclaimed managed task"
        unit_actions.append(unit_action)
        unit_reasons.append(f"unit {unit_index}: {unit_reason}")

    farmer = unit_actions[0] if unit_actions else ["PASS"]
    hand_actions = unit_actions[1:]
    total_buys = sum(buy_counts.values())
    if all(action[0] == "PASS" for action in unit_actions) and total_buys > 0:
        unit_reasons.append(f"market: buying {total_buys} crop seed(s)")
    elif all(action[0] == "PASS" for action in unit_actions) and sum(seed_counts.values()) > 0 and not any(
        _can_finish_crop_planted_on(crop, day) for crop in CROP_DATA
    ):
        unit_reasons.append("market: endgame guard keeps remaining seeds unplanted")
    reason = "; ".join(unit_reasons) or "safe PASS"

    for crop in CROP_DATA:
        drop_amount = sum(
            _as_nonnegative_int(_get(inventories[index], crop, 0))
            for index, action in enumerate(unit_actions)
            if action[0] == "DROP" and index < len(inventories)
        )
        if drop_amount > 0:
            sell_order = next(
                (order for order in market if order[:2] == ["SELL", crop]), None
            )
            if sell_order is None:
                market.insert(0, ["SELL", crop, drop_amount])
            else:
                sell_order[2] += drop_amount

    action = {"farmer": farmer, "hands": hand_actions, "market": market}
    return action, reason


def _debug_log(obs, action, reason):
    if not DEBUG:
        return
    step = _get(obs, "step", "unavailable")
    day = _get(obs, "day", "unavailable")
    print(f"[KAGGRICULTURE step={step} day={day}] action={action!r} reason={reason}")
    if DEBUG_VERBOSE and step == 0:
        print(f"first_observation={obs!r}")


def get_last_decision():
    """Local-test observability hook; the Kaggle harness only calls agent()."""
    return dict(_LAST_DECISION)


def get_runtime_stats():
    return dict(_RUNTIME_STATS)


def get_last_error():
    return _LAST_ERROR


def reset_runtime_state():
    """Reset local counters between test episodes."""
    global _LAST_DECISION, _LAST_ERROR
    _LAST_DECISION = {"reason": "agent has not been called"}
    _LAST_ERROR = None
    _RUNTIME_STATS["calls"] = 0
    _RUNTIME_STATS["exceptions"] = 0


def agent(obs):
    """Kaggle-required entry point. Always attempts to return a valid action.

    Keep this as the final top-level callable: kaggle-environments' file loader
    executes a source file and selects its last callable.
    """
    global _LAST_DECISION, _LAST_ERROR
    _RUNTIME_STATS["calls"] += 1
    try:
        action, reason = _decide(obs)
        _LAST_DECISION = {"action": action, "reason": reason}
        _LAST_ERROR = None
        _debug_log(obs, action, reason)
        return action
    except Exception as exc:  # The fallback must keep a live episode running.
        _RUNTIME_STATS["exceptions"] += 1
        _LAST_ERROR = f"{type(exc).__name__}: {exc}"
        fallback = _fallback_action(obs)
        _LAST_DECISION = {
            "action": fallback,
            "reason": f"exception contained; safe PASS: {_LAST_ERROR}",
        }
        if DEBUG:
            print(
                f"[KAGGRICULTURE ERROR step={_get(obs, 'step', 'unavailable')}] "
                f"{_LAST_ERROR}"
            )
            traceback.print_exc()
            if DEBUG_VERBOSE:
                print(f"exception_observation={obs!r}")
        return fallback
