"""Freeze P2 accounting separately from later research tracks; no games."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / "results/terminal-20260912"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    league = sorted((ROOT / "development").glob("*.json"))
    smoke = sorted((ROOT / "file-smoke").glob("*.json"))
    diagnostic = sorted((LAB / "inbox/diagnostics/terminal-20260912").glob("*.json"))
    assert len(league) == 320 and len(smoke) == 4 and len(diagnostic) == 3
    variants = Counter()
    errors = []
    for path in league:
        row = json.loads(path.read_text(encoding="utf-8"))
        variants[row["variant"]] += 1
        if row["errors"] or row["statuses"] != ["DONE", "DONE"] or row["frames"] != 720:
            errors.append(path.name)
    assert not errors
    candidates = sorted((LAB / "experiments/track-terminal-20260912").glob("*/main.py"))
    assert len(candidates) == 12
    payload = {
        "schema": "p2-accounting-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "full_games": 327, "league_games": 320, "diagnostic_duplicate_games": 3,
        "file_path_duplicate_games": 4, "variant_league_counts": dict(sorted(variants.items())),
        "candidate_artifacts": {str(p.parent.name): digest(p) for p in candidates},
        "public_result_hashes": {str(p.relative_to(LAB)).replace("\\", "/"): digest(p) for p in league + smoke},
        "private_diagnostic_hashes": {str(p.relative_to(LAB)).replace("\\", "/"): digest(p) for p in diagnostic},
        "reports": {str(p.relative_to(LAB)).replace("\\", "/"): digest(p) for p in
                    [ROOT / "p2b-interactions.json", ROOT / "p2c-safety.json", ROOT / "p2c-stress.json"]},
        "errors": errors, "new_holdout_opened": False, "kaggle_submitted": False,
        "baseline_replaced": False, "release_gate": "NOT_OPENED; development and stress evidence do not justify promotion",
        "baseline_sha256": digest(LAB / "public-baseline-v10/main.py"),
        "limits": "Counts are actual full-game executions, not independent samples. Engine phase/unit tests excluded. Private diagnostic bodies and unverified-license sources are not redistributed."
    }
    out = ROOT / "experiment-index.json"
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"full_games": payload["full_games"], "league": len(league), "artifacts": len(candidates), "errors": errors}))


if __name__ == "__main__":
    main()
