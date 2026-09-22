# EquipEffi Phase 1 业务规范与数据契约执行方案

**阶段：** Phase 1  
**阶段名称：** Business Specification & Data Contracts  
**上位路线：** EquipEffi V2.2  
**准入状态：** `PHASE_1_READY`  
**纵向样板：** `pump_water`  
**阶段性质：** 业务规范、数据契约和 Golden Case 冻结  
**本阶段原则：** 定义“以后应该怎么算、数据应该是什么”，暂不大规模重构“现在代码怎么写”。

---

# 1. Phase 1 目标

Phase 1 需要完成六件事：

1. 建立《设备能效分析软件业务规范》V0.1；
    
2. 明确 Canonical、Product/Profile Schema、Import Contract、UI Metadata 和 Ruleset 的边界；
    
3. 用 `pump_water` 验证这些规范能够表达真实业务；
    
4. 建立正式 Golden Case Schema，并批准第一批 `pump_water` Golden Case；
    
5. 对当前 P0 风险完成证据复核，区分“真实业务错误”和“仅工程风险”；
    
6. 冻结进入 Phase 2 所需要的业务契约、版本语义和 Windows V1 Scope 决策。
    

Phase 1 不负责：

- 重写 evaluator；
    
- 大规模搬目录；
    
- 建完整 PySide6 软件；
    
- 建完整 SQLite；
    
- 开 Excel；
    
- 批量迁移 17 Profile。
    

---

# 2. 当前基线不得被改写

Phase 0 当前基线是事实基线：

- 17 个 Profile；
    
- `pump_water` 为首个样板；
    
- Legacy Regression 当前存在已知失败；
    
- 当前标准数据仍采用历史 JSON 结构；
    
- Golden Case 尚未正式建立。
    

Phase 1 不以：

> “把旧测试全部变绿”

作为目标。

现有失败必须保留原始证据，除非经过业务复核确认应该修改。

---

# 3. P1-G01：业务规范骨架

建立：

> 《设备能效分析软件业务规范 V0.1 Draft》

至少冻结以下概念：

## 产品对象

```text
public_device_type
profile_id
standard
analysis_workspace
analysis_record
```

## 业务过程

```text
选择设备/Profile
↓
确定适用标准
↓
输入参数
↓
规范化
↓
范围判断
↓
查表/计算
↓
等级/结论
↓
审计证据
```

## 基础业务状态

正式确认或调整：

```text
SUPPORTED
NOT_IN_RELEASE_SCOPE
UNSUPPORTED_STANDARD
OUT_OF_STANDARD_SCOPE
INSUFFICIENT_DATA
INVALID_INPUT
NOT_APPLICABLE
REQUIRES_REVIEW
```

必须明确每个状态的业务含义。

---

# 4. P1-G01 同时解决公共类型与 Profile 关系

尤其明确：

```text
motor
→ motor_lv
→ motor_hv
→ motor_pmsm
```

以及：

```text
centrifugal_pump
→ pump_water
→ pump_chemical
```

公共类型不得简单等价于：

> 已支持。

必须定义：

- 用户如何选择/识别 Profile；
    
- 一个公共类型部分 Profile 未支持时 UI 如何表达；
    
- 什么情况下进入 `REQUIRES_REVIEW`。
    

---

# 5. P1-G02：数据契约

正式建立五类不同契约。

## A. Canonical Catalog

保存：

- 标准元数据；
    
- 表格；
    
- 阈值；
    
- 标准枚举；
    
- 适用范围事实；
    
- 单位；
    
- 条款；
    
- 来源；
    
- 日期；
    
- 审核状态。
    

唯一权威编辑格式：

> JSON。

---

## B. Product / Profile Schema

保存：

- profile_id；
    
- stable field key；
    
- 数据类型；
    
- unit_id；
    
- 必填性；
    
- 字段关系；
    
- 合法输入结构；
    
- 业务字段分组。
    

---

## C. Import Contract

保存：

- V4 Sheet；
    
- Excel 列名；
    
- 外部字段别名；
    
- 模板版本；
    
- Import Field → Product Field 映射。
    

Import Contract 不参与评价算法。

---

## D. UI Metadata

保存：

- 中文显示名；
    
- 帮助说明；
    
- UI 排序；
    
- 高级字段；
    
- 展示提示。
    

---

## E. Ruleset

保存或定义：

- 如何选标准；
    
- 如何选表；
    
- 边界；
    
- 插值；
    
- 禁止外推；
    
- 缺失数据；
    
- 比较；
    
- 等级；
    
- 淘汰判定；
    
- 结论生成。
    

不得把这五类重新合成一个“大 metadata”。

---

# 6. P1-G02 同时冻结版本语义

正式确认：

```text
app_version
business_spec_version
catalog_data_version

standard_pack_id
standard_pack_version
standard_pack_hash

ruleset_version
result_contract_version

schema_version

formula_id
formula_revision
```

取消模糊的：

```text
algorithm_version
```

---

# 7. Python 运行环境决策

Phase 0 的真实验证环境是 Python 3.13.3，但产品家族技术路线原计划采用 Python 3.12。

