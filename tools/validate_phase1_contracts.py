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
import os
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


CASE_DIR = Path("specs/equipment_efficiency/golden/pump_water")
EVIDENCE_REGISTRY_PATH = Path("specs/equipment_efficiency/evidence_registry.json")
SCHEMA_BY_VERSION = {
    "golden-case-0.1": Path("specs/equipment_efficiency/schemas/golden_case.schema.json"),
    "golden-case-0.2": Path("specs/equipment_efficiency/schemas/golden_case_0_2.schema.json"),
    "golden-case-0.3": Path("specs/equipment_efficiency/schemas/golden_case_0_3.schema.json"),
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


def _load_evidence_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / EVIDENCE_REGISTRY_PATH
    if not path.is_file():
        return {}
    registry = _load_json(path)
    return registry if isinstance(registry, dict) else {}


def _external_source_record(registry: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    sources = registry.get("external_sources", {})
    if source_id in sources:
        return sources[source_id]
    return next(
        (record for record in sources.values() if source_id in record.get("aliases", [])),
        None,
    )


def _historical_hash_reason(
    registry: dict[str, Any],
    version: str | None,
    case: dict[str, Any],
    reference: dict[str, Any],
) -> str | None:
    artifact_path = str(reference.get("artifact_path", "")).replace("\\", "/")
    expected_hash = str(reference.get("artifact_sha256", "")).upper()
    for item in registry.get("historical_repository_hashes", []):
        if (
            item.get("case_schema_version") == version
            and item.get("catalog_data_version") == str(case.get("catalog_data_version", ""))
            and str(item.get("artifact_path", "")).replace("\\", "/") == artifact_path
            and str(item.get("artifact_sha256", "")).upper() == expected_hash
        ):
            return str(item.get("reason", "registered historical repository evidence"))
    return None


def _artifact_path(
    repo_root: Path,
    reference: dict[str, Any],
    *,
    external_evidence_root: Path | None = None,
    evidence_registry: dict[str, Any] | None = None,
) -> Path | None:
    path = Path(reference["artifact_path"])
    if reference["artifact_kind"] == "REPOSITORY_FILE" and not path.is_absolute():
        return repo_root / path
    if reference["artifact_kind"] == "EXTERNAL_FILE":
        if external_evidence_root is None:
            return path if path.is_absolute() else None
        registry = evidence_registry if evidence_registry is not None else _load_evidence_registry(repo_root)
        source = _external_source_record(registry, str(reference.get("source_id", ""))) or {}
        relative_locator = Path(str(source.get("relative_path", path)))
        if relative_locator.is_absolute():
            raise ValueError("registered external evidence path must be relative")
        root = external_evidence_root.resolve()
        resolved = (root / relative_locator).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError("external evidence path escapes --external-evidence-root")
        return resolved
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
    repo_root: Path,
    case: dict[str, Any],
    version: str | None,
    *,
    external_evidence_root: Path | None = None,
    skip_external_evidence: bool = False,
    evidence_registry: dict[str, Any] | None = None,
) -> tuple[list[str], list[str], int]:
    errors: list[str] = []
    historical: list[str] = []
    external_skipped = 0
    registry = evidence_registry if evidence_registry is not None else _load_evidence_registry(repo_root)
    references = _case_source_references(case)
    roles = {reference.get("evidence_role") for reference in references}
    if "STANDARD" not in roles:
        errors.append("source references must contain a STANDARD evidence reference")
    if version == "golden-case-0.3" and "CURRENT_IMPLEMENTATION" not in roles:
        errors.append("v0.3 candidates must identify the current implementation used for replay")

    for index, reference in enumerate(references):
        label = f"source_reference[{index}] {reference.get('source_id', '<unknown>')}"
        source_id = str(reference.get("source_id", ""))
        if reference.get("artifact_kind") == "EXTERNAL_FILE":
            registered_source = _external_source_record(registry, source_id)
            if version == "golden-case-0.3" and registered_source is None:
                if not (repo_root / EVIDENCE_REGISTRY_PATH).is_file():
                    errors.append(f"{label}: evidence registry is missing {EVIDENCE_REGISTRY_PATH}")
                else:
                    errors.append(f"{label}: external source_id is not registered")
                continue
            if registered_source is not None:
                expected_registry_hash = str(registered_source.get("artifact_sha256", "")).upper()
                recorded_hash = str(reference.get("artifact_sha256", "")).upper()
                if reference.get("artifact_kind") != registered_source.get("artifact_kind"):
                    errors.append(f"{label}: artifact_kind differs from the external evidence registry")
                if recorded_hash != expected_registry_hash:
                    errors.append(f"{label}: artifact_sha256 differs from the external evidence registry")
                recorded_path = Path(str(reference.get("artifact_path", "")))
                if version == "golden-case-0.3" and (
                    recorded_path.is_absolute()
                    or recorded_path.as_posix() != str(registered_source.get("relative_path", ""))
                ):
                    errors.append(f"{label}: v0.3 artifact_path must match the portable registry locator")
            if skip_external_evidence:
                external_skipped += 1
                continue

        try:
            target = _artifact_path(
                repo_root,
                reference,
                external_evidence_root=external_evidence_root,
                evidence_registry=registry,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(f"{label}: cannot resolve evidence path: {exc}")
            continue
        if target is None:
            errors.append(
                f"{label}: relative external evidence requires --external-evidence-root "
                "or EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT"
            )
            continue
        if not target.is_file():
            errors.append(f"{label}: artifact does not exist: {target}")
            continue
        actual = _reference_sha256(target, reference)
        expected = str(reference["artifact_sha256"]).upper()
        if actual != expected:
            historical_reason = _historical_hash_reason(registry, version, case, reference)
            if reference.get("artifact_kind") == "REPOSITORY_FILE" and historical_reason is not None:
                historical.append(
                    f"{label}: registered historical hash {expected} ({historical_reason}) "
                    f"differs from current repository-text digest {actual}; preserved as historical provenance"
                )
                continue
            errors.append(f"{label}: SHA-256 {actual} != recorded {expected}")
    return errors, historical, external_skipped


def _schema_errors(schema: dict[str, Any], case: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in sorted(validator.iter_errors(case), key=lambda item: list(item.path))]


def _validate_cases(
    repo_root: Path,
    *,
    external_evidence_root: Path | None = None,
    skip_external_evidence: bool = False,
) -> tuple[int, int, list[str], list[str], int]:
    case_dir = repo_root / CASE_DIR
    schemas = {version: _load_json(repo_root / path) for version, path in SCHEMA_BY_VERSION.items()}
    case_paths = sorted(case_dir.glob("*.json"))
    errors: list[str] = []
    historical: list[str] = []
    external_skipped = 0
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
        source_errors, source_historical, skipped = _source_errors(
            repo_root,
            case,
            version,
            external_evidence_root=external_evidence_root,
            skip_external_evidence=skip_external_evidence,
        )
        historical.extend(f"{case_path}: {message}" for message in source_historical)
        external_skipped += skipped
        schema_error_count += len(schema_errors)
        source_error_count += len(source_errors)
        for message in schema_errors:
            errors.append(f"{case_path}: schema: {message}")
        for message in source_errors:
            errors.append(f"{case_path}: evidence: {message}")

    if not case_paths:
        errors.append(f"no Golden Cases found under {case_dir}")
    return len(case_paths), schema_error_count + source_error_count, errors, historical, external_skipped


def _validate_candidate_jsonl(
    repo_root: Path,
    candidate_path: Path,
    *,
    external_evidence_root: Path | None = None,
    skip_external_evidence: bool = False,
) -> tuple[int, int, list[str], list[str], int]:
    """Validate a versioned, non-approved candidate stream without moving it
    into the official Golden directory.
    """

    resolved = candidate_path if candidate_path.is_absolute() else repo_root / candidate_path
    schemas = {version: _load_json(repo_root / path) for version, path in SCHEMA_BY_VERSION.items()}
    errors: list[str] = []
    historical: list[str] = []
    external_skipped = 0
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
                source_errors, source_historical, skipped = _source_errors(
                    repo_root,
                    case,
                    version,
                    external_evidence_root=external_evidence_root,
                    skip_external_evidence=skip_external_evidence,
                )
                historical.extend(f"{resolved}:{line_number}: {message}" for message in source_historical)
                external_skipped += skipped
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
    return count, schema_error_count + source_error_count, errors, historical, external_skipped


def _negative_probe(repo_root: Path) -> list[str]:
    """Prove the three acceptance counterexamples are rejected.

    The probe is in-memory and never writes an invalid case into the working
    tree: JSON number, invalid unit_id, and missing source artifact.
    """

    schema = _load_json(repo_root / SCHEMA_BY_VERSION["golden-case-0.1"])
    case_path = sorted((repo_root / CASE_DIR).glob("*.json"))[0]
    probe = copy.deepcopy(_load_json(case_path))
    # The probe covers a missing repository artifact; it must not depend on
    # whether a machine has mounted the external standard PDF.
    probe_reference = copy.deepcopy(probe["source_reference"][0])
    probe_reference.update({
        "source_id": "negative-probe-missing-source",
        "artifact_kind": "REPOSITORY_FILE",
        "artifact_path": "specs/does-not-exist.json",
        "evidence_role": "STANDARD",
    })
    probe["source_reference"] = [probe_reference]
    probe["input"]["flow_m3h"] = 100
    probe["input"]["unit_id_by_field"]["flow_m3h"] = "not-a-unit"
    schema_errors = _schema_errors(schema, probe)
    source_errors, _, _ = _source_errors(repo_root, probe, probe.get("case_schema_version"))
    return [f"schema: {message}" for message in schema_errors] + [f"evidence: {message}" for message in source_errors]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--negative-probe", action="store_true", help="also verify the three known invalid counterexamples")
    parser.add_argument("--candidate-jsonl", type=Path, help="optionally validate a DRAFT candidate JSONL using each explicit schema version")
    external_group = parser.add_mutually_exclusive_group()
    external_group.add_argument(
        "--external-evidence-root",
        type=Path,
        default=Path(os.environ["EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT"])
        if os.environ.get("EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT")
        else None,
        help="directory containing registered external evidence files; can also use EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT",
    )
    external_group.add_argument(
        "--skip-external-evidence",
        action="store_true",
        help="validate schemas, registry pins and repository files while explicitly reporting external file checks as skipped",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    external_evidence_root = args.external_evidence_root.resolve() if args.external_evidence_root else None
    case_count, error_count, errors, historical, external_skipped = _validate_cases(
        repo_root,
        external_evidence_root=external_evidence_root,
        skip_external_evidence=args.skip_external_evidence,
    )
    print(f"cases={case_count} errors={error_count}")
    for error in errors:
        print(f"ERROR {error}")
    for message in historical:
        print(f"HISTORICAL {message}")
    if args.skip_external_evidence:
        print(f"external_evidence_not_checked={external_skipped}")

    if args.negative_probe:
        probe_errors = _negative_probe(repo_root)
        print(f"negative_probe_errors={len(probe_errors)}")
        for error in probe_errors:
            print(f"NEGATIVE_PROBE {error}")
        if len(probe_errors) != 3:
            print("ERROR negative probe did not reject exactly JSON number, invalid unit_id, and missing source", file=sys.stderr)
            error_count += 1

    if args.candidate_jsonl is not None:
        candidate_count, candidate_errors, candidate_messages, candidate_historical, candidate_external_skipped = _validate_candidate_jsonl(
            repo_root,
            args.candidate_jsonl,
            external_evidence_root=external_evidence_root,
            skip_external_evidence=args.skip_external_evidence,
        )
        print(f"candidate_cases={candidate_count} candidate_errors={candidate_errors}")
        for error in candidate_messages:
            print(f"CANDIDATE_ERROR {error}")
        for message in candidate_historical:
            print(f"CANDIDATE_HISTORICAL {message}")
        if args.skip_external_evidence:
            print(f"candidate_external_evidence_not_checked={candidate_external_skipped}")
        error_count += candidate_errors

    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
