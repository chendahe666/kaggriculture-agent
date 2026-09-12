"""Read exactly 16 frozen P2 Arlene stress rows; no games or P3 result reads."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

LAB = Path(__file__).resolve().parents[1]
ROWS = LAB / "results/terminal-20260912/development"
ENGINE = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
RUNNER = "4518551bccfb2c2c39a30c928da6d0b16016eb3ee1b18b0dbcb95ec19d87054c"
OPPONENT = "d36ae976ad4a6316e6c1a27a5d04e9cc8e30300f21bdd31e749127c67a9311c4"
VARIANTS = {"baseline": "1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01",
            "depth2-timing-safe-file": "8d37e6f4683c5a8c399c74022211e77061a59600af6278e318c2958c9c6bfbd2"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add(mappings):
    total = Counter()
    for mapping in mappings:
        total.update(mapping)
    return dict(sorted(total.items()))


def player_metrics(row, seat):
    revenue = dict(row["sale_revenue"][seat])
    spending = dict(row["market_spending"][seat])
    cash = row["rewards"][seat]
    atomic = 3000 + sum(revenue.values()) - sum(spending.values()) - cash
    assert atomic >= 0
    return {"cash": cash, "sale_units": row["actual_sales"][seat], "sale_revenue": revenue,
            "unit_purchase_spending": spending, "floor_sale_units": row["floor_units"][seat],
            "sale_revenue_total": sum(revenue.values()), "unit_purchase_spending_total": sum(spending.values()),
            "hire_plus_land_cost_derived": atomic,
            "terminal_shed": row["final_after_market"]["shed"][seat],
            "terminal_cargo_totals": add(row["final_after_market"]["carried"][seat])}


def summarize(rows, side):
    metrics = [row[side] for row in rows]
    scalars = ("cash", "sale_revenue_total", "unit_purchase_spending_total", "hire_plus_land_cost_derived")
    maps = ("sale_units", "sale_revenue", "unit_purchase_spending", "floor_sale_units", "terminal_shed", "terminal_cargo_totals")
    return {"games": len(rows), "totals": {k: sum(row[k] for row in metrics) for k in scalars},
            "means": {k: statistics.mean(row[k] for row in metrics) for k in scalars},
            **{k: add(row[k] for row in metrics) for k in maps}}


def main():
    assert sha(LAB / "official/installed-1.32.7/kaggriculture.py") == ENGINE
    assert sha(LAB / "scripts/run_terminal_track.py") == RUNNER
    cases, input_hashes = [], {}
    for seed in range(91101, 91105):
        for seat in (0, 1):
            pair = {}
            for variant, candidate_hash in VARIANTS.items():
                path = ROWS / f"arlene-{seed}-{seat}-{variant}.json"
                row = json.loads(path.read_text(encoding="utf-8"))
                fixed = {"key": path.name, "seed": seed, "seat": seat, "variant": variant,
                         "candidate_sha256": candidate_hash, "opponent": "arlene", "opponent_sha256": OPPONENT,
                         "engine_sha256": ENGINE, "runner_sha256": RUNNER, "split": "development",
                         "evidence": "closed_loop", "entrypoint": "official_get_last_callable",
                         "family": "reconstructed_mixed_route"}
                assert all(row.get(k) == v for k, v in fixed.items()), path.name
                assert row["statuses"] == ["DONE", "DONE"] and row["frames"] == 720 and not row["errors"]
                assert row["margin"] == row["rewards"][seat] - row["rewards"][1 - seat]
                assert row["final_after_market"]["step"] == 718
                input_hashes[str(path.relative_to(LAB)).replace("\\", "/")] = sha(path)
                pair[variant] = {"own": player_metrics(row, seat), "arlene": player_metrics(row, 1 - seat),
                                 "margin": row["margin"], "shops": row["shops"],
                                 "preterminal_gameplay_sha256": row["terminal_start"]["gameplay_sha256"]}
            assert pair["baseline"]["shops"] == pair["depth2-timing-safe-file"]["shops"]
            assert pair["baseline"]["preterminal_gameplay_sha256"] == pair["depth2-timing-safe-file"]["preterminal_gameplay_sha256"]
            cases.append({"key": f"arlene-{seed}-{seat}", "seed": seed, "seat": seat, "variants": pair,
                          "terminal_patch_margin_effect": pair["depth2-timing-safe-file"]["margin"] - pair["baseline"]["margin"]})
    report = {"scope": "Exactly 16 pre-existing P2 closed-loop development stress games; no P3 result input.",
              "engine_sha256": ENGINE, "runner_sha256": RUNNER, "opponent_sha256": OPPONENT,
              "variant_sha256": VARIANTS, "script_sha256": sha(__file__), "input_sha256": input_hashes,
              "accounting_identity": "cash = 3000 + actual_sale_revenue - successful_unit_purchase_spending - derived_combined_HIRE_and_BUY_LAND_cost",
              "limits": ["No purchase-unit counts, harvested units, work-state trace or wage/land split are available from these summary rows.",
                         "Actual sales are not production: WHEAT and FERTILIZER are purchasable, and carried/discarded/consumed output is not sold output.",
                         "Cross-agent price/quantity differences are joint-policy outcomes, not causal effects of standalone order timing or farm composition."],
              "summaries": {variant: {side: summarize([case["variants"][variant] for case in cases], side)
                                      for side in ("own", "arlene")} for variant in VARIANTS},
              "mean_terminal_patch_margin_effect": statistics.mean(case["terminal_patch_margin_effect"] for case in cases),
              "cases": cases}
    output = LAB / "reports/p3-macro-prior-diagnostics.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "summaries": report["summaries"],
                      "mean_terminal_patch_margin_effect": report["mean_terminal_patch_margin_effect"]}))


if __name__ == "__main__":
    main()
