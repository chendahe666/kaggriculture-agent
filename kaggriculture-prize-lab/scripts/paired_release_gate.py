"""Audit a frozen, fully paired confirmation league without running any agents.

Input: {"rows": [...], "preregistration": {...}, "opened_seeds": [...]}.
Each row identifies variant (baseline/candidate), family, opponent, seed, seat,
rewards, statuses, frames, errors, max_call_ms, split, candidate_sha256,
opponent_sha256 and engine_sha256. candidate_sha256 means the evaluated policy's
hash, including on baseline rows. policy_sha256 is accepted as an alias.

Preregistration pins split="confirmation", seeds, baseline_sha256,
candidate_sha256, engine_sha256, and opponents={name: {family, sha256}}.
It must also declare unopened_at_freeze=true. Freeze this BEFORE looking at the
results and supply the complete opened-seed registry; this tool cannot establish
historical freshness or genuine source independence from numerical rows alone.

CLI exit codes: 0 = this gate passes; 1 = HOLD/REJECT; 2 = invalid input.
Passing is not authorization to submit, nor proof of official sandbox behavior.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics


VERSION = "paired-release-v2"
MIN_FAMILIES = 5
MIN_SEEDS = 30
ALPHA = 0.05
PRIMARY_ALPHA = 0.025
BETTING_LAMBDAS = (0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 0.95, 1.0)
REGRESSION_TOLERANCE = 0.05
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _is_sha(value):
    return isinstance(value, str) and bool(_SHA.fullmatch(value))


def _finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _binomial_cdf(k, n, p):
    if p <= 0:
        return 1.0
    if p >= 1:
        return float(k == n)
    logs = [math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
            + j * math.log(p) + (n - j) * math.log1p(-p) for j in range(k + 1)]
    peak = max(logs)
    return min(1.0, math.exp(peak) * sum(math.exp(x - peak) for x in logs))


def clopper_pearson_upper(k, n, alpha=ALPHA):
    """One-sided exact binomial upper bound; independent seed blocks required."""
    if not (_integer(k) and _integer(n) and 0 <= k <= n and n > 0 and 0 < alpha < 1):
        raise ValueError("require 0 <= k <= n, n > 0, 0 < alpha < 1")
    if k == n:
        return 1.0
    if k == 0:
        return -math.expm1(math.log(alpha) / n)
    lo, hi = k / n, 1.0
    for _ in range(65):
        mid = (lo + hi) / 2
        if _binomial_cdf(k, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _quantile(sorted_values, q):
    at = (len(sorted_values) - 1) * q
    low = int(at)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] * (high - at) + sorted_values[high] * (at - low) if high != low else sorted_values[low]


def _interval(values, bootstrap_means, alpha=ALPHA):
    """Percentile bootstrap; replace degenerate empirical CI with a valid bound.

    For n independent bounded [-1,1] observations, with probability >= 1-alpha,
    at most u=1-(alpha/2)**(1/n) population mass lies below the sample minimum,
    and at most u lies above its maximum (order-statistic tolerance bounds plus
    a union bound). Therefore [min-(min+1)u, max+(1-max)u] bounds the mean.
    This handles ties/discrete outcomes conservatively and never calls a zero
    empirical variance proof of no possible change.
    """
    samples = sorted(bootstrap_means)
    empirical = [_quantile(samples, alpha / 2), _quantile(samples, 1 - alpha / 2)]
    degenerate = min(values) == max(values) or empirical[0] == empirical[1]
    if degenerate:
        u = -math.expm1(math.log(alpha / 2) / len(values))
        low, high = min(values), max(values)
        interval = [max(-1.0, low - (low + 1) * u), min(1.0, high + (1 - high) * u)]
        method = "bounded_order_statistic_fallback"
    else:
        interval = empirical
        method = "synchronized_seed_percentile_bootstrap"
    return {"interval_95": interval, "empirical_bootstrap_95": empirical,
            "method": method, "empirical_degenerate": degenerate,
            "bootstrap_is_approximate": not degenerate}


def _points(row):
    a, b = row["rewards"][row["seat"]], row["rewards"][1 - row["seat"]]
    return 1.0 if a > b else 0.0 if a < b else 0.5


def _mixture_log_e(values, null_mean):
    """Log uniform mixture of pre-fixed bets; -1 < null_mean <= 1."""
    logs = []
    for stake in BETTING_LAMBDAS:
        total = 0.0
        for value in values:
            increment = stake * (value - null_mean) / (1 + null_mean)
            if increment <= -1:
                total = -math.inf
                break
            total += math.log1p(increment)
        logs.append(total)
    peak = max(logs)
    if peak == -math.inf:
        return peak
    return peak + math.log(sum(math.exp(v - peak) for v in logs) / len(logs))


def bounded_mean_betting(values):
    """Fixed-mixture e-test and inverted one-sided 97.5% mean lower bound.

    For IID D in [-1,1] and H0 E[D] <= m, every factor
    1 + lambda*(D-m)/(1+m) is nonnegative and has expectation <= 1.
    Independence makes each product an e-value; their pre-fixed uniform
    mixture is also an e-value. Markov's inequality bounds P(E >= 1/alpha)
    by alpha. The e-value decreases in m, so test inversion is a lower
    confidence bound. No fitting/selection of lambda using these outcomes.

    This bound can be low-powered at n=90. Failure to reject is insufficient
    evidence of superiority, not proof that the mean gain is nonpositive.
    """
    if not values or not all(_finite_number(v) and -1 <= v <= 1 for v in values):
        raise ValueError("betting requires nonempty finite observations in [-1,1]")
    threshold = -math.log(PRIMARY_ALPHA)
    log_e = _mixture_log_e(values, 0.0)
    lo, hi = -1.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if mid == lo or mid == hi:
            break
        if _mixture_log_e(values, mid) > threshold:
            lo = mid
        else:
            hi = mid
    return {"method": "fixed_lambda_bounded_mean_mixture_betting",
            "null_hypothesis": "E[family-equal paired seed gain] <= 0",
            "alpha": PRIMARY_ALPHA, "one_sided_confidence": 1 - PRIMARY_ALPHA,
            "lower_bound_975": lo, "reject_nonpositive_mean": log_e > threshold,
            "e_value_at_zero": math.exp(log_e) if log_e < 700 else None,
            "log_e_value_at_zero": log_e, "e_value_threshold": 1 / PRIMARY_ALPHA,
            "lambda_grid": list(BETTING_LAMBDAS),
            "lambda_weights": [1 / len(BETTING_LAMBDAS)] * len(BETTING_LAMBDAS),
            "assumptions": "IID fresh seed blocks, D in [-1,1], fixed candidate/opponent pool and fixed lambda grid/weights before confirmation. Cross-family and paired-seat correlation within a seed is allowed.",
            "interpretation": "Finite-sample one-sided 97.5% lower bound conditional on the frozen pool. Non-rejection is HOLD, not evidence of no improvement. No budget extension or candidate retuning from this confirmation set."}


def evaluate_release(rows, preregistration, opened_seeds=(), resamples=4000, random_seed=9122026):
    """Return an auditable decision; malformed/incomplete designs fail closed.

    Every registered opponent must have both variants in both seats on the same
    complete seed set. Family weights are equal; opponents within a family are
    equal; seats within a seed are paired. Each bootstrap draw reuses identical
    seed indices for ALL families, preserving cross-family seed correlation.
    """
    result = {"version": VERSION, "passed": False, "decision": "INVALID", "errors": [],
              "gate_scope": "paired outcome and recorded correctness confirmation only",
              "uncertainty_scope": "independent seeds conditional on this fixed, manually classified opponent pool",
              "limitations": ["Not uncertainty over unseen opponents or leaderboard rating.",
                              "Freshness and source lineage require an honest frozen manifest and complete opened-seed registry.",
                              "Local call times and DONE records do not replace raw-file entrypoint, action legality, memory or official sandbox checks.",
                              "Do not repeatedly select candidates or peek at this confirmation set."]}
    errors = result["errors"]
    if not isinstance(rows, list) or not rows:
        errors.append("rows must be a nonempty array")
    if not isinstance(preregistration, dict):
        errors.append("preregistration must be an object")
        return result
    p = preregistration
    if p.get("split") != "confirmation":
        errors.append("only a preregistered confirmation split can release; development is excluded")
    if p.get("unopened_at_freeze") is not True:
        errors.append("unopened_at_freeze declaration is required")
    seeds = p.get("seeds", [])
    if not isinstance(seeds, list) or not seeds or not all(_integer(x) for x in seeds):
        errors.append("preregistration seeds must be nonempty integers")
        seeds = []
    if len(seeds) != len(set(seeds)):
        errors.append("duplicate preregistration seeds")
    if not isinstance(opened_seeds, (list, tuple, set)) or not all(_integer(x) for x in opened_seeds):
        errors.append("opened_seeds must contain only integers")
        opened_seeds = []
    overlap = sorted(set(seeds) & set(opened_seeds))
    if overlap:
        errors.append("confirmation contains previously opened seeds: " + repr(overlap))
    for name in ("baseline_sha256", "candidate_sha256", "engine_sha256"):
        if not _is_sha(p.get(name)):
            errors.append("missing or malformed preregistered " + name)
    opponents = p.get("opponents", {})
    if not isinstance(opponents, dict) or not opponents:
        errors.append("preregistration opponents must be nonempty")
        opponents = {}
    families = defaultdict(list)
    hash_families = defaultdict(set)
    for name, entry in opponents.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("family"), str) or not entry["family"].strip() or not _is_sha(entry.get("sha256")):
            errors.append("missing family/hash for opponent " + str(name))
            continue
        families[entry["family"]].append(name)
        hash_families[entry["sha256"]].add(entry["family"])
    if any(len(v) > 1 for v in hash_families.values()):
        errors.append("identical opponent hashes assigned to different families (cloned family inflation)")
    if not _integer(resamples) or resamples < 1000:
        errors.append("at least 1000 bootstrap resamples required")
    if errors:
        return result

    indexed = {}
    observed_max_ms = {"baseline": 0.0, "candidate": 0.0}
    time_limit = p.get("max_call_ms_limit", 1000.0)
    if not _finite_number(time_limit) or time_limit <= 0:
        errors.append("max_call_ms_limit must be positive and finite")
        return result
    dirty_rows = 0
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row {i}: expected object")
            continue
        variant, opponent, seed, seat = (row.get(k) for k in ("variant", "opponent", "seed", "seat"))
        if variant not in ("baseline", "candidate") or opponent not in opponents or not _integer(seed) or seed not in seeds or not _integer(seat) or seat not in (0, 1):
            errors.append(f"row {i}: unknown variant/opponent/seed/seat")
            continue
        key = (variant, opponent, seed, seat)
        if key in indexed:
            errors.append(f"duplicate row key: {key}")
            continue
        indexed[key] = row
        if row.get("family") != opponents[opponent]["family"]:
            errors.append(f"row {i}: family differs from frozen opponent registry")
        if row.get("split") != p["split"]:
            errors.append(f"row {i}: mixed/development split")
        policy_hash = row.get("policy_sha256", row.get("candidate_sha256"))
        if policy_hash != p[variant + "_sha256"]:
            errors.append(f"row {i}: policy hash differs from frozen {variant}")
        if "policy_sha256" in row and "candidate_sha256" in row and row["policy_sha256"] != row["candidate_sha256"]:
            errors.append(f"row {i}: conflicting policy hash fields")
        if row.get("opponent_sha256") != opponents[opponent]["sha256"]:
            errors.append(f"row {i}: opponent hash differs from frozen registry")
        if row.get("engine_sha256") != p["engine_sha256"]:
            errors.append(f"row {i}: engine hash differs from frozen engine")
        rewards = row.get("rewards")
        if not isinstance(rewards, list) or len(rewards) != 2 or not all(_finite_number(v) for v in rewards):
            errors.append(f"row {i}: malformed/nonfinite rewards")
        times = row.get("max_call_ms")
        if isinstance(times, list) and len(times) == 2:
            times = times[seat]
        if not _finite_number(times) or times < 0:
            errors.append(f"row {i}: missing/nonfinite measured call time")
        else:
            observed_max_ms[variant] = max(observed_max_ms[variant], times)
            if times > time_limit:
                dirty_rows += 1
        if row.get("statuses") != ["DONE", "DONE"] or row.get("frames") != 720 or row.get("errors") != []:
            dirty_rows += 1
    missing = [(v, o, s, seat) for v in ("baseline", "candidate") for o in opponents for s in seeds for seat in (0, 1)
               if (v, o, s, seat) not in indexed]
    if missing:
        errors.append(f"missing paired/seat rows: {len(missing)}; first={missing[:4]}")
    if errors:
        return result

    seeds = sorted(seeds)
    family_values = {}
    family_scores = {}
    flips = {"positive": 0, "negative": 0, "win_to_loss": 0}
    for family, names in sorted(families.items()):
        gains, baseline_scores, candidate_scores = [], [], []
        for seed in seeds:
            b_values, c_values = [], []
            for name in names:
                for seat in (0, 1):
                    b = _points(indexed[("baseline", name, seed, seat)])
                    c = _points(indexed[("candidate", name, seed, seat)])
                    b_values.append(b)
                    c_values.append(c)
                    flips["positive"] += c > b
                    flips["negative"] += c < b
                    flips["win_to_loss"] += b == 1 and c == 0
            baseline_scores.append(statistics.mean(b_values))
            candidate_scores.append(statistics.mean(c_values))
            gains.append(statistics.mean(c_values) - statistics.mean(b_values))
        family_values[family] = gains
        family_scores[family] = {"baseline_match_score": statistics.mean(baseline_scores),
                                 "candidate_match_score": statistics.mean(candidate_scores)}

    names = sorted(family_values)
    n = len(seeds)
    macro_values = [statistics.mean(family_values[f][i] for f in names) for i in range(n)]
    rng = random.Random(random_seed)
    macro_bootstrap, family_bootstrap = [], {f: [] for f in names}
    for _ in range(resamples):
        draw = [rng.randrange(n) for _ in range(n)]
        macro_bootstrap.append(statistics.mean(macro_values[i] for i in draw))
        for family in names:
            family_bootstrap[family].append(statistics.mean(family_values[family][i] for i in draw))
    primary = bounded_mean_betting(macro_values)
    primary["mean_paired_gain"] = statistics.mean(macro_values)
    primary["bootstrap_diagnostic"] = _interval(macro_values, macro_bootstrap)
    primary["bootstrap_diagnostic"]["used_for_release"] = False
    primary["bootstrap_diagnostic"]["limitation"] = "Percentile bootstrap may severely under-cover sparse outcomes with unseen negative tails; diagnostic only, never the superiority gate."
    per_family = {}
    for family in names:
        values = family_values[family]
        negative = sum(v < 0 for v in values)
        upper = clopper_pearson_upper(negative, n, ALPHA / len(names))
        per_family[family] = {**family_scores[family], **_interval(values, family_bootstrap[family]),
                              "opponents": families[family], "seeds": n,
                              "mean_paired_gain": statistics.mean(values),
                              "regressed_seed_blocks": negative,
                              "regression_probability_upper": upper,
                              "conservative_mean_gain_lower": -upper,
                              "noninferiority_pass": upper <= REGRESSION_TOLERANCE}
    checks = {"minimum_families": len(names) >= MIN_FAMILIES,
              "minimum_new_seeds_per_family": n >= MIN_SEEDS,
              "all_recorded_runs_clean": dirty_rows == 0,
              "primary_gain_lower_975_above_zero": primary["lower_bound_975"] > 0 and primary["reject_nonpositive_mean"],
              "simultaneous_family_noninferiority": all(v["noninferiority_pass"] for v in per_family.values())}
    result.update(checks=checks, passed=all(checks.values()),
                  decision="PASS" if all(checks.values()) else "HOLD",
                  rows=len(rows), paired_games=len(rows) // 2, independent_seed_blocks=n,
                  family_count=len(names), primary=primary, per_family=per_family,
                  outcome_flips=flips, max_measured_call_ms=observed_max_ms,
                  resamples=resamples, bootstrap_random_seed=random_seed,
                  paired_seed_gains={str(seed): {f: family_values[f][i] for f in names} for i, seed in enumerate(seeds)},
                  family_gate={"method": "one-sided Clopper-Pearson upper bound on P(seed family gain < 0)",
                               "simultaneous_confidence": 1 - ALPHA,
                               "per_family_alpha": ALPHA / len(names),
                               "multiple_comparison_adjustment": "Bonferroni across registered families",
                               "tolerance": REGRESSION_TOLERANCE,
                               "interpretation": "D is in [-1,1], so E[D] >= -P(D<0). Nonnegative blocks contribute zero to this conservative bound. Failure to certify is HOLD, not proof of harmful regression.",
                               "assumptions": "Independent identically distributed fresh seed blocks; fixed opponent mixture. Family correlation is allowed. Primary exact lower bound is marginal one-sided 97.5%; family bounds are simultaneous 95%. These are not a joint 95% confidence region (a union bound gives at least 92.5% joint coverage). The conjunction is an intersection-union decision: if any required population claim is false, passing all valid component tests has false-release probability at most 5%, under the stated assumptions. This is not a posterior probability of correctness."})
    if dirty_rows:
        result["decision"] = "REJECT"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resamples", type=int, default=4000)
    parser.add_argument("--random-seed", type=int, default=9122026)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    opened = set(payload.get("opened_seeds", []))
    contract_path = Path(__file__).resolve().parents[1] / "evaluation-contract.json"
    if contract_path.exists():
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        opened.update(contract.get("development_seeds", []))
        opened.update(contract.get("validation_seeds_already_opened", []))
    result = evaluate_release(payload.get("rows"), payload.get("preregistration"),
                              opened_seeds=list(opened), resamples=args.resamples, random_seed=args.random_seed)
    result["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    content = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(content)
    print(content)
    return 0 if result["passed"] else 2 if result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
