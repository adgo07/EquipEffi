"""Validate the Phase 1 schemas, Golden Cases, and referenced evidence files.

JSON Schema can validate types and formats, but it cannot prove that a path
exists or that its bytes match a recorded digest.  This small audit command
keeps that repository-level evidence check explicit and reproducible.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


CASE_DIR = Path("specs/equipment_efficiency/golden/pump_water")
SCHEMA_PATH = Path("specs/equipment_efficiency/schemas/golden_case.schema.json")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _artifact_path(repo_root: Path, reference: dict[str, Any]) -> Path:
    path = Path(reference["artifact_path"])
    if reference["artifact_kind"] == "REPOSITORY_FILE" and not path.is_absolute():
        return repo_root / path
    return path


def _source_errors(repo_root: Path, case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    references = case.get("source_reference", [])
    roles = {reference.get("evidence_role") for reference in references}
    if "STANDARD" not in roles:
        errors.append("source_reference must contain a STANDARD evidence reference")

    for index, reference in enumerate(references):
        target = _artifact_path(repo_root, reference)
        label = f"source_reference[{index}] {reference.get('source_id', '<unknown>')}"
        if not target.is_file():
            errors.append(f"{label}: artifact does not exist: {target}")
            continue
        actual = _sha256(target)
        expected = str(reference["artifact_sha256"]).upper()
        if actual != expected:
            errors.append(f"{label}: SHA-256 {actual} != recorded {expected}")
    return errors


def _schema_errors(schema: dict[str, Any], case: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in sorted(validator.iter_errors(case), key=lambda item: list(item.path))]


def _validate_cases(repo_root: Path) -> tuple[int, int, list[str]]:
    schema_path = repo_root / SCHEMA_PATH
    case_dir = repo_root / CASE_DIR
    schema = _load_json(schema_path)
    case_paths = sorted(case_dir.glob("*.json"))
    errors: list[str] = []
    schema_error_count = 0
    source_error_count = 0

    for case_path in case_paths:
        case = _load_json(case_path)
        schema_errors = _schema_errors(schema, case)
        source_errors = _source_errors(repo_root, case)
        schema_error_count += len(schema_errors)
        source_error_count += len(source_errors)
        for message in schema_errors:
            errors.append(f"{case_path}: schema: {message}")
        for message in source_errors:
            errors.append(f"{case_path}: evidence: {message}")

    if not case_paths:
        errors.append(f"no Golden Cases found under {case_dir}")
    return len(case_paths), schema_error_count + source_error_count, errors


def _negative_probe(repo_root: Path) -> list[str]:
    """Prove the three acceptance counterexamples are rejected.

    The probe is in-memory and never writes an invalid case into the working
    tree: JSON number, invalid unit_id, and missing source artifact.
    """

    schema = _load_json(repo_root / SCHEMA_PATH)
    case_path = sorted((repo_root / CASE_DIR).glob("*.json"))[0]
    probe = copy.deepcopy(_load_json(case_path))
    probe["input"]["flow_m3h"] = 100
    probe["input"]["unit_id_by_field"]["flow_m3h"] = "not-a-unit"
    probe["source_reference"][0]["artifact_path"] = "specs/does-not-exist.json"
    schema_errors = _schema_errors(schema, probe)
    source_errors = _source_errors(repo_root, probe)
    return [f"schema: {message}" for message in schema_errors] + [f"evidence: {message}" for message in source_errors]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--negative-probe", action="store_true", help="also verify the three known invalid counterexamples")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    case_count, error_count, errors = _validate_cases(repo_root)
    print(f"cases={case_count} errors={error_count}")
    for error in errors:
        print(f"ERROR {error}")

    if args.negative_probe:
        probe_errors = _negative_probe(repo_root)
        print(f"negative_probe_errors={len(probe_errors)}")
        for error in probe_errors:
            print(f"NEGATIVE_PROBE {error}")
        if len(probe_errors) != 3:
            print("ERROR negative probe did not reject exactly JSON number, invalid unit_id, and missing source", file=sys.stderr)
            error_count += 1

    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
