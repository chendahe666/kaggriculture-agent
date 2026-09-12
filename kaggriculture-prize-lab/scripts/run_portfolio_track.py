"""Frozen, resumable P3 runner. Default is validation/planning, never execution.

Only --execute after a hash-bound approved prefix audit can start games. Each
job receives a fresh spawned process. Neither frozen P2 sources/results nor old
controls are rewritten. Public feature capture is isolated in its own module.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import inspect
import json
import multiprocessing
import os
from pathlib import Path
import platform
import sys
import time

from portfolio_features import FEATURE_SCHEMA, SCHEMA, extract_public72, schema_digest
import portfolio_features

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / "results/portfolio-20260912"
ENGINE_PATH = LAB / "official/installed-1.32.7/kaggriculture.py"
ENGINE_HASH = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
BASELINE_PATH = "public-baseline-v10/main.py"
BASELINE_HASH = "1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01"
PREFIX_AUDIT_PATH = "reports/p3-prefix-audit.json"
ALLOWED_OPPONENTS = ("cok", "seyam", "lonespear", "deepesh", "maverick", "arlene")
OLD_BASELINE_RUNNERS = {
    "1205a7ef72285e7e93caf05d84fbb635ebdce8a1c2046bea1a96c7d92f1e44c9",
    "2ce7669a5bf00f186f39481505db37cbae56c55d2f21df0c75150695302bc502",
    "4518551bccfb2c2c39a30c928da6d0b16016eb3ee1b18b0dbcb95ec19d87054c",
}
ROUTE_FIELDS = ("last_step", "legacy", "label", "third_yarn_milk", "v5_gate", "v5_shops", "v5_expert")
TIMING_SCOPE = "Inner candidate-call wall/CPU, including predecision feature capture but excluding policy source loading and some framework overhead; local callable execution, not official sandbox limits."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def lab_path(value):
    path = Path(value)
    resolved = (path if path.is_absolute() else LAB / path).resolve()
    require(resolved.is_relative_to(LAB.resolve()), "Path must stay within the lab")
    return resolved


def relative(path):
    return str(lab_path(path).relative_to(LAB.resolve())).replace("\\", "/")


def candidate_path(variant):
    require(isinstance(variant, str) and variant and all(c.isalnum() or c in "-_" for c in variant), "Invalid variant name")
    return BASELINE_PATH if variant == "baseline" else f"experiments/track-portfolio-20260912/{variant}/main.py"


def source_hashes():
    return {"runner_sha256": digest(__file__), "features_sha256": digest(portfolio_features.__file__),
            "research_cycle_sha256": digest(LAB / "scripts/research_cycle.py"), "engine_sha256": digest(ENGINE_PATH)}


def load_pool(paths):
    opponents = {}
    for path in paths:
        for opponent in read_json(lab_path(path))["opponents"]:
            name = opponent["name"]
            if name not in ALLOWED_OPPONENTS:
                continue
            if name in opponents:
                require(all(opponents[name][k] == opponent[k] for k in ("path", "sha256", "family")), f"Conflicting pool identity: {name}")
            opponents[name] = opponent
    return opponents


def validate_freeze(freeze, opponents, variants, seeds, split, sources):
    require(split == "development", "P3 runner currently supports development probes only; confirmation remains unopened")
    require(freeze.get("schema") == "portfolio-track-freeze-v1", "Missing portfolio freeze schema")
    require(freeze.get("split") == split, "Freeze split mismatch")
    require(len(set(seeds)) == len(seeds) and all(seed in freeze.get("seeds", []) for seed in seeds), "Unfrozen/duplicate seed")
    require(sources["engine_sha256"] == ENGINE_HASH, "Reference engine changed")
    for key, value in sources.items():
        require(freeze.get(key) == value, f"Freeze source mismatch: {key}")
    require(freeze.get("feature_schema_sha256") == schema_digest(), "Feature schema mismatch")
    require(isinstance(freeze.get("max_new_games"), int) and 0 < freeze["max_new_games"] <= 256, "Missing bounded game authorization")
    audit = freeze.get("prefix_audit", {})
    require(audit.get("approved") is True and audit.get("path") == PREFIX_AUDIT_PATH, "Prefix audit not approved at required path")
    require(digest(lab_path(audit["path"])) == audit.get("sha256"), "Prefix audit hash mismatch")
    audit_record = read_json(lab_path(audit["path"]))
    require(audit_record.get("approved") is True, "Prefix audit document does not approve execution")
    require(len(set(variants)) == len(variants), "Duplicate variant")
    for variant in variants:
        file_hash = digest(lab_path(candidate_path(variant)))
        require(freeze.get("variant_hashes", {}).get(variant) == file_hash, f"Unfrozen candidate: {variant}")
        if variant == "baseline":
            require(file_hash == BASELINE_HASH, "Baseline is not frozen COK")
    for name, opponent in opponents.items():
        require(name in ALLOWED_OPPONENTS, "Unapproved opponent name")
        expected = {k: opponent[k] for k in ("path", "sha256", "family")}
        require(freeze.get("opponents", {}).get(name) == expected, f"Unfrozen opponent: {name}")
        require(digest(lab_path(opponent["path"])) == opponent["sha256"], f"Opponent bytes changed: {name}")


def comparator_reference(path, opponent, seed, seat):
    """Old controls are references, not fabricated new-track result records."""
    row = read_json(path)
    expected = {"variant": "baseline", "candidate_path": BASELINE_PATH, "candidate_sha256": BASELINE_HASH,
                "opponent": opponent["name"], "opponent_path": opponent["path"],
                "opponent_sha256": opponent["sha256"], "family": opponent["family"],
                "seed": seed, "seat": seat, "split": "development", "evidence": "closed_loop",
                "engine_sha256": ENGINE_HASH, "key": f"{opponent['name']}-{seed}-{seat}-baseline.json"}
    for key, value in expected.items():
        require(row.get(key) == value, f"Comparator mismatch: {key} in {path.name}")
    require(row.get("runner_sha256") in OLD_BASELINE_RUNNERS, "Unknown historical baseline runner")
    require(row["margin"] == row["rewards"][seat] - row["rewards"][1 - seat], "Comparator reward/margin mismatch")
    return {"source": "read_only_reused_P2_control", "path": relative(path), "result_sha256": digest(path),
            "candidate_sha256": row["candidate_sha256"], "runner_sha256": row["runner_sha256"],
            "entrypoint": row.get("entrypoint", "legacy_explicit_module_agent_not_recorded"),
            "rewards": row["rewards"], "margin": row["margin"],
            "clean": row["statuses"] == ["DONE", "DONE"] and row["frames"] == 720 and not row["errors"],
            "prefix71": None, "predecision72": None,
            "prefix_missingness": "Historical controls did not record step-71 fingerprints or action-72 features; neither is reconstructed from a later snapshot.",
            "comparability_warning": "Historical controls used different timing instrumentation and may use explicit opponent module.agent. Prefix equivalence cannot be established from these rows."}


def validate_existing(row, job):
    keys = ("key", "variant", "candidate_path", "candidate_sha256", "opponent", "opponent_path", "opponent_sha256",
            "family", "seed", "seat", "split", "freeze_sha256", "runner_sha256", "features_sha256",
            "research_cycle_sha256", "engine_sha256", "feature_schema_sha256")
    for key in keys:
        require(row.get(key) == job[key], f"Existing result identity changed: {job['key']} / {key}")
    require(row.get("entrypoint") == "official_get_last_callable", "Existing result has wrong candidate entrypoint")
    require(row.get("baseline_comparator") == job.get("baseline_comparator"), "Existing comparator reference changed")


def prepare_jobs(variants, seeds, opponents, split, freeze_path, comparator_dir=None):
    freeze_path = lab_path(freeze_path)
    freeze, sources = read_json(freeze_path), source_hashes()
    validate_freeze(freeze, opponents, variants, seeds, split, sources)
    jobs, reused, existing = [], [], []
    for opponent in opponents.values():
        for seed in seeds:
            for seat in (0, 1):
                comparator = None
                if comparator_dir is not None:
                    path = lab_path(comparator_dir) / f"{opponent['name']}-{seed}-{seat}-baseline.json"
                    comparator = comparator_reference(path, opponent, seed, seat)
                    reused.append(comparator)
                for variant in variants:
                    if variant == "baseline" and comparator is not None:
                        continue
                    path = candidate_path(variant)
                    job = {"variant": variant, "candidate_path": path, "candidate_sha256": freeze["variant_hashes"][variant],
                           "opponent_path": opponent["path"], "opponent_sha256": opponent["sha256"],
                           "opponent": opponent["name"], "family": opponent["family"], "seed": seed, "seat": seat,
                           "split": split, "key": f"{opponent['name']}-{seed}-{seat}-{variant}.json",
                           "freeze_path": relative(freeze_path), "freeze_sha256": digest(freeze_path),
                           "feature_schema_sha256": schema_digest(), "baseline_comparator": comparator, **sources}
                    result_path = ROOT / split / job["key"]
                    if result_path.exists():
                        validate_existing(read_json(result_path), job)
                        existing.append(job["key"])
                    else:
                        jobs.append(job)
    saved = list((ROOT / split).glob("*.json")) if (ROOT / split).is_dir() else []
    saved_for_freeze = sum(read_json(path).get("freeze_sha256") == digest(freeze_path) for path in saved)
    validate_budget(len(jobs), saved_for_freeze, freeze["max_new_games"], len(saved))
    require(len({job["key"] for job in jobs}) == len(jobs), "Duplicate job key")
    return jobs, {"pending_games": len(jobs), "existing_games": len(existing), "existing_keys": existing,
                  "reused_baseline_controls": reused, "freeze_sha256": digest(freeze_path),
                  "feature_schema": FEATURE_SCHEMA, "feature_schema_sha256": schema_digest()}


def validate_budget(pending_count, existing_frozen_count, frozen_maximum, all_saved_count):
    require(existing_frozen_count + pending_count <= frozen_maximum, "Existing plus pending games exceed frozen cumulative budget")
    require(all_saved_count + pending_count <= 256, "P3 saved plus pending games exceed 256-game pilot cap")


def phase_flow_audit(row, phase_flows):
    residuals = []
    for seat in (0, 1):
        for final_key, phase_key in (("actual_sales", "actual_sales"), ("sale_revenue", "sale_revenue"),
                                      ("market_spending", "unit_purchase_spending")):
            total = Counter()
            for pair in phase_flows.values():
                total.update(pair[seat][phase_key])
            expected = row[final_key][seat]
            delta = {item: expected.get(item, 0) - total.get(item, 0) for item in set(expected) | set(total)
                     if expected.get(item, 0) != total.get(item, 0)}
            if delta:
                residuals.append({"seat": seat, "field": final_key, "global_minus_phase": delta})
    return {"consistent": not residuals, "residuals": residuals,
            "scope": "Actual successful unit commits; excludes HIRE and BUY_LAND in both spending totals."}


def opponent_entrypoint_audit(function, opponent_name, opponent_hash):
    identical = function.__globals__.get("agent") is function
    seyam_forwarder = (opponent_name == "seyam" and opponent_hash == "4c02a323b0939e8f99df69dc6c23026946b033b0d831c79216ffac0ded9c8e60"
                       and function.__name__ == "_v18s_submission_entrypoint")
    return {"is_module_agent": identical, "known_source_equivalent_forwarder": seyam_forwarder,
            "equivalence_evidence": "Root inspected frozen Seyam source tail: def _v18s_submission_entrypoint(obs): return agent(obs)." if seyam_forwarder
            else "Selected callable is namespace agent." if identical else "Not independently verified equivalent to historical module.agent.",
            "scope": "Source/identity comparison, not a proof that other wrapper/instrumentation differences are behavior-neutral."}


def snapshot_hashes(observations, phase):
    raw = [dict(obs) for obs in observations]
    gameplay = [{k: v for k, v in obs.items() if k != "remainingOverageTime"} for obs in raw]
    return {"raw_sha256": json_digest(raw), "gameplay_sha256": json_digest(gameplay), "phase": phase,
            "gameplay_scope": "All observation fields except remainingOverageTime; only hashes exported, not private raw observations.",
            "runtime_overage_seconds": [obs.get("remainingOverageTime") for obs in raw]}


def route_snapshot(namespace, seat):
    state = namespace.get("_ROUTE_STATE", {}).get(seat, {})
    route = {key: state.get(key) for key in ROUTE_FIELDS}
    diagnostics = namespace.get("_P3_DIAGNOSTICS", {})
    # Take a value copy, not a live mutable reference to the last-callable globals.
    return json.loads(json.dumps({"baseline_route_state": route, "portfolio_diagnostics": diagnostics}, allow_nan=False))


def instrument_candidate(function, seat, call_profile, capture, requested_actions):
    namespace = function.__globals__
    history = {"first_step": None, "last_step": -1, "contiguous_from_zero": True}
    capture["observation_history"] = history
    def measured(observation, configuration):
        tick, cpu = time.perf_counter(), time.process_time()
        step = int(observation["step"])
        try:
            if history["first_step"] is None:
                history["first_step"] = step
            if step != history["last_step"] + 1:
                history["contiguous_from_zero"] = False
            history["last_step"] = step
            if step == 72:
                features = extract_public72(observation)
                capture["predecision72"] = {"phase": "before candidate action-72 decision, after prior turn's town/decay/night",
                                             "feature_snapshot": features, "public_feature_sha256": json_digest(features),
                                             "observation_history_contiguous": history["contiguous_from_zero"],
                                             "eligible_selector_input": features["valid"] and history["contiguous_from_zero"]}
            if step == 168:
                shops = observation.get("town", {}).get("unlocked_shops")
                valid_shops = isinstance(shops, (list, tuple)) and all(shop in portfolio_features.SHOPS for shop in shops)
                capture["predecision168"] = {
                    "phase": "before candidate action-168 decision, after prior town/decay/night",
                    "public_shop_sequence": list(shops) if valid_shops else None, "public_shops_valid": valid_shops,
                    "observation_history_contiguous": history["contiguous_from_zero"],
                    "scope": "Step-168 diagnostic only; never a step-72 predictor or retrospective step-72 feature."}
            action = function(observation, configuration)
            if isinstance(action, dict):
                for op in [action.get("farmer", [])] + list(action.get("hands", []) or []):
                    if isinstance(op, list) and op:
                        requested_actions[str(op[0])] += 1
            if step in (0, 71, 72, 167, 168, 718):
                capture.setdefault("route_checkpoints", {})[str(step)] = route_snapshot(namespace, seat)
            return action
        finally:
            call_profile.append({"step": step, "wall_ms": (time.perf_counter() - tick) * 1000,
                                 "cpu_ms": (time.process_time() - cpu) * 1000})
    return measured


def run_game_configured(players, cfg, engine, make_environment):
    """Independent recorder that preserves the framework's actual configuration.

    The historical research_cycle.run_game wrapper accepted only observation;
    modifying that frozen helper would change old evidence. This implementation
    is intentionally scoped here and is injectable for no-game unit tests.
    """
    durations, wrapped = [[], []], []
    for index, function in enumerate(players):
        signature = inspect.signature(function)
        try:
            signature.bind(None, None)
            takes_config = True
        except TypeError:
            signature.bind(None)
            takes_config = False
        def measured(index=index, function=function, takes_config=takes_config):
            def call(observation, configuration):
                tick = time.perf_counter()
                try:
                    return function(observation, configuration) if takes_config else function(observation)
                finally:
                    durations[index].append((time.perf_counter() - tick) * 1000)
            return call
        wrapped.append(measured())
    env = make_environment("kaggriculture", configuration=cfg, debug=False)
    sales, revenue, floor, failures, spending = ([Counter(), Counter()] for _ in range(5))
    original_market, original_commit = engine._process_market, engine._commit_unit
    farms = []
    def market(state, environment):
        farms[:] = state[0].observation.farms
        return original_market(state, environment)
    def commit(op, item, price, farm, private, market_inventory, shed_capacity=100):
        seat = next(index for index, entry in enumerate(farms) if entry is farm)
        before = farm["money"]
        ok = original_commit(op, item, price, farm, private, market_inventory, shed_capacity)
        if ok and farm["money"] < before:
            spending[seat][op + ":" + str(item)] += before - farm["money"]
        if ok and op == "SELL":
            sales[seat][item] += 1
            revenue[seat][item] += price
            if price == 1:
                floor[seat][item] += 1
        elif not ok:
            failures[seat][op + ":" + str(item)] += 1
        return ok
    engine._process_market, engine._commit_unit = market, commit
    try:
        frames = env.run(wrapped)
    finally:
        engine._process_market, engine._commit_unit = original_market, original_commit
    final = frames[-1]
    errors = [log.get("stderr") for logs in env.logs for log in logs if log.get("stderr")]
    return {"rewards": [float(state.reward or 0) for state in final], "statuses": [state.status for state in final],
            "frames": len(frames), "errors": errors[:5], "actual_sales": sales, "sale_revenue": revenue,
            "floor_units": floor, "failed_market_commits": failures, "market_spending": spending,
            "max_call_ms": [round(max(values or [0]), 3) for values in durations],
            "shops": list(final[0].observation.town.unlocked_shops),
            "terminal_stock": [dict(state.observation.private.shed) for state in final]}


def write_new_result(path, row):
    encoded = (json.dumps(row, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create refuses overwrite, including racing duplicate invocations.
    # A rare interrupted write is preserved and fails resume validation for review.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def run_job(job):
    started = datetime.now(timezone.utc).isoformat()
    tick, cpu = time.perf_counter(), time.process_time()
    sources = source_hashes()
    require(all(job[k] == v for k, v in sources.items()), "Job source drift after dispatch")
    require(digest(lab_path(job["freeze_path"])) == job["freeze_sha256"], "Freeze changed after dispatch")
    require(digest(lab_path(job["candidate_path"])) == job["candidate_sha256"], "Candidate changed after dispatch")
    require(digest(lab_path(job["opponent_path"])) == job["opponent_sha256"], "Opponent changed after dispatch")
    freeze = read_json(lab_path(job["freeze_path"]))
    require(digest(lab_path(PREFIX_AUDIT_PATH)) == freeze["prefix_audit"]["sha256"], "Prefix audit changed after dispatch")
    if job["baseline_comparator"]:
        ref = job["baseline_comparator"]
        require(digest(lab_path(ref["path"])) == ref["result_sha256"], "Comparator changed after dispatch")
    import_start = time.perf_counter()
    from research_cycle import engine
    from kaggle_environments import make
    from kaggle_environments.agent import get_last_callable
    import_seconds = time.perf_counter() - import_start
    require(digest(engine.__file__) == ENGINE_HASH, "Installed runtime engine differs from frozen reference")
    load_start = time.perf_counter()
    our_path, their_path = lab_path(job["candidate_path"]), lab_path(job["opponent_path"])
    ours = get_last_callable(our_path.read_text(encoding="utf-8"), path=str(our_path))
    theirs = get_last_callable(their_path.read_text(encoding="utf-8"), path=str(their_path))
    load_seconds = time.perf_counter() - load_start
    profile, capture, requested = [], {"prefix71": None, "prefix167": None, "predecision72": None, "predecision168": None}, Counter()
    own_function = instrument_candidate(ours, job["seat"], profile, capture, requested)
    final_stock, phase_flows, phase = {}, {}, {"step": -1, "farms": []}
    original_market, original_commit = engine._process_market, engine._commit_unit
    def market(state, env):
        step = int(state[0].observation["step"])
        phase.update(step=step, farms=state[0].observation.farms)
        result = original_market(state, env)
        if step == 71:
            capture["prefix71"] = snapshot_hashes([s.observation for s in state], "step-71 after market, BEFORE town consumption, decay and end-of-day")
        if step == 167:
            capture["prefix167"] = snapshot_hashes([s.observation for s in state], "step-167 after market, BEFORE town consumption, decay and end-of-day")
        if step == 718:
            final_stock.update(step=718,
                               shed=[dict(s.observation.private["shed"]) for s in state],
                               cargo_totals=[dict(sum((Counter(inv) for inv in s.observation.private["inventories"]), Counter())) for s in state])
        return result
    def commit(op, item, price, farm, private, market_inventory, shed_capacity=100):
        before = farm["money"]
        ok = original_commit(op, item, price, farm, private, market_inventory, shed_capacity)
        if ok:
            seat = next(index for index, candidate_farm in enumerate(phase["farms"]) if candidate_farm is farm)
            stage = "opening_0_71" if phase["step"] < 72 else "middle_72_167" if phase["step"] < 168 else "main_168_695" if phase["step"] < 696 else "terminal_696_718"
            bucket = phase_flows.setdefault(stage, [{"actual_sales": Counter(), "sale_revenue": Counter(), "unit_purchase_spending": Counter()} for _ in range(2)])[seat]
            if op == "SELL":
                bucket["actual_sales"][item] += 1
                bucket["sale_revenue"][item] += price
            elif farm["money"] < before:
                bucket["unit_purchase_spending"][op + ":" + str(item)] += before - farm["money"]
        return ok
    engine._process_market, engine._commit_unit = market, commit
    try:
        players = [own_function, theirs] if job["seat"] == 0 else [theirs, own_function]
        row = run_game_configured(players, {"seed": job["seed"], "episodeSteps": 720}, engine, make)
    finally:
        engine._process_market, engine._commit_unit = original_market, original_commit
    seat = job["seat"]
    row.update(job)
    flow_check = phase_flow_audit(row, phase_flows)
    row.update(evidence="closed_loop", started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
               wall_seconds=time.perf_counter() - tick, job_cpu_seconds=time.process_time() - cpu,
               runtime_import_wall_seconds=import_seconds, policy_source_loading_wall_seconds=load_seconds,
               entrypoint="official_get_last_callable", entrypoint_name=ours.__name__,
               opponent_entrypoint="official_get_last_callable", opponent_entrypoint_name=theirs.__name__,
               candidate_agent_is_entrypoint=ours.__globals__.get("agent") is ours,
               opponent_agent_is_entrypoint=theirs.__globals__.get("agent") is theirs,
               opponent_entrypoint_audit=opponent_entrypoint_audit(theirs, job["opponent"], job["opponent_sha256"]),
               margin=row["rewards"][seat] - row["rewards"][1 - seat], own_call_profile=profile,
               timing_scope=TIMING_SCOPE, final_after_market=final_stock, phase_flows=phase_flows, phase_flow_audit=flow_check,
               phase_flow_scope="Actual successful unit commits; HIRE/BUY_LAND atomic costs absent from unit-purchase counters.",
               requested_work_actions=dict(requested), requested_work_scope="Issued commands only, not executed harvest or sale quantities.",
               route_diagnostics=route_snapshot(ours.__globals__, seat), feature_schema=FEATURE_SCHEMA,
               process_provenance={"pid": os.getpid(), "parent_pid": os.getppid(), "python": sys.version,
                                   "platform": platform.platform(), "start_method": "spawn", "max_tasks_per_child": 1,
                                   "isolation": "Fresh OS process and official last-callable namespaces for both files per job"},
               **capture)
    write_new_result(ROOT / job["split"] / job["key"], row)
    return {"key": job["key"], "margin": row["margin"], "wall_seconds": row["wall_seconds"],
            "clean": row["statuses"] == ["DONE", "DONE"] and row["frames"] == 720 and not row["errors"] and flow_check["consistent"],
            "feature72_valid": bool(capture["predecision72"] and capture["predecision72"]["feature_snapshot"]["valid"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", action="append", required=True)
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--opponent", action="append")
    parser.add_argument("--pool", action="append", type=Path)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--split", choices=("development",), default="development")
    parser.add_argument("--baseline-comparators", type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    require(1 <= args.workers <= 2, "P3 authorizes at most two workers")
    pool = load_pool(args.pool or [LAB / "opponent-pool-p2.json", LAB / "opponent-pool-p2-stress.json"])
    names = args.opponent or list(ALLOWED_OPPONENTS)
    require(len(set(names)) == len(names) and set(names) <= set(pool), "Missing/duplicate requested opponent")
    opponents = {name: pool[name] for name in names}
    jobs, plan = prepare_jobs(args.variant, args.seed, opponents, args.split, args.freeze, args.baseline_comparators)
    plan.update(execute=args.execute, workers=args.workers, isolation="spawn; one job per child", family_weighting="Not applied by runner")
    print(json.dumps(plan, ensure_ascii=False), flush=True)
    if not args.execute or not jobs:
        return
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context("spawn"), max_tasks_per_child=1) as executor:
        pending = [executor.submit(run_job, job) for job in jobs]
        for future in as_completed(pending):
            print(json.dumps(future.result()), flush=True)


if __name__ == "__main__":
    main()
