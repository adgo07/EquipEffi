"""低压、高压和永磁同步电动机评价器。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ...common.enums import ComparisonDirection
from ...common.models import EvaluationResult
from ..decimal_math import bracket, decimal, linear_interpolate, rounded
from ..grading import compare, grade_three, grade_three_optional


def _legacy_helper(name: str):
    def call(*args: Any, **kwargs: Any):
        from .. import device_evaluators

        return getattr(device_evaluators, name)(*args, **kwargs)

    return call

_active_or_unable = _legacy_helper("_active_or_unable")
_attach_lookup_trace = _legacy_helper("_attach_lookup_trace")
_attach_metrics = _legacy_helper("_attach_metrics")
_interval_hit = _legacy_helper("_interval_hit")
_missing = _legacy_helper("_missing")
_percent_or_unable = _legacy_helper("_percent_or_unable")
_positive_or_unable = _legacy_helper("_positive_or_unable")
_result = _legacy_helper("_result")
_value = _legacy_helper("_value")
out_of_scope = _legacy_helper("out_of_scope")
unable = _legacy_helper("unable")


# GB 30254-2024 高压电动机表1～表6的冷却方式分组。这里刻意只登记
# 标准表题中出现的值；公共输入枚举可以比标准表更宽（例如 IC86W、
# IC71W(IC3W7)、IC416、IC666），但这些值不能被推断映射到相邻分组。
_HV_COOLING_GROUPS: tuple[tuple[frozenset[str], int], ...] = (
    (frozenset({"IC01", "IC11", "IC21", "IC31", "IC81W"}), 0),
    (frozenset({"IC611", "IC616", "IC511", "IC516"}), 2),
    (frozenset({"IC411"}), 4),
)


class MotorEvaluator:
    def __init__(self, device_type: str):
        self.device_type = device_type

    def _select_table(self, values: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any] | None:
        tables = pack.get("tables")
        if not tables:
            return pack
        requested = str(_value(values, "standard_table", "匹配表/条款") or "")
        if requested:
            for table in tables:
                if requested in (table.get("title", ""), table.get("name", "")) or requested in table.get("title", ""):
                    return table
        if self.device_type == "motor_hv":
            voltage = _value(values, "rated_voltage_v", "额定电压")
            cooling = str(_value(values, "cooling_method", "冷却方式") or "")
            try:
                voltage_value = decimal(voltage)
            except ValueError:
                return None
            low_voltage_group = voltage_value in {Decimal(3000), Decimal(3300), Decimal(6000), Decimal(6600)}
            high_voltage_group = voltage_value in {Decimal(10000), Decimal(11000)}
            base = next((index for members, index in _HV_COOLING_GROUPS if cooling in members), None)
            if base is not None and (low_voltage_group or high_voltage_group):
                index = base + (1 if high_voltage_group else 0)
                return tables[index] if index < len(tables) else None
        criteria = " ".join(str(_value(values, key) or "") for key in ("category", "rated_voltage_v", "cooling_method"))
        hits = [table for table in tables if all(token in table.get("title", "") for token in criteria.split() if token)]
        return hits[0] if len(hits) == 1 else None

    @staticmethod
    def _hv_unmatched_lookup(values: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any] | None:
        """Build an auditable candidate-table record for an HV axis miss.

        The standard has six discrete tables.  A cooling code that is accepted
        by the shared motor input enum is not evidence that GB 30254 covers it;
        retain the voltage-compatible table rows so callers can see exactly
        which standard choices were considered, without selecting a nearest or
        otherwise similar cooling group.  A missing cooling code is also
        retained as a candidate-table record (but never inferred).  A positive
        voltage outside the standard's discrete groups is retained as an
        all-table candidate record instead of silently losing the lookup
        context.
        """

        voltage = _value(values, "rated_voltage_v", "额定电压")
        cooling = _value(values, "cooling_method", "冷却方式")
        # 显式指定标准表/条款时仍由 ``_select_table`` 负责处理；即使
        # 指定值无效，也不要把该输入重新解释成冷却方式未命中。
        if _value(values, "standard_table", "匹配表/条款") not in (None, ""):
            return None
        if voltage in (None, ""):
            return None
        try:
            voltage_value = decimal(voltage)
        except (TypeError, ValueError):
            return None
        low_voltage_group = voltage_value in {Decimal(3000), Decimal(3300), Decimal(6000), Decimal(6600)}
        high_voltage_group = voltage_value in {Decimal(10000), Decimal(11000)}
        voltage_group = "high" if high_voltage_group else "low" if low_voltage_group else None

        candidate_tables: list[dict[str, Any]] = []
        source_pages: set[str] = set()
        data_ids: list[str] = []
        for table_index, table in enumerate(pack.get("tables") or [], start=1):
            title = str(table.get("title", table.get("name", f"表{table_index}")))
            if voltage_group is not None:
                table_is_high_voltage = "10kV" in title
                if table_is_high_voltage != (voltage_group == "high"):
                    continue
            group_base = ((table_index - 1) // 2) * 2
            members = next(
                (sorted(group) for group, base in _HV_COOLING_GROUPS if base == group_base),
                [],
            )
            rows: list[dict[str, Any]] = []
            for row_index, row in enumerate(table.get("rows", []), start=1):
                row_id = str(row.get("data_id") or f"GB30254-T{table_index:02d}-R{row_index:03d}")
                row_item = {
                    "power_kw": str(row.get("power_kw", "")),
                    "data_id": row_id,
                }
                rows.append(row_item)
                if row_id not in data_ids:
                    data_ids.append(row_id)
            raw_pages = table.get("source_pages", table.get("source_page", ""))
            page_values = raw_pages if isinstance(raw_pages, (list, tuple)) else [raw_pages]
            source_pages.update(str(page) for page in page_values if page not in (None, ""))
            candidate_tables.append({
                "table_no": table_index,
                "table": title,
                "available_cooling_methods": members,
                "row_count": len(rows),
                "rows": rows,
                "source_pages": sorted(str(page) for page in page_values if page not in (None, "")),
            })
        if not candidate_tables:
            return None
        table_names = "/".join(f"表{item['table_no']}" for item in candidate_tables)
        if voltage_group is None:
            match_status = "额定电压未命中"
        elif cooling in (None, ""):
            match_status = "冷却方式未提供"
        else:
            match_status = "冷却方式未命中"
        return {
            "step_type": "标准表选择",
            "table": table_names,
            "matching": "额定电压+冷却方式",
            "query_conditions": {
                "rated_voltage_v": str(voltage),
                "cooling_method": "" if cooling in (None, "") else str(cooling),
            },
            "match_status": match_status,
            "standard_rule": "GB 30254-2024仅接受标准表题列出的额定电压组和冷却方式；不将未命中的电压或冷却代码映射到其他分组",
            "candidate_count": len(candidate_tables),
            "candidate_tables": candidate_tables,
            "data_ids": data_ids,
            "source_pages": sorted(source_pages),
            "source_clause": table_names,
        }

    def _missing_power_lookup(
        self,
        values: dict[str, Any],
        pack: dict[str, Any],
        table: dict[str, Any],
    ) -> dict[str, Any]:
        """Keep the selected motor table and all power rows when power is absent.

        GB 18613-2020/GB 30254-2024 select a table before using rated power
        plus poles to select a row.  A missing power value must not be replaced
        with a nearest row; retaining the complete discrete power axis makes
        the missing-input result auditable and actionable.
        """

        all_tables = pack.get("tables") or [pack]
        table_index = next((index for index, item in enumerate(all_tables, start=1) if item is table), 1)
        rows = list(table.get("rows", pack.get("rows", [])))
        mode = table.get("mode", pack.get("mode", "poles"))
        dimension_label = "极数" if mode == "poles" else "额定转速"
        dimension_value = _value(values, "poles", "极数") if mode == "poles" else _value(
            values,
            "speed_rpm",
            "rated_speed_rpm",
            "额定转速",
        )

        candidate_rows: list[dict[str, Any]] = []
        data_ids: list[str] = []
        available_power_kw: list[str] = []
        for row_index, row in enumerate(rows, start=1):
            standard_prefix = "GB30254" if self.device_type == "motor_hv" else "GB18613"
            row_id = str(row.get("data_id") or f"{standard_prefix}-T{table_index:02d}-R{row_index:03d}")
            power_value = str(row.get("power_kw", ""))
            candidate_rows.append({
                "power_kw": power_value,
                "data_id": row_id,
            })
            available_power_kw.append(power_value)
            data_ids.append(row_id)
        raw_pages = table.get("source_pages", table.get("source_page", pack.get("source_page", "")))
        table_name = table.get("title", table.get("name", "表1"))
        dims = table.get("dims", pack.get("dims", []))
        lookup = {
            "step_type": "精确查表",
            "table": table_name,
            "matching": "功率+极数" if mode == "poles" else "功率+转速",
            "query_conditions": {
                "power_kw": "",
                "dimension": "" if dimension_value in (None, "") else str(dimension_value),
                "dimension_name": "poles" if mode == "poles" else "speed_rpm",
            },
            "match_status": "额定功率未提供",
            "standard_rule": "标准表按额定功率离散档查表；缺少额定功率时不选择最近档位、不外推、不进行功率插值",
            "candidate_count": len(candidate_rows),
            "available_power_kw": available_power_kw,
            "available_dimensions": [str(item) for item in dims],
            "candidate_rows": candidate_rows,
            "data_ids": data_ids,
            "source_pages": raw_pages,
            "source_clause": table_name,
            "no_interpolation": True,
            "missing_dimension": "额定功率",
            "dimension_label": dimension_label,
        }
        # 低压GB 18613资源使用包级单页来源；沿用正常查表记录的
        # ``source_page``键，同时保留统一的``source_pages``字段。
        if table is pack and raw_pages not in (None, ""):
            lookup["source_page"] = raw_pages
        return lookup

    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]) -> EvaluationResult:
        if result := _active_or_unable(values, pack):
            return result
        needed = _missing(values, [("额定功率", ("rated_power_kw", "额定功率")), ("额定效率", ("rated_efficiency", "额定效率"))])
        # 额定效率只用于最终等级比较，不参与GB 18613/GB 30254
        # 的表族、功率行选择。两类电动机在其余查询条件完整时延后
        # 处理该缺失，以便保留标准阈值和查表证据；额定功率缺失
        # 仍仅由高压电动机的专门候选功率轴分支处理。
        defer_efficiency_missing = self.device_type in {"motor_lv", "motor_hv"} and needed == ["额定效率"]
        if needed and not defer_efficiency_missing:
            if self.device_type in {"motor_lv", "motor_hv"} and "额定功率" in needed:
                # 电压、冷却方式和极数足以确定表族时，先保留整张表的
                # 功率轴；不因功率缺失而丢掉已提供的效率或标准来源。
                selected_table = self._select_table(values, pack)
                if selected_table is not None:
                    actual_metrics: dict[str, Any] = {}
                    efficiency_value = _value(values, "rated_efficiency", "额定效率")
                    if efficiency_value is not None:
                        try:
                            efficiency = decimal(efficiency_value)
                        except ValueError:
                            efficiency = None
                        if efficiency is not None and Decimal(1) <= efficiency <= Decimal(100):
                            actual_metrics["额定效率_%"] = efficiency
                    lookup = self._missing_power_lookup(values, pack, selected_table)
                    reason = "缺少额定功率" if needed == ["额定功率"] else f"缺少电动机判定参数：{'、'.join(needed)}"
                    result = _attach_metrics(
                        unable(str(values.get("record_id", "")), pack, reason, needed),
                        actual_metrics,
                    )
                    return _attach_lookup_trace(
                        result,
                        pack,
                        lookup["table"],
                        [lookup],
                    )
            return unable(str(values.get("record_id", "")), pack, "缺少电动机判定参数", needed)
        if result := _positive_or_unable(values, pack, [("额定功率", ("rated_power_kw", "额定功率"))]):
            return result
        if not defer_efficiency_missing:
            if result := _percent_or_unable(values, pack, "额定效率", ("rated_efficiency", "额定效率")):
                return result
        power = decimal(_value(values, "rated_power_kw", "额定功率"))
        if defer_efficiency_missing:
            actual = None
            actual_metrics: dict[str, Any] = {}
        else:
            actual = decimal(_value(values, "rated_efficiency", "额定效率"))
            actual_metrics = {"额定效率_%": actual}
        # GB 18613-2020机器标准包只收录表1“三相异步电动机”。公共
        # 电动机sheet还允许电容类、空调风扇用等其他产品，不能因为它们
        # 具有功率和极数就静默套用三相异步电动机效率表。
        if self.device_type == "motor_lv":
            category = str(_value(values, "category", "设备类别") or "").strip()
            supported_categories = ["三相异步电动机"]
            if not category:
                return _attach_metrics(
                    unable(str(values.get("record_id", "")), pack, "低压电动机缺少设备类别", ["设备类别"]),
                    actual_metrics,
                )
            if category not in {"三相异步电动机", "三相异步电动机（一般用途）"}:
                rows = list(pack.get("rows", []))
                candidate_rows = [
                    {
                        "data_id": str(row.get("data_id", "")),
                        "power_kw": str(row.get("power_kw", "")),
                    }
                    for row in rows
                ]
                lookup = {
                    "step_type": "精确查表",
                    "table": "表1",
                    "matching": "设备类别",
                    "category": category,
                    "supported_categories": supported_categories,
                    "candidate_count": len(candidate_rows),
                    "candidate_rows": candidate_rows,
                    "data_ids": [row["data_id"] for row in candidate_rows if row["data_id"]],
                    "match_status": "设备类别未命中",
                    "standard_rule": "GB 18613-2020表1仅适用于三相异步电动机；其他类别不得默认映射",
                    "source_clause": "表1",
                    "source_page": pack.get("source_page", ""),
                    "no_interpolation": True,
                }
                result = _attach_metrics(
                    out_of_scope(
                        str(values.get("record_id", "")),
                        pack,
                        "设备类别不在GB 18613-2020表1的三相异步电动机范围内，不能默认套用效率表",
                    ),
                    actual_metrics,
                )
                return _attach_lookup_trace(result, pack, "表1", [lookup])
        table = self._select_table(values, pack)
        if table is None:
            if self.device_type == "motor_hv":
                lookup = self._hv_unmatched_lookup(values, pack)
                if lookup is not None:
                    voltage_miss = lookup.get("match_status") == "额定电压未命中"
                    cooling_missing = lookup.get("match_status") == "冷却方式未提供"
                    reason = (
                        "额定电压不在GB 30254-2024标准表的离散电压组内，不能自动映射"
                        if voltage_miss
                        else (
                            "高压电动机缺少冷却方式，不能唯一确定GB 30254-2024标准表"
                            if cooling_missing
                            else "高压电动机冷却方式未命中GB 30254-2024标准表，不能自动映射，请填写标准表/条款或核对冷却方式"
                        )
                    )
                    if voltage_miss:
                        status_result = out_of_scope(
                            str(values.get("record_id", "")),
                            pack,
                            reason,
                        )
                    else:
                        status_result = unable(
                            str(values.get("record_id", "")),
                            pack,
                            reason,
                            ["冷却方式"] if cooling_missing else None,
                        )
                    result = _attach_metrics(
                        status_result,
                        actual_metrics,
                    )
                    return _attach_lookup_trace(result, pack, lookup["table"], [lookup])
            return _attach_metrics(unable(str(values.get("record_id", "")), pack, "无法唯一确定标准表，请填写匹配表/条款"), actual_metrics)
        rows = table.get("rows", pack.get("rows", []))
        mode = table.get("mode", pack.get("mode", "poles"))
        dims = table.get("dims", pack.get("dims", []))
        dim_value = _value(values, "poles", "极数") if mode == "poles" else _value(values, "speed_rpm", "rated_speed_rpm", "额定转速")
        if dim_value is None:
            dimension_label = "极数" if mode == "poles" else "额定转速"
            table_name = table.get("title", table.get("name", "表1"))
            all_tables = pack.get("tables") or [pack]
            table_index = next((index for index, item in enumerate(all_tables, start=1) if item is table), 1)

            def candidate_data_id(candidate: dict[str, Any], row_index: int) -> str:
                return str(
                    candidate.get("data_id")
                    or f"GB{('30254' if self.device_type == 'motor_hv' else '18613')}-T{table_index:02d}-R{row_index:03d}"
                )

            candidate_rows = [
                {
                    "power_kw": str(candidate.get("power_kw", "")),
                    "data_id": candidate_data_id(candidate, row_index),
                }
                for row_index, candidate in enumerate(rows, start=1)
            ]
            lookup = {
                "step_type": "精确查表",
                "table": table_name,
                "matching": "功率+极数" if mode == "poles" else "功率+转速",
                "query_conditions": {
                    "power_kw": str(power),
                    "dimension": "",
                    "dimension_name": "poles" if mode == "poles" else "speed_rpm",
                },
                "match_status": f"{dimension_label}未提供",
                "standard_rule": "标准表仅列出离散极数/转速；缺少维度时不选择最近档位、不外推",
                "candidate_count": len(candidate_rows),
                "available_dimensions": [str(item) for item in dims],
                "candidate_rows": candidate_rows,
                "data_ids": [row["data_id"] for row in candidate_rows],
                "source_clause": table_name,
                "no_interpolation": True,
            }
            source_page = table.get("source_page", "")
            if source_page in (None, "") and table is pack:
                source_page = pack.get("source_page", "")
            source_pages = table.get("source_pages", "")
            if source_page not in (None, ""):
                lookup["source_page"] = source_page
            if source_pages not in (None, ""):
                lookup["source_pages"] = source_pages
            result = _attach_metrics(
                unable(
                    str(values.get("record_id", "")),
                    pack,
                    f"缺少{dimension_label}",
                    [dimension_label],
                ),
                actual_metrics,
            )
            return _attach_lookup_trace(result, pack, table_name, [lookup])
        dimension_label = "极数" if mode == "poles" else "额定转速"
        try:
            dim_number = decimal(dim_value)
        except ValueError:
            # 输入无法解析属于数据质量问题，不能误报为标准范围外。
            # 这样手工/API输入与V4校验及其他数值字段保持同一“无法判定”契约。
            return _attach_metrics(
                unable(
                    str(values.get("record_id", "")),
                    pack,
                    f"{dimension_label}不是有效数值",
                    [dimension_label],
                ),
                actual_metrics,
            )
        try:
            dimension_values = [decimal(item) for item in dims]
        except ValueError:
            # 标准资源自身损坏或未完成复核时，不能把无效维度当成输入
            # 越界；保守终止并明确提示标准数据问题。
            return _attach_metrics(
                unable(str(values.get("record_id", "")), pack, "标准表极数或转速维度不是有效数值"),
                actual_metrics,
            )
        try:
            dim_index = dimension_values.index(dim_number)
        except ValueError:
            # 极数/转速是标准表的离散维度；未命中时不能直接丢掉
            # 已选择的表和候选记录，也不能把输入映射到最近维度。
            # 与功率未命中分支保持同一可回放证据契约。
            table_name = table.get("title", table.get("name", "表1"))
            all_tables = pack.get("tables") or [pack]
            table_index = next((index for index, item in enumerate(all_tables, start=1) if item is table), 1)
            candidate_rows = []
            data_ids = []
            for row_index, candidate in enumerate(rows, start=1):
                row_id = str(
                    candidate.get("data_id")
                    or f"GB{('30254' if self.device_type == 'motor_hv' else '18613')}-T{table_index:02d}-R{row_index:03d}-D{dim_number}"
                )
                candidate_rows.append({
                    "power_kw": str(candidate.get("power_kw", "")),
                    "data_id": row_id,
                })
                data_ids.append(row_id)
            lookup = {
                "step_type": "精确查表",
                "table": table_name,
                "matching": "功率+极数" if mode == "poles" else "功率+转速",
                "query_conditions": {
                    "power_kw": str(power),
                    "dimension": str(dim_value),
                    "dimension_name": "poles" if mode == "poles" else "speed_rpm",
                },
                "match_status": f"{dimension_label}档未命中",
                "standard_rule": "标准表仅列出离散极数/转速；禁止外推，禁止映射到最近档位",
                "candidate_count": len(candidate_rows),
                "available_dimensions": [str(item) for item in dims],
                "candidate_rows": candidate_rows,
                "data_ids": data_ids,
                "source_pages": table.get("source_pages", table.get("source_page", pack.get("source_page", ""))),
                "source_clause": table_name,
                "no_interpolation": True,
            }
            result = _attach_metrics(
                out_of_scope(
                    str(values.get("record_id", "")),
                    pack,
                    f"{dimension_label}不在标准表离散维度中，不能映射到最近档位",
                ),
                actual_metrics,
            )
            return _attach_lookup_trace(result, pack, table_name, [lookup])
        table_name = table.get("title", table.get("name", "表1"))
        all_tables = pack.get("tables") or [pack]
        table_index = next((index for index, item in enumerate(all_tables, start=1) if item is table), 1)
        try:
            low, high = bracket(rows, "power_kw", power)
        except ValueError as exc:
            def candidate_data_id(candidate: dict[str, Any], row_index: int) -> str:
                return str(
                    candidate.get("data_id")
                    or f"GB{('30254' if self.device_type == 'motor_hv' else '18613')}-T{table_index:02d}-R{row_index:03d}-D{dim_index:02d}"
                )

            raw_pages = table.get("source_pages", table.get("source_page", pack.get("source_page", "")))
            page_values = raw_pages if isinstance(raw_pages, (list, tuple)) else [raw_pages]
            source_pages = sorted({str(page) for page in page_values if page not in (None, "")})
            candidate_rows = [
                {
                    "data_id": candidate_data_id(candidate, row_index),
                    "power_kw": str(candidate.get("power_kw", "")),
                    "dimension": str(dims[dim_index]) if dim_index < len(dims) else str(dim_value),
                }
                for row_index, candidate in enumerate(rows, start=1)
            ]
            lookup = {
                "step_type": "线性插值",
                "table": table_name,
                "matching": "功率+极数" if mode == "poles" else "功率+转速",
                "query_conditions": {
                    "power_kw": str(power),
                    "dimension": str(dim_value),
                    "dimension_name": "poles" if mode == "poles" else "speed_rpm",
                },
                "match_status": "功率档未命中",
                "standard_rule": "仅标准允许的功率档内插值；禁止外推，不取最近档位",
                "interpolation_blocked": str(exc),
                "candidate_count": len(rows),
                "available_power_kw": [
                    str(candidate["power_kw"])
                    for candidate in sorted(rows, key=lambda item: decimal(item["power_kw"]))
                ],
                "candidate_rows": candidate_rows,
                "data_ids": [row["data_id"] for row in candidate_rows],
                "source_pages": source_pages,
                "source_clause": table_name,
            }
            result = _attach_metrics(
                out_of_scope(str(values.get("record_id", "")), pack, str(exc)),
                actual_metrics,
            )
            return _attach_lookup_trace(result, pack, table_name, [lookup])
        endpoint_rows = [low] if low is high else [low, high]
        row_data_ids = [
            str(
                item.get("data_id")
                or f"GB{('30254' if self.device_type == 'motor_hv' else '18613')}-T{table_index:02d}-R{next((idx for idx, candidate in enumerate(table.get('rows', []), start=1) if candidate is item), 1):03d}-D{dim_index:02d}"
            )
            for item in endpoint_rows
        ]
        lookup = {
            "step_type": "精确查表" if low is high else "线性插值",
            "table": table_name,
            "matching": "功率+极数" if mode == "poles" else "功率+转速",
            "query_conditions": {
                "power_kw": str(power),
                "dimension": str(dim_value),
                "dimension_name": "poles" if mode == "poles" else "speed_rpm",
            },
            "match_status": "命中",
            "endpoints": [low["power_kw"], high["power_kw"]],
            "factor": "0",
            "data_ids": sorted(row_data_ids),
            "data_id": sorted(row_data_ids)[0],
            "source_clause": table_name,
        }
        # 低压GB 18613-2020的来源页存放在包级source_page，高压表族
        # 则通常使用各表的source_pages；精确/插值公共记录只在确有
        # 单页来源时输出source_page，避免伪造高压表页码。
        source_page = table.get("source_page", "")
        if source_page in (None, "") and table is pack:
            source_page = pack.get("source_page", "")
        if source_page not in (None, ""):
            lookup["source_page"] = source_page
        source_pages = table.get("source_pages", "")
        if source_pages not in (None, ""):
            lookup["source_pages"] = source_pages
        thresholds, dash_levels = [], []
        # 功率插值的系数与等级无关；即使某个等级的两个端点为“—”，
        # 仍保留该系数及其他等级的查表结果，不能因第一个空档提前丢失轨迹。
        interpolation_factor = Decimal(0) if low is high else (
            power - decimal(low["power_kw"])
        ) / (decimal(high["power_kw"]) - decimal(low["power_kw"]))
        for level in ("1", "2", "3"):
            def eff(row: dict[str, Any]) -> Any:
                data = row["efficiency"][level]
                return data.get(str(dim_index), data.get(dim_index)) if isinstance(data, dict) else data[dim_index]
            if low is high:
                raw_value = eff(low)
                if raw_value is None:
                    # 标准表的“—”不等于零，也不应触发 decimal(None)；
                    # 作为该等级不作要求保留在比较轨迹中。
                    thresholds.append(None)
                    dash_levels.append(f"{level}级")
                else:
                    thresholds.append(decimal(raw_value))
            else:
                low_value, high_value = eff(low), eff(high)
                if low_value is None or high_value is None:
                    # 该等级不作要求，保留None供grade_three_optional跳过；
                    # 继续查下一个等级，以便部分等级仍可正常判定。
                    thresholds.append(None)
                    dash_levels.append(f"{level}级")
                    continue
                item, factor = linear_interpolate(power, low["power_kw"], low_value, high["power_kw"], high_value)
                thresholds.append(item)
        lookup["factor"] = str(interpolation_factor)
        if dash_levels:
            lookup.update({
                "standard_marker": "—",
                "no_data": True,
                "no_data_levels": dash_levels,
                "dash_semantics": "该等级不作要求，不参与比较",
            })
            if low is not high:
                lookup["interpolation_blocked"] = "部分功率插值端点含标准‘—/无数据’，这些等级不插值；其余等级按标准允许的功率插值处理"
        if all(item is None for item in thresholds):
            result = unable(
                str(values.get("record_id", "")),
                pack,
                "所选标准档位全部为‘—’或无数据，无法判定",
                ["额定效率"] if defer_efficiency_missing else None,
            )
            result.actual_metrics = dict(actual_metrics)
            return _attach_lookup_trace(result, pack, table_name, [lookup])
        limits = {f"{i+1}级效率_%": rounded(thresholds[i]) for i in range(3) if thresholds[i] is not None}
        if defer_efficiency_missing:
            result = unable(
                str(values.get("record_id", "")),
                pack,
                "缺少额定效率，无法进行能效等级比较",
                ["额定效率"],
            )
            result.actual_metrics = dict(actual_metrics)
            result.limits = limits
            return _attach_lookup_trace(result, pack, table_name, [lookup])
        conclusion, comparisons = grade_three_optional(actual, thresholds, ComparisonDirection.GREATER_OR_EQUAL)
        return _result(
            values,
            pack,
            conclusion,
            actual_metrics,
            {},
            limits,
            comparisons,
            table_name,
            [lookup],
            clause=table_name,
        )


class PmsmEvaluator(MotorEvaluator):
    @staticmethod
    def _pmsm_voltage_miss_lookup(
        values: dict[str, Any],
        pack: dict[str, Any],
        product: str,
        voltage: Any,
    ) -> dict[str, Any]:
        """保留PMSM离散电压未命中的全部标准表候选。

        GB 30253-2024只给出≤1140 V、3/6 kV和10 kV三组离散电压。
        额定电压已成功解析但不在这三组时，不能回退到默认低压组；
        同时仍需把被检查过的表、行ID和来源页交给结果/轨迹消费者。
        """
        candidate_tables: list[dict[str, Any]] = []
        data_ids: list[str] = []
        source_pages: set[str] = set()
        for table_index, table in enumerate(pack.get("tables") or [], start=1):
            title = str(table.get("title", table.get("name", f"表{table_index}")))
            raw_pages = table.get("pages", table.get("source_pages", table.get("source_page", [])))
            page_values = list(raw_pages) if isinstance(raw_pages, (list, tuple)) else ([raw_pages] if raw_pages not in (None, "") else [])
            rows: list[dict[str, Any]] = []
            for row_index, row in enumerate(table.get("rows", []), start=1):
                row_id = str(row.get("data_id") or f"GB30253-T{table_index:02d}-R{row_index:03d}")
                rows.append({
                    "power_rule": str(row.get("power_rule", row.get("power_kw", ""))),
                    "power_kw": str(row.get("power_kw", "")),
                    "data_id": row_id,
                })
                if row_id not in data_ids:
                    data_ids.append(row_id)
            source_pages.update(str(page) for page in page_values if page not in (None, ""))
            candidate_tables.append({
                "table_no": table_index,
                "table": title,
                "product": table.get("product", ""),
                "voltage_group": table.get("voltage_group", ""),
                "cooling_group": table.get("cooling_group", ""),
                "row_count": len(rows),
                "rows": rows,
                "source_pages": [str(page) for page in page_values if page not in (None, "")],
            })
        table_names = "/".join(f"表{item['table_no']}" for item in candidate_tables)
        return {
            "step_type": "标准表选择",
            "table": table_names,
            "matching": "产品类别+额定电压",
            "query_conditions": {
                "product": product,
                "category": str(_value(values, "category", "设备类别") or ""),
                "rated_voltage_v": str(voltage),
                "voltage_group": str(_value(values, "voltage_group", "电压组") or ""),
                "cooling_group": str(_value(values, "cooling_group", "cooling_method", "冷却方式") or ""),
            },
            "match_status": "额定电压未命中",
            "standard_rule": "GB 30253-2024仅接受≤1140 V、3kV(3.3kV)/6kV或10kV离散电压组；不将其他电压映射到最近表",
            "candidate_count": len(candidate_tables),
            "candidate_tables": candidate_tables,
            "data_ids": data_ids,
            "source_pages": sorted(source_pages),
            "source_clause": table_names,
        }

    def _pmsm_dimension_miss_lookup(
        self,
        values: dict[str, Any],
        table: dict[str, Any],
        product: str,
        power: Decimal,
        *,
        dimension_name: str = "poles",
        dimension_label: str = "极数",
        match_status: str = "极数未提供",
    ) -> dict[str, Any]:
        """保留PMSM已选标准表中缺失离散维度的全部候选。

        异步起动产品按极数、 电梯用产品按额定转速区间选择效率列。
        离散维度缺失时不能取相邻档， 但功率已经可以定位到标准行，
        因此把每个候选维度的三档标准单元和稳定记录ID完整写入一次
        查表记录，供复核端选择正确维度。
        """
        dims = list(table.get("dims", []))
        candidate_rows: list[dict[str, Any]] = []
        data_ids: list[str] = []
        source_pages: set[str] = set()
        for dim_index, dimension in enumerate(dims):
            levels: dict[str, dict[str, Any]] = {}
            row_ids: list[str] = []
            for level in ("1", "2", "3"):
                item = self._power_lookup(table, power, level, dim_index)
                if item is None:
                    levels[f"{level}级"] = {"match_status": "额定功率未命中"}
                    continue
                trace = item.get("trace", {})
                trace_list = trace if isinstance(trace, list) else [trace]
                trace_ids: list[str] = []
                for trace_item in trace_list:
                    if not isinstance(trace_item, dict):
                        continue
                    trace_id = trace_item.get("data_id")
                    if trace_id not in (None, "") and str(trace_id) not in trace_ids:
                        trace_ids.append(str(trace_id))
                    for page in trace_item.get("source_pages", []) if isinstance(trace_item.get("source_pages", []), list) else [trace_item.get("source_pages", "")]:
                        if page not in (None, ""):
                            source_pages.add(str(page))
                if not trace_ids:
                    for trace_item in trace_list:
                        if isinstance(trace_item, dict):
                            for trace_id in trace_item.get("data_ids", []) if isinstance(trace_item.get("data_ids", []), list) else []:
                                if trace_id not in (None, "") and str(trace_id) not in trace_ids:
                                    trace_ids.append(str(trace_id))
                row_ids.extend(item_id for item_id in trace_ids if item_id not in row_ids)
                for item_id in trace_ids:
                    if item_id not in data_ids:
                        data_ids.append(item_id)
                levels[f"{level}级"] = {
                    "value": None if item.get("no_data") else str(item.get("value")),
                    "data_ids": trace_ids,
                    "data_id": trace_ids[0] if trace_ids else "",
                    "no_data": bool(item.get("no_data")),
                    "standard_marker": trace.get("standard_marker", "") if isinstance(trace, dict) else "",
                }
            candidate_rows.append({
                "dimension": str(dimension),
                "levels": levels,
                "data_ids": row_ids,
            })
        raw_pages = table.get("pages", table.get("source_pages", table.get("source_page", [])))
        if not source_pages:
            page_values = raw_pages if isinstance(raw_pages, (list, tuple)) else [raw_pages]
            source_pages.update(str(page) for page in page_values if page not in (None, ""))
        table_name = table.get("table", table.get("title", table.get("name", "表1")))
        return {
            "step_type": "精确查表",
            "table": table_name,
            "matching": f"功率+{dimension_label}",
            "query_conditions": {
                "product": product,
                "rated_power_kw": str(power),
                "dimension": "",
                "dimension_name": dimension_name,
            },
            "match_status": match_status,
            "standard_rule": f"标准表按额定功率和{dimension_label}选择效率单元；缺少{dimension_label}时保留全部离散档，不取最近档、不外推",
            "candidate_count": len(candidate_rows),
            "available_dimensions": [str(item) for item in dims],
            "candidate_rows": candidate_rows,
            "data_ids": data_ids,
            "source_pages": sorted(source_pages),
            "source_clause": table_name,
            "no_nearest_dimension": True,
        }

    def _pmsm_variable_speed_miss_lookup(
        self,
        table_candidates: list[dict[str, Any]],
        product: str,
        power: Decimal,
    ) -> dict[str, Any]:
        """保留变频调速PMSM三张等级表中缺失转速的全部候选。

        变频调速产品的1～3级分别位于连续的三张表，额定转速是每张表
        的共同离散/区间轴。缺失转速时要同时保留三张表的全部区间，
        不能只返回第一张表，也不能用相邻区间代替输入。
        """
        candidate_tables: list[dict[str, Any]] = []
        data_ids: list[str] = []
        source_pages: set[str] = set()
        for table in sorted(table_candidates, key=lambda item: int(item.get("grade", 99))):
            level = str(table.get("grade", ""))
            dims = list(table.get("dims", []))
            candidate_rows: list[dict[str, Any]] = []
            table_ids: list[str] = []
            for dim_index, dimension in enumerate(dims):
                item = self._power_lookup(table, power, level, dim_index)
                trace = item.get("trace", {}) if item else {}
                trace_list = trace if isinstance(trace, list) else [trace]
                cell_ids: list[str] = []
                for trace_item in trace_list:
                    if not isinstance(trace_item, dict):
                        continue
                    trace_id = trace_item.get("data_id")
                    if trace_id not in (None, "") and str(trace_id) not in cell_ids:
                        cell_ids.append(str(trace_id))
                    nested_ids = trace_item.get("data_ids", [])
                    if isinstance(nested_ids, list):
                        for nested_id in nested_ids:
                            if nested_id not in (None, "") and str(nested_id) not in cell_ids:
                                cell_ids.append(str(nested_id))
                    pages = trace_item.get("source_pages", [])
                    pages = pages if isinstance(pages, list) else [pages]
                    source_pages.update(str(page) for page in pages if page not in (None, ""))
                table_ids.extend(item_id for item_id in cell_ids if item_id not in table_ids)
                for item_id in cell_ids:
                    if item_id not in data_ids:
                        data_ids.append(item_id)
                candidate_rows.append({
                    "dimension": str(dimension),
                    "value": None if item is None or item.get("no_data") else str(item.get("value")),
                    "data_ids": cell_ids,
                    "data_id": cell_ids[0] if cell_ids else "",
                    "no_data": bool(item and item.get("no_data")),
                    "standard_marker": trace.get("standard_marker", "") if isinstance(trace, dict) else "",
                    "match_status": "额定功率未命中" if item is None else "候选",
                })
            raw_pages = table.get("pages", table.get("source_pages", table.get("source_page", [])))
            page_values = raw_pages if isinstance(raw_pages, (list, tuple)) else [raw_pages]
            source_pages.update(str(page) for page in page_values if page not in (None, ""))
            candidate_tables.append({
                "table": table.get("table", table.get("title", table.get("name", ""))),
                "grade": level,
                "available_dimensions": [str(item) for item in dims],
                "candidate_count": len(candidate_rows),
                "candidate_rows": candidate_rows,
                "data_ids": table_ids,
                "source_pages": sorted(str(page) for page in page_values if page not in (None, "")),
            })
        table_names = "/".join(str(item["table"]) for item in candidate_tables)
        return {
            "step_type": "精确查表",
            "table": table_names,
            "matching": "功率+额定转速",
            "query_conditions": {
                "product": product,
                "rated_power_kw": str(power),
                "dimension": "",
                "dimension_name": "rated_speed_rpm",
            },
            "match_status": "额定转速未提供",
            "standard_rule": "变频调速PMSM按额定功率和额定转速区间分别查1～3级标准表；缺少额定转速时保留全部区间，不取最近档、不外推、不进行转速插值",
            "candidate_count": len(candidate_tables),
            "candidate_tables": candidate_tables,
            "data_ids": data_ids,
            "source_pages": sorted(source_pages),
            "source_clause": table_names,
            "no_nearest_dimension": True,
        }

    @staticmethod
    def _pmsm_variable_power_miss_lookup(
        table_candidates: list[dict[str, Any]],
        product: str,
        power: Decimal,
        speed: Decimal,
    ) -> dict[str, Any]:
        """保留变频调速PMSM功率未命中的三级功率轴候选。

        表8～表10的额定功率轴既有离散档，也有 ``315≤P≤1250``
        区间。目标功率不落在任一标准行时，不能取最近档或外推；但已经
        选定的三张等级表仍应把原始功率规则、稳定行ID和来源页交给结果
        /轨迹消费者，便于人工确认是低于下限、落入空档还是超过上限。
        """
        candidate_tables: list[dict[str, Any]] = []
        data_ids: list[str] = []
        source_pages: set[str] = set()
        power_boundary_candidates: list[dict[str, Any]] = []
        for table in sorted(table_candidates, key=lambda item: int(item.get("grade", 99))):
            table_no = int(table.get("table_no", 0) or 0)
            table_ids: list[str] = []
            candidate_rows: list[dict[str, Any]] = []
            for row_index, row in enumerate(table.get("rows", []), start=1):
                row_id = str(
                    row.get("data_id")
                    or f"GB30253-T{table_no:02d}-R{row_index:03d}"
                )
                power_value = row.get("power_kw")
                power_rule = row.get("power_rule")
                if power_rule in (None, ""):
                    if power_value is not None:
                        power_rule = str(power_value)
                    elif row.get("power_min_kw") is not None or row.get("power_max_kw") is not None:
                        minimum = str(row.get("power_min_kw", ""))
                        maximum = str(row.get("power_max_kw", ""))
                        power_rule = f"{minimum}≤P≤{maximum}"
                    else:
                        power_rule = ""
                item = {
                    "power_kw": "" if power_value is None else str(power_value),
                    "power_min_kw": "" if row.get("power_min_kw") is None else str(row.get("power_min_kw")),
                    "power_max_kw": "" if row.get("power_max_kw") is None else str(row.get("power_max_kw")),
                    "power_rule": str(power_rule),
                    "data_id": row_id,
                }
                if power_value is None and (row.get("power_min_kw") is not None or row.get("power_max_kw") is not None):
                    item["power_boundary"] = {
                        "min": row.get("power_min_kw"),
                        "max": row.get("power_max_kw"),
                        "min_inclusive": bool(row.get("power_min_inclusive", True)),
                        "max_inclusive": bool(row.get("power_max_inclusive", True)),
                    }
                    power_boundary_candidates.append({
                        "table": table.get("table", table.get("title", table.get("name", ""))),
                        "data_id": row_id,
                        "power_rule": str(power_rule),
                        **item["power_boundary"],
                    })
                candidate_rows.append(item)
                if row_id not in table_ids:
                    table_ids.append(row_id)
                if row_id not in data_ids:
                    data_ids.append(row_id)
            raw_pages = table.get("pages", table.get("source_pages", table.get("source_page", [])))
            page_values = raw_pages if isinstance(raw_pages, (list, tuple)) else [raw_pages]
            page_strings = [str(page) for page in page_values if page not in (None, "")]
            source_pages.update(page_strings)
            candidate_tables.append({
                "table": table.get("table", table.get("title", table.get("name", ""))),
                "grade": str(table.get("grade", "")),
                "available_power_rules": [item["power_rule"] for item in candidate_rows],
                "candidate_count": len(candidate_rows),
                "candidate_rows": candidate_rows,
                "data_ids": table_ids,
                "source_pages": page_strings,
            })
        table_names = "/".join(str(item["table"]) for item in candidate_tables)
        return {
            "step_type": "功率查表",
            "table": table_names,
            "matching": "功率+额定转速",
            "query_conditions": {
                "product": product,
                "rated_power_kw": str(power),
                "rated_speed_rpm": str(speed),
                "dimension": str(speed),
                "dimension_name": "rated_speed_rpm",
            },
            "match_status": "额定功率未命中",
            "standard_rule": "变频调速PMSM仅在标准功率档或标准功率区间内查表；功率未命中时不取最近档、不外推、不进行无端点插值",
            "candidate_count": len(candidate_tables),
            "candidate_tables": candidate_tables,
            "data_ids": data_ids,
            "source_pages": sorted(source_pages),
            "source_clause": table_names,
            "power_boundary_candidates": power_boundary_candidates,
            "no_extrapolation": True,
            "interpolation_blocked": f"目标功率不在{table_names}的标准功率档或功率区间内",
        }

    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]) -> EvaluationResult:
        if pack.get("pack_id") != "gb30253_2024_pdf_verified_v1" or pack.get("verified_table_count") != 29:
            return unable(str(values.get("record_id", "")), pack, "永磁同步电机29张表尚未全部完成PDF逐格复核")
        if result := _active_or_unable(values, pack):
            return result
        category = str(_value(values, "category", "设备类别") or "").strip()
        # GB 30253-2024表题只注册三种产品。保留历史直接API使用的
        # 短名称别名，但禁止用“异步/变频/电梯”等子串把带未知后缀的
        # 类别静默路由到标准表；未知文本必须在分类门禁处终止。
        product_aliases = {
            "异步起动": "异步起动",
            "异步起动永磁同步电动机": "异步起动",
            "异步起动三相永磁同步电动机": "异步起动",
            "变频调速": "变频调速",
            "变频调速永磁同步电动机": "变频调速",
            "电梯用": "电梯用",
            "电梯用永磁同步电动机": "电梯用",
        }
        product = product_aliases.get(category)
        if product is None:
            return unable(
                str(values.get("record_id", "")),
                pack,
                "设备类别不是GB 30253-2024规定的异步起动、变频调速或电梯用永磁同步电动机",
                ["设备类别"],
            )
        voltage = str(_value(values, "voltage_group", "电压组") or "≤1140V")
        cooling = str(_value(values, "cooling_group", "cooling_method", "冷却方式") or "通用")
        power_value = _value(values, "rated_power_kw", "额定功率")
        if power_value is None:
            return unable(str(values.get("record_id", "")), pack, "缺少额定功率", ["额定功率"])
        try:
            power = decimal(power_value)
        except ValueError:
            return unable(str(values.get("record_id", "")), pack, "额定功率不是有效数值", ["额定功率"])
        if power <= 0:
            return unable(str(values.get("record_id", "")), pack, "额定功率必须为正数", ["额定功率"])
        efficiency_field = ("efficiency_at_90pct_speed", "90%额定转速效率") if product == "变频调速" else ("rated_efficiency", "额定效率")
        actual_value = _value(values, *efficiency_field)
        if actual_value is None:
            return unable(str(values.get("record_id", "")), pack, f"缺少{efficiency_field[1]}", [efficiency_field[1]])
        try:
            actual = decimal(actual_value)
        except ValueError:
            # 标准包激活后仍需沿用公共输入契约：人工复核状态文本、
            # OCR残留文本等不得穿透到Decimal并破坏批量/API结果结构。
            return unable(str(values.get("record_id", "")), pack, f"{efficiency_field[1]}不是有效数值", [efficiency_field[1]])
        if not Decimal(1) <= actual <= Decimal(100):
            return unable(str(values.get("record_id", "")), pack, "效率应按百分数本值填写且位于1~100", [efficiency_field[1]])
        actual_metrics = {efficiency_field[1] + "_%": actual}

        def with_actual(result: EvaluationResult) -> EvaluationResult:
            _attach_metrics(result, actual_metrics)
            return result

        candidates = [table for table in pack["tables"] if table["product"] == product and table["voltage_group"] == voltage and (table["cooling_group"] == cooling or table["cooling_group"] == "通用")]
        lookups: list[dict[str, Any]] = []
        lookup_context: dict[str, str] = {
            "product": product,
            "category": category,
            "rated_voltage_v": str(_value(values, "rated_voltage_v", "额定电压", "rated_voltage") or ""),
            "voltage_group": voltage,
            "cooling_method": str(_value(values, "cooling_method", "冷却方式") or ""),
            "cooling_group": cooling,
            "rated_power_kw": str(power),
        }

        def append_lookup(trace: dict[str, Any]) -> None:
            """给每个PMSM标准单元补齐可回放的表选择上下文。"""
            trace.setdefault("matching", "产品类别+额定电压+电压组+冷却方式+额定功率")
            trace.setdefault("query_conditions", dict(lookup_context))
            trace.setdefault("match_status", "命中")
            trace.setdefault("source_clause", trace.get("table", ""))
            lookups.append(trace)

        def unable_after_lookup(reason: str, table_name: str, missing: list[str] | None = None) -> EvaluationResult:
            """终止判定时保留已经完成的查表结果和实际输入。"""
            result = unable(str(values.get("record_id", "")), pack, reason, missing)
            result.actual_metrics = dict(actual_metrics)
            return _attach_lookup_trace(result, pack, table_name, list(lookups))

        def out_of_scope_after_lookup(reason: str, table_name: str) -> EvaluationResult:
            """标准表命中“—/无数据”时，保留查表轨迹并返回范围外。"""
            result = out_of_scope(str(values.get("record_id", "")), pack, reason)
            result.actual_metrics = dict(actual_metrics)
            return _attach_lookup_trace(result, pack, table_name, list(lookups))

        voltage_out_of_scope = _value(values, "_pmsm_voltage_out_of_scope_v")
        if voltage_out_of_scope not in (None, ""):
            lookup = self._pmsm_voltage_miss_lookup(values, pack, product, voltage_out_of_scope)
            lookups.append(lookup)
            return out_of_scope_after_lookup(
                f"额定电压{voltage_out_of_scope} V不在GB 30253-2024规定的离散电压组范围，不能选择标准表",
                lookup["table"],
            )

        if product in ("异步起动", "电梯用"):
            if len(candidates) != 1:
                return with_actual(unable(str(values.get("record_id", "")), pack, "无法唯一确定永磁同步电机标准表"))
            table = candidates[0]
            if product == "异步起动":
                poles = _value(values, "poles", "极数")
                if poles is None:
                    lookup = self._pmsm_dimension_miss_lookup(values, table, product, power)
                    lookups.append(lookup)
                    return unable_after_lookup("缺少极数", table["table"], ["极数"])
                try:
                    poles_value = decimal(poles)
                except ValueError:
                    return with_actual(unable(str(values.get("record_id", "")), pack, "极数不是有效数值", ["极数"]))
                if poles_value not in [decimal(item) for item in table["dims"]]:
                    return with_actual(out_of_scope(str(values.get("record_id", "")), pack, "极数不在标准表范围"))
                dim_index = [decimal(item) for item in table["dims"]].index(poles_value)
                lookup_context["poles"] = str(poles_value)
            else:
                speed = _value(values, "rated_speed_rpm", "额定转速")
                if speed is None:
                    lookup = self._pmsm_dimension_miss_lookup(
                        values,
                        table,
                        product,
                        power,
                        dimension_name="rated_speed_rpm",
                        dimension_label="额定转速",
                        match_status="额定转速未提供",
                    )
                    lookups.append(lookup)
                    return unable_after_lookup("缺少额定转速", table["table"], ["额定转速"])
                try:
                    speed_value = decimal(speed)
                except ValueError:
                    return with_actual(unable(str(values.get("record_id", "")), pack, "额定转速不是有效数值", ["额定转速"]))
                dim_index = self._band_index(speed_value, table["dims"])
                if dim_index is None:
                    return with_actual(out_of_scope(str(values.get("record_id", "")), pack, "额定转速超出电梯电机表范围"))
                lookup_context["rated_speed_rpm"] = str(speed_value)
            matched_row = next((row for row in table["rows"] if self._row_contains(row, power)), None)
            thresholds = []
            no_data_levels: list[str] = []
            suspicious_levels: list[str] = []
            available_thresholds: dict[str, Decimal] = {}
            for level in (1, 2, 3):
                item = self._power_lookup(table, power, str(level), dim_index)
                if item is None:
                    return with_actual(out_of_scope(str(values.get("record_id", "")), pack, "额定功率超出标准表范围"))
                # 完整收集1～3级查表记录，再统一处理无数据/存疑状态，
                # 避免第一个“—”单元格提前返回而丢失后续等级的数据ID。
                append_lookup(item["trace"])
                if item.get("no_data"):
                    no_data_levels.append(f"{level}级")
                    continue
                if item.get("suspicious"):
                    suspicious_levels.append(f"{level}级")
                    continue
                thresholds.append(item["value"])
                available_thresholds[f"{level}级"] = item["value"]
            if no_data_levels:
                # “—”在标准中表示该档位不作要求。用户已确认表1/55 kW/12极
                # 三档均为“—”，该命中应明确归为“不在范围”，而不是“无法判定”。
                # 部分等级仍有数值时保留原有保守语义，避免把可比较等级误标范围外。
                if len(no_data_levels) == 3:
                    result = out_of_scope_after_lookup(
                        f"表{table['table_no']}、{power} kW、{table['dims'][dim_index]}极的{'、'.join(no_data_levels)}为标准原文‘—’（无数据），按复核结果判定为不在范围；不参与插值或等级比较",
                        table["table"],
                    )
                else:
                    result = unable_after_lookup(
                        f"表{table['table_no']}、{power} kW、{table['dims'][dim_index]}极的{'、'.join(no_data_levels)}按标准原文无数据处理",
                        table["table"],
                    )
                result.calculated_metrics["标准无数据等级"] = list(no_data_levels)
                if available_thresholds:
                    result.calculated_metrics["已查到标准等级阈值_%"] = dict(available_thresholds)
                return result
            if suspicious_levels:
                return unable_after_lookup(
                    f"表{table['table_no']}命中{'、'.join(suspicious_levels)}PDF原文存疑单元格，需人工确认",
                    table["table"],
                )
            table_name = table["table"]
        else:
            if len(candidates) != 3:
                return with_actual(unable(str(values.get("record_id", "")), pack, "变频永磁电机应唯一匹配连续三张等级表"))
            speed = _value(values, "rated_speed_rpm", "额定转速")
            if speed is None:
                lookup = self._pmsm_variable_speed_miss_lookup(candidates, product, power)
                lookups.append(lookup)
                return unable_after_lookup("缺少额定转速", lookup["table"], ["额定转速"])
            try:
                speed_value = decimal(speed)
            except ValueError:
                return with_actual(unable(str(values.get("record_id", "")), pack, "额定转速不是有效数值", ["额定转速"]))
            if any(
                not any(self._row_contains(row, power) for row in table.get("rows", []))
                for table in candidates
            ):
                lookup = self._pmsm_variable_power_miss_lookup(candidates, product, power, speed_value)
                lookups.append(lookup)
                return out_of_scope_after_lookup(
                    f"额定功率不在{lookup['table']}标准功率档或功率区间内，且禁止外推",
                    lookup["table"],
                )
            thresholds = []
            no_data_tables: list[dict[str, Any]] = []
            suspicious_tables: list[dict[str, Any]] = []
            for level in (1, 2, 3):
                table = next(item for item in candidates if item.get("grade") == level)
                speed_lookup = self._speed_lookup(table, power, speed_value, str(level))
                if speed_lookup is None:
                    return with_actual(out_of_scope(str(values.get("record_id", "")), pack, "功率或转速超出标准表，且禁止外推"))
                if speed_lookup.get("no_data"):
                    for trace in speed_lookup.get("trace", []):
                        append_lookup(trace)
                    no_data_tables.append(table)
                    continue
                if speed_lookup.get("suspicious"):
                    # 存疑单元格同样是已完成的查表结果；先保留其端点/数据ID，
                    # 再在循环结束后统一返回，避免跨端消费者失去复核依据。
                    for trace in speed_lookup.get("trace", []):
                        append_lookup(trace)
                    suspicious_tables.append(table)
                    continue
                thresholds.append(speed_lookup["value"])
                for trace in speed_lookup["trace"]:
                    append_lookup(trace)
            if no_data_tables:
                table = no_data_tables[0]
                if len(no_data_tables) == 3:
                    result = out_of_scope_after_lookup(
                        f"表{table['table_no']}、{power} kW对应转速档的1级、2级、3级为标准原文‘—’（无数据），按复核结果判定为不在范围；不参与插值或等级比较",
                        table["table"],
                    )
                    result.calculated_metrics["标准无数据等级"] = [f"{item['grade']}级" for item in no_data_tables]
                    return result
                return unable_after_lookup(
                    f"表{table['table_no']}、{power} kW对应转速档按标准原文无数据处理",
                    table["table"],
                )
            if suspicious_tables:
                table = suspicious_tables[0]
                return unable_after_lookup(
                    f"{table['table']}命中PDF原文存疑单元格，需人工确认",
                    table["table"],
                )
            table_name = "/".join(item["table"] for item in sorted(candidates, key=lambda item: item["grade"]))
        conclusion, comparisons = grade_three(actual, thresholds, ComparisonDirection.GREATER_OR_EQUAL)
        return _result(
            values,
            pack,
            conclusion,
            actual_metrics,
            {},
            {f"{idx+1}级效率_%": rounded(value) for idx, value in enumerate(thresholds)},
            comparisons,
            table_name,
            lookups,
            clause=table_name,
        )

    @staticmethod
    def _band_index(speed: Decimal, bands: list[str]) -> int | None:
        for index, band in enumerate(bands):
            if _interval_hit(speed, band):
                return index
        return None

    @staticmethod
    def _row_contains(row: dict[str, Any], power: Decimal) -> bool:
        if row.get("power_kw") is not None:
            return decimal(row["power_kw"]) == power
        minimum = decimal(row["power_min_kw"])
        maximum = decimal(row["power_max_kw"]) if row.get("power_max_kw") is not None else None
        lower_ok = power >= minimum if row.get("power_min_inclusive", True) else power > minimum
        return lower_ok and (maximum is None or power <= maximum)

    def _power_lookup(self, table: dict[str, Any], power: Decimal, level: str, dim_index: int) -> dict[str, Any] | None:
        rows = table["rows"]
        contained = next((row for row in rows if self._row_contains(row, power)), None)
        flat_index = (int(level) - 1) * len(table["dims"]) + dim_index if table["table_no"] <= 7 or table["table_no"] == 29 else dim_index
        table_no = str(table.get("table_no", "")).zfill(2)
        raw_pages = table.get("pages", table.get("source_pages", table.get("source_page", [])))
        source_pages = list(raw_pages) if isinstance(raw_pages, (list, tuple)) else ([raw_pages] if raw_pages not in (None, "") else [])

        def data_id(row: dict[str, Any]) -> str:
            row_index = next((index for index, candidate in enumerate(rows, start=1) if candidate is row), 0)
            return f"GB30253-T{table_no}-R{row_index:03d}-D{dim_index:02d}-L{int(level):02d}"

        if contained:
            value = contained["efficiency"][level][dim_index]
            standard_id = data_id(contained)
            if value is None:
                # 已人工复核的PDF表中，空单元格对应原文“—”。历史包只
                # 对用户特别确认的三格登记了 ``no_data_cells``，不能因此
                # 把同一张表中其他已复核的“—”误报成“功率超出范围”，
                # 也不能丢掉该等级的 data_id 和原文标记。
                explicitly_marked = flat_index in contained.get("no_data_cells", [])
                return {
                    "value": None,
                    "no_data": True,
                    "suspicious": False,
                    "trace": {
                        "step_type": "精确查表/区间查表",
                        "table": table["table"],
                        "power_rule": contained.get("power_rule", str(power)),
                        "dim": table["dims"][dim_index],
                        "level": level,
                        "data_id": standard_id,
                        "source_pages": source_pages,
                        "standard_marker": "—",
                        "no_data": True,
                        "no_data_reason": "标准原文‘—’（该等级不作要求），不得按0参与比较或插值",
                        "explicit_no_data_registration": explicitly_marked,
                    },
                }
            trace = {
                "step_type": "精确查表/区间查表",
                "table": table["table"],
                "power_rule": contained.get("power_rule", str(power)),
                "dim": table["dims"][dim_index],
                "level": level,
                "data_id": standard_id,
                "source_pages": source_pages,
            }
            if contained.get("power_kw") is None and (
                contained.get("power_min_kw") is not None
                or contained.get("power_max_kw") is not None
            ):
                trace["power_boundary"] = {
                    "min": contained.get("power_min_kw"),
                    "max": contained.get("power_max_kw"),
                    "min_inclusive": bool(contained.get("power_min_inclusive", True)),
                    "max_inclusive": bool(contained.get("power_max_inclusive", True)),
                }
            return {
                "value": decimal(value),
                "no_data": False,
                "suspicious": flat_index in contained.get("suspicious_cells", []),
                "trace": trace,
            }
        exact_rows = [row for row in rows if row.get("power_kw") is not None]
        try:
            low, high = bracket(exact_rows, "power_kw", power)
        except ValueError:
            return None
        low_value, high_value = low["efficiency"][level][dim_index], high["efficiency"][level][dim_index]
        if low_value is None or high_value is None:
            # 与精确命中一致，任一功率端点为标准原文“—”时禁止
            # 插值；即使该端点没有单独登记 no_data_cells，也要保留
            # 两端 data_id、原文标记和禁止原因。
            low_marked = low_value is None and flat_index in low.get("no_data_cells", [])
            high_marked = high_value is None and flat_index in high.get("no_data_cells", [])
            return {
                "value": None,
                "no_data": True,
                "suspicious": False,
                "trace": {
                    "step_type": "功率线性插值",
                    "table": table["table"],
                    "endpoints": [low["power_kw"], high["power_kw"]],
                    "dim": table["dims"][dim_index],
                    "level": level,
                    "data_ids": [data_id(low), data_id(high)],
                    "source_pages": source_pages,
                    "standard_marker": "—",
                    "no_data": True,
                    "no_data_reason": "功率插值端点含标准原文‘—’（该等级不作要求），不得按0参与插值",
                    "explicit_no_data_registration": low_marked or high_marked,
                    "interpolation_blocked": "标准‘—’端点不得插值",
                },
            }
        value, factor = linear_interpolate(power, low["power_kw"], low_value, high["power_kw"], high_value)
        suspicious = flat_index in low.get("suspicious_cells", []) or flat_index in high.get("suspicious_cells", [])
        endpoint_ids = [data_id(low), data_id(high)]
        return {"value": value, "no_data": False, "suspicious": suspicious, "trace": {"step_type": "功率线性插值", "table": table["table"], "endpoints": [low["power_kw"], high["power_kw"]], "factor": str(factor), "dim": table["dims"][dim_index], "level": level, "data_ids": endpoint_ids, "data_id": endpoint_ids[0], "source_pages": source_pages}}

    def _speed_lookup(self, table: dict[str, Any], power: Decimal, speed: Decimal, level: str) -> dict[str, Any] | None:
        dims = table["dims"]
        categorical = self._band_index(speed, [item for item in dims if any(symbol in str(item) for symbol in (">", "<", "≤", "~"))])
        if categorical is not None:
            result = self._power_lookup(table, power, level, categorical)
            return None if result is None else {"value": result["value"], "no_data": result.get("no_data", False), "suspicious": result["suspicious"], "trace": [result["trace"]]}
        numeric = [(index, decimal(item)) for index, item in enumerate(dims) if str(item).replace(".", "", 1).isdigit()]
        exact = next(((index, value) for index, value in numeric if value == speed), None)
        if exact:
            result = self._power_lookup(table, power, level, exact[0])
            return None if result is None else {"value": result["value"], "no_data": result.get("no_data", False), "suspicious": result["suspicious"], "trace": [result["trace"]]}
        lower = sorted((item for item in numeric if item[1] < speed), key=lambda item: item[1])
        upper = sorted((item for item in numeric if item[1] > speed), key=lambda item: item[1])
        if not lower or not upper:
            return None
        left, right = lower[-1], upper[0]
        low_result, high_result = self._power_lookup(table, power, level, left[0]), self._power_lookup(table, power, level, right[0])
        if low_result is None or high_result is None:
            return None
        # 标准表中的“—/无数据”不是0，也不能参与转速插值。若任一
        # 插值端点登记为无数据，沿用与精确查表相同的保守语义，并保留
        # 两个端点的追溯信息，供上层返回“无法判定”及判定轨迹。
        if low_result.get("no_data") or high_result.get("no_data"):
            return {
                "value": None,
                "no_data": True,
                "suspicious": False,
                "trace": [
                    low_result["trace"],
                    high_result["trace"],
                    {
                        "step_type": "转速线性插值",
                        "table": table["table"],
                        "endpoints": [str(left[1]), str(right[1])],
                        "no_data": True,
                    },
                ],
            }
        value, factor = linear_interpolate(speed, left[1], low_result["value"], right[1], high_result["value"])
        trace = [low_result["trace"], high_result["trace"], {"step_type": "转速线性插值", "table": table["table"], "endpoints": [str(left[1]), str(right[1])], "factor": str(factor), "source_pages": table.get("pages", table.get("source_pages", table.get("source_page", [])))}]
        return {"value": value, "suspicious": low_result["suspicious"] or high_result["suspicious"], "trace": trace}
