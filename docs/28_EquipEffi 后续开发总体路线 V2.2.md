# EquipEffi 后续开发总体路线 V2.2

**文档版本：** V2.2  
**适用项目：** EquipEffi 设备能效分析软件  
**文档性质：** 当前正式总体路线  
**状态：** Approved for Phase 0  
**上位规范：** 《青舟工业能源软件架构与产品一致性规范》

---

# 1. 路线定位

EquipEffi 后续不再按照旧 v15 / T04.xx 路线持续逐边界扩展，也不采用一次性推倒重写。

新的总体策略为：

> **冻结旧基线 → 建立业务真相 → 保护现有正确行为 → 渐进改造工程结构 → 用真实纵向样板验证新体系 → 分 Profile 迁移 → 完成 Windows V1 产品闭环。**

本路线的关键词不是：

> 重写。

而是：

> **受证据、黄金案例和回归基线保护的渐进式改造。**

---

# 2. 最高原则

EquipEffi 后续长期遵循：

> **业务真相先于代码结构。**

> **旧代码可改，已验证业务行为不能无证据丢失。**

> **旧实现不是永远正确，但新实现也没有天然优先权。**

> **任何业务行为变化必须有标准证据、业务规范或明确决策支持。**

> **一个业务能力在正式运行链中只能存在一个权威实现。**

> **Canonical JSON 是标准和正式参考数据唯一事实源。**

> **Python 不作为标准事实数据主源。**

> **SQLite 是运行时和查询格式，不是标准事实源。**

> **黄金案例保护业务真相，不保护 Python 实现细节。**

> **公共规范和契约先统一，公共代码后收敛。**

---

# 3. 与产品家族的一致性

EquipEffi 与温室气体排放核算软件保持：

- 产品使用习惯一致；
    
- 工程依赖方向一致；
    
- AppShell 一致；
    
- Design Token 一致；
    
- 数据治理方法一致；
    
- Decimal 与单位体系一致；
    
- Repository 思路一致；
    
- 测试和验收纪律一致；
    
- 历史结果不可漂移原则一致。
    

但以下内容必须独立：

- 设备专业对象；
    
- 输入字段；
    
- Profile；
    
- 标准适用关系；
    
- 公式；
    
- 查表；
    
- 插值；
    
- 等级判定；
    
- 淘汰逻辑；
    
- 结果模型；
    
- 设备专业页面。
    

GHGTOOL 是：

> **产品家族参考实现。**

不是 EquipEffi 当前代码必须逐项复制的模板。

---

# 4. 新旧路线治理切换

V2.2 生效后：

> 旧 v15 / T04.xx 不再决定项目下一任务。

旧材料保留为：

> **Historical QA Backlog / Historical Evidence**

不得删除其事实价值。

新的治理顺序：

```text
青舟工业能源软件架构与产品一致性规范
                ↓
EquipEffi 总体路线 V2.2
                ↓
当前 Phase 执行方案
                ↓
当前 Goal / Task
```

旧 HANDOFF 中任何“自动领取下一边界任务”的内容均失去当前执行权。

---

# 5. 当前路线不是“评价器重写计划”

现有评价层包含大量已经研究和调试过的标准细节。

因此原则上不得采用：

```text
旧 evaluator
    ↓
全部重写
    ↓
再尝试追平旧行为
```

正式迁移方式改为：

```text
旧正式实现
    ↓
Legacy Regression Baseline
    ↓
标准原文 + 旧行为 + 已知缺陷
    ↓
Golden Case Candidate
    ↓
专业复核
    ↓
Approved Golden Case
    ↓
渐进修改 / 迁移
    ↓
Parity / Intentional Change Verification
    ↓
切换新正式实现
    ↓
删除旧路径
```

---

# 6. 每个 Profile 的迁移状态

建议统一使用：

```text
LEGACY_ACTIVE
GOLDEN_BASELINED
NEW_IMPLEMENTATION_READY
PARITY_VERIFIED
NEW_ACTIVE
LEGACY_REMOVABLE
```

必要时增加：

```text
BLOCKED
POST_V1
OBSOLETE
```

核心门禁：

