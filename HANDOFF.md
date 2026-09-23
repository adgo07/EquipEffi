# EquipEffi 项目交接说明

> **Phase 1 执行（2026-09-22～2026-09-23）**
>
> 当前唯一权威路线：`EquipEffi V2.2`；当前阶段：`Phase 1`；当前状态：`BLOCKED`；下一状态：`REVIEW_BLOCKER_RESOLUTION`。
>
> 旧 v7–v15、T04.xx、旧 HANDOFF 和编号执行清单均为 `HISTORICAL / NOT AUTHORITATIVE FOR NEXT TASK`。它们保留事实，不再拥有自动任务调度权。请先读取 [ROADMAP.md](ROADMAP.md)、[TASK_STATE.md](TASK_STATE.md)、[BASELINE.md](BASELINE.md)、[ASSET_AUDIT.md](ASSET_AUDIT.md)、[QA_BACKLOG.md](QA_BACKLOG.md) 和 [V1_SCOPE.md](V1_SCOPE.md)。
>
> Phase 0 已建立 tag `pre-v2-rebaseline`，指向起始 HEAD `a1643ed38e0b934bbc7562348883b8a8bd4badc5`。Phase 1 未修改 evaluator、目录、标准资源或业务算法，未执行 0B Hotfix。六个 Goal 的技术交付已在 HEAD `9cb39cccf0381ba0e560c5f69fcb81725acfbe87` 提交并可复现；Windows V1 产品决策和 CPython 3.12.x x64 环境仍缺失。当前唯一合法下一步是收口这两个 Phase 1 阻塞并提交 Solution/Product Review，不得启动 Phase 2。

## Phase 1 当前权威状态

| 项目 | 当前事实 |
|---|---|
| 当前路线 | `EquipEffi V2.2` |
| 当前阶段 | `Phase 1` |
| 当前 Goal | `Phase 1 Review Package` |
| 状态 | `BLOCKED` |
| 唯一下一步 | 获取产品 Scope 决策并建立/复验 Python 3.12.x x64 环境，再进入 Solution/Product Review；不得跳到 Phase 2 |
| 业务样板 | `pump_water`，后续以 GB 19762-2025 标准映射为证据 |
| 代码边界 | 仅允许规范/契约/Golden/审计文档及必要验证；不改业务实现 |

## Phase 1 Goal Log（当前权威）

| Goal | 状态 | 交付/证据 | 下一步 |
|---|---|---|---|
| `P1-G01` | `COMPLETE` | [business_spec.md](specs/equipment_efficiency/business_spec.md)：业务对象、评价生命周期、Support Status、证据优先级和验收条件 | `P1-G02`：建立五类数据契约和版本字段语义 |
| `P1-G02` | `COMPLETE` | `schemas/canonical.schema.json`、`profile.schema.json`、`import_contract.schema.json`、`golden_case.schema.json`；business spec 第 10/11 节冻结契约边界和版本字段语义；JSON 语法校验通过 | `P1-G03`：完成 `pump_water` / GB 19762-2025 映射 |
| `P1-G03` | `COMPLETE` | [profiles/pump_water.md](specs/equipment_efficiency/profiles/pump_water.md)：字段、单位、别名、标准公式、10 个表 3 数据行、开闭边界、无插值/外推、缺失/未知/冲突语义；当前包哈希已记录 | `P1-G04`：建立并批准首批 `pump_water` Golden Cases |
| `P1-G04` | `COMPLETE` | [golden/pump_water](specs/equipment_efficiency/golden/pump_water)：7 个 `REVIEWED` 案例覆盖正常、下/上端点、区间切换、不外推、缺失效率和未知类别；增强验证器校验 Decimal、受控 `unit_id`、来源存在性/指纹和三项负例拒绝 | `P1-G05`：复核四项 Phase 1 P0 风险 |
| `P1-G05` | `COMPLETE` | [QA_BACKLOG.md](QA_BACKLOG.md) Phase 1 P0 Evidence Review：AUD-010/011/030/031 分别为允许的精确分类；AUD-011 因共享风险证据不足为 `NEEDS_MORE_EVIDENCE`；无 Hotfix、无 evaluator 修改 | `P1-G06`：冻结 Python 版本、版本字段和 Windows V1 Scope |
| `P1-G06` | `COMPLETE` | [V1_SCOPE.md](V1_SCOPE.md) 形成 17 Profile 的工程候选边界、CPython 3.12.x x64 和版本字段语义；商业批准、负责人/日期仍为 `REQUIRED_INPUT`，3.12 环境尚未建立 | `BLOCKED`；先收口验收阻塞，不得自动进入 Phase 2 |

## Phase 1 acceptance re-review（2026-09-23）

