# EquipEffi 设备能效业务规范 V0.1

状态：`DRAFT_FOR_SOLUTION_REVIEW`

本文件是 Phase 1 的业务语义草案，不是 Phase 1 通过声明，也不授权进入 Phase 2。它冻结业务对象、评价生命周期、支持状态和证据优先级；具体标准事实由 Canonical 候选包、Profile Schema、Ruleset 和已批准 Golden Case 共同约束。

## 1. 目标与边界

EquipEffi 对设备的设计值、额定值或铭牌值进行可追溯的标准评价。一次评价必须能够回答：

1. 输入属于哪个公共设备类型和内部 Profile；
2. 使用哪个标准包、版本和适用日期；
3. 哪些输入经过了什么单位和格式归一化；
4. 命中了哪些标准表、记录、公式或目录条件；
5. 实际指标、计算指标和标准限值分别是什么；
6. 结论是否真的可判定，以及不能判定的原因。

Phase 1 只冻结这些语义和契约，不实施批量 Profile 迁移、完整 UI、持久化表、Excel、报告或 Phase 2 功能。

## 2. 业务对象

| 对象 | 责任 | 最小稳定标识 | 可变性 |
|---|---|---|---|
| `public_device_type` | V4/用户看到的公共设备类别，例如 `centrifugal_pump` | 公共 code | 受产品契约约束 |
| `profile_id` | 具体评价口径，例如 `pump_water` | Profile code | 受 Profile Schema 约束 |
| `standard` | 标准身份、适用日期和来源引用 | `standard_code` | 由标准事实包版本化 |
| `standard_pack` | 某 Profile 可加载的标准事实集合 | `standard_pack_id` + version/hash | 不可就地改写 |
| `analysis_workspace` | 用户当前正在编辑的设备输入和草稿问题 | workspace id | 可变 |
| `analysis_record` | 已确认的单次评价快照及证据轨迹 | record id + revision | 不可变 |
| `golden_case` | 用标准证据保护业务真相的可复现案例 | `case_id` | 版本化，批准后不可静默改写 |

### 2.1 公共类型与 Profile 的关系

公共类型不等于标准评价口径。一个公共类型可以路由到多个 Profile，一个 Profile 只能在一个明确的标准和业务适用范围内评价。

Phase 1 采用以下原则：

- `centrifugal_pump` 可以路由到 `pump_water` 或 `pump_chemical`；不能凭公共名称自动选择标准口径。
- `motor` 可以路由到 `motor_lv`、`motor_hv` 或 `motor_pmsm`；必须由输入条件或明确选择消除歧义。
- 如果无法唯一选择 Profile，返回 `REQUIRES_REVIEW`，不得猜测默认 Profile。
- `profile_id` 是结果、标准包、规则、Golden Case 和审计证据的主连接键。

## 3. 一次评价的规范生命周期

```text
接收输入
  → 公共类型/ Profile 路由
  → 标准包与 as_of 选择
  → 输入归一化与单位确认
  → 必填、数值和适用范围检查
  → 标准查表/公式/允许的派生计算
  → 结果状态与等级/结论分离生成
  → 记录证据、来源、版本和问题码
  → 生成可冻结的 Record
```

每一步的业务要求如下：

1. **路由**：输入的公共类型、Profile、标准和必要条件必须形成可审计的路由记录。
2. **标准选择**：必须显式记录 `standard_pack_id`、版本、哈希和 `as_of`；不能因为某包可加载就声称已完成业务验收。
3. **归一化**：别名、字符串格式和单位转换只能把输入转换到稳定 Product/Profile 字段；不能在 Import Contract 中偷偷实现评价规则。
4. **检查**：缺失、非法、超范围、标准未覆盖和规则冲突必须分别保留，不能统一吞成一个“计算失败”。
5. **评价**：只能使用 Profile 对应的 Canonical 事实和经批准的 Ruleset；旧实现和旧测试只作为证据。
6. **结果**：Support Status 与能效等级/评价等级是两个维度；“不支持”不能伪装成某个等级，也不能仅用“无法判定”代替。
7. **审计**：结果必须能回指输入快照、标准来源、稳定 `data_id`、公式/规则 ID、版本和人工复核信息。

## 4. Support Status V0.1

Support Status 是业务状态，不是 Python 异常名，也不是单纯的 UI 文案。它与 `conclusion`、`reference_conclusion`、问题码和证据轨迹分开存储。