> 对应 Profile 的 Approved Golden Case 未建立，新实现未完成验证前，旧正式实现不得删除。

---

# 7. Legacy Regression 与 Golden Case 必须区分

现有单元测试属于：

> **Legacy Regression Baseline**

作用是：

> 防止我们无意改变旧行为。

它们不自动等于业务真相。

正式业务真相由：

> **Approved Golden Case**

表达。

可能存在：

```text
旧测试认为结果 = A
```

但标准复核发现：

```text
正确结果 = B
```

此时应：

- 保留变更依据；
    
- 更新旧测试；
    
- Approved Golden Case 锁定 B。
    

不能为了保持旧测试绿色而维持错误行为。

---

# 8. Golden Case 的形成方式

禁止简单采用：

> “现有程序怎么算，Golden Case 就怎么写。”

正式流程为：

```text
现有行为
+
原始标准证据
+
标准映射
+
人工复核
+
已知 P0/P1
        ↓
Golden Case Candidate
        ↓
Review
        ↓
Approved
```

---

# 9. Golden Case Schema

建议至少包含：

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

正式数值采用：

> 十进制字符串。

单位采用：

> 稳定 `unit_id`。

禁止依赖随意 float tolerance 掩盖业务误差。

---

# 10. Golden Case 不绑定内部实现

原则上不锁定：

- Python 函数调用顺序；
    
- 私有类名；
    
- trace 文本逐字内容；
    
- 内部数组无业务意义的排列。
    

Golden Case 锁定：

- 输入；
    
- 业务状态；
    
- 查表证据；
    
- 规则；
    
- 计算；
    
- 限值；
    
- 结论；
    
- 稳定 issue / rule ID。
    

---

# 11. 旧 QA Backlog 重新分类

旧 v15 / T04.xx 等问题统一进入：

```text
P0
P1
P2
OBSOLETE
```

## P0

可能造成错误业务结论，包括：

- 选错标准；
    
- 选错表；
    
- 单位错误；
    
- 公式错误；
    
- 比较方向错误；
    
- 错误插值；
    
- 非法外推；
    
- “—”错误处理；
    
- 标准适用范围错误；
    
- 淘汰判定错误；
    
- 缺少必要参数仍给确定结论。
    

## P1

结论基本正确，但：

- 追溯不足；
    
- 来源不足；
    
- 审计不足；
    
- 专业详情不足。
    

## P2

低风险问题：

- 次要边界；
    
- UI 文案；
    
- 低频输入；
    
- 非关键体验问题。
    

## OBSOLETE

已经被新版规范或产品设计取代。

---

# 12. P0 不阻止整个新架构建设

P0 的正式门禁是：

```text
某 Profile 进入 NEW_ACTIVE
        ↓
该 Profile 的 P0 = 0
```

Windows V1 发布前：

```text
所有 IN_V1 Profile
        ↓
P0 = 0
```

但不要求：

> 全部旧 P0 修完才能建立 AppShell、Repository 或新规范。

---

# 13. Phase 0 允许窄范围 P0 Hotfix

Phase 0 默认：

> 不修改 evaluator。

但增加一个严格例外：

> **P0 Hotfix Lane**

只有满足以下条件才能执行：

- 已确认会导致错误业务结论、数据破坏或严重安全问题；
    
- 修复范围最小；
    
- 不做结构重构；
    
- 不顺手清理代码；
    
- 必须新增或更新针对性测试；
    
- 必须记录修复前后行为。
    

Phase 0 分为：

```text
Phase 0A
冻结和审计

Phase 0B
仅批准的 P0 Hotfix
```

---

# 14. 死代码处理策略

代码审计发现的：

- `domain/devices/` 空壳；
    
- legacy importer/writer；
    
- report exporter；
    
- template builder；
    
- 未使用 Repository；
    
- 未使用 service；
    
- 未接线 adapter；
    

不得仅因“零引用”自动删除。

Phase 0 先标记：

```text
DELETE_CANDIDATE
```

并验证：

- production refs；
    
- tests；
    
- CLI；
    
- 动态导入；
    
- build；
    
- 外部契约；
    
- 历史兼容。
    

