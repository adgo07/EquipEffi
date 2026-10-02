# EquipEffi 开发参考（从 HANDOFF 拆出的长期参考材料）

状态：**REFERENCE / 长期开发参考**（非当前状态来源）

> 本文件内容原属 `HANDOFF.md` 第 7～10 节，在 2026-10-02 的 HANDOFF 收口（PR #9 / R2）中从 HANDOFF 拆出，**以免随历史正文一起丢失**。
>
> - 当前产品目标、Phase、支持范围与下一步：见 [HANDOFF.md](../HANDOFF.md) 与 [ROADMAP.md](../ROADMAP.md)。
> - 历史逐任务事实：见 [HANDOFF_20260831.md](../HANDOFF_20260831.md) 与 [governance/](governance/)。
> - 原始位置（拆分前）：`HANDOFF.md@40a88dcc` 第 7～10 节。
> - 本文件是**参考**，不承载“当前状态”，也不构成任务调度来源。

本文件保留了四类长期有用的操作性内容：**已踩过的坑（不要重复）**、**关键文件和目录**、**关键命令**、**交接回报格式**。

---

## 已经踩过的坑：不要重复

### 1 标准和数据

- 不要加载旧 PMSM JSON、临时 `~$` 文件、粗校对 PMSM Excel 或旧清洗结果。
- 不要把标准“—”转成 0、普通空值、缺失值或插值点。
- 不要按单调趋势自动修改标准数值。
- 不要取最近功率档、最近极数、最近速度档或最近区间。
- 不要在标准不允许时外推或擅自插值。
- 不要把标准包 `active` 理解成所有边界已经测试完毕。
- 不要把产业目录未命中解释成“未淘汰”。

### 2 输入和单位

- 效率按百分数本值填写：98 表示 98%；0.98 和 101 应被拒绝。
- 冷凝锅炉设计热效率可以按标准例外使用 1～110；非冷凝锅炉仍为 1～100。
- 功率因数是 0～1，不是 0～100。
- COP、EER、SEER、APF 等比值只要求大于 0，不使用效率百分数范围。
- 数量、极数、级数等必须为正整数。
- 所有参数是出厂设计值、额定值或铭牌值，不写“实测”。
- 不为缺失物理参数设置默认值，不默认 80%、1 级、1 级泵或最近档。

### 3 结果和追溯

- 缺字段时不要只返回一个空结论；能安全得到的实际输入、计算值、标准候选、阈值、页码和 data_id 必须保留。
- 不要把实际输入、计算值、标准查询值和最终结论混在同一个字段。
- 淘汰设备即使可以继续计算参考能效等级，最终 `conclusion` 仍必须是“淘汰”。
- `actual_metrics` 和 `calculated_metrics` 不应包含猜测值。
- 早退分支不得丢失已经完成的查表证据。

### 4 工程和性能

- 不要运行全量 `unittest discover`、并行测试、PDF 全量渲染或 Excel 压力测试作为普通小任务的顺手验证；此前出现过 CPU 长时间 100%。
- 固定命令必须串行执行；不要同时启动多个构建/测试进程。
- 不要使用 `INDIRECT`、`OFFSET`、整列易失性公式或大范围条件格式。
- 不要用 `git reset --hard`、`git checkout --`、递归删除或覆盖用户文件。
- 代码编辑使用 `apply_patch`，保留现有脏工作区和用户改动。
- 不要把 UI、Excel、Web 逻辑复制到领域评价器。

### 5 Excel 和 V4

- Excel 上传按钮目前是接口预留，不要误以为已经完成读取。
- 不要修改 V4 表头、sheet 数量、公共 15 类、字段 ID 或模板资源。
- 不要在没有重新授权的情况下实现正式批量写回、图片、保护和性能测试。
- 结果文件必须另存，不能覆盖输入工作簿。

## 关键文件和目录

### 1 入口和说明

