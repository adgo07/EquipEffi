"""热泵、冷水机组及空调产品评价器。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ...common.enums import ComparisonDirection, Conclusion
from ...common.models import EvaluationResult


def _metric_name_key(value: Any) -> str:
    """Return a stable comparison key for a user-entered HVAC metric name."""

    return (
        str(value or "")
        .strip()
        .upper()
        .replace("（", "(")
        .replace("）", ")")
        .replace(" ", "")
    )


class HvacEvaluator:
    def __init__(self, device_type: str, five_levels: bool = False):
        self.device_type, self.five_levels = device_type, five_levels

    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]) -> EvaluationResult:
        from ..device_evaluators import (
            _active_or_unable,
            _attach_metrics,
            _attach_lookup_trace,
            _record_matches,
            _condition_matches,
            _result,
            _value,
            compare,
            out_of_scope,
            unable,
        )
        from ..decimal_math import decimal

        standard_info = {
            "heat_pump_chiller": ("GB 19577-2024", "热泵和冷水机组能效限定值及能效等级"),
            "heat_pump_water_heater": ("GB 29541-2013", "热泵热水机（器）能效限定值及能效等级"),
            "duct_ac": ("GB 37479-2019", "风管送风式空调机组能效限定值及能效等级"),
            "unitary_ac": ("GB 19576-2019", "单元式空气调节机能效限定值及能效等级"),
            "multi_split_ac": ("GB 21454-2021", "多联式空调（热泵）机组能效限定值及能效等级"),
        }[self.device_type]
        effective_pack = {**pack, "standard_code": standard_info[0], "standard_name": standard_info[1]}
        if result := _active_or_unable(values, effective_pack):
            return result
        if self.device_type == "heat_pump_chiller":
            cooling_capacity = _value(values, "cooling_capacity_kw", "cooling_capacity")
            heating_capacity = _value(values, "heating_capacity_kw", "heating_capacity")
            if cooling_capacity is None and heating_capacity is None:
                return unable(
                    str(values.get("record_id", "")),
                    effective_pack,
                    "热泵和冷水机组至少需要名义制冷量或名义制热量",
                    ["名义制冷量或名义制热量"],
                )
        section = pack.get("devices", {}).get(self.device_type, {})
        all_records = list(section.get("records", []) or [])
        records = [record for record in all_records if _record_matches(record, values)]

        def condition_only_match(record: dict[str, Any]) -> bool:
            """Match product axes while deliberately ignoring the range axis.

            A product condition can be valid while its numeric capacity falls
            outside every standard row.  Keeping this distinction lets the
            evaluator return the required ``不在范围`` conclusion instead of
            treating a clear range miss as an unexplained lookup failure.
            """

            for key, expected in (record.get("conditions", {}) or {}).items():
                actual = _value(values, key, record.get("condition_aliases", {}).get(key, key))
                if not _condition_matches(key, actual, expected):
                    return False
            return True

        condition_candidates = [record for record in all_records if condition_only_match(record)]

        def record_summary(record: dict[str, Any]) -> dict[str, Any]:
            """把标准候选行压缩成可跨端展示的查表证据。"""

            return {
                "data_id": record.get("data_id", ""),
                "table": record.get("table", ""),
                "conditions": dict(record.get("conditions", {}) or {}),
                "range_metric": record.get("range_metric", ""),
                "min": record.get("min"),
                "max": record.get("max"),
                "min_inclusive": record.get("min_inclusive", True),
                "max_inclusive": record.get("max_inclusive", True),
                "metric_name": record.get("metric_name", ""),
                "source_page": record.get("source_page", ""),
                "source_clause": record.get("source_clause") or record.get("table", ""),
            }

        def unmatched_lookup(
            source_records: list[dict[str, Any]] | None = None,
            match_status: str | None = None,
        ) -> dict[str, Any]:
            source_records = all_records if source_records is None else source_records
            candidate_records = [record_summary(record) for record in source_records]
            table_names = list(dict.fromkeys(str(item.get("table", "")) for item in candidate_records if item.get("table")))
            clauses = list(dict.fromkeys(str(item.get("source_clause", "")) for item in candidate_records if item.get("source_clause")))
            query_fields = set()
            for candidate in all_records:
                query_fields.update((candidate.get("conditions") or {}).keys())
                if candidate.get("range_metric"):
                    query_fields.add(candidate["range_metric"])
            input_values = {key: str(_value(values, key) or "") for key in sorted(query_fields)}
            return {
                "step_type": "精确查表",
                "table": "/".join(table_names),
                "data_id": f"{standard_info[0].replace(' ', '').replace('-', '')}-{self.device_type}-MATCH-MISS",
                "matching": "产品型式+容量档+标准指标",
                "input_values": input_values,
                "candidate_records": candidate_records,
                "candidate_data_ids": [item["data_id"] for item in candidate_records if item.get("data_id")],
                "candidate_count": len(candidate_records),
                "match_status": match_status or ("多重命中" if len(records) > 1 else "未命中"),
                "source_pages": list(dict.fromkeys(str(item.get("source_page", "")) for item in candidate_records if item.get("source_page"))),
                "source_clause": "、".join(clauses),
                "no_interpolation": True,
            }

        def lookup_query_conditions(record: dict[str, Any]) -> dict[str, str]:
            """Preserve the values used to select a unique HVAC standard row.

            The standard row matcher accepts a small set of input aliases (for
            example ``heating_capacity`` for ``heating_capacity_kw``).  The
            lookup evidence should expose the canonical standard axis while
            still recording the caller's value, so a later report can explain
            exactly why this row was selected.  Design indicator values remain
            in ``actual_metrics``/``comparisons``; this mapping is limited to
            product conditions and the capacity range axis.
            """

            query_conditions: dict[str, str] = {}
            condition_aliases = record.get("condition_aliases", {}) or {}
            keys = list((record.get("conditions", {}) or {}).keys())
            range_metric = record.get("range_metric")
            if range_metric and range_metric not in keys:
                keys.append(range_metric)
            for key in keys:
                aliases = [key]
                alias = condition_aliases.get(key)
                if alias and alias not in aliases:
                    aliases.append(alias)
                # V4/API inputs commonly omit the ``_kw`` suffix while the
                # standard resource keeps units in its canonical field name.
                if key.endswith("_kw"):
                    short_key = key[:-3]
                    if short_key not in aliases:
                        aliases.append(short_key)
                value = _value(values, *aliases)
                query_conditions[key] = "" if value is None else str(value)
            return query_conditions

        def provided_metric_context() -> dict[str, Any]:
            """保留冲突早退前用户填写的动态设计指标。"""

            metrics: dict[str, Any] = {}
            for name_key, value_key in (
                ("indicator_name", "indicator_value"),
                ("indicator1_name", "indicator1_value"),
                ("indicator2_name", "indicator2_value"),
                ("indicator3_name", "indicator3_value"),
            ):
                name = _value(values, name_key)
                value = _value(values, value_key)
                if name not in (None, "") and value not in (None, ""):
                    metrics[str(name)] = value
            return metrics

        # GB 19576-2019表1把普通单元式空调机按风冷式/水冷式拆成
        # 不同标准行。完整类别已经含有冷却方式时，独立填写的冷却方式
        # 必须与之相同；冲突不能让过滤器只看category而静默判级。
        # 这里保留全部标准候选行，便于填表人员校对应选择的类别。
        if self.device_type == "unitary_ac":
            category_text = str(_value(values, "category", "product_type") or "").strip()
            cooling_text = str(_value(values, "cooling_source", "cooling") or "").strip()
            category_cooling = None
            if "风冷式" in category_text and "单元式空调机" in category_text:
                category_cooling = "风冷式"
            elif "水冷式" in category_text and "单元式空调机" in category_text:
                category_cooling = "水冷式"
            if category_cooling and cooling_text and category_cooling != cooling_text:
                lookup = unmatched_lookup()
                lookup.update({
                    "match_status": "类别与冷却方式冲突",
                    "conflict_fields": ["category", "cooling_source"],
                    "conflict_values": {
                        "category": category_text,
                        "category_cooling": category_cooling,
                        "cooling_source": cooling_text,
                    },
                    "no_interpolation": True,
                })
                result = unable(
                    str(values.get("record_id", "")),
                    effective_pack,
                    f"设备类别中的{category_cooling}与冷却方式{cooling_text}冲突，无法唯一匹配标准行",
                    ["设备类别/冷却方式"],
                )
                _attach_metrics(result, provided_metric_context())
                return _attach_lookup_trace(result, effective_pack, lookup["table"], [lookup])

        if len(records) != 1:
            # 产品条件已经唯一/明确命中，但容量没有落入任何标准档位时，
            # 这是标准适用范围外，而不是“无法唯一匹配”。只有在容量为
            # 有效数值且所有候选共享同一容量轴时才走该早退，避免把缺失、
            # 非法容量或条件冲突误判成不在范围。
            range_metrics = {
                str(record.get("range_metric"))
                for record in condition_candidates
                if record.get("range_metric")
            }
            if not records and len(range_metrics) == 1:
                range_metric = next(iter(range_metrics))
                range_value = _value(values, range_metric)
                if range_value is not None:
                    try:
                        range_number = decimal(range_value)
                    except ValueError:
                        range_number = None
                    if range_number is not None:
                        lookup = unmatched_lookup(condition_candidates, "容量超出标准范围")
                        lookup.update({
                            "range_metric": range_metric,
                            "input_range_value": str(range_value),
                            "capacity_boundary_candidates": [
                                {
                                    "data_id": record.get("data_id", ""),
                                    "min": record.get("min"),
                                    "max": record.get("max"),
                                    "min_inclusive": record.get("min_inclusive", True),
                                    "max_inclusive": record.get("max_inclusive", True),
                                }
                                for record in condition_candidates
                            ],
                            "no_interpolation": True,
                        })
                        reason = (
                            f"{range_metric}={range_value}未落入已匹配产品条件的标准容量区间，"
                            "按标准适用范围判定为不在范围"
                        )
                        result = out_of_scope(str(values.get("record_id", "")), effective_pack, reason)
                        return _attach_lookup_trace(result, effective_pack, lookup["table"], [lookup])
            result = unable(str(values.get("record_id", "")), effective_pack, "无法唯一匹配产品型式、容量档和标准指标")
            lookup = unmatched_lookup()
            return _attach_lookup_trace(result, effective_pack, lookup["table"], [lookup])
        record = records[0]
        fixed_gate_definitions = []
        for gate in record.get("fixed_gates", []) or []:
            gate_definition = {
                "field": gate.get("field", ""),
                "name": gate.get("name", ""),
                "direction": gate.get("direction", ">="),
            }
            for key in ("threshold", "thresholds", "levels"):
                if key in gate:
                    gate_definition[key] = gate[key]
            fixed_gate_definitions.append(gate_definition)

        def capacity_band_text() -> str:
            """Return the standard capacity interval for early-return evidence."""

            range_metric = record.get("range_metric")
            if not range_metric:
                return ""
            minimum = record.get("min")
            maximum = record.get("max")
            if minimum is not None and maximum is not None:
                minimum_operator = "<=" if record.get("min_inclusive", True) else "<"
                maximum_operator = "<=" if record.get("max_inclusive", True) else "<"
                return f"{minimum}{minimum_operator}{range_metric}{maximum_operator}{maximum}"
            if maximum is not None:
                return f"{range_metric}<={maximum}"
            if minimum is not None:
                minimum_operator = ">=" if record.get("min_inclusive", True) else ">"
                return f"{range_metric}{minimum_operator}{minimum}"
            return ""

        def capacity_boundary_context() -> dict[str, Any]:
            """Return machine-readable capacity interval evidence.

            The compact ``capacity_band`` text is convenient in reports, but it
            cannot reliably be parsed by downstream clients (especially when a
            standard uses an open lower bound such as ``>14 000 W``).  Keep the
            original numeric endpoints and their inclusivity flags alongside
            that text so every lookup can be audited without reloading the
            standard record.
            """

            range_metric = record.get("range_metric")
            if not range_metric:
                return {}
            return {
                "metric": range_metric,
                "min": record.get("min"),
                "max": record.get("max"),
                "min_inclusive": bool(record.get("min_inclusive", True)),
                "max_inclusive": bool(record.get("max_inclusive", True)),
            }

        record_lookup = {
            "step_type": "精确查表",
            "table": record["table"],
            "data_id": record.get("data_id"),
            "matching": record.get("condition_text", "产品型式+容量档"),
            "query_conditions": lookup_query_conditions(record),
            "source_page": record.get("source_page", ""),
            "source_clause": record.get("source_clause") or record.get("table", ""),
            "match_status": "命中",
            "metric_name": record.get("metric_name", ""),
            "thresholds": list(record.get("thresholds", ()) or ()),
            # 固定门槛的定义也属于查表结果。最终按等级展开后的门槛
            # 会在下面的gate_level_thresholds中回填，便于跨端消费者
            # 不解析设备专属算法就能复核AND逻辑。
            "fixed_gates": fixed_gate_definitions,
            "comparison_channels": [record.get("metric_name", "")] + [
                gate.get("name", "") for gate in fixed_gate_definitions if gate.get("name")
            ],
            # 固定门槛与主分级指标在同一等级按AND组合；没有固定门槛
            # 时明确记录为单指标，避免跨端消费者从数组位置猜逻辑。
            "comparison_logic": {
                "operator": "AND" if fixed_gate_definitions else "SINGLE",
                "primary_metric": record.get("metric_name", ""),
                "fixed_gate_metrics": [
                    gate.get("name", "") for gate in fixed_gate_definitions if gate.get("name")
                ],
            },
            # 在主指标缺失/非法等早退路径上也必须保留已命中的
            # 容量区间，避免结果只剩一个data_id而无法复核档位。
            "capacity_band": capacity_band_text(),
            "capacity_boundary": capacity_boundary_context(),
        }
        # 动态指标名称是标准通道的一部分，必须在唯一命中标准行后
        # 按主指标+固定门槛的顺序逐一核对。否则规范化层可能把错误
        # 的indicator值复制到通用字段，导致多联机的辅助通道只显示
        # “缺少门槛”，却没有指出用户实际填写了错误指标。
        expected_metric_names = [str(record.get("metric_name", ""))] + [
            str(gate.get("name", ""))
            for gate in fixed_gate_definitions
            if gate.get("name")
        ]
        provided_metrics: list[dict[str, Any]] = []
        for position, name_key, value_key in (
            (0, "indicator_name", "indicator_value"),
            (0, "indicator1_name", "indicator1_value"),
            (1, "indicator2_name", "indicator2_value"),
            (2, "indicator3_name", "indicator3_value"),
        ):
            name = _value(values, name_key)
            if name is None:
                continue
            provided_metrics.append({
                "position": position,
                "name": str(name),
                "value": _value(values, value_key),
                "name_field": name_key,
                "value_field": value_key,
            })
        for provided in provided_metrics:
            position = int(provided["position"])
            expected_name = expected_metric_names[position] if position < len(expected_metric_names) else ""
            if not expected_name or _metric_name_key(provided["name"]) != _metric_name_key(expected_name):
                record_lookup.update({
                    "provided_metrics": provided_metrics,
                    "provided_metric_name": provided["name"],
                    "provided_metric_value": provided["value"],
                    "expected_metric_name": expected_name,
                    "indicator_position": position + 1,
                    "match_status": "设计指标名称不匹配",
                })
                reason = (
                    f"indicator{position + 1}填写的设计指标{provided['name']}"
                    f"与标准要求的{expected_name or '当前产品不适用指标'}不一致"
                )
                missing = [expected_name] if expected_name else []
                result = unable(str(values.get("record_id", "")), effective_pack, reason, missing)
                actual_metrics = {
                    item["name"]: item["value"]
                    for item in provided_metrics
                    if item.get("value") is not None
                }
                _attach_metrics(result, actual_metrics)
                return _attach_lookup_trace(result, effective_pack, record["table"], [record_lookup])
        actual = _value(values, record["metric_field"], record.get("metric_name", ""), "primary_metric_value")
        if actual is None:
            # 与非法/非正设计值分支保持同一证据契约：即使主指标
            # 完全缺失，也明确记录标准要求的指标名称和缺失状态，
            # 让跨端消费者无需从missing_fields反推查表结果。
            record_lookup.update({
                "provided_metric_name": record["metric_name"],
                "provided_metric_value": None,
                "match_status": "设计指标缺失",
            })
            result = unable(str(values.get("record_id", "")), effective_pack, f"缺少{record['metric_name']}设计值", [record["metric_name"]])
            return _attach_lookup_trace(result, effective_pack, record["table"], [record_lookup])
        try:
            if decimal(actual) <= 0:
                # 非正设计值不能作为数值指标参与比较，但仍要把原始
                # 值留在lookup中，便于跨端区分“缺失”和“填了0/负数”。
                record_lookup.update({
                    "provided_metric_name": record["metric_name"],
                    "provided_metric_value": actual,
                    "match_status": "设计指标数值非正",
                })
                result = unable(str(values.get("record_id", "")), effective_pack, f"{record['metric_name']}设计值必须大于0", [record["metric_name"]])
                return _attach_lookup_trace(result, effective_pack, record["table"], [record_lookup])
        except ValueError:
            # 非法设计值不能写入actual_metrics作为数值，但原始文本
            # 必须留在查表证据中，便于跨端报告指出具体输入问题。
            record_lookup.update({
                "provided_metric_name": record["metric_name"],
                "provided_metric_value": actual,
                "match_status": "设计指标数值无效",
            })
            result = unable(str(values.get("record_id", "")), effective_pack, f"{record['metric_name']}设计值不是有效数值", [record["metric_name"]])
            return _attach_lookup_trace(result, effective_pack, record["table"], [record_lookup])
        actual = decimal(actual)
        calculated_metrics: dict[str, Any] = {}
        correction_lookup: dict[str, Any] | None = None
        # 标准记录已唯一匹配且主指标已经解析；后续静压修正或固定门槛
        # 早退时也要保留这个实际/标称设计值，不能因为尚未形成最终
        # 分级结果而丢失输入上下文。
        actual_metrics_context: dict[str, Any] = {record["metric_name"]: actual}

        def with_context(result: EvaluationResult) -> EvaluationResult:
            _attach_metrics(result, actual_metrics_context, calculated_metrics)
            # 早退也必须保留已经唯一匹配的标准行；静压修正（如有）放在
            # 主表查表之前，顺序与正常路径保持一致。
            lookup_steps: list[dict[str, Any]] = []
            if correction_lookup is not None:
                lookup_steps.append(dict(correction_lookup))
            lookup_steps.append(dict(record_lookup))
            return _attach_lookup_trace(result, effective_pack, record["table"], lookup_steps)

        # GB 21454-2021第4.2～4.5要求不同静压机组按GB/T 18837/18836
        # 的方法修正能源效率。标准引用的是内部阻力试验/修正参数，不能用经验常数替代。
        # 因此API允许上游测试/设计计算模块传入修正后指标，或传入经标准试验得到的
        # 无量纲修正系数；仅有静压而无修正结果时保守返回无法判定，避免把未修正值误判。
        if self.device_type == "multi_split_ac":
            static_value = _value(values, "external_static_pressure_pa", "external_static")
            if static_value is not None:
                try:
                    static_value = decimal(static_value)
                except ValueError:
                    return with_context(unable(str(values.get("record_id", "")), effective_pack, "机外静压不是有效数值", ["机外静压"]))
                if static_value < 0:
                    return with_context(out_of_scope(str(values.get("record_id", "")), effective_pack, "机外静压不得为负数"))
                corrected_present = _value(values, "static_pressure_corrected_metric", "corrected_metric_value") is not None
                factor_present = _value(values, "static_pressure_correction_factor", "energy_efficiency_correction_factor") is not None
                if corrected_present and factor_present:
                    return with_context(unable(str(values.get("record_id", "")), effective_pack, "静压修正后指标和修正系数只能填写一项", ["静压修正后指标/修正系数"]))
                if (corrected_present or factor_present) and static_value <= 0:
                    return with_context(unable(str(values.get("record_id", "")), effective_pack, "填写静压修正结果时机外静压必须大于0", ["机外静压"]))
                if static_value > 0:
                    corrected = _value(values, "static_pressure_corrected_metric", "corrected_metric_value")
                    factor = _value(values, "static_pressure_correction_factor", "energy_efficiency_correction_factor")
                    if corrected is not None:
                        try:
                            corrected = decimal(corrected)
                        except ValueError:
                            return with_context(unable(str(values.get("record_id", "")), effective_pack, "静压修正后指标不是有效数值", ["静压修正后指标"]))
                        if corrected <= 0:
                            return with_context(unable(str(values.get("record_id", "")), effective_pack, "静压修正后指标必须大于0", ["静压修正后指标"]))
                        calculated_metrics["静压修正前指标"] = actual
                        calculated_metrics["静压修正后指标"] = corrected
                        actual = corrected
                        actual_metrics_context[record["metric_name"]] = actual
                        correction_lookup = {
                            "step_type": "静压修正",
                            "method": "GB/T 18837-2015或GB/T 18836-2017规定的内部阻力试验/修正参数",
                            "source_standards": ["GB/T 18837-2015", "GB/T 18836-2017"],
                            "source_clause": "引用标准规定的内部阻力试验/修正参数（具体条款由上游提供）",
                            "requires_upstream_evidence": True,
                            "external_static_pressure_pa": str(static_value),
                            "input_metric": str(calculated_metrics["静压修正前指标"]),
                            "corrected_metric": str(corrected),
                        }
                    elif factor is not None:
                        try:
                            factor = decimal(factor)
                        except ValueError:
                            return with_context(unable(str(values.get("record_id", "")), effective_pack, "静压修正系数不是有效数值", ["静压修正系数"]))
                        if factor <= 0:
                            return with_context(unable(str(values.get("record_id", "")), effective_pack, "静压修正系数必须大于0", ["静压修正系数"]))
                        calculated_metrics["静压修正前指标"] = actual
                        calculated_metrics["静压修正系数"] = factor
                        actual = actual * factor
                        calculated_metrics["静压修正后指标"] = actual
                        actual_metrics_context[record["metric_name"]] = actual
                        correction_lookup = {
                            "step_type": "静压修正",
                            "method": "上游按GB/T 18837-2015或GB/T 18836-2017取得的修正系数",
                            "source_standards": ["GB/T 18837-2015", "GB/T 18836-2017"],
                            "source_clause": "引用标准规定的内部阻力试验/修正参数（具体条款由上游提供）",
                            "requires_upstream_evidence": True,
                            "external_static_pressure_pa": str(static_value),
                            "input_metric": str(calculated_metrics["静压修正前指标"]),
                            "factor": str(factor),
                            "corrected_metric": str(actual),
                        }
                    else:
                        return with_context(unable(str(values.get("record_id", "")), effective_pack, "机外静压大于0，缺少按引用标准取得的静压修正后指标或修正系数", ["静压修正后指标"]))
        level_count = 5 if self.five_levels else 3
        thresholds = list(record.get("thresholds", ()))
        if len(thresholds) != level_count:
            return with_context(unable(str(values.get("record_id", "")), effective_pack, "标准分级阈值数量不正确"))
        direction = ComparisonDirection(record.get("direction", ">="))
        gate_actual_metrics: dict[str, Any] = {}
        gate_missing: dict[str, str] = {}
        gate_invalid: dict[str, str] = {}
        gate_results: list[dict[str, Any]] = []
        gate_level_thresholds: dict[str, list[Any]] = {}
        gate_directions: dict[str, ComparisonDirection] = {}
        for gate_index, gate in enumerate(record.get("fixed_gates", []), start=1):
            gate_aliases = {
                "eer": ("eer_min_value",),
                "cop_minus_12": ("cop_minus12", "cop_minus12_value"),
                "cop_minus_20": ("cop_minus20", "cop_minus20_value"),
                # 表2的双通道评价把另一套综合指标作为3级固定门槛。
                # 既接受明确的alternate_metric_value，也兼容动态指标
                # 名称映射后的CSPF/IPLV/ACCOP字段和V4辅助指标1。
                "alternate_metric_value": (
                    "alternate_metric",
                    "alternate_metric_design_value",
                    "cspf",
                    "iplv",
                    "iplv_c",
                    "accop",
                ),
            }
            gate_actual = _value(values, gate["field"], *gate_aliases.get(gate["field"], ()))
            # GB 19577-2024的V4表单把标准固定门槛统一暴露为
            # “辅助约束指标1/2设计值”；按标准记录中的门槛顺序映射，
            # 不猜测指标含义，也不设置默认值。
            if gate_actual is None:
                gate_actual = _value(values, f"aux_metric{gate_index}_value")
            gate_actual_number: Decimal | None = None
            if gate_actual is None:
                gate_missing[gate["name"]] = f"缺少固定门槛指标{gate['name']}"
            else:
                try:
                    gate_actual_number = decimal(gate_actual)
                except ValueError:
                    gate_invalid[gate["name"]] = f"固定门槛指标{gate['name']}不是有效数值"
            if gate_actual_number is not None:
                gate_actual_metrics[gate["name"]] = gate_actual_number
            gate_thresholds = gate.get("thresholds")
            if gate_thresholds is None:
                level_count_for_gate = 5 if self.five_levels else 3
                # 某些标准的表格只在指定等级设置固定门槛（例如把某个
                # COP列作为3级限定值），不能把该门槛错误复制到所有等级。
                levels = {int(item) for item in gate.get("levels", ())}
                if levels:
                    gate_thresholds = [
                        gate.get("threshold") if index in levels else None
                        for index in range(1, level_count_for_gate + 1)
                    ]
                else:
                    gate_thresholds = [gate.get("threshold")] * level_count_for_gate
            elif isinstance(gate_thresholds, dict):
                level_count_for_gate = 5 if self.five_levels else 3
                gate_thresholds = [gate_thresholds.get(str(index), gate_thresholds.get(index)) for index in range(1, level_count_for_gate + 1)]
            elif gate.get("levels"):
                level_count_for_gate = 5 if self.five_levels else 3
                levels = [int(item) for item in gate.get("levels", ())]
                values_for_levels = list(gate_thresholds)
                if len(values_for_levels) != len(levels):
                    return with_context(unable(str(values.get("record_id", "")), effective_pack, f"固定门槛{gate['name']}的指定等级阈值数量不正确"))
                mapped = dict(zip(levels, values_for_levels))
                gate_thresholds = [mapped.get(index) for index in range(1, level_count_for_gate + 1)]
            if len(gate_thresholds) != (5 if self.five_levels else 3):
                return with_context(unable(str(values.get("record_id", "")), effective_pack, f"固定门槛{gate['name']}的等级阈值数量不正确"))
            gate_level_thresholds[gate["name"]] = list(gate_thresholds)
            gate_direction = ComparisonDirection(gate.get("direction", ">="))
            gate_directions[gate["name"]] = gate_direction
            for level_index, gate_threshold in enumerate(gate_thresholds, start=1):
                if gate_threshold is None:
                    continue
                comparison = {
                    "level": f"{level_index}级",
                    "metric": gate["name"],
                    "actual": str(gate_actual_number) if gate_actual_number is not None else None,
                    "direction": gate_direction.value,
                    "threshold": str(gate_threshold),
                    "passed": compare(gate_actual_number, gate_threshold, gate_direction) if gate_actual_number is not None else None,
                    "applicable": True,
                    "logic": "AND_WITH_PRIMARY",
                }
                if gate["name"] in gate_missing:
                    comparison["missing"] = True
                    comparison["reason"] = gate_missing[gate["name"]]
                elif gate["name"] in gate_invalid:
                    comparison["invalid"] = True
                    comparison["reason"] = gate_invalid[gate["name"]]
                gate_results.append(comparison)

        level_names = [f"{index}级" for index in range(1, level_count + 1)]
        # 标准表中的“—”表示该等级不作要求，不是零值，也不是输入缺失。
        # 统一保留无数据标记，避免Decimal(None)异常导致查表依据丢失；
        # 当所有主指标等级均为“—”时，保守返回无法判定。
        metric_passes: list[bool | None] = []
        comparisons = []
        for index, threshold in enumerate(thresholds):
            if threshold is None:
                metric_passes.append(None)
                comparisons.append({
                    "level": level_names[index],
                    "metric": record["metric_name"],
                    "actual": str(actual),
                    "direction": direction.value,
                    "threshold": None,
                    "passed": None,
                    "applicable": False,
                    "standard_marker": "—",
                })
                continue
            passed = compare(actual, threshold, direction)
            metric_passes.append(passed)
            comparisons.append({
                "level": level_names[index],
                "metric": record["metric_name"],
                "actual": str(actual),
                "direction": direction.value,
                "threshold": str(threshold),
                "passed": passed,
                "applicable": True,
            })
        # 对于有固定门槛的标准，必须在同一等级同时满足主指标和所有门槛。
        # 标量门槛会复制到各等级；标准中的“—”不创建比较条件。
        # 门槛只约束其声明的等级：如果主指标已经明确达到更高等级，
        # 未涉及该等级的门槛缺失不应阻断结论；如果唯一候选等级需要
        # 该门槛，则返回“无法判定”并列出缺失/非法字段。
        eligible: list[bool] = []
        unknown_by_level: list[list[str]] = [[] for _ in range(level_count)]
        unresolved_gate_fields: list[str] = []
        for index, metric_passed in enumerate(metric_passes):
            if metric_passed is not True:
                eligible.append(False)
                continue
            level_ok = True
            for gate_name, gate_thresholds in gate_level_thresholds.items():
                gate_threshold = gate_thresholds[index]
                if gate_threshold is None:
                    continue
                gate_actual = gate_actual_metrics.get(gate_name)
                if gate_actual is None:
                    level_ok = False
                    if gate_name not in unknown_by_level[index]:
                        unknown_by_level[index].append(gate_name)
                    continue
                level_ok = level_ok and compare(gate_actual, gate_threshold, gate_directions[gate_name])
            eligible.append(level_ok)
        comparisons.extend(gate_results)
        record_lookup["fixed_gate_thresholds"] = {
            name: list(values_for_levels)
            for name, values_for_levels in gate_level_thresholds.items()
        }
        record_lookup["fixed_gate_directions"] = {
            name: direction.value
            for name, direction in gate_directions.items()
        }
        if not any(threshold is not None for threshold in thresholds):
            conclusion = Conclusion.UNABLE_TO_JUDGE
        else:
            selected_index = next((index for index, passed in enumerate(eligible) if passed), None)
            if selected_index is not None:
                conclusion = Conclusion[f"LEVEL_{selected_index + 1}"]
            else:
                # 只有当主指标至少达到某个等级、但该等级所需门槛未知时，
                # 才阻断为无法判定；主指标已经低于3级时可明确判未达标。
                unresolved = [name for names in unknown_by_level for name in names]
                if unresolved:
                    unresolved_gate_fields = list(dict.fromkeys(unresolved))
                    conclusion = Conclusion.UNABLE_TO_JUDGE
                else:
                    conclusion = Conclusion.NOT_COMPLIANT
        limits = {
            f"{i+1}级{record['metric_name']}": value
            for i, value in enumerate(thresholds)
            if value is not None
        }
        for gate in record.get("fixed_gates", []):
            gate_thresholds = gate_level_thresholds.get(gate["name"], [])
            if gate.get("thresholds") is not None:
                limits.update({f"{i+1}级{gate['name']}": value for i, value in enumerate(gate_thresholds) if value is not None})
            elif gate_thresholds:
                # 指定等级门槛（例如仅3级）在展开后前面可能是None；
                # 记录实际定义的阈值，避免结果表显示成“固定门槛:None”。
                defined_threshold = next((value for value in gate_thresholds if value is not None), None)
                if defined_threshold is not None:
                    limits[f"固定门槛:{gate['name']}"] = defined_threshold
        range_metric = record.get("range_metric")
        if range_metric:
            calculated_metrics["容量分档"] = capacity_band_text()
        calculated_metrics["标准分级指标"] = record["metric_name"]
        actual_metrics = {record["metric_name"]: actual, **gate_actual_metrics}
        lookup_steps = []
        if correction_lookup:
            lookup_steps.append(correction_lookup)
        record_lookup["capacity_band"] = calculated_metrics.get("容量分档", "")
        lookup_steps.append(record_lookup)
        result = _result(values, effective_pack, conclusion, actual_metrics, calculated_metrics, limits, comparisons, record["table"], lookup_steps, clause=record_lookup["source_clause"])
        if unresolved_gate_fields:
            reason = "以下固定门槛指标缺失或不是有效数值：" + "、".join(unresolved_gate_fields)
            result.missing_fields = unresolved_gate_fields
            result.explanation = reason
            result.notes = [reason]
        return result
