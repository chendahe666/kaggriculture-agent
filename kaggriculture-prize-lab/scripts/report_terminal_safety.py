"""P2c safety-revision evidence report. Pure JSON analysis; never runs games.

Use --validate-partial during collection. --write-final requires all 240 exact
rows (160 frozen parent/control rows plus 80 new safety rows). The caller must
wait for the experiment owner's completion confirmation before finalization.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys

import report_terminal_interactions as parent

LAB, TRACK, RESULTS = parent.LAB, parent.TRACK, parent.RESULTS
PARENT_REPORT_SOURCE_HASH = "c7a548df068d93bb5d9df2c982da7e31f7c2d5a858b01c49b7208c665f300407"
SAFE_RUNNER_HASH = "4518551bccfb2c2c39a30c928da6d0b16016eb3ee1b18b0dbcb95ec19d87054c"
SAFETY_OVERLAY_HASH = "1bf5ce95f48a15ea91afebcdccf069b3bfa14a0641ed88f0962b695ef257f80e"
SAFE_VARIANTS = {"Bsafe": "timing-safe-file", "ABsafe": "depth2-timing-safe-file"}
SAFE_HASHES = {
    "Bsafe": "5da4bf0a8cc5914e86e0d6b76d2a05f630c9b65fb4609a451869bd6f489e273b",
    "ABsafe": "8d37e6f4683c5a8c399c74022211e77061a59600af6278e318c2958c9c6bfbd2",
}
SAFE_PARENTS = {"Bsafe": "B", "ABsafe": "AB"}
VARIANTS = {**parent.VARIANTS, **SAFE_VARIANTS}
SAFETY_KEYS = {"cash_guard_fallbacks", "ledger_reconciliations", "cancelled_new_fr_units", "cancelled_new_h5_units"}
TIMING_SCOPE = "Local inner function wall/CPU time; excludes source loading and some framework overhead, not official sandbox limits"
CONTRASTS = {
    "Bsafe_minus_Bv1": {"Bsafe": 1, "B": -1},
    "ABsafe_minus_ABv1": {"ABsafe": 1, "AB": -1},
    "Bsafe_minus_base": {"Bsafe": 1, "base": -1},
    "ABsafe_minus_A": {"ABsafe": 1, "A": -1},
    "ABsafe_minus_base": {"ABsafe": 1, "base": -1},
    "ABsafe_minus_Bsafe": {"ABsafe": 1, "Bsafe": -1},
    "safe_interaction_ABsafe_minus_A_minus_Bsafe_plus_base": {"ABsafe": 1, "A": -1, "Bsafe": -1, "base": 1},
}


def exact_counts(mapping, label):
    parent.require(isinstance(mapping, dict), f"Missing count dictionary: {label}")
    return {str(key): parent.number(value, f"{label}.{key}", True) for key, value in sorted(mapping.items())}


def fingerprint_info(raw):
    result = {"raw_sha256": raw["sha256"], "canonical_gameplay_sha256": raw.get("gameplay_sha256"),
              "runtime_overage_seconds": raw.get("runtime_overage_seconds"),
              "canonical_scope": raw.get("gameplay_hash_scope"),
              "provenance": "raw_and_canonical" if raw.get("gameplay_sha256") else "legacy_raw_only"}
    return result


def compare_fingerprints(left, right):
    left_hash, right_hash = left.get("canonical_gameplay_sha256"), right.get("canonical_gameplay_sha256")
    available = left_hash is not None and right_hash is not None
    return {"raw_fingerprint_matched": left["raw_sha256"] == right["raw_sha256"],
            "canonical_comparison_available": available,
            "canonical_fingerprint_matched": left_hash == right_hash if available else None,
            "canonical_status": ("matched" if left_hash == right_hash else "UNVERIFIED_MISMATCH")
            if available else "UNAVAILABLE_LEGACY_ROW_HAS_NO_CANONICAL_HASH"}


def profile_summary(profile, clean):
    parent.require(isinstance(profile, list), "Missing own_call_profile")
    steps = []
    for call in profile:
        parent.require(isinstance(call, dict), "Invalid call profile entry")
        step = call.get("step")
        parent.require(isinstance(step, int) and not isinstance(step, bool) and 0 <= step <= 718,
                       f"Invalid call step {step!r}")
        steps.append(step)
        for name in ("wall_ms", "cpu_ms"):
            parent.number(call.get(name), name, True)
    parent.require(steps == sorted(set(steps)), "Call profile has duplicated or unordered steps")
    complete = steps == list(range(719))
    parent.require(not clean or complete, "Clean completed game has incomplete own_call_profile")
    summary = {"available": True, "recorded_calls": len(profile), "all_719_steps_present": complete,
               "scope": TIMING_SCOPE, "windows": {}}
    for label, calls in {"all": profile, "preterminal_0_to_695": [c for c in profile if c["step"] < 696],
                         "terminal_696_to_718": [c for c in profile if c["step"] >= 696]}.items():
        summary["windows"][label] = {
            "wall_ms": parent.describe(c["wall_ms"] for c in calls),
            "cpu_ms": parent.describe(c["cpu_ms"] for c in calls),
            "inner_calls_over_1000ms": sum(c["wall_ms"] > 1000 for c in calls),
            "inner_wall_excess_above_1s_seconds_proxy": sum(max(0, c["wall_ms"] - 1000) for c in calls) / 1000,
            "zero_cpu_samples": sum(c["cpu_ms"] == 0 for c in calls),
        }
    summary["largest_wall_calls"] = sorted(profile, key=lambda c: -c["wall_ms"])[:5]
    return summary


def verify_safety_artifacts(pool):
    parent.require(parent.digest(parent.__file__) == PARENT_REPORT_SOURCE_HASH, "Frozen parent report utility source changed")
    path = TRACK / "manifest-timing-safety-v1.json"
    manifest = parent.read_json(path)
    parent.require(manifest.get("overlay_sha256") == SAFETY_OVERLAY_HASH, "Safety overlay manifest changed")
    parent.require(parent.digest(TRACK / "safety_overlay.py") == SAFETY_OVERLAY_HASH, "Safety overlay bytes changed")
    for label, variant in SAFE_VARIANTS.items():
        parent_label = SAFE_PARENTS[label]
        expected = {"parent": parent.VARIANTS[parent_label], "parent_sha256": parent.HASHES[parent_label],
                    "sha256": SAFE_HASHES[label]}
        parent.require(manifest.get("variants", {}).get(variant) == expected, f"Safety lineage contradiction: {label}")
        parent.require(parent.digest(TRACK / variant / "main.py") == SAFE_HASHES[label], f"Safety candidate changed: {label}")
    parent.require(set(pool) == set(parent.OPPONENTS), "Wrong opponent set")


def validate_safe_row(row, case, label, path, pool):
    opponent, seed, seat = case["opponent"], case["seed"], case["seat"]
    variant = SAFE_VARIANTS[label]
    fixed = {"variant": variant, "candidate_path": f"experiments/track-terminal-20260912/{variant}/main.py",
             "candidate_sha256": SAFE_HASHES[label], "runner_sha256": SAFE_RUNNER_HASH,
             "engine_sha256": parent.ENGINE_HASH, "opponent": opponent, "seed": seed, "seat": seat,
             "opponent_path": pool[opponent]["path"], "opponent_sha256": pool[opponent]["sha256"],
             "family": pool[opponent]["family"], "split": "development", "key": path.name,
             "evidence": "closed_loop", "entrypoint": "official_get_last_callable", "timing_scope": TIMING_SCOPE}
    for key, value in fixed.items():
        parent.require(row.get(key) == value, f"{path.name}: {key} contradiction, got {row.get(key)!r}")
    for key in ("rewards", "statuses", "actual_sales", "sale_revenue", "floor_units", "market_spending",
                "max_call_ms", "terminal_stock"):
        parent.require(isinstance(row.get(key), list) and len(row[key]) == 2, f"Invalid {key}: {path.name}")
    parent.require(isinstance(row.get("errors"), list) and isinstance(row.get("shops"), list), f"Invalid errors/shops: {path.name}")
    final = row.get("final_after_market", {})
    parent.require(final.get("step") == 718, f"Missing final market: {path.name}")
    for key in ("shed", "carried"):
        parent.require(isinstance(final.get(key), list) and len(final[key]) == 2, f"Missing final {key}: {path.name}")
    parent.require(row["terminal_stock"] == final["shed"], f"Terminal shed contradiction: {path.name}")
    snapshot = row.get("terminal_start", {})
    for key in ("sha256", "gameplay_sha256"):
        value = snapshot.get(key)
        parent.require(isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
                       f"Missing {key}: {path.name}")
    parent.require(snapshot.get("gameplay_hash_scope") == "All observation fields except machine-dependent remainingOverageTime; raw sha256 retained separately",
                   f"Unexpected canonical fingerprint scope: {path.name}")
    overage = snapshot.get("runtime_overage_seconds")
    parent.require(isinstance(overage, list) and len(overage) == 2, f"Missing overage snapshot: {path.name}")
    for value in overage:
        parent.number(value, "runtime_overage_seconds")
    diagnostics = exact_counts(row.get("safety_diagnostics"), "safety_diagnostics")
    parent.require(set(diagnostics) == SAFETY_KEYS, f"Unexpected safety diagnostic schema: {path.name}")
    parent.require(isinstance(row.get("timing_diagnostics"), dict), f"Missing timing diagnostic: {path.name}")
    norm = parent.normalize(row, SAFE_PARENTS[label], path)
    norm.update(variant=variant, safety_diagnostics=diagnostics, safety_diagnostics_available=True,
                preterminal_fingerprint=fingerprint_info(snapshot),
                own_call_profile_summary=profile_summary(row.get("own_call_profile"), norm["clean"]))
    return norm


def load_evidence(allow_partial=False):
    # This validates all frozen control files, hashes, manifests, engine and pool.
    cases, pool = parent.load_evidence()
    verify_safety_artifacts(pool)
    missing = []
    for case in cases:
        case["legacy_four_grid_preterminal_status"] = case.pop("preterminal_equivalence_status")
        case["legacy_four_grid_raw_fingerprint_matched"] = case.pop("preterminal_raw_fingerprint_matched")
        case["legacy_four_grid_same_shop_path"] = case.pop("same_shop_path")
        for label, row in case["variants"].items():
            row.update(preterminal_fingerprint=fingerprint_info({"sha256": row["terminal_start_sha256"]}),
                       safety_diagnostics=None, safety_diagnostics_available=False,
                       own_call_profile_summary={"available": False, "scope": "Historical outer measured function wall maximum only; no CPU or per-call series recorded."})
        for label, variant in SAFE_VARIANTS.items():
            path = RESULTS / "development" / f"{case['key']}-{variant}.json"
            if not path.is_file():
                missing.append(str(path.relative_to(LAB)).replace("\\", "/"))
                continue
            case["variants"][label] = validate_safe_row(parent.read_json(path), case, label, path, pool)
    parent.require(allow_partial or not missing, f"Incomplete P2c evidence, {len(missing)} missing:\n" + "\n".join(missing))
    if missing:
        return cases, pool, missing
    for case in cases:
        case["effects"] = {name: parent.contrast(case["variants"], weights) for name, weights in CONTRASTS.items()}
        case["clean"] = all(row["clean"] for row in case["variants"].values())
        case["strict_own_1s_clean"] = case["clean"] and all(row["own_max_call_ms"] <= 1000 for row in case["variants"].values())
        comparisons = [("Bsafe", "ABsafe"), ("Bsafe", "B"), ("ABsafe", "AB"),
                       ("Bsafe", "base"), ("ABsafe", "A"), ("ABsafe", "base")]
        case["preterminal_comparisons"] = {f"{a}_vs_{b}": compare_fingerprints(
            case["variants"][a]["preterminal_fingerprint"], case["variants"][b]["preterminal_fingerprint"])
            for a, b in comparisons}
        case["safe_pair_canonical_matched"] = case["preterminal_comparisons"]["Bsafe_vs_ABsafe"]["canonical_fingerprint_matched"]
        case["all_six_shop_paths_equal"] = len({tuple(row["shops"]) for row in case["variants"].values()}) == 1
        for effect in case["effects"].values():
            parent.require(effect["cash_identity_residual"] == effect["margin_identity_residual"] == 0,
                           f"Cash/margin identity contradiction: {case['key']}")
    return cases, pool, missing


def diagnostic_totals(rows, key):
    sums = Counter()
    for row in rows:
        sums.update(row.get(key) or {})
    return dict(sorted(sums.items()))


def economic_effect_changed(effect):
    return (any(effect[field] != 0 for field in parent.SCALARS)
            or any(effect[side][field] for side in ("flows", "opponent_flows") for field in parent.FLOW_FIELDS))


def summarize(cases):
    result = {"paired_cases": len(cases), "games": 6 * len(cases), "variants": {}, "effects": {}, "outcome_flips": {}}
    for label in VARIANTS:
        rows = [case["variants"][label] for case in cases]
        result["variants"][label] = {**{field: parent.describe(row[field] for row in rows) for field in parent.SCALARS},
            "wins": sum(row["margin"] > 0 for row in rows), "draws": sum(row["margin"] == 0 for row in rows),
            "losses": sum(row["margin"] < 0 for row in rows), "clean_rows": sum(row["clean"] for row in rows),
            "error_count_capped_per_game": sum(row["error_count_capped_at_five"] for row in rows),
            "own_max_call_ms": parent.describe(row["own_max_call_ms"] for row in rows),
            "wall_seconds": parent.describe(row["wall_seconds"] for row in rows),
            "own_max_over_1s_games": sum(row["own_max_call_ms"] > 1000 for row in rows),
            "safety_diagnostics_available_rows": sum(row["safety_diagnostics_available"] for row in rows),
            "safety_diagnostics": diagnostic_totals(rows, "safety_diagnostics"),
            "timing_diagnostics": diagnostic_totals(rows, "timing_diagnostics"),
            "terminal_diagnostics": diagnostic_totals(rows, "terminal_diagnostics"),
            "flows_total": {field: parent.sum_maps(row["flows"][field] for row in rows) for field in parent.FLOW_FIELDS},
            "opponent_flows_total": {field: parent.sum_maps(row["opponent_flows"][field] for row in rows) for field in parent.FLOW_FIELDS}}
        if label in SAFE_VARIANTS:
            result["variants"][label]["inner_profile_totals"] = {
                "calls": sum(row["own_call_profile_summary"]["recorded_calls"] for row in rows),
                "wall_ms": sum(row["own_call_profile_summary"]["windows"]["all"]["wall_ms"]["sum"] for row in rows),
                "cpu_ms": sum(row["own_call_profile_summary"]["windows"]["all"]["cpu_ms"]["sum"] for row in rows),
                "inner_calls_over_1s": sum(row["own_call_profile_summary"]["windows"]["all"]["inner_calls_over_1000ms"] for row in rows),
                "inner_excess_seconds_proxy": sum(row["own_call_profile_summary"]["windows"]["all"]["inner_wall_excess_above_1s_seconds_proxy"] for row in rows)}
    result["effects"] = {name: parent.aggregate_effects(cases, name) for name in CONTRASTS}
    for source, target in (("B", "Bsafe"), ("AB", "ABsafe"), ("base", "Bsafe"), ("base", "ABsafe"), ("A", "ABsafe")):
        matrix = Counter(f"{parent.outcome(c['variants'][source]['margin'])}_to_{parent.outcome(c['variants'][target]['margin'])}" for c in cases)
        result["outcome_flips"][f"{source}_to_{target}"] = {
            "matrix": dict(sorted(matrix.items())),
            "improved": sum(c["variants"][target]["points"] > c["variants"][source]["points"] for c in cases),
            "worsened": sum(c["variants"][target]["points"] < c["variants"][source]["points"] for c in cases),
            "points_delta": sum(c["variants"][target]["points"] - c["variants"][source]["points"] for c in cases)}
    return result


def build_report(cases, pool):
    parent.require(len(cases) == 40 and all(set(c["variants"]) == set(VARIANTS) for c in cases), "Final report requires 40 complete six-way cases")
    summary = summarize(cases)
    summary["per_opponent"] = {name: summarize([c for c in cases if c["opponent"] == name]) for name in parent.OPPONENTS}
    summary["per_family"] = {name: summarize([c for c in cases if c["family"] == name]) for name in sorted({c["family"] for c in cases})}
    summary["family_macro_points"] = {label: statistics.mean(g["variants"][label]["points"]["mean"] for g in summary["per_family"].values()) for label in VARIANTS}
    diagnostic_cohorts = {
        "all_six_clean_pairs": [c for c in cases if c["clean"]],
        "all_six_own_max_at_most_1s_clean_pairs": [c for c in cases if c["strict_own_1s_clean"]],
        "new_safe_pair_canonical_matched_pairs": [c for c in cases if c["safe_pair_canonical_matched"]],
    }
    outliers = {name: [{"key": c["key"], "family": c["family"], "shops": c["shops"],
                        "effect": c["effects"][name], "preterminal_comparisons": c["preterminal_comparisons"]}
                       for c in sorted(cases, key=lambda c: c["effects"][name]["margin"])
                       if c["effects"][name]["margin"] < 0] for name in CONTRASTS}
    safety_changed = [{"key": c["key"], "label": label, "effect": c["effects"][f"{label}_minus_{'Bv1' if label == 'Bsafe' else 'ABv1'}"]}
                      for c in cases for label in SAFE_VARIANTS
                      if economic_effect_changed(c["effects"][f"{label}_minus_{'Bv1' if label == 'Bsafe' else 'ABv1'}"])]
    return {
        "schema": "p2c-safety-v1", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "report_script_sha256": parent.digest(__file__), "parent_report_utility_sha256": PARENT_REPORT_SOURCE_HASH,
        "evidence": "development_closed_loop_safety_revision_comparison",
        "release_status": "Research report only; successful development games and ledger diagnostic counts are not a submission authorization or proof of raw-file sandbox safety.",
        "design": {"variants": VARIANTS, "candidate_hashes": {**parent.HASHES, **SAFE_HASHES},
                   "new_runner_sha256": SAFE_RUNNER_HASH, "old_runner_hashes": {k: sorted(v) for k, v in parent.RUNNERS.items()},
                   "engine_sha256": parent.ENGINE_HASH, "safety_overlay_sha256": SAFETY_OVERLAY_HASH,
                   "seeds": parent.SEEDS, "seats": [0, 1], "expected_cases": 40, "expected_total_rows": 240,
                   "expected_new_rows": 80, "contrasts": CONTRASTS,
                   "opponents": {o: {k: pool[o][k] for k in ("path", "sha256", "family")} for o in parent.OPPONENTS}},
        "integrity": {"all_expected_rows_present": True, "all_identity_hashes_verified": True,
                      "all_rows_clean": all(c["clean"] for c in cases),
                      "all_new_pair_canonical_hashes_match": all(c["safe_pair_canonical_matched"] for c in cases),
                      "all_six_shop_paths_equal": all(c["all_six_shop_paths_equal"] for c in cases),
                      "canonical_cross_run_comparison_available": False,
                      "fingerprint_warning": "Old 160 rows contain only full-observation raw hashes, including remainingOverageTime. Their canonical hashes cannot be recovered from hashes alone. New 80 rows retain raw hashes and add hashes excluding only remainingOverageTime. Canonical equality of the two new variants does not establish canonical equality to any old row. Raw matches/differences are reported separately; raw mismatches are not silently explained away.",
                      "unmatched_new_canonical_case_keys": [c["key"] for c in cases if not c["safe_pair_canonical_matched"]]},
        "measurement_notes": {
            "outcomes": "Official engine final cash, W/D/L and 1/0.5/0 points, but local function execution is not an official Kaggle leaderboard or sandbox run.",
            "flows": "Full-game actual committed sale quantities/revenue and recorded unit-purchase spending. Action counts are not sales. Cash outflow=3000+sale revenue-final cash; remaining atomic costs are HIRE/BUY_LAND combined and not separately observed.",
            "profile_scope": TIMING_SCOPE,
            "historical_timing": "Old variants have max elapsed function wall time only, no CPU/per-call series. New inner profile and outer max_call_ms cover slightly different wrappers and must not be treated as identical scopes.",
            "clock_resolution": "Short process_time samples can be zero or exceed paired wall samples because of clock resolution; zero samples do not mean no CPU work. Aggregate CPU time is more interpretable than per-call zero samples.",
            "overage": "actTimeout=1 second with initial remainingOverageTime=60 seconds. Sum of max(0, inner wall-1s) is only an inner-call proxy, not measured official budget consumption. Step-695 budget snapshots are actual locally observed fields, not final remaining budget.",
            "diagnostics": "Safety counters record branches/reconciliations, not proven prevented losses. Zero cancellation or fallback counts means those defenses were not exercised in these rows. Legacy safety diagnostics are unavailable, not zero.",
            "held_stock_unit_turns": "Renamed raw held_units is inventory exposure summed across turns, not unique goods or sales.",
            "selection": "All 40 cases remain primary irrespective of timing/raw-fingerprint anomalies. Subsets are diagnostics, not replacement evidence. This is a fixed, partly weak, manually classified development pool, not independent confirmation."},
        "primary_all_cases": summary,
        "diagnostic_cohorts": {name: {"summary": summarize(group), "excluded_case_keys": [c["key"] for c in cases if c not in group]}
                               for name, group in diagnostic_cohorts.items()},
        "safety_revision_changed_cases": safety_changed,
        "negative_margin_delta_outliers": outliers, "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate-partial", action="store_true", help="Validate available rows; never write a report.")
    mode.add_argument("--write-final", action="store_true", help="After owner confirms collection complete, validate and write p2c-safety.json.")
    args = parser.parse_args()
    try:
        cases, pool, missing = load_evidence(allow_partial=args.validate_partial)
        if not args.write_final:
            print(json.dumps({"mode": "validation_only", "expected_new_rows": 80, "validated_new_rows": 80 - len(missing),
                              "missing_new_rows": len(missing), "missing_files": missing, "report_written": False}))
            return
        report = build_report(cases, pool)
        output = RESULTS / "p2c-safety.json"
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        summary = report["primary_all_cases"]
        print(json.dumps({"report": str(output), "integrity": report["integrity"],
                          "points": {label: summary["variants"][label]["points"]["sum"] for label in VARIANTS},
                          "mean_margin_effects": {name: stat["margin"]["mean"] for name, stat in summary["effects"].items()},
                          "safety_revision_changed_cases": len(report["safety_revision_changed_cases"])}))
    except (parent.EvidenceError, KeyError, TypeError, OSError) as error:
        print(f"FAIL CLOSED: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
