"""Phase 8 模板一致性检查：Workbook 配置 ↔ Application 已确认输入契约。

Owner 规则（Phase 8 权威层级）要求：不得让误改 Excel 配置自动改变正式业务算法，
必须建立 Workbook 配置 / Validation / Protection ↔ Application 输入契约的
**机械一致性检查**，发现不一致则 Gate 失败。

**不得靠复制同一规则到更多 Python 常量来"解决"**：本模块的业务期望值一律
从正式 Application 契约读取（类别枚举、字段约束、必填规则），只把
"Excel 结构"事实写在检查逻辑里。

检查维度
--------
A. 模板资产身份（SHA-256 / Sheet 集合 / Sheet 顺序）
B. `离心泵` Sheet 结构契约（27 列、列头、TblPump 范围、保护、editable/locked）
C. 类别枚举与 Application 逐项一致（含 `其他类别` / `不确定类别`）
D. 吸入方式 / 级数验证与 Application 的类别字段约束一致
E. 数量验证为"正整数 > 0"
F. 正式空白模板内**不存在**可独立产出业务结果的第二套 Excel 算法
G. 其他设备 Sheet 语义不变（对基线快照比对）
H. manifest 输入 field_id / unit 与 Application 元数据一致；
   输出 metric_key / unit 与稳定结果指标契约一致

用法::

    python tools/check_v6_pump_template.py            # 打印结论
    python tools/check_v6_pump_template.py --json out.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
from equipeffi.domain.evaluation.device_types import PUBLIC_DEVICE_NAMES
from equipeffi.application.result_projection import (
    PUMP_METRIC_IDS,
    PUMP_RESULT_METRIC_DEFINITIONS,
)
from equipeffi.infrastructure.excel.template_resource import (
    V6_TEMPLATE_ENTRY,
    V6_TEMPLATE_IDENTITY,
    V6TemplateResource,
    pump_header_issues,
)

TEMPLATE = (REPO_ROOT / "src" / "equipeffi" / "resources" / "templates"
            / V6_TEMPLATE_IDENTITY["filename"])
MANIFEST = REPO_ROOT / "src" / "equipeffi" / "resources" / "TEMPLATE_MANIFEST.json"
PUMP_CONTRACT = next(sheet for sheet in V6_TEMPLATE_ENTRY["sheets"]
                     if sheet["sheet_id"] == "centrifugal_pump")
PUMP_SHEET = PUMP_CONTRACT["sheet_name"]
CONFIG_SHEET = next(sheet["sheet_name"] for sheet in V6_TEMPLATE_ENTRY["sheets"]
                    if sheet["sheet_id"] == "configuration")
CONFIGURATION_CONTRACT = V6_TEMPLATE_ENTRY["configuration_contract"]
TABLE_NAME = PUMP_CONTRACT["table"]["name"]
FIRST_DATA_ROW = int(PUMP_CONTRACT["header_row"]) + 1
LAST_DATA_ROW = int(re.search(r"\d+$", PUMP_CONTRACT["table"]["ref"]).group())
EXPECTED_COLUMNS = len(PUMP_CONTRACT["fields"])
CATEGORY_COLUMN = CONFIGURATION_CONTRACT["pump_category_enum"]["column"]
CATEGORY_FIRST_ROW = int(CONFIGURATION_CONTRACT["pump_category_enum"]["first_row"])
EXPECTED_SHEETS = tuple(sheet["sheet_name"] for sheet in V6_TEMPLATE_ENTRY["sheets"])

#: 结果列：本阶段必须**不含业务公式**，由软件批量评价后写入。
BUSINESS_FORMULA_COLUMNS: tuple[str, ...] = tuple(
    field["column"] for field in PUMP_CONTRACT["fields"]
    if field.get("clear_template_formula"))

#: 结果列（列头保留，值由软件写入）——用于"结果列仍存在"的检查。
RESULT_HEADERS: dict[str, str] = {
    field["column"]: field["label"] for field in PUMP_CONTRACT["fields"]
    if field.get("role") == "result"
}

#: 可由用户编辑的输入列（`Y` 为图片、`Z` 为文本，见列头契约）。
EDITABLE_COLUMNS: tuple[str, ...] = tuple(
    field["column"] for field in PUMP_CONTRACT["fields"]
    if field.get("role") == "input")
#: 结果列（软件写入，锁定）。注意 `K`（单吸/双吸）与 `L`（级数）是**用户输入**列：
#: 它们不再由 Excel 公式推导，因此必须保持可编辑，不属于锁定列。
LOCKED_COLUMNS: tuple[str, ...] = ("A",) + tuple(
    field["column"] for field in PUMP_CONTRACT["fields"]
    if field.get("role") == "result")

#: 业务算法特征：出现这些即视为"模板内存在第二套 GB19762 业务算法"。
BUSINESS_ALGORITHM_MARKERS: tuple[str, ...] = (
    "163.33", "168.33",          # C2 / C3 系数
    "9.81*", "9.81 *",           # 功率合理性
    "ns", "比转速",
    "TEXTJOIN",                  # 旧"自动备注"结论拼装
)

#: 允许保留的非业务便利公式（不形成评价真值）。
ALLOWED_FORMULA_SHEETS: tuple[str, ...] = ()


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class Report:
    template: str
    sha256: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.results)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append(CheckResult(name, passed, detail))

    def as_dict(self) -> dict:
        return {
            "template": self.template,
            "sha256": self.sha256,
            "passed": self.passed,
            "failed": [r.as_dict() for r in self.results if not r.passed],
            "checks": [r.as_dict() for r in self.results],
        }


def _application_contract():
    from equipeffi.application.services.centrifugal_pump_analysis_service import (
        CATEGORY_FIELD_CONSTRAINTS,
        LOCKABLE_FIELDS,
        PUMP_CATEGORIES,
        category_field_constraints,
    )

    return {
        "categories": tuple(item.visible_name for item in PUMP_CATEGORIES),
        "formal_categories": tuple(item.visible_name for item in PUMP_CATEGORIES
                                   if item.special is None),
        "special_categories": tuple(item.visible_name for item in PUMP_CATEGORIES
                                    if item.special is not None),
        "constraints": CATEGORY_FIELD_CONSTRAINTS,
        "lockable": LOCKABLE_FIELDS,
        "resolver": category_field_constraints,
    }


def input_field_application_issues(fields) -> tuple[str, ...]:
    """校验 manifest 输入字段 ID / 单位与正式离心泵 Application 元数据一致。"""

    from equipeffi.domain.evaluation.metadata import get_device_profile

    profile = get_device_profile("centrifugal_pump")
    application_fields = {
        str(field.v4_field_id): field
        for field in profile.input_fields
        if field.v4_field_id
    }
    input_fields = [field for field in fields if field.get("role") == "input"]
    field_ids = [str(field.get("field_id") or "").strip()
                 for field in input_fields]
    issues: list[str] = []
    duplicates = sorted({field_id for field_id in field_ids
                         if field_id and field_ids.count(field_id) > 1})
    if duplicates:
        issues.append(f"重复 field_id={duplicates}")

    expected_ids = set(application_fields)
    actual_ids = set(field_ids)
    if actual_ids != expected_ids:
        issues.append(
            f"field_id 不一致：缺少={sorted(expected_ids - actual_ids)}；"
            f"未知={sorted(actual_ids - expected_ids)}")

    for field in input_fields:
        field_id = str(field.get("field_id") or "").strip()
        application_field = application_fields.get(field_id)
        if application_field is None:
            continue
        actual_unit = str(field.get("unit") or "-").strip()
        expected_unit = str(application_field.unit or "-").strip()
        if actual_unit != expected_unit:
            issues.append(
                f"{field.get('column')}:{field_id} unit {actual_unit!r} "
                f"!= Application {expected_unit!r}")
    return tuple(issues)


def _config_category_values(workbook) -> tuple[str, ...]:
    config = workbook[CONFIG_SHEET]
    values: list[str] = []
    for row in range(CATEGORY_FIRST_ROW, config.max_row + 1):
        value = config[f"{CATEGORY_COLUMN}{row}"].value
        if value in (None, ""):
            break
        values.append(str(value).strip())
    return tuple(values)


def _validations(sheet) -> dict[str, list]:
    found: dict[str, list] = {}
    for validation in sheet.data_validations.dataValidation:
        for ref in str(validation.sqref).split():
            match = re.match(r"^([A-Z]+)(\d+)", ref)
            if match:
                found.setdefault(match.group(1), []).append(validation)
    return found


def run_checks(template: Path = TEMPLATE) -> Report:
    template = Path(template)
    report = Report(template=str(template),
                    sha256=hashlib.sha256(template.read_bytes()).hexdigest().upper())
    if not template.exists():
        report.add("template_exists", False, f"模板资产不存在：{template}")
        return report
    report.add("template_exists", True, template.name)

    contract = _application_contract()
    workbook = openpyxl.load_workbook(template, data_only=False)

    # --- A. 资产身份 -------------------------------------------------------
    # 资产 hash 只用于检查空白发布资产；Reader 对用户填写后的 Workbook
    # 按声明身份/legacy 结构和字段/单位契约校验，不拿填写后文件 hash 与空白资产比较。
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        entry = next((t for t in manifest["templates"]
                      if t.get("template_id") == manifest.get("formal_windows_v1_template")
                      and t.get("status") == "FORMAL"), None)
        report.add("manifest_formal_entry_present", entry is not None)
        if entry is not None:
            report.add("manifest_asset_sha_matches_file",
                       entry.get("asset_sha256") == report.sha256,
                       f"清单 {entry.get('asset_sha256')} vs 资产 {report.sha256}")
            report.add("manifest_filename_matches",
                       entry.get("filename") == template.name,
                       f"{entry.get('filename')} vs {template.name}")
            report.add("manifest_asset_size_matches",
                       entry.get("asset_size_bytes") == template.stat().st_size,
                       f"{entry.get('asset_size_bytes')} vs {template.stat().st_size}")
            manifest_sheets = tuple(sheet["sheet_name"] for sheet in entry.get("sheets", ()))
            report.add("manifest_sheet_order_matches",
                       manifest_sheets == EXPECTED_SHEETS,
                       "清单 Sheet 顺序与模板契约一致")
            report.add("manifest_declares_authorized_sheet",
                       (entry.get("authorized_modification") or {}).get("sheet") == PUMP_SHEET)
            sheet_ids = [sheet.get("sheet_id") for sheet in entry.get("sheets", ())]
            report.add("manifest_sheet_machine_ids_unique",
                       len(sheet_ids) == len(set(sheet_ids)) and all(sheet_ids),
                       f"{len(sheet_ids)} 个 Sheet 契约")
            device_contracts = {
                sheet["sheet_id"]: sheet["sheet_name"]
                for sheet in entry.get("sheets", ())
                if sheet.get("sheet_id") in PUBLIC_DEVICE_NAMES
            }
            report.add("manifest_device_sheet_ids_match_application",
                       device_contracts == PUBLIC_DEVICE_NAMES,
                       f"清单 {len(device_contracts)} 个设备 Sheet / Application "
                       f"{len(PUBLIC_DEVICE_NAMES)} 个正式类型")
            input_issues = input_field_application_issues(
                PUMP_CONTRACT["fields"])
            report.add(
                "manifest_input_field_ids_and_units_match_application",
                not input_issues,
                "; ".join(input_issues) or
                f"{sum(field.get('role') == 'input' for field in PUMP_CONTRACT['fields'])} "
                "个输入字段 ID / 单位均匹配 Application 元数据")

            metric_definitions = {
                item.metric_id: item for item in PUMP_RESULT_METRIC_DEFINITIONS
            }
            metric_fields = [field for field in PUMP_CONTRACT["fields"]
                             if field.get("role") == "result"
                             and field.get("metric_key")]
            metric_keys = [str(field["metric_key"]) for field in metric_fields]
            unknown_keys = sorted(set(metric_keys) - set(PUMP_METRIC_IDS))
            metric_ids = [PUMP_METRIC_IDS[key] for key in metric_keys
                          if key in PUMP_METRIC_IDS]
            unit_mismatches: list[str] = []
            for field in metric_fields:
                key = str(field["metric_key"])
                if key not in PUMP_METRIC_IDS:
                    continue
                metric_id = PUMP_METRIC_IDS[key]
                definition = metric_definitions.get(metric_id)
                expected_unit = definition.unit if definition is not None else "<missing>"
                if definition is None or field.get("metric_unit") != expected_unit:
                    unit_mismatches.append(
                        f"{field['column']}:{field.get('metric_unit')!r} != "
                        f"{expected_unit!r}")
            incomplete_metrics = [
                field["column"] for field in PUMP_CONTRACT["fields"]
                if field.get("role") == "result"
                and bool(field.get("metric_key")) != bool(field.get("metric_unit"))
            ]
            metric_mapping_valid = (
                bool(metric_fields)
                and not unknown_keys
                and len(metric_keys) == len(set(metric_keys))
                and len(metric_ids) == len(set(metric_ids))
                and not unit_mismatches
                and not incomplete_metrics
            )
            report.add(
                "manifest_result_metric_projection_matches_application",
                metric_mapping_valid,
                f"unknown keys={unknown_keys}; unit mismatches={unit_mismatches}; "
                f"incomplete fields={incomplete_metrics}")
    else:
        report.add("manifest_present", False, str(MANIFEST))

    resource_validation = V6TemplateResource().validate(template)
    report.add("runtime_template_identity_and_structure_valid",
               resource_validation.is_valid, resource_validation.message)
    report.add("legacy_identity_uses_strict_structure_path",
               resource_validation.identity_source == "legacy-structure",
               resource_validation.identity_source)
    report.add("sheet_order_matches_manifest",
               tuple(workbook.sheetnames) == EXPECTED_SHEETS,
               f"实际 {len(workbook.sheetnames)} 个 Sheet")
    report.add("pump_sheet_present", PUMP_SHEET in workbook.sheetnames)

    sheet = workbook[PUMP_SHEET]

    # --- B. 结构契约 -------------------------------------------------------
    table = sheet.tables.get(TABLE_NAME)
    report.add("pump_table_present", table is not None, TABLE_NAME)
    if table is not None:
        expected_ref = PUMP_CONTRACT["table"]["ref"]
        report.add("pump_table_ref", table.ref == expected_ref,
                   f"{table.ref}（期望 {expected_ref}）")
        report.add("pump_table_columns", len(table.tableColumns) == EXPECTED_COLUMNS,
                   f"{len(table.tableColumns)} 列")
    report.add("pump_sheet_protected", bool(sheet.protection.sheet))
    report.add("config_sheet_protected", bool(workbook[CONFIG_SHEET].protection.sheet))

    header_row = int(PUMP_CONTRACT["header_row"])
    header = [sheet.cell(header_row, column).value
              for column in range(1, EXPECTED_COLUMNS + 1)]
    header_mismatch = pump_header_issues(header, PUMP_CONTRACT)
    report.add("pump_header_labels_and_units_match_manifest",
               not header_mismatch, "；".join(header_mismatch))
    result_headers_present = all(
        str(sheet[f"{column}{header_row}"].value or "").split("\n", 1)[0].strip()
        == expected
        for column, expected in RESULT_HEADERS.items())
    report.add("result_columns_kept", result_headers_present)

    lock_mismatch: list[str] = []
    for column in LOCKED_COLUMNS:
        cell = sheet[f"{column}{FIRST_DATA_ROW}"]
        if not (cell.protection and cell.protection.locked):
            lock_mismatch.append(f"{column} 未锁定")
    for column in EDITABLE_COLUMNS:
        cell = sheet[f"{column}{FIRST_DATA_ROW}"]
        if cell.protection and cell.protection.locked:
            lock_mismatch.append(f"{column} 不应锁定")
    report.add("column_lock_contract", not lock_mismatch, "；".join(lock_mismatch))

    # --- C. 类别枚举 -------------------------------------------------------
    excel_categories = _config_category_values(workbook)
    report.add("category_enum_matches_application",
               excel_categories == contract["categories"],
               f"Excel {len(excel_categories)} 项 vs Application {len(contract['categories'])} 项")
    report.add("category_enum_has_other_label",
               "其他类别" in excel_categories and "其他（请备注说明）" not in excel_categories,
               "「其他类别」已就位且旧文案已退出")
    report.add("category_enum_has_uncertain",
               "不确定类别" in excel_categories)
    category_defined_name = CONFIGURATION_CONTRACT["pump_category_enum"]["defined_name"]
    defined = workbook.defined_names.get(category_defined_name)
    last_category_row = CATEGORY_FIRST_ROW + len(contract["categories"]) - 1
    expected_range = (f"'{CONFIG_SHEET}'!${CATEGORY_COLUMN}${CATEGORY_FIRST_ROW}"
                      f":${CATEGORY_COLUMN}${last_category_row}")
    report.add("category_named_range",
               defined is not None and str(defined.value) == expected_range,
               f"{defined.value if defined else None}（期望 {expected_range}）")
    category_dv = _validations(sheet).get("F", [])
    report.add("category_validation_points_at_enum",
               any(category_defined_name in str(dv.formula1) for dv in category_dv),
               f"{len(category_dv)} 条验证")

    # --- D. 吸入方式 / 级数约束与 Application 一致 -------------------------
    suction_dv = _validations(sheet).get("K", [])
    suction_formula = " ".join(str(dv.formula1) for dv in suction_dv)
    # 石化的单级/多级不代表吸入方式 → 不得出现"由石化类别推导单吸"的规则
    chemical_lock_violation = [
        name for name in contract["categories"]
        if "石油化工" in name and contract["resolver"](name).get("suction")
    ]
    report.add("chemical_suction_not_category_locked", not chemical_lock_violation,
               "；".join(chemical_lock_violation))
    report.add("suction_validation_is_enum",
               "EV_SUCTION" in suction_formula,
               suction_formula[:120])
    report.add("suction_validation_has_no_category_offset",
               "OFFSET" not in suction_formula,
               "吸入方式不再由类别推导")

    stage_dv = _validations(sheet).get("L", [])
    stage_formula = " ".join(str(dv.formula1) for dv in stage_dv)
    report.add("stage_validation_present", bool(stage_dv), f"{len(stage_dv)} 条")
    for name, constraint in contract["constraints"].items():
        if constraint.get("stages") == "1":
            if name not in stage_formula:
                report.add(f"stage_rule_documents_{name}", False, "未在验证公式中出现")
    single_stage_names = [n for n, c in contract["constraints"].items()
                          if c.get("stages") == "1"]
    report.add("stage_validation_covers_single_stage_categories",
               all(n in stage_formula for n in single_stage_names),
               f"{len(single_stage_names)} 个单级类别")

    # --- E. 数量验证 -------------------------------------------------------
    quantity_dv = _validations(sheet).get("D", [])
    quantity_ok = any(dv.type == "whole" and str(dv.operator) == "greaterThan"
                      and str(dv.formula1) == "0" and not dv.allowBlank is False
                      for dv in quantity_dv)
    report.add("quantity_is_positive_integer", quantity_ok,
               "；".join(f"{dv.type}/{dv.operator}/{dv.formula1}" for dv in quantity_dv))

    # --- F. 空白模板不得含第二套业务算法 -----------------------------------
    offenders: list[str] = []
    for column in BUSINESS_FORMULA_COLUMNS:
        for row in range(FIRST_DATA_ROW, LAST_DATA_ROW + 1):
            value = sheet[f"{column}{row}"].value
            if value not in (None, ""):
                offenders.append(f"{column}{row}={str(value)[:40]}")
                if len(offenders) >= 5:
                    break
        if len(offenders) >= 5:
            break
    report.add("pump_business_formula_columns_empty", not offenders,
               "；".join(offenders))

    marker_hits: list[str] = []
    for row in sheet.iter_rows():
        for cell in row:
            value = cell.value
            if isinstance(value, str) and value.startswith("="):
                for marker in BUSINESS_ALGORITHM_MARKERS:
                    if marker in value:
                        marker_hits.append(f"{cell.coordinate}:{marker}")
                        break
    report.add("pump_sheet_has_no_business_algorithm_formula",
               not marker_hits, "；".join(marker_hits[:5]))

    # 全簿扫描：其他 Sheet 允许保留自身算法（本阶段未接通），
    # 因此只对「离心泵」Sheet 断言；同时确认没有跨表引用离心泵结果列。
    cross_refs: list[str] = []
    for name in workbook.sheetnames:
        if name == PUMP_SHEET:
            continue
        for row in workbook[name].iter_rows():
            for cell in row:
                value = cell.value
                if isinstance(value, str) and value.startswith("=") and PUMP_SHEET in value:
                    cross_refs.append(f"{name}!{cell.coordinate}")
    report.add("no_cross_sheet_reference_to_pump", not cross_refs,
               "；".join(cross_refs[:5]))

    # --- G. FieldDictionary 仍可机械读取 -----------------------------------
    config = workbook[CONFIG_SHEET]
    dictionary_name = CONFIGURATION_CONTRACT["field_dictionary_table"]
    dictionary = config.tables.get(dictionary_name)
    report.add("field_dictionary_present", dictionary is not None, dictionary_name)
    if dictionary is not None:
        pump_rows = 0
        for row in range(2, config.max_row + 1):
            if str(config.cell(row, 1).value or "").strip() == PUMP_SHEET:
                pump_rows += 1
        report.add("field_dictionary_covers_pump", pump_rows == EXPECTED_COLUMNS,
                   f"{pump_rows} 行（期望 {EXPECTED_COLUMNS}）")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run_checks(args.template)
    for item in report.results:
        mark = "PASS" if item.passed else "FAIL"
        line = f"  [{mark}] {item.name}"
        if item.detail and not item.passed:
            line += f"  -> {item.detail}"
        print(line)
    print()
    print(f"template: {report.template}")
    print(f"sha256  : {report.sha256}")
    print("GATE    : " + ("PASS" if report.passed else "FAIL"))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report.as_dict(), ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