Phase 1 应正式做出决定。

当前建议：

> **Windows V1 正式开发和验收环境统一为 Python 3.12 x64。**

Phase 0 的 Python 3.13.3 结果继续保留为历史基线，不能覆盖。

Phase 2 开始前必须建立可重复的 Python 3.12 环境。

---

# 8. P1-G03：pump_water 专业业务映射

这是 Phase 1 最重要的实际验证。

以：

> GB 19762-2025 + 当前 `pump.json` + `WaterPumpEvaluator` + Legacy Tests

作为输入。

但：

> 旧代码只作为证据之一，不作为标准真相。

正式整理：

```text
输入字段
↓
单位
↓
适用条件
↓
公式
↓
派生指标
↓
查表维度
↓
边界
↓
插值
↓
禁止外推
↓
能效等级
↓
淘汰判定
↓
缺失输入
↓
来源与条款
```

---

# 9. pump_water 必须验证的能力

至少覆盖：

### 正常计算

清水离心泵正常输入得到完整结果。

### 派生计算

例如：

- 比转速；
    
- 需要由输入计算得到的指标。
    

### 单位

输入单位和标准单位之间关系明确。

### 范围边界

明确：

- `<`
    
- `≤`
    
- `>`
    
- `≥`
    

等边界。

### 插值

明确：

- 哪些值允许插值；
    
- 哪些不允许；
    
- 是否允许外推。
    

### 缺失参数

缺失必要值时：

> 不允许伪造确定等级。

### 未知类别

不能默认映射为：

> 单级单吸清水离心泵。

### 淘汰判定

明确：

> 未命中受控目录 ≠ 自动证明未淘汰。

---

# 10. P1-G04：Golden Case Schema

正式建立：

```text
case_schema_version
case_id
case_status

device_type
profile_id

business_spec_version
standard_pack_id
standard_pack_version
catalog_data_version
ruleset_version

input

expected_status
expected_actual_metrics
expected_lookups
expected_calculated_metrics
expected_limits
expected_conclusion
expected_issue_codes
expected_rule_ids

source_reference
review_status
review_metadata
```

数值统一使用：

> 十进制字符串。

单位使用：

> stable unit_id。

---

# 11. 首批 Golden Cases

优先处理 Phase 0 已识别的：

## GC-PUMP-001

正常清水泵：

> 公式 + 查表 + 等级判定。

## GC-PUMP-002

范围边界：

> 开闭区间、重叠、越界。

## GC-PUMP-003

缺少实际效率：

> 保留能够合法计算的结果，但不得给出缺乏依据的确定等级。

## GC-PUMP-004

未知类别：

> 不允许默认成为已知泵型。

---

# 12. Golden Case 批准规则

Golden Case 不能因为：

> 当前 evaluator 这么算

就 Approved。

必须有：

```text
原始标准证据
+
当前数据
+
当前实现
+
人工复核
```

共同支持。

状态：

```text
DRAFT
REVIEWED
APPROVED
DEPRECATED
```

Phase 1 目标：

> 至少形成一组真正 `APPROVED` 的 pump_water Golden Cases。

---

# 13. P1-G05：P0 证据复核

Phase 1 不直接修所有 P0。

优先调查：

### AUD-010

`_interval_hit`

确认：

- 当前 parser 是否真的存在业务边界错误；
    
- 哪些表达式由实际标准使用；
    
- Golden Case 是否能够覆盖。
    

---

### AUD-011

`v4_validation` 与 `input_normalization`

确认是否：

> 相同输入在两条路径产生不同业务含义。

---

### AUD-030

V4 手工规则与 metadata 派生规则双真相源。

确认是否：

> 已经产生实际行为差异。

---

### AUD-031

默认判定日期。

明确：

```text
evaluation_date
standard_effective_date
default_as_of_date
```

真实业务语义。

---

# 14. P0 复核结果只允许三种

```text
CONFIRMED_P0
```

有明确证据证明当前行为会产生错误结论。

```text
NOT_P0
```

经复核不属于业务正确性问题，可降为 P1/P2。

```text
NEEDS_MORE_EVIDENCE
```

现有证据不足。

不要为了“关问题”强行下结论。

---

# 15. Phase 1 默认不修改 evaluator

即使 P0 被确认：

> 先形成证据和 Golden Case。

除非用户另行批准 Hotfix，否则 Phase 1 不以修 evaluator 为主要工作。

真正结构改造主要进入：

> Phase 2 / Phase 3。

---

# 16. P1-G06：Windows V1 Scope 决策

Phase 0 当前工程草案是：

```text
IN_V1 candidates:
transformer
compressor
pump_water
```

三个 motor 与 `heat_pump_chiller`：

```text
UNDER_REVIEW
```

其余当前：

```text
POST_V1
```

但 Phase 0 已明确：

> 这不是商业批准。

Phase 1 必须由产品负责人确认：

- 哪些确实是 Windows V1 首发；
    
- 哪些明确 POST_V1；
    
- 是否需要调整工程草案。
    

---

# 17. Scope 决策不能只依据代码成熟度

至少结合：

- 实际工作中使用频率；
    
