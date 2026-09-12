"""Freeze the pre-registered 96-game P3 probe matrix after root's audited gates.

This writes metadata only. It never approves an audit, runs games or submits.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import run_portfolio_track as runner
from portfolio_features import schema_digest


def main():
    lab = runner.LAB
    audit_path = lab / runner.PREFIX_AUDIT_PATH
    audit = runner.read_json(audit_path)
    runner.require(audit.get("approved") is True, "Root mechanism audit is not approved")
    variants = ["baseline", "v5-low-file", "v5-high-file"]
    variant_hashes = {name: runner.digest(lab / runner.candidate_path(name)) for name in variants}
    runner.require(audit.get("variant_hashes") == variant_hashes, "Audit is not bound to current candidate bytes")
    sources = runner.source_hashes()
    runner.require(audit.get("source_hashes") == sources, "Audit is not bound to current runner/feature/engine bytes")
    pool = runner.load_pool([lab / "opponent-pool-p2.json", lab / "opponent-pool-p2-stress.json"])
    opponents = {name: pool[name] for name in runner.ALLOWED_OPPONENTS}
    freeze = {
        "schema": "portfolio-track-freeze-v1", "split": "development",
        "seeds": [91101, 91102, 91103, 91104], "variant_hashes": variant_hashes,
        "opponents": {name: {key: opponent[key] for key in ("path", "sha256", "family")}
                      for name, opponent in opponents.items()},
        **sources, "feature_schema_sha256": schema_digest(), "max_new_games": 96,
        "prefix_audit": {"path": runner.PREFIX_AUDIT_PATH, "sha256": runner.digest(audit_path), "approved": True},
        "scope": "Two fixed native experts; 96 new full games plus 48 read-only historical P2 baseline controls. No confirmation or promotion.",
        "protocol_path": "reports/p3-20260912-plan.md",
        "protocol_sha256": runner.digest(lab / "reports/p3-20260912-plan.md"),
    }
    runner.validate_freeze(freeze, opponents, variants, freeze["seeds"], "development", sources)
    path = lab / "results/portfolio-20260912/freeze-probes-v1.json"
    if path.exists():
        previous = runner.read_json(path)
        runner.require(all(previous.get(key) == value for key, value in freeze.items()), "Refusing to overwrite a different freeze")
    else:
        freeze["frozen_utc"] = datetime.now(timezone.utc).isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(freeze, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps({"freeze_path": str(path.relative_to(lab)).replace("\\", "/"),
                      "freeze_sha256": runner.digest(path), "variant_hashes": variant_hashes}, indent=2))


if __name__ == "__main__":
    main()
