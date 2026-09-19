from __future__ import annotations

import json
import importlib.resources as resources
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from ..common.enums import EliminationScope


def normalize_model(value: Any) -> str:
    text = str(value or "").strip().upper().replace("　", " ")
    return re.sub(r"[\s‐‑–—_]+", "-", text)


@dataclass(frozen=True)
class EliminationEntry:
    entry_id: str
    catalog: str
    batch: str
    device_type: str
    model_exact: tuple[str, ...] = ()
    series_patterns: tuple[str, ...] = ()
    conditions: dict[str, Any] = field(default_factory=dict)
    original_condition: str = ""
    item_no: str = ""
    reason: str = ""
    source_file: str = ""
    source_sha256: str = ""
    data_version: str = ""


@dataclass(frozen=True)
class EliminationDecision:
    matched: bool = False
    possible: bool = False
    detail: dict[str, Any] | None = None


def _load_catalog_payload() -> dict[str, Any]:
    """Load the four-batch and user-supplied industry catalog payloads.

    Both files are explicit package resources; no directory scan is performed.
    The returned payload keeps all source entries in one matching stream while
    preserving each entry's blank ``batch`` marker for industry-scope routing.
    """
    names = (
        "elimination_catalog_batches_1_4.json",
        "elimination_catalog_industry_2024.json",
    )
    payloads: list[dict[str, Any]] = []
    filesystem_root = Path(__file__).resolve().parents[2] / "resources"
    for name in names:
        path = filesystem_root / name
        try:
            if path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
            else:
                resource = resources.files("equipeffi").joinpath("resources", name)
                payload = json.loads(resource.read_text(encoding="utf-8"))
        except (FileNotFoundError, ModuleNotFoundError, OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    if not payloads:
        return {}
    if len(payloads) == 1:
        return payloads[0]
    merged = dict(payloads[0])
    merged["data_version"] = "+".join(str(item.get("data_version", "")) for item in payloads if item.get("data_version"))
    industry_payload = next((item for item in payloads if any(not entry.get("batch") for entry in item.get("entries", []))), None)
    industry_status = str(industry_payload.get("status", "")) if industry_payload else ""
    merged["status"] = "normalized_mixed_sources"
    merged["catalog_status"] = industry_status or "normalized_mixed_sources"
    merged["industry_catalog_status"] = industry_status
    merged["source_priority"] = "；".join(str(item.get("source_priority", "")) for item in payloads if item.get("source_priority"))
    merged["sources"] = [source for item in payloads for source in item.get("sources", [])]
    merged["entries"] = [entry for item in payloads for entry in item.get("entries", [])]
    merged["industry_source_complete"] = any(bool(item.get("source_complete")) for item in payloads if any(not entry.get("batch") for entry in item.get("entries", [])))
    return merged


def default_catalog_entries() -> tuple[EliminationEntry, ...]:
    """Load the four-batch DOCX extract plus the explicitly supplied 2024 entries."""
    data = _load_catalog_payload()
    if not data:
        return ()
    source_hashes = {str(item.get("file", "")): str(item.get("sha256", "")) for item in data.get("sources", [])}
    entries: list[EliminationEntry] = []
    for row in data.get("entries", []):
        if not str(row.get("matching_status", "")).startswith("enabled"):
            continue
        entries.append(
            EliminationEntry(
                entry_id=str(row["entry_id"]),
                catalog=str(row["catalog"]),
                batch=str(row["batch"]),
                device_type=str(row["device_type"]),
                model_exact=tuple(str(item) for item in row.get("model_exact", [])),
                series_patterns=tuple(str(item) for item in row.get("series_patterns", [])),
                conditions=dict(row.get("conditions", {})),
                original_condition=str(row.get("original_condition", "")),
                item_no=str(row.get("item_no", "")),
                reason=str(row.get("reason", "")),
                source_file=str(row.get("source_file", "")),
                source_sha256=source_hashes.get(str(row.get("source_file", "")), ""),
                data_version=str(data.get("data_version", "")),
            )
        )
    return tuple(entries)


VALUE_ALIASES = {
    "production_year": ("production_year", "生产年份", "出厂年份", "投运年份"),
    "rated_voltage_v": ("rated_voltage_v", "额定电压", "额定电压_V", "rated_voltage"),
    "frame_size_mm": ("frame_size_mm", "frame_size", "机座号", "机座号_mm"),
    "frame_size_mm_max": ("frame_size_mm", "frame_size", "机座号", "机座号_mm"),
}


def _condition_input(values: dict[str, Any], key: str) -> Any:
    for alias in VALUE_ALIASES.get(key, (key,)):
        if values.get(alias) not in (None, ""):
            value = values[alias]
            if key == "rated_voltage_v":
                # V4的公共电动机表以kV填写；产业目录条件以V表述。
                # 同时处理380/660、0.38/0.66等铭牌复合写法。
                return _normalize_voltage(value)
            return value
    return None


def _decimal(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value).strip())
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _decimal_parts(value: Any) -> tuple[Decimal, ...] | None:
    """Parse a scalar or slash-separated numeric value."""
    text = str(value or "").strip().replace("／", "/")
    if "/" not in text:
        number = _decimal(value)
        return (number,) if number is not None else None
    parts = tuple(_decimal(item) for item in text.split("/"))
    if not parts or any(item is None for item in parts):
        return None
    return tuple(item for item in parts if item is not None)


