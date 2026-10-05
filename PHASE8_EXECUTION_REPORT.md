# PHASE8_EXECUTION_REPORT

Phase 8 — GB 19762 Excel 批量评价闭环。

按任务建议分 **8A（模板正式化 / 一致性矩阵 / Reader）** 与 **8B（批量评价 / Writer / `batch_record` / Qt 闭环）** 两段执行，**同一分支、同一个 PR、一个 final Head**；8A 通过其内部 Gate 后才进入 8B。

> **8B 规格补记**：8A 自测通过后，产品负责人给出了更细的 8B 规格（G05～G09）。
> 首轮 8B 实现与该规格的 6 处差距已全部补齐，见 §6 与 §7 的「8B 规格符合性」。

## 0. 平台预检查

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/adgo07/EquipEffi.git` |
| Base | `master@79ea075967ace07aa9880369220d8bff9b53d9e8`（= Phase 7 的 PR #15 merge） |
| 分支 | `phase8/gb19762-excel-batch` |
| PR | **#16** — https://github.com/adgo07/EquipEffi/pull/16（`open`, `merged=false`） |
| final Head | 见 §11 |
| locked central SHA | `ee5feb0cc34dbd99790500fadd0c4c932e202a20`（**未变更**） |
| 相关 Frozen Contract | Architecture `V2.1 FROZEN`、Numeric Contract `v1 FROZEN` |
| 适用 MUST / MUST NOT | Excel-as-adapter（Excel 只调用同一 evaluator / Calculator，**不复制第二套算法**）；UI 中文优先；普通 UI 不泄露内部 ID/JSON；不得为显示提前 ROUND 影响业务比较；`NEVER_DESTRUCTIVE_RECORD_ASSET` |
| 冲突分类 | `LOCAL DEFECT`（我引入 2 处，已修，见 §9）；**无** `CENTRAL CONTRACT GAP` |
| 是否需改中央 Contract | 否。**本任务不涉及中央公共 Contract。** |

**Standard Issue**：不存在新的标准问题，台账仍只有 `EQP-STD-GB19762-001`（已 `RESOLVED`）。本 Phase **未改变**任何既有软件解释，也未新增标准问题。

## 1. G00 — Phase 7 收口 + Phase 8 rebaseline

新增 [docs/phase7_acceptance_record.md](docs/phase7_acceptance_record.md)：

| 记录项 | 值 |
|---|---|
| Phase 7 | `PHASE_7_PASS` |
| accepted head | `7d6f46c05eb1a6ad7a72dd2dc4a3bf964f29cf62` |
| PR | `#15` |
| merge SHA | `79ea075967ace07aa9880369220d8bff9b53d9e8` |
| acceptance date | 2026-10-05 |

来源说明明确写出：**Phase 7 PASS 为产品负责人收到独立验收后作出的决定，不是执行者自行宣告**；并如实记录复验三项阻断（类别联动越权／两位小数未落实／历史详情不完整）与修复。

同步 `Phase 7 = PHASE_7_PASS` / `Phase 8 = IN_PROGRESS`：`AGENTS.md`、`ROADMAP.md`、`REFERENCE_STANDARD_ROADMAP.md`、`TASK_STATE.md`、`HANDOFF.md`、`UI_CURRENT_STATE_AUDIT.md`、`QA_BACKLOG.md`。

**Owner 产品规则正式落档**：`AGENTS.md` 新增 **§2.9**，逐条记录本次 12 条产品决定与权威层级。

**正式承接**（未借本阶段清理全部 legacy backlog）：`QA-EXCEL-001`、`QA-P5-003`、`QA-P6-001`。

## 2. G01 — V6 模板正式资产化

- Owner 指定的 V6 基线作为**受跟踪的构建输入**入仓：
  `specs/equipment_efficiency/templates/设备能效分析空白模板_重构版V6_变压器.xlsx`
  SHA-256 `FDB8C0B09925B5AE0EA0F0A941040B27890B5455E8E5920E02C409EDD4699CA1`（493,067 B）
- 正式资产由 [tools/build_v6_pump_template.py](tools/build_v6_pump_template.py) 生成：
  `src/equipeffi/resources/templates/设备能效分析空白模板_重构版V6_20261005.xlsx`
  SHA-256 `EE9DBE17A06081739CFB8EF0D330CE30B4634CBA5CE29CCD1EAB058D09348810`（398,096 B）
  **生成前校验基线 SHA-256，不匹配即拒绝生成**（该守卫在实施中真的抓到过我抄错的期望哈希）
- 新增 `TEMPLATE_MANIFEST.json`：template identity / version / SHA-256 / 来源说明 /
  授权修改范围 / 容量实测数据；`BASELINE.md` 记录资产与清单哈希
- 正式产品路径经 `V6TemplateResource` 只使用**入仓资产**，**不依赖本地开发路径**
  （`template_resource.py` 的 `V6_TEMPLATE_IDENTITY` 与清单逐项一致，由门禁机械校验）
- **V4 降为 `LEGACY`**：不再是正式用户模板；实现与兼容保留，本阶段不大规模删除
- V6 成为当前 Windows V1 正式模板；本阶段**只正式接通「离心泵」Sheet**

## 3. G02 — 离心泵 Sheet ↔ Application 一致性矩阵

新增 [tools/check_v6_pump_template.py](tools/check_v6_pump_template.py)：**32 项机械门禁，GATE = PASS**。

覆盖：资产身份 / 清单一致（含 SHA 与体积） / 18 个 Sheet 与顺序 / 27 列 /
`TblPump` 范围与列数 / Sheet 保护 / editable-locked 契约 / 结果列保留 /
**类别枚举逐项等于 `PUMP_CATEGORIES`** / 命名范围 / 类别验证指向枚举 /
**石化类不得由类别锁吸入方式** / 吸入方式验证为枚举且无 `OFFSET` /
级数验证覆盖全部单级类别 / 数量为正整数 / 结果列无业务公式 /
无业务算法特征 / 无跨表引用 / FieldDictionary 可读且覆盖 27 行。

**类别修正**（Owner 规则 5）：Excel 由「其他（请备注说明）」改为「**其他类别**」，
并新增「**不确定类别**」；与软件正式枚举**完全一致**（8 正式泵型 + 2 特殊类别 = 10 项）。

**石化泵纪律**（Owner 规则 5 特别提示）：`单级石油化工离心泵` / `多级石油化工离心泵`
的吸入方式**不**由类别决定，**未**被锁成单吸——与 Phase 7 复验 blocker 同一条纪律。

## 4. G03 — Excel 业务算法退出 + 统一容量策略

### 4.1 退出第二套业务算法

清空「离心泵」Sheet 中可**独立产出** GB19762 结果与等级结论的 Excel 公式：

```text
K  吸入方式（由类别推导）        L  级数（由类别推导）
N  比转速                       O/P/Q  C1/C2/C3
R  基准效率                     S  效率修正值
T  规定点效率                   U/V/W  1/2/3 级效率
X  能效等级                     AA 自动备注（依赖上述公式形成评价结论）
```

**结果列 / 列头 / 样式 / 锁定全部保留**，改由软件批量评价写入。
刻意**没有**把系数挪到配置 Sheet、**没有**隐藏公式、**没有**保留第二算法并声称"软件会覆盖"。

### 4.2 其他设备 Sheet 结构保护

新增 [tools/check_v6_untouched_sheets.py](tools/check_v6_untouched_sheets.py)：
对 **17 个非授权 Sheet** 逐项比对 cell values/formulas、number_format、protection、
data validation、tables、sheet order、merged cells、sheet 保护与 **defined names**
→ **0 差异，GATE = PASS**。

（按任务要求**不**断言 ZIP 逐字节不变；正常 OOXML 重写会改变压缩字节。）

### 4.3 统一容量策略（实测，非预设阈值）

机制：**Excel Table（`TblPump`，27 列 × 100 数据行）+ 语义式 Reader**。
用户直接在表内继续填写或粘贴，Excel 原生 Table 自动扩展；
**软件端不询问行数、不逐 Sheet 扩容**。

| 场景 | 文件大小 | 读取耗时 | 峰值内存 | 读取行数 | 截断 |
|---|---:|---:|---:|---:|---|
| 3 行 | 388.9 KB | 0.040 s | 1.6 MB | 3 | 否 |
| 100 行 | 389.3 KB | 0.051 s | 1.9 MB | 100 | 否 |
| 1,000 行 | 443.5 KB | 0.325 s | 10.9 MB | 1,000 | 否 |
| 10,000 行 | 977.6 KB | 3.075 s | 99.7 MB | 10,000 | 否 |

