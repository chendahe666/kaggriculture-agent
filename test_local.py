"""Run and verify one complete local Kaggriculture episode."""

import json
import platform
import sys
import time
import traceback
from collections.abc import Mapping
from pathlib import Path

import main as agent_module


PROJECT_DIR = Path(__file__).resolve().parent
LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "episode_001.log"
TEST_SEED = 20260901

UNIT_OPS = {
    "NORTH",
    "SOUTH",
    "EAST",
    "WEST",
    "PASS",
    "PICKUP",
    "PLACE",
    "DROP",
    "PLANT",
    "WATER",
    "HARVEST",
    "FERTILIZE",
    "BUILD_COOP",
    "BUILD_PASTURE",
    "FEED",
    "COLLECT_FERTILIZER",
    "CARE",
    "DIG",
}
MARKET_OPS = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND"}
MARKET_ITEMS = {
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
    "GOOSE",
    "COW",
    "SHEEP",
}


def _get(value, key, default):
    getter = getattr(value, "get", None)
    return getter(key, default) if callable(getter) else default


def _plain(value):
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _nonzero(mapping):
    if not isinstance(mapping, Mapping):
        return "unavailable"
    return {key: value for key, value in mapping.items() if value}


def _farm_for(obs):
    farms = _get(obs, "farms", [])
    player = int(_get(obs, "player", 0))
    if not isinstance(farms, (list, tuple)) or not (0 <= player < len(farms)):
        return None
    return farms[player]


def _tile_summaries(farm):
    crops = {}
    animals = {}
    weeds = 0
    if farm is None:
        return "unavailable", "unavailable", "unavailable"
    tiles = _get(farm, "tiles", [])
    if not isinstance(tiles, (list, tuple)):
        return "unavailable", "unavailable", "unavailable"
    for row in tiles:
        if not isinstance(row, (list, tuple)):
            continue
        for tile in row:
            if not isinstance(tile, Mapping):
                continue
            if tile.get("kind") == "PLANT":
                crop = tile.get("crop", "UNKNOWN")
                crops[crop] = crops.get(crop, 0) + 1
            elif tile.get("kind") == "WEED":
                weeds += 1
            if "animal" in tile:
                animal = tile.get("animal", "UNKNOWN")
                animals[animal] = animals.get(animal, 0) + 1
    return crops, animals, weeds


def _snapshot(obs):
    farm = _farm_for(obs)
    private = _get(obs, "private", {}) or {}
    crops, animals, weeds = _tile_summaries(farm)
    return {
        "step": _get(obs, "step", "unavailable"),
        "day": _get(obs, "day", "unavailable"),
        "hour": _get(obs, "hour", "unavailable"),
        "coins": _get(farm, "money", "unavailable") if farm is not None else "unavailable",
        "position": _get(farm, "farmer", "unavailable") if farm is not None else "unavailable",
        "workers": len(_get(farm, "hands", [])) if farm is not None else "unavailable",
        "shed": _nonzero(_get(private, "shed", {})),
        "seeds": _nonzero(_get(private, "seeds", {})),
        "inventories": _plain(_get(private, "inventories", "unavailable")),
        "crops": crops,
        "animals": animals,
        "weeds": weeds,
    }


def _numeric_delta(before, after):
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return after - before
    return "unavailable"


def _mapping_delta(before, after):
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        return "unavailable"
    delta = {}
    for key in sorted(set(before) | set(after)):
        old = before.get(key, 0)
        new = after.get(key, 0)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) and new != old:
            delta[key] = new - old
    return delta


def _validate_unit_action(action, label):
    errors = []
    if not isinstance(action, list) or not action or action[0] not in UNIT_OPS:
        return [f"{label} is not a verified unit action: {action!r}"]
    op = action[0]
    if op in {"PLANT", "PICKUP", "PLACE"} and len(action) < 2:
        errors.append(f"{label} {op} is missing an item argument")
    if op not in {"PLANT", "PICKUP", "PLACE"} and len(action) != 1:
        errors.append(f"{label} {op} has unexpected arguments")
    return errors


def _validate_market_order(order, index):
    label = f"market[{index}]"
    if not isinstance(order, list) or not order or order[0] not in MARKET_OPS:
        return [f"{label} is not a verified market order: {order!r}"]
    op = order[0]
    if op in {"HIRE", "BUY_LAND"}:
        return [] if len(order) == 1 else [f"{label} {op} has unexpected arguments"]
    if len(order) != 3 or order[1] not in MARKET_ITEMS:
        return [f"{label} has invalid shape/item: {order!r}"]
    try:
        quantity = int(order[2])
    except (TypeError, ValueError):
        return [f"{label} quantity is not an integer: {order[2]!r}"]
    return [] if quantity > 0 else [f"{label} quantity is not positive: {quantity}"]


