#!/usr/bin/env python3
"""Summarize public Kaggriculture replay JSON files for failure analysis."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


SNAPSHOT_STEPS = (71, 167, 359, 551, 719)
MILK_SUPPORT = {"PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"}


def route_from_shops(shops: list[str]) -> str:
    if shops[:1] == ["YARN_STORE"]:
        return "6c12s_4q_first_yarn"
    if "YARN_STORE" in shops[:2]:
        return "6c12s_4q_second_yarn"
    if "YARN_STORE" in shops[:3]:
        return "6c8s_3q"
    if MILK_SUPPORT.intersection(shops[:3]):
        return "10c4s_3q"
    return "8c6s_3q"


def tile_counts(farm: dict) -> dict:
    crops: Counter[str] = Counter()
    animals: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    ready_yield: Counter[str] = Counter()
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind"):
                kinds[str(tile["kind"])] += 1
            if tile.get("crop"):
                crop = str(tile["crop"])
                crops[crop] += 1
                ready_yield[crop] += max(0, int(tile.get("yield_units", 0) or 0))
            if tile.get("animal"):
                animals[str(tile["animal"])] += 1
    return {
        "crops": dict(sorted(crops.items())),
        "animals": dict(sorted(animals.items())),
        "kinds": dict(sorted(kinds.items())),
        "ready_yield": dict(sorted(ready_yield.items())),
    }


def own_observation(step: list[dict], seat: int) -> dict:
    observation = step[seat].get("observation") or {}
    return observation if isinstance(observation, dict) else {}


def player_snapshot(step: list[dict], seat: int) -> dict:
    observation = own_observation(step, seat)
    farms = observation.get("farms", []) or []
    farm = farms[seat] if seat < len(farms) else {}
    private = observation.get("private", {}) or {}
    shed = private.get("shed", {}) or {}
    seeds = private.get("seeds", {}) or {}
    inventories = private.get("inventories", []) or []
    carried = Counter()
    for inventory in inventories:
        for item, quantity in (inventory or {}).items():
            carried[str(item)] += max(0, int(quantity or 0))
    return {
        "money": float(farm.get("money", 0) or 0),
        "hands": len(farm.get("hands", []) or []),
        "quadrants": list(farm.get("unlocked_quadrants", []) or []),
        "tiles": tile_counts(farm),
        "shed": {str(k): int(v or 0) for k, v in shed.items() if int(v or 0)},
        "carried": dict(sorted(carried.items())),
        "seeds": {str(k): int(v or 0) for k, v in seeds.items() if int(v or 0)},
    }


def action_summary(steps: list[list[dict]], seat: int) -> dict:
    worker_actions: Counter[str] = Counter()
    market_actions: Counter[str] = Counter()
    sells: Counter[str] = Counter()
    buys: Counter[str] = Counter()
    sale_steps: Counter[str] = Counter()
    for step in steps:
        action = step[seat].get("action") or {}
        if not isinstance(action, dict):
            continue
        worker_orders = [action.get("farmer", ["PASS"]), *(action.get("hands", []) or [])]
        for order in worker_orders:
            if isinstance(order, (list, tuple)) and order:
                worker_actions[str(order[0])] += 1
        sold_this_step: set[str] = set()
        for order in action.get("market", []) or []:
            if not isinstance(order, (list, tuple)) or not order:
                continue
            kind = str(order[0])
            market_actions[kind] += 1
            if len(order) < 3:
                continue
            item = str(order[1])
            quantity = max(0, int(order[2] or 0))
            if kind == "SELL":
                sells[item] += quantity
                sold_this_step.add(item)
            elif kind.startswith("BUY"):
                buys[item] += quantity
        for item in sold_this_step:
            sale_steps[item] += 1
    return {
        "worker_actions": dict(sorted(worker_actions.items())),
        "market_actions": dict(sorted(market_actions.items())),
        "requested_sells": dict(sorted(sells.items())),
        "requested_buys": dict(sorted(buys.items())),
        "sale_steps": dict(sorted(sale_steps.items())),
    }


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def similarity(steps: list[list[dict]]) -> dict:
    exact = market = workers = 0
    comparable = 0
    for step in steps:
        if len(step) < 2:
            continue
        a = step[0].get("action") or {}
        b = step[1].get("action") or {}
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        comparable += 1
        exact += canonical(a) == canonical(b)
        market += canonical(a.get("market", [])) == canonical(b.get("market", []))
        aw = [a.get("farmer", ["PASS"]), *(a.get("hands", []) or [])]
        bw = [b.get("farmer", ["PASS"]), *(b.get("hands", []) or [])]
        workers += canonical(aw) == canonical(bw)
    denominator = max(1, comparable)
    return {
        "comparable_steps": comparable,
        "exact_action_fraction": round(exact / denominator, 4),
        "market_action_fraction": round(market / denominator, 4),
        "worker_action_fraction": round(workers / denominator, 4),
    }


def summarize(path: Path, player_name: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    steps = data.get("steps", []) or []
    names = list((data.get("info", {}) or {}).get("TeamNames", []) or [])
    if player_name not in names:
        raise ValueError(f"{player_name!r} not found in {path}: {names}")
    our_seat = names.index(player_name)
    opponent_seat = 1 - our_seat
    rewards = [float(value or 0) for value in data.get("rewards", [])]
    final_observation = own_observation(steps[-1], our_seat)
    shops = list(((final_observation.get("town", {}) or {}).get("unlocked_shops", []) or []))
    our_reward = rewards[our_seat]
    opponent_reward = rewards[opponent_seat]
    if our_reward > opponent_reward:
        outcome = "win"
    elif our_reward < opponent_reward:
        outcome = "loss"
    else:
        outcome = "tie"
    snapshots = {}
    for index in SNAPSHOT_STEPS:
        if index >= len(steps):
            continue
        snapshots[str(index)] = {
            "ours": player_snapshot(steps[index], our_seat),
            "opponent": player_snapshot(steps[index], opponent_seat),
        }
    return {
        "episode_id": (data.get("info", {}) or {}).get("EpisodeId"),
        "game_uuid": data.get("id"),
        "seed": (data.get("info", {}) or {}).get("seed"),
        "names": names,
        "our_seat": our_seat,
        "opponent": names[opponent_seat],
        "outcome": outcome,
        "our_reward": our_reward,
        "opponent_reward": opponent_reward,
        "margin": our_reward - opponent_reward,
        "statuses": data.get("statuses"),
        "shops": shops,
        "candidate_route": route_from_shops(shops),
        "similarity": similarity(steps),
        "ours": action_summary(steps, our_seat),
        "opponent_actions": action_summary(steps, opponent_seat),
        "snapshots": snapshots,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--player", default="Mike chen666")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = [summarize(path, args.player) for path in args.paths]
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