**8B 端到端大批量实测**（真实 Excel 输入 → Batch 评价 → 结果 Workbook 写回）：

| 行数 | 输入文件 | 输出文件 | 耗时 | 峰值内存 |
|---:|---:|---:|---:|---:|
| 100 | 400,320 B | 400,851 B | 5.283 s | 13.2 MB |
| 1,000 | 442,403 B | 453,774 B | 13.797 s | 21.8 MB |
| 10,000 | 846,024 B | 961,941 B | 78.266 s | 120.3 MB |

均无读取截断、无 hang、无静默丢行（逐行断言 `data_row_count` 与结果数一致）。

无需软件端逐次设置容量；**无 hang、无数据丢失、无读取截断**。
（实测工具：[tools/measure_v6_capacity.py](tools/measure_v6_capacity.py)）

## 5. G04 — Reader 重写 + 关闭 `QA-EXCEL-001`

### 5.1 数值保真（`QA-EXCEL-001`）

`ooxml_reader._parse_number` 曾把非整数 `Decimal` **转成 float** 再经 `str()` 送进正式评价链，
等于把 Numeric Contract 降级。实测精度损失：

```text
0.12345678901234567890123456789012345  ->  0.12345678901234568   （35 位被截成 17 位）
12345678901234567890                   ->  1.2345678901234567e+19（大整数被改写）
```

**修复**：整数值返回 `int`、其余保留 `Decimal`，**绝不经过 `float`**。
覆盖整数 / 普通小数 / 35 位长小数 / 科学计数法 / 大整数 / 文本 / 空值。
**未**因为 Reader 方便而把 Numeric Contract 降级。

### 5.2 正式 Reader

新增 [pump_workbook_reader.py](src/equipeffi/infrastructure/excel/pump_workbook_reader.py)：

- **只读正式 input columns**（`B`–`M`、`Y`、`Z`）；
  `N`–`X`、`AA` 等**旧计算结果永不作为业务输入**（有专门回归测试把伪造的
  旧比转速 / 旧 C1 / 旧等级 / 旧自动备注写进工作簿，断言结论不变）
- **行启用语义式**：所有用户可编辑输入字段全空 → 跳过；**任一非空 → 读取并执行验证**。
  只填「安装位置」的行**不会**被静默跳过
- 表头做**防御性校验**（被误改时报错，而不是静默读错列）
- **无固定行上限**：读取到工作簿实际最后一行

## 6. G05 — 批量评价 + Writer + `batch_record`

### 6.1 最小 additive 持久化

新增迁移 `003 create_batch_record`（**独立表**）：

- 只追加；**不触碰** `record` / `workspace`；`001` / `002` 的
  migration_id、顺序与 checksum **完全未变**
- `record` 表列契约不变（23 列，门禁强制）
- `schema_version` 2 → 3（这是本阶段**唯一**的 schema 变更，Owner 规则 10 明确允许）

新增 `SqliteBatchRecordRepository`（只追加，重复主键显式拒绝，失败保留根因）。

### 6.2 批量评价语义

[PumpBatchEvaluationService](src/equipeffi/application/services/pump_batch_evaluation_service.py)：

- 每一行都调用**正式 Application 契约**——Excel **不是**计算引擎
- **不**创建任何单台 Record（`records_created` 恒为 0，门禁断言数据库 `record` 表为空）
- 一次 Workbook / 一次离心泵批量评价 → **一条** `batch_record`
- **软件侧独立校验数量**（必填正整数 > 0；不得空白默认 1 / 0 / 负数 / 小数）——
  Excel Data Validation 只是辅助，可被粘贴绕过
- **系统异常与业务结论严格区分**：单行 Python 异常计为失败行、结论为「评价失败」，
  **绝不**写成「无法评价」或「无法判定」；且**不**中断其余行

### 6.3 结果 Workbook

[PumpResultWorkbookWriter](src/equipeffi/infrastructure/excel/pump_result_writer.py)：

- 输出**新的** Workbook，**绝不覆盖**输入（写入前显式拒绝同路径）
- 18 个 Sheet 全部保留，不删除、不重排
- 只写结果列；用户输入列原样保留
- 结果列写**完整精度**数值，2 位显示由模板既有数字格式负责（证据不丢、显示合规）

## 6.5 8B 规格符合性（G05～G09 逐条）

| 8B 要求 | 实现 |
|---|---|
| Excel row → `PumpAnalysisRequest` → **同一个** `evaluate()` | 是；`_request_from_row` 只映射正式输入列 |
| **不得**逐行调用 `analyze_and_record()` | **从不调用**；批量路径不产生任何单台 Record |
| 禁止直调 Domain evaluator / 复制公式 / 等级判断 / 边界规则 | 只经 Application；`record` 表始终为空（门禁断言） |
| 行级独立：一行失败不回滚其他行 | 单行异常被捕获并计入执行失败，其余行继续 |
| 系统级失败必须明确报告 | 单行 → `执行失败`；整批 → 向上抛出或 UI 明确提示 |
| 保留原顺序 / 原行号映射 | 每行结果带原 Excel 行号，按行号排序写回 |
| 区分 1级/2级/3级/未达标/不适用/无法评价 | 六种全部可得（测试逐一断言） |
| 其他类别沿用现有语义 | `OUT_OF_STANDARD_SCOPE` → `不适用` |
| 不确定类别 → `无法评价` | `UNRESOLVED` + `requires_category_confirmation` → `无法评价` |
| `INVALID_INPUT` 不属于正式结论 | → `输入错误`，`evaluation_status` 为 `None` |
| `EXECUTION_ERROR` 不属于正式结论 | → `执行失败`，`evaluation_status` 为 `None` |

### batch_record（G06）

`003 create_batch_record` + `004 extend_batch_record`（**均为 additive**）。
可承载规格要求的全部字段（`batch_id` / `created_at` / `evaluation_date` /
`source_file_name`+`sha256` / `output_file_name`+`sha256` /
`template_id`+`version`+`sha256` / `sheet_name` / `standard_code` /
`data_row_count` / `total_quantity` / `evaluated_quantity` / `summary_json` /
`app_version` / `canonical_version` / `numeric_profile_id`）。

- **数量按「数量」列加权**：`数量=20` + `结论=2级` → `2级 +20 台`（测试断言）
- 三个口径分开：**数据行数** / **设备数量总计** / **完成正式评价数量**（台）
- 输入错误按**行**统计；其合法数量仅进 `input_error_quantity` 作辅助，**不**计入正式评价数量
- **不建逐行明细表**；逐设备详细结果保存在结果 Workbook
- **持久化时点**：评价完成 → 结果 Workbook 成功生成 → output SHA-256 取得 → 才写记录。
  结果文件写失败 → 向上抛出，**不**写"成功完成"的批次记录；
  结果已生成但记录写入失败 → `batch_record_error` 带回可读原因，UI 明确显示
  「结果文件已生成，但软件历史记录保存失败」，**不静默吞错**

### Writer（G07）

- 默认名 `原文件名_评价结果_YYYYMMDD_HHMMSS.xlsx`；**目标已存在则显式报错**，不静默覆盖
- 只向「离心泵」Sheet 既有结果区域写入；不删/不重排其他 Sheet
- **复用 V6 现有 12 个结果列**，不新增结果字段体系：
  `X` = 处理/评价状态 + 最终结论 + 能效等级（输入错误 / 执行失败一眼可辨）；
  `U/V/W` = 关键限值；`N`/`O–Q`/`R`/`S`/`T` = 比转速 / C1~C3 / 基准效率 / 效率修正 / 规定点效率；
  `AA` = 自动备注/说明
- 逐行明细足以看到：原输入、数量、每行结论、每行等级、关键结果、问题说明
- 写完整精度数值；2 位小数显示由模板既有数字格式负责（等级比较仍用完整精度）

### Qt 入口（G08）

一级导航入口为「**Excel导入**」；页面流程
**输出空白模板 → 选择 Excel → 导入检查 → 批量评价 → 结果保存 → 批次总结**。
「输出空白模板」为**一次操作**，直接复制 package 内正式 V6 模板，
**不**询问"泵多少行 / 变压器多少行 / 电机多少行"。

### 一致性（G09 / 门禁 20）

`tests/unit/test_phase8b_batch_consistency.py`：**29 条 Approved Golden**
（18 water + 11 chemical）经**真实 Excel 载体**（写入 V6 模板 → Reader → Batch → evaluate）
回放，逐条比对 `evaluation_status` / `conclusion` / `grade` / issue 语义 → **零漂移**；
并对每条做**最强口径**比对（Excel Batch 与单次 Application 的
`derived` / `thresholds` / `messages` 全量相等）。
另覆盖：其他类别、不确定类别、数量>1 加权、非法数量、单级/多级、单吸/双吸、
范围边界、大量空行、中间空行、100 / 1,000 / 10,000 行。

