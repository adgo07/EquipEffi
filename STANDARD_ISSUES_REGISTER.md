# 标准问题与解释台账

状态：**ACTIVE REGISTER**

本台账用于记录标准原文事实、技术判断与软件实现决定。不得用本台账改写标准原文，也不得把内部判断或软件选择表述成发布机构正式解释。

## 1. 类型代码

| type code | 中文解释 |
|---|---|
| `TYPO` | 疑似笔误 |
| `AMBIGUITY` | 歧义 |
| `CONFLICT` | 条款、公式或表格冲突 |
| `MISSING` | 标准未规定 |
| `TERM` | 术语或现实对象对应不清 |
| `REFERENCE` | 引用标准、版本或外部依据问题 |
| `IMPLEMENTATION` | 软件实现解释问题 |

## 2. 状态代码

| status code | 中文解释 |
|---|---|
| `OPEN` | 待解决 |
| `PROVISIONAL` | 已有临时处理口径 |
| `RESOLVED` | 已有充分依据确认 |

`RESOLVED` 不自动等于发布机构官方确认；是否有官方解释必须在“确认程度”中单独说明。

## 3. 登记规则

- 问题编号采用 `EQP-STD-<标准号简写>-NNN`，一旦使用不得改号或复用。
- 每个问题必须分开记录“标准原文事实”“当前技术判断”“软件当前处理方式”。
- 无法准确复制标准原文时，不得凭记忆补写；应记录准确定位、事实摘要或“未复制原文”，并保留证据来源。
- 影响正式业务结果的问题必须可追踪：`Standard Issue → Software Decision → Rule / Calculator → Test / Golden Case`。
- 后续修改既有解释时，必须检查相关测试和历史结果兼容性。
- 当前只登记已有明确证据的问题，不重新审计全部标准，也不为填表制造问题。

## 4. 当前问题

### EQP-STD-GB19762-001 — 标准实施日期与软件评价日期 `as_of` 的关系

| 字段 | 记录 |
|---|---|
| 问题编号 | `EQP-STD-GB19762-001` |
| 标准编号及名称 | GB 19762—2025《离心泵能效限定值及能效等级》 |
| 标准版本 | 2025 |
| 条款 / 表 / 公式 / 页码 | 标准实施日期及软件标准版本选择；现有 `pump_water` 映射记录实施日期为 `2026-03-01`，本问题不涉及泵公式或表 3 数值 |
| 标准原文 | 本台账不复制标准全文。当前可追溯事实为：`specs/equipment_efficiency/profiles/pump_water.md` 记录该标准实施日期为 `2026-03-01`；原文证据由该映射登记的 `GB19762-2025-PDF` 外部证据注册项追溯。**标准原文没有规定软件的评价日期默认值。** |
| 问题类型 | `IMPLEMENTATION`（软件实现解释问题） |
| 问题说明 | 软件多处存在评价日期 `as_of` 的隐式默认行为。标准实施日期可以决定某日期是否允许使用该版本，但标准本身并不会自动给软件定义默认 `as_of`。若默认来源不明确，可能选择错误的标准生效状态 |
| 支持证据 | `QA_BACKLOG.md` 的 `QA-AUD-031`；`specs/equipment_efficiency/profiles/pump_water.md`；源码定位见下方“事实更正与源码核实” |
| 当前技术判断 | `as_of` 应作为可审计的标准版本选择依据。**软件产品决定**（非标准明文）：新建分析以用户本机当前本地日期为默认值、允许手动修改、Finalize 冻结实际日期、Reopen 显示原日期；测试 harness 使用固定日期只是测试条件，不是产品默认 |
| 软件当前处理方式 | 见下方“软件产品决定（2026-10-02）”与“事实更正与源码核实”。Phase 3 统一 `AnalysisService` 采用显式 `as_of`，不设隐式默认 |
| 确认程度 | 标准实施日期与现有运行行为有仓库证据；**软件产品决定已由产品负责人于 2026-10-02 作出**；**不存在发布机构对软件默认日期的官方解释** |
| 业务影响 | 高：错误默认日期可能导致在标准未实施时使用该版本，或在版本切换时选择错误标准，进而影响正式评价结果 |
| 关联 Rule / Calculator | 标准版本选择 / Application request；`pump_water`；Pump Calculator/evaluator 路由 |
| 关联测试 / Golden Case | `QA-AUD-031` 记录的日期 probe；Phase 3 的 `as_of` 默认/注入/Finalize/Reopen 测试；R3 `tests/unit/test_phase3_r3_as_of_lifecycle.py`（water + chemical × 2026-02-28 / 2026-03-01 / 2026-10-03 业务结果一致性、Record/Reopen 保留 `as_of`、非阻断 warning）；本台账的更正不影响任何已批准 Golden |
| 状态 | `RESOLVED`（已有充分依据确认；依软件产品决定关闭，非发布机构官方确认；R3 补充决定见下） |
| 首次发现日期 | 2026-09-22（`QA_BACKLOG.md` Phase 1 P0 Evidence Review） |
| 最后更新日期 | 2026-10-02（R3） |

#### 软件产品决定（2026-10-02）

产品负责人决定；**这是软件产品决定，不是 GB 19762 发布机构的官方解释**：

