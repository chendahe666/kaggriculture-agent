"""Run a repeatable Kaggriculture benchmark suite for one agent file.

The runner mirrors the official file-loader rule by executing the source and
selecting the last callable. It records local engineering evidence; it does not
predict the Kaggle skill rating. The built-in ``random`` opponent is intentionally
stochastic and is a robustness probe, not a deterministic regression oracle.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import statistics
import sys
import time
import traceback
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from test_local import validate_action


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_SEEDS = tuple(range(20260901, 20260911))
DEFAULT_OPPONENTS = ("pass", "random", "starter")
DEFAULT_SIDES = (0, 1)
RESULT_FIELDS = (
    "run_index",
    "seed_requested",
    "seed_resolved",
    "opponent",
    "side",
    "recorded_steps",
    "expected_steps",
    "our_status",
    "opponent_status",
    "our_cash",
    "opponent_cash",
    "cash_delta",
    "result",
    "episode_completed",
    "agent_calls",
    "shape_invalid_actions",
    "wrapper_exceptions",
    "agent_internal_exceptions",
    "total_agent_seconds",
    "max_agent_seconds",
    "episode_seconds",
    "farmer_pass_actions",
    "farmer_nonpass_actions",
    "farmer_harvest_actions",
    "hand_pass_actions",
    "hand_nonpass_actions",
    "hand_move_actions",
    "hand_water_actions",
    "hand_harvest_actions",
    "hand_plant_actions",
    "market_orders",
    "hire_orders",
    "max_hands_observed",
    "hand_turns",
    "unit_tile_action_conflicts",
    "plant_to_weed_transitions",
    "wheat_plant_actions",
    "carrot_plant_actions",
    "wheat_harvest_actions",
    "carrot_harvest_actions",
    "wheat_land_days",
    "carrot_land_days",
    "sell_units",
    "realized_sale_revenue",
    "realized_average_sale_price",
    "revenue_per_land_day",
    "revenue_per_nonpass_unit_action",
    "peak_shed_total",
    "minimum_cash",
    "funding_shortfall_orders",
    "unique_plant_tiles_used",
    "median_mature_wait_steps",
    "max_mature_wait_steps",
    "unharvested_mature_tiles",
    "final_seed_total",
    "final_wheat_seeds",
    "final_shed_total",
    "final_wheat_shed",
    "final_carried_total",
    "final_plant_tiles",
    "final_immature_wheat_tiles",
    "runner_error",
)


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_seeds(value: str) -> list[int]:
    seeds = []
    for part in _parse_csv(value):
        seeds.append(int(part))
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def _parse_sides(value: str) -> list[int]:
    sides = [int(part) for part in _parse_csv(value)]
    if not sides or any(side not in (0, 1) for side in sides):
        raise argparse.ArgumentTypeError("sides must contain 0 and/or 1")
    return sides


def _safe_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    return label or "agent"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_DIR))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plain(value):
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _sum_nonnegative_values(value) -> int:
    if not isinstance(value, Mapping):
        return 0
    total = 0
    for item in value.values():
        try:
            total += max(0, int(item))
        except (TypeError, ValueError):
            continue
    return total


def _fallback(obs):
    try:
        player = int(obs.get("player", 0))
        hands = obs.get("farms", [])[player].get("hands", [])
        count = len(hands)
    except (AttributeError, IndexError, TypeError, ValueError):
        count = 0
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in range(count)],
        "market": [],
    }


def _load_agent(path: Path):
    raw = path.read_text(encoding="utf-8")
    namespace = {}
    exec(compile(raw, str(path), "exec"), namespace)
    callables = [value for value in namespace.values() if callable(value)]
    if not callables:
        raise RuntimeError(f"no callable found in {path}")
    return callables[-1], namespace


def _custom_opponent_path(label: str) -> Path | None:
    if not label.startswith("file:"):
        return None
    candidate = (PROJECT_DIR / label.removeprefix("file:")).resolve()
    try:
        candidate.relative_to(PROJECT_DIR)
    except ValueError as exc:
        raise ValueError(f"custom opponent escapes project directory: {label}") from exc
    return candidate


class TrackedAgent:
    def __init__(self, path: Path, max_market_orders: int):
        self.agent, self.namespace = _load_agent(path)
        reset = self.namespace.get("reset_runtime_state")
        if callable(reset):
            reset()
        self.max_market_orders = max_market_orders
        self.calls = 0
        self.shape_invalid_actions = 0
        self.wrapper_exceptions = 0
        self.total_seconds = 0.0
        self.max_seconds = 0.0
        self.farmer_ops = Counter()
        self.hand_ops = Counter()
        self.market_orders = 0
        self.hire_orders = 0
        self.max_hands_observed = 0
        self.hand_turns = 0
        self.unit_tile_action_conflicts = 0
        self.plant_to_weed_transitions = 0
        self.previous_tiles = None
        self.unique_plant_tiles = set()
        self.maturity_started_at = {}
        self.mature_wait_steps = []
        self.crop_plant_actions = Counter()
        self.crop_harvest_actions = Counter()
        self.crop_tile_turns = Counter()
        self.sell_units = 0
        self.realized_sale_revenue = 0.0
        self.peak_shed_total = 0
        self.minimum_cash = float("inf")
        self.funding_shortfall_orders = 0
        self.previous_money = None
        self.pending_market_cost = 0.0
        self.pending_sell_units = 0
        self.validation_errors = []
        self.exception_messages = []

    def __call__(self, obs, configuration=None):
        self.calls += 1
        self._observe_plant_transitions(obs)
        self._observe_economics(obs)
        try:
            player = int(obs.get("player", 0))
            hand_count = len(obs.get("farms", [])[player].get("hands", []))
        except (AttributeError, IndexError, TypeError, ValueError):
            hand_count = 0
        self.max_hands_observed = max(self.max_hands_observed, hand_count)
        self.hand_turns += hand_count
        started = time.perf_counter()
        try:
            action = self.agent(obs)
        except Exception as exc:
            self.wrapper_exceptions += 1
            self.exception_messages.append(
                f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            )
            action = _fallback(obs)
        duration = time.perf_counter() - started
        self.total_seconds += duration
        self.max_seconds = max(self.max_seconds, duration)

        errors = validate_action(action, obs, self.max_market_orders)
        if errors:
            self.shape_invalid_actions += 1
            self.validation_errors.extend(errors)
            action = _fallback(obs)

        self.unit_tile_action_conflicts += self._count_unit_conflicts(obs, action)

        farmer = action.get("farmer", ["UNKNOWN"])
        farmer_op = farmer[0] if farmer else "UNKNOWN"
        self.farmer_ops[str(farmer_op)] += 1
        for hand in action.get("hands", []):
            hand_op = hand[0] if hand else "UNKNOWN"
            self.hand_ops[str(hand_op)] += 1
        self.market_orders += len(action.get("market", []))
        self.hire_orders += sum(
            isinstance(order, list) and bool(order) and order[0] == "HIRE"
            for order in action.get("market", [])
        )
        self._record_economics(obs, action)
        return action

    @staticmethod
    def _fib(index: int) -> int:
        a, b = 1, 1
        for _ in range(max(0, index)):
            a, b = b, a + b
        return a

    def _observe_economics(self, obs):
        try:
            player = int(obs.get("player", 0))
            farm = obs.get("farms", [])[player]
            money = float(farm.get("money", 0))
            private = obs.get("private", {}) or {}
            shed = private.get("shed", {}) or {}
            tiles = farm.get("tiles", [])
        except (AttributeError, IndexError, TypeError, ValueError):
            return
        self.minimum_cash = min(self.minimum_cash, money)
        self.peak_shed_total = max(self.peak_shed_total, _sum_nonnegative_values(shed))
        for row in tiles:
            if not isinstance(row, (list, tuple)):
                continue
            for tile in row:
                if isinstance(tile, Mapping) and tile.get("kind") == "PLANT":
                    self.crop_tile_turns[str(tile.get("crop", "UNKNOWN"))] += 1
        if self.previous_money is not None and self.pending_sell_units > 0:
            revenue = money - self.previous_money + self.pending_market_cost
            self.realized_sale_revenue += max(0.0, revenue)
        self.previous_money = money
        self.pending_market_cost = 0.0
        self.pending_sell_units = 0

    def _record_economics(self, obs, action):
        try:
            player = int(obs.get("player", 0))
            farm = obs.get("farms", [])[player]
            positions = [farm.get("farmer"), *farm.get("hands", [])]
            unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
            tiles = farm.get("tiles", [])
            budget = float(farm.get("money", 0))
            hires_today = int(farm.get("hires_today", 0))
            prices = (obs.get("market", {}) or {}).get("prices", {}) or {}
        except (AttributeError, IndexError, TypeError, ValueError):
            return

        for position, unit_action in zip(positions, unit_actions):
            if not isinstance(unit_action, list) or not unit_action:
                continue
            if unit_action[0] == "PLANT" and len(unit_action) >= 2:
                self.crop_plant_actions[str(unit_action[1])] += 1
            elif (
                unit_action[0] == "HARVEST"
                and isinstance(position, (list, tuple))
                and len(position) >= 2
            ):
                x, y = int(position[0]), int(position[1])
                if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]):
                    tile = tiles[y][x]
                    if isinstance(tile, Mapping) and tile.get("kind") == "PLANT":
                        self.crop_harvest_actions[str(tile.get("crop", "UNKNOWN"))] += 1

        seed_costs = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
        for order in action.get("market", []):
            if not isinstance(order, list) or not order:
                continue
            op = order[0]
            if op == "HIRE":
                cost = float(self._fib(hires_today))
                hires_today += 1
                if budget < cost:
                    self.funding_shortfall_orders += 1
                else:
                    budget -= cost
                    self.pending_market_cost += cost
            elif op == "BUY_SEED" and len(order) >= 3:
                crop = str(order[1])
                quantity = max(0, int(order[2]))
                unit_cost = float(seed_costs.get(crop, 0))
                affordable = quantity if unit_cost <= 0 else min(quantity, int(budget // unit_cost))
                if affordable < quantity:
                    self.funding_shortfall_orders += 1
                cost = affordable * unit_cost
                budget -= cost
                self.pending_market_cost += cost
            elif op == "SELL" and len(order) >= 3:
                quantity = max(0, int(order[2]))
                self.sell_units += quantity
                self.pending_sell_units += quantity
                budget += quantity * float(prices.get(str(order[1]), 0) or 0)

    def finalize(self, obs):
        """Consume the terminal observation that is not followed by another agent call."""
        self._observe_plant_transitions(obs)
        self._observe_economics(obs)

    @staticmethod
    def _count_unit_conflicts(obs, action) -> int:
        tile_ops = {"PLANT", "WATER", "HARVEST", "DIG", "BUILD_COOP", "BUILD_PASTURE"}
        try:
            player = int(obs.get("player", 0))
            farm = obs.get("farms", [])[player]
            positions = [farm.get("farmer"), *farm.get("hands", [])]
            actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        except (AttributeError, IndexError, TypeError, ValueError):
            return 0
        occupied = Counter()
        for position, unit_action in zip(positions, actions):
            if (
                isinstance(position, (list, tuple))
                and len(position) >= 2
                and isinstance(unit_action, list)
                and unit_action
                and unit_action[0] in tile_ops
            ):
                occupied[(int(position[0]), int(position[1]))] += 1
        return sum(max(0, count - 1) for count in occupied.values())

    def _observe_plant_transitions(self, obs):
        try:
            player = int(obs.get("player", 0))
            tiles = obs.get("farms", [])[player].get("tiles", [])
            step = int(obs.get("step", 0))
            day = int(obs.get("day", 0))
            snapshot = [
                [
                    tile.get("kind") if isinstance(tile, Mapping) else tile
                    for tile in row
                ]
                for row in tiles
            ]
        except (AttributeError, IndexError, TypeError, ValueError):
            return
        if self.previous_tiles is not None:
            for y, (previous_row, current_row) in enumerate(
                zip(self.previous_tiles, snapshot)
            ):
                for x, (previous, current) in enumerate(zip(previous_row, current_row)):
                    position = (x, y)
                    if previous == "PLANT" and current == "WEED":
                        self.plant_to_weed_transitions += 1
                        self.maturity_started_at.pop(position, None)
                    elif previous == "PLANT" and current != "PLANT":
                        matured_at = self.maturity_started_at.pop(position, None)
                        if matured_at is not None:
                            self.mature_wait_steps.append(max(0, step - matured_at))
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if not isinstance(tile, Mapping) or tile.get("kind") != "PLANT":
                    continue
                position = (x, y)
                self.unique_plant_tiles.add(position)
                crop = tile.get("crop")
                mature_day = {"WHEAT": 4, "CARROT": 3}.get(crop)
                if mature_day is not None and day - int(tile.get("planted_day", day)) >= mature_day:
                    self.maturity_started_at.setdefault(position, step)
        self.previous_tiles = snapshot

    def internal_exceptions(self) -> int:
        getter = self.namespace.get("get_runtime_stats")
        if not callable(getter):
            return 0
        try:
            return int(getter().get("exceptions", 0))
        except (AttributeError, TypeError, ValueError):
            return 0


def _empty_result(run_index: int, seed: int, opponent: str, side: int) -> dict:
    row = {field: None for field in RESULT_FIELDS}
    row.update(
        {
            "run_index": run_index,
            "seed_requested": seed,
            "opponent": opponent,
            "side": side,
            "episode_completed": False,
            "result": "ERROR",
            "shape_invalid_actions": 0,
            "wrapper_exceptions": 0,
            "agent_internal_exceptions": 0,
            "runner_error": "",
        }
    )
    return row


def _run_episode(make, agent_path: Path, run_index: int, seed: int, opponent: str, side: int):
    row = _empty_result(run_index, seed, opponent, side)
    started = time.perf_counter()
    try:
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        expected_steps = int(env.configuration.episodeSteps)
        market_order_cap = int(env.configuration.maxMarketOrdersPerTurn)
        tracker = TrackedAgent(agent_path, market_order_cap)
        opponent_path = _custom_opponent_path(opponent)
        opponent_agent = (
            TrackedAgent(opponent_path, market_order_cap) if opponent_path else opponent
        )
        agents = [tracker, opponent_agent] if side == 0 else [opponent_agent, tracker]
        env.run(agents)

        final_states = env.steps[-1]
        statuses = [str(state.status) for state in final_states]
        observation = final_states[side].observation
        tracker.finalize(observation)
        farms = observation.get("farms", [])
        our_farm = farms[side]
        our_cash = float(our_farm.get("money", 0))
        opponent_cash = float(farms[1 - side].get("money", 0))
        private = observation.get("private", {}) or {}
        final_seeds = private.get("seeds", {}) or {}
        final_shed = private.get("shed", {}) or {}
        final_inventories = private.get("inventories", []) or []
        final_day = int(observation.get("day", 0))
        final_tiles = [
            tile
            for row_tiles in our_farm.get("tiles", [])
            if isinstance(row_tiles, (list, tuple))
            for tile in row_tiles
            if isinstance(tile, Mapping)
        ]
        final_plants = [tile for tile in final_tiles if tile.get("kind") == "PLANT"]
        final_immature_wheat = [
            tile
            for tile in final_plants
            if tile.get("crop") == "WHEAT"
            and final_day - int(tile.get("planted_day", final_day)) < 4
        ]
        result = "WIN" if our_cash > opponent_cash else "LOSS" if our_cash < opponent_cash else "DRAW"
        completed = len(env.steps) == expected_steps and all(status == "DONE" for status in statuses)
        turns_per_day = int(env.configuration.turnsPerDay)
        wheat_land_days = tracker.crop_tile_turns.get("WHEAT", 0) / turns_per_day
        carrot_land_days = tracker.crop_tile_turns.get("CARROT", 0) / turns_per_day
        total_land_days = wheat_land_days + carrot_land_days
        total_nonpass_actions = (
            tracker.calls
            - tracker.farmer_ops.get("PASS", 0)
            + sum(count for op, count in tracker.hand_ops.items() if op != "PASS")
        )

        row.update(
            {
                "seed_resolved": env.info.get("seed", "unavailable"),
                "recorded_steps": len(env.steps),
                "expected_steps": expected_steps,
                "our_status": statuses[side],
                "opponent_status": statuses[1 - side],
                "our_cash": our_cash,
                "opponent_cash": opponent_cash,
                "cash_delta": our_cash - opponent_cash,
                "result": result,
                "episode_completed": completed,
                "agent_calls": tracker.calls,
                "shape_invalid_actions": tracker.shape_invalid_actions,
                "wrapper_exceptions": tracker.wrapper_exceptions,
                "agent_internal_exceptions": tracker.internal_exceptions(),
                "total_agent_seconds": round(tracker.total_seconds, 6),
                "max_agent_seconds": round(tracker.max_seconds, 6),
                "episode_seconds": round(time.perf_counter() - started, 6),
                "farmer_pass_actions": tracker.farmer_ops.get("PASS", 0),
                "farmer_nonpass_actions": tracker.calls - tracker.farmer_ops.get("PASS", 0),
                "farmer_harvest_actions": tracker.farmer_ops.get("HARVEST", 0),
                "hand_pass_actions": tracker.hand_ops.get("PASS", 0),
                "hand_nonpass_actions": sum(
                    count for op, count in tracker.hand_ops.items() if op != "PASS"
                ),
                "hand_move_actions": sum(
                    tracker.hand_ops.get(op, 0) for op in ("NORTH", "SOUTH", "EAST", "WEST")
                ),
                "hand_water_actions": tracker.hand_ops.get("WATER", 0),
                "hand_harvest_actions": tracker.hand_ops.get("HARVEST", 0),
                "hand_plant_actions": tracker.hand_ops.get("PLANT", 0),
                "market_orders": tracker.market_orders,
                "hire_orders": tracker.hire_orders,
                "max_hands_observed": tracker.max_hands_observed,
                "hand_turns": tracker.hand_turns,
                "unit_tile_action_conflicts": tracker.unit_tile_action_conflicts,
                "plant_to_weed_transitions": tracker.plant_to_weed_transitions,
                "wheat_plant_actions": tracker.crop_plant_actions.get("WHEAT", 0),
                "carrot_plant_actions": tracker.crop_plant_actions.get("CARROT", 0),
                "wheat_harvest_actions": tracker.crop_harvest_actions.get("WHEAT", 0),
                "carrot_harvest_actions": tracker.crop_harvest_actions.get("CARROT", 0),
                "wheat_land_days": round(wheat_land_days, 3),
                "carrot_land_days": round(carrot_land_days, 3),
                "sell_units": tracker.sell_units,
                "realized_sale_revenue": round(tracker.realized_sale_revenue, 3),
                "realized_average_sale_price": round(
                    tracker.realized_sale_revenue / tracker.sell_units, 3
                )
                if tracker.sell_units
                else 0,
                "revenue_per_land_day": round(
                    tracker.realized_sale_revenue / total_land_days, 3
                )
                if total_land_days
                else 0,
                "revenue_per_nonpass_unit_action": round(
                    tracker.realized_sale_revenue / total_nonpass_actions, 3
                )
                if total_nonpass_actions
                else 0,
                "peak_shed_total": tracker.peak_shed_total,
                "minimum_cash": tracker.minimum_cash
                if tracker.minimum_cash != float("inf")
                else None,
                "funding_shortfall_orders": tracker.funding_shortfall_orders,
                "unique_plant_tiles_used": len(tracker.unique_plant_tiles),
                "median_mature_wait_steps": statistics.median(tracker.mature_wait_steps)
                if tracker.mature_wait_steps
                else 0,
                "max_mature_wait_steps": max(tracker.mature_wait_steps, default=0),
                "unharvested_mature_tiles": len(tracker.maturity_started_at),
                "final_seed_total": _sum_nonnegative_values(final_seeds),
                "final_wheat_seeds": int(final_seeds.get("WHEAT", 0) or 0),
                "final_shed_total": _sum_nonnegative_values(final_shed),
                "final_wheat_shed": int(final_shed.get("WHEAT", 0) or 0),
                "final_carried_total": sum(
                    _sum_nonnegative_values(inventory) for inventory in final_inventories
                ),
                "final_plant_tiles": len(final_plants),
                "final_immature_wheat_tiles": len(final_immature_wheat),
                "runner_error": " | ".join(
                    tracker.exception_messages + tracker.validation_errors
                ),
            }
        )
    except Exception as exc:
        row["episode_seconds"] = round(time.perf_counter() - started, 6)
        row["runner_error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    return row


def _write_csv(path: Path, rows: list[dict]):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, metadata: dict, rows: list[dict]):
    payload = {"metadata": metadata, "episodes": rows}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _aggregate(rows: list[dict]) -> dict:
    completed = [row for row in rows if row["episode_completed"]]
    cash = [float(row["our_cash"]) for row in completed]
    deltas = [float(row["cash_delta"]) for row in completed]
    final_seed_totals = [int(row["final_seed_total"] or 0) for row in completed]
    final_shed_totals = [int(row["final_shed_total"] or 0) for row in completed]
    final_carried_totals = [int(row["final_carried_total"] or 0) for row in completed]
    final_plant_tiles = [int(row["final_plant_tiles"] or 0) for row in completed]
    final_immature_wheat = [
        int(row["final_immature_wheat_tiles"] or 0) for row in completed
    ]
    unique_plant_tiles = [int(row["unique_plant_tiles_used"] or 0) for row in completed]
    harvest_actions = [int(row["farmer_harvest_actions"] or 0) for row in completed]
    mature_wait = [float(row["median_mature_wait_steps"] or 0) for row in completed]
    sale_revenue = [float(row["realized_sale_revenue"] or 0) for row in completed]
    average_sale_price = [float(row["realized_average_sale_price"] or 0) for row in completed]
    revenue_per_land_day = [float(row["revenue_per_land_day"] or 0) for row in completed]
    revenue_per_action = [
        float(row["revenue_per_nonpass_unit_action"] or 0) for row in completed
    ]
    peak_shed = [int(row["peak_shed_total"] or 0) for row in completed]
    minimum_cash = [float(row["minimum_cash"] or 0) for row in completed]
    return {
        "episodes": len(rows),
        "completed": len(completed),
        "wins": sum(row["result"] == "WIN" for row in completed),
        "draws": sum(row["result"] == "DRAW" for row in completed),
        "losses": sum(row["result"] == "LOSS" for row in completed),
        "win_rate": (sum(row["result"] == "WIN" for row in completed) / len(completed))
        if completed
        else 0.0,
        "median_cash": statistics.median(cash) if cash else None,
        "worst_cash": min(cash) if cash else None,
        "best_cash": max(cash) if cash else None,
        "median_cash_delta": statistics.median(deltas) if deltas else None,
        "worst_cash_delta": min(deltas) if deltas else None,
        "median_final_seed_total": statistics.median(final_seed_totals)
        if final_seed_totals
        else None,
        "max_final_seed_total": max(final_seed_totals, default=0),
        "median_final_shed_total": statistics.median(final_shed_totals)
        if final_shed_totals
        else None,
        "max_final_shed_total": max(final_shed_totals, default=0),
        "median_final_carried_total": statistics.median(final_carried_totals)
        if final_carried_totals
        else None,
        "max_final_carried_total": max(final_carried_totals, default=0),
        "median_final_plant_tiles": statistics.median(final_plant_tiles)
        if final_plant_tiles
        else None,
        "max_final_plant_tiles": max(final_plant_tiles, default=0),
        "max_final_immature_wheat_tiles": max(final_immature_wheat, default=0),
        "median_unique_plant_tiles": statistics.median(unique_plant_tiles)
        if unique_plant_tiles
        else None,
        "median_harvest_actions": statistics.median(harvest_actions)
        if harvest_actions
        else None,
        "median_mature_wait_steps": statistics.median(mature_wait)
        if mature_wait
        else None,
        "max_mature_wait_steps": max(
            (float(row["max_mature_wait_steps"] or 0) for row in completed), default=0
        ),
        "unharvested_mature_tiles": sum(
            int(row["unharvested_mature_tiles"] or 0) for row in completed
        ),
        "shape_invalid_actions": sum(int(row["shape_invalid_actions"] or 0) for row in rows),
        "wrapper_exceptions": sum(int(row["wrapper_exceptions"] or 0) for row in rows),
        "agent_internal_exceptions": sum(
            int(row["agent_internal_exceptions"] or 0) for row in rows
        ),
        "runner_errors": sum(bool(row["runner_error"]) for row in rows),
        "plant_to_weed_transitions": sum(
            int(row["plant_to_weed_transitions"] or 0) for row in rows
        ),
        "unit_tile_action_conflicts": sum(
            int(row["unit_tile_action_conflicts"] or 0) for row in rows
        ),
        "funding_shortfall_orders": sum(
            int(row["funding_shortfall_orders"] or 0) for row in rows
        ),
        "median_sale_revenue": statistics.median(sale_revenue) if sale_revenue else None,
        "median_realized_average_sale_price": statistics.median(average_sale_price)
        if average_sale_price
        else None,
        "median_revenue_per_land_day": statistics.median(revenue_per_land_day)
        if revenue_per_land_day
        else None,
        "median_revenue_per_nonpass_unit_action": statistics.median(revenue_per_action)
        if revenue_per_action
        else None,
        "median_peak_shed_total": statistics.median(peak_shed) if peak_shed else None,
        "max_peak_shed_total": max(peak_shed, default=0),
        "worst_minimum_cash": min(minimum_cash) if minimum_cash else None,
        "hire_orders": sum(int(row["hire_orders"] or 0) for row in rows),
        "hand_nonpass_actions": sum(int(row["hand_nonpass_actions"] or 0) for row in rows),
        "max_agent_seconds": max(
            (float(row["max_agent_seconds"] or 0) for row in rows), default=0.0
        ),
    }


def _fmt(value):
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _write_summary(path: Path, metadata: dict, rows: list[dict]):
    overall = _aggregate(rows)
    groups = []
    for opponent in metadata["opponents"]:
        for side in metadata["sides"]:
            selected = [
                row for row in rows if row["opponent"] == opponent and row["side"] == side
            ]
            groups.append((opponent, side, _aggregate(selected)))

    gate_pass = (
        overall["completed"] == overall["episodes"]
        and overall["shape_invalid_actions"] == 0
        and overall["wrapper_exceptions"] == 0
        and overall["agent_internal_exceptions"] == 0
        and overall["runner_errors"] == 0
        and overall["plant_to_weed_transitions"] == 0
        and overall["unit_tile_action_conflicts"] == 0
        and overall["funding_shortfall_orders"] == 0
        and overall["max_final_shed_total"] == 0
        and overall["max_final_carried_total"] == 0
        and overall["max_final_plant_tiles"] == 0
        and overall["unharvested_mature_tiles"] == 0
    )
    lines = [
        f"# Benchmark Summary: {metadata['label']}",
        "",
        f"- Generated: `{metadata['generated_at_utc']}`",
        f"- Agent: `{metadata['agent_path']}`",
        f"- SHA256: `{metadata['agent_sha256']}`",
        f"- Python: `{metadata['python']}`",
        f"- kaggle-environments: `{metadata['kaggle_environments']}`",
        f"- Seeds: `{metadata['seeds']}`",
        f"- Opponents: `{metadata['opponents']}`",
        f"- Sides: `{metadata['sides']}`",
        "",
        "## Gate",
        "",
        f"**{'PASS' if gate_pass else 'FAIL'}**",
        "",
        f"- Completed: `{overall['completed']}/{overall['episodes']}`",
        f"- Shape-invalid actions: `{overall['shape_invalid_actions']}`",
        f"- Wrapper exceptions: `{overall['wrapper_exceptions']}`",
        f"- Agent internal exceptions: `{overall['agent_internal_exceptions']}`",
        f"- Runner errors: `{overall['runner_errors']}`",
        f"- Plant-to-weed transitions: `{overall['plant_to_weed_transitions']}`",
        f"- Unit tile-action conflicts: `{overall['unit_tile_action_conflicts']}`",
        f"- Funding shortfall orders: `{overall['funding_shortfall_orders']}`",
        f"- Hire orders: `{overall['hire_orders']}`",
        f"- Hand non-PASS actions: `{overall['hand_nonpass_actions']}`",
        f"- Slowest agent call: `{overall['max_agent_seconds'] * 1000:.3f} ms`",
        "",
        "## Overall",
        "",
        f"- Wins / draws / losses: `{overall['wins']} / {overall['draws']} / {overall['losses']}`",
        f"- Win rate: `{overall['win_rate']:.1%}`",
        f"- Median cash: `{_fmt(overall['median_cash'])}`",
        f"- Worst cash: `{_fmt(overall['worst_cash'])}`",
        f"- Best cash: `{_fmt(overall['best_cash'])}`",
        f"- Median cash delta: `{_fmt(overall['median_cash_delta'])}`",
        f"- Worst cash delta: `{_fmt(overall['worst_cash_delta'])}`",
        f"- Median realized sale revenue: `{_fmt(overall['median_sale_revenue'])}`",
        f"- Median realized average sale price: `{_fmt(overall['median_realized_average_sale_price'])}`",
        f"- Median revenue per land-day: `{_fmt(overall['median_revenue_per_land_day'])}`",
        f"- Median revenue per non-PASS unit action: `{_fmt(overall['median_revenue_per_nonpass_unit_action'])}`",
        f"- Median / max peak shed items: `{_fmt(overall['median_peak_shed_total'])} / {overall['max_peak_shed_total']}`",
        f"- Worst minimum cash: `{_fmt(overall['worst_minimum_cash'])}`",
        "",
        "## End state",
        "",
        f"- Median / max unused seeds: `{_fmt(overall['median_final_seed_total'])} / {overall['max_final_seed_total']}`",
        f"- Median / max unsold shed items: `{_fmt(overall['median_final_shed_total'])} / {overall['max_final_shed_total']}`",
        f"- Median / max carried items: `{_fmt(overall['median_final_carried_total'])} / {overall['max_final_carried_total']}`",
        f"- Median / max remaining plant tiles: `{_fmt(overall['median_final_plant_tiles'])} / {overall['max_final_plant_tiles']}`",
        f"- Max immature wheat tiles: `{overall['max_final_immature_wheat_tiles']}`",
        f"- Median unique plant tiles used: `{_fmt(overall['median_unique_plant_tiles'])}`",
        f"- Median harvest actions: `{_fmt(overall['median_harvest_actions'])}`",
        f"- Median mature wait: `{_fmt(overall['median_mature_wait_steps'])} steps`",
        f"- Max mature wait: `{_fmt(overall['max_mature_wait_steps'])} steps`",
        f"- Unharvested mature tiles: `{overall['unharvested_mature_tiles']}`",
        "",
        "## By opponent and side",
        "",
        "| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for opponent, side, stats in groups:
        lines.append(
            "| "
            + " | ".join(
                [
                    opponent,
                    str(side),
                    f"{stats['completed']}/{stats['episodes']}",
                    f"{stats['wins']}-{stats['draws']}-{stats['losses']}",
                    f"{stats['win_rate']:.1%}",
                    _fmt(stats["median_cash"]),
                    _fmt(stats["worst_cash"]),
                    _fmt(stats["median_cash_delta"]),
                    _fmt(stats["worst_cash_delta"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This is a local engineering benchmark. It verifies completion, stability,",
            "and paired behavior against fixed built-in opponents. It does not estimate",
            "or predict the live Kaggle skill rating.",
            "The built-in `random` opponent can vary across reruns even with the same",
            "environment seed. Use `pass` and `starter` for exact deterministic regression,",
            "and use `random` only as a repeated stochastic robustness probe.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return gate_pass, overall


def _save(output_dir: Path, metadata: dict, rows: list[dict]):
    _write_csv(output_dir / "episodes.csv", rows)
    _write_json(output_dir / "episodes.json", metadata, rows)
    return _write_summary(output_dir / "summary.md", metadata, rows)


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", default="main.py", help="submission-style Python file")
    parser.add_argument("--label", default="v0", help="short run label")
    parser.add_argument(
        "--seeds",
        type=_parse_seeds,
        default=list(DEFAULT_SEEDS),
        help="comma-separated integer seeds",
    )
    parser.add_argument(
        "--opponents",
        type=_parse_csv,
        default=list(DEFAULT_OPPONENTS),
        help="comma-separated built-in opponents",
    )
    parser.add_argument(
        "--sides",
        type=_parse_sides,
        default=list(DEFAULT_SIDES),
        help="comma-separated player sides, default 0,1",
    )
    parser.add_argument("--output-dir", help="explicit output directory")
    return parser


def main():
    args = _build_parser().parse_args()
    agent_path = (PROJECT_DIR / args.agent).resolve()
    if not agent_path.is_file():
        raise SystemExit(f"agent file not found: {agent_path}")

    from kaggle_environments import __version__ as kaggle_env_version
    from kaggle_environments import environments, make

    available = environments.get("kaggriculture", {}).get("agents", {})
    missing = []
    for opponent in args.opponents:
        opponent_path = _custom_opponent_path(opponent)
        if opponent_path is not None:
            if not opponent_path.is_file():
                missing.append(opponent)
        elif opponent not in available:
            missing.append(opponent)
    if missing:
        raise SystemExit(f"unknown built-in opponents: {missing}; available={sorted(available)}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = _safe_label(args.label)
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else PROJECT_DIR / "benchmarks" / "runs" / f"{timestamp}_{label}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    metadata = {
        "label": label,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent_path": str(agent_path.relative_to(PROJECT_DIR)),
        "agent_sha256": _sha256(agent_path),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "kaggle_environments": kaggle_env_version,
        "seeds": list(args.seeds),
        "opponents": list(args.opponents),
        "sides": list(args.sides),
    }

    rows = []
    total = len(args.seeds) * len(args.opponents) * len(args.sides)
    for seed in args.seeds:
        for opponent in args.opponents:
            for side in args.sides:
                run_index = len(rows) + 1
                row = _run_episode(make, agent_path, run_index, seed, opponent, side)
                rows.append(row)
                _save(output_dir, metadata, rows)
                print(
                    f"[{run_index:02d}/{total}] seed={seed} opponent={opponent} "
                    f"side={side} status={row['our_status']} result={row['result']} "
                    f"cash={row['our_cash']} error={'yes' if row['runner_error'] else 'no'}",
                    flush=True,
                )

    gate_pass, overall = _save(output_dir, metadata, rows)
    print(f"output_dir={_display_path(output_dir)}")
    print(f"completed={overall['completed']}/{overall['episodes']}")
    print(f"gate={'PASS' if gate_pass else 'FAIL'}")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
