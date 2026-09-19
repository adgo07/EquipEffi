"""可重复执行的EquipEffi发布审计。

该脚本把分散的交付验收合并成一个只读命令：检查15类公共接口、17个
内部标准包、永磁同步电机复核激活门禁、V4模板/验证覆盖、人工校对册同源性，
以及wheel中是否包含自洽的资源。它不修改任何输入文件，也不负责把人工
建议修订写回标准JSON。

用法（在仓库根目录）：
    python tools/audit_release.py
    python tools/audit_release.py --wheel tmp/release-20260826/equipeffi-0.2.1-py3-none-any.whl
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zipfile import BadZipFile, ZipFile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
_DEFAULT_REVIEW = object()
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from equipeffi.application.services.v4_template_contract import V4_DEVICE_SHEETS  # noqa: E402
from equipeffi.application.services.evaluation_service import EvaluationService  # noqa: E402
from equipeffi.domain.common.enums import Conclusion, EliminationScope  # noqa: E402
from equipeffi.domain.common.models import DeviceDraft  # noqa: E402
from equipeffi.domain.evaluation.device_specs import get_device_spec, list_device_specs  # noqa: E402
from equipeffi.domain.evaluation.device_types import PUBLIC_DEVICE_TYPES, public_device_types  # noqa: E402
from equipeffi.domain.evaluation.elimination import EliminationMatcher  # noqa: E402
from equipeffi.infrastructure.excel.template_resource import DEFAULT_V4_TEMPLATE  # noqa: E402
from equipeffi.infrastructure.excel.v4_template_audit import audit_v4_template  # noqa: E402
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository  # noqa: E402

# 产业目录当前只纳入用户明确列出的设备相关条目：11项原文拆分成13条
# 受控规则。将ID清单放在发布审计中，使没有原始PDF可读时也能发现过期、
# 多余或重复规则，而不是只依赖运行时“能否加载”。
try:
    from .verify_industry_catalog import EXPECTED as INDUSTRY_EXPECTED  # type: ignore[no-redef]  # noqa: E402
except ImportError:  # direct execution
    from verify_industry_catalog import EXPECTED as INDUSTRY_EXPECTED  # noqa: E402

INDUSTRY_EXPECTED_IDS = frozenset(item[0] for item in INDUSTRY_EXPECTED)

try:  # import as ``tools.audit_release`` from tests or another Python module
    from .audit_v4_validations import audit as audit_validations  # type: ignore[no-redef]  # noqa: E402
    from .validate_human_review_book import validate as validate_review_book  # type: ignore[no-redef]  # noqa: E402
except ImportError:  # direct execution: ``python tools/audit_release.py``
    from audit_v4_validations import audit as audit_validations  # noqa: E402
    from validate_human_review_book import validate as validate_review_book  # noqa: E402


@dataclass(frozen=True)
class ReleaseAudit:
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: dict[str, Any]


def _default_review_book(root: Path) -> Path:
    """按交付日期/ ``latest`` 标记选择校对册，避免误读历史版本。"""

    output_root = Path(root) / "outputs"
    candidates = [
        path for directory in output_root.glob("final_*")
        for path in [directory / "设备能效标准数据_人工校对版.xlsx"]
        if path.is_file()
    ]
    if candidates:
        def sort_key(path: Path) -> tuple[str, int, int]:
            match = re.search(r"final_(\d{8})", path.parent.name)
            date_key = match.group(1) if match else "00000000"
            latest_key = int("latest" in path.parent.name.lower())
            return date_key, latest_key, path.stat().st_mtime_ns

        return max(candidates, key=sort_key)
    # 保留稳定的缺失文件提示路径，便于调用方显示下一步动作。
    return output_root / "final_latest" / "设备能效标准数据_人工校对版.xlsx"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _audit_public_contract(errors: list[str], checks: dict[str, Any]) -> None:
    public = tuple(public_device_types())
    checks["public_device_type_count"] = len(public)
    if len(public) != 15 or tuple(PUBLIC_DEVICE_TYPES) != tuple(item["code"] for item in public):
        errors.append("公共设备类型不是固定的15类V4接口")
    if set(V4_DEVICE_SHEETS) != {item["sheet"] for item in public}:
        errors.append("公共设备类型与V4设备sheet集合不一致")
    checks["public_device_types"] = [item["code"] for item in public]


def _audit_manifest(src: Path, errors: list[str], checks: dict[str, Any]) -> None:
    manifest_path = src / "equipeffi" / "standard_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"无法读取标准manifest: {exc}")
        return
    entries = manifest.get("packs", [])
    checks["manifest_pack_count"] = len(entries)
    if len(entries) != 17:
        errors.append(f"标准manifest应有17个内部profile，实际{len(entries)}个")
    by_type = {str(item.get("device_type")): item for item in entries}
    pmsm = by_type.get("motor_pmsm", {})
    checks["pmsm_status"] = pmsm.get("status", "")
    checks["pmsm_pack_id"] = pmsm.get("pack_id", "")
    if pmsm.get("pack_id") != "gb30253_2024_pdf_verified_v1":
        errors.append("永磁同步电机未使用独立PDF重建包ID")
    if pmsm.get("status") != "active":
        errors.append("永磁同步电机标准包未处于用户复核后的active状态")
    source_names = {str(item.get("source", "")).replace("\\", "/") for item in entries}
    if any(name.endswith("/motor_pmsm.json") or name == "resources/standards/motor_pmsm.json" for name in source_names):
        errors.append("manifest仍引用旧永磁同步电机JSON")
    old_source = src / "equipeffi" / "resources" / "standards" / "motor_pmsm.json"
    if old_source.is_file():
        errors.append(f"资源目录仍存在禁止加载的旧永磁同步电机JSON: {old_source}")
    repository = JsonStandardRepository(src / "equipeffi", manifest=manifest_path)
    checks["loaded_pack_count"] = len(repository.list_packs())
    for entry in entries:
        source = src / "equipeffi" / str(entry.get("source", "")).replace("/", "\\")
        if not source.is_file():
            errors.append(f"manifest标准包文件不存在: {entry.get('device_type')} -> {source}")


def _audit_pmsm_confirmed_no_data(src: Path, errors: list[str], checks: dict[str, Any]) -> None:
    """锁定用户确认的PMSM无数据单元格，防止后续重建误填或误插值。

    该审计只检查机器包中的结构化标记，不修改标准数据；它与完整的29张表
    人工复核门禁互补。表1/55 kW/12极的三档效率必须都是 ``None``，并且
    行内无数据索引必须覆盖同一维度的三个等级。
    """

    source = src / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"
    expected = {
        "table_no": 1,
        "power_kw": 55.0,
        "dimension": 12,
        "levels": ["1", "2", "3"],
        "no_data_indexes": [5, 12, 19],
    }
    record: dict[str, Any] = {
        "source": str(source.resolve()),
        "expected": expected,
        "is_valid": False,
    }
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        table = next(item for item in payload.get("tables", []) if item.get("table_no") == 1)
        dims = list(table.get("dims", []))
        dimension_index = dims.index(expected["dimension"])
        row = next(item for item in table.get("rows", []) if item.get("power_kw") == expected["power_kw"])
        efficiency = row.get("efficiency", {})
        values = [
            efficiency[level][dimension_index]
            for level in expected["levels"]
        ]
        markers = list(row.get("no_data_cells", []))
        record.update({
            "actual_values": values,
            "actual_no_data_indexes": markers,
            "no_data_reason": row.get("no_data_reason", ""),
        })
        record["is_valid"] = (
            values == [None, None, None]
            and markers == expected["no_data_indexes"]
            and all(index < len(dims) * len(expected["levels"]) for index in markers)
        )
    except (OSError, json.JSONDecodeError, KeyError, StopIteration, ValueError, TypeError, IndexError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    checks["pmsm_confirmed_no_data"] = record
    if not record["is_valid"]:
        errors.append("PMSM表1/55 kW/12极1～3级无数据登记不符合用户确认值")


def _audit_hvac_boundaries(src: Path, errors: list[str], checks: dict[str, Any]) -> None:
    """核对HVAC容量分档的相邻开闭端点，不改写标准数据。"""

    try:
        from .audit_hvac_boundaries import audit
    except ImportError:  # direct execution
        from audit_hvac_boundaries import audit
    source = src / "equipeffi" / "resources" / "standards" / "hvac_thresholds.json"
    try:
        result = audit(source)
        checks["hvac_boundary_audit"] = result
        if not result.get("is_valid"):
            errors.append(f"HVAC标准容量分档边界审计发现{result.get('finding_count', 0)}项问题")
    except Exception as exc:  # pragma: no cover - audit should report, not crash
        errors.append(f"HVAC标准容量分档边界审计异常: {type(exc).__name__}: {exc}")


def _audit_standard_provenance(
    src: Path,
    warnings: list[str],
    checks: dict[str, Any],
    source_dir: Path | None = None,
) -> None:
    """记录标准包来源追溯覆盖；缺页码只告警，不猜测也不阻断发布。"""

    try:
        from .audit_standard_provenance import audit
    except ImportError:  # direct execution
        from audit_standard_provenance import audit
    manifest = src / "equipeffi" / "standard_manifest.json"
    try:
        result = audit(manifest, source_dir)
    except Exception as exc:  # pragma: no cover - provenance is supplementary
        warnings.append(f"标准来源覆盖审计异常: {type(exc).__name__}: {exc}")
        return
    # 将完整逐包数据保留在JSON审计中，便于维护者后续按包补录，不把它
    # 变成发布硬门禁；PMSM的激活门禁仍由manifest/校对册审计负责。
    checks["standard_provenance"] = result
    incomplete = [
        item for item in result.get("packs", [])
        if item.get("record_count")
        and item.get("records_with_id_and_page") != item.get("record_count")
    ]
    if incomplete:
        warnings.append(
            "标准来源追溯尚未覆盖全部记录（非阻断）："
            + ", ".join(str(item.get("device_type", "")) for item in incomplete)
        )


def _audit_elimination_catalog(errors: list[str], checks: dict[str, Any]) -> None:
    """校验四批目录与用户提供产业条目的合并快照。"""

    try:
        matcher = EliminationMatcher()
        industry_ids = sorted(entry.entry_id for entry in matcher.entries if not entry.batch)
        resource_path = SRC / "equipeffi" / "resources" / "elimination_catalog_industry_2024.json"
        resource_ids: list[str] = []
        if resource_path.is_file():
            payload = json.loads(resource_path.read_text(encoding="utf-8"))
            resource_ids = [
                str(item.get("entry_id", ""))
                for item in payload.get("entries", [])
                if item.get("entry_id")
            ]
        resource_id_set = set(resource_ids)
        missing_ids = sorted(INDUSTRY_EXPECTED_IDS - resource_id_set)
        extra_ids = sorted(resource_id_set - INDUSTRY_EXPECTED_IDS)
        duplicate_ids = sorted({item for item in resource_ids if resource_ids.count(item) > 1})
        checks["elimination_catalog"] = {
            "entry_count": len(matcher.entries),
            "source_entry_count": matcher.source_entry_count,
            "industry_source_item_count": matcher.industry_source_item_count,
            "review_only_entry_count": matcher.review_only_entry_count,
            "has_industry_catalog": matcher.has_industry_catalog,
            "industry_catalog_complete": matcher.industry_catalog_complete,
            "industry_entry_ids": industry_ids,
            "industry_resource_rule_count": len(resource_ids),
            "industry_missing_rule_ids": missing_ids,
            "industry_extra_rule_ids": extra_ids,
            "industry_duplicate_rule_ids": duplicate_ids,
            "catalog_status": matcher.catalog_status,
            "data_version": matcher.catalog_data_version,
        }
        if not matcher.has_industry_catalog:
            errors.append("淘汰目录缺少用户提供的产业目录条目资源")
        # 四批DOCX来源共402条，产业目录原文为11项；产业目录拆分后
        # 的13条受控规则另由industry_resource_rule_count单独审计。
        if matcher.source_entry_count < 413:
            errors.append(f"淘汰目录来源条目数异常，至少应为413，实际{matcher.source_entry_count}")
        if matcher.industry_source_item_count != 11:
            errors.append(f"产业目录原文条目数应为11，实际{matcher.industry_source_item_count}")
        if len(resource_ids) != 13:
            errors.append(f"产业目录受控匹配规则数应为13，实际{len(resource_ids)}")
        if missing_ids:
            errors.append(f"产业目录机器资源缺少受控规则: {', '.join(missing_ids)}")
        if extra_ids:
            errors.append(f"产业目录机器资源存在未登记规则: {', '.join(extra_ids)}")
        if duplicate_ids:
            errors.append(f"产业目录机器资源存在重复规则ID: {', '.join(duplicate_ids)}")
        # 受控产业目录不是全文时，发布门禁还要验证“未命中”不会
        # 静默降级为能效等级；明确命中则必须继续保留淘汰优先级。
        try:
            manifest_path = SRC / "equipeffi" / "standard_manifest.json"
            service = EvaluationService(
                JsonStandardRepository(SRC / "equipeffi", manifest=manifest_path),
                elimination=matcher,
            )
            unknown = service.evaluate(
                DeviceDraft(
                    "AUDIT-INDUSTRY-UNKNOWN",
                    "compressor",
                    {"model": "AUDIT-UNLISTED-MODEL"},
                ),
                elimination_scope=EliminationScope.INDUSTRY_ONLY,
            )
            explicit = service.evaluate(
                DeviceDraft(
                    "AUDIT-INDUSTRY-EXPLICIT",
                    "compressor",
                    {"model": "3W-0.9/7"},
                ),
                elimination_scope=EliminationScope.INDUSTRY_ONLY,
            )
            combined_motor = service.evaluate(
                DeviceDraft(
                    "AUDIT-COMBINED-MOTOR",
                    "motor_lv",
                    {
                        "model": "YB160M-4",
                        "frame_size_mm": 160,
                        "rated_voltage_v": 660,
                    },
                ),
                elimination_scope=EliminationScope.INDUSTRY_AND_MOTOR_BATCHES,
            )
            # 适配器通常传入枚举，但配置文件/第三方调用也可能传入
            # 中文字符串；审计这个路径，确保字符串不会绕过目录筛选。
            string_scope_batch_only_model = service.evaluate(
                DeviceDraft(
                    "AUDIT-STRING-SCOPE-BATCH-ONLY",
                    "transformer",
                    {"model": "S8-100", "production_year": 1997},
                ),
                elimination_scope=EliminationScope.INDUSTRY_ONLY.value,
            )
            behavior = {
                "catalog_complete": bool(matcher.industry_catalog_complete),
                "unknown_model_conclusion": unknown.conclusion.value,
                "explicit_model_conclusion": explicit.conclusion.value,
                "combined_motor_batch_conclusion": combined_motor.conclusion.value,
                "string_scope_batch_only_model_conclusion": string_scope_batch_only_model.conclusion.value,
                "unknown_trace_output": next(
                    (
                        item.get("output", "")
                        for item in unknown.trace
                        if item.get("step_type") == "淘汰检查"
                    ),
                    "",
                ),
            }
            checks["industry_scope_behavior"] = behavior
            if not matcher.industry_catalog_complete:
                if unknown.conclusion is not Conclusion.UNABLE_TO_JUDGE:
                    errors.append("非全文产业目录未命中时错误地继续了能效判定")
                if explicit.conclusion is not Conclusion.ELIMINATED:
                    errors.append("产业目录明确命中未保持淘汰优先级")
                if combined_motor.conclusion is not Conclusion.ELIMINATED:
                    errors.append("组合口径下四批目录明确命中未保持淘汰优先级")
                if string_scope_batch_only_model.conclusion is not Conclusion.UNABLE_TO_JUDGE:
                    errors.append("字符串淘汰口径绕过产业目录过滤")
        except Exception as exc:  # pragma: no cover - release audit must report
            errors.append(f"产业目录口径行为审计异常: {type(exc).__name__}: {exc}")
    except Exception as exc:  # pragma: no cover - audit should report, not crash
        errors.append(f"淘汰目录加载审计异常: {type(exc).__name__}: {exc}")


def _audit_industry_source(pdf: Path, errors: list[str], checks: dict[str, Any]) -> None:
    """可选核对产业目录原始PDF中的设备相关条目。"""
    try:
        from .verify_industry_catalog import verify
    except ImportError:  # direct execution
        from verify_industry_catalog import verify
    try:
        result = verify(Path(pdf))
        checks["industry_source_pdf"] = {
            "path": result["pdf"],
            "sha256": result["sha256"],
            "expected_count": result["expected_count"],
            "verified_count": result["verified_count"],
            "resource_entry_count": result["resource_entry_count"],
            "missing_resource_ids": result["missing_resource_ids"],
            "extra_resource_ids": result.get("extra_resource_ids", []),
            "duplicate_resource_ids": result.get("duplicate_resource_ids", []),
        }
        if result["verified_count"] != result["expected_count"]:
            errors.append(f"产业目录PDF设备条目核对不完整: {result['verified_count']}/{result['expected_count']}")
        if result["missing_resource_ids"]:
            errors.append(f"产业目录机器资源缺少受控规则: {', '.join(result['missing_resource_ids'])}")
        if result.get("extra_resource_ids"):
            errors.append(f"产业目录机器资源存在未登记规则: {', '.join(result['extra_resource_ids'])}")
        if result.get("duplicate_resource_ids"):
            errors.append(f"产业目录机器资源存在重复规则ID: {', '.join(result['duplicate_resource_ids'])}")
        resource = SRC / "equipeffi" / "resources" / "elimination_catalog_industry_2024.json"
        payload = json.loads(resource.read_text(encoding="utf-8"))
        expected_hash = str((payload.get("source_document") or {}).get("sha256", "")).upper()
        if expected_hash and str(result["sha256"]).upper() != expected_hash:
            errors.append("产业目录PDF SHA-256与机器资源登记不一致")
    except Exception as exc:  # pragma: no cover - audit should report, not crash
        errors.append(f"产业目录PDF来源审计异常: {type(exc).__name__}: {exc}")


def _audit_evaluator_examples(src: Path, errors: list[str], checks: dict[str, Any]) -> None:
    """用每个内部profile的标准示例做一次非破坏性端到端烟测。"""
    manifest_path = src / "equipeffi" / "standard_manifest.json"
    try:
        service = EvaluationService(JsonStandardRepository(src / "equipeffi", manifest=manifest_path))
        results: dict[str, str] = {}
        trace_data_ids: dict[str, list[str]] = {}
        for device_type in list_device_specs():
            example = dict(get_device_spec(device_type).get("example", {}))
            result = service.evaluate(DeviceDraft(f"RELEASE-{device_type}", device_type, example))
            results[device_type] = result.conclusion.value
            standard_step = next(
                (item for item in result.trace if item.get("step_type") == "标准查询结果"),
                None,
            )
            ids = [str(item) for item in (standard_step or {}).get("data_ids", []) if item not in (None, "")]
            trace_data_ids[device_type] = ids
            # 所有已激活标准包的成功示例必须留下可回溯的标准记录ID；
            # 对于标准原文“—”导致的不在范围示例，仍需保留查表轨迹。
            if result.conclusion.value != "无法判定" and not ids:
                errors.append(f"评价器示例{device_type}缺少标准查询结果data_id")
        checks["evaluator_examples"] = results
        checks["evaluator_trace_data_ids"] = trace_data_ids
        # 级数是多级泵公式的离散输入轴；发布审计用一个绕过上层
        # V4验证的字符串值确认评价器仍会拒绝非整数，避免手工/API
        # 入口把虚构的单级扬程带入比转速计算。
        integer_stage_results: dict[str, str] = {}
        for device_type, category in (("pump_water", "多级"), ("pump_chemical", "多级石油化工离心泵")):
            example = dict(get_device_spec(device_type).get("example", {}))
            example.update({"category": category, "stages": "1.5"})
            invalid_stage = service.evaluate(DeviceDraft(f"RELEASE-{device_type}-INVALID-STAGES", device_type, example))
            integer_stage_results[device_type] = invalid_stage.conclusion.value
            if invalid_stage.conclusion is not Conclusion.UNABLE_TO_JUDGE or "级数" not in invalid_stage.missing_fields:
                errors.append(f"评价器示例{device_type}未拒绝非整数级数")
        checks["pump_integer_stage_validation"] = integer_stage_results
        range_miss_context: dict[str, Any] = {}
        for device_type, category in (("pump_water", "单级单吸"), ("pump_chemical", "单级石油化工离心泵")):
            example = dict(get_device_spec(device_type).get("example", {}))
            example.update({"category": category, "flow_m3h": "0.1", "head_m": 50, "rated_speed_rpm": 2900, "pump_efficiency": 80})
            range_miss = service.evaluate(DeviceDraft(f"RELEASE-{device_type}-RANGE-MISS", device_type, example))
            has_context = (
                range_miss.conclusion is Conclusion.OUT_OF_SCOPE
                and "泵效率_%" in range_miss.actual_metrics
                and "比转速" in range_miss.calculated_metrics
                and "输出功率_kW" in range_miss.calculated_metrics
            )
            range_miss_context[device_type] = has_context
            if not has_context:
                errors.append(f"评价器示例{device_type}范围外终止时丢失实际/计算指标")
        checks["pump_range_miss_context"] = range_miss_context
        early_context_cases = {
            "transformer": (
                "transformer",
                {"model": "AUDIT-TRANSFORMER", "category": "10kV油浸式三相双绕组无励磁调压配电变压器", "capacity_kva": 999999, "core_material": "电工钢带", "connection": "Dyn11/Yzn11", "no_load_loss_w": 120, "load_loss_w": 1140},
                Conclusion.OUT_OF_SCOPE,
                ("空载损耗_W", "负载损耗_W"),
                (),
            ),
            "motor_lv": (
                "motor_lv",
                {"category": "三相异步电动机（一般用途）", "rated_power_kw": 99999, "poles": 4, "rated_efficiency": 98},
                Conclusion.OUT_OF_SCOPE,
                ("额定效率_%",),
                (),
            ),
            "compressor": (
                "compressor",
                {"category": "一般用喷油回转（工频）", "input_power_kw": 1.6, "discharge_pressure_mpa": 0.3, "cooling_method": "风冷", "specific_power": 5.8},
                Conclusion.OUT_OF_SCOPE,
                ("机组比功率_kW/(m3/min)",),
                (),
            ),
            "blower": (
                "blower",
                {"category": "单级双支撑低速离心鼓风机", "impeller_width_mm": 30, "impeller_diameter_mm": 300, "polytropic_efficiency": 80},
                Conclusion.OUT_OF_SCOPE,
                ("多变效率_%",),
                ("b2/D2",),
            ),
            "fan": (
                "fan",
                {"category": "离心通风机", "machine_no": 10, "pressure_coefficient": 5, "specific_speed": 40, "compression_correction": 1, "fan_efficiency": 80},
                Conclusion.OUT_OF_SCOPE,
                ("最高通风机效率ηr_%",),
                ("压力系数",),
            ),
            "submersible": (
                "submersible",
                {"category": "小型潜水电泵", "subtype": "未列入标准的型式", "rated_power_kw": 1.5, "pump_efficiency": 50, "efficiency_tolerance": 2, "flow_m3h": 20, "pump_form": "下泵式", "specific_speed": 50, "motor_efficiency": 71},
                Conclusion.OUT_OF_SCOPE,
                ("电泵效率_%",),
                ("规定效率ηDB_%",),
            ),
            "multi_split_static_pressure": (
                "multi_split_ac",
                {"category": "风冷单冷", "cooling_capacity_w": 10000, "rated_power_kw": 2, "external_static_pressure_pa": 120, "seer": 5.5, "eer": 3.6},
                Conclusion.UNABLE_TO_JUDGE,
                ("SEER",),
                (),
            ),
            "heat_treatment": (
                "heat_treatment",
                {"category": "箱式多用炉", "energy_type": "电力", "equivalent_weight_t": 1, "total_electricity_kwh": 600},
                Conclusion.UNABLE_TO_JUDGE,
                ("电炉可比单耗",),
                ("可比单耗未舍入值",),
            ),
        }
        early_context_results: dict[str, bool] = {}
        for name, (device_type, values, expected, actual_keys, calculated_keys) in early_context_cases.items():
            context_result = service.evaluate(DeviceDraft(f"RELEASE-{name}-CONTEXT", device_type, values))
            has_context = context_result.conclusion is expected and all(key in context_result.actual_metrics for key in actual_keys) and all(key in context_result.calculated_metrics for key in calculated_keys)
            early_context_results[name] = has_context
            if not has_context:
                errors.append(f"评价器示例{name}终止时未保留已计算指标")
        checks["early_termination_context"] = early_context_results
    except Exception as exc:  # pragma: no cover - converts a release failure to JSON
        errors.append(f"标准评价器示例烟测异常: {type(exc).__name__}: {exc}")


def _audit_workbooks(
    errors: list[str],
    warnings: list[str],
    checks: dict[str, Any],
    template: Path,
    review_book: Path | None,
) -> None:
    if not template.is_file():
        errors.append(f"V4模板不存在: {template}")
        return
    template_result = audit_v4_template(template)
    checks["template"] = asdict(template_result)
    if not template_result.is_valid:
        errors.append("V4模板结构/保护/公式审计失败")
    validation_result = audit_validations(template)
    checks["template_validations"] = validation_result
    if not validation_result.get("is_valid"):
        errors.append("V4模板数据验证覆盖审计失败")
    if review_book is None:
        return
    if not review_book.is_file():
        warnings.append(f"未找到人工校对册，跳过同源校验: {review_book}")
        return
    review_result = validate_review_book(review_book)
    checks["human_review_book"] = review_result
    if not review_result.get("is_valid"):
        errors.append("人工校对册同源/保护审计失败")


def _audit_wheel(errors: list[str], warnings: list[str], checks: dict[str, Any], wheel: Path | None) -> None:
    if wheel is None:
        return
    if not wheel.is_file():
        warnings.append(f"未找到wheel，跳过包内资源审计: {wheel}")
        return
    checks["wheel"] = {"path": str(wheel.resolve()), "sha256": _sha256(wheel)}
    required = {
        "equipeffi/__init__.py",
        "equipeffi/standard_manifest.json",
        f"equipeffi/resources/templates/{DEFAULT_V4_TEMPLATE}",
        "equipeffi/resources/standards/gb30253_2024_pdf_verified_v1.json",
        "equipeffi/resources/elimination_catalog_batches_1_4.json",
        "equipeffi/resources/elimination_catalog_industry_2024.json",
        "equipeffi/presentation/api/jsonl_server.py",
    }
    try:
        with ZipFile(wheel) as archive:
            names = set(archive.namelist())
            missing = sorted(required - names)
            checks["wheel_member_count"] = len(names)
            checks["wheel_missing_members"] = missing
            if missing:
                errors.append("wheel缺少必要资源: " + ", ".join(missing))
            if "equipeffi/resources/standards/motor_pmsm.json" in names:
                errors.append("wheel包含禁止加载的旧永磁同步电机JSON")
            try:
                manifest = json.loads(archive.read("equipeffi/standard_manifest.json"))
                pmsm = next(item for item in manifest["packs"] if item["device_type"] == "motor_pmsm")
                checks["wheel_pmsm_status"] = pmsm.get("status", "")
                if pmsm.get("status") != "active":
                    errors.append("wheel中的永磁同步电机标准包未标记为active")
            except (KeyError, StopIteration, json.JSONDecodeError) as exc:
                errors.append(f"wheel中的标准manifest无效: {exc}")
    except (OSError, BadZipFile) as exc:
        errors.append(f"wheel不是有效压缩包: {exc}")
    # 成员存在并不等于资源加载路径正确；用隔离的Python进程从wheel本身
    # 读取manifest、模板和一个普通电机样例，避免误用当前源码目录。
    code = (
        "from equipeffi.entrypoint import _api; "
        "api=_api(); "
        "assert len(api.device_types()) == 15; "
        "status=api.status(); "
        "assert status['public_device_type_count'] == 15 and status['elimination']['entry_count'] > 0; "
        "assert api.schema('motor')['fields']; "
        "result=api.evaluate({'device_type':'motor','values':{"
        "'category':'三相异步电动机（一般用途）','rated_voltage':'0.4',"
        "'rated_power':7.5,'poles':4,'rated_speed':1480,'efficiency':98}}); "
        "assert result['conclusion'] == '1级'; "
        "batch=api.evaluate_batch({'records':[{'record_id':'W-BATCH','device_type':'motor','values':{"
        "'category':'三相异步电动机','rated_voltage':'0.4','rated_power':7.5,"
        "'poles':4,'rated_speed':1480,'efficiency':98}}]}); "
        "assert len(batch) == 1 and batch[0]['record_id'] == 'W-BATCH'; "
        "import io, json; from equipeffi.presentation.api.jsonl_server import run_jsonl; "
        "stream=io.StringIO(); run_jsonl(api, io.StringIO('{\\\"op\\\":\\\"status\\\"}\\n{\\\"op\\\":\\\"quit\\\"}\\n'), stream); "
        "assert [json.loads(line)['op'] for line in stream.getvalue().splitlines()] == ['status','quit']; "
        "print('wheel-runtime-ok')"
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    try:
        runtime = subprocess.run(
            [sys.executable, "-S", "-c", code],
            cwd=str(wheel.parent),
            env={**env, "PYTHONPATH": str(wheel.resolve())},
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"wheel运行时烟测无法启动: {exc}")
    else:
        checks["wheel_runtime_stdout"] = runtime.stdout.strip()
        if runtime.returncode != 0 or runtime.stdout.strip() != "wheel-runtime-ok":
            errors.append(f"wheel运行时烟测失败: {runtime.stderr.strip() or runtime.stdout.strip()}")


def _audit_elimination_sources(source_dir: Path, errors: list[str], checks: dict[str, Any]) -> None:
    """可选地核对外部DOCX来源；不传目录时保持离线发布审计自包含。"""
    try:
        from .verify_elimination_sources import verify
    except ImportError:  # direct execution
        from verify_elimination_sources import verify
    result = verify(source_dir)
    checks["elimination_sources"] = result
    if not result.get("is_valid"):
        errors.append("第一至第四批淘汰目录DOCX来源核对失败")


def _audit_native_report(report_path: Path, errors: list[str], checks: dict[str, Any]) -> None:
    """核验可选的PyInstaller构建报告及其可执行文件。"""

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"原生构建报告无法读取: {exc}")
        return
    if not isinstance(report, dict):
        errors.append("原生构建报告必须是JSON对象")
        return
    required = ("platform", "executable", "gui_capable", "presentation_mode")
    missing = [key for key in required if key not in report]
    if missing:
        errors.append("原生构建报告缺少字段: " + ", ".join(missing))
    mode = str(report.get("presentation_mode", ""))
    if mode not in {"native_tk", "web_fallback"}:
        errors.append(f"原生构建报告presentation_mode无效: {mode}")
    executable = Path(str(report.get("executable", "")))
    if not executable.is_file():
        errors.append(f"原生构建报告指向的可执行文件不存在: {executable}")
    package_info = report.get("package")
    package_check: dict[str, Any] = {}
    if package_info is not None:
        if not isinstance(package_info, dict):
            errors.append("原生构建报告package必须是JSON对象")
        else:
            package_path = Path(str(package_info.get("path", "")))
            package_check = {"path": str(package_path), "sha256": str(package_info.get("sha256", ""))}
            if not package_path.is_file():
                errors.append(f"原生构建报告指向的ZIP不存在: {package_path}")
            else:
                actual_package_hash = _sha256(package_path)
                package_check["actual_sha256"] = actual_package_hash
                expected_package_hash = str(package_info.get("sha256", ""))
                if expected_package_hash and expected_package_hash != actual_package_hash:
                    errors.append("原生ZIP SHA-256与构建报告不一致")
                try:
                    with ZipFile(package_path) as archive:
                        names = set(archive.namelist())
                    expected_member = f"{executable.parent.name}/{executable.name}"
                    package_check["member_count"] = len(names)
                    package_check["executable_member"] = expected_member
                    if expected_member not in names:
                        errors.append(f"原生ZIP缺少启动文件: {expected_member}")
                except (OSError, BadZipFile) as exc:
                    errors.append(f"原生ZIP无效: {exc}")
    checks["native_build"] = {
        "report": str(report_path.resolve()),
        "platform": report.get("platform", ""),
        "executable": str(executable),
        "gui_capable": bool(report.get("gui_capable")),
        "presentation_mode": mode,
        "sha256": str(report.get("sha256", "")),
    }
    if package_check:
        checks["native_build"]["package"] = package_check


def _audit_portable_bundle(bundle_path: Path, errors: list[str], checks: dict[str, Any]) -> None:
    """校验便携ZIP清单和成员哈希。"""

    try:
        from .validate_portable_bundle import validate
    except ImportError:  # direct execution
        from validate_portable_bundle import validate
    result = validate(Path(bundle_path))
    checks["portable_bundle"] = result
    if not result.get("is_valid"):
        errors.append("便携ZIP清单/哈希审计失败")


def audit_project(
    root: Path = ROOT,
    *,
    template: Path | None = None,
    review_book: Path | None | object = _DEFAULT_REVIEW,
    wheel: Path | None = None,
    elimination_source_dir: Path | None = None,
    industry_source_pdf: Path | None = None,
    standard_source_dir: Path | None = None,
    native_report: Path | None = None,
    portable_bundle: Path | None = None,
) -> ReleaseAudit:
    """执行只读项目审计并返回可序列化结果。"""
    root = Path(root).resolve()
    source_root = root / "src"
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {"root": str(root)}
    _audit_public_contract(errors, checks)
    _audit_manifest(source_root, errors, checks)
    _audit_pmsm_confirmed_no_data(source_root, errors, checks)
    _audit_hvac_boundaries(source_root, errors, checks)
    _audit_standard_provenance(source_root, warnings, checks, standard_source_dir)
    _audit_elimination_catalog(errors, checks)
    _audit_evaluator_examples(source_root, errors, checks)
    template_path = Path(template) if template else source_root / "equipeffi" / "resources" / "templates" / DEFAULT_V4_TEMPLATE
    review_path = (
        _default_review_book(root)
        if review_book is _DEFAULT_REVIEW
        else Path(review_book) if review_book is not None else None
    )
    _audit_workbooks(errors, warnings, checks, template_path, review_path)
    _audit_wheel(errors, warnings, checks, Path(wheel) if wheel else None)
    if elimination_source_dir is not None:
        _audit_elimination_sources(Path(elimination_source_dir), errors, checks)
    if industry_source_pdf is not None:
        _audit_industry_source(Path(industry_source_pdf), errors, checks)
    if native_report is not None:
        _audit_native_report(Path(native_report), errors, checks)
    if portable_bundle is not None:
        _audit_portable_bundle(Path(portable_bundle), errors, checks)
    return ReleaseAudit(not errors, tuple(errors), tuple(warnings), checks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="审计EquipEffi项目发布状态")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--review-book", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--elimination-source-dir", type=Path, help="可选：核对第一至第四批DOCX来源目录")
    parser.add_argument("--industry-source-pdf", type=Path, help="可选：核对2024年产业目录设备条目原始PDF")
    parser.add_argument("--standard-source-dir", type=Path, help="可选：标准PDF目录，仅用于来源文件名存在性提示")
    parser.add_argument("--native-report", type=Path, help="可选：核验PyInstaller原生构建报告及可执行文件")
    parser.add_argument("--portable-bundle", type=Path, help="可选：核验便携ZIP清单及成员SHA-256")
    parser.add_argument("--output", type=Path, help="可选：将审计JSON同时写入指定文件")
    args = parser.parse_args(argv)
    audit_kwargs: dict[str, Any] = {
        "template": args.template,
        "wheel": args.wheel,
        "elimination_source_dir": args.elimination_source_dir,
        "industry_source_pdf": args.industry_source_pdf,
        "standard_source_dir": args.standard_source_dir,
        "native_report": args.native_report,
        "portable_bundle": args.portable_bundle,
    }
    # 不传--review-book时使用项目默认校对册；显式传空值无法通过CLI表达，
    # 需要跳过时由Python API传 review_book=None（构建脚本使用该接口）。
    if args.review_book is not None:
        audit_kwargs["review_book"] = args.review_book
    result = audit_project(args.root, **audit_kwargs)
    payload = json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str)
    print(payload)
    if args.output is not None:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
