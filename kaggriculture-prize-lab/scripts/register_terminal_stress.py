"""Register reviewed Arlene bytes for local stress testing, never redistribution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
SOURCE = "inbox/opponents/strong-source-audit-20260912/lynnsakurai-farming-score-v3/verified-output/main.py"
SHA = "d36ae976ad4a6316e6c1a27a5d04e9cc8e30300f21bdd31e749127c67a9311c4"


def main():
    payload = (LAB / SOURCE).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == SHA
    reviewed = LAB / "inbox/opponents/strong-source-audit-20260912/lynnsakurai-farming-score-v3/extracted-text/main.py"
    assert reviewed.read_bytes() == payload + b"\n", "Reviewed text must differ only by the disclosed added LF"
    out = LAB / "opponent-pool-p2-stress.json"
    if out.exists():
        old = json.loads(out.read_text(encoding="utf-8"))
        assert old["opponents"][0]["sha256"] == SHA
        print("Already registered; original timestamp retained")
        return
    record = {
        "version": "p2c-arlene-stress-20260912-v1",
        "registered_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Separate development stress group, no change to five-family primary weights",
        "redistribution": "Source excluded from GitHub and all submission artifacts pending upstream attribution review",
        "opponents": [{
            "name": "arlene", "path": SOURCE, "sha256": SHA,
            "family": "reconstructed_mixed_route",
            "source": "https://www.kaggle.com/code/lynnsakurai/farming-score-v3-replay-revised",
            "behavior": "719-step two-route tape; step 360 public-state selection and 72-step cash-reserve response",
            "classification_limit": "Not a sixth independent family; route genealogy unproved",
            "license": "Notebook declares Apache-2.0; upstream supplied C++/action-tape attribution unresolved; local testing only",
            "safety_review": "Two-agent complete Python review; stdlib and constant JSON decompression only; no file/network/process/native/eval/exec operations",
            "source_bytes": len(payload),
            "output_download_from_utc": "2026-09-12T05:51:39.0098318Z",
            "output_download_to_utc": "2026-09-12T05:51:43.8933445Z",
            "page_script_version_id": 347020472,
            "version_binding": "Source hash frozen. Explicit version pull returned 403; CLI output ignores version argument",
            "score_limit": "Conflicting indexed scores are not bound to these bytes and are not a measured rating",
            "audit_path": "inbox/opponents/strong-source-audit-20260912/audit-manifest.json"
        }]
    }
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Registered reviewed local stress opponent: {SHA}")


if __name__ == "__main__":
    main()
