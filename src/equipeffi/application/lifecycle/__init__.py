"""设备无关的生命周期契约（Phase 4 G01）。

本包只包含 Phase 3 已真实证明属于公共工程结构的部分：

```text
models.py   WorkspaceSnapshot / RecordSnapshot / 稳定指纹算法
ports.py    WorkspaceRepository / RecordRepository Protocol
errors.py   LifecycleError / AnalysisError / RecordConflictError
```

刻意**不**包含（Phase 4 明确禁止）：

```text
GenericAnalysisService / UniversalEngine
通用 evaluator 基类
插件式生命周期框架
通用动态表单引擎
```

也刻意不属于本包：产品请求 / 结果契约、产品类别目录与路由、
evaluator 装配、阈值 / trace / grade、标准专属 provenance，
以及 Finalize 的具体业务允许状态政策。
这些继续留在 `application/services/centrifugal_pump_analysis_service.py`。
"""
from __future__ import annotations

from .errors import (
    AnalysisError,
    LifecycleError,
    LifecyclePersistenceError,
    RecordConflictError,
)
from .models import (
    RecordSnapshot,
    WorkspaceSnapshot,
    normalize_fingerprint_value,
    register_business_keys,
    registered_business_keys,
    stable_fingerprint,
)
from .ports import RecordRepository, WorkspaceRepository

__all__ = (
    "AnalysisError",
    "LifecycleError",
    "LifecyclePersistenceError",
    "RecordConflictError",
    "RecordRepository",
    "RecordSnapshot",
    "WorkspaceRepository",
    "WorkspaceSnapshot",
    "normalize_fingerprint_value",
    "register_business_keys",
    "registered_business_keys",
    "stable_fingerprint",
)
