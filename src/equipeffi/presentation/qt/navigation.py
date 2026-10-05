"""一级导航与最小跨页导航契约。

一级导航只包含真实存在的产品页面；**不得**出现 placeholder。
Phase 8 起「批量评价」是真实页面（Excel 批量输入/输出）。
参数库当前无独立用户需求（标准参数/限值/依据归标准详情）。

导航契约刻意保持极小，只承担三件事：

```text
切页
选择目标对象
载入已有对象
```

**不建立**：事件总线、通用 Router Framework、Page Base Class 体系、
全局 DI 容器、复杂导航状态机。
"""
from __future__ import annotations

from typing import Protocol

#: 一级导航（顺序即产品任务顺序）。每一项都必须是真实页面。
PAGES: tuple[str, ...] = ("首页", "标准库", "新建分析", "批量评价", "分析记录", "设置")


class ShellNavigator(Protocol):
    """页面用来请求切换的极小接口（由 MainWindow 实现）。"""

    def open_home(self) -> None: ...

    def open_standards(self, standard_code: str | None = None) -> None: ...

    def open_analysis(self, workspace_id: str | None = None) -> None: ...

    def open_batch(self) -> None: ...

    def open_records(self, record_id: str | None = None) -> None: ...

    def open_settings(self) -> None: ...
