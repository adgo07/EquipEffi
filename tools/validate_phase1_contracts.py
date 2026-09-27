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
SCHEMA_BY_VERSION = {
    "golden-case-0.1": Path("specs/equipment_efficiency/schemas/golden_case.schema.json"),
    "golden-case-0.2": Path("specs/equipment_efficiency/schemas/golden_case_0_2.schema.json"),
    "golden-case-0.3": Path("specs/equipment_efficiency/schemas/golden_case_0_3.schema.json"),
}
HISTORICAL_REPOSITORY_HASHES = {
    (
        "golden-case-0.1",
        "2026.08.23",
        "src/equipeffi/resources/standards/pump.json",
        "D1FAB8310AA5ADE7ACCCB379BD347F442D51202E0EE2EEF4CA6E34F5A2F3EA00",
    ): "GB 19762-2025 water Canonical before the authorized T3-08 C2 correction",
}
REPOSITORY_TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".html",
    ".ini",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _sha256(path: Path, *, normalize_repository_text: bool = False) -> str:
    if normalize_repository_text and path.suffix.lower() in REPOSITORY_TEXT_SUFFIXES:
        data = path.read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(data).hexdigest().upper()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _reference_sha256(path: Path, reference: dict[str, Any]) -> str:
    return _sha256(
        path,
        normalize_repository_text=reference.get("artifact_kind") == "REPOSITORY_FILE",
    )


def _artifact_path(repo_root: Path, reference: dict[str, Any]) -> Path:
    path = Path(reference["artifact_path"])
    if reference["artifact_kind"] == "REPOSITORY_FILE" and not path.is_absolute():
        return repo_root / path
    return path


def _case_source_references(case: dict[str, Any]) -> list[dict[str, Any]]:
    references = case.get("source_reference")
    if isinstance(references, list):
        return references
    sidecar = case.get("source_sidecar")
    if isinstance(sidecar, dict) and isinstance(sidecar.get("source_references"), list):
        return sidecar["source_references"]
    return []