## 7. G06 — Qt 产品闭环

新增一级页面「**批量评价**」（`BatchPage`）：选输入 → 选输出 → 开始。
显示处理行数 / 已评价 / 未评价 / 失败、结论分布、需要关注的行、批次记录号、结果路径。

**不**询问行数、**不**要求逐 Sheet 扩容（门禁断言页面不存在此类控件或文案）。

**Qt 与 Excel 结论一致性**（Owner 规则 7）：结论文案上移到 Application
（`user_conclusion_text` / `user_conclusion_from_snapshot`），Qt 的 `labels.py`
退化为转发，从结构上消除两份文案漂移：

| 情形 | 用户可见结论 |
|---|---|
| 正常 | `1级` / `2级` / `3级` |
| 「其他类别」 | `不适用` |
| 「不确定类别」 | **`无法评价`**（不是「无法判定」） |

「不确定类别」是**正式类别选择**，不是非法输入：它进入批量评价结果与批次汇总，
并计入「未评价」与「需要关注的行」。**未新造 Domain enum**，复用既有
`category_status = UNRESOLVED` + `requires_category_confirmation = True`。

## 8. records.sqlite 原则

```text
records schema change = YES (additive only)
新增迁移 003 create_batch_record（独立表）
record / workspace 语义与列契约不变；001 / 002 未改动
```

这与 Phase 7 的"默认不改 schema"并不冲突：Owner 规则 10 **明确允许**为批次总结新增
最小 additive 持久化结构。**未出现**需要破坏性迁移的情形，因此**未触发 STOP 流程**。
**未新增** lineage table、audit_event table、`workspace.display_name`、Attempt table。

## 9. 过程中发现并修复的自身缺陷（如实记录）

### 9.1 架构违规（CI `Architecture boundaries` 步骤抓到）

Application 层的批量服务在函数内**延迟 import 了 Infrastructure 的 Excel reader/writer**。
延迟 import 只改变加载时机、不改变依赖方向，门禁判断正确。**修复**：按既有
`application/lifecycle/ports.py` 的模式建立
`application/ports/batch_workbook.py`（DTO + `BatchWorkbookReader` / `BatchResultWriter`
Protocol），服务改为**必须注入**端口，Infrastructure 实现端口，composition 注入真实适配器。

### 9.2 CI comparator FAIL 的真根因

CI 的 `Full suite known-regression comparator` 持续失败而本机始终 `gate=PASS`。
本仓 token 缺 `actions:read`（job log 与 artifact 均 401），只能靠 workflow
`::error::` 注解经 check-runs API 读取。诊断结果唯一违规是：

```text
unexpected_skips = ...test_phase8a_template_reader.TemplateAssetTests.test_owner_baseline_is_untouched
```

该测试在 CI 被 **skip**，因为 Owner 指定的 V6 基线位于本地未跟踪的 `outputs/`。
**修复**：把该基线作为**受跟踪的构建输入**入仓到
`specs/equipment_efficiency/templates/`，生成与校验的默认来源同步改到该路径，
并**去掉测试里的 skip 分支**（缺文件应直接失败，不得被静默容忍）。

期间我还因替换诊断块时 `end` 锚点在文件中出现两次，**误删了
"Full suite known-regression comparator (gating)" 与 "Upload exact regression evidence"**
两个真实步骤——已从上一版本逐行恢复，并核对 workflow 相对 base 只剩两处预期改动
（gating 步骤名、新增两个 Phase 8 测试模块）。所有临时诊断脚手架均已移除。

### 9.3 系列既有测试的编码缺陷

`test_build_lock` 的两个 subprocess 调用使用 `text=True` 而未指定 `encoding`，
沿用平台默认编码：本机（UTF-8）通过、CI runner（cp1252）抛 `UnicodeDecodeError`。
属既有缺陷但会阻塞本阶段 gating 证据，因此**就地修好**（显式 `encoding="utf-8"`）。

### 9.4 三个"把阶段退出条件当成永久断言"的测试

- `test_phase7_analysis_history`：Phase 7 的"持久化层零改动"是**阶段**退出条件，
  Phase 8 授权迁移后不应再对 HEAD 断言 → 改为断言长期不变式
  （001/002 身份与顺序、`record` 列契约、每条迁移 additive）
- `test_phase3_r3_closure` / `test_phase3_unified_analysis`：硬编码版本清单
  → 改为依据 `RECORDS_MIGRATIONS` 推导（仍强制 001/002 身份与连续性）
- `test_phase2_qt` / `test_phase6_product_shell`：Shell 构造需注入批量服务，
  否则"所有一级页面都真实"的断言会因空控件而失真

## 10. 实际验证结果

### 10.1 本地

```text
Phase 8A 专项                     33   全通过（隐藏 outputs/ 后仍 33 通过、零跳过）
Phase 8B 专项                     34   全通过
Phase 7 专项                      44   全通过
架构边界契约                      12   全通过
CI gating 模块列表                351  OK / exit 0
全量 unittest           1376 run / 1369 pass / 3 fail / 1 error / 3 skip
known-regression comparator       gate=PASS
                                  new_failures=0 new_errors=0
                                  unexpected_skips=0 missing_baseline_tests=0
模板一致性门禁                    GATE=PASS（32 项）
其他 17 个 Sheet 不变             diffs=0 / GATE=PASS
容量实测                          3/100/1000/10000 行，零截断
compileall -q src tools           exit 0
git diff --check                  clean
```

既有失败仍是既有失败（3 项 V4 reader/writer + 1 项 release audit 错误），
**未修复也未隐藏，且未把任何新失败加入 known baseline**。

### 10.2 实际 GitHub CI（final Head，全部 `success`）

```text
Windows Core
  [ 6] Compileall                                                          success
  [ 7] Architecture boundaries and metadata contract                       success
  [ 8] Application and core tests                                          success
  [ 9] Phase 2/3/4/5/6/7/8 settings, lifecycle, Stage D, Product Shell,
       analysis flow, Excel batch, Qt offscreen (gating)                   success
  [10] Full suite known-regression comparator (gating)                     success
  [12] Package and resource smoke                                          success
Pump Conformance
  [12] pump_chemical Stage D support + Phase 6 product shell (gating)      success
Whitespace check (gating)                                                  success
Full suite baseline (NON-GATING)                                           success
```

## 11. QA 条目变动

| 动作 | 条目 | 说明 |
|---|---|---|
| **关闭** | `QA-EXCEL-001` | Reader 保持可证明的十进制语义，绝不经过 float |
| **关闭** | `QA-P5-003` | Excel 侧第二套业务算法退出；Excel 只做批量输入/输出载体。**8B 补强**：29 条 Approved Golden 经真实 Excel 载体回放零漂移（门禁 20），可据正式 Excel E2E 结果处置 |
| 保留 | `QA-P6-001` | legacy Tk 保留但不接线；Phase 8 **明确不清理** |
| 保留 | `QA-P7-001` / `QA-P7-002` | 版本字段语义 / 旧 Record 依据降级（不因本阶段验收而关闭） |
| 保留 | `QA-P5-004`～`005`、`QA-P6-004` | Android bridge / installer·signing / 非正式 adapter → Phase 9 |

## 12. Phase 8 Exit Gate 自检

