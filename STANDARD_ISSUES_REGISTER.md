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
| 标准原文 | 本台账不复制标准全文。当前可追溯事实为：`docs/standards/gb19762_2025/profiles/pump_water.md` 记录该标准实施日期为 `2026-03-01`；原文证据由该映射登记的 `GB19762-2025-PDF` 外部证据注册项追溯。**标准原文没有规定软件的评价日期默认值。** |
| 问题类型 | `IMPLEMENTATION`（软件实现解释问题） |
| 问题说明 | 软件多处存在评价日期 `as_of` 的隐式默认行为。标准实施日期可以决定某日期是否允许使用该版本，但标准本身并不会自动给软件定义默认 `as_of`。若默认来源不明确，可能选择错误的标准生效状态 |
| 支持证据 | `QA_BACKLOG.md` 的 `QA-AUD-031`；`docs/standards/gb19762_2025/profiles/pump_water.md`；源码定位见下方“事实更正与源码核实” |
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

> 本节按中央治理规则新增稳定编号；D-01～D-08为配套决策文档中的别名。**001/D-01已在软件设计口径层面RESOLVED（Owner 2026-10-11）；002～008仍OPEN**。软件决定不是发布机构官方解释，也不等于已写入生产代码。标准PDF SHA256：`862d32069301bb76bcf1477e38befdcc32dfb219a409032c41ff374e88863a3f`。

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
|软件当前处理方式|【Owner已批准的软件设计口径，2026-10-11】普通表1～28及新能源表29～35同表同完整物理分支、相邻有效标准容量点可线性插值，空载/负载分别计算；不得跨分支、外推、取空白为0或以显示值比较。仅文档设计，尚未实施Calculator/JSON；变压器仍`POST_V1 / NOT_IN_RELEASE_SCOPE`。|
|确认程度|**软件决定已由Owner于2026-10-11在本对话明确批准；未取得发布机构官方解释。** 保留第4章段落位置引起的标准解释空间，产品口径不再等待额外批准。|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`RESOLVED`（Owner批准的软件解释口径；非发布机构官方解释；不等于生产实现/正式验收）|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11（Owner确认插值软件口径）|

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
|当前技术判断|Owner提出4.2%可归4.0%、5.8%可归6～8%的±10%相对容差实例；是否可用实测值直接选标准物理损耗分支须核对设计/试验基准。|
|软件当前处理方式|【PROVISIONAL工程建议】先验证设计额定/实测及实际适用GB/T1094.1短路阻抗偏差条件；候选4.0%可按3.6～4.4%、6～8%按5.4～8.8%辅助人工识别。无唯一组或证据不充分仍无法判定；并未修改生产代码。|

> **最新软件决策（优先于上面的历史处理方式）**：【Owner新决定2026-10-12｜软件默认，不是国家标准统一允差】表2单值4.0%对应[3.6%,4.4%]、范围6.0%～8.0%对应[5.4%,8.8%]，允许边界等号。阻抗属于可用唯一组即可进行能效判定，全部不命中→UNABLE_TO_JUDGE/IMPEDANCE_NO_MATCH；不同限值组同时命中且不能唯一选路→UNABLE_TO_JUDGE/BRANCH_AMBIGUOUS。**不得因GB/T1094.1正式允差条款尚未查完阻断正常判级**。旧PROVISIONAL建议由本决定取代；未修改Calculator。

|确认程度|Owner2026-10-11提供±10%工程实例；尚无对该产品/分接/绕组对的正式逐条核验。GB20052没有一律±10%的明文。|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`RESOLVED`（已批准软件默认±10%选组；非国标明文）|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-12（Owner软件默认/延期决定）|

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
|当前技术判断|GB/T 1094.1—2013第10章的阻抗偏差并非所有设备统一±10%：应分主分接/非主分接、阻抗≥10%/＜10%、两绕组或三绕组指定绕组对、各自耦条件审查。Owner的统一±10%意见先作为工程建议。|
|软件当前处理方式|【PROVISIONAL】不把GB20052表列数值机械解释为实测必须精确相等；亦不将±10%写成统一国家标准允许偏差。明确设备条件与实测/额定口径，查正式条款后再批准判别规则。|

> **最新软件决策（优先于上面的历史处理方式）**：【Owner新决定2026-10-12｜软件默认，不是国家标准统一允差】用于损耗阈值选组的标准阻抗单值v使用[0.9v,1.1v]；范围[a,b]使用[0.9a,1.1b]，包含边界。选组成功继续判级；无匹配或限值冲突→UNABLE_TO_JUDGE；不另设“必须先取得正式试验允差解释”的开发门禁。**不能把软件默认说成GB20052/GB/T1094.1统一法定试验允许误差**。

