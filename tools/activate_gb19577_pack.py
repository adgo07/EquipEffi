"""Build the reviewed GB 19577-2024 table pack.

The source tables were transcribed from the PDF (pages 3-7 of the PDF body,
PDF pages 9-12) and cross-checked against the extracted review workbook.
This script deliberately keeps the source table/page on every record so the
human review workbook and the evaluator have the same traceable data.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "equipeffi" / "resources" / "standards" / "hvac_thresholds.json"


def _record(
    data_id: str,
    table: str,
    conditions: dict[str, Any],
    thresholds: list[float],
    *,
    metric_name: str,
    page: int,
    range_metric: str | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    min_inclusive: bool = True,
    max_inclusive: bool = True,
    fixed_gates: list[dict[str, Any]] | None = None,
    direction: str = ">=",
    **extra: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "data_id": data_id,
        "table": table,
        "conditions": conditions,
        "metric_field": "primary_metric_value",
        "metric_name": metric_name,
        "thresholds": thresholds,
        "direction": direction,
        "source_page": f"PDF第{page}页",
        "source_clause": "4.2、表" + table.removeprefix("表"),
    }
    if range_metric:
        row["range_metric"] = range_metric
    if minimum is not None:
        row["min"] = minimum
        row["min_inclusive"] = min_inclusive
    if maximum is not None:
        row["max"] = maximum
        row["max_inclusive"] = max_inclusive
    if fixed_gates:
        row["fixed_gates"] = fixed_gates
    row.update(extra)
    return row


def _hp_base(category: str, unit_type: str, source: str, system: str) -> dict[str, Any]:
    return {
        "category": category,
        "unit_type": unit_type,
        "source": source,
        "evaluation_system": system,
    }


def build_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    std18430 = ["GB/T 18430.1", "GB/T 18430.2"]
    cat_comfort = "蒸气压缩循环冷水（热泵）机组-舒适型"
    cat_data = "蒸气压缩循环冷水（热泵）机组-数据中心专用型"
    # 表1：季节/综合部分负荷指标，COPc为3级固定门槛。
    table1 = [
        ("水冷式", [(300, [6.00, 5.60, 5.20], 4.20), (528, [7.80, 7.20, 5.70], 5.00), (1163, [8.10, 7.50, 6.20], 5.40), (None, [8.50, 8.10, 6.30], 5.60)], "IPLV"),
        ("风冷式", [(50, [4.50, 4.00, 3.50], 2.70), (None, [4.30, 3.85, 3.30], 2.80)], "CSPF"),
        ("蒸发冷却式", [(300, [5.40, 5.00, 4.40], 4.00), (None, [5.80, 5.40, 5.10], 4.60)], "IPLV"),
    ]
    for source, bands, metric in table1:
        lower = 0.0
        for index, (upper, values, copc) in enumerate(bands, 1):
            conditions = _hp_base(cat_comfort, "舒适型", source, "综合部分负荷/季节性能指标体系（表1）")
            if index == 1:
                conditions["product_standard"] = std18430
            record = _record(
                f"GB19577-T1-{len(records)+1:02d}", "表1", conditions, values,
                metric_name=metric, page=9, range_metric="cooling_capacity_kw",
                minimum=None if index == 1 else lower, maximum=upper,
                min_inclusive=True if index == 1 else False,
                fixed_gates=[{"field": "copc", "name": "COPc", "threshold": copc, "levels": [3]}],
                alternate_metric_name="COPc", alternate_metric_threshold=copc,
            )
            records.append(record)
            if upper is not None:
                lower = upper
    data_bands = [(528, [8.20, 7.50, 6.80], 6.00), (1163, [10.00, 8.00, 7.40], 6.50), (None, [12.00, 10.00, 8.00], 7.00)]
    for source in ("水冷式",):
        lower = 0.0
        for index, (upper, values, copc) in enumerate(data_bands, 1):
            conditions = _hp_base(cat_data, "数据中心专用型", source, "综合部分负荷/季节性能指标体系（表1）")
            conditions["product_standard"] = std18430
            records.append(_record(
                f"GB19577-T1-{len(records)+1:02d}", "表1", conditions, values,
                metric_name="ACCOP", page=9, range_metric="cooling_capacity_kw",
                minimum=None if index == 1 else lower, maximum=upper,
                min_inclusive=True if index == 1 else False,
                fixed_gates=[{"field": "copc", "name": "COPc", "threshold": copc, "levels": [3]}],
                alternate_metric_name="COPc", alternate_metric_threshold=copc,
            ))
            if upper is not None:
                lower = upper
    conditions = _hp_base(cat_data, "数据中心专用型", "风冷式", "综合部分负荷/季节性能指标体系（表1）")
    conditions["product_standard"] = std18430
    records.append(_record(
        f"GB19577-T1-{len(records)+1:02d}", "表1", conditions, [6.80, 5.80, 4.80],
        metric_name="ACCOP", page=9,
        fixed_gates=[{"field": "copc", "name": "COPc", "threshold": 3.00, "levels": [3]}],
        alternate_metric_name="COPc", alternate_metric_threshold=3.00,
    ))

    # 表2：COPc通道；季节指标的3级值作为原文辅助信息保留。
    t2_rows = [("水冷式", [(300, [5.30, 5.10, 4.20], 5.20), (528, [5.80, 5.60, 5.00], 5.70), (1163, [6.20, 6.00, 5.40], 6.20), (None, [6.40, 6.20, 5.60], 6.30)]), ("风冷式", [(None, [3.40, 3.20, 2.80], 3.30)])]
    for source, bands in t2_rows:
        lower = 0.0
        for index, (upper, values, seasonal_l3) in enumerate(bands, 1):
            conditions = _hp_base(cat_comfort, "舒适型", source, "制冷性能系数COPc指标体系（表2）")
            conditions["product_standard"] = std18430
            records.append(_record(
                f"GB19577-T2-{len([r for r in records if r['table']=='表2'])+1:02d}", "表2", conditions, values,
                metric_name="COPc", page=9, range_metric="cooling_capacity_kw",
                minimum=None if index == 1 else lower, maximum=upper,
                min_inclusive=True if index == 1 else False,
                alternate_metric_name="CSPF/IPLV/ACCOP", alternate_metric_threshold=seasonal_l3,
            ))
            if upper is not None:
                lower = upper

    # 表3：低环境温度空气源热泵。
    t3 = [("GB/T 25127.2", "地板采暖型", 35, [3.60, 3.20, 2.80], 2.00, 2.30, "HSPF"), ("GB/T 25127.2", "风机盘管型", 35, [3.05, 2.85, 2.65], 1.80, 2.10, "APF"), ("GB/T 25127.2", "散热器型", 35, [2.60, 2.40, 2.30], 1.50, 1.70, "HSPF"), ("GB/T 25127.1", "地板采暖型", None, [3.40, 3.20, 3.00], 2.10, 2.50, "HSPF"), ("GB/T 25127.1", "风机盘管型", None, [3.30, 3.10, 3.00], 1.80, 2.30, "APF"), ("GB/T 25127.1", "散热器型", None, [2.60, 2.40, 2.30], 1.50, 1.80, "HSPF")]
    for standard, unit, upper, values, copdh, cop_h, metric in t3:
        conditions = _hp_base("低环境温度空气源热泵（冷水）机组", unit, "空气源", "对应产品类别指标体系（表3～表8）")
        conditions["product_standard"] = standard
        records.append(_record(
            f"GB19577-T3-{len([r for r in records if r['table']=='表3'])+1:02d}", "表3", conditions, values,
            metric_name=metric, page=10, range_metric="heating_capacity_kw", maximum=upper,
            max_inclusive=True if upper is not None else True,
            fixed_gates=[{"field": "cop_dh", "name": "COPdh", "threshold": copdh}, {"field": "cop_h", "name": "COPh", "threshold": cop_h}],
        ) if upper is not None else _record(
            f"GB19577-T3-{len([r for r in records if r['table']=='表3'])+1:02d}", "表3", conditions, values,
            metric_name=metric, page=10, range_metric="heating_capacity_kw", minimum=35, min_inclusive=False,
            fixed_gates=[{"field": "cop_dh", "name": "COPdh", "threshold": copdh}, {"field": "cop_h", "name": "COPh", "threshold": cop_h}],
        ))

    # 表4：水（地）源热泵。冷热风热泵型以制冷量以外的容量不作分档（原文为—）。
    def t4(unit: str, mode: str, source: str, values: list[float], *, capacity_field: str | None = None, upper: float | None = None, lower: float | None = None) -> None:
        conditions = _hp_base("水（地）源热泵机组", f"{unit}-{mode}", source, "对应产品类别指标体系（表3～表8）")
        conditions["product_standard"] = "GB/T 19409"
        records.append(_record(f"GB19577-T4-{len([r for r in records if r['table']=='表4'])+1:02d}", "表4", conditions, values, metric_name="ACOP" if mode == "热泵型" else "COP", page=10, range_metric=capacity_field, minimum=lower, maximum=upper, min_inclusive=False if lower is not None else True))
    for source, values in [("水环式", [4.60, 4.10, 3.70]), ("地下水式", [5.10, 4.60, 4.00]), (["地埋管式", "地表水式"], [4.40, 4.00, 3.80])]:
        t4("冷热风型", "热泵型", source, values)
    for mode, source_values in [("单热型", [("水环式", [5.60, 5.00, 4.60]), ("地下水式", [4.90, 4.50, 4.00]), (["地埋管式", "地表水式"], [4.70, 4.30, 4.20])]), ("热泵型", [("水环式", [5.10, 4.70, 4.00]), ("地下水式", [5.70, 5.50, 5.30]), (["地埋管式", "地表水式"], [5.10, 4.70, 4.20])])]:
        for source, values in source_values:
            t4("冷热水型", mode, source, values, capacity_field="heating_capacity_kw" if mode == "单热型" else "cooling_capacity_kw", upper=260)
            if mode == "单热型":
                more = {"水环式": [5.80, 5.40, 4.40], "地下水式": [5.10, 4.70, 4.40], "地埋管式、地表水式": [4.90, 4.50, 4.20]}["地埋管式、地表水式" if isinstance(source, list) else source]
                t4("冷热水型", mode, source, more, capacity_field="heating_capacity_kw", lower=260)
            else:
                more = {"水环式": [5.80, 5.20, 4.30], "地下水式": [6.20, 5.80, 5.40], "地埋管式、地表水式": [5.60, 5.10, 4.40]}["地埋管式、地表水式" if isinstance(source, list) else source]
                t4("冷热水型", mode, source, more, capacity_field="cooling_capacity_kw", lower=260)

    # 表5：溴化锂吸收式，蒸汽型为耗量（越小越好），直燃型为COP（越大越好）。
    for pressure, values in [("饱和蒸汽压力0.4MPa", [1.05, 1.10, 1.19]), ("饱和蒸汽压力0.6MPa", [1.02, 1.05, 1.11]), ("饱和蒸汽压力0.8MPa", [1.00, 1.02, 1.09])]:
        records.append(_record(f"GB19577-T5-{len([r for r in records if r['table']=='表5'])+1:02d}", "表5", _hp_base("溴化锂吸收式冷（温）水机组", pressure, "饱和蒸汽", "对应产品类别指标体系（表3～表8）") | {"product_standard": "GB/T 18431"}, values, metric_name="单位制冷量加热源耗量", page=11, direction="<="))
    records.append(_record(f"GB19577-T5-04", "表5", _hp_base("溴化锂吸收式冷（温）水机组", "直燃型机组", "直燃", "对应产品类别指标体系（表3～表8）") | {"product_standard": "GB/T 18362"}, [1.46, 1.40, 1.30], metric_name="COP", page=11))

    # 表6：高温热泵。
    for unit, values in [("H1a", [4.00, 3.80, 3.60]), ("H2a", [4.40, 4.20, 4.00]), ("H3a", [4.10, 3.90, 3.70]), ("H4a", [3.70, 3.50, 3.30]), ("H5a", [3.40, 3.20, 3.00]), ("H1b", [4.50, 4.20, 4.00]), ("H2b", [4.80, 4.50, 4.30]), ("H3b", [4.50, 4.10, 3.90]), ("H4b", [4.00, 3.70, 3.50]), ("H5b", [3.60, 3.30, 3.20])]:
        records.append(_record(f"GB19577-T6-{len([r for r in records if r['table']=='表6'])+1:02d}", "表6", _hp_base("蒸气压缩循环高温热泵机组", unit, "水源", "对应产品类别指标体系（表3～表8）") | {"product_standard": "GB/T 25861"}, values, metric_name="COPH", page=11))
    records.append(_record("GB19577-T6-11", "表6", _hp_base("蒸气压缩循环高温热泵机组", "循环供水式热泵高温热水机组", "水源", "对应产品类别指标体系（表3～表8）") | {"product_standard": "JB/T 12840"}, [4.10, 3.70, 3.40], metric_name="COP", page=11))

    # 表7：间接蒸发冷却冷水机组。
    for standard, units, metric in [("JB/T 14642", [("标准机型", [(100, [17, 14, 10], 9), (None, [22, 19, 15], 13)]), ("大温差型", [(100, [21, 18, 14], 12), (None, [25, 22, 18], 16)])], "AEER"), ("JB/T 14640", [("外冷式", [(100, [16, 14, 10], None), (None, [20, 17, 14], None)]), ("内冷式", [(100, [15, 11, 9], None), (None, [20, 14, 13], None)]), ("内外冷串联式", [(100, [21, 15, 12], None), (None, [22, 15, 14], None)])], "EER")]:
        for unit, bands in units:
            lower = 0.0
            for index, (upper, values, eer) in enumerate(bands, 1):
                conditions = _hp_base("间接蒸发冷却冷水机组", unit, "不适用", "对应产品类别指标体系（表3～表8）") | {"product_standard": standard}
                gate = [{"field": "eer", "name": "EER", "threshold": eer, "levels": [3]}] if eer is not None else None
                records.append(_record(f"GB19577-T7-{len([r for r in records if r['table']=='表7'])+1:02d}", "表7", conditions, values, metric_name=metric, page=12, range_metric="cooling_capacity_kw", minimum=None if index == 1 else lower, maximum=upper, min_inclusive=True if index == 1 else False, fixed_gates=gate))
                if upper is not None:
                    lower = upper

    # 表8：一体式机组，COPI为各等级固定门槛。
    for unit, bands in [("蒸发冷却式冷却塔式", [(300, [5.40, 5.00, 4.40], 4.00), (528, [5.60, 5.00, 4.80], 4.40), (1163, [5.80, 5.40, 5.10], 4.60), (None, [6.00, 5.60, 5.20], 4.80)]), ("风冷式", [(50, [4.40, 3.90, 3.40], 2.70), (None, [4.20, 3.75, 3.20], 2.70)])]:
        lower = 0.0
        for index, (upper, values, copi) in enumerate(bands, 1):
            conditions = _hp_base("一体式冷水（热泵）机组", unit, "不适用", "对应产品类别指标体系（表3～表8）") | {"product_standard": "JB/T 12839"}
            records.append(_record(f"GB19577-T8-{len([r for r in records if r['table']=='表8'])+1:02d}", "表8", conditions, values, metric_name="IPLV(I)", page=12, range_metric="cooling_capacity_kw", minimum=None if index == 1 else lower, maximum=upper, min_inclusive=True if index == 1 else False, fixed_gates=[{"field": "copi", "name": "COP(I)", "threshold": copi, "levels": [3]}]))
            if upper is not None:
                lower = upper
    return records


def main() -> None:
    existing = json.loads(TARGET.read_text(encoding="utf-8"))
    records = build_records()
    payload = {
        "standard_code": "GB 19577-2024",
        "standard_name": "热泵和冷水机组能效限定值及能效等级",
        "source_note": "PDF逐表复核版；表1～表8分别对应PDF第9～12页，—表示原文不作容量分档或不设置该指标。",
        "status": "active",
        "verified_table_count": 8,
        "source_files": [
            "13. GB 19577-2024 热泵和冷水机组能效限定值及能效等级.pdf",
            "standards2/第四来源Excel_按设备/heat_pump_chiller.xlsx",
        ],
        "devices": {
            "heat_pump_chiller": {
                "status": "active",
                "records": records,
                "notes": [
                    "表1采用综合部分负荷/季节性能指标并以COPc 3级限定值作固定门槛。",
                    "表2为COPc通道；表4～表8按各自标准规定的单一主指标或固定门槛判定。",
                    "所有标称指标按设计/铭牌值输入，不代表型式试验合格证明。",
                ],
            },
            "heat_pump_water_heater": existing["devices"]["heat_pump_water_heater"],
            "duct_ac": existing["devices"]["duct_ac"],
            "unitary_ac": existing["devices"]["unitary_ac"],
            "multi_split_ac": existing["devices"]["multi_split_ac"],
        },
    }
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {TARGET} with {len(records)} GB19577 records")


if __name__ == "__main__":
    main()
