from __future__ import annotations

import json
from copy import deepcopy
import importlib.resources as resources
from pathlib import Path
from typing import Any

from ...domain.common.enums import StandardDataStatus
from .pack_validator import StandardPackValidator


class StandardPackError(RuntimeError):
    pass


class JsonStandardRepository:
    """仅按显式清单加载标准包，避免目录扫描误加载历史文件。"""

    FORBIDDEN_PMSM_NAMES = {"motor_pmsm.json"}
    PMSM_PACK_ID = "gb30253_2024_pdf_verified_v1"

    def __init__(self, root: str | Path, manifest: str | Path | None = None):
        self.root = Path(root).resolve()
        manifest_path = Path(manifest) if manifest else self.root / "src/equipeffi/standard_manifest.json"
        self.manifest_path = manifest_path.resolve()
        self._package_resource_root = None
        if self.manifest_path.is_file():
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        else:
            # Support a wheel imported from a zip path.  The manifest remains
            # explicit and is read only from the installed equipeffi package;
            # no directory scan or untrusted path fallback is introduced.
            try:
                self._package_resource_root = resources.files("equipeffi")
                manifest_resource = self._package_resource_root.joinpath("standard_manifest.json")
                payload = json.loads(manifest_resource.read_text(encoding="utf-8"))
            except (FileNotFoundError, ModuleNotFoundError, OSError, json.JSONDecodeError) as exc:
                raise StandardPackError(f"无法读取标准清单: {self.manifest_path}") from exc
        self._entries = {entry["device_type"]: entry for entry in payload["packs"]}
        self._validator = StandardPackValidator()
        # A batch may request the same standard pack thousands of times.  The
        # resource is immutable for the lifetime of this repository, so cache
        # the successful structural validation by source rather than walking
        # a large shared HVAC pack for every record.
        self._validated_sources: set[str] = set()

    def get_pack(self, device_type: str, pack_id: str | None = None) -> dict[str, Any]:
        if device_type not in self._entries:
            raise KeyError(f"未配置设备标准包: {device_type}")
        entry = self._entries[device_type]
        if pack_id and pack_id != entry["pack_id"]:
            raise KeyError(f"设备{device_type}未配置标准包{pack_id}")
        if self._package_resource_root is not None:
            source = self._package_resource_root.joinpath(*str(entry["source"]).replace("\\", "/").split("/"))
        else:
            source = (self.manifest_path.parent / entry["source"]).resolve()
        if device_type == "motor_pmsm":
            if source.name in self.FORBIDDEN_PMSM_NAMES or entry["pack_id"] != self.PMSM_PACK_ID:
                raise StandardPackError("已拒绝加载旧永磁同步电机标准数据")
            lowered = str(source).lower()
            if "重新整理" in lowered or "standards2" in lowered or "粗校对" in lowered:
                raise StandardPackError("永磁同步电机只能加载本轮PDF独立重建包")
        if self._package_resource_root is None:
            try:
                source.relative_to(self.root)
            except ValueError as exc:
                raise StandardPackError(f"标准包越出允许根目录: {source}") from exc
            source_exists = source.is_file()
        else:
            source_exists = source.is_file()
        if not source_exists:
            return {
                "pack_id": entry["pack_id"],
                "device_type": device_type,
                "status": entry.get("status", StandardDataStatus.EXTRACTED.value),
                "unavailable_reason": entry.get("unavailable_reason", "标准数据文件不存在"),
            }
        data = json.loads(source.read_text(encoding="utf-8"))
        data["pack_id"] = entry["pack_id"]
        data["device_type"] = device_type
        data["status"] = entry.get("status", StandardDataStatus.NORMALIZED.value)
        data["data_version"] = entry.get("data_version", entry["pack_id"])
        data["source_file"] = entry.get("source_file", str(source))
        validation_key = str(source)
        if validation_key not in self._validated_sources:
            issues = self._validator.validate(data)
            if issues:
                raise StandardPackError(f"标准包{device_type}结构校验失败：{'；'.join(issues)}")
            self._validated_sources.add(validation_key)
        return deepcopy(data)

    def find(self, device_type: str, criteria: dict[str, Any]) -> list[dict[str, Any]]:
        pack = self.get_pack(device_type)
        rows = pack.get("records") or pack.get("rows") or []
        return [row for row in rows if all(row.get(key) == expected for key, expected in criteria.items())]

    def list_packs(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(item) for item in self._entries.values())
