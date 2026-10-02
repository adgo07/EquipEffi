# EquipEffi 项目交接说明

> **当前唯一权威路线：EquipEffi V2.3；状态 `PHASE_1_PASS`；下一状态 `PHASE_2_READY`；`automatic_continuation = DISABLED`。**
>
> **当前 Windows V1 产品目标（2026-10-02 产品决定）：首个正式版完整支持 `GB 19762—2025《离心泵能效限定值及能效等级》`，覆盖 `pump_water` 与 `pump_chemical`；`transformer` 本轮暂缓、资产保留。** 详见 [V1_SCOPE.md](V1_SCOPE.md) 与 [REFERENCE_STANDARD_ROADMAP.md](REFERENCE_STANDARD_ROADMAP.md)。
>
> **当前任务：`V2.3-PRODUCT-SCOPE-CLEANUP`（产品范围收口 / V2.3 同步修订 / 治理减负 / 历史 CI 收口），分支 `governance/v2.3-product-scope-cleanup`，基线 `origin/master@f5c34277d35c9a7a1bcfbe4331297de2ad1fcf4f`。本任务不是 Phase 2 执行，不开发新功能，不修改 Pump 业务算法，不修改中央 Contract。完成后停止等待独立验收，不自行合并 PR。**
>
> V2.2 保留为 V2.3 的继承基线；旧 v7–v15、T04.xx、旧 HANDOFF 和编号执行清单均为 `HISTORICAL / NOT AUTHORITATIVE FOR NEXT TASK`。它们保留事实，不再拥有自动任务调度权。请先读取 [ROADMAP.md](ROADMAP.md)、[TASK_STATE.md](TASK_STATE.md)、[AGENTS.md](AGENTS.md)、[BASELINE.md](BASELINE.md)、[ASSET_AUDIT.md](ASSET_AUDIT.md)、[QA_BACKLOG.md](QA_BACKLOG.md)、[V1_SCOPE.md](V1_SCOPE.md)、[REFERENCE_STANDARD_ROADMAP.md](REFERENCE_STANDARD_ROADMAP.md)、[STANDARD_ISSUES_REGISTER.md](STANDARD_ISSUES_REGISTER.md)、[PLATFORM_BASELINE.md](PLATFORM_BASELINE.md) 和 `platform-lock.json`。
>
> R01–R07 技术独立复验固定 SHA 为 `3101e05abd7f33262a9449c390d61ec00008fb75`；P1-SR01 Solution/Product Review 通过的固定基线为 `38bdfc28e078fee067743d30055fb39337881c7c`。FIXED_SHA_INDEPENDENT_REVIEW、GOLDEN_CASE_NAMED_HUMAN_APPROVAL 和 SOLUTION_PRODUCT_REVIEW 均为 RESOLVED。王玮于 2026-09-28T11:03:04+08:00 批准全部 18 条 pump_water Golden 0.4。Golden 0.1 七例、原始 0.3 的 26 条记录及 3 条 replacement candidates 不变，8 条 pump_chemical 候选**仍未获 V1 Golden 批准**。Phase 1 Exit Gate 已满足；PR #1～#8 均已合并。**Numeric Contract v1 adoption（PR #5，合并于 `66835d2ae2e0a8eaee50260f43ee0c52b4858d85`）的独立验收记录仓库内未找到，状态为 `INDEPENDENT_ACCEPTANCE_RECORD_PENDING`——合并事实不等同于独立验收证据，不得报告为验收 PASS。** Phase 2 READY 不代表自动开始，必须由用户明确授权。

## 当前权威状态

| 项目 | 当前事实 |
|---|---|
| 当前路线 | `EquipEffi V2.3` |
| 继承基线 | `EquipEffi V2.2`；未被 V2.3 明确修改的原则与阶段结构继续有效 |
| Windows V1 产品目标 | 完整支持 `GB 19762—2025`，覆盖 `pump_water` + `pump_chemical`；`transformer` 暂缓（`POST_V1`，资产保留） |
| 当前阶段 | `Phase 1 complete / Phase 2 ready` |
| 状态 | `PHASE_1_PASS` |
| 下一状态 | `PHASE_2_READY / NOT_STARTED` |
| 唯一下一步 | 完成本治理任务并停止，等待独立验收；Phase 2 只有用户明确授权后才能开始；automatic continuation 继续 `DISABLED` |
| 业务样板 | `pump_water`（Phase 1 业务真相样板）；`pump_chemical` 已进入 V1 范围但标准开发成熟度仅 `READY_FOR_IMPLEMENTATION` |
| 本轮边界 | 仅范围/治理 Markdown 与 CI 触发配置；不修改生产代码、Schema、Golden、Canonical、V1 范围以外的决策、泵算法、数据库、Excel 实现、UI 实现或 Phase 2 功能 |

