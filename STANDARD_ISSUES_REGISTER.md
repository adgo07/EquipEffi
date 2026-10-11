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

## 5. GB 20052—2024 映射V2.1问题登记（2026-10-11）

> 本节按中央治理规则新增稳定编号；D-01～D-08为配套决策文档中的别名。**全部OPEN**：映射建议非官方解释，亦不是已批准的生产规则。标准PDF SHA256：`862d32069301bb76bcf1477e38befdcc32dfb219a409032c41ff374e88863a3f`。

### EQP-STD-GB20052-001 — 插值条文适用范围

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-001`（别名`D-01`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|第4章，PDF物理页5–6/印刷1–2|
|标准原文|未复制整表，原文事实摘要：普通表1～28的能效限值位于PDF第5页，第6页另起新能源表29～35段落，紧接后有未列容量线性插值条文；未逐表列出覆盖范围。|
|问题类型|`AMBIGUITY`|
|问题说明|插值条文适用范围|
|支持证据|上传PDF 第4章，PDF物理页5–6/印刷1–2；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-01；PR #20|
|当前技术判断|不能无依据断言该句涵盖表1～35所有类别，也不能武断说只能用于新能源。|
|软件当前处理方式|【尚待Owner批准的实现候选】可考虑所有表1～35同表同分支相邻有效点插值；其中普通表1～28的覆盖范围待确认，本PR不实施。 变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`；本轮未修改运行时代码或JSON。|
|确认程度|PDF相关原文事实已查；无发布机构就本问题的正式解释。仍需：发布机构/主管部门对条文适用范围的正式释义及Owner软件决定|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11|

### EQP-STD-GB20052-002 — 表2 630kVA名义阻抗分组

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-002`（别名`D-02`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|表2，PDF物理页8/印刷4|
|标准原文|未复制整表，原文事实摘要：630kVA在表2出现4.0%与6.0%～8.0%两行，损耗阈值不同。|
|问题类型|`TERM`|
|问题说明|表2 630kVA名义阻抗分组|
|支持证据|上传PDF 表2，PDF物理页8/印刷4；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-02；PR #20|
|当前技术判断|设计额定阻抗与实测阻抗的角色可能不同；不能选最近组。|
|软件当前处理方式|【映射建议】要求可核验的设计/额定阻抗，不能明确时不给唯一阈值。 变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`；本轮未修改运行时代码或JSON。|
|确认程度|PDF相关原文事实已查；无发布机构就本问题的正式解释。仍需：制造商技术协议与设计名义阻抗、铭牌、适用产品标准|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11|

### EQP-STD-GB20052-003 — 表列阻抗与允许偏差对应关系

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-003`（别名`D-03`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|第5.1章及表9/13/27/28，PDF物理页6/12/14/19–20|
|标准原文|未复制整表，原文事实摘要：表列短路阻抗存在名义值/范围，第5.1章引用产品技术标准；本标准没有将所有数值规定为实测必须精确相等。|
|问题类型|`REFERENCE`|
|问题说明|表列阻抗与允许偏差对应关系|
|支持证据|上传PDF 第5.1章及表9/13/27/28，PDF物理页6/12/14/19–20；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-03；PR #20|
|当前技术判断|额定阻抗与试验偏差口径不同，尚需适用产品标准条款。|
|软件当前处理方式|【映射建议】分开记录标称阻抗与实测偏差，暂不制定通用硬相等门槛。 变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`；本轮未修改运行时代码或JSON。|
|确认程度|PDF相关原文事实已查；无发布机构就本问题的正式解释。仍需：GB/T1094.1、6451、10228等正式版本相关偏差条款|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11|

### EQP-STD-GB20052-004 — 表15特殊低压组覆盖边界

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-004`（别名`D-04`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|表15，PDF物理页15/印刷11|
|标准原文|未复制整表，原文事实摘要：特殊低压66/69kV组首点为120000kVA，普通组另有90000kVA等容量。|
|问题类型|`MISSING`|
|问题说明|表15特殊低压组覆盖边界|
|支持证据|上传PDF 表15，PDF物理页15/印刷11；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-04；PR #20|
|当前技术判断|特殊组未覆盖的容量不应自动跨组插值或回退。|
|软件当前处理方式|【映射建议】分支内无合法两个端点时无法判定，不跨组、不外推。 变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`；本轮未修改运行时代码或JSON。|
|确认程度|PDF相关原文事实已查；无发布机构就本问题的正式解释。仍需：主管方对特殊组未列容量的口径、设备设计证据|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11|