def _source_errors(
    repo_root: Path, case: dict[str, Any], version: str | None
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    historical: list[str] = []
    references = _case_source_references(case)
    roles = {reference.get("evidence_role") for reference in references}
    if "STANDARD" not in roles:
        errors.append("source references must contain a STANDARD evidence reference")
    if version == "golden-case-0.3" and "CURRENT_IMPLEMENTATION" not in roles:
        errors.append("v0.3 candidates must identify the current implementation used for replay")

    for index, reference in enumerate(references):
        target = _artifact_path(repo_root, reference)
        label = f"source_reference[{index}] {reference.get('source_id', '<unknown>')}"
        if not target.is_file():
            errors.append(f"{label}: artifact does not exist: {target}")
            continue
        actual = _reference_sha256(target, reference)
        expected = str(reference["artifact_sha256"]).upper()
        if actual != expected:
            repository_key = (
                str(version or ""),
                str(case.get("catalog_data_version", "")),
                str(reference.get("artifact_path", "")).replace("\\", "/"),
                expected,
            )
            historical_reason = HISTORICAL_REPOSITORY_HASHES.get(repository_key)
            if reference.get("artifact_kind") == "REPOSITORY_FILE" and historical_reason is not None:
                historical.append(
                    f"{label}: frozen Canonical hash {expected} for catalog {repository_key[1]} "
                    f"({historical_reason}) differs from the current repository-text digest {actual}; preserved as historical provenance"
                )
                continue
            if version in {"golden-case-0.1", "golden-case-0.2"} and reference.get("evidence_role") == "CURRENT_IMPLEMENTATION":
                historical.append(
                    f"{label}: frozen implementation digest {expected} differs from the current repository-text digest {actual}; preserved as historical provenance"
                )
                continue
            errors.append(f"{label}: SHA-256 {actual} != recorded {expected}")
    return errors, historical


def _schema_errors(schema: dict[str, Any], case: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in sorted(validator.iter_errors(case), key=lambda item: list(item.path))]


def _validate_cases(repo_root: Path) -> tuple[int, int, list[str], list[str]]:
    case_dir = repo_root / CASE_DIR
    schemas = {version: _load_json(repo_root / path) for version, path in SCHEMA_BY_VERSION.items()}
    case_paths = sorted(case_dir.glob("*.json"))
    errors: list[str] = []
    historical: list[str] = []
    schema_error_count = 0
    source_error_count = 0

    for case_path in case_paths:
        case = _load_json(case_path)
        version = case.get("case_schema_version")
        schema = schemas.get(version)
        if schema is None:
            errors.append(f"{case_path}: unsupported case_schema_version: {version!r}")
            schema_error_count += 1
            continue
        schema_errors = _schema_errors(schema, case)
        source_errors, source_historical = _source_errors(repo_root, case, version)
        historical.extend(f"{case_path}: {message}" for message in source_historical)
        schema_error_count += len(schema_errors)
        source_error_count += len(source_errors)
        for message in schema_errors:
            errors.append(f"{case_path}: schema: {message}")
        for message in source_errors:
            errors.append(f"{case_path}: evidence: {message}")

    if not case_paths:
        errors.append(f"no Golden Cases found under {case_dir}")
    return len(case_paths), schema_error_count + source_error_count, errors, historical


def _validate_candidate_jsonl(repo_root: Path, candidate_path: Path) -> tuple[int, int, list[str], list[str]]:
    """Validate a versioned, non-approved candidate stream without moving it
    into the official Golden directory.
    """

    resolved = candidate_path if candidate_path.is_absolute() else repo_root / candidate_path
    schemas = {version: _load_json(repo_root / path) for version, path in SCHEMA_BY_VERSION.items()}
    errors: list[str] = []
    historical: list[str] = []
    count = 0
    schema_error_count = 0
    source_error_count = 0
    with resolved.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            count += 1
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{resolved}:{line_number}: invalid JSON: {exc}")
                schema_error_count += 1
                continue
            version = case.get("case_schema_version") if isinstance(case, dict) else None
            schema = schemas.get(version)
            if schema is None:
                errors.append(f"{resolved}:{line_number}: unsupported case_schema_version: {version!r}")
                schema_error_count += 1
                continue
            schema_errors = _schema_errors(schema, case)
            if not schema_errors:
                source_errors, source_historical = _source_errors(repo_root, case, version)
                historical.extend(f"{resolved}:{line_number}: {message}" for message in source_historical)
            else:
                source_errors = []
            schema_error_count += len(schema_errors)
            source_error_count += len(source_errors)
            for message in schema_errors:
                errors.append(f"{resolved}:{line_number}: schema: {message}")
            for message in source_errors:
                errors.append(f"{resolved}:{line_number}: evidence: {message}")
    if count == 0:
        errors.append(f"no candidate Golden Cases found in {resolved}")
        schema_error_count += 1
    return count, schema_error_count + source_error_count, errors, historical


def _negative_probe(repo_root: Path) -> list[str]:
    """Prove the three acceptance counterexamples are rejected.

    The probe is in-memory and never writes an invalid case into the working
    tree: JSON number, invalid unit_id, and missing source artifact.
    """

    schema = _load_json(repo_root / SCHEMA_BY_VERSION["golden-case-0.1"])
    case_path = sorted((repo_root / CASE_DIR).glob("*.json"))[0]
    probe = copy.deepcopy(_load_json(case_path))
    for reference in probe.get("source_reference", []):
        target = _artifact_path(repo_root, reference)
        if target.is_file():
            reference["artifact_sha256"] = _reference_sha256(target, reference)
    probe["input"]["flow_m3h"] = 100
    probe["input"]["unit_id_by_field"]["flow_m3h"] = "not-a-unit"
    probe["source_reference"][0]["artifact_path"] = "specs/does-not-exist.json"
    schema_errors = _schema_errors(schema, probe)
    source_errors, _ = _source_errors(repo_root, probe, probe.get("case_schema_version"))
    return [f"schema: {message}" for message in schema_errors] + [f"evidence: {message}" for message in source_errors]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--negative-probe", action="store_true", help="also verify the three known invalid counterexamples")
    parser.add_argument("--candidate-jsonl", type=Path, help="optionally validate a DRAFT candidate JSONL using each explicit schema version")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    case_count, error_count, errors, historical = _validate_cases(repo_root)
    print(f"cases={case_count} errors={error_count}")
    for error in errors:
        print(f"ERROR {error}")
    for message in historical:
        print(f"HISTORICAL {message}")

    if args.negative_probe:
        probe_errors = _negative_probe(repo_root)
        print(f"negative_probe_errors={len(probe_errors)}")
        for error in probe_errors:
            print(f"NEGATIVE_PROBE {error}")
        if len(probe_errors) != 3:
            print("ERROR negative probe did not reject exactly JSON number, invalid unit_id, and missing source", file=sys.stderr)
            error_count += 1

    if args.candidate_jsonl is not None:
        candidate_count, candidate_errors, candidate_messages, candidate_historical = _validate_candidate_jsonl(repo_root, args.candidate_jsonl)
        print(f"candidate_cases={candidate_count} candidate_errors={candidate_errors}")
        for error in candidate_messages:
            print(f"CANDIDATE_ERROR {error}")
        for message in candidate_historical:
            print(f"CANDIDATE_HISTORICAL {message}")
        error_count += candidate_errors

    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