### 三个状态维度不得互相冒充

| 维度 | 含义 | 定义来源 |
|---|---|---|
| `scope_status` | 产品范围决策 | 本仓产品决策（`V1_SCOPE.md`） |
| `support_status` | 当前发布能力 | 本仓发布门禁 |
| 标准开发成熟度 | Stage A→D 阶段成熟度 | 中央 `STANDARD_DEVELOPMENT_GUIDE_V0.1.md` §19 |

**`pump_chemical`：`scope_status = IN_V1` 且 `standard maturity = READY_FOR_IMPLEMENTATION`，但 `support_status = NOT_IN_RELEASE_SCOPE`** —— 在其 Golden 具名批准与 Stage D 独立验收通过前不得写为 `SUPPORTED`。

R01–R06 清单见 PUMP_V2_R01_R06_COMMIT_MANIFEST.md，R07 清单见 PUMP_V2_R07_COMMIT_MANIFEST.md，P1-G04 来源与批准清单见 PUMP_V2_G04_APPROVAL_MANIFEST.md。Golden 0.1 七例保持历史冻结，原始 0.3 的 26 条候选保持 DRAFT/PENDING，3 条 replacement candidates 未改；18 条正式 pump_water Golden 0.4 均为 APPROVED，8 条 pump_chemical technical-only 候选未获 V1 Golden 批准。精确表3边界由 generated boundary test 负责，首批人工 Golden 不要求重复穷举端点。标准 PDF 不入仓库，validator 支持 external-evidence-root。Phase 1 Exit Gate 已满足；三个评审门禁均为 RESOLVED。

## 当前已知技术债

| QA / 项 | 位置 | 表面 | 当前状态 | 关闭时点 |
|---|---|---|---|---|
| `QA-P0-001` | `test_v4_reader.py::test_copied_v4_row_is_read_and_evaluated` | `NOT_SHIPPED` | OPEN（既有失败） | 发布前必须关闭或有明确不发布决策 |
| `QA-P0-002` | `test_v4_writer.py` 两个写回测试 | `NOT_SHIPPED` | OPEN（既有失败） | 同上 |
| `QA-P1-003` | `test_release_audit.py` 缺 `wheel_pmsm_status` | `DEV_ONLY` | OPEN（既有错误） | Phase 2/8 |
| `QA-P1-006` | 标准包 `active` ≠ 业务已验收 | `V1_RUNTIME` | OPEN | 逐 pack 冻结 Canonical/source |
| `QA-P1-007` | `JsonStandardRepository.get_pack` 重复解析 | `V1_RUNTIME` | OPEN | Phase 2（先登记实测，不预先优化） |
| `QA-EXCEL-001` | `ooxml_reader.py:_parse_number` Decimal → float | `NOT_SHIPPED` | OPEN；authoritative path impact 尚待验证 | **Phase 8 前必须关闭** |
| `EQP-STD-GB19762-001` | `as_of` 默认口径（关联 `QA-AUD-031`） | `V1_RUNTIME` | `PROVISIONAL` | 产品决策收口 |
| `EQP-UI-001`～`005` | 桌面 UI 审计问题 | `PROTOTYPE` | OPEN，无 P0 | 正式 UI 阶段 |

完整登记见 [QA_BACKLOG.md](QA_BACKLOG.md) 与 [STANDARD_ISSUES_REGISTER.md](STANDARD_ISSUES_REGISTER.md)。

## 当前 full-suite baseline

```text
环境：Windows；CPython 3.12.14 x64（项目 .venv）；PYTHONPATH=src
命令：.venv\Scripts\python.exe -m unittest discover -s tests -t .
结果：945 run / 938 pass / 3 failures / 1 error / 3 skipped

既有 4 项失败（NOT_SHIPPED V4 读写 + DEV_ONLY 发布审计），对应 QA-P0-001 / QA-P0-002 / QA-P1-003
```

**CI 语义：** 全量套件在 `.github/workflows/windows-core.yml` 中以 **`NON-GATING BASELINE / KNOWN BASELINE`** 运行，`continue-on-error: true`，只用于保存并显示真实 `run / failure / error / skipped`。**workflow green 不得被解释为 “Full suite PASS”**。Required/gating 测试失败必须使 workflow FAIL。

