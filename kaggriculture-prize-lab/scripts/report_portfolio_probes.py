"""Audit the first 96 P3 probe JSON rows and 48 reused P2 controls.

No policy/runner/engine import, game execution or model fitting. The CLI reads
only until --output is explicitly supplied; output creation is exclusive.
Identity/source corruption rejects the report. Gameplay failures remain in all
primary comparisons; invalid features cannot enter the counterfactual dataset.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from portfolio_features import FEATURE_NAMES, FEATURE_SCHEMA, SCHEMA, SHOPS, schema_digest

LAB = Path(__file__).resolve().parents[1]
VARIANTS = ("v5-low-file", "v5-high-file")
SEEDS = (91101, 91102, 91103, 91104)
FAMILIES = {
    "cok": "reconstructed_mixed_route", "arlene": "reconstructed_mixed_route",
    "seyam": "closed_loop_expert_route", "lonespear": "greedy_dynamic_lineage",
    "deepesh": "single_farmer_staple_greedy", "maverick": "sticky_zoned_crop_economy",
}
OPPONENTS = ("cok", "seyam", "lonespear", "deepesh", "maverick", "arlene")
BASELINE_PATH = "public-baseline-v10/main.py"
BASELINE_HASH = "1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01"
ENGINE_HASH = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
SOURCE_PATHS = {
    "engine_sha256": "official/installed-1.32.7/kaggriculture.py",
    "runner_sha256": "scripts/run_portfolio_track.py",
    "features_sha256": "scripts/portfolio_features.py",
    "research_cycle_sha256": "scripts/research_cycle.py",
}
OLD_RUNNERS = {
    "1205a7ef72285e7e93caf05d84fbb635ebdce8a1c2046bea1a96c7d92f1e44c9",
    "2ce7669a5bf00f186f39481505db37cbae56c55d2f21df0c75150695302bc502",
    "4518551bccfb2c2c39a30c928da6d0b16016eb3ee1b18b0dbcb95ec19d87054c",
}
PHASES = ("opening_0_71", "middle_72_167", "main_168_695", "terminal_696_718")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def json_digest(value):
    return digest_bytes(canonical(value).encode())


def is_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("Non-finite JSON number")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid)


class FileStore:
    """Lab-contained reads, cached bytes, then an end-of-audit drift check."""
    def __init__(self, lab=LAB):
        self.lab, self.cache = Path(lab).resolve(), {}

    def path(self, name):
        path = (self.lab / name).resolve()
        require(path.is_relative_to(self.lab), "Artifact escapes lab")
        return path

    def read(self, name):
        if name not in self.cache:
            self.cache[name] = self.path(name).read_bytes()
        return self.cache[name]

    def verify_unchanged(self):
        for name, raw in self.cache.items():
            require(self.path(name).read_bytes() == raw, f"Artifact changed during audit: {name}")


class Audit:
    def __init__(self, store):
        self.store, self.hashes = store, {}

    def raw(self, path):
        # Normalize logical input paths too, so a memory-store test cannot mask
        # traversal accepted by the production file implementation.
        require(isinstance(path, str) and path and "\\" not in path, "Noncanonical artifact path")
        require(not Path(path).is_absolute() and ":" not in path and ".." not in Path(path).parts,
                "Artifact path must be relative and lab-contained")
        raw = self.store.read(path)
        self.hashes[path] = digest_bytes(raw)
        return raw

    def document(self, path):
        value = strict_json(self.raw(path))
        require(isinstance(value, dict), f"Expected JSON object: {path}")
        return value

    def match_file(self, path, expected):
        require(is_hash(expected), f"Invalid declared hash: {path}")
        require(digest_bytes(self.raw(path)) == expected, f"Actual file hash mismatch: {path}")


def matches(row, expected, label):
    for key, value in expected.items():
        require(row.get(key) == value and (type(value) not in (bool, int) or type(row.get(key)) is type(value)),
                f"{label}: identity mismatch {key}")


def outcome(row):
    rewards, seat, margin = row.get("rewards"), row["seat"], row.get("margin")
    require(isinstance(rewards, list) and len(rewards) == 2 and all(number(v) for v in rewards),
            "Invalid recorded rewards")
    require(number(margin) and margin == rewards[seat] - rewards[1 - seat], "Reward/margin mismatch")
    require(isinstance(row.get("statuses"), list) and len(row["statuses"]) == 2,
            "Missing recorded statuses")
    require(isinstance(row.get("errors"), list) and isinstance(row.get("frames"), int),
            "Missing failure accounting")
    clean = row["statuses"] == ["DONE", "DONE"] and row["frames"] == 720 and not row["errors"]
    return {"score": 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5,
            "margin": margin, "rewards": rewards, "clean": clean,
            "statuses": row["statuses"], "frames": row["frames"], "errors": row["errors"]}


def audit_freeze(audit, path):
    freeze = audit.document(path)
    matches(freeze, {"schema": "portfolio-track-freeze-v1", "split": "development",
                    "engine_sha256": ENGINE_HASH, "feature_schema_sha256": schema_digest()}, "Freeze")
    require(freeze.get("seeds") == list(SEEDS), "Not the pre-registered four-seed initial pilot")
    budget = freeze.get("max_new_games")
    require(isinstance(budget, int) and not isinstance(budget, bool) and 96 <= budget <= 256,
            "Invalid frozen pilot budget")
    for key, source in SOURCE_PATHS.items():
        audit.match_file(source, freeze.get(key))
    audit.match_file(BASELINE_PATH, BASELINE_HASH)
    for variant in VARIANTS:
        audit.match_file(f"experiments/track-portfolio-20260912/{variant}/main.py",
                         freeze.get("variant_hashes", {}).get(variant))
    prefix = freeze.get("prefix_audit", {})
    matches(prefix, {"approved": True, "path": "reports/p3-prefix-audit.json"}, "Prefix approval")
    audit.match_file(prefix["path"], prefix.get("sha256"))
    require(audit.document(prefix["path"]).get("approved") is True, "Prefix document does not approve")
    registered = {}
    for pool_path in ("opponent-pool-p2.json", "opponent-pool-p2-stress.json"):
        for opponent in audit.document(pool_path)["opponents"]:
            name = opponent["name"]
            if name in OPPONENTS:
                identity = {k: opponent[k] for k in ("path", "sha256", "family")}
                require(name not in registered or registered[name] == identity, "Conflicting pool entries")
                registered[name] = identity
    require(set(freeze.get("opponents", {})) == set(OPPONENTS), "Freeze must contain exactly six opponents")
    for name in OPPONENTS:
        item = freeze["opponents"][name]
        require(item == registered.get(name), f"Freeze/pool opponent mismatch: {name}")
        require(item["family"] == FAMILIES[name], f"Source-family inflation: {name}")
        audit.match_file(item["path"], item["sha256"])
    return freeze


def audit_control(audit, reference, opponent, seed, seat):
    require(isinstance(reference, dict), "Missing baseline comparator")
    name = opponent["name"]
    key = f"{name}-{seed}-{seat}-baseline.json"
    path = f"results/terminal-20260912/development/{key}"
    matches(reference, {"source": "read_only_reused_P2_control", "path": path,
                        "candidate_sha256": BASELINE_HASH, "prefix71": None, "predecision72": None}, "Comparator reference")
    require("prefix71" in reference and "predecision72" in reference, "Comparator missingness not explicit")
    require(bool(reference.get("prefix_missingness")) and bool(reference.get("comparability_warning")),
            "Comparator instrument/entrypoint caveat missing")
    audit.match_file(path, reference.get("result_sha256"))
    row = audit.document(path)
    matches(row, {"variant": "baseline", "candidate_path": BASELINE_PATH, "candidate_sha256": BASELINE_HASH,
                  "opponent": name, "opponent_path": opponent["path"], "opponent_sha256": opponent["sha256"],
                  "family": opponent["family"], "seed": seed, "seat": seat, "split": "development",
                  "evidence": "closed_loop", "engine_sha256": ENGINE_HASH, "key": key}, "P2 control")
    require(row.get("runner_sha256") in OLD_RUNNERS, "Unrecognized historical control runner")
    result = outcome(row)
    matches(reference, {"runner_sha256": row["runner_sha256"], "rewards": row["rewards"],
                        "margin": row["margin"], "clean": result["clean"],
                        "entrypoint": row.get("entrypoint", "legacy_explicit_module_agent_not_recorded")}, "Comparator payload")
    return row, result


def audit_features(row):
    errors = []
    capture = row.get("predecision72")
    if not isinstance(capture, dict):
        return {"valid": False, "issues": ["missing_action72_capture"], "values": None}
    if capture.get("phase") != "before candidate action-72 decision, after prior turn's town/decay/night":
        errors.append("wrong_action72_capture_phase")
    snap = capture.get("feature_snapshot")
    if not isinstance(snap, dict):
        return {"valid": False, "issues": ["missing_action72_snapshot"], "values": None}
    if capture.get("public_feature_sha256") != json_digest(snap):
        errors.append("feature_content_hash_mismatch")
    if (set(snap) != {"schema", "schema_sha256", "capture_action_step", "valid", "values", "error"}
            or snap.get("schema") != SCHEMA or snap.get("schema_sha256") != schema_digest()
            or type(snap.get("capture_action_step")) is not int or snap["capture_action_step"] != 72):
        errors.append("feature_schema_or_step_mismatch")
    values = snap.get("values")
    if snap.get("valid") is not True or snap.get("error") is not None:
        errors.append("feature_extractor_marked_invalid")
    if not isinstance(values, dict) or set(values) != set(FEATURE_NAMES):
        errors.append("feature_whitelist_violation")
    elif not all(number(v) and v >= 0 for v in values.values()):
        errors.append("feature_nonfinite_nonnumeric_or_negative")
    if capture.get("observation_history_contiguous") is not True or capture.get("eligible_selector_input") is not True:
        errors.append("ineligible_action72_history")
    history = row.get("observation_history", {})
    if (type(history.get("first_step")) is not int or history["first_step"] != 0
            or type(history.get("last_step")) is not int or history["last_step"] < 72):
        errors.append("recorded_history_does_not_support_action72_eligibility")
    return {"valid": not errors, "issues": errors, "values": values if not errors else None,
            "canonical_values_sha256": json_digest(values) if not errors else None}


def activation(row):
    seat = str(row["seat"])
    def checkpoint(step):
        return row.get("route_checkpoints", {}).get(str(step), {})
    def diag(check):
        return check.get("portfolio_diagnostics", {}).get("seats", {}).get(seat, {})
    entry = diag(checkpoint(72)).get("entry", {})
    decision = diag(checkpoint(168)).get("expert_decision", {})
    expected = "low" if row["variant"] == "v5-low-file" else "high"
    entered = entry.get("step") == 72 and entry.get("mode") == "forced_v5_low"
    entered = entered and checkpoint(72).get("baseline_route_state", {}).get("v5_gate") is True
    low_prefix = all(checkpoint(s).get("baseline_route_state", {}).get("v5_expert") is None
                     and bool(checkpoint(s)) for s in (72, 167))
    fixed = decision.get("step") == 168 and decision.get("expert") == expected and decision.get("mode") == "fixed_probe"
    fixed = fixed and checkpoint(168).get("baseline_route_state", {}).get("v5_expert") == expected
    final = row.get("route_diagnostics", {}).get("portfolio_diagnostics", {})
    sticky = row.get("route_diagnostics", {}).get("baseline_route_state", {}).get("v5_expert") == expected
    return {"entered72": entered, "low_through167_checkpoints": low_prefix, "fixed_expert168": fixed,
            "final_expert_sticky": sticky, "fallback_free": final.get("fallback_count") == 0,
            "history_contiguous_to_end": row.get("observation_history", {}).get("contiguous_from_zero") is True,
            "tested": entered and low_prefix and fixed and sticky, "fallback_count": final.get("fallback_count"),
            "fallback_reasons": final.get("fallback_reasons", {})}


def economic(row):
    seat = row["seat"]
    result = {}
    for key in ("actual_sales", "sale_revenue", "market_spending"):
        raw = row.get(key)
        result[key] = raw[seat] if isinstance(raw, list) and len(raw) == 2 else None
    result["phase_flows"] = {phase: entries[seat] for phase, entries in row.get("phase_flows", {}).items()
                             if isinstance(entries, list) and len(entries) == 2}
    final = row.get("final_after_market", {})
    result["final_after_market"] = {"step": final.get("step"), **{
        key: final[key][seat] if isinstance(final.get(key), list) and len(final[key]) == 2 else None
        for key in ("shed", "cargo_totals")}}
    return result


def phase_reconciles(row):
    phases = row.get("phase_flows")
    if not isinstance(phases, dict) or not phases or not set(phases) <= set(PHASES):
        return False
    for seat in (0, 1):
        for phase_key, total_key in (("actual_sales", "actual_sales"), ("sale_revenue", "sale_revenue"),
                                     ("unit_purchase_spending", "market_spending")):
            total = Counter()
            for entries in phases.values():
                if not isinstance(entries, list) or len(entries) != 2 or not isinstance(entries[seat], dict):
                    return False
                part = entries[seat].get(phase_key)
                if not isinstance(part, dict) or not all(number(v) and v >= 0 for v in part.values()):
                    return False
                total.update(part)
            recorded = row.get(total_key)
            if not isinstance(recorded, list) or len(recorded) != 2 or total != Counter(recorded[seat]):
                return False
    return True


def opponent_callable_compatible(row):
    recorded = row.get("opponent_entrypoint_audit", {})
    identical = row.get("opponent_agent_is_entrypoint") is True and recorded.get("is_module_agent") is True
    forwarder = (row["opponent"] == "seyam"
                 and row["opponent_sha256"] == "4c02a323b0939e8f99df69dc6c23026946b033b0d831c79216ffac0ded9c8e60"
                 and row.get("opponent_entrypoint_name") == "_v18s_submission_entrypoint"
                 and recorded.get("known_source_equivalent_forwarder") is True)
    return identical or forwarder


def prefix_compare(low, high, step=71):
    a, b = low.get(f"prefix{step}"), high.get(f"prefix{step}")
    fields = ("raw_sha256", "gameplay_sha256")
    present = all(isinstance(x, dict) and all(is_hash(x.get(k)) for k in fields) for x in (a, b))
    expected_phase = f"step-{step} after market, BEFORE town consumption, decay and end-of-day"
    return {"both_recorded": present,
            "gameplay_equal": a["gameplay_sha256"] == b["gameplay_sha256"] if present else None,
            "raw_equal": a["raw_sha256"] == b["raw_sha256"] if present else None,
            "phase_equal": a.get("phase") == b.get("phase") == expected_phase if present else None,
            "overage_low": a.get("runtime_overage_seconds") if isinstance(a, dict) else None,
            "overage_high": b.get("runtime_overage_seconds") if isinstance(b, dict) else None}


def resource_row(row):
    profile = row.get("own_call_profile")
    valid = isinstance(profile, list) and bool(profile) and all(
        isinstance(p, dict) and all(number(p.get(k)) and p[k] >= 0 for k in ("wall_ms", "cpu_ms"))
        for p in profile)
    outer = row.get("max_call_ms")
    outer_own = outer[row["seat"]] if isinstance(outer, list) and len(outer) == 2 else None
    if not number(outer_own) or outer_own < 0:
        outer_own = None
    prefix_overage = {}
    for step in (71, 167):
        prefix = row.get(f"prefix{step}") or {}
        pair = prefix.get("runtime_overage_seconds")
        if isinstance(pair, list) and len(pair) == 2:
            value = pair[row["seat"]]
            prefix_overage[str(step)] = value if number(value) else None
    return {"own_outer_max_call_ms": outer_own, "profile_valid": valid,
            "inner_calls": len(profile) if valid else None,
            "inner_wall_total_ms": sum(p["wall_ms"] for p in profile) if valid else None,
            "inner_cpu_total_ms": sum(p["cpu_ms"] for p in profile) if valid else None,
            "inner_wall_max_ms": max(p["wall_ms"] for p in profile) if valid else None,
            "inner_cpu_max_ms": max(p["cpu_ms"] for p in profile) if valid else None,
            "inner_wall_calls_over_1000ms": sum(p["wall_ms"] > 1000 for p in profile) if valid else None,
            "job_cpu_seconds": row.get("job_cpu_seconds"),
            "timing_scope": row.get("timing_scope", "historical instrumentation; not comparable to new inner-call timing"),
            "recorded_prefix_remaining_overage_seconds": prefix_overage,
            "final_remaining_overage_seconds": None,
            "final_overage_missingness": "No terminal overage recorded; prefix values are not final remaining budget."}


def resource_summary(cases):
    result = {}
    for arm in ("baseline", *VARIANTS):
        rows = [c["resources"][arm] for c in cases]
        def maximum(key):
            values = [r[key] for r in rows if number(r.get(key))]
            return max(values) if values else None
        def total(key):
            values = [r[key] for r in rows if number(r.get(key))]
            return sum(values) if values else None
        result[arm] = {"rows": len(rows), "profile_recorded_rows": sum(r["profile_valid"] for r in rows),
                       "max_own_outer_call_ms": maximum("own_outer_max_call_ms"),
                       "outer_game_maxima_over_1000ms": sum(number(r["own_outer_max_call_ms"]) and r["own_outer_max_call_ms"] > 1000 for r in rows),
                       "max_inner_wall_ms": maximum("inner_wall_max_ms"), "max_inner_cpu_ms": maximum("inner_cpu_max_ms"),
                       "recorded_inner_wall_total_ms": total("inner_wall_total_ms"),
                       "recorded_inner_cpu_total_ms": total("inner_cpu_total_ms"),
                       "recorded_inner_calls": total("inner_calls"),
                       "recorded_inner_wall_calls_over_1000ms": total("inner_wall_calls_over_1000ms"),
                       "final_remaining_overage_recorded_rows": 0,
                       "scope": "Local recorded timing only; different historical instrumentation; not resource/release certification."}
    return result


def native168_case(low, high):
    prefix71, prefix167 = prefix_compare(low, high), prefix_compare(low, high, 167)
    a, b = low.get("predecision168"), high.get("predecision168")
    def valid(capture):
        shops = capture.get("public_shop_sequence") if isinstance(capture, dict) else None
        return (isinstance(capture, dict) and capture.get("public_shops_valid") is True
                and capture.get("observation_history_contiguous") is True
                and capture.get("phase") == "before candidate action-168 decision, after prior town/decay/night"
                and isinstance(shops, list) and len(shops) == 2 and all(s in SHOPS for s in shops))
    shops_equal = valid(a) and valid(b) and a["public_shop_sequence"] == b["public_shop_sequence"]
    eligible = shops_equal and all(p["gameplay_equal"] is True and p["phase_equal"] is True for p in (prefix71, prefix167))
    shops = a["public_shop_sequence"] if shops_equal else None
    selected = None
    if eligible:
        high_rule = "YARN_STORE" in shops and shops[:2] != ["ICE_CREAM_SHOP", "YARN_STORE"]
        selected = "v5-high-file" if high_rule else "v5-low-file"
    return {"eligible": eligible, "prefix167_low_high": prefix167, "public168_shops_equal_valid": shops_equal,
            "public168_shop_sequence": shops, "selected_arm_by_native_rule": selected,
            "diagnostic_only_not_action72_predictors": True}


def native168_summary(cases):
    eligible = [c for c in cases if c["secondary_native168"]["eligible"]]
    def arm(c):
        return c["secondary_native168"]["selected_arm_by_native_rule"]
    return {"eligible_cases": len(eligible), "ineligible_cases": len(cases) - len(eligible),
            "rule": "At168 high if observed YARN_STORE, except first two ICE_CREAM_SHOP/YARN_STORE; else low.",
            "selected_counts": dict(Counter(arm(c) for c in eligible)),
            "potential_family_weighted_outcome": weighted(eligible, lambda c: c["outcomes"][arm(c)]["score"]),
            "same_subset_baseline_outcome": weighted(eligible, lambda c: c["outcomes"]["baseline"]["score"]),
            "potential_same_case_score_delta": weighted(eligible, lambda c: c["outcomes"][arm(c)]["score"] - c["outcomes"]["baseline"]["score"]),
            "actual_adaptive_rollouts": 0, "achievable_uplift_claim": False,
            "scope": "Recombined fixed-arm outcomes only where 71/167 gameplay hashes and predecision168 shops match. Partial coverage is not the all-case primary result; no adaptive rollout has been executed."}


def observable_ceiling(dataset):
    """Tighter post-hoc ceiling: a deterministic selector cannot split identical X."""
    cells, opponent_counts, family_members = defaultdict(list), Counter(), defaultdict(set)
    for row in dataset:
        meta = row["metadata_never_predictors"]
        cells[row["predictor_sha256"]].append(row)
        opponent_counts[meta["opponent"]] += 1
        family_members[meta["family"]].add(meta["opponent"])
    totals = Counter()
    cell_maximum = 0.
    for rows in cells.values():
        arm_sums = Counter()
        for row in rows:
            meta = row["metadata_never_predictors"]
            weight = 1 / (len(family_members) * len(family_members[meta["family"]]) * opponent_counts[meta["opponent"]])
            for arm, score in row["outcome_vector"].items():
                arm_sums[arm] += weight * score
                totals[arm] += weight * score
        cell_maximum += max(arm_sums.values())
    best = max(totals.values()) if totals else None
    return {"eligible_subset_cases": len(dataset), "identical_feature_cells": len(cells),
            "identical_feature_cells_with_different_outcome_vectors": sum(len({canonical(r["outcome_vector"]) for r in rows}) > 1 for rows in cells.values()),
            "best_fixed_score_on_eligible_subset": best,
            "feature_cell_oracle_score_on_eligible_subset": cell_maximum if dataset else None,
            "feature_cell_oracle_minus_best_fixed": max(0., cell_maximum - best) if dataset else None,
            "scope": "Post-hoc unlimited-capacity deterministic feature-cell ceiling; not a fitted shallow selector or held-out result."}


def weighted(cases, value):
    # Mean cases within opponent; mean opponents within family; mean families.
    opponents = defaultdict(list)
    for case in cases:
        opponents[case["opponent"]].append(value(case))
    families = defaultdict(list)
    for name, values in opponents.items():
        families[FAMILIES[name]].append(mean(values))
    return mean(mean(values) for values in families.values()) if families else None


def summary(cases):
    arms = ("baseline", *VARIANTS)
    result = {"cases": len(cases), "seed_blocks": len({c["seed"] for c in cases}), "arms": {}}
    for arm in arms:
        scores = [c["outcomes"][arm]["score"] for c in cases]
        deltas = [c["outcomes"][arm]["score"] - c["outcomes"]["baseline"]["score"] for c in cases]
        result["arms"][arm] = {
            "outcomes": dict(Counter("win" if x == 1 else "tie" if x == .5 else "loss" for x in scores)),
            "points": sum(scores), "family_weighted_score": weighted(cases, lambda c: c["outcomes"][arm]["score"]),
            "family_weighted_score_delta": weighted(cases, lambda c: c["outcomes"][arm]["score"] - c["outcomes"]["baseline"]["score"]),
            "mean_margin_delta": mean(c["outcomes"][arm]["margin"] - c["outcomes"]["baseline"]["margin"] for c in cases) if cases else None,
            "family_weighted_margin_delta": weighted(cases, lambda c: c["outcomes"][arm]["margin"] - c["outcomes"]["baseline"]["margin"]),
            "outcome_upgrades": sum(d > 0 for d in deltas), "outcome_downgrades": sum(d < 0 for d in deltas),
            "win_to_loss": sum(c["outcomes"]["baseline"]["score"] == 1 and c["outcomes"][arm]["score"] == 0 for c in cases),
            "unclean_cases": sum(not c["outcomes"][arm]["clean"] for c in cases),
        }
    if not cases:
        result["hindsight_diagnostic"] = None
        return result
    fixed = {arm: result["arms"][arm]["family_weighted_score"] for arm in arms}
    best = max(fixed.values())
    oracle = weighted(cases, lambda c: max(c["outcomes"][arm]["score"] for arm in arms))
    result["hindsight_diagnostic"] = {
        "best_fixed_arms": [a for a in arms if fixed[a] == best], "best_fixed_score": best,
        "casewise_oracle_score": oracle, "oracle_minus_best_fixed": oracle - best,
        "achievable_uplift_claim": False, "trained_model": False,
        "scope": "Post-hoc maxima on dependent development cases; not a deployable selector or validation.",
        "low_beats_high_cases": sum(c["outcomes"][VARIANTS[0]]["score"] > c["outcomes"][VARIANTS[1]]["score"] for c in cases),
        "high_beats_low_cases": sum(c["outcomes"][VARIANTS[1]]["score"] > c["outcomes"][VARIANTS[0]]["score"] for c in cases),
    }
    return result


def build_report(store, freeze_path, result_dir):
    """Read a complete initial-pilot grid through an injectable byte store."""
    audit = Audit(store)
    freeze = audit_freeze(audit, freeze_path)
    freeze_hash = audit.hashes[freeze_path]
    cases, dataset = [], []
    controls = set()
    for name in OPPONENTS:
        opponent = dict(freeze["opponents"][name], name=name)
        for seed in SEEDS:
            for seat in (0, 1):
                rows, outcomes, features, coverage, economics, row_hashes, resources = {}, {}, {}, {}, {}, {}, {}
                refs = []
                for variant in VARIANTS:
                    key = f"{name}-{seed}-{seat}-{variant}.json"
                    path = f"{result_dir.rstrip('/')}/{key}"
                    row = audit.document(path)
                    expected = {"key": key, "variant": variant, "candidate_path": f"experiments/track-portfolio-20260912/{variant}/main.py",
                                "candidate_sha256": freeze["variant_hashes"][variant], "opponent": name,
                                "opponent_path": opponent["path"], "opponent_sha256": opponent["sha256"],
                                "family": opponent["family"], "seed": seed, "seat": seat, "split": "development",
                                "evidence": "closed_loop", "freeze_path": freeze_path, "freeze_sha256": freeze_hash,
                                "entrypoint": "official_get_last_callable", "opponent_entrypoint": "official_get_last_callable",
                                "entrypoint_name": "_p3_portfolio_entrypoint", "candidate_agent_is_entrypoint": False,
                                "feature_schema_sha256": schema_digest()}
                    expected.update({k: freeze[k] for k in SOURCE_PATHS})
                    matches(row, expected, key)
                    require(canonical(row.get("feature_schema")) == canonical(FEATURE_SCHEMA), "Row feature schema changed")
                    control, base_outcome = audit_control(audit, row.get("baseline_comparator"), opponent, seed, seat)
                    refs.append(row["baseline_comparator"])
                    controls.add(refs[-1]["path"])
                    outcomes["baseline"], outcomes[variant] = base_outcome, outcome(row)
                    features[variant], coverage[variant] = audit_features(row), activation(row)
                    coverage[variant]["phase_flow_reconciles"] = phase_reconciles(row)
                    coverage[variant]["phase_flow_audit_record_agrees"] = row.get("phase_flow_audit", {}).get("consistent") is coverage[variant]["phase_flow_reconciles"]
                    coverage[variant]["opponent_callable_compatible_with_old_control"] = opponent_callable_compatible(row)
                    economics["baseline"], economics[variant] = economic(control), economic(row)
                    resources["baseline"], resources[variant] = resource_row(control), resource_row(row)
                    row_hashes[variant], rows[variant] = audit.hashes[path], row
                require(refs[0] == refs[1], "Low/high refer to different controls")
                prefix = prefix_compare(rows[VARIANTS[0]], rows[VARIANTS[1]])
                valid_features = all(f["valid"] for f in features.values())
                feature_equal = valid_features and features[VARIANTS[0]]["values"] == features[VARIANTS[1]]["values"]
                eligible = feature_equal and prefix["gameplay_equal"] is True and prefix["phase_equal"] is True
                case = {"opponent": name, "family": opponent["family"], "seed": seed, "seat": seat,
                        "outcomes": outcomes, "same_case_deltas": {
                            arm: {"score": outcomes[arm]["score"] - outcomes["baseline"]["score"],
                                  "margin": outcomes[arm]["margin"] - outcomes["baseline"]["margin"]} for arm in VARIANTS},
                        "prefix71_low_high": prefix, "action72_features_valid": valid_features,
                        "action72_features_equal": feature_equal, "counterfactual_dataset_eligible": eligible,
                        "feature_issues": {arm: features[arm]["issues"] for arm in VARIANTS},
                        "activation": coverage, "economics_diagnostic": economics, "resources": resources, "result_hashes": row_hashes,
                        "secondary_native168": native168_case(rows[VARIANTS[0]], rows[VARIANTS[1]]),
                        "baseline_reference": refs[0], "baseline_prefix71_equal": None,
                        "baseline_action72_features_equal": None}
                cases.append(case)
                if eligible:
                    dataset.append({"predictors": features[VARIANTS[0]]["values"],
                                    "predictor_sha256": features[VARIANTS[0]]["canonical_values_sha256"],
                                    "outcome_vector": {a: outcomes[a]["score"] for a in ("baseline", *VARIANTS)},
                                    "metadata_never_predictors": {"opponent": name, "family": opponent["family"], "seed": seed,
                                                                  "seat": seat, "result_hashes": row_hashes,
                                                                  "all_clean": all(o["clean"] for o in outcomes.values()),
                                                                  "both_probes_tested": all(x["tested"] for x in coverage.values())}})
    require(len(cases) == 48 and len(controls) == 48, "Unexpected control/case count")
    all_summary = summary(cases)
    hard_gates = all(all(o["clean"] for o in c["outcomes"].values())
                     and c["counterfactual_dataset_eligible"]
                     and all(x["tested"] and x["fallback_free"] and x["history_contiguous_to_end"] and x["phase_flow_reconciles"]
                             and x["phase_flow_audit_record_agrees"] and x["opponent_callable_compatible_with_old_control"]
                             for x in c["activation"].values()) for c in cases)
    observable = observable_ceiling(dataset)
    gap = all_summary["hindsight_diagnostic"]["oracle_minus_best_fixed"]
    fixed_gain = all_summary["hindsight_diagnostic"]["best_fixed_score"] - all_summary["arms"]["baseline"]["family_weighted_score"]
    tested = sum(x["tested"] for c in cases for x in c["activation"].values())
    decision = ("zero_activation_untested_do_not_train" if tested == 0 else
                "evidence_or_mechanism_gate_failed_do_not_train" if not hard_gates else
                "fixed_expert_merits_fresh_evaluation_no_ml_needed" if gap <= 1e-12 and fixed_gain > 1e-12 else
                "no_official_outcome_complementarity_do_not_train" if gap <= 1e-12 else
                "no_observable72_headroom_do_not_train" if observable["feature_cell_oracle_minus_best_fixed"] <= 1e-12 else
                "descriptive_complementarity_parent_review_before_any_training")
    report = {"schema": "p3-probe-report-v1", "new_probe_games": 96, "reused_control_games": 48,
              "matched_cases": 48, "seed_blocks": 4, "independent_strategy_families": 5,
              "all_cases_primary": True, "failed_cases_filtered": False, "hard_gates_passed": hard_gates,
              "hard_gate_scope": "Dataset and observed mechanism gate for considering training only; not release, runtime, sandbox, or generalization certification.",
              "metric": "Recorded terminal reward outcome: win=1,tie=.5,loss=0; retain failures and gate them separately.",
              "weighting": "Equal cases within opponent; COK/Arlene equal within route family; then five families equal.",
              "combined_five_family": all_summary,
              "original_five_opponents": summary([c for c in cases if c["opponent"] != "arlene"]),
              "arlene_stress_only": summary([c for c in cases if c["opponent"] == "arlene"]),
              "by_opponent": {n: summary([c for c in cases if c["opponent"] == n]) for n in OPPONENTS},
              "by_seed_block": {str(s): summary([c for c in cases if c["seed"] == s]) for s in SEEDS},
              "by_seat": {str(s): summary([c for c in cases if c["seat"] == s]) for s in (0, 1)},
              "resources_diagnostic": resource_summary(cases),
              "secondary_native168_rule": native168_summary(cases),
              "coverage": {"tested_probe_rows": tested, "untested_probe_rows": 96 - tested,
                           "eligible_counterfactual_cases": len(dataset),
                           "equal_gameplay_prefix_cases": sum(c["prefix71_low_high"]["gameplay_equal"] is True for c in cases),
                           "equal_raw_prefix_cases": sum(c["prefix71_low_high"]["raw_equal"] is True for c in cases),
                           "raw_prefix_differences_are_not_automatically_gameplay_differences": True,
                           "historical_control_prefix_and_features_missing_cases": 48},
              "counterfactual_dataset": {"schema": SCHEMA, "feature_schema_sha256": schema_digest(), "rows": dataset,
                                         "model_trained": False, **observable,
                                         "metadata_must_not_be_used_as_predictors": True,
                                         "failure_rows_retained_when_feature_eligible": True},
              "cases": cases, "decision": decision, "promotion": False, "submission": False,
              "limits": ["Four reused development seeds; arms/seats/related opponents are dependent, not 144 independent scenarios.",
                         "Historical P2 controls have different callers/timing and no action71/72 snapshots; prefix equivalence to controls is unavailable.",
                         "Snapshot whitelist/hash validation does not reconstruct unrecorded observations or prove all source semantics.",
                         "Casewise oracle and best fixed are post-hoc diagnostics, not achievable uplift or independent validation.",
                         "Actual unit-commit flows omit HIRE/BUY_LAND atomic costs; requested work is not successful harvest.",
                         "Phase diagnostics are recorded only for new probes; no fabricated historical phase control.",
                         "No rating mapping, learned selector, release confirmation, or unknown-opponent generalization claim."],
              "source_hashes": audit.hashes}
    store.verify_unchanged()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", required=True, help="Lab-relative frozen manifest")
    parser.add_argument("--results", default="results/portfolio-20260912/development", help="Lab-relative result directory")
    parser.add_argument("--output", help="Optional new lab-relative report; refuses overwrite")
    args = parser.parse_args()
    store = FileStore()
    result = build_report(store, args.freeze, args.results)
    result["analysis_code_sha256"] = digest_bytes(Path(__file__).read_bytes())
    if args.output:
        destination = store.path(args.output)
        require(destination.parent.is_dir(), "Output parent must already exist")
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
    print(json.dumps({"hard_gates_passed": result["hard_gates_passed"], "coverage": result["coverage"],
                      "summary": result["combined_five_family"], "decision": result["decision"]}, allow_nan=False))


if __name__ == "__main__":
    main()