### EQP-STD-GB20052-005 — 适用范围与表列容量/空白差异

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-005`（别名`D-05`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|第1章及表1/12/18/25/26/33/34，PDF物理页5–26|
|标准原文|未复制整表，原文事实摘要：第1章与部分专用表的容量端点不同，表1部分Yyn0格为空白。|
|问题类型|`MISSING`|
|问题说明|适用范围与表列容量/空白差异|
|支持证据|上传PDF 第1章及表1/12/18/25/26/33/34，PDF物理页5–26；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-05；PR #20|
|当前技术判断|无表值不能等同于不适用或不达标。|
|软件当前处理方式|【映射建议】可能适用但表值空白或缺端点时无法判定，保留来源。 变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`；本轮未修改运行时代码或JSON。|
|确认程度|PDF相关原文事实已查；无发布机构就本问题的正式解释。仍需：适用产品范围的权威技术解释及实际设备分类依据|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11|

### EQP-STD-GB20052-006 — 负载损耗参考温度转换依据

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-006`（别名`D-06`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|第5.1、6章及负载损耗列，PDF物理页6–26|
|标准原文|未复制整表，原文事实摘要：油浸负载损耗列以75℃计，干式B/F/H为100/120/145℃，并引用GB/T 1094试验方法。|
|问题类型|`REFERENCE`|
|问题说明|负载损耗参考温度转换依据|
|支持证据|上传PDF 第5.1、6章及负载损耗列，PDF物理页6–26；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-06；PR #20|
|当前技术判断|应具备试验报告及权威温度修正条款；不能按摄氏温度简单比例换算。|
|软件当前处理方式|【映射建议】试验条件不明确时无法判定，温度换算另立依据。 变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`；本轮未修改运行时代码或JSON。|
|确认程度|PDF相关原文事实已查；无发布机构就本问题的正式解释。仍需：GB/T1094系列测试/温度修正条款和完整试验数据|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11|

### EQP-STD-GB20052-007 — 表27/28阻抗B/C组识别

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-007`（别名`D-07`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|表27、28，PDF物理页19–20|
|标准原文|未复制整表，原文事实摘要：表27、28存在A/B/C阻抗三元组；B/C损耗可相同但阻抗组合不同。|
|问题类型|`AMBIGUITY`|
|问题说明|表27/28阻抗B/C组识别|
|支持证据|上传PDF 表27、28，PDF物理页19–20；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-07；PR #20|
|当前技术判断|即使数值损耗相同也要保留物理分组和源行，未知组不应自动推断。|
|软件当前处理方式|【映射建议】A/B/C保持不同source_id，分组冲突阻断。 变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`；本轮未修改运行时代码或JSON。|
|确认程度|PDF相关原文事实已查；无发布机构就本问题的正式解释。仍需：制造商额定阻抗三元组、标称位置及技术协议|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11|

### EQP-STD-GB20052-008 — 全35表数值校对及生产发布

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-008`（别名`D-08`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|表1～35，PDF物理页7–26|
|标准原文|未复制整表，原文事实摘要：本次检查35表的结构与关键金样；原表全部损耗数字尚无逐格双人校验签字。|
|问题类型|`IMPLEMENTATION`|
|问题说明|全35表数值校对及生产发布|
|支持证据|上传PDF 表1～35，PDF物理页7–26；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-08；PR #20|
|当前技术判断|质量签字是项目批准生产标准值的门禁，不是标准原文额外技术指标。|
|软件当前处理方式|【质量约定】待逐格复核签字后方可冻结标准数字；本PR不修改生产JSON。 变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`；本轮未修改运行时代码或JSON。|
|确认程度|PDF相关原文事实已查；无发布机构就本问题的正式解释。仍需：35表逐格校对记录、复核人、证据hash及业务批准|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11|

### 后续联动要求

稳定追踪链：`Standard Issue → Owner批准的Software Decision → Transformer Rule/Calculator → Test/Golden Case`。本轮只有第一环节正式登记，尚未批准软件口径或修改计算器。OPEN不得因文档或PR合并自动关闭。