## Phase 2 下一步

Phase 2 为 `PHASE_2_READY / NOT_STARTED`，**不会自动开始**。进入 Phase 2 须用户明确授权，且只建立最小正式工程底座：Python 3.12、PySide6 薄 AppShell、Design Token、Repository Protocol、三库职责、Migration 基础、Logging 与有限工程清理。

不得在 Phase 2 批量迁移 Profile、批量重写 evaluator、实现完整 Excel / 完整产品 Shell / 移动端 / Suite，或一次性实现全部中央 DRAFT Contract。详见 [ROADMAP.md](ROADMAP.md) 第 4 节与 [docs/28_EquipEffi 后续开发总体路线 V2.3.md](docs/28_EquipEffi%20后续开发总体路线%20V2.3.md) 第 5、8 节。

## Historical evidence 链接

以下文件承载历史事实（Phase 0 结论、Phase 1 Goal Log 与验收复验、Phase 1 Verification Evidence、Phase 0 事实摘要、QZC-A01 接入、Roadmap V2.3 Alignment、P1-SR01 等），**本文件不再复制其正文**：

- [ROADMAP.md](ROADMAP.md) 第 7 节 Historical 入口
- [docs/governance/](docs/governance/) — 各阶段执行/接入/收口报告
- [HANDOFF_20260831.md](HANDOFF_20260831.md) — 逐任务历史事实（第 213 章及以前）
- [PUMP_V2_G04_APPROVAL_MANIFEST.md](PUMP_V2_G04_APPROVAL_MANIFEST.md)、[PUMP_V2_R01_R06_COMMIT_MANIFEST.md](PUMP_V2_R01_R06_COMMIT_MANIFEST.md)、[PUMP_V2_R07_COMMIT_MANIFEST.md](PUMP_V2_R07_COMMIT_MANIFEST.md)
- [QZC_N01_B_EXECUTION_REPORT.md](QZC_N01_B_EXECUTION_REPORT.md)（`HISTORICAL-SUPERSEDED`）
- `docs/23～docs/27` 编号执行清单（`HISTORICAL`）

---

## 1. 当前项目目标

EquipEffi 是一个设备能效分析工具。目标是以 V4 空白模板为数据入口，以标准原文为依据，对设备的出厂设计值、额定值或铭牌值进行能效等级、评价等级、适用范围和淘汰目录判定，并输出可审计的中间计算、查表结果和判定轨迹。

最终系统应包括：

1. 与 V4 模板完全一致的 15 类公共设备接口；
2. 17 个内部评价 profile，允许多个内部 profile 共用一个公共设备类型；
3. 16 项能效/评价标准的数据包、版本、来源页码、表号和稳定 data_id；
4. 标准查表、标准允许的计算、插值和多指标比较；
5. “不在范围、无法判定、淘汰、未达标”以及各设备专用等级；
6. 第一至第四批高耗能落后机电设备淘汰目录匹配；
7. 可替换的桌面窗口、Web 窗口、JSON/JSONL 接口和未来 Linux/Android 展示层；
8. 在获得明确授权后接入 V4 Excel 的读取、判定、写回、图片、保护和批量性能验收；
9. 原始模板、标准 PDF、粗校对文件和用户文件不被覆盖；不使用宏。

当前阶段的重点是“先保证参数评价内核和追溯正确”，Excel 正式导入/写回仍是冻结端口，不应在普通 profile 边界任务中顺手开启。

## 2. 当前状态摘要

> **测试数字以本文件顶部“当前 full-suite baseline”为准。** 下表零星出现的旧回归数字（如 852 项、2026-09-07 记录）为历史快照，不代表当前基线。

| 项目 | 当前状态 | 说明 |
|---|---|---|
| 公共设备接口 | 已完成基础架构 | 15 类，与 V4 公共 sheet 对齐 |
| 内部评价 profile | 主路径已实现，边界未全部验收 | 17 个 profile |
| 标准数据 | 已建立并可加载 | 17 个内部标准包为 active；active 只表示可加载，不表示所有边界都已验收 |
| PMSM 标准数据 | 已人工复核并激活 | GB 30253-2024 29 张表；旧粗校对 PMSM 数据禁止重新加载 |
| 人工校对册 | 已生成 | README 记录全量 61,958 条记录为“正确” |
| 淘汰目录 | 第一至第四批已接入 | 产业结构调整目录目前只是用户明确提供的受控子集，不是全文 |
| 参数评价 API | 可用 | 单条、批量、JSON、JSONL、Web 共用同一门面 |
| 桌面/Web 窗口 | 可用原型 | Tk 不可用时自动 Web 回退 |
| Excel | 接口和模板下载存在，正式读写冻结 | 上传接口默认返回“尚未接入 Excel 适配器” |
| Linux/Android | JSONL 桥接协议已具备 | Android 应用、签名、安装包尚未完成 |
| 最近固定轻量回归 | 852 项通过 | 2026-09-07 记录，约 8.763 秒，退出码 0 |
| 项目整体 | 未完成 | 852 项通过不是全部完成证明 |

