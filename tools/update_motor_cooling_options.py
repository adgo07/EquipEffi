"""更新V4模板的电动机冷却方式枚举。

电动机sheet共用一个停止型下拉。其选项必须覆盖GB 18613/GB 30254及
GB 30253中出现的IC代码；本工具只改配置sheet对应的枚举列和命名区域，
不改设备字段、公式、保护或标准数据。

默认行为是就地更新指定模板；调用方应在发布前将原模板复制到独立输出目录。
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from openpyxl import load_workbook


DEFAULT_TEMPLATE = Path(__file__).resolve().parents[1] / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"

# 按标准分组后的稳定顺序；保留原有IC01/IC11/IC21/IC31及其它已有值，
# 并补充用户指定的IC86W、IC71W(IC3W7)、IC416、IC666。
MOTOR_COOLING_OPTIONS = (
    "IC01", "IC11", "IC21", "IC31",
    "IC81W", "IC86W", "IC71W(IC3W7)",
    "IC411", "IC416",
    "IC511", "IC516", "IC611", "IC616", "IC666",
    "不适用", "其他（请备注说明）",
)


def _set_named_range(workbook, name: str, sheet: str, column: str, last_row: int) -> None:
    defined = workbook.defined_names.get(name)
    if defined is None:
        raise ValueError(f"模板缺少命名区域: {name}")
    defined.attr_text = f"'{sheet}'!${column}$2:${column}${last_row}"


def update(path: Path) -> dict[str, object]:
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    workbook = load_workbook(path)
    try:
        if "配置" not in workbook.sheetnames or "电动机" not in workbook.sheetnames:
            raise ValueError("模板缺少配置或电动机sheet")
        config = workbook["配置"]
        column = "AA"
        header = str(config[f"{column}1"].value or "").strip()
        if header != "EV_COOLING_MOTOR_HV":
            raise ValueError(f"配置!{column}1不是EV_COOLING_MOTOR_HV: {header!r}")
        # 先清理该枚举的旧值，避免旧选项残留导致下拉和契约不一致。
        for row in range(2, max(config.max_row, 2) + 1):
            config[f"{column}{row}"].value = None
        for row, value in enumerate(MOTOR_COOLING_OPTIONS, start=2):
            config[f"{column}{row}"].value = value
        _set_named_range(workbook, "EV_COOLING_MOTOR_HV", "配置", column, 1 + len(MOTOR_COOLING_OPTIONS))
        # 电动机sheet的冷却方式验证必须仍指向该命名区域；若被外部编辑器
        # 改成了固定区域，恢复为命名区域以保持模板/窗口契约一致。
        motor = workbook["电动机"]
        cooling_dv = [dv for dv in motor.data_validations.dataValidation if str(dv.sqref) == "I4:I1048576"]
        if len(cooling_dv) != 1:
            raise ValueError("电动机冷却方式列缺少唯一数据验证")
        cooling_dv[0].formula1 = "EV_COOLING_MOTOR_HV"
        workbook.calculation.fullCalcOnLoad = True
        workbook.calculation.forceFullCalc = True
        workbook.calculation.calcMode = "auto"
        workbook.save(path)
    finally:
        workbook.close()
    return {"path": str(path), "option_count": len(MOTOR_COOLING_OPTIONS), "options": list(MOTOR_COOLING_OPTIONS)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="更新V4电动机冷却方式枚举")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_TEMPLATE)
    args = parser.parse_args(argv)
    import json
    print(json.dumps(update(args.path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
