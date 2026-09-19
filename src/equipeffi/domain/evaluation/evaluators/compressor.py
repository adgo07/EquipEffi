"""GB 19153空压机评价器。"""
from __future__ import annotations

from typing import Any


class CompressorEvaluator:
    """按型式、功率、压力和冷却方式精确查表的空压机评价器。"""

    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]):
        # Keep shared result/validation helpers in the compatibility module
        # until the remaining device families are migrated.  Local imports
        # avoid a circular dependency when this module is imported directly.
        from ..device_evaluators import (
            _active_or_unable,
            _attach_lookup_trace,
            _attach_metrics,
            _missing,
            _positive_or_unable,
            _result,
            _value,
            out_of_scope,
            unable,
        )
        from ..decimal_math import decimal
        from ..grading import grade_three_optional
        from ...common.enums import ComparisonDirection

        if result := _active_or_unable(values, pack):
            return result
        category_value = _value(values, "category", "设备类别")
        category = str(category_value or "")
        category_rows = [
            row for row in pack.get("rows", []) if str(row.get("type")) == category
        ]
        # GB 19153表3/表4的往复活塞型式在冷却栏以空白表示
        # 不适用；只有标准行确实区分风冷/液冷时才把冷却方式设为必填。
        # 未知型式仍要求冷却方式，避免掩盖类别或输入缺失。
        cooling_required = not category_rows or any(
            str(row.get("cooling") or "").strip() for row in category_rows
        )
        fields = [
            ("设备类别", ("category", "设备类别")),
            ("额定输入功率", ("input_power_kw", "rated_power_kw", "额定输入功率", "额定或实际输入功率")),
            ("额定排气压力", ("discharge_pressure_mpa", "额定排气压力")),
            ("机组比功率", ("specific_power", "机组比功率")),
        ]
        if cooling_required:
            fields.insert(3, ("冷却方式", ("cooling_method", "冷却方式")))
        missing = _missing(values, fields)
        # 机组比功率是标准行命中后的比较指标，不参与型式、功率、
        # 压力和冷却方式查表。单独缺失时延后比较，以保留三级阈值和
        # 标准来源；其他判定轴缺失仍按原契约直接无法判定。
        defer_specific_power_missing = missing == ["机组比功率"]
        if missing and not defer_specific_power_missing:
            return unable(str(values.get("record_id", "")), pack, "缺少空压机判定参数", missing)
        positive_fields = [
            ("额定输入功率", ("input_power_kw", "rated_power_kw", "额定输入功率", "额定或实际输入功率")),
            ("额定排气压力", ("discharge_pressure_mpa", "额定排气压力")),
        ]
        if not defer_specific_power_missing:
            positive_fields.append(("机组比功率", ("specific_power", "机组比功率")))
        if result := _positive_or_unable(values, pack, positive_fields):
            return result
        if defer_specific_power_missing:
            actual = None
            actual_metrics: dict[str, Any] = {}
        else:
            actual = decimal(_value(values, "specific_power", "机组比功率"))
            actual_metrics = {"机组比功率_kW/(m3/min)": actual}
        input_power = decimal(_value(values, "input_power_kw", "rated_power_kw", "额定输入功率", "额定或实际输入功率"))
        discharge_pressure = decimal(_value(values, "discharge_pressure_mpa", "额定排气压力"))
        cooling_method = str(_value(values, "cooling_method", "冷却方式") or "")
        matching = "型式+功率+压力+冷却方式" if cooling_required else "型式+功率+压力"
        matches = [
            row for row in pack.get("rows", [])
            if str(row.get("type")) == category
            and decimal(row.get("power_kw")) == input_power
            and decimal(row.get("pressure_mpa")) == discharge_pressure
            and str(row.get("cooling")) == cooling_method
        ]
        if not matches:
            category_rows = [row for row in pack.get("rows", []) if str(row.get("type")) == category]
            lookup = {
                "step_type": "精确查表",
                "table": "/".join(sorted({str(row.get("table")) for row in category_rows if row.get("table") not in (None, "")})) or "表1～表4",
                "matching": matching,
                "query_conditions": {
                    "type": category,
                    "power_kw": str(input_power),
                    "pressure_mpa": str(discharge_pressure),
                    "cooling": cooling_method,
                },
                "match_status": "精确档位未命中",
                "standard_rule": "标准未授权通用插值，不取最近档位",
                "candidate_count": len(category_rows),
                "available_power_kw": sorted({str(row.get("power_kw")) for row in category_rows if row.get("power_kw") not in (None, "")}),
                "available_pressure_mpa": sorted({str(row.get("pressure_mpa")) for row in category_rows if row.get("pressure_mpa") not in (None, "")}),
                "available_cooling": sorted({str(row.get("cooling")) for row in category_rows if row.get("cooling") not in (None, "")}),
                "source_pages": sorted({str(row.get("source_pages")) for row in category_rows if row.get("source_pages") not in (None, "")}),
                "source_clause": "表1～表4",
            }
            result = _attach_metrics(out_of_scope(str(values.get("record_id", "")), pack, "功率、压力或型式不在标准离散档位；标准未授权通用插值"), actual_metrics)
            return _attach_lookup_trace(result, pack, lookup["table"], [lookup])
        by_level = {int(row["level"]): row for row in matches}
        thresholds = [by_level.get(level, {}).get("specific_power") for level in (1, 2, 3)]
        data_ids = [
            row.get("data_id") or f"GB19153-{row['table']}-R{next((idx for idx, candidate in enumerate(pack.get('rows', []), start=1) if candidate is row), 1):04d}-L{int(row['level'])}"
            for row in matches
            if row.get("table") is not None and row.get("level") is not None
        ]
        lookup = {
            "step_type": "精确查表",
            "table": matches[0]["table"],
            "matching": matching,
            "query_conditions": {
                "type": category,
                "power_kw": str(input_power),
                "pressure_mpa": str(discharge_pressure),
                "cooling": cooling_method,
            },
            "source_clause": "表1～表4",
            "source_pages": sorted({str(row.get("source_pages")) for row in matches if row.get("source_pages") not in (None, "")}),
            "match_status": "命中",
            "dash_semantics": "—表示该等级不作要求，不参与比较",
            "data_ids": data_ids,
            "data_id": data_ids[0] if data_ids else "",
        }
        dash_levels = [f"{level}级" for level, threshold in zip((1, 2, 3), thresholds) if threshold is None]
        if dash_levels:
            lookup.update({"standard_marker": "—", "no_data": True, "no_data_levels": dash_levels})
        if all(threshold is None for threshold in thresholds):
            result = unable(
                str(values.get("record_id", "")),
                pack,
                "该组合的标准表为‘—’或无数据，无法判定",
                ["机组比功率"] if defer_specific_power_missing else None,
            )
            result.actual_metrics = actual_metrics
            return _attach_lookup_trace(result, pack, str(matches[0]["table"]), [lookup])
        limits = {
            f"{i + 1}级机组比功率": threshold
            for i, threshold in enumerate(thresholds)
            if threshold is not None
        }
        if defer_specific_power_missing:
            result = unable(
                str(values.get("record_id", "")),
                pack,
                "缺少机组比功率，无法进行能效等级比较",
                ["机组比功率"],
            )
            result.actual_metrics = actual_metrics
            result.limits = limits
            return _attach_lookup_trace(result, pack, str(matches[0]["table"]), [lookup])
        conclusion, comparisons = grade_three_optional(actual, thresholds, ComparisonDirection.LESS_OR_EQUAL)
        return _result(values, pack, conclusion, actual_metrics, {}, limits, comparisons, str(matches[0]["table"]), [lookup], clause="表1～表4")
