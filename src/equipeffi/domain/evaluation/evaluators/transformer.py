"""GB 20052变压器评价器。

本模块只承载变压器规则；共享追踪、查表和结果辅助函数暂由旧兼容模块
提供。辅助函数采用方法内导入，确保本模块可独立导入且不会形成循环依赖。
"""
from __future__ import annotations

import re
from typing import Any


class TransformerEvaluator:
    required = [
        ("设备类别", ("category", "设备类别")),
        ("额定容量", ("capacity_kva", "额定容量")),
        ("空载损耗", ("no_load_loss_w", "空载损耗")),
        ("负载损耗", ("load_loss_w", "负载损耗")),
    ]

    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]):
        # Keep shared helpers in the compatibility module for this first,
        # behavior-preserving extraction.  Local imports avoid a module-level
        # cycle when callers import this evaluator directly.
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
        from ..decimal_math import bracket, decimal, linear_interpolate, rounded
        from ...common.enums import Conclusion

        if result := _active_or_unable(values, pack):
            return result
        missing = _missing(values, self.required)
        # 分类与容量已齐、但只缺少一项（或两项）损耗时仍应完成标准
        # 查表。损耗是比较所需的实际指标，不是选择标准行的查询轴；
        # 直接在入口早退会丢失另一项已填损耗、三级阈值和来源页。
        missing_loss_fields = [item for item in missing if item in {"空载损耗", "负载损耗"}]
        defer_loss_comparison = bool(missing) and len(missing_loss_fields) == len(missing)
        if missing and not defer_loss_comparison:
            return unable(str(values.get("record_id", "")), pack, "缺少变压器判定参数", missing)
        if result := _positive_or_unable(values, pack, [
            ("额定容量", ("capacity_kva", "额定容量")),
            ("空载损耗", ("no_load_loss_w", "空载损耗")),
            ("负载损耗", ("load_loss_w", "负载损耗")),
        ]):
            return result
        category = str(_value(values, "category", "设备类别"))
        capacity = decimal(_value(values, "capacity_kva", "额定容量"))
        actual_no = None
        actual_load = None
        actual_metrics = {}
        raw_no = _value(values, "no_load_loss_w", "空载损耗")
        raw_load = _value(values, "load_loss_w", "负载损耗")
        if raw_no is not None:
            actual_no = decimal(raw_no)
            actual_metrics["空载损耗_W"] = actual_no
        if raw_load is not None:
            actual_load = decimal(raw_load)
            actual_metrics["负载损耗_W"] = actual_load
        filters = {
            "category": category,
            "core_material": str(_value(values, "core_material", "铁芯材质") or ""),
            "insulation": str(_value(values, "insulation", "绝缘耐热等级", "绝缘等级") or ""),
            "connection": str(_value(values, "connection", "连接组标号") or ""),
        }
        rows = [row for row in pack.get("rows", []) if all(str(row.get(k, "")) == v for k, v in filters.items())]
        if not rows:
            # 类别已命中但铁芯材质、绝缘等级或连接组等分类条件组合未命中
            # 时，不能只给一个无上下文的无法判定。保留同类别候选行和稳定
            # 记录ID，便于用户校对输入；候选行不参与容量插值或等级比较。
            category_rows = [
                row for row in pack.get("rows", [])
                if str(row.get("category", "")) == category
            ]
            if category_rows:
                def row_data_id(candidate: dict[str, Any]) -> str:
                    candidate_index = next(
                        (index for index, item in enumerate(pack.get("rows", []), start=1) if item is candidate),
                        1,
                    )
                    return str(candidate.get("data_id") or f"GB20052-{candidate.get('table', '标准表')}-R{candidate_index:03d}")

                table_names = "/".join(sorted({str(row.get("table")) for row in category_rows if row.get("table") not in (None, "")})) or "标准表"
                source_pages: set[str] = set()
                candidate_rows: list[dict[str, Any]] = []
                for candidate in category_rows:
                    raw_page = candidate.get("source_pages", candidate.get("source_page"))
                    page_values = raw_page if isinstance(raw_page, (list, tuple)) else [raw_page]
                    source_pages.update(str(page) for page in page_values if page not in (None, ""))
                    candidate_rows.append({
                        "capacity_kva": str(candidate.get("capacity_kva", "")),
                        "core_material": str(candidate.get("core_material", "")),
                        "insulation": str(candidate.get("insulation", "")),
                        "connection": str(candidate.get("connection", "")),
                        "data_id": row_data_id(candidate),
                    })
                lookup = {
                    "step_type": "精确查表",
                    "table": table_names,
                    "matching": "类别+铁芯材质+绝缘耐热等级+连接组标号+额定容量",
                    "query_conditions": {
                        **filters,
                        "capacity_kva": str(capacity),
                    },
                    "match_status": "分类条件组合未命中",
                    "standard_rule": "类别和分类参数必须与标准枚举组合完全匹配；不自动映射、不取最近档位",
                    "candidate_count": len(candidate_rows),
                    "candidate_rows": candidate_rows,
                    "available_core_materials": sorted({item["core_material"] for item in candidate_rows if item["core_material"]}),
                    "available_insulations": sorted({item["insulation"] for item in candidate_rows if item["insulation"]}),
                    "available_connections": sorted({item["connection"] for item in candidate_rows if item["connection"]}),
                    "data_ids": [item["data_id"] for item in candidate_rows],
                    "source_pages": sorted(source_pages),
                    "source_clause": table_names,
                }
                result = _attach_metrics(
                    unable(str(values.get("record_id", "")), pack, "类别已命中，但分类参数组合未命中标准表"),
                    actual_metrics,
                )
                return _attach_lookup_trace(result, pack, table_names, [lookup])
            return _attach_metrics(unable(str(values.get("record_id", "")), pack, "未找到完整类别、材质、绝缘和连接组组合"), actual_metrics)
        exact = [row for row in rows if decimal(row["capacity_kva"]) == capacity]
        lookup: dict[str, Any]
        if exact:
            row = exact[0]
            row_index = next((index for index, item in enumerate(pack.get("rows", []), start=1) if item is row), 1)
            no_load = [decimal(x) * 1000 for x in row["no_load_kw"]]
            load = [decimal(x) * 1000 for x in row["load_kw"]]
            lookup = {
                "step_type": "精确查表",
                "table": row["table"],
                "matching": "类别+铁芯材质+绝缘耐热等级+连接组标号+额定容量",
                "query_conditions": {
                    **filters,
                    "capacity_kva": str(capacity),
                },
                "match_status": "命中",
                "capacity_kva": str(capacity),
                # 标准包中的稳定记录ID优先；旧/临时包才回退到行号ID。
                "data_id": row.get("data_id") or f"GB20052-{row['table']}-R{row_index:03d}",
                "source_clause": row["table"],
                # 精确命中时保留标准行的PDF页码，供结果、报告和后续
                # Excel/移动端适配器直接追溯；旧包没有页码时保持空值。
                "source_page": row.get("source_page", row.get("source_pages", "")),
            }
        else:
            tables = {row["table"] for row in rows}
            table_names = "/".join(sorted(str(table) for table in tables)) or "标准表"

            def row_data_id(candidate: dict[str, Any]) -> str:
                candidate_index = next(
                    (index for index, item in enumerate(pack.get("rows", []), start=1) if item is candidate),
                    1,
                )
                return str(candidate.get("data_id") or f"GB20052-{candidate['table']}-R{candidate_index:03d}")

            source_pages: list[str] = []
            for candidate in rows:
                raw_pages = candidate.get("source_pages", candidate.get("source_page"))
                page_values = raw_pages if isinstance(raw_pages, (list, tuple)) else [raw_pages]
                for page in page_values:
                    if page not in (None, "") and str(page) not in source_pages:
                        source_pages.append(str(page))
            lookup = {
                "step_type": "线性插值",
                "table": table_names,
                "matching": "类别+铁芯材质+绝缘耐热等级+连接组标号+额定容量",
                "query_conditions": {
                    **filters,
                    "capacity_kva": str(capacity),
                },
                "match_status": "容量插值端点未命中",
                "standard_rule": "仅标准明确允许的容量表内插值；禁止外推，不取最近档位",
                "candidate_count": len(rows),
                "available_capacity_kva": [
                    str(candidate["capacity_kva"])
                    for candidate in sorted(rows, key=lambda item: decimal(item["capacity_kva"]))
                ],
                "data_ids": [row_data_id(candidate) for candidate in rows],
                "source_pages": sorted(source_pages),
                "source_clause": table_names,
            }
            if len(tables) != 1 or not any(int(re.sub(r"\D", "", table) or 0) >= 29 for table in tables):
                lookup["match_status"] = "容量插值未授权"
                lookup["standard_rule"] = "对应标准表不允许容量插值；禁止外推，不取最近档位"
                result = _attach_metrics(
                    out_of_scope(str(values.get("record_id", "")), pack, "额定容量不在离散容量档，且对应表不允许插值"),
                    actual_metrics,
                )
                return _attach_lookup_trace(result, pack, table_names, [lookup])
            try:
                low, high = bracket(rows, "capacity_kva", capacity)
            except ValueError as exc:
                lookup["interpolation_blocked"] = str(exc)
                result = _attach_metrics(
                    out_of_scope(str(values.get("record_id", "")), pack, str(exc)),
                    actual_metrics,
                )
                return _attach_lookup_trace(result, pack, table_names, [lookup])
            no_load, load, factors = [], [], []
            for idx in range(3):
                item, factor = linear_interpolate(capacity, low["capacity_kva"], low["no_load_kw"][idx], high["capacity_kva"], high["no_load_kw"][idx])
                no_load.append(item * 1000)
                factors.append(factor)
                item, _ = linear_interpolate(capacity, low["capacity_kva"], low["load_kw"][idx], high["capacity_kva"], high["load_kw"][idx])
                load.append(item * 1000)
            row = low
            low_index = next((index for index, item in enumerate(pack.get("rows", []), start=1) if item is low), 1)
            high_index = next((index for index, item in enumerate(pack.get("rows", []), start=1) if item is high), 1)
            lookup.update({
                "table": row["table"],
                "endpoints": [low["capacity_kva"], high["capacity_kva"]],
                "factor": str(factors[0]),
                "match_status": "命中",
                "data_ids": [
                    low.get("data_id") or f"GB20052-{low['table']}-R{low_index:03d}",
                    high.get("data_id") or f"GB20052-{high['table']}-R{high_index:03d}",
                ],
            })
        limits = (
            {f"空载损耗-{i+1}级_W": rounded(no_load[i]) for i in range(3)}
            | {f"负载损耗-{i+1}级_W": rounded(load[i]) for i in range(3)}
        )
        if defer_loss_comparison:
            result = unable(
                str(values.get("record_id", "")),
                pack,
                f"缺少{'、'.join(missing_loss_fields)}，无法进行空载损耗和负载损耗等级比较",
                missing_loss_fields,
            )
            _attach_metrics(result, actual_metrics)
            result.limits = limits
            return _attach_lookup_trace(result, pack, row["table"], [lookup])

        comparisons = []
        conclusion = Conclusion.NOT_COMPLIANT
        for idx, level in enumerate((Conclusion.LEVEL_1, Conclusion.LEVEL_2, Conclusion.LEVEL_3)):
            no_ok, load_ok = actual_no <= no_load[idx], actual_load <= load[idx]
            comparisons.append({
                "level": level.value,
                "rule": "空载损耗AND负载损耗",
                "passed": no_ok and load_ok,
                "no_load_passed": no_ok,
                "load_passed": load_ok,
                "no_load_actual": str(actual_no),
                "no_load_threshold": str(no_load[idx]),
                "load_actual": str(actual_load),
                "load_threshold": str(load[idx]),
                "direction": "<=",
            })
            if no_ok and load_ok and conclusion is Conclusion.NOT_COMPLIANT:
                conclusion = level
        return _result(
            values,
            pack,
            conclusion,
            actual_metrics,
            {},
            limits,
            comparisons,
            row["table"],
            [lookup],
            clause=row["table"],
        )