def _normalize_voltage(value: Any) -> Any:
    """Normalize kV/V scalar or dual-voltage input to a comparable V value."""
    text = str(value or "").strip().upper()
    text = text.replace("／", "/").replace("千伏", "").replace("KV", "").replace("V", "")
    parts = _decimal_parts(text)
    if not parts:
        return value
    normalized = tuple(item * Decimal(1000) if abs(item) < Decimal(20) else item for item in parts)
    return "/".join(format(item.normalize(), "f") for item in normalized)


def _condition_passes(actual: Any, expected: Any) -> bool:
    if not isinstance(expected, dict):
        return str(actual) == str(expected)
    op = expected.get("op", "==")
    target = expected.get("value")
    if op in {"<", "<=", ">", ">="}:
        left, right = _decimal(actual), _decimal(target)
        if right is None:
            return False
        if left is not None:
            return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right}[op]
        # 对复合额定电压，目录的“及以下/以上”条件要求每个铭牌电压
        # 分量都满足边界；例如380/660满足“660 V及以下”，而
        # 660/1140不满足。
        parts = _decimal_parts(actual)
        if not parts:
            return False
        compare = {"<": lambda item: item < right, "<=": lambda item: item <= right,
                   ">": lambda item: item > right, ">=": lambda item: item >= right}[op]
        return all(compare(item) for item in parts)
    if op == "in":
        actual_number = _decimal(actual)
        for item in expected.get("values", []):
            if actual_number is not None:
                expected_number = _decimal(item)
                if expected_number is not None and actual_number == expected_number:
                    return True
            if str(actual) == str(item):
                return True
        return False
    if op == "regex":
        return bool(re.fullmatch(str(target), str(actual)))
    left_num, right_num = _decimal(actual), _decimal(target)
    if left_num is not None and right_num is not None:
        return left_num == right_num
    return str(actual) == str(target)


