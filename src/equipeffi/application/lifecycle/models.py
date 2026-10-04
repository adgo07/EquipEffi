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

#: `payload` 中存放"哪些键参与业务指纹"的保留元数据键。
#:
#: 为什么必须随快照持久化：`WorkspaceSnapshot` 在**跨进程恢复**后（只从
#: `records.sqlite` 读回）必须能自建指纹，而 Phase 4 不允许新增数据库列 /
#: 新增迁移。若改用进程内的全局注册，指纹就会依赖"某个产品模块是否恰好被
#: import 过"——这是运行时耦合，且会让不同业务输入算出相同指纹。
#:
#: 因此业务键集合作为**已持久化的自描述元数据**存放在既有 JSON 载荷里：
#: 不新增列、不新增迁移、不依赖导入顺序、不依赖全局可变状态。
BUSINESS_KEYS_METADATA_KEY = "_business_keys"

#: `payload` 中**不参与**业务指纹的生命周期级登记键（设备无关，故可在此声明）。
#:
#: 仅用于 Phase 4 之前、未携带 `BUSINESS_KEYS_METADATA_KEY` 的历史快照回退。
RESERVED_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {BUSINESS_KEYS_METADATA_KEY, "project_name", "equipment_no", "product_type"}
)


def business_keys_metadata(keys: "tuple[str, ...]") -> dict[str, list[str]]:
    """构造随快照持久化的业务键元数据载荷片段。

    由产品模块在写 Workspace 时合并进 `payload`；生命周期层不自行决定字段清单。
    """

    return {BUSINESS_KEYS_METADATA_KEY: list(keys)}


def business_key_names(payload: dict[str, Any]) -> tuple[str, ...]:
    """从已持久化的载荷中读出业务键名。

    1. 优先使用快照自己持久化的 `BUSINESS_KEYS_METADATA_KEY`（Phase 4 起写入）；
    2. 否则回退到"载荷中除生命周期级登记键以外的全部键"。

    回退分支只服务 Phase 4 之前的历史快照，且**完全由快照自身内容决定**：
    不读取任何进程内全局状态，因此同一份快照在任意进程、任意导入顺序下
    都得到同一指纹。历史快照里"当时为空的字段"本就未写入载荷，故该回退
    与写入当次 `PumpAnalysisRequest.request_fingerprint()` 的取值一致。
    """

    recorded = payload.get(BUSINESS_KEYS_METADATA_KEY)
    if isinstance(recorded, (list, tuple)):
        return tuple(str(name) for name in recorded)
    return tuple(sorted(name for name in payload if name not in RESERVED_PAYLOAD_KEYS))


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

        `business_keys` 省略时，使用**该快照自己持久化**的业务键元数据
        （`BUSINESS_KEYS_METADATA_KEY`），因此跨进程恢复不需要产品模块被导入，
        也不存在全局可变状态；未携带该元数据的历史快照按
        `business_key_names()` 的回退规则处理。
        """

        keys = business_key_names(self.payload) if business_keys is None else business_keys
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