如果用户只需要“输入参数并反馈结果”，当前核心链路已经可以使用；如果需要“直接上传 V4 Excel、批量写回、保护和现场发布”，还不能宣称完成。

## 3. 已经完成的工作

### 3.1 公共类型和架构边界

公共 code 必须只在 `device_types.py` 中定义和映射，不能在 UI、Excel、JSONL 或 Android 层复制第二套映射。

| 公共 code | 公共名称 | 内部 profile |
|---|---|---|
| `transformer` | 变压器 | `transformer` |
| `motor` | 电动机 | `motor_lv`、`motor_hv`、`motor_pmsm` |
| `compressor` | 空压机 | `compressor` |
| `centrifugal_pump` | 离心泵 | `pump_water`、`pump_chemical` |
| `centrifugal_fan` | 离心通风机 | `fan` |
| `axial_fan` | 轴流通风机 | `fan` |
| `blower` | 鼓风机 | `blower` |
| `submersible_pump` | 潜水电泵 | `submersible` |
| `industrial_boiler` | 工业锅炉 | `boiler` |
| `heat_treatment` | 热处理设备 | `heat_treatment` |
| `heat_pump_chiller` | 热泵和冷水机组 | `heat_pump_chiller` |
| `heat_pump_water_heater` | 热泵热水机 | `heat_pump_water_heater` |
| `duct_ac` | 风管送风式空调 | `duct_ac` |
| `unitary_ac` | 单元式空调 | `unitary_ac` |
| `multi_split_ac` | 多联式空调 | `multi_split_ac` |

核心评价器不得导入 Tk、Excel、Web 或文件扫描模块；展示层只能调用 `EvaluationFacade`/`ApplicationApi`。

### 3.2 标准数据和 PMSM 特殊处理

- 标准原文 PDF 优先，其次是逐项复核的人可读校对册；粗校对 Excel 和历史 JSON 只能作为历史材料。
- 永磁同步电机粗校对工作簿、旧 `motor_pmsm.json`、旧清洗版 Excel 不得进入数据生成或验证链路。
- 当前 PMSM 标准包为 `gb30253_2024_pdf_verified_v1`。
- GB 30253-2024 的 29 张表已经逐表人工复核。
- 表 1 的 55 kW、12 极的 1/2/3 级均为原文“—”，机器数据保留无数据；命中时返回“不在范围”，不能转为 0、缺失或可插值值。
- 电动机冷却方式已包含 `IC86W、IC71W（IC3W7）、IC416、IC666`。
- 当前鼓风机使用 GB 28381-2012；GB 28381-2026 已发布但尚未启用。

校对数据、标准来源和激活状态主要位于：

- `src/equipeffi/standard_manifest.json`
- `src/equipeffi/resources/standards/`
- `src/equipeffi/resources/standards/gb30253_2024_pdf_verified_v1.json`
- `src/equipeffi/resources/templates/`
- `outputs/final_20260830_all_verified/`
- `outputs/final_20260830_portable_provenance_v12/`

### 3.3 评价结论和结果契约

所有设备都支持以下通用结论：

```text
不在范围、无法判定、淘汰、未达标
```

普通三级设备另外支持 `1级、2级、3级`。特殊设备允许值为：

- 鼓风机：`节能评价值、能效限定值`
- 热处理设备：`一等、二等、三等`
- 热泵热水机：`1级、2级、3级、4级、5级`

结果对象的关键字段包括：

```text
conclusion
reference_conclusion
actual_metrics
calculated_metrics
limits
comparisons
lookups
missing_fields
data_quality_issues
standard_reference
elimination_match
elimination_scope
trace
trace_schema_version
```

评价优先级固定为：

1. 明确命中淘汰目录：最终结论为“淘汰”；
2. 淘汰条件疑似适用但信息不足：无法判定；
3. 明确超出标准范围：不在范围；
4. 缺少判定参数或标准数据不可用：无法判定；
5. 低于最低等级或限定值：未达标；
6. 其他情况按标准比较结果返回等级。