|确认程度|外部GB/T1094.1—2013第10章/表1说明不同条件允许偏差不同；仍需取得适用版本正式页、核实各产品/绕组组合。|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`RESOLVED`（已批准软件默认±10%；正式试验允差另论）|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-12（Owner软件默认/延期决定）|

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
|当前技术判断|表15的普通组和LV66/69kV特殊组为不同物理分支，各自容量首末点组成软件可评价容量边界；不跨分支插值、外推或回退。|
|软件当前处理方式|【Owner软件决定2026-10-11】目标表/分支容量在首末点外→OUT_OF_SCOPE/OUTSIDE_TABLE_CAPACITY_RANGE；例LV66kV且100000kVA不评价。该状态是软件覆盖边界，不等同GB20052第1章官方排除。|
|确认程度|Owner于2026-10-11明确批准3问的答案：普通组不得回退，范围外不评价，特殊组只覆盖表列点及合法插值区间；PDF物理页15原表范围可核实。|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`RESOLVED`（Owner软件评价口径，不代表发布机构正式解释）|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11（Owner意见与PDF/产品标准证据复核）|

### EQP-STD-GB20052-005 — 适用范围与表列容量/空白差异

|字段|记录|
|---|---|
|问题编号|`EQP-STD-GB20052-005`（别名`D-05`）|
|标准编号及名称|GB 20052—2024《电力变压器能效限定值及能效等级》|
|标准版本|2024|
|条款 / 表 / 公式 / 页码|第1章及表1/12/18/25/26/33/34，PDF物理页5–26|
|标准原文|原文事实摘要：GB20052第1章为一般适用框架；具体表列容量不尽一致。表1 PDF物理页7的630、800、1000、1250、1600、2000、2500kVA负载损耗**横向合并单元格**同时覆盖Dyn11/Yzn11和Yyn0列，不是Yyn0空白。|
|问题类型|`MISSING`|
|问题说明|适用范围与表列容量/空白差异|
|支持证据|上传PDF 第1章及表1/12/18/25/26/33/34，PDF物理页5–26；`docs/standards/gb20052_v21/GB20052_DECISIONS_NEEDED.md` D-05；PR #20|
|当前技术判断|Owner确认按具体表/物理分支首末容量作为软件评价边界。此前Yyn0负载损耗“空白”是PDF合并单元格解析错误，已依据原表页图纠正。|
|软件当前处理方式|【Owner软件决定2026-10-11】表/分支容量低于首点或高于末点→OUT_OF_SCOPE/OUTSIDE_TABLE_CAPACITY_RANGE；范围内未列容量按D-01合法插值。表1上述7容量的Yyn0与Dyn11/Yzn11共享相同Pk物理合并单元格，撤销旧STANDARD_BLANK/G09。|
|确认程度|2026-10-11用户指出表1问题；复核上传GB20052-2024 PDF物理页7图像确认单元格合并；软件评价容量边界由Owner明确批准，但不冒充GB20052第1章的官方释义。|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`RESOLVED`（PDF视觉证据＋Owner软件口径）|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-11（Owner意见与PDF/产品标准证据复核）|

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
|当前技术判断|每台干式设备的B/F/H绝缘等级是单一已确定输入：F设备只取F列，与B/H无关。另需独立核对实际测试Pk是否已按F的120℃或其它规定参考温度校准，两问题不可混同。|
|软件当前处理方式|【已明确选列】只比较设备自身等级对应列；有效报告已给出相应温度Pk则直接评价，不设计无依据自动温度修正。仅原始/未知参考温度的损耗值仍TEST_CONDITION_UNVERIFIED，正式温度换算条款待查。|

> **最新软件决策（优先于上面的历史处理方式）**：【Owner新决定2026-10-12】暂搁置自动温度换算功能，待实际遇到问题再处理。B/F/H只按自身绝缘等级列比对；报告若提供可与该等级标准参考温度比较的Pk，正常判定，不增设无意义的额外温度输入。报告若**明确**只给出不可比的非参考温度原始损耗，不得伪装成已换算，针对该条记录说明不可比/UNABLE_TO_JUDGE。不得把未实现温度换算作为全部变压器能效功能上线前置门禁。

