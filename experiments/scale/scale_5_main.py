"""Submission entry point for the Kaggriculture scale-5 experiment.

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
WHEAT_MAX_YIELD_DAY = 4
TARGET_TILE_COUNT = 5

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


def _can_finish_wheat_planted_on(day):
    return day + WHEAT_MAX_YIELD_DAY <= LAST_GAME_DAY


def _replacement_wheat_seed_can_finish(tile, day):
    """Whether one newly bought seed can still become sold wheat this episode."""
    if tile is None:
        return _can_finish_wheat_planted_on(day)
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        if tile.get("crop") == "WHEAT":
            planted_day = _as_nonnegative_int(tile.get("planted_day", day))
            next_plant_day = planted_day + WHEAT_MAX_YIELD_DAY
            return _can_finish_wheat_planted_on(next_plant_day)
    return _can_finish_wheat_planted_on(day)


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
    for row_offset, y in enumerate(range(origin, -1, -1)):
        xs = range(origin, -1, -1) if row_offset % 2 == 0 else range(0, origin + 1)
        positions.extend((x, y) for x in xs)
    return positions[:TARGET_TILE_COUNT]


def _future_seed_slots(tiles, targets, day):
    return sum(
        _replacement_wheat_seed_can_finish(_tile_at(tiles, position), day)
        for position in targets
    )


def _task_for_tile(tile, day, wheat_seeds):
    """Return (priority, action, reason) for one managed tile, if actionable."""
    if tile is None:
        if wheat_seeds > 0 and _can_finish_wheat_planted_on(day):
            return 3, ["PLANT", "WHEAT"], "plant an empty managed tile"
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
        if crop == "WHEAT" and age >= WHEAT_MAX_YIELD_DAY and yield_units > 0:
            return 1, ["HARVEST"], "harvest mature managed wheat"
        if crop != "WHEAT" and yield_units > 0:
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
    wheat_seeds = _as_nonnegative_int(_get(seeds, "WHEAT", 0))
    wheat_in_shed = _as_nonnegative_int(_get(shed, "WHEAT", 0))
    day = _as_nonnegative_int(_get(obs, "day", 0))
    hour = _as_nonnegative_int(_get(obs, "hour", 0))
    inventories = _get(private, "inventories", []) or []
    farmer_inventory = inventories[0] if isinstance(inventories, (list, tuple)) and inventories else {}
    wheat_carried = _as_nonnegative_int(_get(farmer_inventory, "WHEAT", 0))
    money = _get(farm, "money", 0)
    try:
        money = float(money)
    except (TypeError, ValueError):
        money = 0.0

    hands = _get(farm, "hands", [])
    hand_actions = [
        ["PASS"] for _ in range(len(hands) if isinstance(hands, (list, tuple)) else 0)
    ]
    market = []
    if wheat_in_shed > 0:
        market.append(["SELL", "WHEAT", wheat_in_shed])
    wanted_seeds = _future_seed_slots(tiles, targets, day)
    missing_seeds = max(0, wanted_seeds - wheat_seeds)
    affordable_seeds = max(0, int(money // 10))
    buy_count = min(missing_seeds, affordable_seeds)
    if buy_count > 0:
        market.append(["BUY_SEED", "WHEAT", buy_count])

    farmer = ["PASS"]
    reason = "no useful verified tile action; safe PASS"

    candidates = []
    shed_position = targets[0]
    remaining_calls = max(0, 23 - hour) if day == LAST_GAME_DAY else 24
    for index, target in enumerate(targets):
        task = _task_for_tile(_tile_at(tiles, target), day, wheat_seeds)
        if task is None:
            continue
        priority, task_action, task_reason = task
        distance = abs(target[0] - x) + abs(target[1] - y)
        if day == LAST_GAME_DAY and task_action[0] == "HARVEST":
            return_distance = abs(target[0] - shed_position[0]) + abs(
                target[1] - shed_position[1]
            )
            calls_to_bank = distance + 1 + return_distance + 1
            if calls_to_bank > remaining_calls:
                continue
        candidates.append((priority, distance, index, target, task_action, task_reason))

    cashout_distance = abs(shed_position[0] - x) + abs(shed_position[1] - y)
    cashout_due = (
        day == LAST_GAME_DAY
        and wheat_carried > 0
        and (not candidates or remaining_calls <= cashout_distance + 1)
    )
    if cashout_due and cashout_distance == 0:
        farmer = ["DROP"]
        reason = "final-day cashout: drop carried wheat at shed access"
    elif cashout_due:
        farmer = _move_toward((x, y), shed_position)
        reason = f"final-day cashout: return to shed access at {list(shed_position)}"
    elif candidates:
        _, distance, _, target, task_action, task_reason = min(candidates)
        if distance == 0:
            farmer = task_action
            reason = f"{task_reason} at {list(target)}"
        else:
            farmer = _move_toward((x, y), target)
            reason = f"move toward {list(target)} to {task_reason}"
    elif buy_count > 0:
        reason = f"buying {buy_count} wheat seed(s); available next turn"
    elif wheat_seeds > 0 and not _can_finish_wheat_planted_on(day):
        reason = "endgame guard: remaining seed cannot mature before game end"
    elif tile == "LOCKED":
        reason = "current tile is locked and no managed task is actionable"
    else:
        reason = "all managed tiles are safe for this turn"

    if farmer[0] == "DROP" and wheat_carried > 0:
        sell_order = next(
            (order for order in market if order[:2] == ["SELL", "WHEAT"]), None
        )
        if sell_order is None:
            market.insert(0, ["SELL", "WHEAT", wheat_carried])
        else:
            sell_order[2] += wheat_carried

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