参数统一视为出厂设计值、额定值或铭牌标称值，不使用“实测”措辞。

### 3.4 已完成的评价边界和追溯补强

历史任务已经覆盖许多缺失字段、标准表边界和早退追溯场景，包括：

- 变压器缺少单项损耗时保留另一项损耗、三级阈值和标准行；
- 低压/高压电动机缺少功率、极数、冷却方式、额定效率时保留候选和阈值；
- PMSM 缺少极数、额定转速、功率未命中及“—”语义；
- 清水泵、石化泵缺少泵效率或级数时保留计算值、候选标准行和缺失字段；
- 离心/轴流/外转子风机缺少效率时保留压力系数、轮毂比、机号、结构修正和三级阈值；
- 鼓风机缺少出口压力或温度时保留 `b₂/D₂`、已知进口参数、表 1/表 5 阈值和 data_id；
- 工业锅炉蒸发量和热功率双空时明确提示二选一缺失；单填、双填冲突和容量边界已有部分测试；
- 热处理设备能源类型和耗能字段的正向、反向互斥已有 V4 校验；
- 许多标准开闭边界、禁止最近档、禁止外推和“—”值已经写入回归测试。

最近三个交接任务：

- 第 211 章：鼓风机压力/温度缺失追溯；
- 第 212 章：工业锅炉容量双空门禁；
- 第 213 章：热处理燃料能源填写电炉耗电量的反向互斥。

详细输入、标准页码、data_id、结果契约和测试证据必须以 `HANDOFF_20260831.md` 末尾章节为准。

### 3.5 窗口、模板和接口

内置模板为：

```text
src/equipeffi/resources/templates/设备能效分析空白模板_重构版V4_20260825.xlsx
```

当前已具备：

- 15 类设备选择；
- 按 V4 契约动态生成输入字段；
- 效率、功率因数、正值、枚举等输入提示；
- 下载内置空白模板；
- 上传 V4 工作簿的接口按钮和端口；
- JSON/JSONL/Web/桌面共用评价门面；
- `/api/template` 模板下载接口。

当前明确未启用：

- 正式解析上传的 `.xlsx`；
- 批量读取工作簿数据；
- 将结果写回新工作簿；
- 图片置于单元格；
- 自动编号、排序、保护和 1500 行 Excel 压力验收。

## 4. 现在进行到哪里

当前处于“Phase 1 已 PASS、Phase 2 READY / NOT_STARTED、参考标准产品工程尚未开始”的阶段：评价内核、标准数据、Phase 1 契约与 `pump_water` 业务真相均已就位，主要缺口在**产品工程层**（正式 Windows 壳、标准库→分析→结果纵向闭环、正式记录/历史、Excel），而不是重新设计泵算法。详见 [REFERENCE_STANDARD_ROADMAP.md](REFERENCE_STANDARD_ROADMAP.md)。

> **测试数字以本文件顶部“当前 full-suite baseline”为准。** 本节旧有的 2026-09-07 局部数字（852 / 323 / 126）已移除，避免与当前基线冲突；历史数字只在 [HANDOFF_20260831.md](HANDOFF_20260831.md) 等历史文件中保留。

不要把“标准包 `active`”或任何单一通过数字解释为项目整体完成。

## 5. 当前问题和阻塞

### 5.1 不是代码阻塞，但必须继续做的范围

17 个 profile 的完整边界矩阵还没有全部完成。仍需要逐 profile 验证：

- 正常精确查表；
- 离散维度缺失和未命中；
- 允许插值与禁止插值；
- 开闭区间边界；
- 标准“—”值；
- 缺失、非法、零值、负值和单位错误；
- 多个条件同时满足或冲突；
- 结构修正和多指标 AND/OR 规则；
- 早退时已读取参数、计算值、查表值、阈值和来源是否完整保留。

### 5.2 Excel 集成冻结

Excel 适配器代码、V4 合同和端口已经存在，但正式读取和写回是单独阶段，不能在普通评价器任务中偷偷开启。重新授权 Excel 后，应单独验收：

1. 读取 V4 15 个公共 sheet；
2. 字段 ID、列顺序、分组和单位映射；
3. V4 校验和自动备注；
4. 批量调用 `EvaluationFacade`；
5. 输出查表值、计算值、结论和判定轨迹；
6. 图片保留、保护、冻结、筛选、排序后编号；
7. 原文件不覆盖；
8. 1500 行以上批量性能和重新打开验收。