| Exit Gate 条件 | 结果 |
|---|---|
| Owner 指定 V6 模板正式资产化并入仓 | PASS |
| 正式产品路径不依赖本地开发路径 | PASS |
| 其他 17 个设备 Sheet 语义不变 | PASS（0 差异） |
| 离心泵 Sheet 27 列 / `TblPump` / 验证 / 保护结构契约保持 | PASS |
| Excel 类别枚举与软件正式枚举逐项一致 | PASS（10/10） |
| 「其他（请备注说明）」→「其他类别」，新增「不确定类别」 | PASS |
| 石化泵单级/多级不隐含吸入方式 | PASS |
| Excel 内不再存在可独立产出结果的第二套业务算法 | PASS |
| 数量：必填正整数 > 0，Excel 与软件双重校验 | PASS |
| 只填安装位置的行不被静默跳过 | PASS |
| 空白模板一次输出，无需逐 Sheet 配置容量 | PASS |
| 少量 / 100 / 1,000 / 10,000 行均无截断 | PASS |
| Reader 不读取旧计算结果作为业务输入 | PASS |
| Reader 数字保持十进制语义（`QA-EXCEL-001` 关闭） | PASS |
| 一次批量 → 一条 `batch_record` | PASS |
| 批量评价不为每行创建单台 Record | PASS |
| 单台 Qt 分析语义不变 | PASS |
| 输出为新 Workbook，不覆盖输入 | PASS |
| 其他设备 Sheet 不被删除/重排 | PASS |
| 「不确定类别」→「无法评价」，进入批次汇总 | PASS |
| Qt 与 Excel 用户可见结论一致（同一函数） | PASS |
| 系统异常不伪装成业务结论 | PASS |
| 最小 additive 持久化；单台 Record 语义不变 | PASS |
| 001 / 002 未改动，`record` 列契约不变 | PASS |
| 29 条 Approved Golden 零业务漂移 | PASS |
| Numeric Profile / 标准边界 / 公式 / 等级判断未改 | PASS |
| Phase 9 范围没有被提前实现 | PASS |
| Required CI 无新增未知 regression | PASS（§10.2） |
| 批次处理行级独立，一行失败不回滚其他行 | PASS |
| 系统级失败被明确报告（不伪装成业务结论） | PASS |
| 保留原顺序 / 原行号映射 | PASS |
| 六种正式结论（1/2/3级、未达标、不适用、无法评价）可区分 | PASS |
| `INVALID_INPUT` / `EXECUTION_ERROR` 不属于正式评价结论 | PASS |
| **数量按「数量」列加权**统计 | PASS |
| 数据行数 / 设备数量总计 / 完成正式评价数量三口径分开 | PASS |
| 输入错误按行统计，其数量不伪装成正式评价数量 | PASS |
| 不建逐行明细数据库表 | PASS |
| `batch_record` 承载模板身份 / 文件哈希 / 数量口径 / 版本引用 | PASS |
| 持久化时点：结果 Workbook 成功 + SHA-256 取得后才写 | PASS |
| 结果文件写失败不写「成功完成」记录；记录写失败明确告知用户 | PASS |
| Writer 默认名带时间戳，目标已存在不静默覆盖 | PASS |
| Writer 复用 V6 现有结果列，不新增结果字段体系 | PASS |
| 结果 Workbook 是正式逐行明细载体（原输入/数量/结论/等级/关键结果/说明） | PASS |
| 一级导航入口为「Excel导入」，不泄露内部 ID / JSON / Python 名称 | PASS |
| 输出空白模板为一次操作，不询问任何行数 | PASS |
| **29 条 Approved Golden 经 Excel Batch 路径零漂移**（门禁 20） | PASS |
| 架构契约测试纳入 gating（防止依赖方向违规再次逃逸） | PASS |

## 13. 状态

```text
Phase 8 implementation = EXECUTION_COMPLETE
READY_FOR_INDEPENDENT_ACCEPTANCE
```

**不合并 PR。不自宣 `PHASE_8_PASS`。不进入 Phase 9。**

## 14. Final Head

独立验收的**唯一对象**：本报告所在提交的 head（见 PR #16 的 head SHA）。

报告完成后**不得**再向该分支追加提交。如 Head 改变，必须重新声明新的 final Head、
重新执行必要测试，并等待该 Head 对应的 CI。

---

# Phase 8 R1 — Independent Acceptance blocker fixes + UI product cleanup

## R1.0 上一轮的验收结论（历史保留，不抹掉）

| 项 | 值 |
|---|---|
| 上一轮验收结论 | **`PHASE_8_BLOCKED`** |
| 被 BLOCKED 的 head | `8cb6eec1845cc26bed43e3dfea2dec1c5880729c` |
| 独立验收提出的 blocker | 4 项（见下表） |

四项 blocker **全部成立**，其中 B1/B2/B3/B4 都是真实缺陷（B3 与 B4 尤其严重：
一个改写了用户原始数据，一个把上一批的 provenance 伪造成本批的）。

| # | blocker | 独立验收实测 | 根因 |
|---|---|---|---|
| B1 | 结果 Workbook 未写出真实等级限值 | water / chemical 成功结果已有正式 `thresholds`，但 U/V/W 为空 | Writer 只消费 `calculation_trace.derived`，**从未消费 `PumpAnalysisResult.thresholds`** |
| B2 | `INVALID_INPUT` 污染批次统计 | 负流量 + 数量=7 → 计入已评价 7、input error=0、attention 空、输出「无法判定」 | `_evaluate_row` 把 `INVALID_INPUT` 当成有 `evaluation_status` 的正式评价 |
| B3 | Writer 改写原始输入精度 | 输入 `100.12345678901234567890123456789012345` → 结果文件 `100.1234567890124` | Writer 用 openpyxl **整体重写**工作簿，而 openpyxl 把数值读成 `float` |
| B4 | batch provenance 跨批次串用 | 批次 A 合法、批次 B 全非法，B 仍复用了 A 的 Canonical / Numeric 引用 | `self._first_result` 是 **service 实例状态**，跨调用残留 |

## R1.1 逐项处置与证据

### B1 — 结果 Workbook 写出真实等级限值

- 查清契约：`PumpAnalysisResult.thresholds` 的键为
  `1级能效效率限值（%）` / `2级能效效率限值（%）` / `3级能效效率限值（%）`，
  与 `calculation_trace.derived` 是**两个不同的来源**。
- 修复：新增 `THRESHOLD_COLUMNS` 映射，`U/V/W` **只取自正式 thresholds**；
  **不重算、不从 Excel 旧公式恢复**。
- 无正式阈值的状态（`OUT_OF_STANDARD_SCOPE` / `INSUFFICIENT_DATA` / 不确定类别）
  **不写** `U/V/W`，绝不伪造。
- Excel 显示保留 2 位小数（**仅 Presentation**；等级比较仍用完整精度，
  未改 Result 原始 Decimal / Record / Golden / Numeric Profile）。
- 证据：`tests/unit/test_phase8r1_blockers.py::B1ThresholdWritebackTests`
  （water / chemical 各覆盖成功等级案例；与正式 `evaluate()` 的 thresholds 逐项相等；
  重新打开结果 Workbook 后仍一致；无阈值状态不伪造）。

实测（修复后，重新打开结果文件读出）：

```text
water    r4  U=79.786165 V=77.786165 W=72.786165
chemical r5  U=81.247202 V=79.247202 W=72.247202
其他类别 r6  U=None      V=None      W=None        （不伪造）
```

### B2 — `INVALID_INPUT` 不属正式评价结论

- 修复：`INVALID_INPUT` 归为**输入错误**。数量本身合法时：
  计入 `total_quantity` 与 `input_error_quantity`；
  **不**计入 `evaluated_quantity`、**不**进入任何正式结论数量；
  `input_error_row_count +1`；必须出现在"需要关注"列表。
- 数量本身非法（空白 / 0 / 负数 / 小数）：同样按输入错误计，
  且**不虚构设备数量**（不进入 `total_quantity`）。
- 「不确定类别」**不是** `INVALID_INPUT`：仍是正式用户结论「无法评价」，
  数量进入 `conclusion_quantities` 与未评价计数。
- 「其他类别」沿用现有正式业务语义，未重新定义。
- 结果 Workbook 明确写「输入错误」+ 具体说明，**不**写「无法评价 / 无法判定」；
  `EXECUTION_ERROR` 继续单独显示「执行失败」。
- 证据：`B2InvalidInputTests`（负流量+数量 7、级数冲突+数量 7、非法数量、
  不确定类别 quantity>1、混合批次、执行失败单独区分）。

修复后实测：

```text
负流量 + 数量7 -> 结论=输入错误  input_error=True
                  total_qty=7  evaluated_qty=0  input_error_rows=1  issues=1
                  conclusion_quantities={}
混合批次(6 行) -> total_qty=30  evaluated_qty=27  input_error_rows=2
                  {2级:20, 1级:5, 无法评价:3, 不适用:2}
```

### B3 — 结果 Workbook = 原文件副本 + 只写结果区域

- 根因确认：openpyxl 读入数值即变 `float`，写回即降精度。
- 修复：Writer 改为**先逐字节复制原文件**（其他 17 个 Sheet、图片、验证、
  保护、样式、sharedStrings、以及**全部用户输入 cell 的原始 XML** 一律原样保留），
  **再只对「离心泵」Sheet 的 12 个授权结果列做 XML 级定点补丁**；
  数值用 `<v>`，文本用 `inlineStr`（因此不改动 sharedStrings，不影响其他单元格）。
- 用户输入列（企业/项目、设备名称、型号、数量、安装位置、类别、流量、扬程、
  转速、功率、吸入方式、级数、效率、附件/备注）**不会被重新序列化**。