def validate_action(action, obs, max_market_orders):
    errors = []
    if not isinstance(action, dict):
        return [f"action is not a dict: {action!r}"]
    errors.extend(_validate_unit_action(action.get("farmer"), "farmer"))

    hands = action.get("hands")
    farm = _farm_for(obs)
    expected_hands = len(_get(farm, "hands", [])) if farm is not None else 0
    if not isinstance(hands, list):
        errors.append("hands is not a list")
    else:
        if len(hands) != expected_hands:
            errors.append(f"hands count {len(hands)} != observed worker count {expected_hands}")
        for index, hand_action in enumerate(hands):
            errors.extend(_validate_unit_action(hand_action, f"hands[{index}]"))

    market = action.get("market")
    if not isinstance(market, list):
        errors.append("market is not a list")
    else:
        if len(market) > max_market_orders:
            errors.append(f"market order count {len(market)} > cap {max_market_orders}")
        for index, order in enumerate(market):
            errors.extend(_validate_market_order(order, index))
    return errors


class EpisodeLogger:
    def __init__(self, handle, max_market_orders):
        self.handle = handle
        self.max_market_orders = max_market_orders
        self.calls = 0
        self.invalid_actions = 0
        self.wrapper_exceptions = 0
        self.previous = None
        self.previous_action = None
        self.first_observation_written = False

    def _write(self, text=""):
        self.handle.write(text + "\n")

    def _write_outcome(self, current):
        if self.previous is None:
            return
        self._write(
            f"[OUTCOME {self.previous['step']} -> {current['step']}] "
            f"coins_after={current['coins']} "
            f"coins_change={_numeric_delta(self.previous['coins'], current['coins'])} "
            f"shed_change={_mapping_delta(self.previous['shed'], current['shed'])} "
            f"seeds_change={_mapping_delta(self.previous['seeds'], current['seeds'])} "
            f"position_change={self.previous['position']}->{current['position']}"
        )

    def __call__(self, obs, configuration=None):
        # kaggle-environments passes configuration to callable objects even
        # though the submitted plain agent(obs) entry point receives only obs.
        self.calls += 1
        current = _snapshot(obs)
        if not self.first_observation_written:
            self._write("=== FULL FIRST-TURN OBSERVATION ===")
            self._write(json.dumps(_plain(obs), indent=2, sort_keys=True))
            self._write("=== END FIRST-TURN OBSERVATION ===")
            self.first_observation_written = True
        self._write_outcome(current)

        try:
            action = agent_module.agent(obs)
        except Exception:
            self.wrapper_exceptions += 1
            self._write("AGENT WRAPPER EXCEPTION:")
            self._write(traceback.format_exc())
            action = {
                "farmer": ["PASS"],
                "hands": [["PASS"] for _ in range(current["workers"] or 0)],
                "market": [],
            }

        validation_errors = validate_action(action, obs, self.max_market_orders)
        if validation_errors:
            self.invalid_actions += 1
            self._write(f"INVALID ACTION REPLACED: {validation_errors!r}")
            action = {
                "farmer": ["PASS"],
                "hands": [["PASS"] for _ in range(current["workers"] or 0)],
                "market": [],
            }

        decision = agent_module.get_last_decision()
        self._write(f"[TURN {current['step']} | DAY {current['day']} | HOUR {current['hour']}]")
        self._write(f"coins={current['coins']}")
        self._write(f"farmer_position={current['position']}")
        self._write(f"workers={current['workers']}")
        self._write(f"shed={current['shed']}")
        self._write(f"seeds={current['seeds']}")
        self._write(f"inventories={current['inventories']}")
        self._write(f"crops={current['crops']} weeds={current['weeds']}")
        self._write(f"animals={current['animals']}")
        self._write("decision:")
        self._write(f"farmer_action={action.get('farmer')}")
        self._write(f"worker_actions={action.get('hands')}")
        self._write(f"market_actions={action.get('market')}")
        self._write(f"reason={decision.get('reason', 'unavailable')!r}")
        self._write()
        self.previous = current
        self.previous_action = action
        return action

    def finish(self, final_obs):
        current = _snapshot(final_obs)
        self._write_outcome(current)
        self._write("=== END OF EPISODE ===")
        self.handle.flush()


def _format_value(value):
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _print_summary(summary):
    print("=" * 40)
    print("KAGGRICULTURE LOCAL TEST SUMMARY")
    print("=" * 40)
    for key, value in summary.items():
        print(f"{key}: {_format_value(value)}")
    print("=" * 40)


