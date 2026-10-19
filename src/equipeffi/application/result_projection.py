"""Stable metric identities and display metadata for formal pump results.

The values in this projection are serialized decimal text copied from the
Application evaluator output. This module does not calculate, round, or infer
business values from display labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class PumpResultMetric:
    """One pump result metric with stable identity and explicit unit."""

    metric_id: str
    value: str
    unit: str
    display_name: str

    def as_dict(self) -> dict[str, str]:
        return {
            "metric_id": self.metric_id,
            "value": self.value,
            "unit": self.unit,
            "display_name": self.display_name,
            "value_representation": "decimal_text",
        }


@dataclass(frozen=True)
class _MetricDefinition:
    metric_id: str
    source: Literal["calculated_metrics", "limits"]
    source_key: str
    display_name: str
    unit: str


# Consumers should import IDs from this map instead of duplicating names or
# attempting to resolve them from translated display text.
PUMP_METRIC_IDS: dict[str, str] = {
    "suction_factor": "pump.suction_factor",
    "stage_count": "pump.stage_count",
    "flow_for_specific_speed": "pump.flow_for_specific_speed",
    "head_per_stage": "pump.head_per_stage",
    "specific_speed": "pump.specific_speed",
    "output_power": "pump.output_power",
    "c1": "pump.c1",
    "c2": "pump.c2",
    "c3": "pump.c3",
    "base_efficiency": "pump.base_efficiency",
    "efficiency_correction": "pump.efficiency_correction",
    "specified_efficiency": "pump.specified_efficiency",
    "grade_1_efficiency_limit": "pump.grade_1_efficiency_limit",
    "grade_2_efficiency_limit": "pump.grade_2_efficiency_limit",
    "grade_3_efficiency_limit": "pump.grade_3_efficiency_limit",
}

PUMP_RESULT_METRIC_DEFINITIONS: tuple[_MetricDefinition, ...] = (
    _MetricDefinition(PUMP_METRIC_IDS["suction_factor"], "calculated_metrics",
                      "suction_factor", "吸入方式系数", "1"),
    _MetricDefinition(PUMP_METRIC_IDS["stage_count"], "calculated_metrics",
                      "stage_count", "级数", "级"),
    _MetricDefinition(PUMP_METRIC_IDS["flow_for_specific_speed"], "calculated_metrics",
                      "q_for_ns_m3s", "比转速用流量（m³/s）", "m³/s"),
    _MetricDefinition(PUMP_METRIC_IDS["head_per_stage"], "calculated_metrics",
                      "h_for_ns_m", "单级扬程（m）", "m"),
    _MetricDefinition(PUMP_METRIC_IDS["specific_speed"], "calculated_metrics",
                      "ns_raw", "比转速 ns", "1"),
    _MetricDefinition(PUMP_METRIC_IDS["output_power"], "calculated_metrics",
                      "输出功率_kW", "输出功率（kW）", "kW"),
    _MetricDefinition(PUMP_METRIC_IDS["c1"], "calculated_metrics",
                      "C1", "C1", "%"),
    _MetricDefinition(PUMP_METRIC_IDS["c2"], "calculated_metrics",
                      "C2", "C2", "%"),
    _MetricDefinition(PUMP_METRIC_IDS["c3"], "calculated_metrics",
                      "C3", "C3", "%"),
    _MetricDefinition(PUMP_METRIC_IDS["base_efficiency"], "calculated_metrics",
                      "基准效率_%", "基准效率 η_b（%）", "%"),
    _MetricDefinition(PUMP_METRIC_IDS["efficiency_correction"], "calculated_metrics",
                      "效率修正值_%", "效率修正值 Δη（%）", "%"),
    _MetricDefinition(PUMP_METRIC_IDS["specified_efficiency"], "calculated_metrics",
                      "规定点效率_%", "规定点效率 η₀（%）", "%"),
    _MetricDefinition(PUMP_METRIC_IDS["grade_1_efficiency_limit"], "limits",
                      "1级效率_%", "1级能效效率限值（%）", "%"),
    _MetricDefinition(PUMP_METRIC_IDS["grade_2_efficiency_limit"], "limits",
                      "2级效率_%", "2级能效效率限值（%）", "%"),
    _MetricDefinition(PUMP_METRIC_IDS["grade_3_efficiency_limit"], "limits",
                      "3级效率_%", "3级能效效率限值（%）", "%"),
)

# Compatibility maps retained for existing Qt and trace consumers. Their
# labels now come from the same definitions as the stable ID projection.
DERIVED_DISPLAY_NAMES: dict[str, str] = {
    item.source_key: item.display_name
    for item in PUMP_RESULT_METRIC_DEFINITIONS
    if item.source == "calculated_metrics"
}
THRESHOLD_DISPLAY_NAMES: dict[str, str] = {
    item.source_key: item.display_name
    for item in PUMP_RESULT_METRIC_DEFINITIONS
    if item.source == "limits"
}


def _decimal_text(value: Any) -> str:
    """Preserve the Application scalar's existing text without presentation rounding."""

    return str(value)


def project_pump_metrics(
    calculated_metrics: dict[str, Any] | None,
    limits: dict[str, Any] | None,
) -> dict[str, PumpResultMetric]:
    """Project existing evaluator outputs under stable IDs.

    Missing outputs are omitted. Values are copied as decimal text from the
    evaluator; this function performs no formula, unit conversion, or rounding.
    """

    sources = {
        "calculated_metrics": calculated_metrics or {},
        "limits": limits or {},
    }
    projected: dict[str, PumpResultMetric] = {}
    for definition in PUMP_RESULT_METRIC_DEFINITIONS:
        value = sources[definition.source].get(definition.source_key)
        if value is None:
            continue
        projected[definition.metric_id] = PumpResultMetric(
            metric_id=definition.metric_id,
            value=_decimal_text(value),
            unit=definition.unit,
            display_name=definition.display_name,
        )
    return projected