- 原输入 Workbook 永不覆盖；目标已存在时显式报错。
- 证据：`B3InputPrecisionTests`（35 位精度保留；只有该 worksheet 部件变化；
  输入 cell 的 value / number_format / protection / 其他 Sheet 值不变；
  原文件哈希不变；目标已存在不静默覆盖）。

修复后实测：

```text
输入 G4  <c r="G4" s="226"><v>100.12345678901234567890123456789012345</v></c>
输出 G4  <c r="G4" s="226"><v>100.12345678901234567890123456789012345</v></c>   <- 原样
变化的 zip 部件：['xl/worksheets/sheet4.xml']                                    <- 仅此一个
```

### B4 — batch provenance 绝不跨批次串用

- 修复：**彻底移除实例级批次状态**。`summary` / `outcomes` / `provenance`
  全部改为 `evaluate_workbook` 内的局部对象；新增 `_BatchProvenance` 累积器，
  只记录**当前批次真正执行过正式评价**的 Result。
- 本批若在进入正式评价前全部失败 → references 保持为**空**
  （按现有 `batch_record` 结构采取最诚实的表示，**不伪造 Result**）。
  当前批次的客观信息（app version、模板身份/版本/哈希、standard_code、
  输入/输出哈希）仍照实写入。
- 证据：`B4ProvenanceIsolationTests`（同一 service 连续三批 A 合法 /
  B 全非法 / C 合法但组成不同；"全非法批次 references 必须为空"；
  以及"service 实例上不得存在批次作用域状态"的机械守卫）。

修复后实测（**同一 service 实例**连续三批）：

```text
批次1 (合法)   canonical='2026.09.26-t3-08-c2-142.33-v1' numeric='EQUIPEFFI_PUMP_DECIMAL50_V2'
批次2 (全非法) canonical=''                              numeric=''          <- 未串批
批次3 (合法)   canonical='2026.09.26-t3-08-c2-142.33-v1' numeric='EQUIPEFFI_PUMP_DECIMAL50_V2'
```

## R1.2 UI 四组 Owner 修改的实际落点

| 项 | 落点 | 实际改动 | 是否影响业务 |
|---|---|---|---|
| **UI01** | `presentation/qt/pages/analysis.py` | QGroupBox 标题「规定点参数（BEP）」→「**设备参数**」；`POINT_FIELDS` 标签改为 `流量 Q` / `扬程 H` / `转速 n` / `泵效率 η`；占位文案改为「请输入设备参数数值」 | **否**：内部字段名 `QBEP`/`HBEP`/`speed`/`efficiency` 与计算契约未改；Canonical / Golden / Application Contract 字段 identity 未改 |
| **UI02** | 同上 | 删除结果区的「判定说明」「为什么是这个结果」「所选标准」「标准依据」；保留 最终结论/等级、**关键计算参数**、**对应等级效率限值**（限值显示 2 位小数） | **否**：`explanation` / `references` / `provenance` 仍完整保存在 Result 与 Record；等级比较仍用完整精度 |
| **UI03** | `presentation/qt/pages/records.py` | 详情页**不再创建**「审计信息」折叠面板（保留一个不可见的内部占位控件以兼容既有内部引用） | **否**：Record 数据结构与历史数据未改；provenance / snapshot / hash / numeric profile / matched rule / canonical references 全部继续保存（有专门测试证明） |
| **UI04** | `presentation/qt/pages/settings.py` | 日志级别下拉显示中文（调试 / 信息 / 警告 / 错误 / 严重错误，按**严重程度递增**排序），内部保存值仍为正式枚举（`itemData`） | **否**：未迁移 settings schema；映射可稳定往返（有重启恢复测试）；未知级别回退显示原值而不是隐藏 |

## R1.3 本轮回归

```text
tests.unit.test_phase8r1_blockers           34   全通过（本轮新增 blocker/UI 回归）
tests.unit.test_phase8a_template_reader     33   全通过
tests.unit.test_phase8b_batch_evaluation    34   全通过
tests.unit.test_phase8b_batch_consistency   10   全通过（含 29 Approved Golden 回放）
tests.contract.test_architecture_boundaries 12   全通过
CI gating 模块列表（同 CI 形态）            406  OK / exit 0（约 349s）
全量 unittest                     1419 run / 1410 pass / 3 fail / 1 error / 3 skip
known-regression comparator       gate=PASS
```

既有失败仍是既有失败（3 项 V4 reader/writer + 1 项 release audit 错误），
**未更新 known baseline、未删除测试、未降低断言、未 skip 新 blocker**。

**本轮发现的性能问题（自行引入并修掉）**：XML 补丁最初是"每行一次全串正则搜索"，
在 10,000 行时退化为 O(n²)（78s → 408s）。已改为**单遍扫描 + 已编译正则缓存**，
10,000 行写回 **2.79s**（线性）。

## R1.4 本轮实际 GitHub CI（final Head）

```text
Windows Core
  [ 6] Compileall                                                          success
  [ 7] Architecture boundaries and metadata contract                       success
  [ 8] Application and core tests                                          success
  [ 9] Phase 2/3/4/5/6/7/8 settings, lifecycle, Stage D, Product Shell,
       analysis flow, Excel batch, R1 blockers, Qt offscreen (gating)       success
  [10] Full suite known-regression comparator (gating)                     success
  [12] Package and resource smoke                                          success
Pump Conformance
  [12] pump_chemical Stage D support + Phase 6 product shell (gating)      success
Whitespace check (gating)                                                  success
Full suite baseline (NON-GATING)                                           success
```

## R1.5 是否修改了受保护资产

| 资产 | 本轮是否修改 |
|---|---|
| Approved Golden（29 条） | **否** |
| Canonical（`resources/standards/pump.json`） | **否** |
| Numeric Profile | **否** |
| pump 公式 / boundary / grade | **否** |
| migration `001` / `002` | **否**（未触碰） |
| `batch_record` schema | **否**（本轮未新增迁移） |
| 正式 V6 模板资产 | **否**（SHA-256 未变） |
| 其他设备 Sheet 业务结构 | **否** |
| Presentation 文案（UI01～UI04） | 是（仅显示层） |
| Excel Reader / Writer 实现 | 是（B1/B3 修复） |
| 批量评价统计与 provenance | 是（B2/B4 修复） |

## R1.6 交付对象

| 项 | 值 |
|---|---|
| Repo | `https://github.com/adgo07/EquipEffi.git` |
| Base SHA | `79ea075967ace07aa9880369220d8bff9b53d9e8` |
| Branch | `phase8/gb19762-excel-batch` |
| PR | **#16** — https://github.com/adgo07/EquipEffi/pull/16（`open`, `merged=false`） |
| 上一轮 BLOCKED head | `8cb6eec1845cc26bed43e3dfea2dec1c5880729c` |
| **R1 final Head** | `eb8b9fb06918aac8f86f88be92896085aa508586`（R1 修复提交；其后的提交仅为报告与治理文档） |
| Base → R1 final Head | 56 files, +6116 / −248 |
| `8cb6eec` → R1 final Head（本轮 R1 diff） | 11 files, +1236 / −146 |

### `8cb6eec` → R1 final Head 变更文件

```text
.github/workflows/windows-core.yml
src/equipeffi/application/services/pump_batch_evaluation_service.py
src/equipeffi/infrastructure/excel/pump_result_writer.py
src/equipeffi/presentation/qt/pages/analysis.py
src/equipeffi/presentation/qt/pages/records.py
src/equipeffi/presentation/qt/pages/settings.py
tests/unit/test_phase3_qt_unified.py
tests/unit/test_phase3_r1_blockers.py
tests/unit/test_phase6_product_shell.py
tests/unit/test_phase8b_batch_consistency.py
tests/unit/test_phase8r1_blockers.py
```

## R1.7 状态

```text
Phase 8 R1 implementation = EXECUTION_COMPLETE
READY_FOR_REACCEPTANCE
```

**不自宣 `PHASE_8_PASS`。不合并 PR。不进入 Phase 9。**

R1 final Head **= 下一轮独立复验唯一对象**。

R1 final Head 为**本轮 R1 修复提交**：

```text
R1 final Head = eb8b9fb06918aac8f86f88be92896085aa508586
```

该提交包含全部四项 blocker 修复、UI01～UI04 与 R1 blocker 回归测试。
其**之后**的提交只包含 `PHASE8_EXECUTION_REPORT.md` 与治理文档同步
（`QA_BACKLOG.md` / `TASK_STATE.md` / `UI_CURRENT_STATE_AUDIT.md`），
**不包含任何代码改动**——因此对这四项目的独立复验对象是 `eb8b9fb06918`。

PR #16 的 head SHA 也是独立复验的有效对象（它等于上述修复提交 + 文档提交）。

