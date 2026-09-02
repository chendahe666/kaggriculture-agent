"""Submission entry point for the Kaggriculture V1 endgame-guard agent.

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


def _decide(obs):
    """Choose a conservative one-tile wheat-cycle action and its reason."""
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
    private = _get(obs, "private", {}) or {}
    seeds = _get(private, "seeds", {}) or {}
    shed = _get(private, "shed", {}) or {}
    wheat_seeds = _as_nonnegative_int(_get(seeds, "WHEAT", 0))
    wheat_in_shed = _as_nonnegative_int(_get(shed, "WHEAT", 0))
    day = _as_nonnegative_int(_get(obs, "day", 0))
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
    if (
        wheat_seeds == 0
        and money >= 10
        and _replacement_wheat_seed_can_finish(tile, day)
    ):
        market.append(["BUY_SEED", "WHEAT", 1])

    farmer = ["PASS"]
    reason = "no useful verified tile action; safe PASS"

    if tile is None:
        if wheat_seeds > 0 and _can_finish_wheat_planted_on(day):
            farmer = ["PLANT", "WHEAT"]
            reason = "empty owned tile and wheat seed available"
        elif wheat_seeds > 0:
            reason = "endgame guard: wheat planted now cannot mature before game end"
        elif any(order[:2] == ["BUY_SEED", "WHEAT"] for order in market):
            reason = "buying wheat seed; purchase is available next turn"
        else:
            reason = "endgame guard: no remaining profitable wheat cycle"
    elif isinstance(tile, dict):
        kind = tile.get("kind")
        if kind == "PLANT":
            crop = tile.get("crop")
            watered = bool(tile.get("watered_today", False))
            planted_day = _as_nonnegative_int(tile.get("planted_day", day))
            age = max(0, day - planted_day)
            yield_units = _as_nonnegative_int(tile.get("yield_units", 0))

            if not watered:
                farmer = ["WATER"]
                reason = f"water {crop or 'plant'} for daily survival/yield"
            elif crop == "WHEAT" and age >= 4 and yield_units > 0:
                farmer = ["HARVEST"]
                reason = "wheat reached verified max-yield day"
            elif crop != "WHEAT" and yield_units > 0:
                farmer = ["HARVEST"]
                reason = "unexpected crop has harvestable yield"
            else:
                reason = "plant already watered; waiting for harvest maturity"
        elif kind == "WEED":
            farmer = ["DIG"]
            reason = "clear weed from the working tile"
        elif kind in {"COOP", "PASTURE"} and "animal" not in tile:
            farmer = ["DIG"]
            reason = "clear unexpected empty structure from the working tile"
        elif "animal" in tile:
            reason = "unexpected animal present without a verified feed inventory plan"
    elif tile == "LOCKED":
        reason = "current tile is locked; safe PASS"

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
