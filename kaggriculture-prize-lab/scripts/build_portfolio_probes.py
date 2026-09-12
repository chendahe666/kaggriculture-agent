"""Build immutable COK-only expert probes; never runs or submits them."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
TRACK = LAB / "experiments/track-portfolio-20260912"
BASE_SHA = "1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    baseline = (LAB / "public-baseline-v10/main.py").read_bytes()
    assert sha(baseline) == BASE_SHA, "Baseline bytes changed"
    overlay = (TRACK / "portfolio_overlay.py").read_bytes()
    variants = {}
    for expert in ("low", "high"):
        name = f"v5-{expert}-file"
        data = baseline + f"\n\n# P3 frozen native expert probe; no Arlene or P2 policy bytes.\nP3_EXPERT = {expert!r}\n\n".encode() + overlay
        compile(data, name, "exec")  # Syntax only; never executes policy.
        path = TRACK / name / "main.py"
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(f"Refusing to overwrite frozen candidate {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        variants[name] = {"sha256": sha(data), "expert": expert, "bytes": len(data),
                          "first_possible_entry_step": 72, "fixed_expert_decision_step": 168}
    path = TRACK / "manifest-v1.json"
    manifest = {"schema": "p3-expert-probes-v1", "baseline_sha256": BASE_SHA,
                "overlay_sha256": sha(overlay), "variants": variants,
                "scope": "Mechanism-gated local research probes; no strength validation or submission implied"}
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if any(previous.get(k) != v for k, v in manifest.items()):
            raise ValueError("Frozen build manifest differs")
    else:
        manifest["built_utc"] = datetime.now(timezone.utc).isoformat()
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, indent=2)
            stream.write("\n")
    print(json.dumps(variants, indent=2))


if __name__ == "__main__":
    main()
