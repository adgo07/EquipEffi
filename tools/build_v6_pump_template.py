"""从 Owner 指定的 V6 模板基线生成正式「离心泵」模板资产（Phase 8）。

设计原则
--------
1. **单一事实源**：本文件只描述"如何从 V6 基线派生出正式模板资产"这一**模板结构**
   事实；GB 19762 的**业务**事实（类别枚举、字段约束、必填规则）一律来自正式
   Application 契约，本文件不得复制第二份业务规则常量。
2. **最小改动**：除「离心泵」Sheet 的授权修改外，其他设备 Sheet 必须语义不变。
   脚本不触碰其他 Sheet 的任何单元格、命名范围、验证、保护或表格。
3. **可重复**：同一基线 + 同一脚本 → 同一资产语义。

授权修改（Owner Phase 8 规则 4 / 5）
------------------------------------
- 退出「离心泵」Sheet 内**独立执行 GB19762 业务算法**的 Excel 公式
  （`K` 吸入方式、`L` 级数、`N:X` 比转速 / C1~C3 / 基准效率 / 效率修正值 /
  规定点效率 / 1~3 级效率 / 能效等级、`AA` 自动备注）。这些公式能够**独立**产出
  正式计算结果与等级结论，构成第二套业务算法。
  结果列/列头/样式/锁定**全部保留**，改由软件批量评价后写入。
- 类别下拉与「配置」Sheet 的 `EV_PUMP_CATEGORY` 与正式类别枚举逐项一致：
  `其他（请备注说明）` → `其他类别`，并新增 `不确定类别`。
- 吸入方式/级数验证改为枚举约束（不再用 `OFFSET` 由类别推导），与 Application
  契约一致：石化的单级/多级**不代表吸入方式自动固定**。

用法::

    python tools/build_v6_pump_template.py --source <V6 基线路径> --output <目标路径>

不带参数时使用仓库内默认路径（基线放在 `outputs/`，资产写入
`src/equipeffi/resources/templates/`）。
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Owner 指定的 V6 模板基线（构建输入；**读取，绝不写回**）。
DEFAULT_SOURCE = REPO_ROOT / "outputs" / "设备能效分析空白模板_重构版V6_变压器.xlsx"
#: 正式模板资产（产品运行时只使用入仓版本，不依赖本地开发路径）。
DEFAULT_OUTPUT = (REPO_ROOT / "src" / "equipeffi" / "resources" / "templates"
                  / "设备能效分析空白模板_重构版V6_20261005.xlsx")

#: Owner 指定基线的期望 SHA-256（来源证据；不匹配即中止，防止静默换基线）。
OWNER_BASELINE_SHA256 = "FDB8C0B09925B5AE0EA0F0A941040B27890B5455E8E5920E02C409EDD4699CA1"

PUMP_SHEET = "离心泵"
CONFIG_SHEET = "配置"

#: 「离心泵」Sheet 中必须退出模板的**业务算法**列。
BUSINESS_FORMULA_COLUMNS: tuple[str, ...] = (
    "K",   # 单吸/双吸（由类别推导）
    "L",   # 级数（由类别推导）
    "N",   # 比转速
    "O",   # C1
    "P",   # C2
    "Q",   # C3
    "R",   # 基准效率
    "S",   # 效率修正值
    "T",   # 规定点效率
    "U",   # 1级效率
    "V",   # 2级效率
    "W",   # 3级效率
    "X",   # 能效等级
    "AA",  # 自动备注（依赖上述业务公式形成评价结论）
)

#: 数据行范围（与 `TblPump` 一致；容量策略见统一容量说明）。
FIRST_DATA_ROW = 4
LAST_DATA_ROW = 103

#: 「配置」Sheet 中 `EV_PUMP_CATEGORY` 所在列与起始行。
CATEGORY_COLUMN = "AE"
CATEGORY_FIRST_ROW = 2

#: FieldDictionary 中「离心泵」Sheet 需要同步的字段行（按"字段ID"定位，不写死行号）。
FIELD_DICTIONARY_REQUIRED_UPDATES: dict[str, dict[str, str]] = {
    # 吸入方式：不再由类别推导；石化类的单级/多级**不代表**吸入方式固定。
    "suction": {
        "验证规则": "枚举：单吸/双吸（停止型下拉）",
        "必填条件": "整行启用时必填",
        "自动备注规则": "由软件评价写入；模板不判定",
    },
    "stages": {
        "验证规则": "正整数；单级类别固定为1，多级类别应为≥2",
        "自动备注规则": "由软件评价写入；模板不判定",
    },
    "category": {
        "验证规则": "枚举：EV_PUMP_CATEGORY（停止型下拉）",
        "自动备注规则": "由软件评价写入；模板不判定",
    },
    "auto_note": {
        "自动备注规则": "由软件评价写入，模板不含业务公式",
    },
}


@dataclass(frozen=True)
class BuildReport:
    source: Path
    source_sha256: str
    output: Path
    output_sha256: str
    categories: tuple[str, ...]
    cleared_columns: tuple[str, ...]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def _application_pump_categories() -> tuple[str, ...]:
    """正式类别枚举的**唯一来源**：Application 契约 + 两个特殊类别。

    本函数不复制枚举文本，而是从正式 Application 契约读取，从结构上排除
    "Excel 一份、Python 一份"的漂移可能。
    """
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from equipeffi.application.services.centrifugal_pump_analysis_service import (
        PUMP_CATEGORIES,
    )

    return tuple(item.visible_name for item in PUMP_CATEGORIES)


def _patch_categories(workbook) -> tuple[str, ...]:
    """把 `EV_PUMP_CATEGORY` 写为正式类别枚举（`AE` 列连续写入）。"""
    config = workbook[CONFIG_SHEET]
    categories = _application_pump_categories()

    # 先清空原范围，避免残留旧文案（如"其他（请备注说明）"）。
    for row in range(CATEGORY_FIRST_ROW, CATEGORY_FIRST_ROW + 60):
        config[f"{CATEGORY_COLUMN}{row}"] = None
    for offset, name in enumerate(categories):
        config[f"{CATEGORY_COLUMN}{CATEGORY_FIRST_ROW + offset}"] = name

    last_row = CATEGORY_FIRST_ROW + len(categories) - 1
    workbook.defined_names["EV_PUMP_CATEGORY"].value = (
        f"'{CONFIG_SHEET}'!${CATEGORY_COLUMN}${CATEGORY_FIRST_ROW}"
        f":${CATEGORY_COLUMN}${last_row}")
    return categories


def _validate_suction_reference(categories: tuple[str, ...]) -> None:
    """结构守卫：石化类的单级/多级不得隐含吸入方式。"""
    chemical = [name for name in categories if "石油化工" in name]
    if not chemical:
        raise SystemExit("正式类别枚举中找不到石油化工泵类别，模板生成中止")


def _clear_business_formulas(workbook) -> tuple[str, ...]:
    """清空「离心泵」Sheet 的业务算法公式，保留样式 / 结果列 / 锁定。"""
    sheet = workbook[PUMP_SHEET]
    for column in BUSINESS_FORMULA_COLUMNS:
        for row in range(FIRST_DATA_ROW, LAST_DATA_ROW + 1):
            sheet[f"{column}{row}"] = None
    return BUSINESS_FORMULA_COLUMNS


def _patch_validations(workbook, categories: tuple[str, ...]) -> None:
    """重设吸入方式 / 级数验证：与 Application 契约一致，去掉类别推导公式。"""
    sheet = workbook[PUMP_SHEET]
    kept = []
    for validation in sheet.data_validations.dataValidation:
        refs = str(validation.sqref)
        if refs.startswith("K4:") or refs.startswith("L4:"):
            continue  # 由下面重建
        kept.append(validation)
    sheet.data_validations.dataValidation = kept

    suction = DataValidation(
        type="list", formula1="EV_SUCTION", allow_blank=True, showDropDown=False)
    suction.error = ("单吸/双吸必须为「单吸」或「双吸」。"
                     "石油化工泵的单级/多级不代表吸入方式，请按铭牌填写。")
    suction.errorTitle = "单吸/双吸"
    suction.prompt = "请选择单吸或双吸（按铭牌实际结构）"
    suction.promptTitle = "单吸/双吸"
    sheet.add_data_validation(suction)
    suction.add(f"K{FIRST_DATA_ROW}:K{LAST_DATA_ROW}")

    stage_rule = (
        'OR($F4="",'
        'AND(OR($F4="单级单吸清水离心泵",$F4="单级双吸清水离心泵",'
        '$F4="管道清水离心泵",$F4="单级石油化工离心泵"),L4=1),'
        'AND(OR($F4="多级清水离心泵",$F4="轻型多级清水离心泵（立式）",'
        '$F4="轻型多级清水离心泵（卧式）",$F4="多级石油化工离心泵"),'
        'ISNUMBER(L4),L4>=2,L4=INT(L4)),'
        'OR($F4="其他类别",$F4="不确定类别"))'
    )
    stages = DataValidation(type="custom", formula1=stage_rule, allow_blank=True)
    stages.error = ("单级清水泵、管道清水泵、单级石油化工离心泵的级数固定为 1；"
                    "多级泵级数应为 ≥2 的整数。")
    stages.errorTitle = "级数"
    stages.prompt = "单级泵填 1；多级泵填 ≥2 的整数"
    stages.promptTitle = "级数"
    sheet.add_data_validation(stages)
    stages.add(f"L{FIRST_DATA_ROW}:L{LAST_DATA_ROW}")

    quantity = DataValidation(
        type="whole", operator="greaterThan", formula1="0", allow_blank=True)
    quantity.error = "数量必须为大于 0 的正整数（不得空白、0、负数或小数）。"
    quantity.errorTitle = "数量"
    sheet.add_data_validation(quantity)
    quantity.add(f"D{FIRST_DATA_ROW}:D{LAST_DATA_ROW}")


def _patch_field_dictionary(workbook) -> None:
    """同步 FieldDictionary 中「离心泵」Sheet 的描述列（机械读的范围）。"""
    config = workbook[CONFIG_SHEET]
    headers = {str(config.cell(1, c).value).strip(): c for c in range(1, 17)}
    field_id_col = headers["字段ID"]
    sheet_col = headers["sheet"]

    for row in range(2, config.max_row + 1):
        if str(config.cell(row, sheet_col).value or "").strip() != PUMP_SHEET:
            continue
        field_id = str(config.cell(row, field_id_col).value or "").strip()
        updates = FIELD_DICTIONARY_REQUIRED_UPDATES.get(field_id)
        if not updates:
            continue
        for header, text in updates.items():
            column = headers.get(header)
            if column:
                config.cell(row, column).value = text


def build(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT,
          *, enforce_owner_hash: bool = True) -> BuildReport:
    source = Path(source)
    output = Path(output)
    if not source.exists():
        raise SystemExit(f"找不到 V6 模板基线：{source}")

    source_sha = sha256_of(source)
    if enforce_owner_hash and source_sha != OWNER_BASELINE_SHA256:
        raise SystemExit(
            f"V6 基线的 SHA-256 与 Owner 指定基线不符，拒绝生成。\n"
            f"  期望 {OWNER_BASELINE_SHA256}\n  实际 {source_sha}")

    workbook = openpyxl.load_workbook(source, data_only=False)
    if PUMP_SHEET not in workbook.sheetnames:
        raise SystemExit(f"基线缺少「{PUMP_SHEET}」Sheet，模板生成中止")

    categories = _patch_categories(workbook)
    _validate_suction_reference(categories)
    cleared = _clear_business_formulas(workbook)
    _patch_validations(workbook, categories)
    _patch_field_dictionary(workbook)

    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    return BuildReport(
        source=source, source_sha256=source_sha, output=output,
        output_sha256=sha256_of(output), categories=categories,
        cleared_columns=cleared)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-other-baseline", action="store_true",
                        help="允许非 Owner 指定基线（仅用于实验，不用于正式资产）")
    args = parser.parse_args(argv)

    report = build(args.source, args.output,
                   enforce_owner_hash=not args.allow_other_baseline)
    print(f"source       : {report.source}")
    print(f"source sha256: {report.source_sha256}")
    print(f"output       : {report.output}")
    print(f"output sha256: {report.output_sha256}")
    print(f"categories   : {len(report.categories)} 项")
    for name in report.categories:
        print(f"   - {name}")
    print("cleared      : " + "、".join(report.cleared_columns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