- **新建分析**：默认值为用户电脑的**当前本地日期**；允许用户手动修改；
- **Evaluate / Finalize**：使用该 Workspace 中**实际**的 `as_of`；
- **Finalize**：把实际 `as_of` **永久写入** Record；
- **Reopen**：显示历史 Record 的**原** `as_of`，**不得**重新取当天日期；
- **Golden / regression replay**：测试 harness **显式**传入固定日期 `2026-08-23`；该日期**只属于测试条件**，不是产品默认日期。

因此正式产品模型中**不得**存在把 `date(2026, 8, 23)` 当作隐式默认的行为。Phase 3 新增的统一 `AnalysisService` 采用显式 `as_of`；既有 CLI/API 的兼容默认值按 `AGENTS.md §2.0` 作为兼容边界**登记保留**，其全局取消须单独做兼容影响评估（见“事实更正与源码核实”第 3 条）。

#### 软件产品决定补充（2026-10-02，R3）：`as_of` 不是标准执行门禁

产品负责人作出后续正式决定，**取代**此前"评价日期早于标准实施日期则不执行计算"的设计：

> **评价日期仅用于记录与追溯，不是标准执行门禁；标准生命周期状态只做非阻断提示。**

- `as_of` **只用于**：默认新建分析日期、用户手动修改、Record 历史追溯、Reopen 显示原评价日期；
- `as_of` **不再决定所选标准能否执行**。用户可以主动使用**尚未实施**、**当前现行**、
  **已废止或已被替代**的标准版本进行评价；只要用户明确选择某个标准版本，
  软件就按**该版本的冻结规则正常计算**；
- 标准的未实施 / 已废止 / 已被替代状态只作为**非阻断提示**（`PumpAnalysisResult.warnings`），
  **不得**阻止计算、**不得**改成 `INSUFFICIENT_DATA`、**不得**改变 `evaluation_status`、
  **不得**改变 Finalize 权限、**不得**自动切换到其他标准版本；
- 同一输入在实施日之前与之后必须调用**同一规则集**并得到**相同业务计算结果**；
  日期本身**不得**参与泵效率、等级、范围判断；
- 生命周期提示**不得**进入 `evaluation_status` / `issue_codes` / `missing_fields`，
  也不得影响 `finalizable`；本决定**不新建状态体系**，只复用结果契约的一个纯展示字段。

被删除的旧门禁：`as_of < effective_date → INSUFFICIENT_DATA → 不执行 evaluator`
（连同 `STANDARD_NOT_YET_EFFECTIVE` 这一 `issue_code`，以及此前为它设的
Finalize 白名单例外 `WHITELIST_EXCEPTIONS`）。删除后 `finalizable` 严格等价于
"`evaluation_status` 在统一白名单内"，**不存在任何 `as_of` 特例**。

**作用域**：本决定作用于**统一离心泵分析链**（`pump_water` / `pump_chemical`）。
遗留 `EvaluationService` 对**其他设备**（motor / transformer）的生效日期门禁**不在本 Phase 范围**，
未作改动；如需同样调整须另立任务并做兼容影响评估。

**本条决定不改变**任何已批准 Golden、泵算法、Canonical 或 Numeric Profile。

#### 事实更正与源码核实（2026-10-02）

本条此前有两处不准确的既有记录，现更正如下（保留更正痕迹）：

1. **更正：18 条 `pump_water` Golden 0.4 不携带 `as_of`。**
   逐文件核实结果：`specs/equipment_efficiency/golden/pump_water/` 下 18 条 `golden-case-0.4` 记录**均不含** `as_of` 字段；仅 7 条历史 `golden-case-0.1` 记录含该字段。因此既有表述“18 条已批准 Golden 均显式携带 `as_of`”**不成立**，且**不得**为了补 `as_of` 而修改这 18 条已批准记录。

2. **更正：隐式默认不在业务模型，而在 Application 层的默认参数。**
   仓库中 `date(2026, 8, 23)` 作为隐式默认出现在 5 处：
   `src/equipeffi/application/services/evaluation_service.py:13`（`DEFAULT_EVALUATION_DATE`，并被 `_coerce_as_of(None)` 回退使用）、
   `src/equipeffi/application/services/evaluation_facade.py:27` 与 `:68`、
   `src/equipeffi/application/services/v4_workbook_service.py:34` 与 `:67`、
   `src/equipeffi/presentation/api/application_api.py:539`。

3. **兼容边界（登记保留，不在本任务全局替换）。**
   既有 CLI/API/JSONL 入口的默认日期先作为兼容边界保留并记录影响；正式产品的评价日期入口以 Phase 3 `AnalysisService` 的显式 `as_of` 为准。统一取消旧入口默认值应另立任务，附兼容影响评估、版本说明与针对性测试。

### 追踪链

```text
EQP-STD-GB19762-001
→ Software Decision: 新建分析默认本机当前日期、可修改；Finalize 冻结实际日期；Reopen 用原日期；
   Golden/regression replay 显式传 2026-08-23（仅测试条件）；正式产品不设隐式默认
→ Rule / Calculator: AnalysisService 显式 as_of → 标准版本选择 → pump_water / pump_chemical evaluation path
→ Test / Golden Case: QA-AUD-031 date probes + Phase 3 as_of default/injection/finalize/reopen tests
   + 既有 18 条 pump_water Golden 0.4（未修改）+ 11 条 pump_chemical Golden 0.5（未修改）
```

本条现已关闭为 `RESOLVED`（软件产品决定层面）。**关闭不改变**任何已批准 Golden、泵算法、Canonical 或 Numeric Profile。
