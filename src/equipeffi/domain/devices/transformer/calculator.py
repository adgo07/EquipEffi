"""GB 20052—2024 transformer Domain calculator.

All loss values are compared in W using the transformer's Decimal50 profile.
The caller supplies the already-loaded derived standard pack; reading, hashing,
or serializing that pack belongs to the Application/Infrastructure layers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from typing import Any

from .input_contract import (
    TransformerCategoryOption,
    TransformerInputError,
    normalize_transformer_input,
)
from .model import TransformerEvaluation


DECIMAL_PROFILE_ID = "EQUIPEFFI_TRANSFORMER_GB20052_DECIMAL50_V1"
CALCULATOR_VERSION = "transformer-gb20052-v2.1.1"
_DECIMAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
_PACK_ID = "GB20052-2024-TRANSFORMER-V2.1"
_SCHEMA_VERSION = "equipeffi.transformer-standard-pack.v1"
_THRESHOLD_KEYS = (
    "no_load_loss_1", "load_loss_1",
    "no_load_loss_2", "load_loss_2",
    "no_load_loss_3", "load_loss_3",
)
_FIELD_LABELS = {
    "category_id": "设备类别",
    "capacity_kva": "额定容量(kVA)",
    "standard_conditions": "标准条件",
    "core_material": "铁心材料",
    "vector_group": "联结组别",
    "thermal_class": "热等级",
    "renewable_type": "新能源用途",
    "no_load_loss_w": "空载损耗(W)",
    "load_loss_w": "负载损耗(W)",
    "lv_rated_voltage_kv": "低压额定电压(kV)",
    "hv_rated_voltage_kv": "高压额定电压(kV)",
    "uk_rated_percent": "额定阻抗(%)",
    "uk_hm_rated_percent": "额定阻抗高—中(%)",
    "uk_hl_rated_percent": "额定阻抗高—低(%)",
    "uk_ml_rated_percent": "额定阻抗中—低(%)",
}
_CONDITION_FIELDS_BY_TABLE = {
    1: ("core_material", "vector_group"),
    2: ("core_material", "thermal_class"),
    29: ("renewable_type",),
    30: ("renewable_type", "thermal_class"),
    31: ("renewable_type",),
    32: ("renewable_type", "thermal_class"),
    33: ("renewable_type",),
    34: ("renewable_type", "thermal_class"),
    35: ("renewable_type",),
}
_ROW_CONDITION_FIELDS_BY_TABLE = {
    1: ("core_material", "vector_group"),
    2: ("core_material", "thermal_class"),
    30: ("thermal_class",),
    32: ("thermal_class",),
    34: ("thermal_class",),
}
_THERMAL_TABLES = {30, 32, 34}
_RENEWABLE_RANGES = {
    29: (Decimal("6"), Decimal("7.2"), Decimal("0.4"), Decimal("1.14")),
    30: (Decimal("6"), Decimal("7.2"), Decimal("0.4"), Decimal("1.14")),
    31: (Decimal("10"), Decimal("12"), Decimal("0.4"), Decimal("1.14")),
    32: (Decimal("10"), Decimal("12"), Decimal("0.4"), Decimal("1.14")),
    33: (Decimal("35"), Decimal("38.5"), Decimal("0.4"), Decimal("1.14")),
    34: (Decimal("35"), Decimal("38.5"), Decimal("0.4"), Decimal("1.14")),
    35: (Decimal("66"), Decimal("72.5"), Decimal("0.4"), Decimal("1.14")),
}
_TWO_WINDING_UK_RANGES = {
    "uk_4_0": ((Decimal("4"), Decimal("4")),),
    "uk_6_0_to_8_0": ((Decimal("6"), Decimal("8")),),
}
# The intervals are transcribed from the frozen mapping's physical-condition
# descriptions. The +/-10% expansion is the Owner-approved temporary matching
# rule; it applies only to group selection, never to loss comparisons.
_AUTOTRANSFORMER_UK_RANGES = {
    27: {
        "A": ((Decimal("12"), Decimal("12")), (Decimal("34"), Decimal("38")), (Decimal("20"), Decimal("22"))),
        "B": ((Decimal("12"), Decimal("12")), (Decimal("42"), Decimal("46")), (Decimal("28"), Decimal("30"))),
        "C": ((Decimal("14"), Decimal("22")), (Decimal("42"), Decimal("64")), (Decimal("28"), Decimal("40"))),
    },
    28: {
        "A": ((Decimal("12"), Decimal("12")), (Decimal("34"), Decimal("38")), (Decimal("20"), Decimal("22"))),
        "B": ((Decimal("12"), Decimal("12")), (Decimal("42"), Decimal("46")), (Decimal("28"), Decimal("30"))),
        "C": ((Decimal("14"), Decimal("15")), (Decimal("42"), Decimal("46")), (Decimal("28"), Decimal("30"))),
    },
}


class TransformerPackError(RuntimeError):
    """The supplied frozen transformer data pack is unavailable or malformed."""


class _InvalidValue(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


class TransformerCalculator:
    """Evaluate one explicit GB 20052 transformer type and its measured losses."""

    calculator_id = CALCULATOR_VERSION
    calculator_version = CALCULATOR_VERSION
    numeric_profile_id = DECIMAL_PROFILE_ID

    def evaluate(self, values: Mapping[str, Any], pack: Mapping[str, Any]) -> TransformerEvaluation:
        try:
            normalized = normalize_transformer_input(values)
        except TransformerInputError as exc:
            return self._result(
                "INVALID_INPUT", None, "输入无效",
                "设备类别或标准条件选择无效，请检查所选类别及其可用条件。",
                reason_codes=("INPUT_INVALID",),
            )

        category_id = normalized.get("category_id")
        if category_id is None:
            return self._result(
                "INSUFFICIENT_DATA", None, "无法判定", "请选择明确的变压器类别。",
                missing_fields=("category_id",), reason_codes=("MISSING_FIELD",),
            )
        if category_id == "OTHER_CATEGORY":
            return self._result(
                "OUT_OF_STANDARD_SCOPE", None, "不在范围", "所选类别为“其他类别”，不进入GB 20052—2024表值评价。",
                reason_codes=("OUT_OF_SCOPE_EXPLICIT",),
            )
        if category_id == "UNCERTAIN_CATEGORY":
            return self._result(
                None, None, "无法判定", "所选类别为“不确定类别”，未运行损耗限值评价。",
                reason_codes=("CATEGORY_UNCERTAIN",),
            )

        table_no = int(category_id[-2:])
        try:
            table = self._get_table(pack, table_no)
            numbers = self._parse_numeric_inputs(normalized, table_no)
        except _InvalidValue as exc:
            return self._result(
                "INVALID_INPUT", None, "输入无效", str(exc),
                reason_codes=("INPUT_INVALID",),
            )

        required_numeric = ["capacity_kva"]
        if table_no in {8, 14, 15}:
            required_numeric.append("lv_rated_voltage_kv")
        if table_no in _RENEWABLE_RANGES:
            required_numeric.extend(("hv_rated_voltage_kv", "lv_rated_voltage_kv"))
        missing_numeric = tuple(field for field in required_numeric if numbers.get(field) is None)
        if missing_numeric:
            return self._result(
                "INSUFFICIENT_DATA", None, "无法判定",
                "请补充必要数值：" + "、".join(self._field_label(field) for field in missing_numeric) + "。",
                missing_fields=missing_numeric, reason_codes=("MISSING_FIELD",),
            )

        missing_conditions = tuple(
            field for field in _CONDITION_FIELDS_BY_TABLE.get(table_no, ())
            if normalized.get(field) in (None, "")
        )
        if missing_conditions:
            return self._result(
                "INSUFFICIENT_DATA", None, "无法判定",
                "请补充标准条件：" + "、".join(self._field_label(field) for field in missing_conditions) + "。",
                missing_fields=missing_conditions,
                reason_codes=("MISSING_FIELD",),
            )

        scope_result = self._check_category_physical_facts(normalized, table_no, numbers)
        if scope_result is not None:
            return scope_result

        if table_no == 15 and numbers.get("lv_rated_voltage_kv") is None:
            return self._result(
                "INSUFFICIENT_DATA", None, "无法判定", "表15需提供低压绕组额定电压以选择普通或66/69kV分支。",
                missing_fields=("lv_rated_voltage_kv",), reason_codes=("MISSING_FIELD",),
            )

        rows = table["rows"]
        selected, selection_error = self._select_rows(normalized, numbers, table_no, rows)
        if selection_error is not None:
            return selection_error
        if not selected:
            return self._result(
                "INSUFFICIENT_DATA", None, "无法判定", "未找到与输入条件一致的有效损耗分支。",
                reason_codes=("BRANCH_NO_MATCH",),
            )

        capacity = numbers["capacity_kva"]
        looked_up: list[tuple[Mapping[str, Any], dict[str, Decimal], dict[str, Any]]] = []
        for branch_rows in selected:
            thresholds, lookup_trace, lookup_error = self._lookup_thresholds(branch_rows, capacity)
            if lookup_error is not None:
                return lookup_error
            assert thresholds is not None and lookup_trace is not None
            looked_up.append((branch_rows[0], thresholds, lookup_trace))

        if len(looked_up) > 1:
            reference = looked_up[0][1]
            if any(candidate[1] != reference for candidate in looked_up[1:]):
                trace = tuple(self._candidate_trace(row, lookup) for row, _, lookup in looked_up)
                return self._result(
                    "INSUFFICIENT_DATA", None, "无法判定",
                    "多个额定阻抗组同时命中，但本容量的六项限值不同，不能自动选取。",
                    trace=trace, reason_codes=("BRANCH_AMBIGUOUS",),
                )
            thresholds = reference
            trace = tuple(self._candidate_trace(row, lookup) for row, _, lookup in looked_up)
        else:
            _, thresholds, lookup_trace = looked_up[0]
            trace = (self._candidate_trace(selected[0][0], lookup_trace),)

        missing_losses = tuple(
            field for field in ("no_load_loss_w", "load_loss_w")
            if numbers.get(field) is None
        )
        if missing_losses:
            return self._result(
                "INSUFFICIENT_DATA", None, "无法判定",
                "已取得六项限值，但正式判级还需空载损耗和负载损耗。",
                thresholds=thresholds, missing_fields=missing_losses, trace=trace,
                reason_codes=("MISSING_FIELD",),
            )

        no_load = numbers["no_load_loss_w"]
        load = numbers["load_loss_w"]
        grade = None
        for level in ("1", "2", "3"):
            if no_load <= thresholds[f"no_load_loss_{level}"] and load <= thresholds[f"load_loss_{level}"]:
                grade = level
                break
        if grade is None:
            grade = "BELOW_MINIMUM"
            conclusion = "未达3级"
            explanation = "空载损耗与负载损耗均按W分别比较；两项未同时满足3级限值。"
        else:
            conclusion = f"{grade}级"
            explanation = f"空载损耗与负载损耗均不高于{grade}级对应限值。"
        return self._result(
            "SUCCESS", grade, conclusion, explanation, thresholds=thresholds,
            trace=trace, reason_codes=(),
        )

    def _parse_numeric_inputs(self, values: Mapping[str, Any], table_no: int) -> dict[str, Decimal | None]:
        fields = {"capacity_kva": True, "no_load_loss_w": False, "load_loss_w": False}
        if table_no in {7, 8, 12, 14, 15}:
            fields["lv_rated_voltage_kv"] = True
        if table_no in _RENEWABLE_RANGES:
            fields["hv_rated_voltage_kv"] = True
            fields["lv_rated_voltage_kv"] = True
        if table_no == 2:
            fields["uk_rated_percent"] = True
        if table_no in {23, 24}:
            fields["uk_hm_rated_percent"] = False
        if table_no in {27, 28}:
            fields.update({
                "uk_hm_rated_percent": True,
                "uk_hl_rated_percent": True,
                "uk_ml_rated_percent": True,
            })
        parsed: dict[str, Decimal | None] = {}
        loss_fields = {"no_load_loss_w", "load_loss_w"}
        for field, required_positive in fields.items():
            value = values.get(field)
            if value in (None, ""):
                parsed[field] = None
                continue
            decimal = self._decimal(value, field)
            if field in loss_fields:
                if decimal < 0:
                    raise _InvalidValue(field, f"{self._field_label(field)}不能为负数")
            elif decimal <= 0:
                raise _InvalidValue(field, f"{self._field_label(field)}必须大于0")
            parsed[field] = decimal
        if table_no in {8, 14, 15} and parsed.get("lv_rated_voltage_kv") is None:
            # Missing voltage is a business information gap, not a bad number.
            return parsed
        return parsed

    @staticmethod
    def _decimal(value: Any, field: str) -> Decimal:
        if isinstance(value, bool) or isinstance(value, float):
            raise _InvalidValue(field, f"{TransformerCalculator._field_label(field)}必须使用十进制文本、整数或Decimal")
        if not isinstance(value, (str, int, Decimal)):
            raise _InvalidValue(field, f"{TransformerCalculator._field_label(field)}必须是十进制文本、整数或Decimal")
        text = str(value).strip()
        if not text:
            raise _InvalidValue(field, f"{TransformerCalculator._field_label(field)}不能为空白文本")
        try:
            result = Decimal(text)
        except InvalidOperation as exc:
            raise _InvalidValue(field, f"{TransformerCalculator._field_label(field)}不是有效十进制数") from exc
        if not result.is_finite():
            raise _InvalidValue(field, f"{TransformerCalculator._field_label(field)}不能是非有限数值")
        return result

    @staticmethod
    def _field_label(field: str) -> str:
        """Return user-facing Chinese text while keeping stable IDs in metadata."""
        return _FIELD_LABELS.get(field, "相关输入")

    def _check_category_physical_facts(
        self, values: Mapping[str, Any], table_no: int, numbers: Mapping[str, Decimal | None]
    ) -> TransformerEvaluation | None:
        lv = numbers.get("lv_rated_voltage_kv")
        if table_no in {7, 12} and lv is not None:
            special = Decimal("35") if table_no == 7 else Decimal("66")
            if lv == special:
                dedicated_table = "表08" if table_no == 7 else "表14"
                return self._result(
                    "INVALID_INPUT", None, "输入无效",
                    f"F类别与低压额定电压矛盾：该参数属于{dedicated_table}专用类别，不会回退或改选其他表。",
                    reason_codes=("ROUTE_CONFLICT",),
                )
        if table_no in {8, 14} and lv is not None:
            expected = Decimal("35") if table_no == 8 else Decimal("66")
            if lv != expected:
                return self._result(
                    "INVALID_INPUT", None, "输入无效",
                    f"所选类别要求低压额定电压为{expected}kV，实际输入为{lv}kV。",
                    reason_codes=("ROUTE_CONFLICT",),
                )
        if table_no in _RENEWABLE_RANGES:
            hv = numbers.get("hv_rated_voltage_kv")
            assert hv is not None and lv is not None
            hv_min, hv_max, lv_min, lv_max = _RENEWABLE_RANGES[table_no]
            if not (hv_min <= hv <= hv_max and lv_min <= lv <= lv_max):
                return self._result(
                    "OUT_OF_STANDARD_SCOPE", None, "不在范围",
                    f"实际绕组电压不在所选新能源类别范围内：高压{hv_min}～{hv_max}kV，低压{lv_min}～{lv_max}kV。",
                    reason_codes=("OUTSIDE_VOLTAGE_RANGE",),
                )
        return None

    def _select_rows(
        self,
        values: Mapping[str, Any],
        numbers: Mapping[str, Decimal | None],
        table_no: int,
        rows: Sequence[Mapping[str, Any]],
    ) -> tuple[list[list[Mapping[str, Any]]], TransformerEvaluation | None]:
        conditions = {key: values.get(key) for key in _ROW_CONDITION_FIELDS_BY_TABLE.get(table_no, ())}
        filtered = [row for row in rows if self._row_matches_conditions(row, conditions)]
        if not filtered:
            raise TransformerPackError(f"GB20052-T{table_no:02d} has no rows for required conditions {conditions!r}")

        if table_no == 2:
            return self._select_t02_rows(filtered, numbers)
        if table_no == 15:
            lv = numbers["lv_rated_voltage_kv"]
            assert lv is not None
            branch = "lv_66_69_special" if lv in (Decimal("66"), Decimal("69")) else "ordinary"
            filtered = [row for row in filtered if row.get("conditions", {}).get("loss_group") == branch]
            return ([filtered] if filtered else []), None
        if table_no in {27, 28}:
            return self._select_autotransformer_rows(table_no, filtered, numbers)

        groups: dict[str, list[Mapping[str, Any]]] = {}
        for row in filtered:
            branch_id = row.get("branch_id")
            if not isinstance(branch_id, str):
                raise TransformerPackError(f"GB20052-T{table_no:02d} row has no branch_id")
            groups.setdefault(branch_id, []).append(row)
        if len(groups) != 1:
            raise TransformerPackError(f"GB20052-T{table_no:02d} has ambiguous rows without a modeled selector")
        return [next(iter(groups.values()))], None

    def _select_t02_rows(
        self, rows: Sequence[Mapping[str, Any]], numbers: Mapping[str, Decimal | None]
    ) -> tuple[list[list[Mapping[str, Any]]], TransformerEvaluation | None]:
        capacity = numbers["capacity_kva"]
        impedance = numbers.get("uk_rated_percent")
        assert capacity is not None
        by_group: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            group = row.get("conditions", {}).get("uk_group")
            if group not in _TWO_WINDING_UK_RANGES:
                raise TransformerPackError(f"T02 contains unsupported impedance group {group!r}")
            by_group.setdefault(group, []).append(row)

        capacity_groups: list[tuple[str, list[Mapping[str, Any]]]] = []
        for group, branch_rows in by_group.items():
            caps = [self._pack_decimal(row.get("capacity_kva"), "capacity_kva") for row in branch_rows]
            if min(caps) <= capacity <= max(caps):
                capacity_groups.append((group, list(branch_rows)))
        if not capacity_groups:
            all_caps = [self._pack_decimal(row.get("capacity_kva"), "capacity_kva") for row in rows]
            if capacity < min(all_caps) or capacity > max(all_caps):
                return [], self._capacity_scope_result(capacity, min(all_caps), max(all_caps), 2)
            return [], self._result(
                "INSUFFICIENT_DATA", None, "无法判定", "表02在所选阻抗分支中没有可用插值端点。",
                reason_codes=("NO_INTERPOLATION_BRACKET",),
            )

        if impedance is None:
            if len(capacity_groups) > 1:
                return [], self._result(
                    "INSUFFICIENT_DATA", None, "无法判定", "630kVA表02存在两个阻抗分支，请填写实际额定阻抗。",
                    missing_fields=("uk_rated_percent",), reason_codes=("MISSING_FIELD",),
                )
            return [capacity_groups[0][1]], None

        impedance_groups = [
            (group, branch_rows) for group, branch_rows in by_group.items()
            if self._matches_interval(impedance, *_TWO_WINDING_UK_RANGES[group][0])
        ]
        if not impedance_groups:
            return [], self._result(
                "INSUFFICIENT_DATA", None, "无法判定", "额定阻抗未命中表02的4.0%或6.0%～8.0%软件选组范围。",
                reason_codes=("IMPEDANCE_NO_MATCH",),
            )
        capacity_branch_ids = {group for group, _ in capacity_groups}
        matching = [(group, branch_rows) for group, branch_rows in impedance_groups if group in capacity_branch_ids]
        if not matching:
            group, branch_rows = impedance_groups[0]
            branch_caps = [self._pack_decimal(row.get("capacity_kva"), "capacity_kva") for row in branch_rows]
            return [], self._capacity_scope_result(capacity, min(branch_caps), max(branch_caps), 2)
        return [branch_rows for _, branch_rows in matching], None

    def _select_autotransformer_rows(
        self, table_no: int, rows: Sequence[Mapping[str, Any]], numbers: Mapping[str, Decimal | None]
    ) -> tuple[list[list[Mapping[str, Any]]], TransformerEvaluation | None]:
        fields = ("uk_hm_rated_percent", "uk_hl_rated_percent", "uk_ml_rated_percent")
        values = tuple(numbers.get(field) for field in fields)
        if any(value is None for value in values):
            missing = tuple(field for field, value in zip(fields, values) if value is None)
            return [], self._result(
                "INSUFFICIENT_DATA", None, "无法判定", "表27/28需提供完整的高—中、高—低、中—低额定阻抗三元组。",
                missing_fields=missing, reason_codes=("MISSING_FIELD",),
            )
        impedances = (values[0], values[1], values[2])
        assert all(isinstance(value, Decimal) for value in impedances)
        matched_groups: set[str] = set()
        for group, ranges in _AUTOTRANSFORMER_UK_RANGES[table_no].items():
            if all(self._matches_interval(actual, low, high)
                   for actual, (low, high) in zip(impedances, ranges)):
                matched_groups.add(group)
        if not matched_groups:
            return [], self._result(
                "INSUFFICIENT_DATA", None, "无法判定", "三项额定阻抗未共同命中表27/28的A、B或C阻抗组。",
                reason_codes=("IMPEDANCE_NO_MATCH",),
            )
        groups: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            group = row.get("conditions", {}).get("uk_group")
            if group in matched_groups:
                groups.setdefault(str(group), []).append(row)
        if set(groups) != matched_groups:
            raise TransformerPackError(f"T{table_no:02d} rows omit matched impedance branches")
        return [groups[group] for group in sorted(groups)], None

    @staticmethod
    def _matches_interval(value: Decimal, low: Decimal, high: Decimal) -> bool:
        with localcontext(_DECIMAL_CONTEXT):
            return low * Decimal("0.9") <= value <= high * Decimal("1.1")

    @staticmethod
    def _row_matches_conditions(row: Mapping[str, Any], conditions: Mapping[str, Any]) -> bool:
        row_conditions = row.get("conditions")
        if not isinstance(row_conditions, Mapping):
            raise TransformerPackError("transformer pack row conditions must be an object")
        return all(row_conditions.get(key) == value for key, value in conditions.items())

    def _lookup_thresholds(
        self, rows: Sequence[Mapping[str, Any]], capacity: Decimal
    ) -> tuple[dict[str, Decimal] | None, dict[str, Any] | None, TransformerEvaluation | None]:
        if not rows:
            raise TransformerPackError("selected transformer branch is empty")
        by_capacity: dict[Decimal, list[Mapping[str, Any]]] = {}
        for row in rows:
            row_capacity = self._pack_decimal(row.get("capacity_kva"), "capacity_kva")
            by_capacity.setdefault(row_capacity, []).append(row)
        capacities = sorted(by_capacity)
        if capacity < capacities[0] or capacity > capacities[-1]:
            return None, None, self._capacity_scope_result(capacity, capacities[0], capacities[-1], None)

        if capacity in by_capacity:
            selected_rows = by_capacity[capacity]
            threshold_candidates = [self._read_thresholds(row) for row in selected_rows]
            if any(candidate != threshold_candidates[0] for candidate in threshold_candidates[1:]):
                trace = {"lookup_method": "exact", "capacity_kva": capacity,
                         "sources": [self._source_trace(row) for row in selected_rows]}
                return None, None, self._result(
                    "INSUFFICIENT_DATA", None, "无法判定", "同一分支同一容量对应多个不同限值。",
                    trace=(trace,), reason_codes=("BRANCH_AMBIGUOUS",),
                )
            return threshold_candidates[0], {
                "lookup_method": "exact", "capacity_kva": capacity,
                "source_rows": selected_rows,
            }, None

        lower_capacity = max(candidate for candidate in capacities if candidate < capacity)
        upper_capacity = min(candidate for candidate in capacities if candidate > capacity)
        lower_rows = by_capacity[lower_capacity]
        upper_rows = by_capacity[upper_capacity]
        # A physical branch must have one unambiguous value at each endpoint.
        lower_candidates = [self._read_thresholds(row) for row in lower_rows]
        upper_candidates = [self._read_thresholds(row) for row in upper_rows]
        if any(item != lower_candidates[0] for item in lower_candidates[1:]) or any(
            item != upper_candidates[0] for item in upper_candidates[1:]
        ):
            trace = {"lookup_method": "unavailable", "capacity_kva": capacity,
                     "sources": [self._source_trace(row) for row in (*lower_rows, *upper_rows)]}
            return None, None, self._result(
                "INSUFFICIENT_DATA", None, "无法判定", "插值端点在同一分支内仍有不同限值。",
                trace=(trace,), reason_codes=("BRANCH_AMBIGUOUS",),
            )
        with localcontext(_DECIMAL_CONTEXT):
            interpolated: dict[str, Decimal] = {}
            for key in _THRESHOLD_KEYS:
                delta = upper_candidates[0][key] - lower_candidates[0][key]
                interpolated[key] = lower_candidates[0][key] + (
                    (capacity - lower_capacity) * delta / (upper_capacity - lower_capacity)
                )
        return interpolated, {
            "lookup_method": "interpolated", "capacity_kva": capacity,
            "lower_capacity_kva": lower_capacity, "upper_capacity_kva": upper_capacity,
            "lower_source_rows": lower_rows, "upper_source_rows": upper_rows,
        }, None

    def _read_thresholds(self, row: Mapping[str, Any]) -> dict[str, Decimal]:
        source = row.get("source")
        if not isinstance(source, Mapping):
            raise TransformerPackError("transformer pack row has no provenance object")
        if source.get("value_status") != "explicit":
            raise TransformerPackError(f"selected source row is not explicit: {source.get('value_status')!r}")
        threshold_block = row.get("thresholds_w")
        if not isinstance(threshold_block, Mapping):
            raise TransformerPackError("transformer pack thresholds_w must be an object")
        result: dict[str, Decimal] = {}
        for level in ("1", "2", "3"):
            grade = threshold_block.get(f"grade_{level}")
            if not isinstance(grade, Mapping):
                raise TransformerPackError(f"selected row is missing grade_{level} thresholds")
            for metric in ("no_load_loss", "load_loss"):
                key = f"{metric}_{level}"
                value = grade.get(metric)
                if value is None:
                    raise TransformerPackError(f"selected row has null {key} threshold")
                result[key] = self._pack_decimal(value, key)
                if result[key] < 0:
                    raise TransformerPackError(f"selected row has negative {key} threshold")
        return result

    @staticmethod
    def _pack_decimal(value: Any, field: str) -> Decimal:
        if not isinstance(value, (str, int, Decimal)) or isinstance(value, bool):
            raise TransformerPackError(f"pack {field} must be a decimal string, integer, or Decimal")
        try:
            result = Decimal(str(value).strip())
        except InvalidOperation as exc:
            raise TransformerPackError(f"pack {field} is not a decimal value") from exc
        if not result.is_finite():
            raise TransformerPackError(f"pack {field} must be finite")
        return result

    def _get_table(self, pack: Mapping[str, Any], table_no: int) -> Mapping[str, Any]:
        if not isinstance(pack, Mapping):
            raise TransformerPackError("transformer standard pack must be a mapping")
        if pack.get("schema_version") != _SCHEMA_VERSION or pack.get("pack_id") != _PACK_ID:
            raise TransformerPackError("unexpected transformer standard pack identity")
        if pack.get("runtime_loss_unit") != "W":
            raise TransformerPackError("transformer standard pack runtime_loss_unit must be W")
        tables = pack.get("tables")
        if not isinstance(tables, list) or len(tables) != 35:
            raise TransformerPackError("transformer standard pack must contain 35 ordered tables")
        table = tables[table_no - 1]
        if not isinstance(table, Mapping):
            raise TransformerPackError(f"GB20052-T{table_no:02d} is not a table object")
        expected_id = f"GB20052-T{table_no:02d}"
        if table.get("table_no") != table_no or table.get("table_id") != expected_id or table.get("route_id") != expected_id:
            raise TransformerPackError(f"standard pack table {table_no} identity does not match its position")
        rows = table.get("rows")
        if not isinstance(rows, list) or not rows:
            raise TransformerPackError(f"{expected_id} has no source rows")
        for row in rows:
            if not isinstance(row, Mapping) or not isinstance(row.get("conditions"), Mapping):
                raise TransformerPackError(f"{expected_id} contains a malformed row")
            if not isinstance(row.get("branch_id"), str):
                raise TransformerPackError(f"{expected_id} row is missing branch_id")
            if not isinstance(row.get("source"), Mapping):
                raise TransformerPackError(f"{expected_id} row is missing source provenance")
        return table

    @staticmethod
    def _source_trace(row: Mapping[str, Any]) -> Mapping[str, Any]:
        source = row.get("source", {})
        return {
            "source_row_id": row.get("source_row_id"),
            "source_sheet": source.get("sheet"),
            "source_row": source.get("row"),
            "capacity_kva": row.get("capacity_kva"),
            "branch_id": row.get("branch_id"),
            "page_reference": source.get("page_reference"),
            "cell_coordinates": source.get("cell_coordinates"),
            "shared_source_label": source.get("shared_source_label"),
        }

    def _candidate_trace(self, row: Mapping[str, Any], lookup: Mapping[str, Any]) -> Mapping[str, Any]:
        trace: dict[str, Any] = {
            "table_id": row.get("branch_id", "").split("/", 1)[0],
            "branch_id": row.get("branch_id"),
            "lookup_method": lookup["lookup_method"],
            "capacity_kva": lookup["capacity_kva"],
        }
        if lookup["lookup_method"] == "exact":
            source_rows = lookup["source_rows"]
        else:
            trace["lower_capacity_kva"] = lookup["lower_capacity_kva"]
            trace["upper_capacity_kva"] = lookup["upper_capacity_kva"]
            source_rows = (*lookup["lower_source_rows"], *lookup["upper_source_rows"])
        trace["sources"] = tuple(self._source_trace(source_row) for source_row in source_rows)
        return trace

    def _capacity_scope_result(
        self, capacity: Decimal, minimum: Decimal, maximum: Decimal, table_no: int | None
    ) -> TransformerEvaluation:
        label = f"表{table_no:02d}" if table_no is not None else "所选损耗分支"
        return self._result(
            "OUT_OF_STANDARD_SCOPE", None, "不在范围",
            f"{label}的软件评价容量范围为{minimum}～{maximum}kVA，输入{capacity}kVA在范围外；不会回退到其他表或分支。",
            reason_codes=("OUTSIDE_TABLE_CAPACITY_RANGE",),
        )

    @staticmethod
    def _result(
        status: str | None,
        grade: str | None,
        conclusion: str,
        explanation: str,
        *,
        thresholds: Mapping[str, Decimal] | None = None,
        missing_fields: tuple[str, ...] = (),
        trace: tuple[Mapping[str, Any], ...] = (),
        reason_codes: tuple[str, ...] = (),
    ) -> TransformerEvaluation:
        stable_thresholds = {
            key: (thresholds or {}).get(key)
            for key in _THRESHOLD_KEYS
            if key in (thresholds or {})
        }
        return TransformerEvaluation(
            evaluation_status=status,
            grade=grade,
            ui_conclusion=conclusion,
            thresholds=stable_thresholds,
            explanation=explanation,
            missing_fields=tuple(missing_fields),
            trace=tuple(trace),
            reason_codes=tuple(reason_codes),
        )

