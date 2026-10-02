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

## 长期操作参考

原属本文件第 7～10 节的操作性内容（**已踩过的坑：不要重复**、**关键文件和目录**、**关键命令**、**交接回报格式**）已拆出到 [docs/DEVELOPMENT_REFERENCE.md](docs/DEVELOPMENT_REFERENCE.md)，以免随历史正文一并丢失。该文件是长期参考，不承载“当前状态”。

## Historical evidence 链接

以下文件承载历史事实（Phase 0 结论、Phase 1 Goal Log 与验收复验、Phase 1 Verification Evidence、Phase 0 事实摘要、QZC-A01 接入、Roadmap V2.3 Alignment、P1-SR01 等），**本文件不再复制其正文**：

- [ROADMAP.md](ROADMAP.md) 第 7 节 Historical 入口
- [docs/governance/](docs/governance/) — 各阶段执行/接入/收口报告
- [HANDOFF_20260831.md](HANDOFF_20260831.md) — 逐任务历史事实（第 213 章及以前）
- [PUMP_V2_G04_APPROVAL_MANIFEST.md](PUMP_V2_G04_APPROVAL_MANIFEST.md)、[PUMP_V2_R01_R06_COMMIT_MANIFEST.md](PUMP_V2_R01_R06_COMMIT_MANIFEST.md)、[PUMP_V2_R07_COMMIT_MANIFEST.md](PUMP_V2_R07_COMMIT_MANIFEST.md)
- [QZC_N01_B_EXECUTION_REPORT.md](QZC_N01_B_EXECUTION_REPORT.md)（`HISTORICAL-SUPERSEDED`）
- `docs/23～docs/27` 编号执行清单（`HISTORICAL`）
