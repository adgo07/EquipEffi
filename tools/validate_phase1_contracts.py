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
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


CASE_DIR = Path("specs/equipment_efficiency/golden/pump_water")
APPROVAL_REVIEW_DIR = Path("specs/equipment_efficiency/golden/pump_water_approval_review")
PUMP_CANDIDATE_JSONL = Path("specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl")
PUMP_WATER_REPLACEMENT_CANDIDATE_JSONL = Path(
    "specs/equipment_efficiency/golden/pump_water_replacement_candidates_v0_1.jsonl"
)
CANDIDATE_SOURCE_REGISTRY_PATH = Path(
    "specs/equipment_efficiency/golden/pump_candidate_source_registry_v0_1.json"
)
CANDIDATE_SOURCE_REGISTRY_SCHEMA_PATH = Path(
    "specs/equipment_efficiency/schemas/pump_candidate_source_registry_v0_1.schema.json"
)
PUMP_CANDIDATE_SOURCE_ALLOWLIST = {
    PUMP_CANDIDATE_JSONL.as_posix(): {
        "candidate_set_version": "pump-water-e2e-v0.3",
        "source_candidate_schema_version": "golden-case-0.3",
        "source_baseline_sha": "3101e05abd7f33262a9449c390d61ec00008fb75",
        "source_file_sha256": "E8096D18E4B62A6986222C6E5ADEC9519FA842AE44860A736D45AFA3AE712C8D",
        "record_count": 26,
    },
    PUMP_WATER_REPLACEMENT_CANDIDATE_JSONL.as_posix(): {
        "candidate_set_version": "pump-water-replacement-v0.1",
        "source_candidate_schema_version": "golden-case-0.3",
        "source_baseline_sha": "6c672fe48ac3da09b173cb62fd4119daf1c0ab54",
        "source_file_sha256": "2600E577B25926263823AA7C42A59B8CD1433B5A6D49C2C0075D14543103CED9",
        "record_count": 3,
    },
}
PUMP_CANDIDATE_REPLACEMENTS = {
    "GC-PUMP-V3-WATER-LIGHT-VERTICAL-L2": "GC-PUMP-V3-R1-WATER-LIGHT-VERTICAL-L2",
    "GC-PUMP-V3-WATER-LIGHT-HORIZONTAL-L3": "GC-PUMP-V3-R1-WATER-LIGHT-HORIZONTAL-L3",
    "GC-PUMP-V3-WATER-PIPELINE-L1": "GC-PUMP-V3-R1-WATER-PIPELINE-L1",
}
EVIDENCE_REGISTRY_PATH = Path("specs/equipment_efficiency/evidence_registry.json")
SCHEMA_BY_VERSION = {
    "golden-case-0.1": Path("specs/equipment_efficiency/schemas/golden_case.schema.json"),
    "golden-case-0.2": Path("specs/equipment_efficiency/schemas/golden_case_0_2.schema.json"),
    "golden-case-0.3": Path("specs/equipment_efficiency/schemas/golden_case_0_3.schema.json"),
    "golden-case-0.4": Path("specs/equipment_efficiency/schemas/golden_case_0_4.schema.json"),
    "golden-case-0.4-review": Path("specs/equipment_efficiency/schemas/golden_case_0_4_review.schema.json"),
}
LINEAGE_VERSIONS = {"golden-case-0.3", "golden-case-0.4", "golden-case-0.4-review"}
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
    if version in LINEAGE_VERSIONS and "CURRENT_IMPLEMENTATION" not in roles:
        errors.append("versioned pump cases must identify the current implementation used for replay")

    for index, reference in enumerate(references):
        label = f"source_reference[{index}] {reference.get('source_id', '<unknown>')}"
        source_id = str(reference.get("source_id", ""))
        if reference.get("artifact_kind") == "EXTERNAL_FILE":
            registered_source = _external_source_record(registry, source_id)
            if version in LINEAGE_VERSIONS and registered_source is None:
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
                if version in LINEAGE_VERSIONS and (
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


def _canonical_record_sha256(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def _candidate_evidence_review_flags(candidate: dict[str, Any]) -> list[str]:
    rule_id = candidate.get("expected_calculation_trace", {}).get("matched_rule_id")
    if rule_id is None:
        return []
    canonical_ids = [
        stable_id
        for reference in _case_source_references(candidate)
        if reference.get("evidence_role") == "CANONICAL_PACK"
        for stable_id in reference.get("stable_data_ids", [])
    ]
    if rule_id in canonical_ids:
        return []
    recorded = ",".join(canonical_ids) if canonical_ids else "<empty>"
    return [
        f"matched_rule_id={rule_id} is absent from CANONICAL_PACK stable_data_ids={recorded}; resolve provenance before approval"
    ]


def _load_candidate_source_registry(
    repo_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[str]]:
    """Load only explicitly allowlisted, versioned candidate files and pins."""

    registry_path = repo_root / CANDIDATE_SOURCE_REGISTRY_PATH
    schema_path = repo_root / CANDIDATE_SOURCE_REGISTRY_SCHEMA_PATH
    errors: list[str] = []
    if not registry_path.is_file():
        return {}, {}, [f"candidate source registry is missing: {CANDIDATE_SOURCE_REGISTRY_PATH}"]
    if not schema_path.is_file():
        return {}, {}, [f"candidate source registry schema is missing: {CANDIDATE_SOURCE_REGISTRY_SCHEMA_PATH}"]
    try:
        registry = _load_json(registry_path)
        schema = _load_json(schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {}, {}, [f"candidate source registry cannot be loaded: {exc}"]
    if not isinstance(registry, dict):
        return {}, {}, ["candidate source registry root must be an object"]
    errors.extend(f"candidate source registry schema: {message}" for message in _schema_errors(schema, registry))

    root = repo_root.resolve()
    sources: dict[str, dict[str, Any]] = {}
    for entry in registry.get("candidate_sources", []):
        if not isinstance(entry, dict):
            errors.append("candidate source registry entries must be objects")
            continue
        source_file = entry.get("source_candidate_file")
        if not isinstance(source_file, str) or source_file not in PUMP_CANDIDATE_SOURCE_ALLOWLIST:
            errors.append(f"candidate source file is not allowlisted: {source_file!r}")
            continue
        relative = PurePosixPath(source_file)
        if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".jsonl":
            errors.append(f"candidate source path must be a relative repository JSONL path: {source_file!r}")
            continue
        if source_file in sources:
            errors.append(f"candidate source registry contains duplicate path: {source_file}")
            continue
        expected = PUMP_CANDIDATE_SOURCE_ALLOWLIST[source_file]
        source = dict(entry)
        for key in ("candidate_set_version", "source_candidate_schema_version", "source_baseline_sha", "source_file_sha256", "record_count"):
            if source.get(key) != expected[key]:
                errors.append(
                    f"candidate source registry {source_file}: {key} {source.get(key)!r} "
                    f"does not match its registered version pin {expected[key]!r}"
                )
        path = (root / Path(*relative.parts)).resolve()
        if not path.is_relative_to(root):
            errors.append(f"candidate source path escapes the repository: {source_file}")
            continue
        if not path.is_file():
            errors.append(f"registered candidate source is missing: {source_file}")
            continue
        actual_file_hash = _sha256(path, normalize_repository_text=True)
        if actual_file_hash != str(source.get("source_file_sha256", "")).upper():
            errors.append(
                f"candidate source file SHA-256 {actual_file_hash} != registered "
                f"{source.get('source_file_sha256')} for {source_file}"
            )
        sources[source_file] = source

    if set(sources) != set(PUMP_CANDIDATE_SOURCE_ALLOWLIST):
        errors.append(
            "candidate source registry must contain exactly the allowlisted versioned files; "
            f"missing={sorted(set(PUMP_CANDIDATE_SOURCE_ALLOWLIST) - set(sources))}; "
            f"extra={sorted(set(sources) - set(PUMP_CANDIDATE_SOURCE_ALLOWLIST))}"
        )

    registered_replacements: dict[str, str] = {}
    for pair in registry.get("replacements", []):
        if not isinstance(pair, dict):
            errors.append("candidate replacement entries must be objects")
            continue
        source_id = pair.get("source_candidate_case_id")
        replacement_id = pair.get("replacement_candidate_case_id")
        if not isinstance(source_id, str) or not isinstance(replacement_id, str):
            errors.append("candidate replacement entries must identify source and replacement case IDs")
            continue
        if source_id in registered_replacements:
            errors.append(f"candidate source has more than one replacement: {source_id}")
            continue
        registered_replacements[source_id] = replacement_id
    if registered_replacements != PUMP_CANDIDATE_REPLACEMENTS:
        errors.append(
            "candidate replacement map differs from the explicit allowlist: "
            f"{registered_replacements}"
        )
    return sources, registered_replacements, errors


def _replacement_payload_errors(
    records: dict[str, tuple[int, dict[str, Any], dict[str, Any]]],
    replacements: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    for source_id, replacement_id in replacements.items():
        source_record = records.get(source_id)
        replacement_record = records.get(replacement_id)
        if source_record is None or replacement_record is None:
            errors.append(f"replacement pair is incomplete: {source_id} -> {replacement_id}")
            continue
        source = source_record[1]
        replacement = replacement_record[1]
        for key, value in source.items():
            if key in {"case_id", "source_sidecar"}:
                continue
            if replacement.get(key) != value:
                errors.append(f"replacement {replacement_id}: field {key!r} differs from source candidate {source_id}")
        expected_sidecar = copy.deepcopy(source.get("source_sidecar"))
        rule_id = source.get("expected_calculation_trace", {}).get("matched_rule_id")
        canonical_refs = [
            reference
            for reference in expected_sidecar.get("source_references", [])
            if reference.get("evidence_role") == "CANONICAL_PACK"
        ] if isinstance(expected_sidecar, dict) else []
        if not isinstance(rule_id, str) or len(canonical_refs) != 1:
            errors.append(f"replacement source {source_id} must have one Canonical reference and a matched rule")
        else:
            canonical_refs[0]["stable_data_ids"] = [rule_id]
            if replacement.get("source_sidecar") != expected_sidecar:
                errors.append(
                    f"replacement {replacement_id}: source_sidecar must differ only by setting "
                    f"CANONICAL_PACK stable_data_ids to {rule_id}"
                )
    return errors


def _candidate_index(
    repo_root: Path,
) -> tuple[dict[str, tuple[int, dict[str, Any], dict[str, Any]]], dict[str, str], list[str]]:
    source_files, replacements, errors = _load_candidate_source_registry(repo_root)
    records: dict[str, tuple[int, dict[str, Any], dict[str, Any]]] = {}
    schemas = {version: _load_json(repo_root / path) for version, path in SCHEMA_BY_VERSION.items()}
    root = repo_root.resolve()
    for source_file in PUMP_CANDIDATE_SOURCE_ALLOWLIST:
        source = source_files.get(source_file)
        relative = PurePosixPath(source_file)
        path = (root / Path(*relative.parts)).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            continue
        expected_schema_version = source["source_candidate_schema_version"] if source else None
        count = 0
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                count += 1
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{source_file}:{line_number}: invalid JSON: {exc}")
                    continue
                if not isinstance(item, dict) or not isinstance(item.get("case_id"), str):
                    errors.append(f"{source_file}:{line_number}: candidate must be an object with case_id")
                    continue
                case_id = item["case_id"]
                if case_id in records:
                    errors.append(f"{source_file}:{line_number}: duplicate candidate case_id {case_id}")
                    continue
                schema_version = item.get("case_schema_version")
                if schema_version != expected_schema_version:
                    errors.append(
                        f"{source_file}:{line_number}: case_schema_version {schema_version!r} "
                        f"does not match registered {expected_schema_version!r}"
                    )
                schema = schemas.get(schema_version)
                if schema is None:
                    errors.append(f"{source_file}:{line_number}: unsupported candidate schema version {schema_version!r}")
                else:
                    errors.extend(
                        f"{source_file}:{line_number}: schema: {message}"
                        for message in _schema_errors(schema, item)
                    )
                records[case_id] = (line_number, item, source or {})
        expected_count = source.get("record_count") if source else None
        if count != expected_count:
            errors.append(f"{source_file}: record count {count} != registered {expected_count}")
    errors.extend(_replacement_payload_errors(records, replacements))
    return records, replacements, errors


def _provenance_errors(repo_root: Path, case: dict[str, Any], version: str | None) -> list[str]:
    if version not in {"golden-case-0.4", "golden-case-0.4-review"}:
        return []
    errors: list[str] = []
    provenance = case.get("provenance")
    if not isinstance(provenance, dict):
        return ["provenance must identify an unchanged 0.3 pump_water candidate"]
    candidate_id = provenance.get("source_candidate_case_id")
    records, replacements, index_errors = _candidate_index(repo_root)
    errors.extend(index_errors)
    record = records.get(candidate_id)
    if record is None:
        errors.append(f"provenance candidate does not exist: {candidate_id!r}")
        return errors
    actual_line, candidate, source_record = record
    if provenance.get("source_candidate_line") != actual_line:
        errors.append(f"provenance source_candidate_line {provenance.get('source_candidate_line')!r} != {actual_line}")
    for key in ("source_candidate_file", "source_candidate_schema_version", "source_baseline_sha"):
        registry_key = key
        if provenance.get(key) != source_record.get(registry_key):
            errors.append(
                f"provenance {key} {provenance.get(key)!r} does not match the registered candidate source "
                f"{source_record.get(registry_key)!r}"
            )
    actual_hash = _canonical_record_sha256(candidate)
    if str(provenance.get("source_candidate_sha256", "")).upper() != actual_hash:
        errors.append(f"provenance candidate SHA-256 {actual_hash} != recorded {provenance.get('source_candidate_sha256')}")
    if candidate.get("case_schema_version") != provenance.get("source_candidate_schema_version"):
        errors.append("provenance source schema version does not match the candidate record")
    if candidate.get("profile_id") != "pump_water" or candidate.get("evaluation_layer") != "APPLICATION_E2E":
        errors.append("formal V2 Golden provenance must resolve to a pump_water APPLICATION_E2E candidate")
    if candidate.get("case_status") != "DRAFT" or candidate.get("approval_status") != "PENDING":
        errors.append("source 0.3 candidate is not retained as DRAFT/PENDING")
    source_case_id = next((old_id for old_id, new_id in replacements.items() if new_id == candidate_id), candidate_id)
    if not source_case_id.startswith("GC-PUMP-V3-WATER-"):
        errors.append(f"candidate {candidate_id!r} has no registered original business scenario ID")
    expected_id = "GC-PUMP-V4-WATER-" + str(source_case_id).removeprefix("GC-PUMP-V3-WATER-")
    if case.get("case_id") != expected_id:
        errors.append(f"case_id must be {expected_id!r} for the linked source candidate")
    # Every source payload field must be copied without changing inputs, expected results,
    # trace, source sidecar, notes, or other candidate evidence.
    for key, value in candidate.items():
        if key in {"case_schema_version", "case_id", "case_status", "approval_status", "review_status"}:
            continue
        if case.get(key) != value:
            errors.append(f"candidate payload field {key!r} differs from its linked 0.3 source")
    evidence_flags = _candidate_evidence_review_flags(candidate)
    if version == "golden-case-0.4-review":
        if case.get("review_flags") != evidence_flags:
            errors.append(f"review_flags must exactly record candidate source-evidence issues: {evidence_flags}")
    elif version == "golden-case-0.4":
        if case.get("review_flags") != []:
            errors.append("approved 0.4 Golden must have review_flags=[]")
        for flag in evidence_flags:
            errors.append(f"cannot approve while candidate source evidence is unresolved: {flag}")
    return errors


def _approval_semantic_errors(case: dict[str, Any], version: str | None) -> list[str]:
    if version != "golden-case-0.4":
        return []
    errors: list[str] = []
    owner = str(case.get("review_owner", "")).strip()
    if owner.casefold() in {"required_input", "tbd", "pending", "unknown", "solution review designated standards owner (required_input)"}:
        errors.append("review_owner must be a real named human, not a placeholder")
    try:
        reviewed = datetime.fromisoformat(str(case.get("reviewed_at", "")).replace("Z", "+00:00"))
        approved = datetime.fromisoformat(str(case.get("approved_at", "")).replace("Z", "+00:00"))
        if reviewed.tzinfo is None or approved.tzinfo is None:
            errors.append("reviewed_at and approved_at must include a timezone")
        elif approved < reviewed:
            errors.append("approved_at must be equal to or later than reviewed_at")
    except ValueError:
        # JSON Schema format validation reports malformed/missing timestamps.
        pass
    return errors


def _validate_approval_review_packages(
    repo_root: Path,
    review_dir: Path = APPROVAL_REVIEW_DIR,
    *,
    external_evidence_root: Path | None = None,
    skip_external_evidence: bool = False,
) -> tuple[int, int, list[str], list[str], int, int]:
    resolved = review_dir if review_dir.is_absolute() else repo_root / review_dir
    schemas = {version: _load_json(repo_root / path) for version, path in SCHEMA_BY_VERSION.items()}
    paths = sorted(resolved.glob("*.json")) if resolved.is_dir() else []
    errors: list[str] = []
    historical: list[str] = []
    external_skipped = 0
    open_review_flags = 0
    for error in ([] if resolved.is_dir() else [f"approval review directory is missing: {resolved}"]):
        errors.append(error)
    observed_candidates: list[str] = []
    for case_path in paths:
        case = _load_json(case_path)
        version = case.get("case_schema_version")
        if version != "golden-case-0.4-review":
            errors.append(f"{case_path}: approval review directory only accepts golden-case-0.4-review records")
            continue
        schema = schemas.get(version)
        if schema is None:
            errors.append(f"{case_path}: unsupported case_schema_version: {version!r}")
            continue
        for message in _schema_errors(schema, case):
            errors.append(f"{case_path}: schema: {message}")
        review_flags = case.get("review_flags", [])
        if isinstance(review_flags, list):
            open_review_flags += len(review_flags)
        provenance = case.get("provenance", {})
        if isinstance(provenance, dict) and isinstance(provenance.get("source_candidate_case_id"), str):
            observed_candidates.append(provenance["source_candidate_case_id"])
        for message in _provenance_errors(repo_root, case, version):
            errors.append(f"{case_path}: provenance: {message}")
        source_errors, source_historical, skipped = _source_errors(
            repo_root, case, version, external_evidence_root=external_evidence_root,
            skip_external_evidence=skip_external_evidence,
        )
        historical.extend(f"{case_path}: {message}" for message in source_historical)
        external_skipped += skipped
        for message in source_errors:
            errors.append(f"{case_path}: evidence: {message}")
    candidates, replacements, candidate_errors = _candidate_index(repo_root)
    errors.extend(candidate_errors)
    water_e2e_candidates = {
        case_id for case_id, (_, candidate, _) in candidates.items()
        if candidate.get("profile_id") == "pump_water" and candidate.get("evaluation_layer") == "APPLICATION_E2E"
    }
    replaced_source_ids = set(replacements)
    replacement_candidate_ids = set(replacements.values())
    expected_candidates = (water_e2e_candidates - replaced_source_ids) | replacement_candidate_ids
    if len(expected_candidates) != 18:
        errors.append(f"expected 18 selected water Application E2E cases after registered replacements, found {len(expected_candidates)}")
    if len(observed_candidates) != len(set(observed_candidates)):
        errors.append("approval review package contains duplicate source candidate references")
    if set(observed_candidates) != expected_candidates:
        missing = sorted(expected_candidates - set(observed_candidates))
        extra = sorted(set(observed_candidates) - expected_candidates)
        errors.append(f"approval review package must cover exactly the 18 pump_water E2E candidates; missing={missing}; extra={extra}")
    if not paths:
        errors.append(f"no approval review package files found under {resolved}")
    return len(paths), len(errors), errors, historical, external_skipped, open_review_flags


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
        if version in {"golden-case-0.3", "golden-case-0.4-review"}:
            errors.append(f"{case_path}: {version} is a candidate/review schema and cannot be loaded as an official Golden")
            schema_error_count += 1
            continue
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
        provenance_errors = _provenance_errors(repo_root, case, version)
        semantic_errors = _approval_semantic_errors(case, version)
        schema_error_count += len(schema_errors)
        source_error_count += len(source_errors) + len(provenance_errors) + len(semantic_errors)
        for message in schema_errors:
            errors.append(f"{case_path}: schema: {message}")
        for message in source_errors:
            errors.append(f"{case_path}: evidence: {message}")
        for message in provenance_errors:
            errors.append(f"{case_path}: provenance: {message}")
        for message in semantic_errors:
            errors.append(f"{case_path}: approval: {message}")

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

    root = repo_root.resolve()
    resolved = candidate_path if candidate_path.is_absolute() else repo_root / candidate_path
    resolved = resolved.resolve()
    try:
        relative_candidate_path = resolved.relative_to(root).as_posix()
    except ValueError:
        return 0, 1, [f"candidate JSONL path is outside the repository: {candidate_path}"], [], 0
    registered_sources, _, registry_errors = _load_candidate_source_registry(repo_root)
    if relative_candidate_path not in registered_sources:
        return 0, 1, [f"candidate JSONL path is not in the versioned source registry: {relative_candidate_path}"], [], 0
    if not resolved.is_file():
        return 0, 1, [f"registered candidate JSONL is missing: {relative_candidate_path}"], [], 0
    schemas = {version: _load_json(repo_root / path) for version, path in SCHEMA_BY_VERSION.items()}
    errors: list[str] = list(registry_errors)
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
            if version in {"golden-case-0.4", "golden-case-0.4-review"}:
                errors.append(f"{resolved}:{line_number}: {version} must be validated from its official/review directory, not a candidate JSONL")
                schema_error_count += 1
                continue
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
    parser.add_argument("--candidate-jsonl", type=Path, action="append", help="validate a registered, versioned DRAFT candidate JSONL; may be repeated")
    parser.add_argument("--approval-review-dir", type=Path, help="validate pending 0.4 pump_water approval review packages and their 0.3 source provenance")
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

    for candidate_path in args.candidate_jsonl or []:
        candidate_count, candidate_errors, candidate_messages, candidate_historical, candidate_external_skipped = _validate_candidate_jsonl(
            repo_root,
            candidate_path,
            external_evidence_root=external_evidence_root,
            skip_external_evidence=args.skip_external_evidence,
        )
        print(f"candidate_file={candidate_path.as_posix()} candidate_cases={candidate_count} candidate_errors={candidate_errors}")
        for error in candidate_messages:
            print(f"CANDIDATE_ERROR {error}")
        for message in candidate_historical:
            print(f"CANDIDATE_HISTORICAL {message}")
        if args.skip_external_evidence:
            print(f"candidate_external_evidence_not_checked={candidate_external_skipped}")
        error_count += candidate_errors

    if args.approval_review_dir is not None:
        review_count, review_errors, review_messages, review_historical, review_external_skipped, review_open_flags = _validate_approval_review_packages(
            repo_root,
            args.approval_review_dir,
            external_evidence_root=external_evidence_root,
            skip_external_evidence=args.skip_external_evidence,
        )
        print(f"approval_review_cases={review_count} approval_review_errors={review_errors} open_evidence_flags={review_open_flags}")
        for error in review_messages:
            print(f"APPROVAL_REVIEW_ERROR {error}")
        for message in review_historical:
            print(f"APPROVAL_REVIEW_HISTORICAL {message}")
        if args.skip_external_evidence:
            print(f"approval_review_external_evidence_not_checked={review_external_skipped}")
        error_count += review_errors

    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
