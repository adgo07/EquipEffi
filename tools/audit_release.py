"""只读核验当前 Qt/V6.2、正式泵、变压器与电机服务及发布资源。

用法（在仓库根目录）：
    python tools/audit_release.py
    python tools/audit_release.py --wheel dist/equipeffi-0.2.2-py3-none-any.whl
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import BadZipFile, ZipFile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datetime import date

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    PumpAnalysisRequest,
)
from equipeffi.application.services.transformer_analysis_service import (
    TransformerAnalysisRequest,
)
from equipeffi.domain.evaluation.elimination import EliminationMatcher
from equipeffi.infrastructure.excel.pump_workbook_reader import V6PumpWorkbookReader
from equipeffi.infrastructure.excel.unified_workbook_reader import UnifiedWorkbookReader
from equipeffi.infrastructure.excel.template_resource import (
    DEFAULT_V6_TEMPLATE,
    DEFAULT_V61_TEMPLATE,
    DEFAULT_V62_TEMPLATE,
    V6_TEMPLATE_IDENTITY,
    V62_TEMPLATE_IDENTITY,
    V6TemplateResource,
    V61TransformerTemplateResource,
    V62MotorTemplateResource,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from equipeffi.infrastructure.standards.transformer_repository import load_transformer_pack

try:
    from .check_distribution_assets import audit_artifact
except ImportError:  # direct execution
    from check_distribution_assets import audit_artifact

# 产业目录当前只纳入用户明确列出的设备相关条目：11项原文拆分成13条
# 受控规则。将ID清单放在发布审计中，使没有原始PDF可读时也能发现过期、
# 多余或重复规则，而不是只依赖运行时“能否加载”。
try:
    from .verify_industry_catalog import EXPECTED as INDUSTRY_EXPECTED  # type: ignore[no-redef]  # noqa: E402
except ImportError:  # direct execution
    from verify_industry_catalog import EXPECTED as INDUSTRY_EXPECTED  # noqa: E402

INDUSTRY_EXPECTED_IDS = frozenset(item[0] for item in INDUSTRY_EXPECTED)

@dataclass(frozen=True)
class ReleaseAudit:
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    # 将逐包数据保留在JSON审计中，便于维护者补录来源信息；此覆盖率不作
    # 发布硬门禁，也不改变标准包的支持状态。
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
    """通过当前正式泵 Use Case 核验两个标准包及关键输入边界。"""

    try:
        from equipeffi.composition import create_pump_analysis_service

        service = create_pump_analysis_service(with_persistence=False)
        overview = service.standard_overview()
        profiles = {
            str(item.get("rule_profile")): item
            for item in overview.get("scopes", [])
            if isinstance(item, dict)
        }
        expected_profiles = {"pump_water", "pump_chemical"}
        checks["pump_profiles"] = {
            profile: {
                "available": bool(
                    profiles.get(profile, {}).get("support_status") == "SUPPORTED"
                    and profiles.get(profile, {}).get("pack_id")
                ),
                "support_status": profiles.get(profile, {}).get("support_status"),
                "pack_id": profiles.get(profile, {}).get("pack_id"),
            }
            for profile in sorted(expected_profiles)
        }
        if set(profiles) != expected_profiles:
            errors.append("正式泵服务必须只发布pump_water与pump_chemical两个profile")
        for profile, state in checks["pump_profiles"].items():
            if not state["available"]:
                errors.append(f"正式泵profile不可用或未SUPPORTED: {profile}")

        examples = {
            "pump_water": PumpAnalysisRequest(
                product_category="单级单吸清水离心泵",
                as_of=date.today(),
                QBEP="100", HBEP="50", speed="2900",
                efficiency="90", suction="单吸", stages="1",
            ),
            "pump_chemical": PumpAnalysisRequest(
                product_category="单级石油化工离心泵",
                as_of=date.today(),
                QBEP="100", HBEP="14", speed="2900",
                efficiency="73", suction="单吸", stages="1",
            ),
        }
        example_results: dict[str, dict[str, Any]] = {}
        for profile, request in examples.items():
            result = service.evaluate(request)
            example_results[profile] = {
                "evaluation_status": result.evaluation_status,
                "ui_conclusion": result.ui_conclusion,
                "matched_rule_id": result.matched_rule_id,
                "support_status": result.support_status,
            }
            if (
                result.rule_profile != profile
                or result.evaluation_status != "SUCCESS"
                or result.support_status != "SUPPORTED"
                or result.ui_conclusion not in {"1级", "2级", "3级", "未达3级"}
                or not result.matched_rule_id
            ):
                errors.append(f"正式泵服务示例未完成可追溯评价: {profile}")
        checks["pump_examples"] = example_results

        invalid_stage_results: dict[str, str] = {}
        for profile, category in (
            ("pump_water", "多级清水离心泵"),
            ("pump_chemical", "多级石油化工离心泵"),
        ):
            result = service.evaluate(PumpAnalysisRequest(
                product_category=category,
                as_of=date.today(),
                QBEP="100", HBEP="50", speed="2900",
                efficiency="90", suction="单吸", stages="1.5",
            ))
            invalid_stage_results[profile] = str(result.evaluation_status)
            if (
                result.evaluation_status != "INVALID_INPUT"
                or "STAGES_INVALID" not in result.issue_codes
            ):
                errors.append(f"{profile}未将非整数级数拒绝为INVALID_INPUT")
        checks["pump_integer_stage_validation"] = invalid_stage_results

        range_miss: dict[str, bool] = {}
        for profile, category in (
            ("pump_water", "单级单吸清水离心泵"),
            ("pump_chemical", "单级石油化工离心泵"),
        ):
            result = service.evaluate(PumpAnalysisRequest(
                product_category=category,
                as_of=date.today(),
                QBEP="0.1", HBEP="50", speed="2900",
                efficiency="80", suction="单吸", stages="1",
            ))
            has_context = (
                result.evaluation_status == "OUT_OF_STANDARD_SCOPE"
                and result.matched_rule_id is None
                and {"pump.actual_efficiency", "pump.specific_speed", "pump.output_power"}
                    <= set(result.metrics_by_id)
            )
            range_miss[profile] = has_context
            if not has_context:
                errors.append(f"{profile}范围外终止时未保留正式输入派生指标")
        checks["pump_range_miss_context"] = range_miss
    except Exception as exc:  # pragma: no cover - release audit must report a JSON diagnostic
        errors.append(f"正式泵服务烟测异常: {type(exc).__name__}: {exc}")


def _audit_workbooks(
    errors: list[str],
    warnings: list[str],
    checks: dict[str, Any],
    template: Path,
) -> None:
    """核验当前 V6.2 产品模板，同时确认旧 V6 泵模板仍可读取。"""

    if not template.is_file():
        errors.append(f"当前V6.2模板不存在: {template}")
        return
    identity_keys = (
        "template_id", "template_version", "template_kind",
        "template_contract_revision", "filename", "asset_sha256",
    )
    try:
        result = V62MotorTemplateResource().validate(template)
        checks["template"] = asdict(result)
        checks["template_identity"] = V62_TEMPLATE_IDENTITY
        if not result.is_valid:
            errors.append("当前V6.2模板身份或泵/变压器/电机契约校验失败")
        if any(result.identity.get(key) != V62_TEMPLATE_IDENTITY.get(key)
               for key in identity_keys):
            errors.append("当前模板身份不是清单登记的V6.2产品版本")

        unified = UnifiedWorkbookReader().read(template)
        checks["template_unified_sheets"] = sorted(unified.sheets)
        if not {"离心泵", "变压器", "电动机"}.issubset(unified.sheets):
            errors.append("V6.2统一Reader未识别离心泵、变压器与电动机工作表")
        pump_workbook = V6PumpWorkbookReader().read(template)
        checks["template_empty_pump_rows"] = len(pump_workbook.rows)
        if pump_workbook.rows:
            errors.append("V6.2空白模板的离心泵输入区不应预载数据行")
    except Exception as exc:
        errors.append(f"当前V6.2模板检查异常: {type(exc).__name__}: {exc}")

    legacy_v61 = V61TransformerTemplateResource()
    legacy_validation = legacy_v61.validate()
    checks["legacy_v61_transformer_template"] = asdict(legacy_validation)
    if not legacy_validation.is_valid:
        errors.append("旧V6.1变压器模板契约校验失败")

    # The previously published pump-only workbook remains a readable input.
    # Keep this check separate from the current mixed-device template contract.
    try:
        legacy_resource = V6TemplateResource()
        legacy_result = legacy_resource.validate()
        legacy_workbook = V6PumpWorkbookReader().read(legacy_resource.template_path)
        checks["legacy_v6_pump_template"] = {
            "identity": legacy_result.identity,
            "is_valid": legacy_result.is_valid,
            "empty_pump_rows": len(legacy_workbook.rows),
        }
        if (
            not legacy_result.is_valid
            or any(legacy_result.identity.get(key) != V6_TEMPLATE_IDENTITY.get(key)
                   for key in identity_keys)
        ):
            errors.append("旧V6泵模板身份或原有契约校验失败")
        if legacy_workbook.rows:
            errors.append("旧V6空白泵模板的输入区不应预载数据行")
    except Exception as exc:
        errors.append(f"旧V6泵模板兼容检查异常: {type(exc).__name__}: {exc}")


def _audit_transformer_pack(errors: list[str], checks: dict[str, Any]) -> None:
    """验证已派生GB20052包、运行时服务和一个可追溯计算样例。"""

    try:
        pack, digest = load_transformer_pack()
        tables = pack.get("tables", [])
        threshold_rows = [row for table in tables for row in table.get("rows", [])]
        threshold_values = sum(
            1
            for row in threshold_rows
            for grade in (row.get("thresholds_w") or {}).values()
            for value in grade.values()
            if value is not None
        )
        counts = {
            "tables": len(tables),
            "threshold_rows": len(threshold_rows),
            "threshold_values": threshold_values,
        }
        checks["transformer_pack"] = {
            "pack_id": pack.get("pack_id"),
            "standard_code": pack.get("standard_code"),
            "mapping_revision": pack.get("mapping_revision"),
            "counts": counts,
            "sha256": digest,
        }
        if (
            pack.get("pack_id") != "GB20052-2024-TRANSFORMER-V2.1"
            or pack.get("standard_code") != "GB 20052-2024"
            or pack.get("mapping_revision") != "V2.1"
            or counts != {"tables": 35, "threshold_rows": 589, "threshold_values": 3534}
            or pack.get("counts") != counts
        ):
            errors.append("GB20052变压器标准包身份、V2.1版本或35表阈值计数不匹配")

        from equipeffi.composition import create_transformer_analysis_service

        service = create_transformer_analysis_service(with_persistence=False)
        overview = service.standard_overview()
        category_id = "GB20052-T03"
        result = service.evaluate(TransformerAnalysisRequest({
            "category_id": category_id,
            "capacity_kva": "3150",
            "no_load_loss_w": "1700",
            "load_loss_w": "20700",
        }))
        checks["transformer_implementation"] = {
            "support_status": overview.get("support_status"),
            "evaluation_status": result.evaluation_status,
            "ui_conclusion": result.ui_conclusion,
            "pack_sha256_matches": result.references.get("canonical_package_hash") == digest,
        }
        if (
            overview.get("support_status") != "SUPPORTED"
            or result.support_status != "SUPPORTED"
            or result.evaluation_status != "SUCCESS"
            or not result.references.get("calculator_version")
            or result.references.get("canonical_package_hash") != digest
        ):
            errors.append("GB20052变压器服务未以SUPPORTED状态完成V2.1可追溯计算")
    except Exception as exc:
        errors.append(f"GB20052变压器标准包/服务烟测异常: {type(exc).__name__}: {exc}")


def _audit_wheel(errors: list[str], warnings: list[str], checks: dict[str, Any], wheel: Path | None, root: Path) -> None:
    """核验wheel含Qt/V6.2与V2.1运行资源，并保留旧V6泵输入兼容。"""

    if wheel is None:
        return
    if not wheel.is_file():
        warnings.append(f"未找到wheel，跳过包内资源审计: {wheel}")
        return
    checks["wheel"] = {"path": str(wheel.resolve()), "sha256": _sha256(wheel)}
    required = {
        "equipeffi/__init__.py",
        "equipeffi/entrypoint.py",
        "equipeffi/composition.py",
        "equipeffi/presentation/qt/app.py",
        "equipeffi/presentation/qt/shell.py",
        "equipeffi/application/services/centrifugal_pump_analysis_service.py",
        "equipeffi/infrastructure/excel/template_resource.py",
        "equipeffi/infrastructure/excel/pump_workbook_reader.py",
        "equipeffi/infrastructure/excel/unified_workbook_reader.py",
        "equipeffi/application/services/transformer_analysis_service.py",
        "equipeffi/domain/devices/transformer/calculator.py",
        "equipeffi/infrastructure/standards/transformer_repository.py",
        "equipeffi/standard_manifest.json",
        f"equipeffi/resources/templates/{DEFAULT_V62_TEMPLATE}",
        f"equipeffi/resources/templates/{DEFAULT_V61_TEMPLATE}",
        f"equipeffi/resources/templates/{DEFAULT_V6_TEMPLATE}",
        "equipeffi/resources/standards/pump.json",
        "equipeffi/resources/standards/gb20052_2024_v21.json",
        "equipeffi/resources/TEMPLATE_MANIFEST.json",
    }
    try:
        with ZipFile(wheel) as archive:
            names = set(archive.namelist())
            missing = sorted(required - names)
            checks["wheel_member_count"] = len(names)
            checks["wheel_missing_members"] = missing
            if missing:
                errors.append("wheel缺少当前Qt/V6.2、变压器V2.1或旧V6泵运行文件: " + ", ".join(missing))
            if any(name.endswith(".xlsx") and "V4" in name for name in names):
                errors.append("wheel包含已退役的V4模板")
            metadata_members = sorted(
                name for name in names
                if name.endswith(".dist-info/METADATA")
            )
            checks["wheel_metadata_members"] = metadata_members
            metadata = archive.read(metadata_members[0]).decode("utf-8", errors="replace") if metadata_members else ""
            has_desktop_extra = (
                "Provides-Extra: desktop" in metadata
                and "PySide6" in metadata
            )
            checks["wheel_desktop_extra_declared"] = has_desktop_extra
            if not has_desktop_extra:
                errors.append("wheel未声明PySide6 desktop extra")
            try:
                manifest = json.loads(archive.read("equipeffi/standard_manifest.json"))
                pump_packs = {
                    str(item.get("device_type")): str(item.get("pack_id") or "")
                    for item in manifest["packs"]
                    if item.get("device_type") in {"pump_water", "pump_chemical"}
                }
                checks["wheel_pump_pack_ids"] = pump_packs
                if set(pump_packs) != {"pump_water", "pump_chemical"} or any(
                    not pack_id for pack_id in pump_packs.values()
                ):
                    errors.append("wheel标准manifest缺少正式清水泵/石化泵资源身份")
            except (KeyError, json.JSONDecodeError, TypeError) as exc:
                errors.append(f"wheel中的标准manifest无效: {exc}")
    except (OSError, BadZipFile) as exc:
        errors.append(f"wheel不是有效压缩包: {exc}")
    asset_audit = audit_artifact(wheel, root=root)
    checks["wheel_distribution_asset_audit"] = asdict(asset_audit)
    if not asset_audit.is_valid:
        errors.extend(asset_audit.errors)
    warnings.extend(asset_audit.warnings)

    env = dict(os.environ)
    env.pop("EQUIPEFFI_ENABLE_MOTOR_CANDIDATE", None)
    env.pop("PYTHONPATH", None)
    env["PYTHONPATH"] = str(wheel.resolve())
    env["PYTHONIOENCODING"] = "utf-8"
    headless_code = """
