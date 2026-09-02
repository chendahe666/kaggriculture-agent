"""Print concise market-decision traces for one deterministic paired episode."""

from __future__ import annotations

import argparse
from pathlib import Path

from kaggle_environments import make


PROJECT_DIR = Path(__file__).resolve().parent


def _load_agent(path: Path):
    namespace = {}
    source = path.read_text(encoding="utf-8")
    exec(compile(source, str(path), "exec"), namespace)
    callables = [value for value in namespace.values() if callable(value)]
    if not callables:
        raise RuntimeError(f"no callable found in {path}")
    return callables[-1]


class MarketTrace:
    def __init__(self, label: str, path: Path):
        self.label = label
        self.agent = _load_agent(path)
        self.events = []
        self.last_signature = None

    def __call__(self, obs, configuration=None):
        action = self.agent(obs)
        private = obs.get("private", {}) or {}
        shed = private.get("shed", {}) or {}
        wheat = int(shed.get("WHEAT", 0) or 0)
        price = int(((obs.get("market", {}) or {}).get("prices", {}) or {}).get("WHEAT", 0) or 0)
        sells = [
            order
            for order in action.get("market", [])
            if isinstance(order, list) and order[:2] == ["SELL", "WHEAT"]
        ]
        signature = (price, wheat, bool(sells), sum(int(order[2]) for order in sells))
        if (wheat or sells) and signature != self.last_signature:
            farm = obs.get("farms", [])[int(obs.get("player", 0))]
            self.events.append(
                {
                    "step": int(obs.get("step", 0)),
                    "day": int(obs.get("day", 0)),
                    "hour": int(obs.get("hour", 0)),
                    "cash": int(farm.get("money", 0) or 0),
                    "wheat_price": price,
                    "shed_wheat": wheat,
                    "sold": signature[3],
                }
            )
            self.last_signature = signature
        return action


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--agent", default="main.py")
    parser.add_argument("--opponent", default="experiments/hands/hand1_6near_main.py")
    parser.add_argument("--side", type=int, choices=(0, 1), default=0)
    args = parser.parse_args()

    ours = MarketTrace("candidate", (PROJECT_DIR / args.agent).resolve())
    previous = MarketTrace("previous", (PROJECT_DIR / args.opponent).resolve())
    agents = [ours, previous] if args.side == 0 else [previous, ours]
    env = make("kaggriculture", configuration={"seed": args.seed}, debug=False)
    env.run(agents)

    final = env.steps[-1][args.side].observation
    farms = final.get("farms", [])
    print(
        f"seed={args.seed} side={args.side} "
        f"candidate_cash={farms[args.side].get('money')} "
        f"previous_cash={farms[1 - args.side].get('money')}"
    )
    for trace in (ours, previous):
        print(f"[{trace.label}]")
        for event in trace.events:
            decision = "SELL" if event["sold"] else "HOLD"
            print(
                f"step={event['step']:03d} day={event['day']:02d} "
                f"hour={event['hour']:02d} cash={event['cash']:4d} "
                f"price={event['wheat_price']:2d} shed={event['shed_wheat']:2d} "
                f"decision={decision} qty={event['sold']:2d}"
            )


if __name__ == "__main__":
    main()