形成本报告后**不再追加 commit**；如 Head 改变，将重新声明 final Head、
重新执行受影响测试，并等待该 Head 的 CI。

---

# Phase 8 R1W — 复审清单外审计发现的 Writer 阻断

## R1W.0 复审结论（历史保留，不抹掉）

| 项 | 值 |
|---|---|
| 上一轮 R1 的验收结论 | **`PHASE_8_BLOCKED`**（第二次） |
| 被 blocked 的 head | `348a1994352e9e16d841a0589b0af2416a83b0df` |
| 复审已确认通过的部分 | 原四项 blocker（B1～B4）与 UI01～UI04 **均已验证通过** |
| 新阻断 | 清单外审计发现 **2 个 Writer 阻断**（同一根因） |

| # | blocker | 复审实测 | 根因 |
|---|---|---|---|
| 5 | 结果**静默漏写** | `<row ht="42" customHeight="1" s="184" r="4">` 时 Reader 正常读、Application 正常算，但结果整行未写出，**仍保存"成功"批次记录** | Writer 的行定位正则假设 `r` 是 `<row>` 的**第一个**属性 |
| 6 | 产生**重复单元格** | 既有 `<c s="234" r="U4">`（`s` 在 `r` 之前）时未识别原单元格，又插入一个 `U4`，输出出现**重复坐标** | Writer 的单元格匹配正则假设 `r` 紧跟 `<c ` |

**共同根因**：OOXML **不保证**属性顺序、命名空间前缀或自闭合形式，
而首版 Writer 用「属性顺序假设」的正则做元素匹配。两个阻断都是该假设的直接后果。

## R1W.1 处置

- 元素解析改为**顺序无关扫描器**：

```text
_find_tag_end   正确定位标签结束（跳过属性值内的引号与 XML 实体）
_parse_attrs    把属性解析成字典（去掉命名空间前缀）
_scan_cells     扫描行内所有 <c>（自闭合与带内容都识别）
_scan_rows      扫描 sheetData 内所有 <row>（r 在任意位置都识别）
```

- 按 **`r` 属性（坐标）**匹配既有单元格并**就地替换**，保留原有样式 `s`
  → 不再产生重复坐标；缺失的结果 cell 按**列序**插入，不破坏既有列顺序。
- **写回自校验**：补丁后重新扫描该行，要求每个目标坐标**恰好出现 1 次**；
  不满足即抛 `ResultWorkbookWriteError`。
- **绝不静默漏写**：任何结果行在 Sheet 中定位不到 → 抛
  `ResultWorkbookWriteError`，批次整体失败、**不保存** `batch_record`，
  而不是"部分写回 + 成功记录"。

## R1W.2 复现与修复证据

```text
复现 1（被 blocked 的 head）
  row4 标签 : <row ht="42" customHeight="1" s="184" r="4">
  结果       : X4 = None      <- 整行未写出，仍保存"成功"批次记录
修复后
  X4 = '2级'  U4 = 79.786165  <- 正常写回

复现 2（被 blocked 的 head）
  U4 标签    : <c s="234" r="U4" t="n">
  输出次数   : U4 出现 2 次    <- 重复坐标
修复后
  输出次数   : U4 出现 1 次，且保留原样式 s="234"
  输出片段   : <c r="U4" s="234"><v>79.786165</v></c>

硬失败验证
  传入无法定位的行 99999 -> ResultWorkbookWriteError:
  「结果写回失败：无法在「离心泵」Sheet 中定位以下数据行 [99999]（共 1 行）；
    拒绝保存部分写回的结果工作簿」
```

## R1W.3 本轮回归

```text
tests.unit.test_phase8r1w_writer_structure   9   全通过（本轮新增；在被 blocked 的 head 上失败）
tests.unit.test_phase8r1_blockers           34   全通过
Phase 8 全部（8A + 8B + 一致性 + R1 + R1W）  111  全通过
tests.contract.test_architecture_boundaries  12   全通过
CI gating 模块列表（同 CI 形态）             415  OK / exit 0（约 458s）
全量 unittest                   1428 run / 1421 pass / 3 fail / 1 error / 3 skip
known-regression comparator      gate=PASS
```

10,000 行批量仍无读取截断、无静默丢行（写回包含自校验）。
既有失败仍是既有失败（3 项 V4 + 1 项 release audit），
**未更新 known baseline、未删测试、未降断言**。

## R1W.4 QA 变动

| 动作 | 条目 | 说明 |
|---|---|---|
| **新增并关闭** | `QA-P8-005` | 结果 Writer 行定位依赖属性顺序 → 静默漏写。已改顺序无关扫描 + 定位失败即硬失败 |
| **新增并关闭** | `QA-P8-006` | 结果 Writer 单元格匹配依赖属性顺序 → 重复坐标。已改按坐标匹配 + 写回自校验 |

**教训（已落到实现约定）**：OOXML 的属性顺序、命名空间前缀、自闭合形式
都**不是**契约；解析必须顺序无关，且"没写成"必须是**硬失败**而不是静默成功。

## R1W.5 交付对象

| 项 | 值 |
|---|---|
| Repo | `https://github.com/adgo07/EquipEffi.git` |
| Base SHA | `79ea075967ace07aa9880369220d8bff9b53d9e8` |
| Branch | `phase8/gb19762-excel-batch` |
| PR | **#16** — https://github.com/adgo07/EquipEffi/pull/16（`open`, `merged=false`） |
| 第一次 BLOCKED head | `8cb6eec1845cc26bed43e3dfea2dec1c5880729c`（四项 blocker） |
| 第二次 BLOCKED head | `348a1994352e9e16d841a0589b0af2416a83b0df`（两个 Writer 阻断） |
| **R1W 修复提交** | `eef41f54436f01aa7db4f9b2e9f4bfa4c7bb5f60`（3 files, +540 / −43） |

### `348a199` → R1W 修复提交 变更文件

```text
.github/workflows/windows-core.yml
src/equipeffi/infrastructure/excel/pump_result_writer.py
tests/unit/test_phase8r1w_writer_structure.py
```

## R1W.6 是否修改了受保护资产

| 资产 | 本轮是否修改 |
|---|---|
| Approved Golden（29 条） | **否** |
| Canonical / Numeric Profile | **否** |
| pump 公式 / boundary / grade | **否** |
| migration `001` / `002` / `batch_record` schema | **否**（本轮未新增迁移） |
| 正式 V6 模板资产 | **否**（SHA-256 未变） |
| 其他设备 Sheet 业务结构 | **否** |
| 结果 Writer 实现 | 是（R1W 修复） |

## R1W.7 状态

```text
Phase 8 R1 implementation = EXECUTION_COMPLETE
READY_FOR_REACCEPTANCE
```

**不自宣 `PHASE_8_PASS`。不合并 PR。不进入 Phase 9。**

R1W 修复提交 `eef41f54436f01aa7db4f9b2e9f4bfa4c7bb5f60` 与本报告所在 head
均为有效复验对象；其后的提交只包含本报告与治理文档同步，**不含代码改动**。
形成本报告后**不再追加 commit**。

---

# Phase 8 R2 — 命名空间前缀敏感的 OOXML 扫描器（第三次复审 blocker）

> 本节**只追加**，不改写上文任何历史结论。R1 / R1W 两轮的结论、blocker 与
> 状态原样保留在上面。

## R2.0 前两次尝试为什么没有真正关闭这个 blocker（历史保留，不抹掉）

| 轮次 | 被 BLOCKED 的 head | 该轮宣称修好的东西 | 为什么**没有**关闭本 blocker |
|---|---|---|---|
| **第一次**（R1） | `8cb6eec1845cc26bed43e3dfea2dec1c5880729c` | B1～B4 四项：U/V/W 取自正式 `thresholds`、`INVALID_INPUT` 不污染统计、结果文件=原文件副本、provenance 不跨批次串用 | 该轮修的是**业务取值与持久化语义**，完全没有触及元素识别方式；扫描器仍按**字符串前缀**匹配 |
| **第二次**（R1W） | `348a1994352e9e16d841a0589b0af2416a83b0df` | "两个新 Writer 阻断"（结果静默漏写 / 产生重复坐标），并明确其根因是**属性顺序假设** | 只把"属性顺序"这一**载体变体**做对了：改成顺序无关扫描器（`_find_tag_end` + `_parse_attrs`）。但元素**身份判定方式**没变——仍是 `find("<c")`、`find("<row")`、`rfind("</row>")` 这类**字面字符串**匹配，因此**命名空间前缀**这一同类载体变体原封不动地留了下来 |

第二次尝试的关键失误在**测试**：它写了"前缀测试"，但夹具是

