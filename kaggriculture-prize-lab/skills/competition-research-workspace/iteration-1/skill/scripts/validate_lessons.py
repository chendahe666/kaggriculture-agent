"""Validate lesson bookkeeping, not the truth or usefulness of a claim."""
import argparse
import json
from pathlib import Path


def validate(data):
    errors = []
    allowed = {"literature_guidance", "hypothesis", "local_evidence", "cross_context_evidence", "retired"}
    known_sources = {f"{prefix}{i}" for prefix in ("B", "P") for i in range(1, 6)}
    seen = set()
    if data.get("schema_version") != 1 or not data.get("skill_version"):
        errors.append("Missing supported schema or skill version")
    if not data.get("lessons"):
        errors.append("Empty lesson store")
    for lesson in data.get("lessons", []):
        ident = lesson.get("id", "<missing>")
        if ident in seen:
            errors.append(f"{ident}: duplicate ID")
        seen.add(ident)
        for key in ("id", "claim", "scope", "limitations", "falsification"):
            if not isinstance(lesson.get(key), str) or not lesson[key].strip():
                errors.append(f"{ident}: missing {key}")
        if not isinstance(lesson.get("version"), int) or lesson["version"] < 1:
            errors.append(f"{ident}: invalid version")
        status = lesson.get("status")
        if status not in allowed:
            errors.append(f"{ident}: unknown status")
        for key in ("sources", "evidence", "validations"):
            if not isinstance(lesson.get(key), list):
                errors.append(f"{ident}: {key} must be a list")
        if not set(lesson.get("sources", [])).issubset(known_sources):
            errors.append(f"{ident}: source missing from current catalog")
        if status == "literature_guidance" and not lesson.get("sources"):
            errors.append(f"{ident}: literature guidance needs sources")
        if status in {"local_evidence", "cross_context_evidence"} and not lesson.get("evidence"):
            errors.append(f"{ident}: empirical status needs evidence")
        if status == "cross_context_evidence":
            contexts = {v.get("context") for v in lesson.get("validations", [])
                        if isinstance(v, dict) and v.get("independent") is True and v.get("artifact") and v.get("context")}
            if len(contexts) < 2:
                errors.append(f"{ident}: cross-context status needs two named independent validation contexts")
        if status == "retired" and not lesson.get("retirement_reason"):
            errors.append(f"{ident}: retirement needs a reason")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path(__file__).resolve().parents[1] / "lessons.json")
    args = parser.parse_args()
    errors = validate(json.loads(args.path.read_text(encoding="utf-8")))
    if errors:
        raise SystemExit("\n".join(errors))
    print("Lesson bookkeeping valid. No causal or competition-performance claim verified.")


if __name__ == "__main__":
    main()
