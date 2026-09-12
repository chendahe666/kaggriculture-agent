"""Describe a frozen eight-pair stress group; never promote or infer a rating."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import mean

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / "results/terminal-20260912"
BASE = "1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01"
CAND = "8d37e6f4683c5a8c399c74022211e77061a59600af6278e318c2958c9c6bfbd2"
ENGINE = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(margin):
    return 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5


def main():
    opponent = json.loads((LAB / "opponent-pool-p2-stress.json").read_text(encoding="utf-8"))["opponents"][0]
    assert digest(LAB / opponent["path"]) == opponent["sha256"]
    rows, source_hashes = [], {}
    for seed in (91101, 91102, 91103, 91104):
        for seat in (0, 1):
            pair = []
            for variant, sha in (("baseline", BASE), ("depth2-timing-safe-file", CAND)):
                path = ROOT / "development" / f"arlene-{seed}-{seat}-{variant}.json"
                r = json.loads(path.read_text(encoding="utf-8"))
                expected = {"variant": variant, "candidate_sha256": sha, "engine_sha256": ENGINE,
                            "opponent_sha256": opponent["sha256"], "opponent": "arlene",
                            "family": "reconstructed_mixed_route", "seed": seed, "seat": seat,
                            "split": "development", "evidence": "closed_loop",
                            "entrypoint": "official_get_last_callable"}
                for k, v in expected.items():
                    if r[k] != v:
                        raise ValueError(f"{path.name}: metadata mismatch {k}")
                assert r["margin"] == r["rewards"][seat] - r["rewards"][1 - seat]
                source_hashes[str(path.relative_to(LAB))] = digest(path)
                pair.append(r)
            b, c = pair
            profile = c["own_call_profile"]
            c_carry = c["final_after_market"]["carried"][seat]
            rows.append({
                "seed": seed, "seat": seat, "baseline_rewards": b["rewards"], "candidate_rewards": c["rewards"],
                "baseline_margin": b["margin"], "candidate_margin": c["margin"],
                "margin_gain": c["margin"] - b["margin"],
                "baseline_score": score(b["margin"]), "candidate_score": score(c["margin"]),
                "score_gain": score(c["margin"]) - score(b["margin"]),
                "baseline_clean": b["statuses"] == ["DONE", "DONE"] and b["frames"] == 720 and not b["errors"],
                "candidate_clean": c["statuses"] == ["DONE", "DONE"] and c["frames"] == 720 and not c["errors"],
                "baseline_statuses": b["statuses"], "candidate_statuses": c["statuses"],
                "errors": {"baseline": b["errors"], "candidate": c["errors"]},
                "gameplay_start_equal": b["terminal_start"]["gameplay_sha256"] == c["terminal_start"]["gameplay_sha256"],
                "raw_start_equal": b["terminal_start"]["sha256"] == c["terminal_start"]["sha256"],
                "baseline_start_overage": b["terminal_start"]["runtime_overage_seconds"],
                "candidate_start_overage": c["terminal_start"]["runtime_overage_seconds"],
                "actual_sales_baseline": b["actual_sales"][seat], "actual_sales_candidate": c["actual_sales"][seat],
                "sale_revenue_baseline": b["sale_revenue"][seat], "sale_revenue_candidate": c["sale_revenue"][seat],
                "market_spending_baseline": b["market_spending"][seat], "market_spending_candidate": c["market_spending"][seat],
                "candidate_final_shed": c["final_after_market"]["shed"][seat],
                "candidate_final_carried": c_carry,
                "candidate_carried_units": sum(sum(inv.values()) for inv in c_carry),
                "candidate_max_outer_call_ms": c["max_call_ms"][seat],
                "candidate_max_inner_wall_ms": max(p["wall_ms"] for p in profile),
                "candidate_max_inner_cpu_ms": max(p["cpu_ms"] for p in profile),
                "candidate_safety_diagnostics": c["safety_diagnostics"],
                "baseline_runner_sha256": b["runner_sha256"], "candidate_runner_sha256": c["runner_sha256"]
            })
    result = {
        "schema": "p2c-stress-v1", "games": 16, "paired_scenarios": 8, "independent_seed_blocks": 4,
        "comparison": "Existing frozen candidate vs COK on an additional locally reviewed route policy",
        "source_hashes": source_hashes, "opponent": opponent,
        "primary_five_family_weights_changed": False, "new_independent_families": 0,
        "summary": {"baseline_outcome_counts": dict(Counter(str(r["baseline_score"]) for r in rows)),
                    "candidate_outcome_counts": dict(Counter(str(r["candidate_score"]) for r in rows)),
                    "baseline_points": sum(r["baseline_score"] for r in rows),
                    "candidate_points": sum(r["candidate_score"] for r in rows),
                    "mean_margin_gain": mean(r["margin_gain"] for r in rows),
                    "mean_score_gain": mean(r["score_gain"] for r in rows),
                    "outcome_downgrades": sum(r["score_gain"] < 0 for r in rows),
                    "all_clean": all(r["baseline_clean"] and r["candidate_clean"] for r in rows),
                    "all_gameplay_starts_equal": all(r["gameplay_start_equal"] for r in rows)},
        "rows": rows,
        "decision": "DESCRIPTIVE DEVELOPMENT ONLY; no release test or Kaggle rating prediction",
        "limits": ["Four reused development seeds; seats and paired arms dependent",
                   "Additional route policy, not a sixth independent strategy family",
                   "Download scores not bound to source bytes; measure actual outcomes here",
                   "Inner wall/CPU excludes source loading and some framework overhead",
                   "Opponent source remains private-local pending upstream attribution review"]
    }
    destination = ROOT / "p2c-stress.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