- `README.md`：项目运行、发布包、模板、JSONL 和验收说明；
- `HANDOFF.md`：本文件，当前统一入口；
- `ROADMAP.md`：V2.3 当前路线入口；
- `docs/28_EquipEffi 后续开发总体路线 V2.3.md`：当前总体路线增量校准；
- `docs/28_EquipEffi 后续开发总体路线 V2.2.md`：V2.3 继承基线；
- `PLATFORM_BASELINE.md` / `platform-lock.json`：Qingzhou-contracts 锁定基线；
- `HANDOFF_20260831.md`：逐任务历史事实和最新第 213 章；
- `docs/27_后续Agent和大模型可直接照做交付清单_v15_20260905.md`：历史执行手册，不再决定当前下一任务；
- `docs/26_多Agent可直接照做交付清单_v14_执行手册_20260905.md`：历史低 CPU 执行流程和停止条件。

### 2 核心代码

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

### 3 标准、模板和目录

- `src/equipeffi/standard_manifest.json`：标准包清单和状态；
- `src/equipeffi/resources/standards/`：机器可读标准数据；
- `src/equipeffi/resources/templates/设备能效分析空白模板_重构版V4_20260825.xlsx`：内置 V4 空白模板；
- `src/equipeffi/resources/templates/README.md`：模板资源说明；
- `src/equipeffi/resources/elimination_catalog_batches_1_4.json`：第一至第四批淘汰目录；
- `src/equipeffi/resources/elimination_catalog_industry_2024.json`：用户提供的产业目录受控子集。

### 4 测试

- `tests/unit/test_device_evaluator_matrix.py`：17 个 profile 的评价矩阵和边界测试；
- `tests/unit/test_evaluation_engine.py`：核心评价服务、淘汰、结果契约；
- `tests/unit/test_v4_validation.py`：V4 输入和自动备注校验；
- `tests/unit/test_v4_input_adapter.py`：V4 字段适配；
- `tests/unit/test_v4_contract_and_facade.py`：V4 合同和公共门面；
- `tests/contract/`：公共类型、架构边界和接口合同；
- `tests/integration/test_workbook_contract.py`：工作簿合同的冻结测试。

## 关键命令

以下命令在 Windows PowerShell、项目根目录运行。必须先设置 `PYTHONPATH`。

### 1 查看状态和运行示例

```powershell
Set-Location '<仓库根目录>'
$env:PYTHONPATH = 'src'
python -m equipeffi --list-device-types
python -m equipeffi --status
python -m equipeffi --web
python -m equipeffi --gui
```

`--gui` 在 Tk 不可用时应回退到 Web；不要把回退提示当成评价失败。

### 2 单条参数评价

```powershell
$env:PYTHONPATH = 'src'
python -m equipeffi --device-type motor --json '{"category":"三相异步电动机","rated_voltage":"0.4","rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}'
```

固定判定基准日期可增加 `--as-of YYYY-MM-DD`。淘汰目录口径可使用 CLI 的 `--elimination-scope`。

### 3 固定轻量回归命令

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

### 4 目标/核心/静态检查

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_device_evaluator_matrix.DeviceEvaluatorMatrixTests.<目标测试> -q
python -m unittest tests.unit.test_device_evaluator_matrix tests.unit.test_evaluation_engine -q
python -m compileall -q src main.py
git diff --check -- . ':(exclude)outputs'
```

不要因为目标测试首次通过就虚构“修复前失败”；如果生产代码本来已满足契约，应如实记录“新增测试首次通过，未修改生产代码”。

### 5 查重和证据

```powershell
rg -n 'T[0-9]{2}\.[0-9]{2}-|目标边界|唯一下一步' HANDOFF_20260831.md docs
rg -n '<任务ID>|<边界关键词>' HANDOFF_20260831.md docs
rg -n 'data_id|source_page|source_clause|match_status' src tests
```

标准值无法从仓库资源或原文可靠确认时，停止并报告证据不足；不要猜数值、不要按趋势修正。

## 交接回报格式

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
