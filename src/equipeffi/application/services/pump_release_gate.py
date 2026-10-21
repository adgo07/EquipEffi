"""离心泵发布支持门禁的单一事实源。

正式清水泵与石油化工泵分析服务通过本模块读取已批准的支持状态。
该状态只表述发布范围，不改变 Calculator 的专业规则。
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