V2.3 对该历史条目的新约束是：正式 Excel 仍在 Phase 8；Phase 2～4 只建立 contract-driven 字段/Import/result 接口，不提前开启完整 Excel 产品实现。

### 5.3 产业目录不完整

第一至第四批机电淘汰目录是当前默认目录。产业结构调整目录只有用户明确提供的受控设备条目，未接入全文。未覆盖条目不能解释为“未淘汰”；条件不足或目录不完整时应返回“无法判定”。

### 5.4 窗口和跨平台发布未完成

- 当前环境 Tk 原生窗口不可用，使用标准库 Web 回退；
- Linux 只具备可复用的 Python/JSONL 入口，尚无正式发行包验收；
- Android 仅有 JSONL 桥接设计和目录，不代表 APK 已完成；
- Windows 便携包/发布目录已有产物，但还需最终发布审计和目标机验证。

### 5.5 外部标准源可能不可访问

新环境不一定能访问 `G:\标准  规范\...`。优先使用仓库内标准包和来源元数据；如果必须重新提取 PDF，必须保留独立输入/输出文件、页码、表号和校对状态，不能猜测模糊数值。

## 6. 下一步应该做什么

本节以下旧小任务顺序属于历史执行材料，不再拥有当前调度权。V2.3 生效后的唯一当前下一步是：

> **Roadmap V2.3 Alignment 完成后停止，等待用户单独授权 Phase 2。**

在授权 Phase 2 前，不得自动领取工程清理、PySide6、Excel、Profile 迁移或其他 Phase 2+ 正式实现任务。

### 历史第一步：领取一个新的单一边界

当前 HANDOFF 第 213 章建议的下一步是：

- 工业锅炉蒸发量/热功率二选一的非法数值或候选追溯；或
- 热处理非法能源枚举及燃料候选保留；或
- 另一个尚未登记、且有标准原文证据的 profile 边界。

领取前查重：

```powershell
Set-Location '<仓库根目录>'
rg -n 'T[0-9]{2}\.[0-9]{2}-|目标边界|唯一下一步' HANDOFF_20260831.md docs
rg -n '<任务ID>|<边界关键词>' HANDOFF_20260831.md docs
```

### 历史第二步：遵循小任务流程

```text
只读预检
→ 标准证据卡
→ 先写一个能证明契约的测试
→ 只运行该测试
→ 必要时做最小生产修改
→ 目标测试
→ 相关矩阵/核心测试
→ compileall + diff-check
→ 固定轻量完整回归一次
→ 追加 HANDOFF 章节
→ 更新本文件和 docs/23～docs/27
```

每次只认领一个任务 ID、一个内部 profile、一个标准边界。没有 PDF 或校对册证据时，停止并报告“证据不足”，不要猜标准值。

### 历史第三步：建立最终覆盖矩阵

待边界任务足够后，建立 17×场景矩阵，至少包含：正常、边界、未命中、可插值、禁止插值、缺失、非法、零/负值、—值、冲突条件、淘汰命中和标准未激活。每个单元格都要能追溯到标准表号、页码、data_id 和测试。

### 历史第四步：单独重新授权 Excel 集成

Excel 阶段必须以版本化 Product/Profile + Import Contract 为字段与映射契约，不在评价器中复制 Excel 逻辑。正式实现仍归 Phase 8；批量行必须进入统一 Application/EvaluationService 路径，结果文件必须是新文件，不覆盖输入。

### 历史第五步：发布和跨平台验收

完成覆盖矩阵和 Excel 后，再做 Windows 便携包、Linux JSONL、Android 桥接、安装/签名和最终审计。发布审计必须同时验证标准来源、模板、校对册、目录和包内资源路径。

## 7. 已经踩过的坑：不要重复

### 7.1 标准和数据

- 不要加载旧 PMSM JSON、临时 `~$` 文件、粗校对 PMSM Excel 或旧清洗结果。
- 不要把标准“—”转成 0、普通空值、缺失值或插值点。
- 不要按单调趋势自动修改标准数值。
- 不要取最近功率档、最近极数、最近速度档或最近区间。
- 不要在标准不允许时外推或擅自插值。
- 不要把标准包 `active` 理解成所有边界已经测试完毕。
- 不要把产业目录未命中解释成“未淘汰”。

### 7.2 输入和单位

- 效率按百分数本值填写：98 表示 98%；0.98 和 101 应被拒绝。
- 冷凝锅炉设计热效率可以按标准例外使用 1～110；非冷凝锅炉仍为 1～100。
- 功率因数是 0～1，不是 0～100。
- COP、EER、SEER、APF 等比值只要求大于 0，不使用效率百分数范围。
- 数量、极数、级数等必须为正整数。
- 所有参数是出厂设计值、额定值或铭牌值，不写“实测”。
- 不为缺失物理参数设置默认值，不默认 80%、1 级、1 级泵或最近档。

