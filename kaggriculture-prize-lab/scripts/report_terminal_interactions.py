"""Read-only P2b factorial analysis; no policy imports or game execution.

The only generated artifact is an aggregate report. Missing, malformed, or
contradictory evidence fails before writing it. Historical runner revisions are
explicitly pinned: an expected schema-only revision is not a hash contradiction.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import sys

LAB = Path(__file__).resolve().parents[1]
TRACK = LAB / "experiments/track-terminal-20260912"
RESULTS = LAB / "results/terminal-20260912"
OPPONENTS = ("cok", "seyam", "lonespear", "deepesh", "maverick")
SEEDS = (91101, 91102, 91103, 91104)
VARIANTS = {"base": "baseline", "A": "depth2-file", "B": "timing-file",
            "AB": "depth2-timing-file"}
HASHES = {
    "base": "1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01",
    "A": "c06dc267e07ce5b07e8bf5380104dc3c87efbbbcdaf72386677ba31e7bb55624",
    "B": "6509cee22521b47a0e4f33b923dd48d4740f9864c5c79a01296b6d3cb0cc10fb",
    "AB": "de4f002b5bd990728b8d31d3ea47a0788d5dbb20a9cf3edf92239e7aabe1e6cd",
}
ENGINE_HASH = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
RUNNER_OLD = "1205a7ef72285e7e93caf05d84fbb635ebdce8a1c2046bea1a96c7d92f1e44c9"
RUNNER_FILE = "2ce7669a5bf00f186f39481505db37cbae56c55d2f21df0c75150695302bc502"
RUNNER_TIMING = "51ae5e2c6197afb680a0e4ee5d60b0bdfe3d1939d22dc163815b8676ec9a6c35"
RUNNERS = {"base": {RUNNER_OLD, RUNNER_FILE}, "A": {RUNNER_FILE},
           "B": {RUNNER_TIMING}, "AB": {RUNNER_TIMING}}
STARTING_MONEY = 3000
STRICT_MS = 1000
CONTRASTS = {
    "A_minus_base": {"A": 1, "base": -1},
    "B_minus_base": {"B": 1, "base": -1},
    "AB_minus_base": {"AB": 1, "base": -1},
    "AB_minus_A": {"AB": 1, "A": -1},
    "AB_minus_B": {"AB": 1, "B": -1},
    "interaction_AB_minus_A_minus_B_plus_base": {"AB": 1, "A": -1, "B": -1, "base": 1},
}
FLOW_FIELDS = ("actual_sale_units", "sale_revenue", "recorded_purchase_costs",
               "floor_sale_units", "terminal_shed", "terminal_cargo")
SCALARS = ("margin", "points", "own_cash", "opponent_cash", "sale_units_total",
           "sale_revenue_total", "recorded_purchase_costs_total", "all_cash_outflow_derived",
           "atomic_costs_derived", "opponent_sale_units_total", "opponent_sale_revenue_total",
           "opponent_all_cash_outflow_derived", "terminal_shed_units", "terminal_cargo_units")


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise EvidenceError(f"Cannot read complete JSON {path}: {error}") from error


def number(value, label, nonnegative=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f"Invalid numeric {label}: {value!r}")
    require(not nonnegative or value >= 0, f"Negative {label}: {value}")
    return value


def count_map(value, label):
    require(isinstance(value, dict), f"Expected dictionary: {label}")
    return {str(k): number(v, f"{label}.{k}", True) for k, v in sorted(value.items()) if v != 0}


def sum_maps(maps):
    result = Counter()
    for mapping in maps:
        result.update(mapping)
    return {k: v for k, v in sorted(result.items()) if v != 0}


def points(margin):
    return 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5


def outcome(margin):
    return "win" if margin > 0 else "loss" if margin < 0 else "draw"


def describe(values):
    values = list(values)
    if not values:
        return {"n": 0, "sum": 0, "mean": None, "median": None, "min": None, "max": None}
    return {"n": len(values), "sum": sum(values), "mean": statistics.mean(values),
            "median": statistics.median(values), "min": min(values), "max": max(values)}


def metric_maps(row, seat):
    final = row["final_after_market"]
    return {
        "actual_sale_units": count_map(row["actual_sales"][seat], "actual_sales"),
        "sale_revenue": count_map(row["sale_revenue"][seat], "sale_revenue"),
        "recorded_purchase_costs": count_map(row["market_spending"][seat], "market_spending"),
        "floor_sale_units": count_map(row["floor_units"][seat], "floor_units"),
        "terminal_shed": count_map(final["shed"][seat], "terminal_shed"),
        "terminal_cargo": sum_maps(count_map(inv, "terminal_cargo") for inv in final["carried"][seat]),
    }


def normalize(row, label, path):
    seat = row["seat"]
    own = metric_maps(row, seat)
    other = metric_maps(row, 1 - seat)
    own_cash = number(row["rewards"][seat], "own_cash")
    opponent_cash = number(row["rewards"][1 - seat], "opponent_cash")
    margin = own_cash - opponent_cash
    require(margin == row["margin"], f"Reward/margin contradiction in {path.name}")
    income = sum(own["sale_revenue"].values())
    costs = STARTING_MONEY + income - own_cash
    purchased = sum(own["recorded_purchase_costs"].values())
    other_income = sum(other["sale_revenue"].values())
    require(costs >= purchased, f"Cash-flow contradiction in {path.name}")
    clean = row["statuses"] == ["DONE", "DONE"] and row["frames"] == 720 and not row["errors"]
    timing = row.get("timing_diagnostics", {})
    # The raw counter is a sum of warehouse exposure across turns, not units sold.
    timing = {("held_stock_unit_turns" if k == "held_units" else k): v for k, v in timing.items()}
    timing = count_map(timing, "timing_diagnostics")
    return {
        "variant": VARIANTS[label], "result_file": str(path.relative_to(LAB)).replace("\\", "/"),
        "result_sha256": digest(path), "candidate_sha256": row["candidate_sha256"],
        "runner_sha256": row["runner_sha256"],
        "entrypoint": row.get("entrypoint", "legacy_explicit_module_agent_not_recorded"),
        "clean": clean, "statuses": row["statuses"], "frames": row["frames"],
        "error_count_capped_at_five": len(row["errors"]), "margin": margin, "points": points(margin),
        "own_cash": own_cash, "opponent_cash": opponent_cash,
        "sale_units_total": sum(own["actual_sale_units"].values()), "sale_revenue_total": income,
        "recorded_purchase_costs_total": purchased, "all_cash_outflow_derived": costs,
        "atomic_costs_derived": costs - purchased,
        "opponent_sale_units_total": sum(other["actual_sale_units"].values()),
        "opponent_sale_revenue_total": other_income,
        "opponent_all_cash_outflow_derived": STARTING_MONEY + other_income - opponent_cash,
        "terminal_shed_units": sum(own["terminal_shed"].values()),
        "terminal_cargo_units": sum(own["terminal_cargo"].values()),
        "flows": own, "opponent_flows": other,
        "own_max_call_ms": number(row["max_call_ms"][seat], "own_max_call_ms", True),
        "opponent_max_call_ms": number(row["max_call_ms"][1 - seat], "opponent_max_call_ms", True),
        "wall_seconds": number(row["wall_seconds"], "wall_seconds", True),
        "started_utc": row["started_utc"], "completed_utc": row["completed_utc"],
        "terminal_diagnostics": count_map(row["terminal_diagnostics"], "terminal_diagnostics"),
        "timing_diagnostics": timing,
        "terminal_start_sha256": row["terminal_start"]["sha256"], "shops": row["shops"],
    }


def scalar_contrast(variants, weights, field):
    return sum(weight * variants[label][field] for label, weight in weights.items())


def map_contrast(variants, weights, field, opponent=False):
    source = "opponent_flows" if opponent else "flows"
    keys = set().union(*(variants[label][source][field] for label in weights))
    result = {key: sum(weight * variants[label][source][field].get(key, 0)
                       for label, weight in weights.items()) for key in sorted(keys)}
    return {key: value for key, value in result.items() if value != 0}


def contrast(variants, weights):
    result = {field: scalar_contrast(variants, weights, field) for field in SCALARS}
    result["flows"] = {field: map_contrast(variants, weights, field) for field in FLOW_FIELDS}
    result["opponent_flows"] = {field: map_contrast(variants, weights, field, True) for field in FLOW_FIELDS}
    # Exact ex-post accounting split, not a causal price/quantity counterfactual.
    result["cash_identity_residual"] = (result["own_cash"] - result["sale_revenue_total"]
                                         + result["all_cash_outflow_derived"])
    result["margin_identity_residual"] = result["margin"] - result["own_cash"] + result["opponent_cash"]
    return result


def validate_pair(case):
    variants = case["variants"]
    matched = len({v["terminal_start_sha256"] for v in variants.values()}) == 1
    require(len({tuple(v["shops"]) for v in variants.values()}) == 1,
            f"Shop-path contradiction: {case['key']}")
    case["preterminal_raw_fingerprint_matched"] = matched
    case["preterminal_equivalence_status"] = "raw_fingerprint_matched" if matched else "UNVERIFIED"
    case["same_shop_path"] = True
    case["shops"] = variants["base"]["shops"]
    case["clean"] = all(v["clean"] for v in variants.values())
    case["strict_own_1s_clean"] = case["clean"] and all(v["own_max_call_ms"] <= STRICT_MS for v in variants.values())
    case["effects"] = {name: contrast(variants, weights) for name, weights in CONTRASTS.items()}
    for effect in case["effects"].values():
        require(effect["cash_identity_residual"] == effect["margin_identity_residual"] == 0,
                f"Accounting contradiction: {case['key']}")
    return case


def load_evidence():
    combinations = list(itertools.product(OPPONENTS, SEEDS, (0, 1)))
    expected = [(opponent, seed, seat, label, RESULTS / "development" /
                 f"{opponent}-{seed}-{seat}-{variant}.json")
                for opponent, seed, seat in combinations for label, variant in VARIANTS.items()]
    missing = [str(path.relative_to(LAB)).replace("\\", "/") for *_, path in expected if not path.is_file()]
    require(not missing, f"Incomplete 160-row factorial evidence; {len(missing)} missing:\n" + "\n".join(missing))
    pool_path = LAB / "opponent-pool-p2.json"
    pool = {p["name"]: p for p in read_json(pool_path)["opponents"] if p["name"] in OPPONENTS}
    require(set(pool) == set(OPPONENTS), "Opponent pool does not contain exact five selected opponents")
    file_manifest = read_json(TRACK / "manifest-file-v2.json")
    timing_manifest = read_json(TRACK / "manifest-timing-v1.json")
    require(file_manifest["baseline_sha256"] == HASHES["base"], "Changed frozen baseline manifest")
    require(file_manifest["variants"]["depth2-file"]["sha256"] == HASHES["A"], "Changed frozen A manifest")
    require(timing_manifest["parent_sha256"] == HASHES["A"], "Timing parent contradiction")
    for label in ("B", "AB"):
        require(timing_manifest["variants"][VARIANTS[label]]["sha256"] == HASHES[label], f"Changed frozen {label} manifest")
    require(timing_manifest["variants"][VARIANTS["B"]]["timing_only"] is True
            and timing_manifest["variants"][VARIANTS["AB"]]["timing_only"] is False, "Timing mode contradiction")
    candidate_paths = {label: "public-baseline-v10/main.py" if label == "base"
                       else f"experiments/track-terminal-20260912/{variant}/main.py"
                       for label, variant in VARIANTS.items()}
    for label, path in candidate_paths.items():
        require(digest(LAB / path) == HASHES[label], f"Frozen candidate bytes changed: {label}")
    for opponent in pool.values():
        require(digest(LAB / opponent["path"]) == opponent["sha256"], f"Opponent bytes changed: {opponent['name']}")
    engine = LAB / "official/installed-1.32.7/kaggriculture.py"
    require(digest(engine) == ENGINE_HASH, "Reference engine changed")
    source_json = read_json(engine.with_suffix(".json"))
    require(source_json["configuration"]["startingMoney"]["default"] == STARTING_MONEY, "Starting cash contradiction")
    cases = {(o, seed, seat): {"key": f"{o}-{seed}-{seat}", "opponent": o,
                              "family": pool[o]["family"], "seed": seed, "seat": seat, "variants": {}}
             for o, seed, seat in combinations}
    for opponent, seed, seat, label, path in expected:
        row = read_json(path)
        fixed = {"opponent": opponent, "seed": seed, "seat": seat, "variant": VARIANTS[label],
                 "candidate_sha256": HASHES[label], "engine_sha256": ENGINE_HASH,
                 "candidate_path": candidate_paths[label], "opponent_path": pool[opponent]["path"],
                 "opponent_sha256": pool[opponent]["sha256"], "family": pool[opponent]["family"],
                 "evidence": "closed_loop", "split": "development", "key": path.name}
        for key, value in fixed.items():
            require(row.get(key) == value, f"{path.name}: {key} contradiction, got {row.get(key)!r}")
        require(row.get("runner_sha256") in RUNNERS[label], f"Unknown runner revision in {path.name}")
        if label != "base":
            require(row.get("entrypoint") == "official_get_last_callable", f"Unverified file entry in {path.name}")
        if label in ("B", "AB"):
            require(isinstance(row.get("timing_diagnostics"), dict), f"Missing timing diagnostics in {path.name}")
        require(row.get("final_after_market", {}).get("step") == 718, f"Wrong final market step in {path.name}")
        fingerprint = row.get("terminal_start", {}).get("sha256", "")
        require(isinstance(fingerprint, str) and len(fingerprint) == 64, f"Missing preterminal fingerprint in {path.name}")
        for key in ("rewards", "statuses", "actual_sales", "sale_revenue", "market_spending",
                    "max_call_ms", "floor_units", "terminal_stock"):
            require(isinstance(row.get(key), list) and len(row[key]) == 2, f"Missing two-seat {key} in {path.name}")
        require(isinstance(row.get("errors"), list) and isinstance(row.get("shops"), list), f"Bad errors/shops in {path.name}")
        require(isinstance(row["final_after_market"].get("shed"), list)
                and len(row["final_after_market"]["shed"]) == 2
                and isinstance(row["final_after_market"].get("carried"), list)
                and len(row["final_after_market"]["carried"]) == 2, f"Missing terminal inventories in {path.name}")
        require(row["terminal_stock"] == row["final_after_market"]["shed"], f"Terminal shed contradiction in {path.name}")
        cases[(opponent, seed, seat)]["variants"][label] = normalize(row, label, path)
    return [validate_pair(cases[key]) for key in combinations], pool


def aggregate_effects(cases, name):
    effects = [case["effects"][name] for case in cases]
    result = {field: describe(e[field] for e in effects) for field in SCALARS}
    result["flows_total"] = {field: sum_maps(e["flows"][field] for e in effects) for field in FLOW_FIELDS}
    result["opponent_flows_total"] = {field: sum_maps(e["opponent_flows"][field] for e in effects) for field in FLOW_FIELDS}
    result["margin_improved_unchanged_worsened"] = {
        "improved": sum(e["margin"] > 0 for e in effects), "unchanged": sum(e["margin"] == 0 for e in effects),
        "worsened": sum(e["margin"] < 0 for e in effects)}
    return result


def summarize(cases):
    summary = {"paired_cases": len(cases), "games": 4 * len(cases), "variants": {}, "effects": {}}
    for label in VARIANTS:
        rows = [case["variants"][label] for case in cases]
        stat = {field: describe(r[field] for r in rows) for field in SCALARS}
        stat.update(wins=sum(r["margin"] > 0 for r in rows), draws=sum(r["margin"] == 0 for r in rows),
                    losses=sum(r["margin"] < 0 for r in rows), clean_rows=sum(r["clean"] for r in rows),
                    own_max_call_ms=describe(r["own_max_call_ms"] for r in rows),
                    opponent_max_call_ms=describe(r["opponent_max_call_ms"] for r in rows),
                    wall_seconds=describe(r["wall_seconds"] for r in rows),
                    own_calls_over_1s_games=sum(r["own_max_call_ms"] > STRICT_MS for r in rows),
                    timing_diagnostics=sum_maps(r["timing_diagnostics"] for r in rows),
                    terminal_diagnostics=sum_maps(r["terminal_diagnostics"] for r in rows),
                    flows_total={field: sum_maps(r["flows"][field] for r in rows) for field in FLOW_FIELDS},
                    opponent_flows_total={field: sum_maps(r["opponent_flows"][field] for r in rows) for field in FLOW_FIELDS})
        summary["variants"][label] = stat
    for name in CONTRASTS:
        summary["effects"][name] = aggregate_effects(cases, name)
    summary["outcome_flips"] = {}
    for source, target in (("base", "A"), ("base", "B"), ("base", "AB"), ("A", "AB"), ("B", "AB")):
        matrix = Counter(f"{outcome(c['variants'][source]['margin'])}_to_{outcome(c['variants'][target]['margin'])}" for c in cases)
        summary["outcome_flips"][f"{source}_to_{target}"] = {"matrix": dict(sorted(matrix.items())),
            "improved": sum(c["variants"][target]["points"] > c["variants"][source]["points"] for c in cases),
            "worsened": sum(c["variants"][target]["points"] < c["variants"][source]["points"] for c in cases),
            "points_delta": sum(c["variants"][target]["points"] - c["variants"][source]["points"] for c in cases)}
    return summary


def runtime_audit(cases):
    records = [{"key": case["key"], "variant": label, "family": case["family"],
                **{k: row[k] for k in ("own_max_call_ms", "opponent_max_call_ms", "wall_seconds", "started_utc", "completed_utc")},
                "search_nodes": row["terminal_diagnostics"].get("search_nodes", 0), "clean": row["clean"]}
               for case in cases for label, row in case["variants"].items()]
    a_reference = [r for r in records if r["variant"] == "A" and r["key"].startswith("lonespear-")]
    return {"act_timeout_seconds": 1, "initial_remaining_overage_seconds": 60,
            "strict_threshold_ms": STRICT_MS,
            "measurement": "Per-game maximum of our function-call elapsed wall time, not CPU time; imports/file loading outside that function are omitted.",
            "limits": ["No per-call timing sequence or consumed overage was recorded in these rows.",
                       "The local function runner and get_last_callable do not establish raw-file process startup/runtime safety.",
                       "A call above 1000 ms is not automatically fatal with the 60-second overage budget; below-threshold maxima likewise do not prove platform safety.",
                       "The strict cohort is a conservative sensitivity subset, not a timeout adjudication or an independent sample."],
            "original_A_lonespear_evidence": a_reference,
            "host_scheduling_inference": "A/91102 has 97203 search nodes per seat, fewer than A/91101's 108521, but both seats' own maxima, opponent maxima, and whole-game wall times inflate concurrently. Shared host scheduling/load is plausible; max-only wall measurements cannot isolate or exclude algorithmic tail latency.",
            "all_over_1s_rows": sorted((r for r in records if r["own_max_call_ms"] > STRICT_MS), key=lambda r: -r["own_max_call_ms"]),
            "largest_own_maxima": sorted(records, key=lambda r: -r["own_max_call_ms"])[:12]}


def build_report(cases, pool):
    cohorts = {"all_complete_pairs": cases, "clean_complete_pairs": [c for c in cases if c["clean"]],
               "strict_own_1s_clean_complete_pairs": [c for c in cases if c["strict_own_1s_clean"]],
               "raw_fingerprint_matched_pairs_diagnostic_only": [c for c in cases if c["preterminal_raw_fingerprint_matched"]]}
    summaries = {}
    for name, cohort in cohorts.items():
        summary = summarize(cohort)
        summary["excluded_case_keys"] = [c["key"] for c in cases if c not in cohort]
        summary["per_opponent"] = {o: summarize([c for c in cohort if c["opponent"] == o]) for o in OPPONENTS}
        families = sorted({c["family"] for c in cases})
        summary["per_family"] = {f: summarize([c for c in cohort if c["family"] == f]) for f in families}
        summary["family_macro_mean_points"] = {label: statistics.mean(
            group["variants"][label]["points"]["mean"] for group in summary["per_family"].values()
            if group["paired_cases"]) if cohort else None for label in VARIANTS}
        summaries[name] = summary
    negative = {}
    for name in CONTRASTS:
        negative[name] = [{"key": c["key"], "opponent": c["opponent"], "family": c["family"],
                           "seed": c["seed"], "seat": c["seat"], "clean": c["clean"],
                           "strict_own_1s_clean": c["strict_own_1s_clean"], "shops": c["shops"],
                           "effect": c["effects"][name]}
                          for c in sorted(cases, key=lambda c: c["effects"][name]["margin"])
                          if c["effects"][name]["margin"] < 0]
    return {
        "schema": "p2b-interactions-v1", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "report_script_sha256": digest(__file__), "evidence": "development_closed_loop_four_cell_factorial",
        "artifact_release_status": "Research only: frozen timing v1 has known HIRE financing-prefix and cancelled-sale/prepayment-ledger synchronization issues. These four-grid results do not authorize release; later safety revisions are deliberately excluded.",
        "selection_warning": "Development results used to choose methods; not independent confirmation or leaderboard estimates. Opponent families are manually classified and include weak controls.",
        "design": {"variants": VARIANTS, "candidate_hashes": HASHES, "engine_sha256": ENGINE_HASH,
                   "allowed_historical_runner_hashes": {k: sorted(v) for k, v in RUNNERS.items()},
                   "opponents": {name: {key: pool[name][key] for key in ("path", "sha256", "family")} for name in OPPONENTS},
                   "seeds": SEEDS, "seats": [0, 1], "expected_cases": 40, "expected_rows": 160,
                   "contrast_weights": CONTRASTS, "points": "win=1, draw=0.5, loss=0"},
        "accounting": {"flow_scope": "Full-game actual unit commits, not action counts or offered quantities. Step-695 fingerprints are checked per case; mismatched raw fingerprints remain in primary numerical results with preterminal equivalence UNVERIFIED. Preterminal flow-history equivalence is not separately hashed.",
                       "all_cash_outflow_derived": "3000 + sum(actual sale revenue) - final cash",
                       "atomic_costs_derived": "all_cash_outflow_derived - recorded unit-purchase spending; official engine cash changes outside unit commits are HIRE and BUY_LAND. Their split is not observed.",
                       "held_stock_unit_turns": "Raw held_units diagnostic summed available-minus-released inventory over calls. This is exposure in unit-turns, not unique retained goods, extra harvest, or actual sales.",
                       "diagnostic_release_counts": "Policy-planned release counters, not independently committed sale units; actual_sales/sale_revenue are authoritative.",
                       "terminal_inventory": "Aggregated item counts after the final step-718 market; worker-level private raw inventories are not exported.",
                       "price_quantity_attribution": "Revenue and quantity differences are exact observed outcomes; no causal price/quantity split or unobserved harvest-to-deposit identity is claimed from these aggregate rows."},
        "integrity": {"all_expected_rows_present": True, "candidate_and_opponent_hashes_verified": True,
                      "all_preterminal_raw_fingerprints_equal": all(c["preterminal_raw_fingerprint_matched"] for c in cases),
                      "preterminal_equivalence_unverified_cases": [
                          {"key": c["key"], "raw_fingerprints": {label: row["terminal_start_sha256"]
                           for label, row in c["variants"].items()}}
                          for c in cases if not c["preterminal_raw_fingerprint_matched"]],
                      "raw_fingerprint_warning": "The frozen runner hashes full observations including remainingOverageTime. Elapsed-time budget differences could change these hashes without changing economic state, but original full snapshots were not saved and this cause is not proven. No claim that all pre-696 states are equivalent; unverified cases stay in primary results and matched-only figures are diagnostic.",
                      "all_shop_paths_equal": all(c["same_shop_path"] for c in cases),
                      "all_rows_clean": all(c["clean"] for c in cases),
                      "all_rows_strict_own_1s": all(c["strict_own_1s_clean"] for c in cases)},
        "cohorts": summaries, "runtime_audit": runtime_audit(cases),
        "negative_margin_delta_outliers": negative, "cases": cases,
    }


def self_test():
    # Pure arithmetic/schema tests; no engine import, policy import, or games.
    variants = {}
    for label, value in {"base": 10, "A": 13, "B": 15, "AB": 21}.items():
        variants[label] = {key: value for key in SCALARS}
        variants[label]["points"] = {"base": 0, "A": .5, "B": 1, "AB": 1}[label]
        variants[label]["flows"] = {field: {"MILK": value} for field in FLOW_FIELDS}
        variants[label]["opponent_flows"] = {field: {"WOOL": 2 * value} for field in FLOW_FIELDS}
    interaction = contrast(variants, CONTRASTS["interaction_AB_minus_A_minus_B_plus_base"])
    assert interaction["margin"] == 3
    assert interaction["points"] == -.5
    assert interaction["flows"]["actual_sale_units"] == {"MILK": 3}
    assert interaction["opponent_flows"]["sale_revenue"] == {"WOOL": 6}
    assert sum_maps([{"a": -2, "b": 4}, {"a": 1, "b": -4}]) == {"a": -1}
    assert describe([])["mean"] is None
    assert [points(n) for n in (-1, 0, 1)] == [0, .5, 1]
    for label, row in variants.items():
        row.update(terminal_start_sha256="a" if label == "base" else "b", shops=[], clean=True, own_max_call_ms=2)
        row["own_cash"] = row["margin"]
        row["opponent_cash"] = 0
        row["all_cash_outflow_derived"] = 0
    quarantined = validate_pair({"key": "unverified", "variants": variants})
    assert quarantined["preterminal_equivalence_status"] == "UNVERIFIED"
    assert not quarantined["preterminal_raw_fingerprint_matched"]
    print(json.dumps({"self_test": "passed", "engine_imported": False, "games_run": 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    try:
        cases, pool = load_evidence()
        report = build_report(cases, pool)
        output = RESULTS / "p2b-interactions.json"
        # All validations finish before any report is written; no input mutation.
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        summary = report["cohorts"]["all_complete_pairs"]
        print(json.dumps({"report": str(output), "paired_cases": len(cases), "integrity": report["integrity"],
                          "points": {label: summary["variants"][label]["points"]["sum"] for label in VARIANTS},
                          "mean_margin_effects": {name: stats["margin"]["mean"] for name, stats in summary["effects"].items()}}))
    except (EvidenceError, KeyError, TypeError, OSError) as error:
        print(f"FAIL CLOSED: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