```python
lambda xml: xml.replace('<c r="U4"', '<c r="U4"', 1)   # 空操作（no-op）
```

`xml.replace(a, a)` 是**恒等变换**，从来没有真正产生过 `<x:c>` 输入，
断言 `r="U4"` 只出现一次在**无前缀**输入上当然成立。**一个空操作的夹具
让一个假测试通过了**——这正是本轮把"夹具必须机械自证"写成硬纪律的原因。

**共同教训（已落到本轮的实现与测试约定）**：
OOXML 的**属性顺序**、**命名空间前缀**、**自闭合形式**都不是契约；
"解析器看不见某个元素"必须是**硬失败**，而不是静默补一个出来。

## R2.1 根因

> **namespace prefix-sensitive raw OOXML scanner（命名空间前缀敏感的原生
> OOXML 扫描器）**

`f2518a9` 的 `src/equipeffi/infrastructure/excel/pump_result_writer.py`
用字面字符串识别元素（静态证据，行号即 `f2518a9` 的行号）：

```text
329: start = row_xml.find("<c", index)                  # 只认无前缀 <c
333: if after and (after.isalnum() or after in "_:.-"): # 把 <x:c 当成 <cols 误匹配**主动跳过**
343: close = row_xml.find("</c>", tag_end)              # 只认无前缀 </c>
359: start = xml.find("<row", index)                    # 只认无前缀 <row
363: if after and (after.isalnum() or after in "_:.-"): # 同样跳过 <x:row
454: insertion = row_xml.rfind("</row>")               # 只认无前缀 </row>
```

合法 OOXML **允许任意命名空间前缀**。于是：

```text
<x:c r="U4">      -> 第 333 行判定为"前缀误匹配" -> 完全不可见
<ss:c r="U4"/>    -> 同上
<x:row r="4">     -> 第 359 行找不到 <row -> 整行不可见
</x:row>          -> 第 454 行 rfind("</row>") 找不到
```

后果：Writer 以为 `U4` 不存在，追加一个**无前缀**的 `<c r="U4">`，
输出工作簿出现**重复坐标**；若整张工作表都是前缀形式，则连数据行都定位不到。

**机械复现（在 `f2518a9` 的扫描器行为上，用真实前缀化工作表）**：

```text
输入 row4 : <x:row r="4" ht="42" customHeight="1" s="184"><x:c r="A4" ...
OLD _scan_cells found cells : 0            <- 整行 27 个单元格一个都认不出
OLD recognises U4           : False
OLD _scan_rows finds <x:row r="4"> : False  <- 整行定位失败
```

## R2.2 修复

### 1) QName / local-name 感知的元素身份（取代 `find("<c")`）

```text
_iter_tags         逐标记产出 (起点, 终点, 限定名)，跳过注释 / CDATA / 处理指令
_element_name      从 <x:c r="U4"/> / </x:c> 取**限定名**（x:c）
_local_name        限定名 -> 局部名（x:c -> c）
_element_extent    按**嵌套深度**配对开/闭标记，返回元素真实结束位置
_close_tag         该元素对应的**精确**结束标记（x:c -> </x:c>）
_scan_cells        仅 local-name == "c" 才是单元格；结束标记必须匹配**实际限定名**
_scan_rows         仅 local-name == "row" 才是行；同上
```

因此以下四者被认定为**同一个** SpreadsheetML 单元格：

```text
<c r="U4">   <x:c r="U4">   <ss:c r="U4">   <p1:c r="U4">
```

`<cols>` / `<col>` / `<customFilter>` / `<cell>` / `<cfRule>` 等
local-name 不是 `c`/`row` 的元素**永不**误判（由 `test_H3` 机械守卫）。

`_element_extent` 是必需的：单元格可以**含子元素**
（`<c><f>…</f><v>…</v></c>`、`<c t="inlineStr"><is><t>…</t></is></c>`），
简单找第一个 `</c>` 会停在子元素的结束处、把外层单元格区间**截断**。

### 2) 行扫描同样修复（同一根因，允许且已做）

`row_xml.rfind("</row>")` 改为按该行元素**实际限定名**定位
（`</x:row>` 对 `<x:row>`）；自闭合行 `<x:row r="4"/>` 会先显式展开成
开/闭标记对再插入。

### 3) 目标坐标写语义（§四）

```text
已有 0 个 -> 按既有逻辑插入 1 个（按列序，继承该行前缀与样式）
已有 1 个 -> **就地更新**该单元格（带任何合法前缀都能识别；保留原样式与原有前缀）
已有 >1 个 -> 输入本身已歧义 -> **fail closed**（不猜哪个才是真的）
```

### 4) 重复坐标 fail-closed 后置条件（§三）

补丁完成、**写结果文件之前**，对**整张工作表**重新扫描
（不只 U/V/W），统计 `坐标 -> 出现次数`：

```text
任何非空坐标出现多于一次
    -> ResultWorkbookWriteError
    -> 不产出任何结果工作簿
    -> 不保存"成功"的 batch_record
```

同时新增**良构性**后置条件 `_assert_well_formed`（补丁是原生字符串操作，
因此用 XML 解析器独立复核）。并且 `write()` 改为
**"先全部算完、再落盘"**：后置条件在目标文件创建之前完成，失败时磁盘上
**不会**留下半成品结果文件。

### 5) 结果文件仍必须"打得开"：主命名空间归一

修好识别之后立刻暴露了第二层问题：本仓测试所用 `openpyxl` 以及其它现有
OOXML 读取器**只按字面无前缀标签**匹配 `c` / `v` / `row`，对
`<x:c><x:v>…</x:v></x:c>` 会**静默丢掉单元格值**（实测：`U4` 读成 `None`，
而 `B4` 等无前缀格正常）。输入是前缀写法时，若结果原样保留前缀，
用户用 Excel / 其它工具打开就会"结果消失"。

因此 Writer 在产出前把**主命名空间**的元素统一写回**默认命名空间**形式：

```text
<x:c   -> <c        </x:row> -> </row>
xmlns:x="…/main"    -> xmlns="…/main"      （无默认声明时改写）
                    -> 删除（已有默认声明时，避免第二个 xmlns 属性）
```

只改这两件事：元素**限定名上的前缀**与**该前缀自己的声明**。属性、属性顺序、
文本、其它命名空间（`r:` / `mc:` / `x14ac:` 等）以及 `<sheetData>` 一类结构
逐字节保留；最终整张工作表由 `_assert_well_formed` 机械复核为良构。
**扫描识别**本身始终是前缀无关的（先行完成），归一只是**输出**的可读性收口。

## R2.3 测试：真实前缀化 OOXML 夹具（§五）

上一轮的"前缀测试"因空操作而无效，**本轮禁止**任何未经验证的替换。
每个前缀化夹具都走同一条流水线，并**在调用 Writer 之前**自证：

```text
1. 复制/创建真实 xlsx（V6 模板 + 用户输入）
2. 打开 ZIP 内真实的 worksheet XML
3. **结构化**改写为合法命名空间前缀 SpreadsheetML（XML 解析器改写 +
   注册 xmlns:<prefix> 声明，而不是碰运气的字符串替换）
4. 写回 ZIP
5. assert_prefixed()：机械断言 <x:c 存在、U4 **真的是**前缀化单元格、
   没有残留无前缀 <c>、<x:row 存在
6. 只有通过第 5 步才调用 Writer
```

`assert_prefixed(..., fully_prefixed=False)` 专供**故意**混用前缀/无前缀表示的
夹具（§六 F / G）——那种夹具本来就应当同时含两种写法。

### 回归用例 A～H 与端到端

| 用例 | 内容 | 断言 |
|---|---|---|
| A | 无前缀 `<c r="U4">…</c>` | U4 == 1 |
| B | 前缀 `x`：`<x:c r="U4">…</x:c>` | U4 == 1 **且值 == 当前正式 `thresholds`** |
| C | 非 `x` 前缀：`<ss:c r="U4">…</ss:c>`（另有 `p1`） | U4 == 1 |
| D | 自闭合 `<x:c r="U4"/>` | U4 == 1（夹具显式断言 U4 确为自闭合） |
| E | 前缀化行 `<x:row r="4"><x:c r="U4">…</x:c></x:row>` | 整行结果列各恰好 1 次 |
| F | 同一 worksheet 混用 `<c …>` 与 `<x:c …>`（不同坐标）；补充：不同行用 `x:` 与 `ss:` | 各坐标恰好 1 次 |
| G | 输入**已有**重复坐标（`<c r="U4">` 与 `<x:c r="U4">` 并存） | **fail closed**：抛错、无结果文件、无 `batch_record` |
| H | 整表不变式：扫描**每个**带 `r` 的单元格 | 全部坐标唯一（另有正则独立复算交叉验证） |