### 7.3 结果和追溯

- 缺字段时不要只返回一个空结论；能安全得到的实际输入、计算值、标准候选、阈值、页码和 data_id 必须保留。
- 不要把实际输入、计算值、标准查询值和最终结论混在同一个字段。
- 淘汰设备即使可以继续计算参考能效等级，最终 `conclusion` 仍必须是“淘汰”。
- `actual_metrics` 和 `calculated_metrics` 不应包含猜测值。
- 早退分支不得丢失已经完成的查表证据。

### 7.4 工程和性能

- 不要运行全量 `unittest discover`、并行测试、PDF 全量渲染或 Excel 压力测试作为普通小任务的顺手验证；此前出现过 CPU 长时间 100%。
- 固定命令必须串行执行；不要同时启动多个构建/测试进程。
- 不要使用 `INDIRECT`、`OFFSET`、整列易失性公式或大范围条件格式。
- 不要用 `git reset --hard`、`git checkout --`、递归删除或覆盖用户文件。
- 代码编辑使用 `apply_patch`，保留现有脏工作区和用户改动。
- 不要把 UI、Excel、Web 逻辑复制到领域评价器。

### 7.5 Excel 和 V4

- Excel 上传按钮目前是接口预留，不要误以为已经完成读取。
- 不要修改 V4 表头、sheet 数量、公共 15 类、字段 ID 或模板资源。
- 不要在没有重新授权的情况下实现正式批量写回、图片、保护和性能测试。
- 结果文件必须另存，不能覆盖输入工作簿。

## 8. 关键文件和目录

### 8.1 入口和说明

- `README.md`：项目运行、发布包、模板、JSONL 和验收说明；
- `HANDOFF.md`：本文件，当前统一入口；
- `ROADMAP.md`：V2.3 当前路线入口；
- `docs/28_EquipEffi 后续开发总体路线 V2.3.md`：当前总体路线增量校准；
- `docs/28_EquipEffi 后续开发总体路线 V2.2.md`：V2.3 继承基线；
- `PLATFORM_BASELINE.md` / `platform-lock.json`：Qingzhou-contracts 锁定基线；
- `HANDOFF_20260831.md`：逐任务历史事实和最新第 213 章；
- `docs/27_后续Agent和大模型可直接照做交付清单_v15_20260905.md`：历史执行手册，不再决定当前下一任务；
- `docs/26_多Agent可直接照做交付清单_v14_执行手册_20260905.md`：历史低 CPU 执行流程和停止条件。

### 8.2 核心代码

- `src/equipeffi/domain/evaluation/device_types.py`：15 类公共类型和路由；
- `src/equipeffi/domain/evaluation/evaluator_registry.py`：17 个内部 profile 注册；
- `src/equipeffi/domain/evaluation/evaluators/`：设备专属评价器；
- `src/equipeffi/domain/evaluation/metadata.py`：字段、单位、V4 映射和元数据；
- `src/equipeffi/application/services/evaluation_service.py`：单条评价服务；
- `src/equipeffi/application/services/evaluation_facade.py`：跨 API/UI/JSONL 的公共门面；
- `src/equipeffi/application/services/v4_validation.py`：V4 自动备注和条件校验；
- `src/equipeffi/application/services/v4_workbook_service.py`：V4 批量编排层，不包含具体 Excel 库调用；
- `src/equipeffi/application/ports/`：Excel、模板、评价等端口；
- `src/equipeffi/presentation/`：桌面、Web、JSONL 等展示层；
- `src/equipeffi/infrastructure/excel/`：模板资源、V4 读取/写回骨架和审计工具，正式导入/回写仍冻结。

### 8.3 标准、模板和目录

- `src/equipeffi/standard_manifest.json`：标准包清单和状态；
- `src/equipeffi/resources/standards/`：机器可读标准数据；
- `src/equipeffi/resources/templates/设备能效分析空白模板_重构版V4_20260825.xlsx`：内置 V4 空白模板；
- `src/equipeffi/resources/templates/README.md`：模板资源说明；
- `src/equipeffi/resources/elimination_catalog_batches_1_4.json`：第一至第四批淘汰目录；
- `src/equipeffi/resources/elimination_catalog_industry_2024.json`：用户提供的产业目录受控子集。

