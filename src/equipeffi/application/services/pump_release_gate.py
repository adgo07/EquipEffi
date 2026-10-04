"""离心泵发布支持门禁的**单一事实源**（Phase 6 G06）。

为什么需要它：Phase 5 提升了 `pump_chemical` 的支持状态，但当时只改了统一
纵向切片路径（`CentrifugalPumpAnalysisService`）。遗留 `EvaluationService`
（供 `--json` / `ApplicationApi` / JSONL / CLI / `--web` 使用）另有一份硬编码，
因此**共享 Application/CLI 语义**仍把石化泵错误短路成 `NOT_IN_RELEASE_SCOPE`
（独立验收登记为 `QA-P5-001` / `QA-P5-002(b)`）。

本模块把该策略收敛为一份，两个使用方都从这里取：

    CentrifugalPumpAnalysisService._release_support
    EvaluationService._pump_release_support

放这里而不是放在 `lifecycle` 包里：`lifecycle` 是**设备无关**的生命周期契约，
不得出现泵专属知识（Phase 4 G01 的边界）。
"""
from __future__ import annotations

#: GB 19762—2025 离心泵内部的 rule profile 集合。
PUMP_RULE_PROFILES: tuple[str, ...] = ("pump_water", "pump_chemical")

#: 发布支持门禁取值（只有这两个值是"发布能力"，`None` 表示没有已批准路由）。
SUPPORTED = "SUPPORTED"
NOT_IN_RELEASE_SCOPE = "NOT_IN_RELEASE_SCOPE"

#: 发布门禁策略：Phase 5 Stage D 独立验收通过后，两个 rule profile 均为正式支持。
PUMP_RELEASE_SUPPORT: dict[str, str] = {
    "pump_water": SUPPORTED,
    "pump_chemical": SUPPORTED,
}


def pump_release_support(rule_profile: str | None) -> str | None:
    """返回该内部 rule profile 的发布支持状态；无已批准路由时返回 `None`。"""

    if rule_profile is None:
        return None
    return PUMP_RELEASE_SUPPORT.get(str(rule_profile), None)