补充用例：`G2`（直接调 Writer 也 fail closed 且不留文件）、
`G3`（重复坐标在**非首行** U5 时同样 fail closed）、
`H2`（后置条件门禁**独立**生效：人为注入一个扫描器漏掉的重复坐标，
`_assert_unique_references` 必须拒绝）、
`H3`（`<cols>`/`<col>`/`<customFilter>`/`<cell>`/`<cfRule>` 永不被当成单元格）、
`test_prefixed_and_plain_inputs_agree_exactly`（前缀化与普通输入的结论、
`evaluation_status`、`grade`、`thresholds`、`summary.as_dict()` 与结果列**逐项相同**）。

### §七 真实工作簿级端到端（`test_prefixed_end_to_end_reader_batch_writer_reopen`）

```text
合法输入工作簿 -> 结构化改写为 <x:row>/<x:c>（并自证）-> Reader -> 批量评价
   -> Writer -> 解压结果工作簿 -> 检查 worksheet XML
```

机械证明链：

```text
1. U4 在结果工作簿中恰好出现 1 次
2. U4 的值 == 正式 Result.thresholds 的 1 级限值（与单台 Application 结果同源对照）
3. 结果工作簿可正常重新打开（openpyxl 读回 U4/X4/D4，且二次读取一致）
4. 批次统计正确（data_row_count=1 / total_quantity=3 / evaluated_quantity=3 /
   conclusion_quantities 合计 3 / input_error_rows=0 / execution_error_rows=0）
5. batch_record 仅在 Writer 成功后保存（=1 条，result_workbook 指向结果文件，
   total_quantity=3，result_workbook_sha256 非空）
6. 整表坐标唯一
```

## R2.4 本轮实际本地验证

```text
tests/unit/test_phase8r2_prefixed_writer.py        17 passed / 51 subtests   （本轮新增）
tests/unit/test_phase8r1w_writer_structure.py       9 passed / 39 subtests   （前缀测试已换成真夹具）
tests/unit/test_phase8r1_blockers.py               34 passed / 148 subtests
tests/contract（architecture boundaries 等）       113 passed / 4841 subtests
python -m compileall -q src tools tests            exit 0
本仓 CI gating 模块清单（Phase 2–8 全量）          116 passed / 382 subtests
全量 pytest tests                                  1551 passed / 3 skipped / 7002 subtests
                                                   4 failed（既有失败，见下）

最终字节上的一次合并复验（本轮交付的 3 个测试 + 全部受影响模块 + contract）：
pytest tests/unit/test_phase8r2_prefixed_writer.py
       tests/unit/test_phase8r1w_writer_structure.py
       tests/unit/test_phase8r1_blockers.py
       tests/unit/test_phase8b_batch_evaluation.py
       tests/unit/test_phase8b_batch_consistency.py
       tests/unit/test_phase8a_template_reader.py
       tests/contract
    -> 250 passed / 5251 subtests passed / exit 0   （约 1032s）
```

**既有失败与基线逐项一致**（同一组 4 项在未应用本轮改动的 `f2518a9`
工作区上**同样失败**，已实测）：

```text
tests/unit/test_release_audit.py::...test_source_and_bundled_wheel_pass_release_audit
tests/unit/test_v4_reader.py::...test_copied_v4_row_is_read_and_evaluated
tests/unit/test_v4_writer.py::...test_end_to_end_v4_1500_rows_read_evaluate_write_and_reopen
tests/unit/test_v4_writer.py::...test_writer_creates_new_workbook_with_locked_results
```

**未更新 known baseline、未删除任何测试、未添加 skip/xfail/deselect、
未放宽任何断言。**

## R2.5 本轮明确点名的三个测试

| # | 测试 | 覆盖 |
|---|---|---|
| 1 | `tests/unit/test_phase8r2_prefixed_writer.py::PrefixAgnosticCellTests::test_B_prefix_x_cell_is_recognised_and_updated_in_place` | **前缀化 `U4` 回归**：真实 `<x:c r="U4">` 输入下 U4 恰好 1 次，且值 == 当前正式 `thresholds` |
| 2 | `tests/unit/test_phase8r2_prefixed_writer.py::DuplicateCoordinateFailClosedTests::test_G_duplicate_input_fails_closed_without_result_workbook` | **重复输入 fail-closed**：输入已含 `U4` 两处时硬失败，无结果文件、无 `batch_record` |
| 3 | `tests/unit/test_phase8r2_prefixed_writer.py::WholeSheetUniquenessInvariantTests::test_H_every_coordinate_in_the_written_sheet_is_unique` | **整表坐标唯一性不变式**：写回后扫描整张工作表（>1000 个坐标）断言全部唯一，并用独立正则交叉复算 |

## R2.6 交付对象

| 项 | 值 |
|---|---|
| Repo | `https://github.com/adgo07/EquipEffi.git` |
| Base SHA | `79ea075967ace07aa9880369220d8bff9b53d9e8` |
| Branch | `phase8/gb19762-excel-batch` |
| PR | **#16** — https://github.com/adgo07/EquipEffi/pull/16（`open`, `merged=false`） |
| 第一次 BLOCKED head | `8cb6eec1845cc26bed43e3dfea2dec1c5880729c`（B1～B4） |
| 第二次 BLOCKED head | `348a1994352e9e16d841a0589b0af2416a83b0df`（两个 Writer 阻断） |
| R1W 修复提交 | `eef41f54436f01aa7db4f9b2e9f4bfa4c7bb5f60` |
| **第三次 BLOCKED head（本轮起点）** | `f2518a93179f51fd5339d8bfcf8cbbe02fa67e28` |
| **R2 修复（本地工作区，未提交）** | 本报告所述改动，见下 |

### `f2518a9… → R2` 实际 diff

```text
 .github/workflows/windows-core.yml                        |   1 +
 src/equipeffi/infrastructure/excel/pump_result_writer.py  | 669 ++++++++++----
 tests/unit/test_phase8r1w_writer_structure.py             |  77 ++-
 3 files changed, 640 insertions(+), 107 deletions(-)

 新增（untracked）
 tests/unit/test_phase8r2_prefixed_writer.py               | 599 行（17 个测试）
```

- `.github/workflows/windows-core.yml`：CI gating 模块清单加入
  `tests.unit.test_phase8r2_prefixed_writer`（否则新回归在 CI 中不执行）。
- `src/equipeffi/infrastructure/excel/pump_result_writer.py`：本轮修复本体。
- `tests/unit/test_phase8r1w_writer_structure.py`：
  `test_worksheet_prefix_is_tolerated` 的**空操作夹具**替换为真实结构化
  前缀夹具（并新增 `_prefix_worksheet_in_zip` / `_sheet_path_of` 辅助）。
  **未删除该测试，未放宽断言**——只是让夹具真的产生 `<x:c>` 输入。
- `tests/unit/test_phase8r2_prefixed_writer.py`：本轮新增回归（A～H + 端到端）。

## R2.7 是否修改了受保护资产

| 资产 | 本轮是否修改 |
|---|---|
| pump 公式 / boundary / grade | **否** |
| Approved Golden（29 条） | **否** |
| Canonical / Numeric Profile | **否** |
| 正式 `thresholds` 业务值 | **否**（U/V/W 仍只取自正式 `Result.thresholds`） |
| 批次统计语义 | **否** |
| Qt UI | **否** |
| V6 模板业务设计与模板资产 | **否**（模板 SHA-256 未变；夹具不改模板文件本体，只改测试临时副本） |
| migration / `batch_record` schema | **否**（未新增迁移） |
| 其他 Sheet 逻辑 | **否** |
| Phase 9 相关内容 | **否** |
| Excel Writer / Reader 基础设施 | 是（仅本缺陷所需范围） |
| 既有 Excel 相关测试文件 | 是（仅 `test_phase8r1w_writer_structure.py` 的前缀测试夹具，及新增 R2 文件） |

本任务不涉及中央公共 Contract（无 Frozen Contract 语义变化）；
与 `platform-lock.json` 锁定的 Architecture 2.1 / Numeric Contract v1 无冲突。

## R2.8 状态

```text
Phase 8 R2 implementation = EXECUTION_COMPLETE
READY_FOR_REACCEPTANCE
```

**不自宣 `PHASE_8_PASS`。不合并 PR。不进入 Phase 9。**
本轮**未提交、未推送**：工作区改动留待 Owner 复核、冻结并自行提交/推送/更新 PR#16。
形成本报告后**不再追加 commit**。
