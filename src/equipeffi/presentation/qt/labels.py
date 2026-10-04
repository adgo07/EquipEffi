"""面向用户的 `support_status` 显示文案（Phase 5 G03）。

`support_status` 是**发布门禁维度**，与 `evaluation_status`（业务判定）互不冒充。
UI 只显示中文文案，不泄露内部英文枚举值。

`NOT_IN_RELEASE_SCOPE` 枚举**继续保留**：它仍用于

- Phase 3/4 期间已固化的历史 Record（快照里存的就是当时的值，显示即为当时事实）；
- 其他未发布 Profile（如 `transformer`）；
- 已登记的发布表面 deviation（遗留 JSON / Web / V4 等非正式入口）。
"""
from __future__ import annotations

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
