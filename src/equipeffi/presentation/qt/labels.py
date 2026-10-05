"""面向用户的显示文案（Qt 侧薄转发，Phase 5 G03 / Phase 8 统一来源）。

**Phase 8 起本模块不再定义业务文案**：唯一来源是 Application 契约
`centrifugal_pump_analysis_service`（Qt 白名单允许导入的契约模块），
这样 Qt 与 Excel 的用户可见结论**不可能**各自漂移。

`support_status` 是**发布门禁维度**，与 `evaluation_status`（业务判定）互不冒充。
UI 只显示中文文案，不泄露内部英文枚举值。

`NOT_IN_RELEASE_SCOPE` 枚举**继续保留**：它仍用于

- Phase 3/4 期间已固化的历史 Record（快照里存的就是当时的值，显示即为当时事实）；
- 其他未发布 Profile（如 `transformer`）；
- 已登记的发布表面 deviation（遗留 JSON / Web / V4 等非正式入口）。
"""
from __future__ import annotations

from typing import Any

from ...application.services.centrifugal_pump_analysis_service import (
    ISSUE_CODE_LABELS,
    SUPPORT_STATUS_LABELS,
    USER_CONCLUSION_FALLBACK,
    USER_CONCLUSION_UNCERTAIN_CATEGORY,
    format_metric,
    issue_code_texts,
    support_status_text,
    user_conclusion_text,
)

__all__ = [
    "ISSUE_CODE_LABELS",
    "SUPPORT_STATUS_LABELS",
    "USER_CONCLUSION_FALLBACK",
    "USER_CONCLUSION_UNCERTAIN_CATEGORY",
    "format_metric",
    "issue_code_texts",
    "support_status_text",
    "user_conclusion_text",
]


def format_display_number(value: Any, *, name: str = "") -> str:
    """兼容旧调用点：转发到共享的 `format_metric`。"""

    return format_metric(value, name=name)
