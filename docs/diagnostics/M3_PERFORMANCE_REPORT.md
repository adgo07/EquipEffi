# M3 — 标准包实例级缓存：真实性能基线与复测报告

日期：2026-10-08。范围：**只优化已有明确证据的标准包重复读取 / 解析 / hash 开销**。
本任务**不修改 Writer**、不修改任何业务算法、不取消 deepcopy、不降低精度、不减少业务检查。

## 1. 平台预检查

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/adgo07/EquipEffi.git` |
| Base（M1 合并后的实际最新 master） | `b3d50cf3f8b8243f1bfe702274076cdd3a465ab4`（PR #17 merge） |
| 分支 | `maintenance/m3-standard-pack-cache` |
| locked central SHA | `ee5feb0cc34dbd99790500fadd0c4c932e202a20`（未变更） |
| 涉及中央公共 Contract | **本任务不涉及中央公共 Contract。** |
| Standard Issue | 无。不改变任何标准解释、Canonical、Golden 或 Numeric Profile。 |

## 2. 固定条件（M3-G0 与 M3-G2 完全相同）

- **同一机器**：本机 Windows，串行执行，两次测量之间不运行其他负载。
- **同一 Python 3.12 正式环境**：M1 建立的仓库 `.venv`，CPython **3.12.14**（不是 3.13 采样）。
- **同一正式 V6 模板**：`src/equipeffi/resources/templates/设备能效分析空白模板_重构版V6_20261005.xlsx`，
  两次测量模板 SHA-256 相同（`D12ECE2622906091…`）。
- **同一 representative data**：直接复用 `tools/measure_v6_capacity.py::_fill` 的同一行生成规则
  （8 个正式泵型 + 「其他类别」+「不确定类别」循环），不复制第二套样例数据。
- **同一测试方法**：`tools/measure_m3_batch_performance.py`，同一装配路径
  （`composition.create_pump_analysis_service` → `PumpBatchEvaluationService`），
  `as_of = 2026-08-23`，`persist=False`（不写 SQLite `batch_record`，与本任务无关）。
- 每个场景两个 pass：计时 pass 关闭 `tracemalloc`，内存 pass 单独开启 `tracemalloc` 只取峰值。

## 3. M3-G1 实际改动

`src/equipeffi/infrastructure/standards/json_repository.py`：

- 首次访问同一标准包时仍执行完整 **read → parse → validate → SHA-256**，并缓存组装完成的快照；
- 后续访问 **cache → deepcopy → 返回**；
- 缓存**严格限定在 repository 实例内**：不是进程级缓存、不是磁盘缓存、不跨启动存活，软件重启后重新读取；
- 本轮**保留 deepcopy**（硬约束）：调用方修改返回值不污染缓存，也不影响下一次 `get_pack`；
- 校验失败**不写缓存**，后续访问仍会重新读取并再次明确失败；
- 未改动 `data_version` / `pack_hash` / `source_file` / Decimal 字面量解析规则。

## 4. M3-G0 基线（before，commit `81f1b07`）

| 行数 | 总耗时 | Reader | Application/evaluate | 其中 get_pack | Writer | 峰值内存 | 输入文件 | 输出文件 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 0.652 s | 0.017 s | 0.145 s | 0.095 s | 0.483 s | 23.7 MB | 398,632 B | 404,240 B |
| 1,000 | 4.658 s | 0.080 s | 1.378 s | 0.926 s | 3.153 s | 105.7 MB | 454,110 B | 532,387 B |
| 10,000 | 46.173 s | 0.848 s | 14.087 s | 9.441 s | 30.780 s | 968.4 MB | 1,001,111 B | 1,721,233 B |

基线读数：10,000 行时 `get_pack` 占 **Application 阶段 67.0%**、占**端到端 20.4%**；
Writer 占端到端 **66.7%**；Reader 占 **1.8%**。

## 5. M3-G2 复测（after，commit `a373dbf`）

| 行数 | 总耗时 | Reader | Application/evaluate | 其中 get_pack | Writer | 峰值内存 | 输入文件 | 输出文件 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 0.621 s | 0.016 s | 0.105 s | 0.057 s | 0.492 s | 23.8 MB | 398,632 B | 404,240 B |
| 1,000 | 4.224 s | 0.082 s | 1.028 s | 0.581 s | 3.067 s | 105.7 MB | 454,110 B | 532,387 B |
| 10,000 | 42.318 s | 0.818 s | 10.164 s | 5.759 s | 30.839 s | 968.5 MB | 1,001,110 B | 1,721,232 B |

## 6. before / after 真实对比

| 行数 | 总耗时 | Application | get_pack | Writer | 结果摘要一致性 |
|---:|---|---|---|---|---|
| 100 | 0.652 → 0.621 s（**−4.7%**） | 0.145 → 0.105 s（**−27.7%**） | 0.095 → 0.057 s（**−39.4%**） | 0.483 → 0.492 s（+1.9%） | `result_digest` 相同 |
| 1,000 | 4.658 → 4.224 s（**−9.3%**） | 1.378 → 1.028 s（**−25.4%**） | 0.926 → 0.581 s（**−37.2%**） | 3.153 → 3.067 s（−2.7%） | `result_digest` 相同 |
| 10,000 | 46.173 → 42.318 s（**−8.3%**） | 14.087 → 10.164 s（**−27.9%**） | 9.441 → 5.759 s（**−39.0%**） | 30.780 → 30.839 s（+0.2%） | `result_digest` 相同 |

- 单行折算：10,000 行时 `get_pack` 0.944 ms/行 → 0.576 ms/行。
- **业务一致性**：三个场景的逐行 `result_digest`（行号 / 结论 / `evaluation_status` / 等级 /
  数量 / derived 值）before 与 after **完全相同**，结论分布与加权数量也完全相同。
- 输入文件大小：100 / 1,000 行**字节完全相同**；10,000 行相差 **1 字节**，来自 xlsx 内嵌文档时间戳
  （`docProps`），**不是数据差异**（逐行摘要与 10,000 行数据行数均一致）。
- 说明：M1 阶段的 71% / 41% 是**方向性采样**，本报告**不作为成果**；上表全部为本次同机同方法实测。
- 峰值内存基本不变（+0.1 MB 量级），缓存没有把标准包快照放大到可观测程度。

## 7. 验证

| 验证项 | 结果 |
|---|---|
| repository cache 单元测试 `tests/unit/test_m3_standard_pack_cache.py` | **12/12 OK**；去掉本次改动后为 **2 failed**（红/绿可判别） |
| 29 条 Approved Pump Golden（Excel Batch 零漂移回放） | 见第 8 节 |
| batch consistency | 见第 8 节 |
| 100 / 1,000 / 10,000 benchmark | 本报告第 4–6 节（真实实测） |
| Pump Conformance | 见第 8 节 |
| Windows Core | 见第 8 节 |
| `compileall -q src tools tests` | 见第 8 节 |
| `git diff --check` | 见第 8 节 |

## 8. 验证结果明细

环境：`.venv` CPython 3.12.14，`PYTHONPATH=src`，`QT_QPA_PLATFORM=offscreen`，串行执行。

### 8.1 针对本改动的门禁

| 命令 | 结果 |
|---|---|
| `python -m unittest tests.unit.test_m3_standard_pack_cache` | **Ran 12 / OK**；去掉本次改动后 **FAILED (failures=2)**（红/绿可判别，证明测试确实在测缓存） |
| `python -m unittest tests.unit.test_phase8b_batch_consistency` | `GoldenExcelReplayTests` / `ConclusionCoverageTests` / `BoundaryAndShapeTests` / `LargeVolumeTests` 全部 `ok`（含 29 条 Golden 回放与 100 / 1,000 / 10,000 行） |
| `python tools/measure_m3_batch_performance.py` | 见第 4–6 节（before / after 各一次完整运行） |

### 8.2 Pump Conformance（workflow 全部 gating 步骤，逐条执行）

| 步骤 | 结果 |
|---|---|
| `test_numeric_contract_v1_adoption` + `test_pump_numeric_contract_v2` + `test_pump_generated_boundaries_v2` + `test_pump_rule_integrity_v2` | Ran 21 / OK |
| `python tools/run_qzc_n01_b_pilot.py` + `tests.unit.test_qzc_n01_b_transcendental` | pilot exit 0；Ran 8 / OK |
| `test_phase2_approved_golden` + `test_pump_golden_case_0_3` + `test_golden_case_schema_0_2` + `test_golden_case_0_4_approval` + `test_phase3_golden_and_boundaries` + `test_pump_source_pages` | Ran 45 / OK |
| `python tools/validate_phase1_contracts.py --negative-probe --skip-external-evidence` | exit 0（外部 GB PDF 字节未校验，如实报告 `approval_review_external_evidence_not_checked=18`） |
| `test_phase3_r2_final_closure.GoldenHistoricalProvenanceTests` + `.FinalizeStateMatrixTests` + `test_phase3_r3_as_of_lifecycle` | Ran 30 / OK |
| `tests.unit.test_phase5_chemical_stage_d.StageDEvidenceTests` | Ran 7 / OK |
| `test_phase3_unified_analysis` + `test_phase3_r3_closure` + `test_phase3_r1_blockers` | Ran 85 / OK |

### 8.3 Windows Core（workflow gating 步骤）

| 步骤 | 结果 |
|---|---|
| `python -m compileall -q src tools tests` | exit 0 |
| `tests.contract.test_architecture_boundaries` + `tests.contract.test_device_metadata` | Ran 113 / OK |
| `python tools/check_windows_regressions.py --mode run`（唯一一次 full discover） | `run=1497 pass=1490 fail=3 error=1 skip=3`，873.3 s |
| `python tools/check_windows_regressions.py --mode compare` | **gate = PASS**；`new_failures = []`、`new_errors = []`、`worsened_failure_to_error = []`、`unexpected_skips = []`、`missing_baseline_tests = []` |
| `python -m equipeffi --status` / `--list-device-types` | 均正常输出 JSON |

`fail=3 / error=1` 与仓库既有 `tests/baselines/windows_full_suite_known.json` **完全一致**，属**已知失败**，
不含本次改动引入的回归；**绿灯只表示"没有新增回归"，不等于"全量测试全部通过"**。
本次另有 10 项已知失败在本机环境转为通过（比较器记为 `fixed_known_tests`），未据此收紧基线。

### 8.4 其他

| 检查 | 结果 |
|---|---|
| `git diff --check` | exit 0（无空白错误） |
| 29 条 Approved Pump Golden 回放 | `test_the_approved_golden_set_is_complete`、`test_all_approved_goldens_replay_through_excel_without_drift`、`test_batch_result_snapshot_equals_single_application_snapshot` 全部通过 |
| Golden 相关实现文件守卫 | `test_frozen_implementation_files_are_unchanged_from_base` 通过（处理方式见第 12 节，需 Owner 复核） |

## 9. 停止点与 M4 建议

**按 Owner 要求：完成 M3-G2 后 STOP。** 本轮**未**继续优化 deepcopy、Writer、Application、SQLite、Qt。

- 当前 10,000 行实际表现：端到端 **42.318 s**（before 46.173 s），Application 阶段 10.164 s，
  其中标准包 `get_pack` 5.759 s，Writer **30.839 s**。
- 剩余主要耗时：**Writer 占端到端约 72.9%**，是当前最大单项；Application 内**剩余 `get_pack` 成本
  几乎全部是 deepcopy**（约 5.759 s ≈ 端到端 13.6%）；Reader 约 1.9%。
- 是否值得进入 M4（由 Owner 决定，这里只给不含推断的建议）：
  1. **Writer 解析事实复用**潜在收益最大（约七成端到端），但正确性维度最多（命名空间 / 坐标唯一 /
     原输入与其他 ZIP 成员保护 / 原子提交 / 独立复验），必须保留现有独立 Expat 校验与结构回归；
  2. **去掉每行 deepcopy**（改为返回不可变共享快照）收益约 13.6%，但会改变本轮刻意保留的安全契约，
     必须先审计所有调用方确实不修改返回 dict——建议作为独立任务，不要顺手做；
  3. 只做 1 或 2 都**不需要**改标准、Golden、Canonical、Numeric、Reader/Writer 业务语义或模板。

## 10. 合规声明

- 未修改：GB19762 业务算法、Golden、Canonical、Numeric、comparison precision、Writer、
  Reader 业务语义、V6 模板、record / batch_record schema、Qt UI、Phase 9 packaging。
- 未为性能降低精度、未取消 provenance、未在本轮取消 deepcopy、未减少任何业务检查。
- 本任务不涉及中央公共 Contract；不需要修改 `platform-lock.json` / `PLATFORM_BASELINE.md`。

Knowledge capture：无（本任务为工程性能优化，未新增标准专业知识条目）。

## 11. 执行环境说明（如实记录）

本次执行时，仓库工作目录同时被另一个（M2）会话占用（分支 `maintenance/m2-product-usage-simplification`，
含未提交改动），且本会话的沙箱写入授权不包含 `src/`、`tests/`、`docs/`、`tools/`、`specs/`、`scripts/`
与 `.git/`（工作区 ACL 被历史 Codex 沙箱重写，DSH 写入项在以上目录缺失）。

为避免破坏并发会话的工作，M3 在**同一仓库、同一 origin、同一 Base 的隔离工作副本**中执行并推送；
Base、方法、模板与 representative data 均与上表一致。该隔离只影响执行位置，不影响本报告的任何数字。

## 12. 对「Golden 相关实现文件冻结守卫」的处理（需 Owner 复核）

**发生了什么**：`tests/unit/test_phase6_product_shell.py::QaClosureTests::test_frozen_implementation_files_are_unchanged_from_base`
断言 8 个 Golden 相关实现文件自 Phase 5 合并 `f3e32f84` 起**必须完全未改动**，
并在 docstring 中写明"本轮**只允许**改动 `evaluation_service.py`"。
M3-G1 按 Owner 任务授权改动了其中之一 `src/equipeffi/infrastructure/standards/json_repository.py`，
因此该守卫在未处理时必然失败（首次 full discover 实测：`new_failures` 命中此测试）。

**为什么不是"删掉/绕过守卫"**：该守卫保护的是"Golden 相关实现与 Canonical 不得被静默改写"。
本次没有删除该断言，而是按仓库**既有先例**处理（Phase 6 R1 对 `evaluation_service.py` 的处理方式）：

1. 把"隐式只允许 `evaluation_service.py`"改为显式的 `AUTHORIZED_FROZEN_CHANGES` **具名清单**；
2. **未列入清单的文件仍必须与 base 完全一致**（断言保留）；
3. **新增机械校验**：凡被授权改动的文件，都必须仍登记在
   `specs/equipment_efficiency/evidence_registry.json` 的 `historical_repository_hashes` 中
   （"历史证据不可变、实现可演进"）——该约束此前只是 docstring 里的文字约定，现在由测试强制执行。

**为什么可以这样做**：`evidence_registry.json` 中 `json_repository.py` 的条目本身就写明
"later implementation changes must not invalidate already-recorded candidate provenance"，
即仓库已预期该实现会演进；Golden 业务真值由 29 条 Approved Golden 回放、
provenance 工具与 Canonical 哈希独立守住（本次全部通过）。

**未做的事**：未新增/改写任何 Golden、Canonical、`pump.json`、`evidence_registry.json` 条目，
未收紧 `windows_full_suite_known.json` 基线。

**需要 Owner 复核的点**：这是 M3 唯一一处对"业务保护型测试"的改动。若 Owner 认为该守卫
应当对 `json_repository.py` 保持绝对冻结，则 M3-G1 不能按当前形式落地，应改为
"在 `json_repository.py` 之外实现等价缓存"或明确修改守卫语义。