原则上在 Phase 2 工程清理阶段删除。

只有确认：

> 纯空壳 + 无任何运行意义 + 明显造成双正式架构歧义

时，才可在 Phase 0B 单独清理。

---

# 15. 一个能力只能有一个正式实现

现有审计已经发现双架构和兼容门面问题。

后续禁止长期存在：

```text
旧正式 evaluator
+
新正式 evaluator
```

两套运行实现。

迁移期间允许：

> Adapter / Compatibility Layer

但必须明确：

```text
AUTHORITATIVE_IMPLEMENTATION
```

切换完成后旧路径应进入：

```text
LEGACY_REMOVABLE
```

再统一删除。

---

# 16. 元数据重新分类

现有 `metadata.py`、`device_specs.py` 等承载了过多不同性质的信息。

以后不得再把所有内容统称：

> metadata。

正式拆成四类。

## 16.1 Canonical Catalog

保存标准事实：

- 标准号；
    
- 标准版本；
    
- 表格；
    
- 阈值；
    
- 枚举值；
    
- 适用范围数据；
    
- 单位；
    
- 来源；
    
- 条款；
    
- 有效期；
    
- 审核状态。
    

---

## 16.2 Product / Profile Schema

保存 EquipEffi 产品自身输入契约：

- profile_id；
    
- 稳定字段 key；
    
- 数据类型；
    
- 默认 unit_id；
    
- 字段关系；
    
- 必填性；
    
- 业务分组；
    
- 合法输入结构。
    

---

## 16.3 Import Contract

保存外部输入映射：

- V4 Sheet；
    
- Excel 列名；
    
- 别名；
    
- 模板字段；
    
- 导入映射；
    
- 外部文件版本。
    

---

## 16.4 Ruleset / Domain

保存业务行为：

- 如何选择标准；
    
- 如何选表；
    
- 是否插值；
    
- 如何比较；
    
- 如何处理缺失；
    
- 如何形成等级；
    
- 如何形成淘汰结论。
    

---

# 17. UI 展示元数据单独管理

例如：

- 中文显示名；
    
- 帮助文字；
    
- UI 排序；
    
- 高级字段标记；
    
- 提示信息。
    

不应自动进入 Standard Canonical。

原则是：

> 标准事实、产品输入定义、导入协议、业务行为、UI 展示不能再混成一个 1800 行模块。

---

# 18. Canonical Source

V1 正式采用：

> **JSON**

作为设备标准与正式参考数据唯一事实源。

链路：

```text
Canonical JSON
      ↓
Schema Validation
      ↓
Cross Validation
      ↓
Normalization
      ↓
Build
      ↓
catalog.sqlite
```

禁止：

- 人工修改发布 SQLite；
    
- JSON/YAML 并行成为正式事实源；
    
- Python 常量成为标准表格事实源。
    

---

# 19. Canonical 与 Ruleset 的边界

Canonical 表达：

> 事实。

Ruleset 表达：

> 行为。

例如：

```text
某功率下三级效率是多少
```

属于 Canonical。

而：

```text
该条件应查哪张表
是否允许插值
边界包含左还是右
如何形成等级
```

属于 Ruleset。

当前不发展复杂的“JSON 可执行规则语言”。

---

# 20. Windows V1 版本模型

正式使用：

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
global algorithm_version
```

---

# 21. ruleset_version 的唯一语义

`ruleset_version` 表示：

> 同样输入 + 同样 Canonical 数据时，决定业务结论的规则集合版本。

只改 UI：

> 不升级。

修正查表、边界、插值、比较或结论逻辑：

> 必须升级。

---

# 22. 数据库体系

Windows V1 保持三库。

## catalog.sqlite

- 官方标准；
    
- 标准表；
    
- 阈值；
    
- 来源；
    
- 正式参考数据。
    

性质：

> 只读、可重建。

## user.sqlite

- 用户设置；
    
- 用户自定义参数；
    
- 设备档案；
    
- 本地偏好。
    

## records.sqlite

- Workspace；
    
- 正式 Record；
    
- 输入快照；
    
- 结果快照；
    
- 数据引用；
    
- lineage；
    
- audit。
    

---

# 23. Workspace 与 Record

正式采用：

```text
Workspace
    ↓