class EliminationMatcher:
    def __init__(self, entries: Iterable[EliminationEntry] | None = None):
        if entries is None:
            payload = _load_catalog_payload()
            self.entries = tuple(default_catalog_entries())
            all_entries = payload.get("entries", []) if isinstance(payload, dict) else []
            sources = payload.get("sources", []) if isinstance(payload, dict) else []
            source_counts = [
                int(item.get("entry_count", 0))
                for item in sources
                if str(item.get("entry_count", "")).strip()
            ]
            self.source_entry_count = sum(source_counts) if source_counts else len(all_entries)
            # ``source_entry_count`` counts original source entries.  The
            # 2024 industry PDF has 11 original lines, while three motor
            # lines and several combined product lines are expanded into 13
            # enabled matching rules.  Keep both figures explicit so clients
            # do not infer one from the other.
            self.industry_source_item_count = sum(
                int(item.get("entry_count", 0))
                for item in sources
                if "batch" not in item and str(item.get("entry_count", "")).strip()
            )
            self.industry_resource_rule_count = sum(
                1 for item in all_entries if not str(item.get("batch", ""))
            )
            self.review_only_entry_count = sum(
                1 for item in all_entries if not str(item.get("matching_status", "")).startswith("enabled")
            )
            self.catalog_status = str(payload.get("catalog_status") or "normalized_pending_human_review") if isinstance(payload, dict) else ""
            self.industry_catalog_status = str(payload.get("industry_catalog_status") or "") if isinstance(payload, dict) else ""
            self.catalog_data_version = str(payload.get("data_version", "")) if isinstance(payload, dict) else ""
            self.industry_catalog_complete = bool(payload.get("industry_source_complete", False)) if isinstance(payload, dict) else False
        else:
            self.entries = tuple(entries)
            self.source_entry_count = len(self.entries)
            self.industry_source_item_count = sum(1 for entry in self.entries if not entry.batch)
            self.industry_resource_rule_count = self.industry_source_item_count
            self.review_only_entry_count = 0
            self.catalog_status = "custom"
            self.industry_catalog_status = ""
            self.catalog_data_version = ""
            self.industry_catalog_complete = any(not entry.batch for entry in self.entries)

    @property
    def has_industry_catalog(self) -> bool:
        """是否已经载入产业结构调整目录。

        产业目录条目与第一至第四批机电目录并行保存；空batch表示产业目录。
        产业目录的覆盖范围由资源中的用户提供条目标记，未提供的目录内容不会
        被推断或静默当成“未命中”。
        """

        return any(not entry.batch for entry in self.entries)

    def match(
        self,
        device_type: str,
        values: dict[str, Any],
        scope: EliminationScope | str,
    ) -> EliminationDecision:
        # ``match`` is a public domain helper used by catalog audits and may
        # be called without the application service.  Normalize string input
        # here as well so identity-based scope filtering cannot be bypassed.
        try:
            scope = scope if isinstance(scope, EliminationScope) else EliminationScope(str(scope))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"淘汰目录口径无效: {scope}") from exc
        model = normalize_model(values.get("model") or values.get("型号"))
        if not model:
            return EliminationDecision()
        possible: EliminationEntry | None = None
        possible_missing: list[str] = []
        possible_basis = ""
        possible_pattern = ""
        for entry in self.entries:
            if entry.device_type != device_type:
                continue
            if scope is EliminationScope.INDUSTRY_ONLY and entry.batch:
                continue
            if scope is EliminationScope.MOTOR_BATCHES_1_4 and not entry.batch:
                continue
            model_hit = model in {normalize_model(item) for item in entry.model_exact}
            match_basis = "精确型号" if model_hit else ""
            matched_pattern = ""
            if not model_hit:
                for pattern in entry.series_patterns:
                    if re.fullmatch(pattern, model):
                        model_hit = True
                        match_basis = "受控系列规则"
                        matched_pattern = pattern
                        break
            if not model_hit:
                continue
            missing: list[str] = []
            for key in entry.conditions:
                if _condition_input(values, key) in (None, ""):
                    # 一个输入字段可能同时承担上下界条件（如机座号的
                    # frame_size_mm 与 frame_size_mm_max），对外只提示一次。
                    label = key.removesuffix("_max")
                    if label not in missing:
                        missing.append(label)
            if missing:
                possible = entry
                possible_missing = missing
                possible_basis = match_basis
                possible_pattern = matched_pattern
                continue
            if all(_condition_passes(_condition_input(values, key), expected) for key, expected in entry.conditions.items()):
                return EliminationDecision(
                    matched=True,
                    detail={
                        "entry_id": entry.entry_id,
                        "catalog": entry.catalog,
                        "batch": entry.batch,
                        "item_no": entry.item_no,
                        "condition": entry.original_condition,
                        "catalog_reason": entry.reason,
                        "source_file": entry.source_file,
                        "source_sha256": entry.source_sha256,
                        "data_version": entry.data_version,
                        "normalized_model": model,
                        "match_basis": match_basis,
                        "matched_pattern": matched_pattern,
                        "reason": "型号及全部附加条件精确命中",
                    },
                )
        if possible:
            return EliminationDecision(
                possible=True,
                detail={
                    "entry_id": possible.entry_id,
                    "catalog": possible.catalog,
                    "batch": possible.batch,
                    "item_no": possible.item_no,
                    "condition": possible.original_condition,
                    "catalog_reason": possible.reason,
                    "source_file": possible.source_file,
                    "source_sha256": possible.source_sha256,
                    "data_version": possible.data_version,
                    "normalized_model": model,
                    "match_basis": possible_basis,
                    "matched_pattern": possible_pattern,
                    "missing_conditions": possible_missing,
                    "reason": "型号命中，但附加条件信息不足",
                },
            )
        return EliminationDecision()