|确认程度|Owner2026-10-11明确B/F/H只取一个等级；PDF表2/30/32/34有分温度列；第6章引用试验方法。温度换算细则/参数尚未独立取得。|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`OPEN`（自动温度换算需求DEFERRED，非当前正常判级阻断）|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-12（Owner软件默认/延期决定）|

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
|当前技术判断|Owner强调三绕组阻抗相互耦合，应以高—中、高—低、中—低的完整三元组对照A/B/C；“高—低约等于另外两项相加”仅某些结构下的工程近似，不是通用恒等式。若一律±10%扩展表27/28组值，则B/C可能在三个维度同时重叠。|
|软件当前处理方式|【PROVISIONAL】三元组必须同时匹配一个组；完全无组→UNABLE_TO_JUDGE，匹配多组→BRANCH_AMBIGUOUS/UNABLE_TO_JUDGE。Owner提议多组匹配OUT_OF_SCOPE暂未批准为正式状态，需先核实设备参考条件和偏差规则；不可凭近似加法自动决定。|

> **最新软件决策（优先于上面的历史处理方式）**：【Owner新决定2026-10-12｜软件默认，不是国家标准统一允差】表27/28重复容量正常，不能因此阻断。高—中、高—低、中—低三阻抗**全部按±10%相对容差**对照A/B/C完整组；一个组命中→按其阈值评价；所有组不匹配→UNABLE_TO_JUDGE/IMPEDANCE_NO_MATCH。多组同时命中时，若本容量的所有等级P0/Pk阈值完全相同→可以按共同阈值评价并保留多个source IDs；若阈值有冲突→UNABLE_TO_JUDGE/BRANCH_AMBIGUOUS，不随意选组。近似阻抗加和不是标准严格等式。

|确认程度|Owner2026-10-11说明三元组物理相关与完整组合；PDF页19-20保留A/B/C。容差扩展造成重叠可数学验证，但无外部正式规则证明多命中应视为标准不适用。|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`RESOLVED`（已批准三阻抗完整匹配及失败策略的软件默认）|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-12（Owner软件默认/延期决定）|

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
|当前技术判断|2026-10-12 Owner明确确认全部35表无误，同意合并PR #21，批准工作簿与主映射V2.1共同冻结；此为Owner项目批准，非本轮助手独立双人逐格复核。|
|软件当前处理方式|【Owner批准冻结】双文件一体作为Transformer开发的正式基准；未经Owner就具体修改事先明确审批，不得改动任一文件（包括Excel重存）。获批修订需新版本、保留旧SHA并核验影响；不等于Calculator/JSON/Golden已实现或软件SUPPORTED。|
|确认程度|Owner2026-10-12明确宣布35表全部确认无误，作为最终项目批准；旧Excel中待核标记作为历史过程记录保持不动，不虚称本轮助手独立双人复核。两文件哈希见GB20052_V21_FROZEN_BASELINE.md。|
|业务影响|高：误释可能影响表路由/阈值/实际等级或标准数字发布。|
|关联 Rule / Calculator|文档候选standard_scope / product_table_route / threshold_branch / threshold_row；未来Transformer Calculator。未实施、未修改。|
|关联测试 / Golden Case|`docs/standards/gb20052_v21/GB20052_V21_ACCEPTANCE.md`文档候选案例；无新批准Golden，无生产测试变更。|
|状态|`RESOLVED`（Owner批准全部35表与主映射V2.1一体冻结）|
|首次发现日期|2026-10-11（首次正式登记，历史映射讨论可能更早）|
|最后更新日期|2026-10-12（Owner最终审批）|

### 后续联动要求

稳定追踪链：`Standard Issue → Owner批准的Software Decision → Transformer Rule/Calculator → Test/Golden Case`。001～005和007软件口径已由Owner明确决定，其中D-02/03/07仅为暂用软件±10%默认，**不是国标统一法定允差**；D-06温度换算仍OPEN但DEFERRED，不阻断正常判级；D-08经Owner确认全部35表无误并批准冻结，RESOLVED。**本轮未修改Calculator、JSON或Approved Golden**，解释档及纠错证据见`docs/standards/gb20052_v21/GB20052_STANDARD_INTERPRETATIONS.md`。不得因PR合并自动关闭其余OPEN问题或声称数值全部验证。


> 长期记录入口：`docs/standards/README.md`。本根台账继续保持**稳定ID、正式问题状态的唯一权威**；标准专属解释档存标准原文依据、工程补充、Owner决定和失效解释的历史。未来新标准按模板记录，不新增重复台账或额外发布门禁。
