"""GB/T 19761-2020通风机评价器。"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from ...common.enums import ComparisonDirection, Conclusion
from ...common.models import EvaluationResult
class FanEvaluator:
    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]) -> EvaluationResult:
        from ..device_evaluators import (
            _active_or_unable,
            _attach_lookup_trace,
            _attach_metrics,
            _interval_hit,
            _missing,
            _positive_or_unable,
            _range_or_unable,
            _result,
            _value,
            out_of_scope,
            unable,
        )
        from ..decimal_math import decimal, rounded
        from ..grading import grade_three_optional
        from ...common.enums import ComparisonDirection

        if result := _active_or_unable(values, pack):
            return result
        # 最高通风机效率可按GB 19761-2020式(1)由设计物理量计算，
        # 因此效率填报值不是绝对必需项；物理量不完整时仍保守返回无法判定。
        required = [("设备类别", ("category", "设备类别")), ("机号", ("machine_no", "机号"))]
        missing = _missing(values, required)
        if missing:
            return unable(str(values.get("record_id", "")), pack, "通风机查表缺少设备类别或机号", missing)
        if result := _positive_or_unable(values, pack, [("机号", ("machine_no", "机号"))]):
            return result
        if result := _range_or_unable(values, pack, "等熵指数k", ("isentropic_k", "k", "等熵指数k"), Decimal(1), Decimal(2)):
            return result
        category = str(_value(values, "category", "设备类别") or "").strip()
        # GB 19761-2020 的标准表族只有离心、轴流和外转子前向多翼
        # 三类。不能把未知值或“其他（请备注说明）”静默当成离心风机，
        # 否则压力系数/比转速恰好落档时会错误输出能效等级。
        category_type = {
            "离心通风机": "离心",
            "轴流通风机": "轴流",
            "外转子电机直联前向多翼离心风机": "外转子",
        }.get(category)
        if category_type is None:
            return out_of_scope(
                str(values.get("record_id", "")),
                pack,
                "设备类别不在GB 19761-2020标准表族内，不能默认按离心通风机判定",
            )
        transmission = str(_value(values, "transmission", "传动方式") or "").strip()
        # GB 19761-2020表4针对“外转子电机直联前向多翼离心风机”，
        # 考核指标是机组效率ηe，而不是普通通风机效率ηr。该型式的传动
        # 条件必须明确；不能把填写的ηr直接拿来和表4的ηe比较。
        outer_rotor = category_type == "外转子"
        if outer_rotor and not transmission:
            return unable(str(values.get("record_id", "")), pack, "外转子前向多翼离心风机缺少传动方式", ["传动方式"])
        if outer_rotor and transmission and "外转子" not in transmission:
            return unable(str(values.get("record_id", "")), pack, "外转子前向多翼离心风机的传动方式必须为外转子电机直联", ["传动方式"])
        psi = _value(values, "pressure_coefficient", "压力系数")
        calculated: dict[str, Any] = {}
        lookup_trace: list[dict[str, Any]] = []
        defer_efficiency_missing = False
        efficiency_missing_fields: list[str] = []
        compression = _value(values, "compression_correction", "压缩性修正系数")
        # GB/T 1236-2017 14.8.2方法b：在没有预先给定kp时，使用
        # 风量、压力、进口滞止压力、叶轮功率和绝热指数计算压缩性修正系数。
        # 这一步只在原始物理量齐全时执行，不设置默认kp。
        pressure_for_calc = _value(values, "fan_pressure_pa", "fan_pressure", "风机压力")
        if pressure_for_calc is None:
            inlet_pressure = _value(values, "inlet_stagnation_pressure_pa", "inlet_stag_pressure", "进口滞止压力")
            outlet_pressure = _value(values, "outlet_stagnation_pressure_pa", "outlet_stag_pressure", "出口滞止压力")
            if inlet_pressure is not None and outlet_pressure is not None:
                try:
                    pressure_for_calc = decimal(outlet_pressure) - decimal(inlet_pressure)
                except ValueError:
                    pressure_for_calc = None
        if compression is None:
            kp_fields = [
                ("流量", ("flow_m3h", "flow", "流量")),
                ("进口滞止压力", ("inlet_stagnation_pressure_pa", "inlet_stag_pressure", "进口滞止压力")),
                ("叶轮功率", ("impeller_power_kw", "impeller_power", "叶轮功率")),
                ("等熵指数k", ("isentropic_k", "k", "等熵指数k")),
            ]
            kp_missing = _missing(values, kp_fields)
            # pF可以直接填报，也可以由出口/进口滞止压力之差得到；后者是V4
            # 表单允许的完整物理输入，不能因为没有单独的pF列而重复要求用户填报。
            if pressure_for_calc is None:
                kp_missing.append("风机压力（或出口/进口滞止压力）")
            if not kp_missing:
                try:
                    q = decimal(_value(values, *kp_fields[0][1])) / Decimal(3600)
                    p_f = decimal(pressure_for_calc)
                    p_sg1 = decimal(_value(values, *kp_fields[1][1]))
                    power_w = decimal(_value(values, *kp_fields[2][1])) * Decimal(1000)
                    k = decimal(_value(values, *kp_fields[3][1]))
                    if min(q, p_f, p_sg1, power_w) <= 0 or k <= 1:
                        raise ValueError("流量、压力、进口压力和叶轮功率必须为正，等熵指数k必须大于1")
                    x = p_f / p_sg1
                    z_p = (k - 1) / k * power_w / (q * p_sg1)
                    if x <= 0 or z_p <= 0:
                        raise ValueError("压缩性修正系数计算参数必须为正")
                    compression = ((x + 1).ln() / x) * (z_p / (z_p + 1).ln())
                    calculated["压缩性修正系数"] = compression
                    lookup_trace.append({
                        "step_type": "公式计算",
                        "formula": "kp=ln(1+x)/x×Zp/ln(1+Zp)",
                        "standard": "GB/T 1236-2017 14.8.2.2",
                        "inputs": {"x": str(x), "Zp": str(z_p)},
                        "value": str(compression),
                    })
                except (ValueError, ArithmeticError) as exc:
                    return unable(str(values.get("record_id", "")), pack, f"压缩性修正系数计算失败：{exc}")
            elif psi is None:
                return unable(str(values.get("record_id", "")), pack, "缺少压力系数，且缺少按GB/T 1236计算压缩性修正系数的物理参数", kp_missing)
        if compression is not None:
            try:
                compression = decimal(compression)
            except ValueError:
                return unable(str(values.get("record_id", "")), pack, "压缩性修正系数不是有效数值", ["压缩性修正系数"])
            if compression <= 0:
                return unable(str(values.get("record_id", "")), pack, "压缩性修正系数必须为正数", ["压缩性修正系数"])
            calculated.setdefault("压缩性修正系数", compression)
        if psi is None:
            # GB 19761使用机号对应叶轮直径D=0.1×No（m），
            # Ψ=pF×kp/(ρu²)，u=πDn/60。仅在V4原始字段完整时计算，不设置默认值。
            raw_fields = [
                ("进口滞止密度", ("inlet_stagnation_density", "density", "进口滞止密度")),
                ("转速", ("rated_speed_rpm", "speed", "转速")),
            ]
            raw_missing = _missing(values, raw_fields)
            if raw_missing:
                return unable(str(values.get("record_id", "")), pack, "缺少压力系数，且无法由V4原始参数计算；不使用经验近似", raw_missing)
            if pressure_for_calc is None:
                return unable(str(values.get("record_id", "")), pack, "缺少压力系数，且无法由V4原始参数计算；不使用经验近似", ["风机压力（或出口/进口滞止压力）"])
            try:
                pressure = decimal(pressure_for_calc if pressure_for_calc is not None else _value(values, "fan_pressure_pa", "风机压力"))
                density = decimal(_value(values, "inlet_stagnation_density", "density", "进口滞止密度"))
                speed = decimal(_value(values, "rated_speed_rpm", "speed", "转速"))
                machine_no = decimal(_value(values, "machine_no", "机号"))
                diameter = machine_no / Decimal(10)
                u = Decimal("3.141592653589793238462643383279") * diameter * speed / Decimal(60)
                if min(pressure, density, speed, diameter, u) <= 0:
                    raise ValueError("通风机压力、密度、转速、机号必须为正数")
                psi = pressure * decimal(compression or 1) / (density * u * u)
                calculated.update({"叶轮直径_m": diameter, "叶轮圆周速度_m/s": u})
                lookup_trace.append({"step_type": "公式计算", "formula": "D=0.1×No；u=πDn/60；Ψ=pF×kp/(ρu²)", "pressure_coefficient": str(psi), "inputs": {"pF_Pa": str(pressure), "kp": str(compression or 1), "rho_kg/m3": str(density), "n_r/min": str(speed), "No": str(machine_no)}})
            except (ValueError, ArithmeticError) as exc:
                return unable(str(values.get("record_id", "")), pack, f"通风机压力系数计算失败：{exc}")
        try:
            psi = decimal(psi)
        except ValueError:
            return unable(str(values.get("record_id", "")), pack, "压力系数不是有效数值", ["压力系数"])
        if psi <= 0:
            return unable(str(values.get("record_id", "")), pack, "压力系数必须为正数", ["压力系数"])
        # 压力系数到这里已经完成了输入解析或标准公式计算。后续
        # 任何查表早退都应保留这一可复核的中间结果。
        calculated["压力系数"] = psi
        # GB 19761-2020式(1)：ηr=qvsg1·pF·kp/(1000Pr)×100%。
        # 已填写的效率作为铭牌/设计值优先；缺失时仅在公式所需物理量齐全时计算，
        # 不把额定电机功率当作叶轮功率，也不设置经验默认值。
        if outer_rotor:
            actual_efficiency = _value(values, "unit_efficiency", "机组效率", "机组效率ηe", "fan_unit_efficiency")
            if actual_efficiency is None:
                # 表4的ηe可按式(3)由进口滞止容积流量、压力、kp和电动机
                # 输入功率Pe计算。额定功率在此仅作为Pe使用，只有外转子
                # 表4路径才允许这样解释；普通通风机仍要求叶轮功率Pr。
                eta_fields = [
                    ("流量", ("flow_m3h", "flow", "流量")),
                    ("电动机输入功率", ("rated_power_kw", "motor_input_power_kw", "额定功率")),
                ]
                eta_missing = _missing(values, eta_fields)
                if pressure_for_calc is None:
                    eta_missing.append("风机压力（或出口/进口滞止压力）")
                if compression is None:
                    eta_missing.append("压缩性修正系数")
                if eta_missing:
                    # 机号、压力系数和比转速仍可唯一确定表4标准行；
                    # 不因缺少式(3)的备用物理量而丢失查表阈值和来源。
                    defer_efficiency_missing = True
                    efficiency_missing_fields = list(dict.fromkeys(["机组效率ηe", *eta_missing]))
                try:
                    if not defer_efficiency_missing:
                        flow_m3s = decimal(_value(values, *eta_fields[0][1])) / Decimal(3600)
                        pressure = decimal(pressure_for_calc)
                        motor_input_power_kw = decimal(_value(values, *eta_fields[1][1]))
                        if min(flow_m3s, pressure, motor_input_power_kw, decimal(compression)) <= 0:
                            raise ValueError("流量、压力、电动机输入功率和压缩性修正系数必须为正")
                        actual_efficiency = flow_m3s * pressure * decimal(compression) / (Decimal(1000) * motor_input_power_kw) * Decimal(100)
                        calculated["机组效率ηe_%"] = actual_efficiency
                        lookup_trace.append({
                            "step_type": "公式计算",
                            "formula": "ηe=qvsg1·pF·kp/(1000Pe)×100%",
                            "standard": "GB 19761-2020式(3)",
                            "inputs": {"qvsg1_m3s": str(flow_m3s), "pF_Pa": str(pressure), "kp": str(compression), "Pe_kW": str(motor_input_power_kw)},
                            "value": str(actual_efficiency),
                        })
                except (ValueError, ArithmeticError) as exc:
                    return unable(str(values.get("record_id", "")), pack, f"机组效率ηe计算失败：{exc}", ["机组效率ηe"])
            metric_name = "机组效率ηe"
        else:
            actual_efficiency = _value(values, "fan_efficiency", "设计风机效率", "风机效率")
            metric_name = "最高通风机效率ηr"
            # GB 19761-2020式(4)：普通电动机直联时，可由机组效率ηe
            # 和电动机效率ηm换算最高通风机效率ηr。两项均按百分数本值
            # （例如95）输入，因此换算时需要乘以100；只有明确填写直联
            # 传动方式才启用该路径，避免把任意机组效率误当作叶轮效率。
            if actual_efficiency is None:
                unit_efficiency = _value(values, "unit_efficiency", "机组效率", "机组效率ηe", "fan_unit_efficiency")
                motor_efficiency = _value(values, "motor_efficiency", "电动机效率", "ηm")
                direct_motor = any(token in transmission for token in ("普通电动机直联", "电动机直联", "A式"))
                if unit_efficiency is not None and motor_efficiency is not None and direct_motor:
                    try:
                        unit_eta = decimal(unit_efficiency)
                        motor_eta = decimal(motor_efficiency)
                        if not (Decimal(1) <= unit_eta <= Decimal(100) and Decimal(1) <= motor_eta <= Decimal(100)):
                            raise ValueError("机组效率和电动机效率应位于1~100")
                        actual_efficiency = unit_eta / motor_eta * Decimal(100)
                        calculated["机组效率ηe_%"] = unit_eta
                        calculated["电动机效率ηm_%"] = motor_eta
                        calculated["最高通风机效率ηr_由式4_%"] = actual_efficiency
                        lookup_trace.append({
                            "step_type": "公式计算",
                            "formula": "ηr=(ηe/ηm)×100（百分数输入）",
                            "standard": "GB 19761-2020式(4)",
                            "inputs": {"ηe_%": str(unit_eta), "ηm_%": str(motor_eta)},
                            "value": str(actual_efficiency),
                        })
                    except (ValueError, ArithmeticError) as exc:
                        return unable(str(values.get("record_id", "")), pack, f"按GB 19761式(4)换算最高通风机效率失败：{exc}", ["机组效率ηe", "电动机效率ηm"])
        if actual_efficiency is None and not outer_rotor:
            eta_fields = [
                ("流量", ("flow_m3h", "flow", "流量")),
                ("叶轮功率", ("impeller_power_kw", "impeller_power", "叶轮功率")),
            ]
            eta_missing = _missing(values, eta_fields)
            if pressure_for_calc is None:
                eta_missing.append("风机压力（或出口/进口滞止压力）")
            if compression is None:
                eta_missing.append("压缩性修正系数")
            if eta_missing:
                # 效率只用于最终三级比较；当压力系数、比转速和机号
                # 已经可以唯一确定标准行时，不能因缺少式(1)的备用
                # 物理输入而在查表前丢失标准阈值。保留“直接效率”
                # 和“公式计算参数”两条补充路径，最后统一返回无法判定。
                defer_efficiency_missing = True
                efficiency_missing_fields = list(dict.fromkeys(["风机效率", *eta_missing]))
            try:
                if not defer_efficiency_missing:
                    flow_m3s = decimal(_value(values, *eta_fields[0][1])) / Decimal(3600)
                    pressure = decimal(pressure_for_calc)
                    impeller_power_kw = decimal(_value(values, *eta_fields[1][1]))
                    if min(flow_m3s, pressure, impeller_power_kw, decimal(compression)) <= 0:
                        raise ValueError("流量、压力、叶轮功率和压缩性修正系数必须为正")
                    actual_efficiency = flow_m3s * pressure * decimal(compression) / (Decimal(1000) * impeller_power_kw) * Decimal(100)
                    calculated["最高通风机效率ηr_%"] = actual_efficiency
                    lookup_trace.append({
                        "step_type": "公式计算",
                        "formula": "ηr=qvsg1·pF·kp/(1000Pr)×100%",
                        "standard": "GB 19761-2020式(1)",
                        "inputs": {"qvsg1_m3s": str(flow_m3s), "pF_Pa": str(pressure), "kp": str(compression), "Pr_kW": str(impeller_power_kw)},
                        "value": str(actual_efficiency),
                    })
            except (ValueError, ArithmeticError) as exc:
                return unable(str(values.get("record_id", "")), pack, f"最高通风机效率计算失败：{exc}", ["最高通风机效率"])
        if actual_efficiency is None and not defer_efficiency_missing:
            return unable(str(values.get("record_id", "")), pack, f"缺少{metric_name}", [metric_name])
        if actual_efficiency is None:
            actual_metrics: dict[str, Any] = {}
        else:
            try:
                actual_efficiency = decimal(actual_efficiency)
            except ValueError:
                return unable(str(values.get("record_id", "")), pack, f"{metric_name}不是有效数值", [metric_name])
            if not Decimal(1) <= actual_efficiency <= Decimal(100):
                return unable(str(values.get("record_id", "")), pack, f"{metric_name}应按百分数本值填写且位于1~100", [metric_name])
            actual_metrics = {"风机效率_%": actual_efficiency, f"{metric_name}_%": actual_efficiency}
        # 轴流通风机的标准分档轴是轮毂比。必须先区分“缺少必填参数”
        # 与“参数已给但超出标准范围”，避免用0代入查表后误报为范围外。
        if category_type == "轴流":
            hub_ratio = _value(values, "hub_ratio", "轮毂比")
            if hub_ratio is None:
                return _attach_metrics(unable(str(values.get("record_id", "")), pack, "轴流通风机缺少轮毂比", ["轮毂比"]), actual_metrics, calculated)
            try:
                if result := _range_or_unable(values, pack, "轮毂比", ("hub_ratio", "轮毂比"), Decimal(0), Decimal(1), minimum_inclusive=False):
                    return _attach_metrics(result, actual_metrics, calculated)
            except ValueError:
                return _attach_metrics(unable(str(values.get("record_id", "")), pack, "轮毂比不是有效数值", ["轮毂比"]), actual_metrics, calculated)
        # 类别字符串“外转子电机直联前向多翼离心风机”同时包含“离心”，
        # 不能用简单子串把它误选到表1/表2；先按标准产品类别确定表族。
        if outer_rotor:
            tables = [table for table in pack.get("tables", []) if table.get("type") == "外转子"]
        elif category_type == "轴流":
            tables = [table for table in pack.get("tables", []) if table.get("type") == "轴流"]
        else:
            tables = [table for table in pack.get("tables", []) if table.get("type") == "离心"]

        def table_number(table: dict[str, Any]) -> int:
            """Return the standard table number used by fallback row IDs."""
            if table.get("type") == "外转子":
                return 4
            if table.get("type") == "轴流":
                return 3
            return 1 if re.search(r"表\s*[１1](?:\D|$)", str(table.get("title", ""))) else 2

        def row_data_id(table: dict[str, Any], row: dict[str, Any], index: int) -> str:
            # 标准包行已有稳定ID；仅旧/临时包使用表内行号回退。
            return str(row.get("data_id") or f"GB19761-T{table_number(table)}-R{index:02d}")

        def lookup_miss(
            table: dict[str, Any],
            status: str,
            rows: list[dict[str, Any]],
            extra: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            item: dict[str, Any] = {
                "step_type": "精确查表",
                "table": table.get("title", ""),
                "data_ids": [
                    row_data_id(table, row, index)
                    for index, row in enumerate(table.get("rows", []), start=1)
                    if any(row is candidate for candidate in rows)
                ],
                "match_status": status,
                "source_clause": "表1～表4",
                "source_page": table.get("source_page", ""),
            }
            if extra:
                item.update(extra)
            return item

        selected = next((table for table in tables if (
            any(_interval_hit(psi, row.get("psi", "")) for row in table.get("rows", []))
            if table.get("has_ns")
            else any(_interval_hit(_value(values, "hub_ratio", "轮毂比") or Decimal(0), row.get("psi", "")) for row in table.get("rows", []))
        )), None)
        if selected is None:
            misses: list[dict[str, Any]] = []
            for table in tables:
                primary_label = "轮毂比" if not table.get("has_ns") else "压力系数"
                primary_value = _value(values, "hub_ratio", "轮毂比") if not table.get("has_ns") else psi
                misses.append(lookup_miss(
                    table,
                    f"{primary_label}档位未命中",
                    list(table.get("rows", [])),
                    {
                        "primary_value": str(primary_value),
                        "primary_ranges": [row.get("psi", "") for row in table.get("rows", [])],
                    },
                ))
            result = _attach_metrics(out_of_scope(str(values.get("record_id", "")), pack, "压力系数或风机型式超出标准表范围"), actual_metrics, calculated)
            if misses:
                return _attach_lookup_trace(result, pack, "/".join(item.get("table", "") for item in misses), lookup_trace + misses)
            return result
        secondary_name = "specific_speed" if selected.get("has_ns") else "hub_ratio"
        secondary = _value(values, secondary_name, "比转速" if secondary_name == "specific_speed" else "轮毂比")
        primary_rows = [
            item for item in selected.get("rows", [])
            if _interval_hit(psi, item.get("psi", ""))
        ] if selected.get("has_ns") else list(selected.get("rows", []))
        secondary_ranges = [
            item.get("ns", "") if selected.get("has_ns") else item.get("psi", "")
            for item in primary_rows
        ]

        def secondary_early_exit(
            status: str,
            reason: str,
            value: Any,
            missing_fields: list[str] | None = None,
        ) -> EvaluationResult:
            # 主压力系数已经唯一确定标准表时，次轴缺失/非法也要保留
            # 已检查过的候选标准行；不能因为无法继续计算就丢失来源。
            miss = lookup_miss(
                selected,
                status,
                primary_rows,
                {
                    "primary_value": str(psi),
                    "secondary_value": "" if value is None else str(value),
                    "secondary_ranges": secondary_ranges,
                    "matching": "型式+压力系数+比转速/轮毂比",
                    "no_interpolation": True,
                },
            )
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, reason, missing_fields),
                actual_metrics,
                calculated,
            )
            return _attach_lookup_trace(result, pack, str(selected.get("title", "")), lookup_trace + [miss])

        if secondary is None and secondary_name == "specific_speed":
            # GB 19761-2020式(6)/(7)：离心通风机比转速由进口滞止容积流量、
            # 压力、kp、进口滞止密度和转速计算；双吸按q/2。
            ns_fields = [
                ("流量", ("flow_m3h", "flow", "流量")),
                ("转速", ("rated_speed_rpm", "speed", "转速")),
                ("进口滞止密度", ("inlet_stagnation_density", "density", "进口滞止密度")),
            ]
            ns_missing = _missing(values, ns_fields)
            if pressure_for_calc is None:
                ns_missing.append("风机压力")
            if ns_missing:
                return secondary_early_exit("比转速/轮毂比未提供", "缺少比转速，且缺少按GB 19761式(6)/(7)计算的物理参数", None, ns_missing)
            try:
                q = decimal(_value(values, *ns_fields[0][1])) / Decimal(3600)
                if "双吸" in category or str(_value(values, "suction", "单双吸") or "") == "双吸":
                    q /= Decimal(2)
                speed = decimal(_value(values, *ns_fields[1][1]))
                density = decimal(_value(values, *ns_fields[2][1]))
                p_f = decimal(pressure_for_calc)
                if min(q, speed, density, p_f) <= 0:
                    raise ValueError("流量、转速、密度和压力必须为正")
                denominator_base = Decimal("1.2") * p_f * decimal(compression or 1) / density
                denominator = (denominator_base.ln() * Decimal("0.75")).exp()
                secondary = Decimal("5.54") * speed * (q.ln() * Decimal("0.5")).exp() / denominator
                calculated["比转速"] = secondary
                lookup_trace.append({"step_type": "公式计算", "formula": "ns=5.54n√q/(1.2pFkp/ρ)^0.75", "value": str(secondary), "suction_adjustment": "双吸q/2" if q * 2 == decimal(_value(values, *ns_fields[0][1])) else "单吸"})
            except (ValueError, ArithmeticError) as exc:
                return secondary_early_exit("比转速/轮毂比计算失败", f"比转速计算失败：{exc}", None, ["比转速/轮毂比"])
        if secondary is None:
            return secondary_early_exit("比转速/轮毂比未提供", "缺少比转速或轮毂比", None, ["比转速/轮毂比"])
        # 比转速/轮毂比可能来自批量粘贴的文本；在查表前显式做数值
        # 解析，避免 decimal() 异常穿透评价服务，破坏批量结果结构。
        try:
            secondary = decimal(secondary)
        except ValueError:
            return secondary_early_exit("比转速/轮毂比不是有效数值", "比转速或轮毂比不是有效数值", secondary, ["比转速/轮毂比"])
        if secondary <= 0:
            return secondary_early_exit("比转速/轮毂比非正", "比转速或轮毂比必须为正数", secondary, ["比转速/轮毂比"])
        calculated[secondary_name] = secondary
        row = next((item for item in selected["rows"] if (
            _interval_hit(psi, item.get("psi", "")) and _interval_hit(secondary, item.get("ns", ""))
            if selected.get("has_ns")
            else _interval_hit(secondary, item.get("psi", ""))
        )), None)
        if row is None:
            miss = lookup_miss(
                selected,
                "比转速/轮毂比档位未命中",
                primary_rows,
                {
                    "pressure_coefficient": str(psi),
                    "secondary_value": str(secondary),
                    "secondary_ranges": [
                        item.get("ns", "") if selected.get("has_ns") else item.get("psi", "")
                        for item in primary_rows
                    ],
                    "matching": "型式+压力系数+比转速/轮毂比",
                },
            )
            result = _attach_metrics(out_of_scope(str(values.get("record_id", "")), pack, "比转速或轮毂比超出标准表范围"), actual_metrics, calculated)
            return _attach_lookup_trace(result, pack, str(selected.get("title", "")), lookup_trace + [miss])
        machine_no = decimal(_value(values, "machine_no", "机号"))
        no_idx = next((idx for idx, item in enumerate(selected["no_ranges"]) if _interval_hit(machine_no, item["no"])), None)
        selected_title = str(selected.get("title", ""))
        row_index = next((index for index, item in enumerate(selected["rows"], start=1) if item is row), None)
        if no_idx is None:
            lookup = lookup_miss(
                selected,
                "机号档位未命中",
                [row],
                {
                    "data_id": row_data_id(selected, row, row_index or 1),
                    "pressure_coefficient": str(psi),
                    "secondary_value": str(secondary),
                    "machine_no": str(machine_no),
                    "machine_ranges": [item.get("no", "") for item in selected.get("no_ranges", [])],
                    "matching": "型式+压力系数+比转速/轮毂比+机号",
                },
            )
            result = _attach_metrics(out_of_scope(str(values.get("record_id", "")), pack, "机号超出标准表范围"), actual_metrics, calculated)
            return _attach_lookup_trace(result, pack, selected_title, lookup_trace + [lookup])
        raw_thresholds = row["eff"][no_idx * 3 : no_idx * 3 + 3]
        if len(raw_thresholds) != 3:
            lookup = lookup_miss(
                selected,
                "三级指标不完整",
                [row],
                {
                    "data_id": row_data_id(selected, row, row_index or 1),
                    "machine_interval": selected["no_ranges"][no_idx].get("no", ""),
                    "matching": "型式+压力系数+比转速/轮毂比+机号",
                },
            )
            result = _attach_metrics(unable(str(values.get("record_id", "")), pack, "命中的通风机标准档位缺少完整的三级指标"), actual_metrics, calculated)
            return _attach_lookup_trace(result, pack, selected_title, lookup_trace + [lookup])
        # fan.json按标准表头顺序保存为[3级,2级,1级]，评价器统一使用[1级,2级,3级]。
        thresholds = [
            decimal(raw_thresholds[2]) if raw_thresholds[2] is not None else None,
            decimal(raw_thresholds[1]) if raw_thresholds[1] is not None else None,
            decimal(raw_thresholds[0]) if raw_thresholds[0] is not None else None,
        ]
        # 表2标题本身也包含上限“ψ<0.95”，不能用数值子串判断表号；
        # 以标准表题的显式“表1/表１”标识为准。
        dash_levels = [
            f"{level}级" for level, raw_value in zip((3, 2, 1), raw_thresholds) if raw_value is None
        ]
        if dash_levels and all(item is None for item in thresholds):
            lookup = {
                "step_type": "精确查表",
                "table": selected["title"],
                # 标准包行已有稳定ID；旧/临时包才按表内行号回退。
                "data_id": row_data_id(selected, row, row_index or 1),
                "source_page": selected.get("source_page", ""),
                "source_clause": "表1～表4",
                "matching": "型式+压力系数+比转速/轮毂比+机号",
                "query_conditions": {
                    "category": category,
                    "pressure_coefficient": str(psi),
                    secondary_name: str(secondary),
                    "machine_no": str(machine_no),
                },
                "pressure_interval": row.get("psi", ""),
                "secondary_interval": row.get("ns", "") if selected.get("has_ns") else row.get("psi", ""),
                "machine_interval": selected["no_ranges"][no_idx].get("no", ""),
                "standard_marker": "—",
                "no_data": True,
                "no_data_levels": dash_levels,
                "dash_semantics": "—表示该等级不作要求，不参与比较",
            }
            result = unable(str(values.get("record_id", "")), pack, "命中的通风机标准档位全部为‘—’或无数据，无法判定")
            result.actual_metrics = dict(actual_metrics)
            return _attach_lookup_trace(result, pack, str(selected["title"]), lookup_trace + [lookup])
        structure_adjustments = [Decimal(0), Decimal(0), Decimal(0)]
        yes = lambda key, label: str(_value(values, key, label) or "").strip() in {"是", "是的", "true", "1"}
        if selected.get("type") == "离心":
            if "双吸" in str(_value(values, "suction", "单双吸") or ""):
                structure_adjustments = [item - delta for item, delta in zip(structure_adjustments, (Decimal(1), Decimal(1), Decimal(3)))]
            if yes("hvac_use", "是否暖通空调用"):
                structure_adjustments = [item - delta for item, delta in zip(structure_adjustments, (Decimal(1), Decimal(1), Decimal(3)))]
            if yes("inlet_box", "是否带进气箱"):
                structure_adjustments = [item - Decimal(4) for item in structure_adjustments]
        elif selected.get("type") == "轴流":
            if yes("inlet_box", "是否带进气箱"):
                structure_adjustments = [item - Decimal(3) for item in structure_adjustments]
            if yes("diffuser", "是否带扩散筒"):
                reference = next((item for item in selected["rows"] if item.get("psi") == "0.55≤γ<0.75"), None)
                if reference is not None:
                    reference_raw = reference["eff"][6:9]
                    if len(reference_raw) == 3 and all(item is not None for item in reference_raw):
                        reference_thresholds = [decimal(reference_raw[2]), decimal(reference_raw[1]), decimal(reference_raw[0])]
                        thresholds = [max(current, reference_value) if current is not None else None for current, reference_value in zip(thresholds, reference_thresholds)]
            else:
                structure_adjustments = [item + Decimal(2) for item in structure_adjustments]
            if yes("variable_blade", "是否动叶可调") and not yes("inlet_box", "是否带进气箱") and not yes("diffuser", "是否带扩散筒"):
                thresholds = [max(current, fixed) if current is not None else None for current, fixed in zip(thresholds, (Decimal("89.5"), Decimal("87"), Decimal("82")))]
            if yes("reversible", "是否可逆转"):
                structure_adjustments = [item - Decimal(8) for item in structure_adjustments]
        if any(structure_adjustments):
            thresholds = [value + adjustment if value is not None else None for value, adjustment in zip(thresholds, structure_adjustments)]
            calculated.update({f"结构修正_{level}级_百分点": value for level, value in zip((1, 2, 3), structure_adjustments)})
            lookup_trace.append({"step_type": "结构条件修正", "table": selected["title"], "adjustments_percentage_points": [str(item) for item in structure_adjustments]})
        calculated["压力系数"] = psi
        calculated[secondary_name] = decimal(secondary)
        lookup_trace.append({
            "step_type": "精确查表",
            "table": selected["title"],
            "data_id": row_data_id(selected, row, row_index or 1),
            "source_page": selected.get("source_page", ""),
            "source_clause": "表1～表4",
            "matching": "型式+压力系数+比转速/轮毂比+机号",
            "query_conditions": {
                "category": category,
                "pressure_coefficient": str(psi),
                secondary_name: str(secondary),
                "machine_no": str(machine_no),
            },
            "pressure_interval": row.get("psi", ""),
            "secondary_interval": row.get("ns", "") if selected.get("has_ns") else row.get("psi", ""),
            "machine_interval": selected["no_ranges"][no_idx].get("no", ""),
            "standard_marker": "—" if dash_levels else "",
            "no_data": bool(dash_levels),
            "no_data_levels": dash_levels,
            "dash_semantics": "—表示该等级不作要求，不参与比较" if any(item is None for item in raw_thresholds) else "",
            "match_status": "命中",
        })
        limits = {
            f"{i + 1}级效率_%": thresholds[i]
            for i in range(3)
            if thresholds[i] is not None
        }
        if defer_efficiency_missing:
            metric_label = "机组效率ηe" if outer_rotor else "风机效率"
            formula_label = "GB19761式(3)" if outer_rotor else "GB19761式(1)"
            result = unable(
                str(values.get("record_id", "")),
                pack,
                f"缺少{metric_label}，且缺少按{formula_label}计算的物理参数，无法进行能效等级比较",
                efficiency_missing_fields or [metric_label],
            )
            result.actual_metrics = dict(actual_metrics)
            result.calculated_metrics = dict(calculated)
            result.limits = limits
            return _attach_lookup_trace(result, pack, selected_title, lookup_trace)
        actual = actual_efficiency
        conclusion, comparisons = grade_three_optional(actual, thresholds, ComparisonDirection.GREATER_OR_EQUAL)
        actual_metrics = {"风机效率_%": actual}
        actual_metrics[f"{metric_name}_%"] = actual
        return _result(values, pack, conclusion, actual_metrics, calculated, limits, comparisons, selected["title"], lookup_trace, clause="表1～表4")