| 验收项 | 状态 | 证据/处理 |
|---|---|---|
| Phase 1 交付物进入可复现 Git 提交 | `RESOLVED` | HEAD `9cb39cccf0381ba0e560c5f69fcb81725acfbe87` 已包含权威 Phase 1 交付物、治理文件、验证器和 docs/28～30 路线/方案文件；未提交业务实现 |
| Golden Case Schema 类型、单位、来源门禁 | `RESOLVED_TECHNICALLY` | `golden_case.schema.json` 约束 Decimal 字符串和 `unit_id` 枚举；`tools/validate_phase1_contracts.py` 负责来源存在性和 SHA-256；负例必须得到 3 个错误 |
| `pump_water` 规定点语义 | `RESOLVED_TECHNICALLY` | 映射明确 `flow_m3h=Q_BEP`、`head_m=H_BEP`、`pump_efficiency=η_BEP`，案例机器字段为 `STANDARD_BEP/BEP`；GB PDF 外部指纹已记录 |
| AUD-011 精确分类及共享风险 | `RESOLVED_AS_REVIEW_RESULT` | `review_result=NEEDS_MORE_EVIDENCE`；保留 `classification=P0`，样板证据不外推为全 Profile `NOT_P0` |
| Windows V1 产品决策 | `BLOCKED` | `V1_SCOPE.md` 显式要求具名负责人、日期、用户需求/商业价值证据和接受/拒绝理由；Agent 不代填 |
| CPython 3.12.x x64 可复验环境 | `BLOCKED` | 当前仅有 Python 3.13.3；`py -3.12 --version` 尚未可用，不能把 3.13 结果冒充 V1 验收 |

在产品 Scope 决策和可重复 3.12.x x64 复验缺失期间，本交接保持 `BLOCKED`；不声明 `PHASE_1_PASS`，不启动 Phase 2。

## Phase 1 Verification Evidence（2026-09-22）