反复修改 / 计算
    ↓
Finalize
    ↓
Record
```

## Workspace

可变。

Windows V1 原则上支持：

> 跨启动保存和恢复。

## Record

不可变。

需要重新分析：

```text
Record A
    ↓
Create Workspace from Record
    ↓
重新分析
    ↓
Record B
```

---

# 24. Workspace 与 Record 不混为一个实体

不采用：

```text
analysis
status=draft/final
```

简单混用。

概念上至少区分：

```text
analysis_workspaces
analysis_records
record_lineage
audit_events
```

具体物理表结构在样板阶段验证后冻结。

---

# 25. 正式记录事务

Finalize 时：

```text
Record
+
Input Snapshot
+
Result Snapshot
+
Data References
+
Rule References
+
Audit Event
```

必须：

> 同一事务写入。

任何一步失败：

> 整体回滚。

---

# 26. 设备档案与分析输入分离

正式模型：

```text
Device Profile
      ↓
复制 / 引用
      ↓
Analysis Input Snapshot
      ↓
本次允许调整
      ↓
Record
```

设备档案以后发生变化：

> 不得改变历史分析。

---

# 27. Windows V1 Scope 必须明确

旧系统拥有：

> 15 类公共设备 / 17 Profile。

新版不能默认承诺全部。

每个 Profile 必须明确：

```text
IN_V1
POST_V1
UNDER_REVIEW
OBSOLETE
```

未进入 V1 的 Profile 不得在正式 UI 中伪装成已支持。

---

# 28. 运行时支持状态

业务状态至少应能区分：

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

最终命名在业务规范中冻结。

不能把不同原因统一显示：

> 无法计算。

---

# 29. 首个纵向样板

首个样板不用于证明：

> 页面能显示。

而用于证明完整体系成立。

至少覆盖：

- 明确标准包；
    
- 多维查表；
    
- 派生计算；
    
- 单位转换；
    
- 范围边界；
    
- 缺失参数；
    
- 插值或禁止插值；
    
- 业务结论；
    
- 来源；
    
- Workspace；
    
- Record；
    
- 历史读取；
    
- 尽可能覆盖淘汰目录。
    

---

# 30. 首个样板候选

当前优先候选：

> `pump_water`

但不在总体路线中永久写死。

Phase 0 应比较候选：

- 标准证据质量；
    
- evaluator 成熟度；
    
- Legacy Test 可信度；
    
- P0；
    
- 数据可迁移度；
    
- 业务复杂度；
    
- 实施工作量。
    

然后正式决定。

---

# 31. AppShell 策略

不先完成所有空页面。

第一步只做：

```text
Design Token
+
薄 AppShell
+
首个真实设备分析页
```

样板证明架构可用后，再扩展：

```text
首页
标准库
新建分析
Excel 导入
分析记录
参数库
设置
```

UI 统一：

> 使用方式和视觉语言。

不强制：

> 专业业务页面布局完全一致。

---

# 32. 旧 Tk / Web 界面定位

现有 Tk / Web 默认分类为：

```text
PROTOTYPE
REFERENCE
DIAGNOSTIC
```

Phase 0 不删除。

后续按资产审计决定：

```text
KEEP
MIGRATE
DEPRECATE
DELETE_CANDIDATE
```

---

# 33. Excel 原则

Excel 继续后置。

未来唯一允许链路：

```text
Excel
 ↓
Import Contract
 ↓
Parser
 ↓
Domain Input
 ↓
Application Service
 ↓
Domain
 ↓
Workspace / Record
```

禁止建立：

> Excel 专用评价算法。

---

# 34. 发布表面分类

所有资产增加：

```text
RELEASE_SURFACE
```

至少区分：

```text
V1_RUNTIME
DEV_ONLY
PROTOTYPE
LEGACY
NOT_SHIPPED
```

风险优先级必须结合：

> 是否真正进入 Windows V1 发布包。

例如：

Web Server 的安全问题如果属于：

```text
PROTOTYPE / NOT_SHIPPED
```

仍需处理，但未必阻断 Windows V1。

---

# 35. 性能基线

Phase 0 先测现状，不拍脑袋设 SLA。

至少测：

```text
应用核心启动
Standard Pack 首次加载
Standard Pack 重复读取