### 8.4 测试

- `tests/unit/test_device_evaluator_matrix.py`：17 个 profile 的评价矩阵和边界测试；
- `tests/unit/test_evaluation_engine.py`：核心评价服务、淘汰、结果契约；
- `tests/unit/test_v4_validation.py`：V4 输入和自动备注校验；
- `tests/unit/test_v4_input_adapter.py`：V4 字段适配；
- `tests/unit/test_v4_contract_and_facade.py`：V4 合同和公共门面；
- `tests/contract/`：公共类型、架构边界和接口合同；
- `tests/integration/test_workbook_contract.py`：工作簿合同的冻结测试。

## 9. 关键命令

以下命令在 Windows PowerShell、项目根目录运行。必须先设置 `PYTHONPATH`。

### 9.1 查看状态和运行示例

```powershell
Set-Location '<仓库根目录>'
$env:PYTHONPATH = 'src'
python -m equipeffi --list-device-types
python -m equipeffi --status
python -m equipeffi --web
python -m equipeffi --gui
```

`--gui` 在 Tk 不可用时应回退到 Web；不要把回退提示当成评价失败。

### 9.2 单条参数评价

```powershell
$env:PYTHONPATH = 'src'
python -m equipeffi --device-type motor --json '{"category":"三相异步电动机","rated_voltage":"0.4","rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}'
```

固定判定基准日期可增加 `--as-of YYYY-MM-DD`。淘汰目录口径可使用 CLI 的 `--elimination-scope`。

### 9.3 固定轻量回归命令

普通小任务使用下面这组固定命令，串行运行，不要并行：

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.contract.test_device_metadata tests.contract.test_architecture_boundaries tests.unit.test_entrypoint tests.unit.test_application_api tests.unit.test_desktop_form_model tests.unit.test_v4_validation tests.unit.test_v4_input_adapter tests.unit.test_device_evaluator_matrix tests.unit.test_evaluation_engine tests.unit.test_public_device_types tests.unit.test_v4_contract_and_facade tests.integration.test_workbook_contract tests.unit.test_disabled_adapters tests.unit.test_standard_provenance_audit -q
$code=$LASTEXITCODE
Write-Output ("EXIT=" + $code)
exit $code
```

最近记录应看到末尾类似：

```text
Ran 852 tests ... OK
EXIT=0
```

> 上方的 `852` 是 2026-09-07 的历史快照，**不是当前数字**；该组轻量回归的当前项数应以实际运行输出为准。当前权威基线见本文件顶部“当前 full-suite baseline”。

命令中的两处 argparse usage error 和 Tk 回退提示是已知非阻断输出；如果退出码不是 0，必须保留完整错误，不能只写“测试通过”。

### 9.4 目标/核心/静态检查

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_device_evaluator_matrix.DeviceEvaluatorMatrixTests.<目标测试> -q
python -m unittest tests.unit.test_device_evaluator_matrix tests.unit.test_evaluation_engine -q
python -m compileall -q src main.py
git diff --check -- . ':(exclude)outputs'
```

不要因为目标测试首次通过就虚构“修复前失败”；如果生产代码本来已满足契约，应如实记录“新增测试首次通过，未修改生产代码”。

### 9.5 查重和证据

```powershell
rg -n 'T[0-9]{2}\.[0-9]{2}-|目标边界|唯一下一步' HANDOFF_20260831.md docs
rg -n '<任务ID>|<边界关键词>' HANDOFF_20260831.md docs
rg -n 'data_id|source_page|source_clause|match_status' src tests
```

标准值无法从仓库资源或原文可靠确认时，停止并报告证据不足；不要猜数值、不要按趋势修正。

## 10. 交接回报格式

每完成一个已授权的后续任务，应同步当前权威治理文件。历史 `HANDOFF_20260831.md` 继续保留逐任务事实，但不自动调度新任务。回报至少记录：

```text
任务ID
状态
唯一目标
业务/标准证据
修改范围
新增或修改测试
结果契约
未修改边界
真实验证命令与结果
静态检查
已知风险
下一步
```

不要写“项目全部完成”，除非负责人已经完成 Windows V1 的正式全量验收并有独立审计证据。

## 11. 当前建议的下一项任务

当前没有自动领取的工程任务。

Roadmap V2.3 Alignment 完成后：

```text
Phase 0 = PASS
Phase 1 = PASS
QZC-A01 = COMPLETE
Phase 2 = READY / NOT_STARTED
automatic_continuation = DISABLED
```

**停止。等待用户单独授权 Phase 2。**