| 类别 | exact command / probe | environment | duration | pass | fail | error | skip | not_run / reason |
|---|---|---|---:|---:|---:|---:|---:|---|
| Legacy Regression | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -m unittest discover -s tests -p 'test_*.py'` | Windows；Python 3.13.3；完整依赖；源码工作区 | 142.123 s（unittest 内部；PowerShell wall 未单独包裹） | 880 | 3 | 1 | 3 | 0 |
| Legacy failures retained | 同上 | 与 Phase 0 相同 | — | — | 3（V4 motor reader/writer） | 1（release audit `wheel_pmsm_status`） | 3 | 未修复、未隐藏、已保留在 QA_BACKLOG |
| compileall | `$py -m compileall -q src tools tests` | Python 3.13.3；`PYTHONPATH=src` | 0.911 s | 1 | 0 | 0 | 0 | 0 |
| package import | `$env:PYTHONPATH='src'; $py -c "import equipeffi; print(equipeffi.__file__)"` | Python 3.13.3；`PYTHONPATH=src` | 0.068 s | 1 | 0 | 0 | 0 | 0 |
| package/resource smoke | `$py -m equipeffi --status`；`$py -m equipeffi --device-type centrifugal_pump --example` | Python 3.13.3；`PYTHONPATH=src` | 0.279 s / 0.257 s | 2 | 0 | 0 | 0 | 0 |
| Contract/Golden validation | `python tools/validate_phase1_contracts.py --negative-probe` | Python 3.13.3；`jsonschema 4.23.0`；工作区外部 GB PDF 可访问 | 0.317 s | 7 cases；negative probe=3 errors | 0 | 0 | 0 | 0 |
| Python 3.12 environment | `py -3.12 --version` | Windows Python launcher | — | — | — | — | — | NOT_RUN：未安装 Python 3.12；Phase 2 前必须建立可重复 x64 环境 |
| `git diff --check` | `git diff --check` | Git working tree | <1 s | PASS | 0 | 0 | 0 | 0 |

Phase 1 没有修改标准 JSON、模板、evaluator 或测试期望，因此没有重写 `BASELINE.md` 的 Phase 0 起始事实。上表是本次 Phase 1 复验事实；旧失败仍然是当前失败。

以下 Phase 0 摘要和旧正文保留为历史事实；本节及后续 Goal Log 覆盖其中的当前阶段和下一步说明。

## 当前事实摘要（Phase 0 Revalidated）

| 项目 | 当前事实 |
|---|---|
| 正式运行实现 | `domain/evaluation` → `EvaluationService` → `evaluator_registry` → 17 个 evaluators → `JsonStandardRepository` |
| 空壳/兼容路径 | `domain/devices/` 为 0 引用空壳；`device_evaluators.py` 为当前仍被依赖的兼容门面；均未删除 |
| 当前正式测试 | Python 3.13.3 Phase 1 复验：887 项，880 pass、3 fail、1 error、3 skip；unittest 内部 142.123 s；4 个已知失败未改变，详见上方 Evidence |
| compileall / package import | Python 3.13.3：0.315 s / 0.055 s，均 PASS |
| 标准加载 | 17 个 manifest pack 可加载并报告 active；不等于业务边界已验收；`pump_water` 已有 7 个 Golden Case |
| Windows V1 Scope | 工程候选冻结为 `transformer`、`compressor`、`pump_water`；motor 三 Profile 与 `heat_pump_chiller` `UNDER_REVIEW`，其余 `POST_V1`；产品批准待评审 |
| 首个纵向样板 | `pump_water`；候选比较和必须证明项见 `V1_SCOPE.md` |
| 当前唯一下一步 | 收口 Phase 1 阻塞并提交 Solution/Product Review；不得继续 T04.xx、批量改 evaluator、建完整 PySide6/SQLite/Excel 产品或启动 Phase 2 |

以下旧正文保留为历史事实参考；其中的日期、通过数字和“下一任务”说明不覆盖本节及 Phase 0 权威文件。

> 文档用途：给一个完全没有前文上下文的新 Codex/开发者使用。阅读本文件后，应能知道项目要做什么、当前做到哪里、哪些内容不能重复做，以及如何安全地继续工作。
>
> 本文件是项目根目录的当前交接入口。历史逐项记录仍在 [HANDOFF_20260831.md](HANDOFF_20260831.md)；详细执行规则见 [docs/27_后续Agent和大模型可直接照做交付清单_v15_20260905.md](docs/27_后续Agent和大模型可直接照做交付清单_v15_20260905.md)。
>
> 最近一次 HANDOFF 事实记录：2026-09-07，第 213 章。当前日期可能晚于该日期；如果代码或测试发生变化，必须重新运行验证并更新本文件，不要直接沿用旧数字。

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

当前处于“评价内核可运行、标准数据已校对、按标准边界逐项补齐回归”的阶段。

最新已验证基线（记录于 2026-09-07）：

```text
V4 校验套件：126 tests passed
矩阵 + 核心评价器：323 tests passed
固定轻量完整回归：852 tests passed，约 8.763 秒，EXIT=0
compileall：0
git diff --check：0
```

固定轻量完整回归会出现两处预期的 CLI argparse usage error，以及 Tk 不可用时的 Web 回退提示；只要最后为 `OK` 且 `EXIT=0`，它们不是失败。

截至本交接文件生成时，未有证据证明 17 个 profile 的全部标准表、所有区间、所有组合条件和所有输出字段均已验收。不要把“标准包 active”或“852 项通过”解释为项目整体完成。

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

按以下顺序继续，不要一次扩大到整个项目：

### 第一步：领取一个新的单一边界

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

### 第二步：遵循小任务流程

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

### 第三步：建立最终覆盖矩阵

待边界任务足够后，建立 17×场景矩阵，至少包含：正常、边界、未命中、可插值、禁止插值、缺失、非法、零/负值、—值、冲突条件、淘汰命中和标准未激活。每个单元格都要能追溯到标准表号、页码、data_id 和测试。

### 第四步：单独重新授权 Excel 集成

Excel 阶段必须以 V4 模板为唯一字段合同，不在评价器中复制 Excel 逻辑。使用 `V4WorkbookService` 编排读取→验证→评价→写回，结果文件必须是新文件，不覆盖输入。

### 第五步：发布和跨平台验收

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
- `HANDOFF_20260831.md`：逐任务历史事实和最新第 213 章；
- `docs/27_后续Agent和大模型可直接照做交付清单_v15_20260905.md`：首选执行手册；
- `docs/26_多Agent可直接照做交付清单_v14_执行手册_20260905.md`：低 CPU 执行流程和停止条件。

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

每完成一个小任务，必须在 `HANDOFF_20260831.md` 末尾追加一个新章节，并同步本文件及 docs/23～docs/27 的当前基线。章节至少记录：

```text
任务ID
状态
唯一目标
标准编号、表号、条款、PDF页码、pack_id、data_version
输入条件和边界
修复前真实失败（若有）
最小生产改动
新增测试
结果契约
查表/计算/插值中间证据
未修改的标准、模板、目录和 Excel 文件
真实测试命令、耗时和退出码
静态检查
性能和 CPU 观察
已知风险
唯一下一步
```

不要写“项目全部完成”，除非负责人已经完成全量覆盖矩阵、Excel、发布和跨平台验收，并有独立审计证据。

## 11. 当前建议的下一项任务

优先从第 213 章的唯一下一步中选择一个尚未重复的单一边界：

1. 工业锅炉容量二选一的非法数值，保留容量候选并明确“无法判定/不在范围”；或
2. 热处理非法能源枚举，保留表 9 燃料候选和字段缺失/冲突说明；或
3. 其他 profile 中有标准原文证据的一个新缺失/边界场景。

完成后必须重新实测，不得直接复制旧的 852 数字。若没有清晰标准证据，停止并请求用户确认。