| 状态 | 适用条件 | 允许的结论形态 | V1 UI 语义 |
|---|---|---|---|
| `SUPPORTED` | Profile 在 V1 Scope 内，输入有效，标准条件和必要事实已满足 | 可有等级、评价值或标准结论 | 显示评价结果和证据 |
| `NOT_IN_RELEASE_SCOPE` | Profile 已识别，但不在当前发布范围 | 不生成正式等级；可显示范围说明 | 当前版本未支持 |
| `UNSUPPORTED_STANDARD` | 已识别需求，但项目没有可批准的标准事实包 | 不生成正式等级 | 缺少已支持标准 |
| `OUT_OF_STANDARD_SCOPE` | 标准存在，但设备类型、参数或工况不在标准适用范围 | 不生成标准等级；可保留确定的派生指标 | 不在标准范围 |
| `INSUFFICIENT_DATA` | 评价所需字段、来源或条件不完整 | 不得补默认值；可保留不依赖缺失项的中间结果 | 缺少必要数据 |
| `INVALID_INPUT` | 输入违反数据类型、单位、正负性、枚举或一致性约束 | 不执行会误导的评价 | 输入无效 |
| `NOT_APPLICABLE` | 业务上明确不适用于该对象或场景 | 不生成该评价结论 | 不适用 |
| `REQUIRES_REVIEW` | 路由、标准解释、来源、规则冲突或证据不足需要人工确认 | 不自动生成不可逆的正式结论 | 需人工复核 |

### 4.1 状态优先级

当一次输入同时触发多个问题，按以下顺序确定主状态，同时保留全部问题码和证据：

```text
INVALID_INPUT
  > REQUIRES_REVIEW
  > UNSUPPORTED_STANDARD / NOT_IN_RELEASE_SCOPE / NOT_APPLICABLE
  > OUT_OF_STANDARD_SCOPE
  > INSUFFICIENT_DATA
  > SUPPORTED
```

该优先级只定义状态选择，不允许把输入错误掩盖为“不在范围”，也不允许用标准缺失掩盖路由冲突。

### 4.2 部分支持

部分支持不作为隐藏状态。一个 Profile 可以在字段或标准条件层面存在限制，但对外必须明确写出限制：

- 能够完成标准评价的输入，返回 `SUPPORTED`；
- Profile 已识别但缺少当前发布能力，返回 `NOT_IN_RELEASE_SCOPE`；
- 仅能计算不依赖缺失字段的功率、比转速等派生指标时，保留这些指标，同时主状态仍为 `INSUFFICIENT_DATA` 或 `OUT_OF_STANDARD_SCOPE`；
- 不允许返回“已支持，只是算不出来”这种模糊状态。

## 5. 输入、单位与缺失语义

- Product/Profile Schema 定义稳定字段、类型、单位、必填条件和约束。
- `unit_id` 必须稳定且可解释；显示单位可以本地化，但不能替换字段的内部单位语义。
- 小数、阈值和公式中间值在契约中以十进制字符串表达，避免跨语言二进制浮点差异。
- 空字符串、`null`、未提供和无法解析必须在归一化阶段区分，并映射到明确问题码。
- 单位未知或单位换算不安全时，不得猜测；返回 `INVALID_INPUT` 或 `REQUIRES_REVIEW`。
- 缺失字段不得使用示例值、零值或某个设备类型的默认值代替，除非 Product/Profile Schema 明确批准且结果中记录默认来源。

## 6. Workspace 与 Record

Phase 1 采用已批准方向：

- `Workspace` 是用户可编辑的当前草稿，可以修订输入、查看问题、重新评价。
- `Record` 是一次明确版本、输入快照、标准事实和结果证据的不可变记录。
- Finalize 之后，Record 的业务事实、版本、来源和结论不能被静默覆盖；修订应产生新的 Workspace revision 或新的 Record revision。
- 自动保存、跨启动恢复、Finalize 事务、Record→Workspace 和 lineage 属于 Phase 1/2 后续设计输入，本阶段只冻结语义，不建立 SQLite 表。

## 7. 证据优先级与业务真相

用于确定业务结论的证据优先级如下：

1. 标准原文及其可核验的表号、条款、页码；
2. 由标准原文复核形成的 Canonical 标准事实包；
3. 经人工复核并批准的 Golden Case；
4. Profile/Import/UI/Ruleset 契约；
5. 当前正式运行实现的输出和 trace；
6. Legacy Regression、旧 matrix、旧 V4 样例和历史 HANDOFF。