from datetime import date
from equipeffi.application.services.centrifugal_pump_analysis_service import PumpAnalysisRequest
from equipeffi.application.services.transformer_analysis_service import TransformerAnalysisRequest
from equipeffi.composition import create_pump_analysis_service
from equipeffi.composition import create_transformer_analysis_service
from equipeffi.infrastructure.excel.pump_workbook_reader import V6PumpWorkbookReader
from equipeffi.infrastructure.excel.template_resource import V6TemplateResource, V62MotorTemplateResource
from equipeffi.infrastructure.excel.unified_workbook_reader import UnifiedWorkbookReader
from equipeffi.infrastructure.standards.transformer_repository import load_transformer_pack
service = create_pump_analysis_service(with_persistence=False)
scopes = {item['rule_profile']: item for item in service.standard_overview()['scopes']}
assert set(scopes) == {'pump_water', 'pump_chemical'}
assert all(item['support_status'] == 'SUPPORTED' and item['pack_id'] for item in scopes.values())
result = service.evaluate(PumpAnalysisRequest('单级单吸清水离心泵', date.today(), QBEP='100', HBEP='50', speed='2900', efficiency='90', suction='单吸', stages='1'))
assert result.evaluation_status == 'SUCCESS' and result.rule_profile == 'pump_water'
current = V62MotorTemplateResource()
assert current.validate().is_valid and current.identity['template_version'] == 'V6.2'
unified = UnifiedWorkbookReader().read(current.template_path)
assert {'离心泵', '变压器', '电动机'} <= set(unified.sheets)
assert not V6PumpWorkbookReader().read(current.template_path).rows
legacy = V6TemplateResource()
assert legacy.validate().is_valid and legacy.identity['template_version'] == 'V6-20261005'
assert not V6PumpWorkbookReader().read(legacy.template_path).rows
pack, digest = load_transformer_pack()
assert pack['pack_id'] == 'GB20052-2024-TRANSFORMER-V2.1'
assert pack['mapping_revision'] == 'V2.1' and len(pack['tables']) == 35
transformer = create_transformer_analysis_service(with_persistence=False)
result = transformer.evaluate(TransformerAnalysisRequest({'category_id': 'GB20052-T03', 'capacity_kva': '3150', 'no_load_loss_w': '1700', 'load_loss_w': '20700'}))
assert result.support_status == 'SUPPORTED' and result.evaluation_status == 'SUCCESS'
assert result.references['canonical_package_hash'] == digest
from equipeffi.composition import create_motor_analysis_service
from equipeffi.application.services.motor_analysis_service import MotorAnalysisRequest
motor = create_motor_analysis_service(with_persistence=False)
result = motor.evaluate(MotorAnalysisRequest(dict(category_id='three_phase_induction', rated_voltage_kv='0.38', rated_frequency_hz='50', rated_output_power_kw='0.14', poles='4', measured_efficiency_pct='71.43')))
assert result.support_status == 'SUPPORTED' and result.evaluation_status == 'SUCCESS'
assert result.ui_conclusion == '3级'
print('headless-pumps-v6.2-transformer-v2.1-motor-ok')
"""
    try:
        runtime = subprocess.run(
            [sys.executable, "-S", "-c", headless_code],
            cwd=str(wheel.parent),
            env=env,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"wheel headless运行时烟测无法启动: {exc}")
    else:
        checks["wheel_headless_stdout"] = runtime.stdout.strip()
        if runtime.returncode != 0 or runtime.stdout.strip() != "headless-pumps-v6.2-transformer-v2.1-motor-ok":
            errors.append(f"wheel headless泵/V6.2/变压器烟测失败: {runtime.stderr.strip() or runtime.stdout.strip()}")

    try:
        status = subprocess.run(
            [sys.executable, "-m", "equipeffi", "--status"],
            cwd=str(wheel.parent),
            env=env,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
        )
        status_payload = json.loads(status.stdout)
        checks["wheel_status"] = status_payload
        valid_status = (
            set(status_payload) == {"ready", "desktop", "template", "pump_profiles", "transformer", "motor"}
            and status_payload.get("desktop", {}).get("surface") == "PySide6 Qt"
            and status_payload.get("desktop", {}).get("available") is True
            and status_payload.get("template", {}).get("available") is True
            and status_payload.get("template", {}).get("template_id") == V62_TEMPLATE_IDENTITY["template_id"]
            and status_payload.get("template", {}).get("template_version") == V62_TEMPLATE_IDENTITY["template_version"]
            and set(status_payload.get("pump_profiles", {})) == {"pump_water", "pump_chemical"}
            and all(
                item.get("available") is True
                and item.get("support_status") == "SUPPORTED"
                and item.get("pack_id")
                for item in status_payload["pump_profiles"].values()
            )
            and status_payload.get("transformer", {}).get("available") is True
            and status_payload.get("transformer", {}).get("support_status") == "SUPPORTED"
            and status_payload.get("transformer", {}).get("standard_code") == "GB 20052-2024"
            and status_payload.get("motor", {}).get("enabled") is True
            and status_payload.get("motor", {}).get("available") is True
            and status_payload.get("motor", {}).get("support_status") == "SUPPORTED"
            and status_payload.get("ready") is True
            and status.returncode == 0
        )
        if not valid_status:
            errors.append(
                "wheel --status未验证当前Qt/V6.2/变压器SUPPORTED/正式泵profile: "
                + (status.stderr.strip() or json.dumps(status_payload, ensure_ascii=False))
            )
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        errors.append(f"wheel --status运行时烟测失败: {type(exc).__name__}: {exc}")

    try:
        candidate = subprocess.run(
            [sys.executable, "-m", "equipeffi", "--motor-candidate", "--status"],
            cwd=str(wheel.parent), env=env, capture_output=True, text=True,
            encoding="utf-8", timeout=45, check=False)
        payload = json.loads(candidate.stdout)
        checks["wheel_motor_candidate_status"] = payload
        if not (
            candidate.returncode == 0 and payload.get("ready") is True
            and payload.get("template", {}).get("available") is True
            and payload.get("template", {}).get("template_id") == "equipeffi.device-efficiency.V6.2"
            and payload.get("template", {}).get("template_version") == "V6.2"
            and payload.get("motor", {}).get("enabled") is True
            and payload.get("motor", {}).get("available") is True
            and payload.get("motor", {}).get("support_status") == "SUPPORTED"
            and payload.get("motor", {}).get("standard_code") == "GB 18613-2020"
        ):
            errors.append("wheel旧电机命令兼容V6.2/GB18613资源烟测失败：" + candidate.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        errors.append(f"wheel旧电机命令兼容烟测异常: {type(exc).__name__}: {exc}")


def _audit_sdist(sdist: Path | None, root: Path, errors: list[str], warnings: list[str], checks: dict[str, Any]) -> None:
    if sdist is None:
        return
    if not sdist.is_file():
        warnings.append(f"未找到sdist，跳过源码包资产审计: {sdist}")
        return
    asset_audit = audit_artifact(sdist, root=root)
    checks["sdist_distribution_asset_audit"] = asdict(asset_audit)
    if not asset_audit.is_valid:
        errors.extend(asset_audit.errors)
    warnings.extend(asset_audit.warnings)


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


def _audit_native_report(
    report_path: Path,
    errors: list[str],
    warnings: list[str],
    checks: dict[str, Any],
    root: Path,
) -> None:
    """核验可选的PyInstaller构建报告及其可执行文件。"""

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"原生构建报告无法读取: {exc}")
        return
    if not isinstance(report, dict):
        errors.append("原生构建报告必须是JSON对象")
        return
    required = ("platform", "executable", "qt_capable", "presentation_mode", "status_ready")
    missing = [key for key in required if key not in report]
    if missing:
        errors.append("原生构建报告缺少字段: " + ", ".join(missing))
    mode = str(report.get("presentation_mode", ""))
    if mode not in {"pyside6_qt", "unavailable"}:
        errors.append(f"原生构建报告presentation_mode无效: {mode}")
    if not report.get("qt_capable") or mode != "pyside6_qt":
        errors.append("原生桌面包未证明PySide6 Qt可用")
    if not report.get("status_ready"):
        errors.append("原生桌面包--status未验证Qt/V6.2/变压器实现/正式泵服务")
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
        "qt_capable": bool(report.get("qt_capable")),
        "presentation_mode": mode,
        "status_ready": bool(report.get("status_ready")),
        "qt_environment": report.get("qt_environment", {}),
        "sha256": str(report.get("sha256", "")),
    }
    if package_check:
        checks["native_build"]["package"] = package_check
        if package_check.get("path") and Path(str(package_check["path"])).is_file():
            asset_audit = audit_artifact(Path(str(package_check["path"])), root=root)
            checks["native_build"]["package_asset_audit"] = asdict(asset_audit)
            if not asset_audit.is_valid:
                errors.extend(asset_audit.errors)
            warnings.extend(asset_audit.warnings)


def _audit_portable_bundle(bundle_path: Path, errors: list[str], warnings: list[str], checks: dict[str, Any], root: Path) -> None:
    """校验便携ZIP清单和成员哈希。"""

    try:
        from .validate_portable_bundle import validate
    except ImportError:  # direct execution
        from validate_portable_bundle import validate
    result = validate(Path(bundle_path))
    checks["portable_bundle"] = result
    if not result.get("is_valid"):
        errors.append("便携ZIP清单/哈希审计失败")
    asset_audit = audit_artifact(bundle_path, root=root)
    checks["portable_distribution_asset_audit"] = asdict(asset_audit)
    if not asset_audit.is_valid:
        errors.extend(asset_audit.errors)
    warnings.extend(asset_audit.warnings)


def audit_project(
    root: Path = ROOT,
    *,
    template: Path | None = None,
    wheel: Path | None = None,
    sdist: Path | None = None,
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
    _audit_manifest(source_root, errors, checks)
    _audit_pmsm_confirmed_no_data(source_root, errors, checks)
    _audit_hvac_boundaries(source_root, errors, checks)
    _audit_standard_provenance(source_root, warnings, checks, standard_source_dir)
    _audit_elimination_catalog(errors, checks)
    _audit_evaluator_examples(source_root, errors, checks)
    template_path = (
        Path(template)
        if template
        else source_root / "equipeffi" / "resources" / "templates" / DEFAULT_V62_TEMPLATE
    )
    _audit_workbooks(errors, warnings, checks, template_path)
    _audit_transformer_pack(errors, checks)
    _audit_wheel(errors, warnings, checks, Path(wheel) if wheel else None, root)
    _audit_sdist(Path(sdist) if sdist else None, root, errors, warnings, checks)
    if elimination_source_dir is not None:
        _audit_elimination_sources(Path(elimination_source_dir), errors, checks)
    if industry_source_pdf is not None:
        _audit_industry_source(Path(industry_source_pdf), errors, checks)
    if native_report is not None:
        _audit_native_report(Path(native_report), errors, warnings, checks, root)
    if portable_bundle is not None:
        _audit_portable_bundle(Path(portable_bundle), errors, warnings, checks, root)
    return ReleaseAudit(not errors, tuple(errors), tuple(warnings), checks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="审计EquipEffi项目发布状态")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--sdist", type=Path, help="可选：检查源码分发包中的实际成员")
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
        "sdist": args.sdist,
        "elimination_source_dir": args.elimination_source_dir,
        "industry_source_pdf": args.industry_source_pdf,
        "standard_source_dir": args.standard_source_dir,
        "native_report": args.native_report,
        "portable_bundle": args.portable_bundle,
    }
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