def run_test():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    agent_module.reset_runtime_state()
    started = time.perf_counter()

    with LOG_FILE.open("w", encoding="utf-8", newline="\n") as log:
        log.write("KAGGRICULTURE V0 LOCAL EPISODE LOG\n")
        log.write(f"platform={platform.platform()}\n")
        log.write(f"python={sys.version.split()[0]}\n")
        log.write(f"requested_seed={TEST_SEED}\n")
        log.write("opponent=starter (official deterministic built-in)\n\n")

        from kaggle_environments import __version__ as kaggle_env_version
        from kaggle_environments import environments, make

        environment_loaded = "kaggriculture" in environments
        if not environment_loaded:
            raise RuntimeError("kaggriculture is not registered in kaggle-environments")
        available_agents = sorted(environments["kaggriculture"].get("agents", {}))
        if "starter" not in available_agents:
            raise RuntimeError(f"starter opponent unavailable; found {available_agents}")

        env = make("kaggriculture", configuration={"seed": TEST_SEED}, debug=True)
        expected_steps = int(env.configuration.episodeSteps)
        turns_per_day = int(env.configuration.turnsPerDay)
        tracker = EpisodeLogger(log, int(env.configuration.maxMarketOrdersPerTurn))

        env.run([tracker, "starter"])
        runtime = time.perf_counter() - started
        final_states = env.steps[-1]
        tracker.finish(final_states[0].observation)

        statuses = [state.status for state in final_states]
        rewards = [state.reward for state in final_states]
        farms = _get(final_states[0].observation, "farms", [])
        final_coins = farms[0]["money"] if len(farms) > 0 else None
        opponent_coins = farms[1]["money"] if len(farms) > 1 else None
        if isinstance(final_coins, (int, float)) and isinstance(opponent_coins, (int, float)):
            result = "WIN" if final_coins > opponent_coins else "LOSS" if final_coins < opponent_coins else "DRAW"
        else:
            result = "unavailable"

        runtime_stats = agent_module.get_runtime_stats()
        episode_completed = len(env.steps) == expected_steps and all(
            status == "DONE" for status in statuses
        )
        pass_conditions = (
            environment_loaded
            and callable(getattr(agent_module, "agent", None))
            and tracker.calls > 0
            and episode_completed
            and tracker.invalid_actions == 0
            and tracker.wrapper_exceptions == 0
            and runtime_stats["exceptions"] == 0
        )

        log.write(f"kaggle_environments={kaggle_env_version}\n")
        log.write("episode_identifier=unavailable (not exposed by local environment)\n")
        log.write(f"resolved_seed={env.info.get('seed', 'unavailable')}\n")
        log.write(f"configuration={json.dumps(_plain(env.configuration), sort_keys=True)}\n")
        log.write(f"available_agents={available_agents}\n")
        log.write(f"recorded_episode_steps={len(env.steps)}\n")
        log.write(f"agent_calls={tracker.calls}\n")
        log.write(f"final_statuses={statuses}\n")
        log.write(f"rewards={rewards}\n")
        log.write(f"final_coins={final_coins}\n")
        log.write(f"opponent_final_coins={opponent_coins}\n")
        log.write(f"result={result}\n")
        log.write(f"runtime_seconds={runtime:.6f}\n")
        log.write(f"invalid_actions={tracker.invalid_actions}\n")
        log.write(f"agent_exceptions={runtime_stats['exceptions']}\n")
        log.write(f"wrapper_exceptions={tracker.wrapper_exceptions}\n")

    summary = {
        "status": "PASS" if pass_conditions else "FAIL",
        "environment_loaded": "yes" if environment_loaded else "no",
        "agent_entrypoint_found": "yes" if callable(getattr(agent_module, "agent", None)) else "no",
        "agent_called": "yes" if tracker.calls > 0 else "no",
        "episode_completed": "yes" if episode_completed else "no",
        "recorded_episode_steps": len(env.steps),
        "agent_calls": tracker.calls,
        "turns_per_day": turns_per_day,
        "runtime_seconds": round(runtime, 6),
        "final_coins": final_coins,
        "opponent_final_coins": opponent_coins,
        "result": result,
        "invalid_actions": tracker.invalid_actions,
        "agent_exceptions": runtime_stats["exceptions"],
        "uncaught_exceptions": 0,
        "log_file": str(LOG_FILE.relative_to(PROJECT_DIR)),
    }
    _print_summary(summary)
    return 0 if pass_conditions else 1


def main():
    try:
        return run_test()
    except Exception as exc:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        error_text = traceback.format_exc()
        with LOG_FILE.open("a", encoding="utf-8", newline="\n") as log:
            log.write("\nUNCAUGHT TEST FAILURE\n")
            log.write(error_text)
        _print_summary(
            {
                "status": "FAIL",
                "environment_loaded": "unverified",
                "agent_entrypoint_found": "yes" if callable(getattr(agent_module, "agent", None)) else "no",
                "episode_completed": "no",
                "error": f"{type(exc).__name__}: {exc}",
                "uncaught_exceptions": 1,
                "log_file": str(LOG_FILE.relative_to(PROJECT_DIR)),
            }
        )
        print(error_text, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
