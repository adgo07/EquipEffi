"""最小生命周期错误契约（Phase 4 G03）。

设计原则：**只建立真实需要的最小语义**，不建立复杂异常继承树。

```text
LifecycleError          生命周期层根错误
└── AnalysisError       Use Case 的输入/状态错误（保留 Phase 3 名称以兼容既有调用方）
    └── RecordConflictError   正式记录不可变冲突（重复 record_id）
```

`AnalysisError` 同时继承 `ValueError`，因为这正是 Phase 3 以来的既有行为，
且既有调用方（UI / 测试）依赖该语义；Phase 4 不改变它。

`LifecycleError` 本身不继承 `ValueError`：生命周期层还承载持久化类失败，
把它们统统标记为"值错误"是不准确的。
"""
from __future__ import annotations


class LifecycleError(Exception):
    """生命周期层的根错误：Workspace / Record 的读取、写入与不可变冲突。"""


class AnalysisError(LifecycleError, ValueError):
    """统一分析入口的输入/状态错误；不得与业务"无法判定"混淆。"""


class RecordConflictError(AnalysisError):
    """正式记录不可变冲突：`record_id` 已存在，拒绝覆盖。"""


class LifecyclePersistenceError(LifecycleError):
    """持久化失败。

    必须始终以 `raise ... from <root cause>` 抛出，保留底层根因
    （`sqlite3.Error` / `OSError` 等），使调用方能够区分"保存失败"与
    "保存成功"——**不得**在失败后让 UI 认为保存成功。
    """
