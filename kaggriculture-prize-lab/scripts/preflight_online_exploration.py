"""R1 bounded actual-path loading checks. No network or Kaggle submission."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

LAB = Path(__file__).resolve().parents[1]
OUTPUT = LAB / "results/online-exploration-20260912"
EXPECTED = {
    "depth2-file": "c06dc267e07ce5b07e8bf5380104dc3c87efbbbcdaf72386677ba31e7bb55624",
    "depth2-timing-safe-file": "8d37e6f4683c5a8c399c74022211e77061a59600af6278e318c2958c9c6bfbd2",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from research_cycle import make, engine
    paths = {name: LAB / f"experiments/track-terminal-20260912/{name}/main.py" for name in EXPECTED}
    for name, path in paths.items():
        assert digest(path) == EXPECTED[name]
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    baseline = LAB / "public-baseline-v10/main.py"
    assert digest(baseline) == "1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for seat in (0, 1):
        destination = OUTPUT / f"preflight-depth2-file-91101-{seat}.json"
        if destination.exists():
            raise SystemExit(f"Refusing overwrite: {destination}")
        started = datetime.now(timezone.utc).isoformat()
        tick = time.perf_counter()
        env = make("kaggriculture", configuration={"seed": 91101, "episodeSteps": 720}, debug=False)
        players = [str(baseline), str(baseline)]
        players[seat] = str(paths["depth2-file"])
        frames = env.run(players)
        rewards = [s.reward for s in frames[-1]]
        statuses = [s.status for s in frames[-1]]
        errors = [log.get("stderr") for frame in env.logs for log in frame if log.get("stderr")]
        reference_path = LAB / f"results/terminal-20260912/development/cok-91101-{seat}-depth2-file.json"
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        row = {
            "variant": "depth2-file", "seat": seat, "seed": 91101,
            "started_utc": started, "completed_utc": datetime.now(timezone.utc).isoformat(),
            "wall_seconds": time.perf_counter() - tick,
            "candidate_sha256": digest(paths["depth2-file"]), "baseline_sha256": digest(baseline),
            "engine_sha256": digest(Path(engine.__file__)), "runner_sha256": digest(Path(__file__)),
            "frames": len(frames), "statuses": statuses, "rewards": rewards, "errors": errors,
            "own_max_framework_seconds": max(float(frame[seat].get("duration", 0)) for frame in env.logs if len(frame) == 2),
            "own_min_overage_seconds": min(float(frame[seat].observation.get("remainingOverageTime", 60)) for frame in frames),
            "matches_prior_rewards": rewards == reference["rewards"],
            "reference_sha_matches": reference["candidate_sha256"] == EXPECTED["depth2-file"],
            "reference": reference_path.relative_to(LAB).as_posix(),
            "evidence": "R1 preflight: both actual Python paths, duplicate development case; not new strength evidence or official sandbox guarantee",
        }
        destination.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(row), flush=True)
        assert not errors and statuses == ["DONE", "DONE"] and len(frames) == 720
        assert row["matches_prior_rewards"] and row["reference_sha_matches"]


if __name__ == "__main__":
    main()
