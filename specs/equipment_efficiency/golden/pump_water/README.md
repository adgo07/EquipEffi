# `pump_water` Golden Case 首批

状态：`REVIEWED`（Phase 1 技术复核完成；Solution Review 最终批准待定）

本目录的 7 个案例覆盖：

| 案例 | 目的 | 关键证据 |
|---|---|---|
| `GC-PUMP-001-NORMAL` | 单级单吸正常计算 | T3-01、公式、三级阈值 |
| `GC-PUMP-002-LOWER-INCLUSIVE` | 下端点包含 | `5 ≤ Q` 命中 T3-01 |
| `GC-PUMP-002-UPPER-INCLUSIVE` | 上端点包含 | `Q=300` 仍命中 T3-01 |
| `GC-PUMP-002-UPPER-SWITCH` | 开区间切换 | `Q=300.0001` 命中 T3-02 |
| `GC-PUMP-002-OUTSIDE` | 不外推 | `Q=4.999` 不生成等级但保留派生量 |
| `GC-PUMP-003-MISSING-EFFICIENCY` | 缺失语义 | 保留公式/查表/限值，状态为 `INSUFFICIENT_DATA` |
| `GC-PUMP-004-UNKNOWN-CATEGORY` | 不允许默认类别 | “其他”不映射单级单吸、不生成比转速/等级 |

## 数值格式

- 输入和期望值中的十进制统一为字符串；每个 metric 同时提供稳定 `unit_id`。
- `input_basis=STANDARD_BEP`、`measurement_point=BEP` 是 `flow_m3h`、`head_m`、`pump_efficiency` 同属 GB 19762-2025 最高效率点的机器可读声明。
- `source_reference` 必须记录 `artifact_kind`、`artifact_path` 和 `artifact_sha256`；Schema 约束字段形状，文件存在性和指纹匹配由仓库验证器执行。
- `specific_speed` 使用独立 Decimal 计算后 `HALF_UP` 到 12 位；限值按当前契约候选保留 6 位；输出功率保留计算所需尾数。
- `expected_conclusion` 是展示层文本；真正的业务门控由 `expected_status`、稳定规则 ID 和期望指标共同完成。

从仓库根目录运行：

```powershell
python tools/validate_phase1_contracts.py --negative-probe
```

`--negative-probe` 必须拒绝 JSON number、非法 `unit_id` 和不存在的来源文件，且不把反例写入案例目录。

## 批准依据与限制

首批案例由当前标准包、标准 PDF 的路径与 SHA-256、其表号/页码 provenance、独立十进制重算和当前运行 trace 交叉复核，并显式记录了 `CURRENT_IMPLEMENTATION` 仅为辅助证据。标准 PDF 原件不随仓库提交；Solution Review 指定的具名标准责任人仍需补入 `review_owner` 后才能形成最终批准。不得静默改写已复核文件；若证据变化，应生成新案例版本。
