from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from decimal import Decimal
import importlib.resources as resources
from pathlib import Path
from typing import Any

from ...domain.common.enums import StandardDataStatus
from .pack_validator import StandardPackValidator


def repository_text_sha256(data: bytes) -> str:
    """仓库既有文本哈希规则：UTF-8 文本、CRLF→LF 归一后 SHA-256（大写十六进制）。

    与 `tools/validate_phase1_contracts.py::_sha256(normalize_repository_text=True)`
    和 `tools/build_phase3_chemical_golden.py::canonical_file_sha256` 保持一致。
    """

    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest().upper()


def canonical_source_sha256(path: Path) -> str:
    """对实际 Canonical 源文件计算 SHA-256（不改写文件内容）。"""

    return repository_text_sha256(Path(path).read_bytes())


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
        # M3-G1：同一个 repository 实例里，同一个标准包只做一次
        # read → parse → validate → SHA-256，并缓存组装完成的快照。
        # 缓存范围**严格限定在本实例**：不是进程级缓存、不是磁盘缓存、
        # 不跨启动存活；软件重启后重新读取即可（标准包对实例生命周期不可变）。
        # 每次返回前仍然 deepcopy，调用方拿到的对象互相隔离；并发首次访问最多
        # 重复一次读取，dict 整体赋值是原子的，不会返回半成品或错误数据。
        self._pack_cache: dict[str, dict[str, Any]] = {}

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
        # M3-G1：同一实例内同一标准包只读一次；命中缓存时只做 deepcopy。
        cached = self._pack_cache.get(device_type)
        if cached is None:
            cached = self._load_pack(device_type, entry, source)
            self._pack_cache[device_type] = cached
        # 恒返回 deepcopy：这是本轮的硬约束，调用方修改返回值不得污染缓存，
        # 也不得影响下一次 get_pack（改成返回共享 dict 属于后续独立决策）。
        return deepcopy(cached)

    def _load_pack(self, device_type: str, entry: dict[str, Any],
                   source: Path) -> dict[str, Any]:
        """首次访问：read → parse → validate → SHA-256，返回组装完成的快照。

        只在完成校验后返回；校验失败时抛错且**不写入缓存**，
        因此后续访问仍会重新读取并再次明确失败，不会把失败静默缓存成成功。
        """

        # Pump formula coefficients and table boundaries are decimal source
        # literals.  Keep their JSON lexemes exact instead of first parsing
        # them as binary floats; other packages retain their historical loader.
        if device_type in {"pump_water", "pump_chemical"}:
            data = json.loads(source.read_text(encoding="utf-8"), parse_float=Decimal)
        else:
            data = json.loads(source.read_text(encoding="utf-8"))
        data["pack_id"] = entry["pack_id"]
        data["device_type"] = device_type
        data["status"] = entry.get("status", StandardDataStatus.NORMALIZED.value)
        data["data_version"] = entry.get("data_version", entry["pack_id"])
        data["source_file"] = entry.get("source_file", str(source))
        # 注入实际 Canonical 源的 SHA-256（UTF-8、CRLF→LF）。这是业务真值来源
        # 的客观指纹，供 Record 固化与审计；不得用 commit SHA 或空值冒充。
        data["pack_hash"] = self._source_sha256(source)
        validation_key = str(source)
        if validation_key not in self._validated_sources:
            issues = self._validator.validate(data)
            if issues:
                raise StandardPackError(f"标准包{device_type}结构校验失败：{'；'.join(issues)}")
            self._validated_sources.add(validation_key)
        return data

    def _source_sha256(self, source: Path) -> str:
        """Canonical 源文件的 SHA-256（UTF-8、CRLF→LF）。

        包以 zip 资源形式导入时无法按路径读取，此时从包资源读取字节，
        仍使用同一哈希规则；任何读取失败都明确报错，不返回空值冒充。
        """

        if self._package_resource_root is None:
            try:
                return canonical_source_sha256(source)
            except OSError as exc:
                raise StandardPackError(f"无法读取 Canonical 源以计算哈希: {source}") from exc
        relative = str(source).replace("\\", "/")
        marker = "/equipeffi/"
        index = relative.find(marker)
        resource_name = relative[index + len(marker):] if index >= 0 else source.name
        try:
            resource = self._package_resource_root.joinpath(*resource_name.split("/"))
            raw = resource.read_bytes()
        except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
            raise StandardPackError(f"无法读取 Canonical 包资源以计算哈希: {resource_name}") from exc
        return repository_text_sha256(raw)

    def find(self, device_type: str, criteria: dict[str, Any]) -> list[dict[str, Any]]:
        pack = self.get_pack(device_type)
        rows = pack.get("records") or pack.get("rows") or []
        return [row for row in rows
                if all(row.get(key) == expected for key, expected in criteria.items())]

    def list_packs(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(item) for item in self._entries.values())
