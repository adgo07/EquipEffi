"""设备无关的生命周期模型（Phase 4 G01）。

本模块只承载 **Workspace / Record 生命周期本身**的数据形状，刻意不认识任何设备：

- 不认识任何产品专属输入字段名（例如几何或工况点参数）；
- 不包含任何标准代码判定、等级、阈值或规则路由；
- 不导入 `equipeffi.domain` / `infrastructure` / `presentation`。

业务字段集合由**具体产品模块**声明并通过
`business_key_values()` 注入；本模块只负责"怎么算一个稳定指纹"，
不负责"哪些字段算业务字段"。

数据库形态：本模块的字段与 Phase 3 的 `records.sqlite` 列一一对应，
Phase 4 **不新增列、不新增迁移**。
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

#: 指纹载荷中"缺失值"的规范化文本。Phase 3 起即为 `"None"`，不得改变，
#: 否则既有 Workspace 的指纹会漂移。
_MISSING = "None"

#: 当前生命周期使用方的业务字段集合注册点。
#:
#: 为什么需要它：`WorkspaceSnapshot` 在**跨进程恢复**后（只从 `records.sqlite`
#: 读回）必须能自己重建指纹，而 Phase 4 又不允许新增列 / 新增迁移，因此这份
#: 字段清单只能来自进程内的注册，而不能写进数据库。
#:
#: 本模块仍然**不认识**任何具体字段名——这里存的只是"调用方声明的不透明键"。
#: 目前只有一个产品级入口，其内部各 rule profile 共用一套业务键，
#: 因此注册点是单值的；若将来出现第二个真实设备，应改为按 device/profile 分派，
#: 而不是在这里堆叠字段名。
_registered_business_keys: tuple[str, ...] = ()


def register_business_keys(keys: tuple[str, ...]) -> None:
    """登记业务字段集合（由产品模块在模块级调用一次）。"""

    global _registered_business_keys
    _registered_business_keys = tuple(keys)


def registered_business_keys() -> tuple[str, ...]:
    """当前登记的业务字段集合。"""

    return _registered_business_keys


def normalize_fingerprint_value(value: Any) -> str:
    """把单个业务字段规范化成指纹载荷里的稳定文本。

    这是**唯一**的取值规则；`PumpAnalysisRequest` 与 `WorkspaceSnapshot`
    必须共用它，不得各自维护一份。
    """

    return _MISSING if value is None else str(value)


def stable_fingerprint(values: dict[str, Any]) -> str:
    """对一组业务字段取稳定指纹。

    这是**唯一**的指纹算法：JSON（`ensure_ascii=False`、键排序、
    紧凑分隔符）→ UTF-8 → SHA-256 十六进制。
    """

    payload = {key: normalize_fingerprint_value(value) for key, value in values.items()}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkspaceSnapshot:
    """可变草稿的持久化形状。

    `payload` 存放产品专属输入字段；生命周期层只把它当作不透明字典。
    """

    workspace_id: str
    standard_code: str
    device_type: str
    product_category: str
    rule_profile: str | None
    as_of: str
    payload: dict[str, Any]
    schema_version: int
    created_at_utc: str
    updated_at_utc: str
    #: 单调递增修订号；每次 save 都 +1。Finalize 用它拒绝"旧结果 + 新输入"。
    revision: int = 1

    def business_key_values(self, business_keys: tuple[str, ...]) -> dict[str, Any]:
        """按**调用方声明的**业务键集合取指纹输入。

        本方法刻意不认识任何具体字段名：`business_keys` 由产品模块提供，
        因此生命周期模型不构成第二处"业务字段清单"。
        """

        values: dict[str, Any] = {
            "product_category": self.product_category,
            "as_of": self.as_of,
        }
        for key in business_keys:
            values[key] = self.payload.get(key)
        return values

    def request_fingerprint(self, business_keys: tuple[str, ...] | None = None) -> str:
        """草稿当前输入的指纹；与 `PumpAnalysisRequest.request_fingerprint()` 同源。

        `business_keys` 省略时使用当前登记的业务字段集合（见
        `register_business_keys`），使跨进程恢复场景无需外部上下文即可重建指纹。
        """

        keys = registered_business_keys() if business_keys is None else business_keys
        return stable_fingerprint(self.business_key_values(keys))


@dataclass(frozen=True)
class RecordSnapshot:
    """不可变正式记录的持久化形状。

    字段与 Phase 3 的 `record` 表列一一对应；Phase 4 未增删任何字段。
    """

    record_id: str
    workspace_id: str | None
    standard_code: str
    standard_version: str
    device_type: str
    product_category: str
    rule_profile: str | None
    as_of: str
    evaluation_status: str
    grade: str | None
    ui_conclusion: str
    input_snapshot: dict[str, Any]
    result_snapshot: dict[str, Any]
    reference_snapshot: dict[str, Any]
    ruleset_version: str
    calculator_version: str
    numeric_profile_id: str
    canonical_version: str
    canonical_package_hash: str
    result_contract_version: str
    schema_version: int
    created_at_utc: str
    finalized_at_utc: str