单条评价
100 条批量
1500 条批量

Workspace 保存
Workspace 加载
Record 读取
```

Excel 实现后增加：

```text
Workbook parse
Workbook writeback
```

Phase 1/2 根据真实基线制定预算。

---

# 36. 标准仓库性能原则

类似当前：

> 每次 get_pack 都重新读取并解析完整 JSON

的行为不得直接进入最终 V1。

目标：

- 校验一次；
    
- 缓存已解析 Pack；
    
- 建立必要索引；
    
- 保持返回对象不可污染正式缓存；
    
- 明确缓存失效机制。
    

具体实现由性能测试决定。

---

# 37. 自动化质量门禁

现阶段不要求立即依赖 GitHub Actions。

但必须建立：

> 一个可重复执行的统一质量门禁。

最终至少覆盖：

```text
Legacy Regression
Approved Golden Cases
Canonical Validation
Schema Validation
Migration Tests
compileall
dependency check
architecture boundary scan
performance regression
release audit
```

GitHub Actions 后续只是该门禁的一种执行环境。

---

# 38. 文档规模控制

停止继续产生：

```text
v15
v16
v17
v18
```

整份复制型执行手册。

后续权威文档收敛为：

```text
ROADMAP.md
BASELINE.md
ASSET_AUDIT.md
QA_BACKLOG.md
V1_SCOPE.md

ADR/

AGENTS.md
HANDOFF.md
TASK_STATE.md
```

历史文档进入：

```text
docs/archive/
```

不删除事实，但不再参与下一任务决策。

---

# 39. WIP 控制

任何时刻原则上只允许：

> 一个当前 Phase。

同一 Phase 内只允许有限 Goal 并行。

禁止：

> Phase 1 尚未通过就同时开始 Phase 3/4 的正式实现。

允许进行只读调研，但不能越级提交正式产品功能。

---

# 40. Phase 0

目标：

> 重新建立可信项目基线。

Phase 0 拆分：

```text
0A
治理切换
基线冻结
真实测试
资产盘点
风险分类
Scope
样板选择

0B
仅批准的 P0 Hotfix
必要治理清理
```

Phase 0 不进行全面重构。

---

# 41. Phase 1

建立：

```text
业务规范 V0.x
Canonical Schema
Product/Profile Schema
Import Contract Schema
Golden Case Schema
Support Status
首个样板标准映射
```

这是：

> 业务真相建模阶段。

---

# 42. Phase 2

建立最小正式工程底座：

```text
Python 3.12
PySide6
Repository Protocol
三库职责
Migration 基础
日志
Design Token
薄 AppShell
```

同时开始解决：

- 双正式架构；
    
- 循环依赖；
    
- 包级反向依赖；
    
- 大型 metadata 的职责拆分；
    
- 确认后的 DELETE_CANDIDATE。
    

但不大规模迁移所有 Profile。

---

# 43. Phase 3

完成首个真实纵向样板：

```text
规范
↓
Canonical
↓
Product Schema
↓
Ruleset
↓
Golden Case
↓
Domain
↓
Application
↓
PySide6
↓
Workspace
↓
Record
↓
Reopen / Reproduce
```

只有 Phase 3 通过，才能证明新版架构适合真实设备标准。

---

# 44. Phase 4

将样板中验证成功的设计：

> 通用化。

包括：

- persistence；
    
- Catalog；
    
- Profile Schema；
    
- Repository；
    
- Workspace；
    
- Record；
    
- lineage；
    
- audit；
    
- performance；
    
- migration。
    

不再依靠理论设计通用化。

---

# 45. Phase 5

迁移所有：

```text
IN_V1
```

Profile。

每个 Profile 独立执行：

```text
Legacy Baseline
↓
Golden Case
↓
P0 Close
↓
Migration
↓
Parity
↓
NEW_ACTIVE
↓
Legacy Removal
```

不能一次批量重写 17 个 evaluator。

---

# 46. Phase 6

建设完整产品 Shell：

```text
首页
标准库
新建分析
Excel 占位
分析记录
参数库
设置
```

并正式达到产品家族统一 UI 规范。

---

# 47. Phase 7

进行业务生命周期与质量收口：

- Workspace；
    
- Record；
    
- history reproduction；
    
- Golden Coverage；
    
- P0=0；
    
- P1 收口；
    
- performance budget；
    
- audit；
    
- version compatibility。
    

---

# 48. Phase 8

实现外围能力：

- Excel；
    
- Word/PDF；
    
- 导出；
    
- 备份恢复；
    
- 项目文件；
    
- 数据包更新；
    
- 授权；
    
- 关于；
    
- 发布构建。
    

---

# 49. Phase 9

Windows V1 正式全量验收。

验收范围包括：

```text
业务正确性
标准证据
数据完整性
Golden Cases
UI一致性
DPI
普通窗口
数据库
迁移
历史复现
性能
日志
安全
打包
版权边界
发布审计
```

---

# 50. Phase 10

Windows V1 稳定后再考虑：

```text
共享公共代码包
工业能源综合版
Web
HarmonyOS
平板
微信小程序
```

当前只要求：

> 公共契约可跨平台。

不提前建设第二平台产品。

---

# 51. 总体阶段路线

```text
Phase 0
重新基线与治理切换
        ↓
