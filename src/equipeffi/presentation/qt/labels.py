"""面向用户的 `support_status` 显示文案（Phase 5 G03）。

`support_status` 是**发布门禁维度**，与 `evaluation_status`（业务判定）互不冒充。
UI 只显示中文文案，不泄露内部英文枚举值。

`NOT_IN_RELEASE_SCOPE` 枚举**继续保留**：它仍用于

- Phase 3/4 期间已固化的历史 Record（快照里存的就是当时的值，显示即为当时事实）；
- 其他未发布 Profile（如 `transformer`）；
- 已登记的发布表面 deviation（遗留 JSON / Web / V4 等非正式入口）。
"""
from __future__ import annotations

from typing import Any

#: 发布支持状态文案。
#:
#: Record 详情直接使用同一张表：历史快照里存的是**当时的**发布门禁取值，
#: 因此"显示快照值"本身就等于"显示当时的事实"，不需要第二套文案，
#: 也不会把历史追溯改写成当前状态。
SUPPORT_STATUS_LABELS: dict[str, str] = {
    "SUPPORTED": "正式支持",
    "NOT_IN_RELEASE_SCOPE": "当前版本未支持",
}


def support_status_text(value: str | None) -> str:
    """把内部 `support_status` 转成用户可见文案。

    未知取值与缺失值回退为"—"，绝不把内部英文枚举直接展示给用户。
    """

    if not value:
        return "—"
    return SUPPORT_STATUS_LABELS.get(value, "—")

#: 业务判定提示码（`issue_codes`）→ 面向用户的中文说明。
#:
#: 机制与 `SUPPORT_STATUS_LABELS` 相同：内部码是**审计标识**，只允许出现在
#: 明确折叠的技术详情区；普通结果区只能显示中文说明。
#: **没有**中文映射的内部码一律**不展示**（而不是退化显示内部英文码）。
ISSUE_CODE_LABELS: dict[str, str] = {
    # 类别维度
    "CATEGORY_UNCERTAIN": "尚未确认产品类别",
    "CATEGORY_UNRESOLVED": "产品类别无法解析",
    "CATEGORY_MISSING": "缺少产品类别",
    "CATEGORY_NOT_APPLICABLE": "该产品类别不属于本标准适用范围",
    # 吸入方式 / 级数一致性
    "SUCTION_CATEGORY_CONFLICT": "吸入方式与所选类别不一致",
    "STAGE_CATEGORY_CONFLICT": "级数与所选类别不一致",
    # 数值字段非法
    "FLOW_INVALID": "流量数值无效",
    "HEAD_INVALID": "扬程数值无效",
    "SPEED_INVALID": "转速数值无效",
    "STAGES_INVALID": "级数数值无效",
    "EFFICIENCY_INVALID": "泵效率数值无效",
    "SUCTION_INVALID": "吸入方式取值无效",
    # 数值字段缺失
    "FLOW_MISSING": "缺少流量",
    "HEAD_MISSING": "缺少扬程",
    "SPEED_MISSING": "缺少转速",
    "STAGES_MISSING": "缺少级数",
    "EFFICIENCY_MISSING": "缺少泵效率",
    "SUCTION_MISSING": "缺少吸入方式",
    # 通用
    "INVALID_INPUT": "输入不合法",
}


def issue_code_texts(codes) -> list[str]:
    """把内部 `issue_codes` 转成用户可见中文说明（丢弃无映射的内部码）。"""

    texts: list[str] = []
    for code in codes or ():
        text = ISSUE_CODE_LABELS.get(str(code))
        if text and text not in texts:
            texts.append(text)
    return texts

#: 整数型业务量（不补小数位）。
_INTEGER_METRIC_NAMES: frozenset[str] = frozenset({"级数", "吸入方式系数"})


def format_metric(value: Any, *, name: str = "") -> str:
    """把计算派生量格式化为面向用户的 **2 位小数**文本（**仅用于显示**）。

    判定基于**数值类型**而不是按名字维护白名单——白名单必然漏掉真实键名，
    从而出现"该格式化的没格式化"。规则：

    ```text
    非数值 / None / 非有限   -> 原样返回（None -> "—"）
    整数值（如 级数=1）       -> 不补小数位（"1"）
    其它数值（含小数部分）     -> 固定 2 位小数（"79.79"）
    ```

    只影响本页文本：**不改变** `Decimal` 原始值、Numeric Profile、等级比较值、
    Record 精确快照或 Golden business truth。
    """

    if value is None:
        return "—"
    try:
        from decimal import Decimal, InvalidOperation

        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    if not number.is_finite():
        return str(value)
    if name in _INTEGER_METRIC_NAMES or number == number.to_integral_value():
        return str(number.to_integral_value())
    return f"{number:.2f}"
