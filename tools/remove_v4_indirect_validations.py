"""将V4模板的动态下拉改为静态命名范围，避免INDIRECT易失性公式。

设备类别与专属参数的条件匹配由V4ValidationService再次检查；Excel下拉使用
相应字段的完整标准枚举集合，批量粘贴和跨端输入仍不会绕过条件校验。
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"


def patch(path: Path = TEMPLATE) -> Path:
    workbook = load_workbook(path, data_only=False)
    replacements = {
        "潜水电泵": {"G4:G1048576": "=EV_SUB_FORM_ALL"},
        "热泵和冷水机组": {
            "G4:G1048576": "=EV_HP_STD_ALL",
            "H4:H1048576": "=EV_HP_UNIT_ALL",
            "I4:I1048576": "=EV_HP_SOURCE_ALL",
        },
        # EV_WATER_SOURCE同时含水冷机组的三类水源、“不适用”和说明项，
        # 因此无需再按类别调用INDIRECT；非水冷类别由服务层条件校验。
        "多联式空调": {"G4:G1048576": "=EV_WATER_SOURCE"},
    }
    changed = 0
    for sheet_name, by_range in replacements.items():
        sheet = workbook[sheet_name]
        for validation in sheet.data_validations.dataValidation:
            sqref = str(validation.sqref)
            for cell_range, formula in by_range.items():
                if sqref == cell_range and "INDIRECT(" in str(validation.formula1 or "").upper():
                    validation.formula1 = formula
                    changed += 1
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.save(path)
    print(f"已移除V4动态下拉INDIRECT公式：{changed}项；文件：{path}")
    return path


if __name__ == "__main__":
    patch()