Phase 1
业务规范与数据契约
        ↓
Phase 2
最小正式工程底座
        ↓
Phase 3
真实纵向样板
        ↓
Phase 4
经过样板验证后的通用化
        ↓
Phase 5
V1 Profile 渐进迁移
        ↓
Phase 6
完整产品 Shell
        ↓
Phase 7
生命周期与质量收口
        ↓
Phase 8
Excel / 报告 / 发布外围能力
        ↓
Phase 9
Windows V1
        ↓
Phase 10
公共包 / 综合版 / 多平台
```

---

# 52. V2.2 相对 V2.1 的正式变化

V2.2 新增并冻结：

### ① 迁移性质

从：

> 可能被理解为新版 Domain 重建

改为：

> **Golden-protected incremental migration。**

### ② Phase 0 Hotfix

增加：

> P0 Hotfix 窄口。

### ③ Legacy Test 定位

明确：

> Legacy Regression ≠ Golden Truth。

### ④ 死代码处理

从：

> 资产盘点

提升为：

> DELETE_CANDIDATE + 受控清理。

### ⑤ 元数据职责

新增：

```text
Canonical Catalog
Product/Profile Schema
Import Contract
Ruleset
UI Metadata
```

五类职责。

### ⑥ 性能

新增：

> Performance Baseline / Budget。

### ⑦ 发布表面

新增：

> RELEASE_SURFACE。

### ⑧ 文档治理

压缩 Phase 交付文档，停止版本手册复制膨胀。

---

# 53. 当前唯一允许的下一步

V2.2 生效后：

> **只执行 Phase 0。**

Phase 0 尚未 PASS 前，不允许：

- 继续 T04.xx；
    
- 批量修改 evaluator；
    
- 大规模搬目录；
    
- 建全部 PySide6 页面；
    
- 批量迁移 17 Profile；
    
- 开发 Excel；
    
- 抽共享公共包；
    
- 合并 GHGTOOL；
    
- 启动跨平台。
    

---

# 54. 最终路线结论

EquipEffi 后续不是：

> 重新做一套设备能效分析软件。

而是：

> **把现有已经积累的设备标准、算法、测试和追溯成果，从一个历史演进复杂的 Python 工程，逐步提升成有业务规范、有 Canonical 数据、有黄金案例、有稳定产品架构、有历史复现能力的正式 Windows 专业软件。**

因此：

> **保业务真相，不保历史偶然结构。**

> **保正确算法，不保不必要兼容层。**

> **保标准研究成果，不保 Python 硬编码形式。**

> **保经过证据确认的行为，不盲目保旧行为。**

> **任何新实现必须先证明自己没有丢掉旧系统真正有价值的专业知识。**

这就是 EquipEffi V2.2 的核心。