后两类不能单独推翻标准证据。实现与标准或 Golden Case 不一致时，应登记 QA/P0 或 `REQUIRES_REVIEW`，不能为了让旧测试通过而修改业务真相。

## 8. 结果的最小审计要求

每个可发布的结果至少应带有：

```text
public_device_type
profile_id
support_status
conclusion / reference_conclusion
standard_code
standard_pack_id / standard_pack_version / standard_pack_hash
catalog_data_version
ruleset_version
schema_version
formula_id / formula_revision（适用时）
input snapshot
actual metrics
calculated metrics
lookups and stable data_id
limits and comparisons
issue codes
source references
trace
```

结果中如有“评价参考结果”与“最终结果”不同，必须同时保存二者及原因；例如淘汰目录证据不足不能把能效参考等级冒充最终结论。

## 9. V0.1 验收条件

本规范只有在 Solution Review 中确认以下事项后，才可成为下一版冻结输入：

- Support Status 的业务文案和状态优先级获得确认；
- 公共类型到 Profile 的歧义处理获得确认；
- `as_of`、版本字段和 Record 不可变边界与数据契约一致；
- `pump_water` 映射中的标准证据、边界和 Golden Case 可以回溯；
- V1 Scope 的实际用户需求和商业价值由产品负责人补齐或明确批准保持未知。

在上述确认前，本文件状态保持 `DRAFT_FOR_SOLUTION_REVIEW`，不得据此启动 Phase 2。

## 10. 五类契约的边界（Phase 1 冻结草案）

| 契约 | 负责回答 | 可以包含 | 明确不能包含 |
|---|---|---|---|
| Canonical | 标准原文说了什么 | 标准事实、表、公式、边界、单位、来源和稳定 `data_id` | 用户输入别名、UI 文案、运行时默认值、结论流程 |
| Product/Profile | 某类产品需要哪些稳定字段 | `profile_id`、字段类型/单位/必填条件、公共类型映射、结果字段、Ruleset 引用 | 标准表格复制、Excel 单元格位置、展示层临时字段 |
| Import | 外部来源如何安全进入 Product/Profile | Sheet/列、模板版本、别名、单位转换、导入校验责任和人工复核标记 | 公式、查表、等级比较、标准选择和结论 |
| UI Metadata | 字段怎样被用户理解和编辑 | 显示名、帮助、可见性、编辑性、枚举呈现、顺序和错误提示投影 | 标准事实、核心业务规则、默认业务结论 |
| Ruleset | 在已归一化输入和 Canonical 事实上如何判定 | 适用范围、路由条件、公式调用、比较方向、边界、插值/不外推策略、问题码和规则 ID | UI/Excel 结构、标准事实的再次硬编码、未经批准的产品默认值 |

同一信息只允许有一个权威归属：标准数值回到 Canonical，稳定业务字段回到 Product/Profile，模板别名回到 Import，展示说明回到 UI Metadata，判定逻辑回到 Ruleset。Python 常量若承载其中任一类数据，必须在资产审计中标记为迁移候选，不得在迁移前静默删除。

## 11. 版本字段语义（Phase 1 草案）

版本字段必须按职责分离，禁止再引入含义不清的全局 `algorithm_version`：

| 字段 | 语义 | 变化触发 |
|---|---|---|
| `app_version` | 可发布应用/构建版本 | 应用发行物变化 |
| `business_spec_version` | 业务规范版本 | 业务语义或状态契约变化 |
| `catalog_data_version` | Canonical 数据内容版本 | 标准事实包内容变化 |
| `standard_pack_id` | 标准包稳定身份 | 标准包身份变化 |
| `standard_pack_version` | 标准包包装/契约版本 | 包结构或包级版本变化 |
| `standard_pack_hash` | 实际加载内容指纹 | 任一包字节变化 |
| `ruleset_version` | Profile 判定规则版本 | 规则、边界、比较或问题码语义变化 |
| `result_contract_version` | 结果对外字段和语义版本 | 结果契约变化 |
| `schema_version` | 所使用输入/Canonical/Golden Schema 版本 | Schema 变化 |
| `formula_id` | 公式的稳定身份 | 公式定义新增或替换 |
| `formula_revision` | 公式解释/实现修订 | 公式表达、精度或修约规则变化 |

一次可复现评价至少同时保存适用的这些字段；只有 `app_version` 不能证明业务结果相同。`standard_pack_hash` 应由装配/加载层记录，不能由 UI 自行生成或省略。