- 客户需求；
    
- 软件出售价值；
    
- 标准覆盖价值；
    
- 已有工程成熟度；
    
- 开发工作量；
    
- 风险。
    

最终形成真正：

> Windows V1 Product Scope。

---

# 18. Phase 1 不处理的工程债

以下已知问题原则上仍留 Phase 2：

- `domain/devices/` 删除；
    
- evaluator 兼容门面；
    
- 循环依赖；
    
- `inspect.signature`；
    
- bootstrap 分层穿透；
    
- metadata.py 拆文件；
    
- Json Repository 缓存；
    
- logging；
    
- Web 安全；
    
- UI 重构；
    
- dead code 大清理。
    

Phase 1 负责告诉 Phase 2：

> 正确契约应该是什么。

而不是提前完成结构重构。

---

# 19. Phase 1 交付物

继续控制文档数量。

建议主要形成：

```text
specs/equipment_efficiency/
    business_spec.md

    schemas/
        canonical.schema.json
        profile.schema.json
        golden_case.schema.json

    profiles/
        pump_water.md

    golden/
        pump_water/
            ...

ROADMAP.md
QA_BACKLOG.md
V1_SCOPE.md
ADR/
HANDOFF.md
TASK_STATE.md
```

Import Contract 如需单独 Schema：

```text
import_contract.schema.json
```

UI Metadata 可先作为 Product Schema 的独立 section，不要求本阶段做最终文件拆分。

---

# 20. Phase 1 不追求 Schema V1.0

本阶段使用：

```text
V0.x Draft / Reviewed
```

即可。

通过 `pump_water` 真实样板验证后：

> 才进入 Candidate。

不要为了形式过早叫 V1.0。

---

# 21. Phase 1 测试要求

必须继续运行：

> 当前 Legacy Regression。

已知基线失败：

> 不允许静默消失或被隐藏。

同时新增：

### Schema validation

确保新增 Schema 和示例文件合法。

### Golden Case validation

确保：

- case 可解析；
    
- Decimal 为字符串；
    
- unit_id 合法；
    
- 引用存在；
    
- Approved Case 有来源证据。
    

### Boundary cases

重点覆盖：

> pump_water。

---

# 22. Phase 1 禁止事项

禁止：

- 批量迁移 17 Profile；
    
- 批量重写 evaluator；
    
- 大规模目录搬迁；
    
- 删除 Legacy evaluator；
    
- 开完整 PySide6 UI；
    
- 建完整 SQLite 产品数据库；
    
- 开 Excel；
    
- 开报告；
    
- 合并 GHGTOOL；
    
- 抽公共产品包。
    

---

# 23. Phase 1 Exit Gate

只有全部满足才 PASS。

## Business Spec

- 业务规范 V0.x 已形成；
    
- public type 与 profile 关系明确；
    
- Support Status 语义明确。
    

## Contract

- Canonical Schema 已形成；
    
- Product/Profile Schema 已形成；
    
- Golden Case Schema 已形成；
    
- Import Contract 边界明确；
    
- UI Metadata 边界明确。
    

## pump_water

- 输入、公式、范围、查表、插值、缺失、结论和来源已完成映射；
    
- 现有历史数据能够映射到新版契约；
    
- 没有为了适配 Schema 丢失标准事实。
    

## Golden

- 首批 pump_water Golden Cases 已审查；
    
- 至少核心正常、边界、缺失场景存在 Approved Case；
    
- Golden 不是机械复制 evaluator 输出。
    

## P0

- AUD-010 / 011 / 030 / 031 已完成证据分类；
    
- 每项为 CONFIRMED / NOT_P0 / NEEDS_MORE_EVIDENCE 之一。
    

## Version

- Python Windows V1 正式版本已冻结；
    
- 版本字段语义已冻结。
    

## Scope

- Windows V1 Scope 已获得产品决策；
    
- 不再把工程草案误写成产品承诺。
    

---

# 24. Phase 1 PASS 后

状态：

```text
PHASE_1_PASS
```

下一状态：

```text
PHASE_2_READY
```

Phase 2 才允许开始：

> 最小正式工程底座和结构清理。

---

# 25. Phase 1 建议执行顺序

```text
P1-G01
业务规范骨架
↓
P1-G02
数据与版本契约
↓
P1-G03
pump_water 专业映射
↓
P1-G04
Golden Case
↓
P1-G05
P0 证据复核
↓
P1-G06
V1 Scope + Phase 1 收口
```

原则上：

> 一次只做一个 Goal。

每个 Goal 验收通过后再进入下一个。

---

# 26. Phase 1 核心原则

> **① 这阶段定义业务，不重写业务。**

> **② pump_water 用于验证规范，不用于提前启动 Phase 3。**

> **③ 旧实现是重要证据，但不是自动真相。**

> **④ Golden Case 必须有标准证据。**

> **⑤ Schema 必须适应真实业务，不让业务迁就漂亮的数据模型。**

> **⑥ P0 先证明，再修改。**

> **⑦ Scope 必须由产品决策确认。**

> **⑧ Phase 1 通过以后，Phase 2 才允许真正改工程结构。**