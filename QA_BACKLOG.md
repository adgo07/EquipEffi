# EquipEffi QA_BACKLOG

**状态：** `Phase 1 = PASS`（18 条 `pump_water` Golden 0.4 已具名批准，Phase 1 Exit Gate 已满足）；**当前开放的 QA 条目不追溯性地阻塞 Phase 1**，按各条目的 `target_phase` / 发布门禁处理。Phase 0B = `NOT_EXECUTED`；未批准 Phase 1 Hotfix。
**来源：** v7–v15 / T04.xx 历史材料、第三方 `docs/重构问题清单_20260921.csv` 的 55 项、Phase 0 重跑和资产审计。

## 字段规则

- `P0/P1/P2/OBSOLETE` 是业务/发布风险，不是第三方代码审计的“高/中/低”的直接翻译。
- `P0` 只表示可能影响业务结论、数据安全或发布门禁；未标为 `CONFIRMED` 的 P0 仍需标准/Golden 证据。
- `EVIDENCE` 只用于第三方第 55 项“已有回归基线”这一正向事实，不表示缺陷。
- 发布表面：`V1_RUNTIME`、`DEV_ONLY`、`PROTOTYPE`、`LEGACY`、`NOT_SHIPPED`。
- 本阶段所有 `OPEN`、`VERIFY`、`DEFERRED` 项均不自动授权代码修改。

## Phase 0 当前发现

| issue_id | legacy_id/audit_id | profile_id | location | description | business_risk | engineering_risk | release_surface | classification | target_phase | status | evidence | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QA-P0-001 | BASELINE-TEST-001 | motor_lv | `tests/unit/test_v4_reader.py::test_copied_v4_row_is_read_and_evaluated` | 7.5 kW 电机 V4 行期望 `1级`，实际 `无法判定` | 可能错误结论 | H | NOT_SHIPPED | P0 | VERIFY_BEFORE_PHASE9 | OPEN | Python 3.13 全量重跑 | 先核对标准日期、输入映射和 fixture；不在 0A 修；<br>**Phase 8 disposition review（2026-10-07）**：→ VERIFY_BEFORE_PHASE9——V4 motor reader 可能错误结论；表面 NOT_SHIPPED 但 CLI `--v4-sheet` 可达，须先决定「修复 or 明确不发布」 |
| QA-P0-002 | BASELINE-TEST-002 | motor_lv | `tests/unit/test_v4_writer.py` 两个结果写回测试 | V4 写回的等级/三个等级指标为空或为 `无法判定` | 可能错误结论 | H | NOT_SHIPPED | P0 | VERIFY_BEFORE_PHASE9 | OPEN | Python 3.13 全量重跑 | V4 为冻结端口；进入发布前必须关闭或有明确不发布决策；<br>**Phase 8 disposition review（2026-10-07）**：→ VERIFY_BEFORE_PHASE9——同上（V4 writer 结果写回）；属发布前须有结论项 |
| QA-P1-003 | BASELINE-TEST-003 | shared | `tests/unit/test_release_audit.py` | Release audit 结果缺少 `wheel_pmsm_status` 键 | 影响发布审计完整性，不直接改变评价结论 | M | DEV_ONLY | P1 | Phase 9 | OPEN | Python 3.13 全量重跑 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：先修复审计契约/fixture，再作为发布门禁；<br>**Phase 8 disposition review（2026-10-07）**：→ Phase 9——发布审计完整性（`wheel_pmsm_status` 键缺失）属发布前门禁 |
| QA-P1-004 | BASELINE-TEST-004 | shared | `.venv_build` | 3.11 构建环境缺 `openpyxl`、`python-docx`、`pytest`，导致 10 error | 结果不可完整复验 | M | DEV_ONLY | P1 | Phase 0 follow-up | EVIDENCE | BASELINE.md | 保留完整 Python 3.13 结果；不把缺依赖误报为源码 PASS |
| QA-P1-005 | BASELINE-TEST-005 | shared | tests inventory | 历史审计声称 60 个真实 unittest；Phase 0 实测 54 个 test module、887 项 unittest | 治理数字漂移 | M | DEV_ONLY | P1 | Future | OPEN | 第三方 #55 + unittest | 以可重跑命令和本次数字为当前事实，历史数字仅作 Historical Evidence；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——治理数字漂移（历史审计 60 vs 实测）；当前计数已由可重跑命令 + known-regression 比较常设化 |
| QA-P1-006 | BASELINE-SMOKE-001 | shared | `standard_manifest.json` / resource packs | 17 pack 报告 `active`，但 active 不等于来源/边界/Golden 已验收 | 可能把可加载误认为业务可信 | M | V1_RUNTIME | P1 | Future | OPEN | status smoke + ASSET_AUDIT | Phase 1 逐 pack 冻结 Canonical/source/readiness；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——17 pack 的 `active` ≠ 已验收；正式 Qt 仅提供离心泵链，其余标准包属后续标准扩展 |
| QA-P1-007 | BASELINE-PERF-001 | shared | `JsonStandardRepository.get_pack` | 同一 pack 重复读取仍 read_text + json.loads + deepcopy | 性能退化，不直接改结论 | M | V1_RUNTIME | P1 | Future | OPEN | 3.225 ms 首读；1.947 ms 重读 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：Phase 0 只记录，不缓存重构 |

## 历史路线入库

| issue_id | legacy_id/audit_id | profile_id | location | description | business_risk | engineering_risk | release_surface | classification | target_phase | status | evidence | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QA-LEGACY-001 | v7-v15 | shared | `docs/` 编号执行清单、历史 HANDOFF | 编号执行清单和复制型手册曾拥有下一任务调度权 | 治理调度歧义 | M | LEGACY | OBSOLETE | Phase 0 | MAPPED | ROADMAP.md；历史文件清单 | 事实保留；统一标记 `HISTORICAL / NOT AUTHORITATIVE FOR NEXT TASK` |
| QA-LEGACY-002 | T04.xx | shared | T04.xx 历史路线文件 | 旧路线边界任务继续自动领取的风险 | 治理调度歧义 | M | LEGACY | OBSOLETE | Phase 0 | MAPPED | ROADMAP.md；旧路线入口 | V2.2 已正式终止自动执行权 |
| QA-LEGACY-003 | HANDOFF_20260831 / 历史摘要 | shared | 历史 HANDOFF、摘要和测试报告 | 852、323、126 等历史测试数字可能被误当当前结果 | 验收证据漂移 | M | LEGACY | P1 | Phase 0 | MAPPED | BASELINE.md；历史数字来源待逐项复核 | 仅保留为 Historical Evidence；当前数字以 BASELINE 为准 |
| QA-LEGACY-004 | 历史 evaluator backlog | all | 历史 evaluator backlog；具体条目位置 `UNKNOWN / NEEDS_EVIDENCE` | 旧问题未按业务风险、工程风险和 release surface 分层 | 风险优先级不清 | M | LEGACY | P1 | Phase 0 | MAPPED | ASSET_AUDIT.md、QA_BACKLOG.md | 已由本表和第三方 55 项统一收口 |

## 第三方 55 项逐项登记

| issue_id | legacy_id/audit_id | profile_id | location | description | business_risk | engineering_risk | release_surface | classification | target_phase | status | evidence | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QA-AUD-001 | AUD-001 | shared | `domain/devices/` | 8 个空壳与 `domain/evaluation` 并存；误认第二正式实现 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Future | OPEN | CSV#1 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：标为 DELETE_CANDIDATE，先完成动态/构建/外部契约证明 |
| QA-AUD-002 | AUD-002 | shared | `device_evaluators.py` + evaluators | 兼容门面与延迟反向导入；维护变化可能影响评价 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Future | OPEN | CSV#2 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：当前仍是运行依赖，禁止 0A 删除 |
| QA-AUD-003 | AUD-003 | motor | `evaluators/motor.py` | 字符串 `getattr` 动态 helper；改名可能静默失效 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Future | OPEN | CSV#3 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：改为静态契约前保留回归 |
| QA-AUD-004 | AUD-004 | shared | `evaluation_engine.py` | `inspect.signature` 兼容 2/3 参数掩盖契约错误 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | SUPERSEDED | OPEN | CSV#4 | DEFER_TO_P4：真实样板后再通用化；不在薄壳阶段重构业务；原决定：唯一 evaluate 契约留 Phase 2；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ SUPERSEDED——`evaluation_engine.py` 在 `src/` 内 **0 入边引用**（已无调用方） |
| QA-AUD-005 | AUD-005 | shared | `device_types.py` | 15 公共类型、17 Profile 和旧 fan 入口并存；路由理解成本高 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future | OPEN | CSV#5 | DEFER_TO_P3：非 settings 切片，保持既有风险与证据；原决定：Phase 0 已确认映射权威，暂不合并；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——`device_types.py` 路由可读性 / 理解成本，结构债务，无错误结论证据 |
| QA-AUD-006 | AUD-006 | shared | `domain/common/models.py` | `EvaluationResult` 混合结果、轨迹、淘汰和质量 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future | OPEN | CSV#6 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：保持现有契约，未来按职责拆分；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——正式链已改用专用契约 `PumpAnalysisResult`；旧 `EvaluationResult` 职责拆分属重构 |
| QA-AUD-007 | AUD-007 | shared | `metadata.py` | 1687 行混合枚举、V4 映射、展示和 profile 构建 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future | OPEN | CSV#7 | DEFER_TO_P4：非 settings 切片，保持既有风险与证据；原决定：已在 ASSET_AUDIT 完成职责分类，暂不迁移；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——`metadata.py` 体积与职责混合，结构债务 |
| QA-AUD-008 | AUD-008 | shared | `device_specs.py:179-188` | 导入时就地修改 `DEVICE_SPECS` | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future | OPEN | CSV#8 | DEFER_TO_P4：真实样板后再通用化；不在薄壳阶段重构业务；原决定：记录为导入副作用，不在 0A 重写；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——`device_specs.py` 导入副作用，结构债务 |
| QA-AUD-009 | AUD-009 | all | `device_specs.py`、`metadata.py`、`entrypoint.py` | 标准/字段/示例硬编码多份，可能产生数据漂移 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future | OPEN | CSV#9 | DEFER_TO_P3：非 settings 切片，保持既有风险与证据；原决定：Python 数据先盘点，不能直接删除；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——标准 / 字段 / 示例数据多份硬编码；正式标准事实以 Canonical 为准，属数据卫生治理 |
| QA-AUD-010 | AUD-010 | shared | `evaluators/shared.py:_interval_hit` | 核心区间解析难验证，边界错误可能给错结论 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | VERIFY_BEFORE_PHASE9 | VERIFY | CSV#10 + source；Phase 1 已执行 12 个开闭端点 probe，全部符合预期 | Phase 1 review=`NEEDS_MORE_EVIDENCE`；现有 probe 未发现错误，但尚缺跨标准/Golden 的完整覆盖；不进入 Hotfix；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ VERIFY_BEFORE_PHASE9——`evaluators/shared.py` 区间判定位于业务判定链，边界错误可能给错结论；P0 且尚未证明安全 |
| QA-AUD-011 | AUD-011 | shared | `v4_validation.py` / `input_normalization.py` | 规范化重复实现，差异可能改变输入含义 | 可能影响业务结论；需标准/Golden 证据 | H | NOT_SHIPPED | P0 | POST_V1 | VERIFY | CSV#11；pump_water 的完整别名与 canonical 输入输出一致，V4 validation valid/invalid probe 有预期结果 | DEFER_TO_P8：非 settings 切片，保持既有风险与证据；原决定：Phase 1 review=`NEEDS_MORE_EVIDENCE`；样板证据不能代表全 Profile 的共享风险；不重构；<br>**Phase 8 disposition review（2026-10-07）**：→ POST_V1——重复实现只在非正式 V4 / legacy API 链（正式 Qt 分析页不经 `schema_constraints`） |
| QA-AUD-012 | AUD-012 | shared | `evaluation_service.py:148-426` | 279 行上帝方法，门禁分支难审计 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | POST_V1 | OPEN | CSV#12 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：结构债务，不因严重度直接 Hotfix；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——`evaluation_service.py` 上帝方法属 legacy 服务；正式 Qt 链不经该实现 |
| QA-AUD-013 | AUD-013 | shared | `v4_validation.py` | 882 行、多 sheet 特例链，新增规则易漏 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | POST_V1 | OPEN | CSV#13 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：Import Contract 冻结后拆分；<br>**Phase 8 disposition review（2026-10-07）**：→ POST_V1——`v4_validation` 属 V4 / legacy adapter 链 |
| QA-AUD-014 | AUD-014 | shared | `input_normalization.py` | 226 行、16 类转换硬编码，输入错误风险 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | POST_V1 | OPEN | CSV#14 | DEFER_TO_P8：非 settings 切片，保持既有风险与证据；原决定：先建立 Product/Profile Schema；<br>**Phase 8 disposition review（2026-10-07）**：→ POST_V1——`input_normalization` 属 V4 / legacy adapter 链 |
| QA-AUD-015 | AUD-015 | shared | `application_api.py` / `main_window.py` | fallback 表单构建重复，UI 可能与 API 不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | H | PROTOTYPE | P2 | POST_V1 | OPEN | CSV#15 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：暂由 `metadata_projection` 共享，UI 非 V1 门禁；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——legacy API / 桌面 fallback 表单重复；`metadata_projection` 只被 legacy 两处引用，Qt 不使用 |
| QA-AUD-016 | AUD-016 | shared | 多处 conclusion label | 同一结论列标题重复，展示可能漂移 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | POST_V1 | OPEN | CSV#16 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：Presentation 清理阶段处理；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——结论列标题重复属 legacy 展示面 |
| QA-AUD-017 | AUD-017 | shared | `application_api.py` / `main_window.py` | 基础信息字段元组重复 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | POST_V1 | OPEN | CSV#17 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：不影响当前核心评价；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——基础信息字段元组重复属 legacy 展示面 |
| QA-AUD-018 | AUD-018 | shared | `main_window.py` / `web/server.py` | 结果摘要 Python/JS 重复，说明可能不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | POST_V1 | OPEN | CSV#18 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：API 摘要结构化后处理；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——Python / JS 结果摘要重复属 legacy Web 面 |
| QA-AUD-019 | AUD-019 | shared | `infrastructure/excel/v4_writer.py` | 完整 writer 生产链 0 引用，V4 结果可能无法交付 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | POST_V1 | OPEN | CSV#19 + QA-P0-002 | V4 未纳入当前首发，不接线；<br>**Phase 8 disposition review（2026-10-07）**：→ POST_V1——`v4_writer` 0 入边引用；正式写回由 `pump_result_writer` 承担 |
| QA-AUD-020 | AUD-020 | shared | `excel/legacy_*`、`report_exporter.py`、`template_builder.py` | 4 个 FeatureNotEnabled 空桩，制造能力错觉 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | SUPERSEDED | OPEN | CSV#20 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：DELETE_CANDIDATE，先查契约/构建/测试；<br>**Phase 8 disposition review（2026-10-07）**：→ SUPERSEDED——4 个 FeatureNotEnabled 空桩 0 引用；正式的 Excel 能力已由 Phase 8 V6 批量链提供 |
| QA-AUD-021 | AUD-021 | shared | `strict_importer.py` | 3 行别名子类无 runtime 引用 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Future | OPEN | CSV#21 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：暂保兼容名，后续统一；<br>**Phase 8 disposition review（2026-10-07）**：→ Future——`strict_importer` 死别名，无任何入边引用 |
| QA-AUD-022 | AUD-022 | shared | SQLite repositories | 两个空桩仓储，实际持久化不存在 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | SUPERSEDED | OPEN | CSV#22 + ADR-005 | PARTIAL_IN_P2：旧 SQLite 空桩已明确 DEPRECATED / NOT_SHIPPED / NOT_WIRED；新 settings 独立接线，业务仓储留 Phase 3；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ SUPERSEDED——`sqlite_repository` / `sqlite_project_repository` **0 入边引用**，`test_disabled_adapters` 机械断言其 disabled |
| QA-AUD-023 | AUD-023 | shared | `cleaning_service.py` / `import_service.py` | 0 引用服务，可能是未完成能力或死代码 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Future | OPEN | CSV#23 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：DELETE_CANDIDATE，先查外部契约 |
| QA-AUD-024 | AUD-024 | shared | `application/ports/*.py` | Protocol 0 引用，实际实现未显式接入 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future | OPEN | CSV#24 | PARTIAL_IN_P2：仅完成 settings 端口/存储；原业务仓储与其他端口仍开放；原决定：保留契约方向，阶段性补接线；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——ports 已由正式批量链接入（`pump_workbook_reader` / `pump_result_writer`）；其余端口悬空属结构清理 |
| QA-AUD-025 | AUD-025 | shared | `v4_template_audit.py` / `config/settings.py` | 0 引用包装和默认设置 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Future | OPEN | CSV#25 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：不影响 V1，删除前做动态引用检查 |
| QA-AUD-026 | AUD-026 | shared | `v4_input_adapter.py` | `adapt_many`、`validate_draft` 未接线 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | POST_V1 | OPEN | CSV#26 | DEFER_TO_P8：非 settings 切片，保持既有风险与证据；原决定：Import Contract 确认后接入或删除；<br>**Phase 8 disposition review（2026-10-07）**：→ POST_V1——`v4_input_adapter` 未接线方法属 V4 adapter |
| QA-AUD-027 | AUD-027 | shared | OOXML 解析三处 | sheet 名和 rels 解析重复，修复容易不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | POST_V1 | OPEN | CSV#27 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：不在冻结 V4 端口中重构；<br>**Phase 8 disposition review（2026-10-07）**：→ POST_V1——正式链只用 `ooxml_reader`；重复落在 legacy `v4_reader` / `v4_template_audit` |
| QA-AUD-028 | AUD-028 | shared | `ooxml_reader.py` / `v4_writer.py` | 列号互换换算重复 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | POST_V1 | OPEN | CSV#28 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：归入 OOXML 工具清理；<br>**Phase 8 disposition review（2026-10-07）**：→ POST_V1——同 027（`ooxml_reader` 与 `v4_writer` 列号换算重复） |
| QA-AUD-029 | AUD-029 | shared | `template_resource.py` / `v4_template_contract.py` | 模板名、sheet 清单和说明重复配置 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 9 | OPEN | CSV#29 | DEFER_TO_P8：非 settings 切片，保持既有风险与证据；原决定：Import Contract 单一来源；<br>**Phase 8 disposition review（2026-10-07）**：→ Phase 9——模板/设备 sheet 配置同时被正式 `template_resource` 与发布审计 `v4_template_contract` 持有，漂移直接影响发布审计 |
| QA-AUD-030 | AUD-030 | shared | `v4_validation.py` | 手工规则表和 metadata 派生规则双真相源 | 可能影响业务结论；需标准/Golden 证据 | M | NOT_SHIPPED | P0 | POST_V1 | VERIFY | CSV#30；pump_water 元数据字段约束与 V4 valid/zero/fraction/percent probes 未发现当前输入差异 | Phase 1 review=`NEEDS_MORE_EVIDENCE`；样板路径未证明全 Profile 无差异；待 Import/Profile 矩阵；未授权 Hotfix；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——双真相源的另一半 `v4_validation.py` 属 V4 / 非正式链 |
| QA-AUD-031 | AUD-031 | shared | 多处默认判定日期 | 日期硬编码可能选错标准生效状态 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | SUPERSEDED | VERIFY | CSV#31；default/explicit `2026-08-23` 一致，`2026-02-28` 与 `2026-03-01` 明确跨过实施日期 | DEFER_TO_P3：非 settings 切片，保持既有风险与证据；原决定：Phase 1 review=`NEEDS_MORE_EVIDENCE`；Golden 已显式填写 `as_of`，但默认日期是否允许仍需产品/业务决策；不改实现；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ SUPERSEDED——Owner 决定（2026-10-02，Phase 5 / 7 收口）：评价日期不是业务门禁，不改变等级 / `evaluation_status`；正式路径自动取本机当天 |
| QA-AUD-032 | AUD-032 | shared | `__init__.py`、`pyproject.toml`、`build_msi.py` | 版本号 0.2.1 多处硬编码，追溯可能漂移 | 当前未确认影响 V1 业务结论；维护风险待证 | M | DEV_ONLY | P2 | Future | OPEN | CSV#32 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：版本模型由 ADR-003 进入 Phase 1 |
| QA-AUD-033 | AUD-033 | shared | `main_window.py:339` | UI 写死公共类型数量 15 | 当前未确认影响 V1 业务结论；维护风险待证 | L | PROTOTYPE | P2 | Future | OPEN | CSV#33 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：非业务结论问题 |
| QA-AUD-034 | AUD-034 | shared | `application/bootstrap.py` | Application 直接导入 infrastructure | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | CLOSED | CSV#34；Phase 2 AST / test_composition / test_phase2_logging / test_phase2_qt 实测通过 | CLOSE_IN_P2：按 docs/31 实施；对应测试已通过，CLOSED（工程项，不表示 Phase 2 PASS）；原决定：装配方向重做时处理 |
| QA-AUD-035 | AUD-035 | shared | `application/bootstrap.py` / API | Application 反向导入 Presentation，包级环 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | CLOSED | CSV#35；Phase 2 AST / test_composition / test_phase2_logging / test_phase2_qt 实测通过 | CLOSE_IN_P2：按 docs/31 实施；对应测试已通过，CLOSED（工程项，不表示 Phase 2 PASS）；原决定：不在 Phase 0 改结构 |
| QA-AUD-036 | AUD-036 | shared | `bootstrap.load_v4_contract` | `except Exception` 静默降级，模板损坏难诊断 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 2 | CLOSED | CSV#36；Phase 2 AST / test_composition / test_phase2_logging / test_phase2_qt 实测通过 | CLOSE_IN_P2：按 docs/31 实施；对应测试已通过，CLOSED（工程项，不表示 Phase 2 PASS）；原决定：V4 发布前必须限定异常并记录 |
| QA-AUD-037 | AUD-037 | shared | `config/logging.py` | 日志占位，关键路径无可用日志 | 可能影响发布可靠性或长期维护；业务影响待证 | M | DEV_ONLY | P1 | Phase 2 | CLOSED | CSV#37；Phase 2 AST / test_composition / test_phase2_logging / test_phase2_qt 实测通过 | CLOSE_IN_P2：按 docs/31 实施；对应测试已通过，CLOSED（工程项，不表示 Phase 2 PASS）；原决定：安全/发布阶段补齐 |
| QA-AUD-038 | AUD-038 | shared | writer / JSON repository | 损坏文件异常根因可能丢失 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future | OPEN | CSV#38 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：统一异常模型，保留根因；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——损坏文件异常根因保留属诊断质量，不影响业务结论 |
| QA-AUD-039 | AUD-039 | shared | `evaluation_service.py` / `v4_validation.py` | 裸 KeyError/ValueError 可能中断整批 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | POST_V1 | OPEN | CSV#39 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：改为领域 issue 需 Golden 保护；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——`evaluation_service.py` / `v4_validation.py` 属 legacy 链 |
| QA-AUD-040 | AUD-040 | shared | `JsonStandardRepository.get_pack` | 每次解析完整 JSON，批量性能随数据量增长 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future | OPEN | CSV#40 + QA-P1-007 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：先保留实测，再设计缓存 |
| QA-AUD-041 | AUD-041 | shared | `json_repository.py` | manifest 缺键直接 KeyError；缺文件静默空记录；find 线性 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | VERIFY_BEFORE_PHASE9 | OPEN | CSV#41 | DEFER_TO_P3：非 settings 切片，保持既有风险与证据；原决定：Schema/错误语义进入 Phase 1；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ VERIFY_BEFORE_PHASE9——`json_repository.py` 在正式链上；缺键 `KeyError` / 缺文件静默空记录可能掩盖数据问题，须在发布前给出结论（`audit_release` 已显式检查 manifest / 包文件存在性，属部分缓解） |
| QA-AUD-042 | AUD-042 | shared | `v4_writer.py` / `template_resource.py` | 整体读写 xlsx 内存高、临时目录生命周期隐含 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | VERIFY_BEFORE_PHASE9 | OPEN | CSV#42 | Excel 后置，不在 0A 优化；<br>**Phase 8 disposition review（2026-10-07）**：→ VERIFY_BEFORE_PHASE9——正式批量链 10,000 行实测峰值 952 MB；发布前须给出资源结论 |
| QA-AUD-043 | AUD-043 | shared | `web/server.py` / `entrypoint.py` | `--host 0.0.0.0` 无鉴权，可暴露服务 | 可能影响发布可靠性或长期维护；业务影响待证 | M | PROTOTYPE | P1 | Future | OPEN | CSV#43 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：Web 非当前 V1 入口，仍需安全处理 |
| QA-AUD-044 | AUD-044 | shared | Web upload `X-Filename` | 文件名拼接宿主路径，存在路径穿越风险 | 可能影响发布可靠性或长期维护；业务影响待证 | M | PROTOTYPE | P1 | Future | OPEN | CSV#44 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：上传功能未作为 V1 发布，但不得带风险发布 |
| QA-AUD-045 | AUD-045 | shared | `desktop/main_window.py` | 窗口混合表单、IO、结果展示，270 行上帝窗口 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | POST_V1 | OPEN | CSV#45 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：AppShell 以后用真实样板验证；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——legacy 桌面上帝窗口；Qt 不引用 `desktop/main_window` |
| QA-AUD-046 | AUD-046 | shared | `docs/` | 27 个编号清单和多份 HANDOFF 重叠，调度来源不清 | 可能影响发布可靠性或长期维护；业务影响待证 | M | LEGACY | P1 | Phase 0 | MAPPED | CSV#46 + ROADMAP | 本次冻结权威入口，暂不批量移动 |
| QA-AUD-047 | AUD-047 | shared | repository root | 缺 LICENSE/CHANGELOG；README 偏交接文档 | 当前未确认影响 V1 业务结论；维护风险待证 | M | DEV_ONLY | P2 | Future | OPEN | CSV#47 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：不影响 Phase 1 业务契约 |
| QA-AUD-048 | AUD-048 | shared | `equip_test.spec` / `build_native.py` | spec 引用旧 standards，和构建脚本重复 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Future | OPEN | CSV#48 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：构建清理前保留 |
| QA-AUD-049 | AUD-049 | shared | `tools/extract_*.py` | G 盘绝对路径，换环境可能误读本机资源 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Future | OPEN | CSV#49 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：标记 legacy 或参数化 |
| QA-AUD-050 | AUD-050 | shared | `v4_template_audit.py` | 16 个国标号、GB 28381-2026 和状态字符串硬编码 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Phase 9 | OPEN | CSV#50 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：标准事实不得继续散落；<br>**Phase 8 disposition review（2026-10-07）**：→ Phase 9——发布审计 `audit_release` 直接调用 `audit_v4_template`；硬编码国标号/状态串漂移会污染发布门禁 |
| QA-AUD-051 | AUD-051 | shared | OOXML reader / template audit | inline 字符串和 namespace 重复实现 | 当前未确认影响 V1 业务结论；维护风险待证 | L | NOT_SHIPPED | P2 | VERIFY_BEFORE_PHASE9 | OPEN | CSV#51 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：V4 后置处理；<br>**Phase 8 disposition review（2026-10-07）**：→ VERIFY_BEFORE_PHASE9——OOXML 解析重复横跨正式 `ooxml_reader` 与发布审计用 `v4_template_audit`，需先确认正式链单一来源 |
| QA-AUD-052 | AUD-052 | shared | `v4_writer.py:450-451` | 恒假分支，维护噪音 | 当前未确认影响 V1 业务结论；维护风险待证 | L | NOT_SHIPPED | P2 | POST_V1 | OPEN | CSV#52 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：不得在 0A 顺手删除；<br>**Phase 8 disposition review（2026-10-07）**：→ POST_V1——`v4_writer` 恒假分支，属 V4 adapter |
| QA-AUD-053 | AUD-053 | shared | `application/ports/__init__.py` | 端口导出策略不一致，外部导入可能遗漏 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Future | OPEN | CSV#53 | DEFER_TO_P4：真实样板后再通用化；不在薄壳阶段重构业务；原决定：契约整理时修；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——ports 导出策略不一致，契约整理项 |
| QA-AUD-054 | AUD-054 | shared | `schema_constraints.py` 等 | 缺专门单测，死代码也缺验证 | 可能影响发布可靠性或长期维护；业务影响待证 | M | DEV_ONLY | P1 | Future | OPEN | CSV#54 | DEFER_TO_P4：非 settings 切片，保持既有风险与证据；原决定：Golden/契约测试规划时补齐；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ Future——`schema_constraints.py` 等缺专门单测（非正式链） |
| QA-EVID-055 | AUD-055 | shared | `tests/` | 第三方认为存在 60 个真实 unittest，用于保护重构 | 不表示缺陷；仅为测试基线事实 | UNKNOWN / NEEDS_EVIDENCE | DEV_ONLY | EVIDENCE | Phase 0 | MAPPED | CSV#55 | Phase 0 实测为 54 module、887 项，历史数字不作当前事实 |

## P0 Hotfix Lane 状态

当前登记的 P0 是 `QA-P0-001`、`QA-P0-002`、`AUD-010`、`AUD-011`、`AUD-030`、`AUD-031` 等风险项，但均尚未满足“明确标准证据 + 最小修复 + 回归测试”的全部 Hotfix 条件，且部分属于 `NOT_SHIPPED` V4 表面。因此：

```text
Phase 0A: PASS
Phase 0B: NOT_EXECUTED
Hotfix IDs: none
```

进入 Phase 1 后，先把 P0 风险转成标准复核和 Golden Candidate；未经批准不得修 evaluator、拆架构或清理空壳。

## Phase 1 P0 Evidence Review（2026-09-22）

本节只记录证据复核，不关闭原始 P0 条目，也不授权 Hotfix。`review_result` 只能使用 `CONFIRMED_P0`、`NOT_P0`、`NEEDS_MORE_EVIDENCE`；它与 backlog 的 `classification=P0` 分开。本节也使用与其他来源一致的最小字段；未知信息必须写 `UNKNOWN / NEEDS_EVIDENCE`。

| issue_id | legacy_id/audit_id | profile_id | location | description | business_risk | engineering_risk | release_surface | classification | target_phase | status | review_result | evidence | decision | next_action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `QA-AUD-010` | `AUD-010` | shared | `evaluators/shared.py:_interval_hit` | 核心区间解析可能造成边界结论错误 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | VERIFY_BEFORE_PHASE9 | VERIFY | `NEEDS_MORE_EVIDENCE` | 复跑既有 12 个标准区间 probe：`0.25`、`0.95`、`3.15`、`10`、`17700`、`21000`、`700`、`700.01`、`1000`、`1000.01` 及严格开区间样例，实际结果全部符合预期 | 尚未证明错误；保持 P0/VERIFY，不因 probe 通过而自报关闭；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ VERIFY_BEFORE_PHASE9——`evaluators/shared.py` 区间判定位于业务判定链，边界错误可能给错结论；P0 且尚未证明安全 | 以标准原文区间和 Golden Case 扩大覆盖，再决定是否需要最小修复 |
| `QA-AUD-011` | `AUD-011` | shared | `v4_validation.py` / `input_normalization.py` | 规范化重复实现，差异可能改变输入含义 | 可能影响业务结论；需标准/Golden 证据 | H | NOT_SHIPPED | P0 | POST_V1 | VERIFY | `NEEDS_MORE_EVIDENCE` | `pump_water` 的短类别和完整 V4 别名均归一化为同一字段；同一输入得到相同等级、指标、限值和查表命中；V4 validation 对合法、零值、分数级数和效率越界分别给出预期问题 | 样板路径未显示业务结论差异，但证据不足以对共享风险作整体 `NOT_P0` 判断；保持 P0/VERIFY，不重构；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——`v4_validation` / `input_normalization` 属 V4 / legacy 链（与 Phase 8 轮 QA-AUD-011 同口径） | 将其他 V1 Profile 纳入 Import Contract/Golden 矩阵；未完成前不删除重复实现 |
| `QA-AUD-030` | `AUD-030` | shared | `v4_validation.py` metadata/manual constraints | 手工规则表和 metadata 派生规则可能形成双真相源 | 可能影响业务结论；需标准/Golden 证据 | M | NOT_SHIPPED | P0 | POST_V1 | VERIFY | `NEEDS_MORE_EVIDENCE` | 元数据字段：流量/扬程/转速为正、级数为整数、效率 1–100；V4 probe 对 0、分数级数、0/101 效率均按预期拒绝；未发现样板输入差异 | 样板未复现错误，不能外推到所有 Profile；保持 P0/VERIFY；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ POST_V1——双真相源的另一半 `v4_validation.py` 属 V4 / 非正式链 | 完成各 V1 Profile 的字段约束对照和 Golden 证据；不在 Phase 1 重构校验器 |
| `QA-AUD-031` | `AUD-031` | shared | 默认 `as_of` 与标准实施日期 | 多处默认判定日期可能选择错误的标准生效状态 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | SUPERSEDED | VERIFY | `NEEDS_MORE_EVIDENCE` | 默认/显式 `2026-08-23` 均判为 1 级；显式 `2026-02-28` 在 `2026-03-01` 实施日前拒绝使用该标准；Golden Cases 全部显式记录 `as_of` | 当前未证明错误结论；默认日期是否允许、默认来源和审计展示仍是业务决策；<br>**已完成 Phase 遗留 disposition review（2026-10-07）**：→ SUPERSEDED——Owner 决定（2026-10-02，Phase 5 / 7 收口）：评价日期不是业务门禁，不改变等级 / `evaluation_status`；正式路径自动取本机当天 | 在 Result Contract/产品决策中确认 `as_of` 必填或兼容默认，并要求结果带默认来源；不改实现 |

## CPython 3.12.x x64 V1 revalidation（2026-09-23）

本次用项目 `.venv\Scripts\python.exe`（CPython 3.12.14 x64）重跑当前正式 unittest：

```text
$env:PYTHONPATH='src'; & '.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_*.py'
Ran 887 tests in 151.127s
FAILED (failures=3, errors=1, skipped=3)
wall duration: 155.565s
pass=880; fail=3; error=1; skip=3; not_run=0
```

失败集合与 Python 3.13.3 Phase 0/Phase 1 记录一致：3 个 V4 电机 reader/writer 失败（`NOT_SHIPPED`），1 个 release audit `wheel_pmsm_status` 错误（`DEV_ONLY`）。本次仅完成环境复验，没有修改业务实现、测试期望或发布表面。

## Pump V2 R01–R06 remediation record（2026-09-27）

王玮已授权按独立正式验收报告限定修订 R01–R06。本节记录实现和针对性证据；状态是 `IMPLEMENTED_PENDING_FIXED_SHA_INDEPENDENT_REVIEW`，不是业务批准、Golden 批准、P0 复核分类变更或 Phase 1 PASS。实施范围在独立 clean worktree，起点为 `9e413051177fbfa7f1b217de17d344f33176b152`；逐文件 allowlist 见 `PUMP_V2_R01_R06_COMMIT_MANIFEST.md`。

| ID | 本次处理和证据 | 剩余门禁 |
|---|---|---|
| R01 | 非空非法流量、扬程、效率、单双吸和级数统一为 `INVALID_INPUT`，从 `missing_fields` 移除；缺失字段仍为 `INSUFFICIENT_DATA`。`test_pump_numeric_contract_v2` 与 `test_pump_golden_case_0_3` 覆盖非法值、真正缺失和冲突。 | 原独立会话按固定 SHA 复验；不扩大为共享 evaluator 重构。 |
| R02 | 公共 pump API 对已准入 `pump_water` 返回 `SUPPORTED`；`pump_chemical`、类别缺失/未知/OTHER 等无已批准公开路由的结果显式返回 `NOT_IN_RELEASE_SCOPE`。技术 Profile 的 `support_status=null` 仍表示未经过发布门禁。 | `pump_chemical` 仍 `UNDER_REVIEW`；不得把技术计算解释为发布支持。 |
| R03 | 新版 26 个候选均为 `DRAFT/PENDING`：18 条水泵通过公共 Application E2E，覆盖有效 1/2/3 级、轻型立式/卧式和管道泵；8 条化工泵仅作技术 Profile 诊断。候选 schema 和回放由 `test_pump_golden_case_0_3` 验证。 | 全部案例仍待具名业务/标准复核，不批准 Golden。 |
| R04 | validator 支持 0.1/0.2/0.3 版本读取；仓库文本引用的 CRLF/LF 统一以 LF 内容计算 SHA-256，外部/非文本文件仍按原始字节；0.3 sidecar pins 对应提交内容。只将确切登记的 0.1 Canonical 路径、catalog 和旧哈希作为历史 provenance。旧七个官方案例文件保持基线字节；未知哈希仍报错。`test_golden_case_schema_0_2` 验证跨行尾 hash、26 个候选引用及历史哈希规则。 | 旧官方历史 hash 不更新；Golden 业务批准仍待独立验收。 |
| R05 | `EV_SUCTION` metadata projection 恢复冻结的 V4 选项“一吸/双吸/不适用/其他（请备注说明）”；公式有效性仍只接受单双吸。由 metadata contract、architecture 和 evaluator matrix 覆盖。 | 表单可表达值不等于有效公式输入，不扩展产品适用范围。 |
| R06 | HANDOFF、TASK_STATE、ROADMAP、BASELINE、QA_BACKLOG 和实施报告反映本轮范围、阻塞、命令及现存失败；release-audit 只带入泵诊断差异，排除 `tests/unit/test_release_audit.py` 的工作区行尾状态及所有非泵审计行为。 | `wheel_pmsm_status` 全量测试错误仍保留为既有发布审计基线；等待原独立正式验收。 |

截至本记录，V2 目标测试全部通过；最终 fixed-SHA fresh worktree 全量 unittest 为 916 tests，909 pass、3 fail、1 error、3 skip，失败为既有 V4 motor reader/writer 三项及 wheel 审计缺少 `wheel_pmsm_status` 一项错误。没有修复或隐藏这些基线结果。无 P0 `review_result` 被改写；Phase 1/Golden/Solution-Product Review 继续阻塞。

## Pump V2 R07 follow-up（2026-09-28）

用户根据 fixed head `72e8e490d2da56ec8064ad799750fb7b83425a57` 的独立验收结论，授权定点处理 R02 路由和 R04 外部证据问题。R07 实施状态为 `IMPLEMENTED_PENDING_FIXED_SHA_INDEPENDENT_REVIEW`；以下技术修复不代表外部验收通过、业务批准或 Phase 1 状态转换。

| ID | 实施与证据 | 剩余门禁 |
|---|---|---|
| R07-01 / R02 | `device_types.py` 将公共离心泵 `product_type` 改为完整名称/登记别名精确映射；显式 profile 只接受受支持的注册值；未知含“多级/管道/单级单吸”的类别不会落入 `pump_water`。Application 回归测试要求三种未知关键词请求为 `NOT_IN_RELEASE_SCOPE`、`UNRESOLVED`、`INVALID_INPUT`，只保留类别路由 trace，不执行公式。 | 固定 SHA 交原独立会话复验；`pump_chemical` 的发布门禁仍冻结。 |
| R07-02 / R04 | 新增外部 evidence registry，以标准 source ID、相对文件名和原始 PDF SHA-256 标识 GB 19762-2025；validator 支持 CLI evidence root 或 `EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT`，不提交 PDF。0.3 候选移除本机盘符路径。 | 独立 clone 的 PDF 字节校验需要用户/复验者挂载同一标准文件并提供 evidence root。CI 只校验结构、registry pins 和仓库证据，会清楚报告跳过数。 |
| R07-03 | 新增 unknown-keyword Application 负例、外部 evidence root 跨 clone 定位及内容 hash 篡改测试、机器盘符扫描，并覆盖 v0.1 legacy source ID 到 registry locator 的映射。 | 原独立验收复验最终候选 SHA。 |
| R07-04 | `CURRENT_IMPLEMENTATION` 历史差异不再宽泛自动放行；仅严格匹配 registry 中的 schema version/catalog/path/hash 才保留历史 provenance。登记的确切 0.1 implementation hash 可读；任意改动值和 0.2 未登记值均为错误。旧 case bytes/hash 不改。 | 无历史 hash 刷新；复验 validator 与对应回归测试。 |
| R07-05 | 增加面向 PR #1 的 Windows 3.12 workflow，覆盖 contract/schema、泵 route/numeric/boundary/Golden、metadata/architecture、evaluator matrix、compileall 和 diff check。首轮 Windows CI 暴露临时目录短路径与 `.resolve()` 长路径比较差异，现已把测试期望改为规范化路径。 | 修复后的 GitHub Actions 正在对新 SHA 重跑；CI 不验证外部 PDF 原始字节。 |

R07 本机 isolated-worktree 定向泵组为 157 pass；metadata/architecture/evaluator matrix 为 394 pass。外部证据根目录模式验证 7 条旧案例和 26 条候选、0 错误；显式 skip 模式也为 0 结构/hash 错误，分别标记跳过 7 和 26 项 PDF 字节检查。全量 unittest 更新为 921 total：914 pass、3 fail、1 error、3 skip；既有 3 个 V4 motor 失败和 wheel `wheel_pmsm_status` 错误保持原样。详见 `IMPLEMENTATION_REPORT.md` 与逐文件 `PUMP_V2_R07_COMMIT_MANIFEST.md`。Golden 仍全部 `DRAFT/PENDING`，Phase 1 仍 `BLOCKED`，不启动 Phase 2。

> **后续状态更正（2026-10-02）**：上段末句是 **R07 当时（2026-09-28）的状态快照**，**已被取代**，不要按当前状态解读：
> - Phase 1 已 `PHASE_1_PASS`（Exit Gate 已满足），不再是 `BLOCKED`；
> - 18 条 `pump_water` Golden 0.4 已于 2026-09-28T11:03:04+08:00 由王玮具名批准为 `APPROVED`；Golden 0.1 七例与原始 0.3 的 26 条候选仍为历史冻结 / `DRAFT`；
> - `pump_chemical` 的 C1–C11 已于 2026-10-02 获产品负责人 **11/11** 业务真值批准，并形式化为 11 条正式 `golden-case-0.5`；其 `support_status` 仍保持 `NOT_IN_RELEASE_SCOPE`（业务真值 blocker 已关闭，剩余 blocker 为 Stage D 独立验收）。
>
> 历史正文保留不改写；当前权威状态见 [ROADMAP.md](ROADMAP.md)、[TASK_STATE.md](TASK_STATE.md) 与 [V1_SCOPE.md](V1_SCOPE.md)。

## Excel Decimal Ingress（2026-10-02 登记）

本节登记 Excel 数值入口的 Decimal 保真风险。**只登记，不在本轮修改任何 Python 实现。**

| issue_id | legacy_id/audit_id | profile_id | location | description | business_risk | engineering_risk | release_surface | classification | target_phase | status | evidence | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `QA-EXCEL-001` | `V2.3-CLEANUP-R1` | `pump_water`（`pump_chemical` 同路径） | `src/equipeffi/infrastructure/excel/ooxml_reader.py::_parse_number`（第 35–45 行），调用点 `ooxml_reader.py:144`；上层 `v4_reader.OOXMLV4Reader.read_rows`（`v4_reader.py:62`）、`v4_writer.py:421` | 该函数先 `Decimal(text)` 解析单元格词法文本，再 `return float(number)`，在可无损的位置物化为 binary float。xlsx 数值本身是 XML 词法文本，`Decimal` 已在手，转 float 是纯损失 | 可能影响业务结论：若该 float 进入权威链并参与 full-value 比较或表 3 边界，存在翻转分档的可能 | M | `NOT_SHIPPED` | P1（暂定；视影响面验证结果可上调） | CLOSED（Phase 8A 承接登记） | OPEN（历史登记；当前已 `CLOSED`，见 Phase 8 承接登记） | 源码定位；`git grep` 确认 `src` 内无 openpyxl，该链路为自研标准库读取器，入口完全可控 | 保留登记；**Phase 8 前必须关闭**。不因本条目在治理任务中修改 Python |

```text
QA-EXCEL-001
表面            = NOT_SHIPPED（V4 Excel 读写路径，生产链 0 引用）
authoritative path impact = 尚待验证
  —— 需先确认该 float 是否经 V4 输入适配器进入权威数值链；
     若适配器已转为 Decimal 字符串，则属潜在缺陷；若直接消费，则属活跃缺陷
最小修法候选    = 保留 Decimal 或返回词法文本，不转 float（不需改架构）
关闭时点        = Phase 8 正式 Excel 实现前（已于 Phase 8A 关闭，见下方「Phase 8 承接登记」）
本轮约束        = 不改 Python 实现、不改测试期望、不改 V4 行为
关联            = Numeric Contract v1 §2.1 ingress boundary；
                  docs/28_EquipEffi 后续开发总体路线 V2.3.md 第 7.1 节
```

该条目与 `QA-P0-002`（V4 writer 写回测试失败）同属 `NOT_SHIPPED` 表面，但**根因不同**：`QA-P0-002` 是结果写回，`QA-EXCEL-001` 是数值入口保真。两者不得合并关闭。

## Phase 2 最小工程切片处置（2026-10-02）

来源：本次用户执行授权与 docs/31；下表覆盖起点所有 target_phase 含 Phase 2 的 OPEN/VERIFY 项。延期项保持 OPEN/VERIFY。

> **历史表说明（2026-10-07）**：下表 `target_phase = Phase 8` 为 2026-10-02 的历史目标记录；Phase 8 已 `EXECUTION_COMPLETE`
> 并合并 PR #16（`64b656ee`）。历史 `disposition`（`DEFER_TO_P8`）**保留不改写**，`target_phase` 单元格已标注当前去向，
> 完整判定见下方「Phase 8 disposition review（2026-10-07）」。

| issue_id | disposition | target_phase | decision |
|---|---|---|---|
| QA-P1-003 | DEFER_TO_P8 | Phase 8（历史）→ Phase 9 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-P1-007 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-001 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-002 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-003 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-004 | DEFER_TO_P4 | Phase 4（历史）→ SUPERSEDED | 真实样板后再通用化；不在薄壳阶段重构业务 |
| QA-AUD-006 | DEFER_TO_P3 | Phase 3（历史）→ Future | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-008 | DEFER_TO_P4 | Phase 4（历史）→ Future | 真实样板后再通用化；不在薄壳阶段重构业务 |
| QA-AUD-012 | DEFER_TO_P3 | Phase 3（历史）→ POST_V1 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-013 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-015 | DEFER_TO_P3 | Phase 3（历史）→ POST_V1 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-016 | DEFER_TO_P3 | Phase 3（历史）→ POST_V1 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-017 | DEFER_TO_P3 | Phase 3（历史）→ POST_V1 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-018 | DEFER_TO_P3 | Phase 3（历史）→ POST_V1 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-020 | DEFER_TO_P8 | Phase 8（历史）→ SUPERSEDED | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-021 | DEFER_TO_P8 | Phase 8（历史）→ Future | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-023 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-024 | PARTIAL_IN_P2 | Phase 2/3（历史）→ Future | 仅完成 settings 端口/存储；原业务仓储与其他端口仍开放 |
| QA-AUD-025 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-027 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-028 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-032 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-033 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-034 | CLOSE_IN_P2 | Phase 2 | 按 docs/31 实施；对应测试已通过，CLOSED |
| QA-AUD-035 | CLOSE_IN_P2 | Phase 2 | 按 docs/31 实施；对应测试已通过，CLOSED |
| QA-AUD-036 | CLOSE_IN_P2 | Phase 2 | 按 docs/31 实施；对应测试已通过，CLOSED |
| QA-AUD-037 | CLOSE_IN_P2 | Phase 2 | 按 docs/31 实施；对应测试已通过，CLOSED |
| QA-AUD-038 | DEFER_TO_P3 | Phase 3（历史）→ Future | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-039 | DEFER_TO_P3 | Phase 3（历史）→ POST_V1 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-040 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-043 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-044 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-045 | DEFER_TO_P3 | Phase 3（历史）→ POST_V1 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-047 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-048 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-049 | KEEP_OPEN_FUTURE | Future | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-050 | DEFER_TO_P8 | Phase 8（历史）→ Phase 9 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-051 | DEFER_TO_P8 | Phase 8（历史）→ VERIFY_BEFORE_PHASE9 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-052 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-053 | DEFER_TO_P4 | Phase 4（历史）→ Future | 真实样板后再通用化；不在薄壳阶段重构业务 |
| QA-AUD-005 | DEFER_TO_P3 | Phase 3（历史）→ Future | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-007 | DEFER_TO_P4 | Phase 4（历史）→ Future | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-009 | DEFER_TO_P3 | Phase 3（历史）→ Future | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-011 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-014 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-022 | PARTIAL_IN_P2 | Phase 2/3（历史）→ SUPERSEDED | settings 已真实接线，旧空桩保留未接线，业务仓储仍 OPEN |
| QA-AUD-026 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-029 | DEFER_TO_P8 | Phase 8（历史）→ Phase 9 | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-031 | DEFER_TO_P3 | Phase 3（历史）→ SUPERSEDED | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-041 | DEFER_TO_P3 | Phase 3（历史）→ VERIFY_BEFORE_PHASE9 | 非 settings 切片，保留 OPEN/VERIFY |
| QA-AUD-054 | DEFER_TO_P4 | Phase 4（历史）→ Future | 非 settings 切片，保留 OPEN/VERIFY |

## Phase 3 统一纵向闭环处置（2026-10-02）

来源：用户 Phase 3 执行授权与 `docs/32`；下表覆盖所有 `target_phase` 含 Phase 3 的项，以及 Phase 2 延后到 Phase 3 的项。

处置口径：只有**真实完成并有测试证据**的项才 `CLOSE_IN_P3`；实际只做了一部分的记 `PARTIAL_IN_P3` 并保留 OPEN；不在本轮范围的记 `DEFER` / `NOT_APPLICABLE`。**不为 Phase 3 PASS 虚假清空台账。**

> **历史表说明（2026-10-07）**：下表 `target_phase = Phase 8` 为 2026-10-02 的历史目标记录；Phase 8 已 `EXECUTION_COMPLETE`
> 并合并 PR #16（`64b656ee`）。历史 `disposition`（`DEFER_TO_P8`）**保留不改写**，`target_phase` 单元格已标注当前去向，
> 完整判定见下方「Phase 8 disposition review（2026-10-07）」。

| issue_id | disposition | target_phase | decision |
|---|---|---|---|
| QA-AUD-005 | PARTIAL_IN_P3 | Phase 3（历史）→ Future | 新增统一 `AnalysisService` 经 profile 查询路由（不复制映射，架构门禁已断言）；旧 `device_types`/兼容入口仍在，路由理解成本未消除 |
| QA-AUD-006 | PARTIAL_IN_P3 | Phase 3/4（历史）→ Future | 新增独立 `PumpAnalysisResult` / `RecordSnapshot` 契约并把 Decimal 归一为文本；`EvaluationResult` 混合职责的拆分仍留 Phase 4 |
| QA-AUD-009 | DEFER_TO_P4 | Phase 4（历史）→ Future | `device_specs`/`metadata` 硬编码未迁移；Phase 3 未授权数据迁移 |
| QA-AUD-012 | PARTIAL_IN_P3 | Phase 3/4（历史）→ POST_V1 | Phase 3 以新增薄编排服务承载统一入口；`evaluation_service` 279 行上帝方法未重写（避免大规模重写，符合 Non-goals） |
| QA-AUD-015 | PARTIAL_IN_P3 | Phase 3/6 | 新 Qt 统一分析页不再重复 fallback 表单；遗留 Tk/Web 重复仍在 |
| QA-AUD-016 | PARTIAL_IN_P3 | Phase 3/6 | 新统一结果页使用单一结论投影；遗留多份结论标签仍在 |
| QA-AUD-017 | PARTIAL_IN_P3 | Phase 3/6 | 新页面字段来自 Application 契约；遗留基础信息元组重复仍在 |
| QA-AUD-018 | PARTIAL_IN_P3 | Phase 3/6 | 新页面摘要由 Application 结果直接投影；Python/JS 重复摘要仍在 |
| QA-AUD-038 | PARTIAL_IN_P3 | Phase 3/4（历史）→ Future | 统一入口用 `AnalysisError` 显式区分业务与执行错误；损坏文件/仓储异常根因归一仍留后续 |
| QA-AUD-039 | PARTIAL_IN_P3 | Phase 3/4（历史）→ POST_V1 | 统一入口不抛裸 `KeyError`；旧 `evaluation_service`/`v4_validation` 裸异常仍 OPEN |
| QA-AUD-045 | PARTIAL_IN_P3 | Phase 3/6 | Qt 侧新增统一页面；遗留 Tk `main_window` 270 行上帝窗口按 Non-goals **未动** |
| QA-AUD-031 | PARTIAL_IN_P3 | Phase 5 | `as_of` 产品口径已由 `EQP-STD-GB19762-001` 关闭为 `RESOLVED`（软件产品决定）；统一入口要求显式 `as_of` 且无隐式默认。**遗留 CLI/API 的 5 处兼容默认值仍按 `AGENTS.md §2.0` 登记保留**，全局取消须另立任务做兼容影响评估 |
| QA-AUD-041 | DEFER | Phase 4/8 | `json_repository` 缺键/缺文件语义与线性 find 未在 Phase 3 处理 |
| QA-AUD-011 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | 规范化重复实现属 Import/V4 路径；统一入口未新增第三套规范化，但未消除既有重复 |
| QA-AUD-014 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | `input_normalization` 16 类硬编码未拆分 |
| QA-AUD-026 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | `adapt_many`/`validate_draft` 未接线；属 V4 适配 |
| QA-AUD-029 | DEFER_TO_P8 | Phase 8（历史）→ Phase 9 | 模板名/sheet 清单重复配置；属 Import Contract 单一来源 |
| QA-AUD-013 | DEFER_TO_P8 | Phase 8（历史）→ POST_V1 | `v4_validation` 882 行特例链；Phase 3 未动 |
| QA-EXCEL-001 | DEFER_TO_P8 | Phase 8（历史）→ CLOSED（Phase 8A 承接登记） | Excel 数值入口 Decimal→float；按既定约束 Phase 8 前必须关闭，本 Phase 不改 Python |
| QA-P0-001 / QA-P0-002 | DEFER | Phase 8（历史）→ VERIFY_BEFORE_PHASE9 | V4 motor reader/writer 失败，`NOT_SHIPPED`；不在 Phase 3 范围 |
| QA-P1-003 | DEFER_TO_P8 | Phase 8（历史）→ Phase 9 | 发布审计 `wheel_pmsm_status`，`DEV_ONLY` |
| QA-P1-007 / QA-AUD-040 | DEFER | Future | 标准包缓存/解析性能；Phase 3 先登记实测，不做缓存重构 |
| QA-AUD-034 / 035 / 036 / 037 | ALREADY_CLOSED_IN_P2 | Phase 2 | Phase 2 已 `CLOSE_IN_P2`，Phase 3 未回退 |

### Phase 3 新增登记

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-P3-001` | `V1_RUNTIME` | OPEN | **遗留兼容默认日期**：`date(2026,8,23)` 仍作为隐式默认出现在 6 处源码位置（`evaluation_service.py:13`、`evaluation_facade.py:27/68`、`v4_workbook_service.py:34/67`、`application_api.py:539`）。统一 `AnalysisService` 已要求显式 `as_of`；遗留入口按 `AGENTS.md §2.0` 登记保留，全局取消须另立任务并附兼容影响评估 |
| `QA-P3-002` | `V1_RUNTIME` | OPEN | **标准生命周期元数据缺失**：Canonical Pack 目前只提供 `effective_date`，没有 `superseded_by` / 废止日期等生命周期元数据，因此软件只能对"评价日期早于实施日期"给出非阻断提示（Phase 5 起为四字短语"该标准尚未实施"），**无法**自动识别"已废止 / 已被替代"。Owner 决定明确不为凑齐提示而私造公共规则；补齐须走标准映射流程 |
| `QA-P3-003` | `CLOSED`（Phase 6 R1） | **遗留非正式表面的旧 `as_of` 门禁**：Owner 规则规定评价日期不是业务门禁。R1 已让离心泵（`pump_water` / `pump_chemical`）在遗留 `EvaluationService` 中**豁免**该门禁（`internal_device_type in PUMP_RULE_PROFILES` 时不再短路标准评价）；该门禁仍保留给其他 Profile，本 Phase 不为它们改语义。实测：`as_of=2026-02-28` 时两个 rule profile 均正常计算、`evaluation_status = SUCCESS`，且 trace 中不再出现「标准生效日期」跳过步骤。<br>`closed_by`：`tests/unit/test_phase6_product_shell.py::QaClosureTests::test_qa_p3_003_legacy_as_of_gate_no_longer_blocks_pumps` |

### Phase 4 新增登记

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-P4-001` | `V1_RUNTIME` | `REGISTERED_DEVIATION` | **ADR-002 的完整 lineage / audit event 长期目标继续有效，但 Phase 3 / Phase 4 均未完整实现。** ADR-002 要求 Finalize 时把输入快照、结果快照、数据引用、规则引用、lineage 与 audit event 在**同一事务**中写入；当前只实现了输入/结果/引用快照与不可变追加，**没有** lineage 表与 audit event。Phase 4 / Phase 5 明确**不实现** lineage / audit / reproduce，且不因此修改 `records.sqlite`（不新增表、不新增迁移、`schema_version` 保持 2）。<br>`target_phase`：**不再被动排期**（Phase 7 明确判定：普通用户流程不需要正式 Reproduce / Attempt / 通用 Audit·Lineage Framework）<br>**Phase 7 决定**：不建立通用 Audit / Lineage Framework，也不为理论上的未来能力扩展数据库；本条目保持 `REGISTERED_DEVIATION`（长期目标不再自动继承到后续 Phase），如将来确实需要「基于历史记录重新分析」，须作为**独立、明确需求**单独设计与授权<br>本条目为**已登记未关闭**的偏差：不得假装已解决，也不得据此阻塞任何 Phase 的 Exit Gate |

### Phase 5 新增登记

发布表面边界（Owner 决定）：**Windows V1 当前正式发布用户表面 = PySide6 Qt Desktop（`--qt`）**。
以下表面是**现存的 compatibility / development / future-adapter surfaces**，
不是历史废代码；它们与正式表面的 `support_status` 语义差异在此**逐项登记**，
不得用"历史兼容代码"含糊带过。

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-P5-001` | `CLOSED`（Phase 6 R1） | **`--json` / `ApplicationApi` / JSONL / CLI 曾对 `pump_chemical` 返回 `NOT_IN_RELEASE_SCOPE`**。根因是遗留 `EvaluationService` 中一段硬编码短路（`PROFILE_NOT_IN_RELEASE_SCOPE`）未与统一纵向切片同步。R1 已删除该短路，并把发布门禁收敛为**单一事实源** `application/services/pump_release_gate.py`；`EvaluationService` 与 `CentrifugalPumpAnalysisService` 都**实际调用** `pump_release_gate.pump_release_support`（后者在 R1 首轮仅声明而未调用，复验已指出并修正）。机械证据：在内存中替换 `PUMP_RELEASE_SUPPORT['pump_chemical']` 后两条路径同步变化；见 `R1SecondRoundBlockerTests::test_shared_release_gate_is_actually_used_by_both_paths`。<br>实测：同一石化泵输入经 `--json` CLI、`ApplicationApi` 与正式纵向切片得到**相同**的 `support_status = SUPPORTED` / 结论 / 等级。<br>`closed_by`：`tests/unit/test_phase6_product_shell.py::EntrySurfaceParityTests` |
| `QA-P5-002` | `CLOSED`（Phase 6 / R1） | (a) **legacy Tk `--gui` 已收口**：不再启动 Tk，与无参数启动、`--qt` 相同进入正式 Qt Shell；Tk 不再是任何用户产品入口；已删除 Tk→Web fallback。(b) **`--web` 语义已同步**：`--web` 经 `ApplicationApi` → `EvaluationFacade` → `EvaluationService`，与 (a) 的 `--json` / CLI 走同一条链路，因此 `pump_chemical` 同样返回 `SUPPORTED` 并正常评价；见 `QA-P5-001`。<br>`closed_by`：`tests/unit/test_phase6_product_shell.py::EntrySurfaceParityTests` 与 `...::EntrypointTests::test_legacy_tk_launcher_is_not_a_product_entrypoint` |
| `QA-P5-003` | `REGISTERED_DEVIATION` | OPEN（历史登记；当前已 `CLOSED`，见 Phase 8 承接登记） | **V4 / Excel adapter 仍对 `pump_chemical` 返回 `NOT_IN_RELEASE_SCOPE`**：Excel 收口排在 Phase 8。<br>`disposition`：**Phase 8**（且 Phase 8 **必须**调用同一 Application / Calculator，**不得**建立第二套业务算法） |
| `QA-P5-004` | `REGISTERED_DEVIATION` | OPEN | **Android bridge 未纳入本阶段正式支持表面**。正式发布前必须消除所有未声明的发布表面语义分歧。<br>`disposition`：**Phase 9** |
| `QA-P5-005` | `REGISTERED_DEVIATION` | OPEN | **安装包 / 代码签名 / 正式发布产物**未产生：本 Phase 不声明可发布。<br>`disposition`：**Phase 9** |

**不得**把这些已登记 deviation 误报为 Phase 5 PASS 范围内已修复。

未完成项保持 OPEN/VERIFY；本表不因 Phase 3 / Phase 4 / Phase 5 交付而关闭任何缺乏测试证据的条目。

### Phase 6 新增登记

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-P6-001` | `LEGACY_TK` | `REGISTERED_DEVIATION`（仍开；Phase 8 明确不清理，见 Phase 8 承接登记） | **legacy Tk 桌面窗口实现保留但不接线**。Phase 6 已按 Owner 决定断开正式入口：`--gui` / 无参数 / `--qt` 均进入 Qt；`launcher.py` 不再导出 `launch_packaged_gui`，也不再回退 Web。<br>**未删除** `src/equipeffi/presentation/desktop/main_window.py`：该文件同时承载被 `tests/unit/test_desktop_form_model.py`（110 项）引用的**非 Tk 表单模型契约**（`form_fields_for_public_type` / `result_summary` / `capability_status_text` / `elimination_scope_options` / `download_builtin_template` / `conclusion_field_label`）与 1 项 Tk 实例测试，因此**不是零引用可盲删**的代码；按 Owner 规则"若仍有真实兼容依赖，只断开正式运行路径并登记，不得盲删"。<br>`disposition`：**Phase 8**（随 V4 / Excel 收口一并处置：迁移表单模型、删除 Tk 类） |
| `QA-P6-002` | `CLOSED`（Phase 6 R1） | **候选层 Golden 以实现哈希 pin 冻结了 10 个实现文件，曾被误判为『Phase 6 无权限完成入口语义收口』。** R1 经真实代码审计确认：validator **本就**内置了「历史证据保持不可变、当前实现可以演进」的机制（`tools/validate_phase1_contracts.py` 的 `_historical_hash_reason` 配合 `specs/equipment_efficiency/evidence_registry.json` 的 `historical_repository_hashes`；注册表内既有一条 `golden-case-0.3` 记录，其 reason 已明确写着 later implementation changes must not invalidate already-recorded candidate provenance）。缺口只是**该登记未覆盖 `evaluation_service.py`**。<br>R1 的处理：**未**改写候选文件、**未**改写任何 Approved Golden，只把该实现文件的冻结哈希（`EEF8731E…`，已在冻结提交 `72e8e49` / `90af7f8` 处实测复核一致）补登记为历史证据。此后当前实现可正常演进，历史 provenance 校验仍对其锚定提交严格成立。<br>`closed_by`：`tests/unit/test_phase6_product_shell.py::QaClosureTests::test_evaluation_service_history_is_registered_not_rewritten` |
| `QA-P6-003` | `CLOSED`（Phase 7 重新判断） | **草稿 identity「名称即 ID / 改名等价于新建」**。Phase 7 已取消普通用户「分析草稿」概念，Workspace 退出产品表面，因此**不再新增** `workspace.display_name` / `rename_workspace` 等草稿产品能力。本阶段只保证**内部** identity 稳定：Workspace 的 create/update/load/list/delete 契约与修订号语义保持不变，自动记录流程不依赖 Workspace（`finalize(workspace_id=None)`）。关闭依据：`tests/unit/test_phase7_analysis_history.py` 与 `test_phase3_qt_unified.WorkspaceIsNoLongerAProductConceptTests`。<br>`disposition`：Phase 7 关闭（产品概念消失，问题不再存在） |
| `QA-P6-004` | `NON_FORMAL_SURFACES` | `REGISTERED_DEVIATION` | **非正式 adapter 仍存在，但 Phase 6 未将其升级为正式 Windows UI**：`--web` / `--json` / `--jsonl` / `ApplicationApi` / 遗留 Tk 代码保留为 compatibility / development surface。Phase 6 已在启动入口与文档中明确：**正式发布用户表面 = PySide6 Qt Desktop**。<br>`disposition`：**Phase 8 / Phase 9**（随适配器与发布收口） |

**Phase 6 R1 结论**：`QA-P5-001`、`QA-P5-002(a)(b)`、`QA-P3-003` 与 `QA-P6-002` 均已在 Phase 6 内**真正关闭**，关闭依据是可复现的机械测试（见各自 `closed_by`）。关闭方式**未**改写候选文件，也**未**改写任何 Approved Golden 的业务真值或历史 provenance；唯一新增的是一条历史实现哈希登记。

### Phase 7 新增登记

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-P7-001` | `RECORD_VERSION_FIELDS` | `REGISTERED_DEVIATION` | **`RecordSnapshot.ruleset_version` 与 `calculator_version` 实际存的是 rule profile 标识**（如 `pump_water`），不是真正的版本号。Phase 7 审查确认属实。<br>当前 Result 契约中**没有**任何真实可用的规则集版本 / 计算器版本字符串，因此**不得编造**版本值。<br>Phase 7 的处理：① **不伪造**版本；② Presentation 不再把这些字段当作版本展示，审计信息区标注为「规则集标识」；③ 只对新 Record 修正明显错误语义需要 schema 变更，而 Phase 7 默认不改 `records.sqlite` schema，故**不自行变更**。<br>`disposition`：随将来真正引入 Calculator / RuleSet 版本化证据的任务一并处理 |
| `QA-P7-002` | `LEGACY_RECORD_BASIS` | `REGISTERED_DEVIATION` | **Phase 3～6 形成的旧 Record 未冻结完整标准依据**（如缺 `data_version` / `pack_hash` / `table` / `clause`）。<br>Phase 7 **不**追溯 UPDATE、不补写当前数据、不重新计算、不伪造 provenance；记录详情对这些旧记录**降级显示**「该历史记录保存时未包含完整标准依据。」（机械测试覆盖）。<br>新 Record 已冻结快照自身真实存在且可信的依据。`disposition`：保持现状（历史事实不得追溯改写） |

### Phase 8 承接登记

Phase 8 正式承接以下与 Excel 批量评价直接相关的条目（**不借本 Phase 顺便清理全部 legacy backlog**）：

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-EXCEL-001` | `EXCEL_READER` | **CLOSED（Phase 8A）** | `ooxml_reader._parse_number` 曾把非整数数值 **Decimal → float** 再送进正式评价链，等于把 Numeric Contract 降级。**已修复**：整数返回 `int`、其余保留 `Decimal`，**绝不经过 float**；覆盖整数 / 普通小数 / 35 位长小数 / 科学计数法 / 大整数 / 文本 / 空值。并新增正式 Reader `pump_workbook_reader`，只读正式输入列、行启用为语义式、表头做防御性校验。<br>`disposition`：Phase 8 关闭（测试见 `tests/unit/test_phase8a_template_reader.py`） |
| `QA-P5-003` | `V4_EXCEL_ADAPTER` | **CLOSED（Phase 8 / 8B 正式 E2E 确认）** | 「Excel 侧存在独立业务算法」问题**已解决**：正式 V6 模板的「离心泵」Sheet 已退出全部可独立产出 GB19762 结果的 Excel 公式（`K`/`L`/`N:X`/`AA`），改由软件批量评价写入；Excel 只做批量输入/输出载体，每行都调用正式 Application 契约。V4 模板降为 `LEGACY`（不再作为正式用户模板，实现保留）。<br>`disposition`：Phase 8 关闭（门禁见 `tools/check_v6_pump_template.py`） |
| `QA-P6-001` | `LEGACY_TK` | **OPEN（Phase 8 明确不清理）** | legacy Tk 桌面窗口实现保留但不接线。Phase 8 **不**删除该实现，也**不**触碰其表单模型依赖链；`disposition` 保持 Phase 8 之后按需处理。 |

### Phase 8 disposition review（2026-10-07）

Phase 8 已 `EXECUTION_COMPLETE` 并合并 PR #16（`64b656ee`），不得再留下「目标阶段是 Phase 8、但仍开放」的幽灵待办。
本节对原 `target_phase = Phase 8`（含 `Phase 1/8`）且状态仍为 `OPEN` / `VERIFY` 的 **17** 项，
逐项复核**真实引用与正式发布路径**后重新分派。**只重分派去向，不关闭任何问题**；`status` 一律保持原值。

分派口径（统一使用，非机械改期）：

| 处置 | 含义 |
|---|---|
| `Phase 9` | 位于 V1 **发布前门禁 / 发布工具**上，其正确性直接影响发布判定 |
| `VERIFY_BEFORE_PHASE9` | 目前无法判定是否进入正式发布链，须在 Phase 9 之前先给出结论（修复 / 明确不发布 / 量化） |
| `POST_V1` | 落在 **V4 / legacy Excel 适配器路线**（V1 明确不发布该适配器；重开 V4 或进入第二标准时处理） |
| `Future` | 与具体路线无关的通用清理 / 死代码（V1 不排期） |
| `SUPERSEDED` | 其功能需求已被 Phase 8 正式链取代，且有明确证据（0 入边引用 + 机械测试） |

| issue_id | 原 target_phase | 新 disposition | 判定依据（真实引用核实） |
|---|---|---|---|
| `QA-P1-003` | Phase 8 | **Phase 9** | 发布审计缺 `wheel_pmsm_status` 键，属发布前门禁完整性 |
| `QA-P0-001` | Phase 1/8 | **VERIFY_BEFORE_PHASE9** | V4 motor reader 可能错误结论；表面 `NOT_SHIPPED` 但 CLI `--v4-sheet` 可达 → 发布前须有「修复 or 明确不发布」结论 |
| `QA-P0-002` | Phase 1/8 | **VERIFY_BEFORE_PHASE9** | 同上（V4 结果写回） |
| `QA-AUD-011` | Phase 8 | **POST_V1** | `v4_validation` / `input_normalization` 只被 non-formal V4 / legacy API 链引用；正式 Qt 分析页不经 `schema_constraints` |
| `QA-AUD-013` | Phase 8 | **POST_V1** | `v4_validation.py` 属 V4 adapter 链 |
| `QA-AUD-014` | Phase 8 | **POST_V1** | `input_normalization.py` 属 V4 / legacy 链 |
| `QA-AUD-019` | Phase 8 | **POST_V1** | `v4_writer.py` 在 `src/` 内 **0 入边引用**；正式写回由 `pump_result_writer` 承担 |
| `QA-AUD-020` | Phase 8 | **SUPERSEDED** | `legacy_importer` / `legacy_writer` / `report_exporter` / `template_builder` 4 个 stub 0 入边引用，`tests/unit/test_disabled_adapters.py` 机械断言其 `FeatureNotEnabled`；正式 Excel 能力已由 Phase 8 的 V6 批量链提供 |
| `QA-AUD-021` | Phase 8 | **Future** | `strict_importer.py` 无任何入边引用（死别名） |
| `QA-AUD-026` | Phase 8 | **POST_V1** | `v4_input_adapter.py` 的 `adapt_many` / `validate_draft` 属 V4 adapter |
| `QA-AUD-027` | Phase 8 | **POST_V1** | 正式链只经 `ooxml_reader`；重复落在 legacy `v4_reader` / `v4_template_audit` |
| `QA-AUD-028` | Phase 8 | **POST_V1** | 同 027（`ooxml_reader` 与 `v4_writer` 列号换算重复） |
| `QA-AUD-029` | Phase 8 | **Phase 9** | 模板名 / 设备 sheet 配置同时被正式 `template_resource`（`V6TemplateResource`）与发布审计 `v4_template_contract` 持有，漂移直接影响发布审计 |
| `QA-AUD-042` | Phase 8 | **VERIFY_BEFORE_PHASE9** | `template_resource` 在正式批量链上；Phase 8 实测 10,000 行峰值 952 MB → 发布前须量化结论 |
| `QA-AUD-050` | Phase 8 | **Phase 9** | 发布审计 `tools/audit_release.py` 直接调用 `audit_v4_template`；其中硬编码国标号 / 状态串漂移会污染发布门禁 |
| `QA-AUD-051` | Phase 8 | **VERIFY_BEFORE_PHASE9** | OOXML 解析重复横跨正式 `ooxml_reader` 与发布审计用 `v4_template_audit`，须先确认正式链是否单一来源 |
| `QA-AUD-052` | Phase 8 | **POST_V1** | `v4_writer.py:450-451` 恒假分支，属 V4 adapter |

小结：`Phase 9` **3** 项、`VERIFY_BEFORE_PHASE9` **4** 项、`POST_V1` **8** 项、`Future` **1** 项、`SUPERSEDED` **1** 项。

- 历史 `DEFER_TO_P8` 处置原文**保留不改写**；历史处置表的 `target_phase` 单元格标注为 `Phase 8（历史）→ <新去向>`，
  权威 audit 表（「Phase 0 当前发现」「第三方 55 项逐项登记」）已直接写入新 `target_phase`。
- **本节不关闭任何条目**，也不改变任何业务结论；`QA-P0-001` / `QA-P0-002` 的 P0 属性与 `NOT_SHIPPED` 表面定义保持不变。
- 判定依据限于**只读核实**（`git grep` 真实入边引用 + 正式链 import 关系），未修改业务代码、Golden、Canonical、Numeric 与 Excel Reader/Writer。
- 复扫口径：`target_phase` 含 `Phase 8` 且 `status` 仍为 `OPEN` / `VERIFY` / `REGISTERED_DEVIATION` 的条目 = **0**。

### 已完成 Phase（1～4）遗留待办 disposition review（2026-10-07）

同一套口径的第二轮：Phase 1～7 均已独立验收并合并，凡 `target_phase` 指向**已完成 Phase**
且状态仍为 `OPEN` / `VERIFY` 的条目，同样不得留作幽灵待办。本轮覆盖
**28 行 / 24 个编号**（`QA-AUD-010`、`QA-AUD-030`、`QA-AUD-031` 各出现在 2 张表；
`QA-AUD-011` 的主行已在 Phase 8 轮定案为 `POST_V1`，本轮只对齐其 P0 复核表行）。
处置口径与 Phase 8 轮相同（见上一节口径表）。**只重分派去向，不关闭任何问题**；`status` 保持原值。

| issue_id | 原 target_phase | 新 disposition | 判定依据（只读核实） |
|---|---|---|---|
| `QA-P1-005` | Phase 1 | **Future** | 治理数字漂移（历史审计 60 vs 实测）；当前计数已由可重跑命令 + known-regression 比较常设化 |
| `QA-P1-006` | Phase 1 | **Future** | 17 pack 的 `active` ≠ 已验收；正式 Qt 仅提供离心泵链，其余标准包属后续标准扩展 |
| `QA-AUD-004` | Phase 4 | **SUPERSEDED** | `evaluation_engine.py` 在 `src/` 内 **0 入边引用**（已无调用方） |
| `QA-AUD-005` | Phase 3 | **Future** | `device_types.py` 路由可读性 / 理解成本，结构债务，无错误结论证据 |
| `QA-AUD-006` | Phase 3 | **Future** | 正式链已改用专用契约 `PumpAnalysisResult`；旧 `EvaluationResult` 职责拆分属重构 |
| `QA-AUD-007` | Phase 4 | **Future** | `metadata.py` 体积与职责混合，结构债务 |
| `QA-AUD-008` | Phase 4 | **Future** | `device_specs.py` 导入副作用，结构债务 |
| `QA-AUD-009` | Phase 3 | **Future** | 标准 / 字段 / 示例数据多份硬编码；正式标准事实以 Canonical 为准，属数据卫生治理 |
| `QA-AUD-010` | Phase 1（P0 复核表为 Phase 1） | **VERIFY_BEFORE_PHASE9** | `evaluators/shared.py:_interval_hit` 位于业务判定链，边界错误可能给错结论；P0 且尚未证明安全 |
| `QA-AUD-011` | Phase 1/2（P0 复核表） | **POST_V1**（对齐主行定案） | `v4_validation` / `input_normalization` 属 V4 / legacy 链 |
| `QA-AUD-012` | Phase 3 | **POST_V1** | `evaluation_service.py` 上帝方法属 legacy 服务；正式 Qt 链不经该实现 |
| `QA-AUD-015` | Phase 3 | **POST_V1** | legacy API / 桌面 fallback 表单重复；`metadata_projection` 只被 legacy 两处引用，Qt 不使用 |
| `QA-AUD-016` | Phase 3 | **POST_V1** | 结论列标题重复属 legacy 展示面 |
| `QA-AUD-017` | Phase 3 | **POST_V1** | 基础信息字段元组重复属 legacy 展示面 |
| `QA-AUD-018` | Phase 3 | **POST_V1** | Python / JS 结果摘要重复属 legacy Web 面 |
| `QA-AUD-022` | Phase 2/3 | **SUPERSEDED** | `sqlite_repository` / `sqlite_project_repository` **0 入边引用**，`test_disabled_adapters` 机械断言其 disabled |
| `QA-AUD-024` | Phase 2/3 | **Future** | ports 已由正式批量链接入（`pump_workbook_reader` / `pump_result_writer`）；其余端口悬空属结构清理 |
| `QA-AUD-030` | Phase 1 | **POST_V1** | 双真相源的另一半 `v4_validation.py` 属 V4 / 非正式链 |
| `QA-AUD-031` | Phase 3 | **SUPERSEDED** | Owner 决定（2026-10-02，Phase 5 / 7 收口）：评价日期不是业务门禁，不改变等级 / `evaluation_status`；正式路径自动取本机当天 |
| `QA-AUD-038` | Phase 3 | **Future** | 损坏文件异常根因保留属诊断质量，不影响业务结论 |
| `QA-AUD-039` | Phase 3 | **POST_V1** | `evaluation_service.py` / `v4_validation.py` 属 legacy 链 |
| `QA-AUD-041` | Phase 3 | **VERIFY_BEFORE_PHASE9** | `json_repository.py` 在正式链上；缺键 `KeyError` / 缺文件静默空记录可能掩盖数据问题，须在发布前给出结论（`audit_release` 已显式检查 manifest / 包文件存在性，属部分缓解） |
| `QA-AUD-045` | Phase 3 | **POST_V1** | legacy 桌面上帝窗口；Qt 不引用 `desktop/main_window` |
| `QA-AUD-053` | Phase 4 | **Future** | ports 导出策略不一致，契约整理项 |
| `QA-AUD-054` | Phase 4 | **Future** | `schema_constraints.py` 等缺专门单测（非正式链） |

小结（编号级）：`Future` **11**、`POST_V1` **8**（另 `QA-AUD-011` 对齐 1）、
`VERIFY_BEFORE_PHASE9` **2**、`SUPERSEDED` **3**、`Phase 9` **0**。

- 本轮**没有**条目进入 `Phase 9`：这 24 项均不位于发布门禁 / 发布工具或包装路径上
  （对比 Phase 8 轮的 3 项 `Phase 9`，其模块被 `tools/audit_release.py` 直接调用）。
- 历史处置表（「Phase 2 最小工程切片处置」「Phase 3 统一纵向闭环处置」）中这些编号的
  `target_phase` 单元格同步标注为 `<原值>（历史）→ <新去向>`，历史 `disposition` 原文不改写。
- 复扫口径：**有 `status` 列的表中**，`target_phase` 指向已完成 Phase（1 / 1-2 / 2-3 / 3 / 3-4 / 4）
  且状态开放（`OPEN` / `VERIFY` / `REGISTERED_DEVIATION`）的条目 = **0**。
- 与 Phase 8 轮一致：未改业务代码、Golden、Canonical、Numeric、Excel Reader/Writer；
  未关闭任何条目；`QA-AUD-010`、`QA-AUD-030`、`QA-AUD-031` 的 P0 属性保持不变。

### Phase 8 R1 登记（独立验收 blocker）

被独立验收 `BLOCKED` 的 head 为 `8cb6eec1845cc26bed43e3dfea2dec1c5880729c`。
四项 blocker 均为真实缺陷，R1 已逐项修复并附机械回归：

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-P8-001` | `EXCEL_RESULT_THRESHOLDS` | **CLOSED（Phase 8 R1）** | 结果 Workbook 的 U/V/W 恒为空：Writer 只消费 `calculation_trace.derived`，而**等级限值在正式 `PumpAnalysisResult.thresholds`**。已新增 `THRESHOLD_COLUMNS` 映射，U/V/W 直接取自正式 thresholds；无正式阈值的状态不写、不伪造。回归：`test_phase8r1_blockers.B1ThresholdWritebackTests` |
| `QA-P8-002` | `BATCH_STATISTICS` | **CLOSED（Phase 8 R1）** | `INVALID_INPUT` 被当成正式评价：负流量 + 数量=7 时计入 evaluated_quantity=7、input_error_rows=0、attention 为空，并输出「无法判定」。已改为归入**输入错误**：数量合法时计入 total_quantity 与 input_error_quantity，但不计入 evaluated_quantity、不进入任何正式结论数量，且必须出现在需要关注列表。回归：`B2InvalidInputTests` |
| `QA-P8-003` | `RESULT_WORKBOOK_FIDELITY` | **CLOSED（Phase 8 R1）** | Writer 用 openpyxl 整体重写工作簿，把用户输入精度从 35 位改写成 `100.1234567890124`。已改为**逐字节复制原文件 + 只对结果列做 XML 定点补丁**（数值 `<v>`、文本 inlineStr）。回归：`B3InputPrecisionTests`（含"只有该 worksheet 部件变化"的机械证明） |
| `QA-P8-004` | `BATCH_PROVENANCE` | **CLOSED（Phase 8 R1）** | `self._first_result` 为实例级状态，导致全非法批次沿用上一批的 Canonical / Numeric 引用。已彻底移除实例级批次状态，改为 `evaluate_workbook` 内局部 `_BatchProvenance`，只记录当前批次真正执行过正式评价的 Result。回归：`B4ProvenanceIsolationTests`（含连续三批与"实例上不得存在批次状态"守卫） |

UI 简化（Owner 决定，非缺陷）：UI01 术语简化 / UI02 结果区删解释与依据 /
UI03 记录页删「审计信息」展示 / UI04 日志级别中文化。四项均只改 Presentation，
底层数据、字段 identity 与业务计算契约未变。

### Phase 8 R1W 登记（复审清单外审计发现的 Writer 阻断）

复审对 head `348a1994352e9e16d841a0589b0af2416a83b0df` 再次给出 `PHASE_8_BLOCKED`，
并提出两个**同一根因**的新 Writer 阻断：Writer 用属性顺序假设匹配 OOXML 元素，
而 OOXML 不保证属性顺序。

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-P8-005` | `RESULT_WRITER_ROW_MATCH` | **CLOSED（Phase 8 R1W）** | `<row ht="42" customHeight="1" s="184" r="4">`（`r` 不在首位）时，Writer 的行定位失败，结果**整行未写出**，却仍保存"成功"批次记录（静默漏写）。已改为**顺序无关的行扫描器**；且任何结果行定位不到即抛 `ResultWorkbookWriteError`，批次整体失败、**不保存** batch_record。回归：`test_phase8r1w_writer_structure` |
| `QA-P8-006` | `RESULT_WRITER_CELL_MATCH` | **CLOSED（Phase 8 R1W）** | `<c s="234" r="U4" t="n">`（`s` 在 `r` 之前）时未识别既有单元格，又插入一个 `U4`，输出出现**重复坐标**（工作簿结构无效）。已改为按 `r` 属性（坐标）匹配并就地替换、保留原样式；写回后自校验每个目标坐标恰好出现一次。回归：`test_phase8r1w_writer_structure`（含"全表无重复坐标"机械校验） |

**教训（已落到实现约定）**：OOXML 元素的属性顺序、命名空间前缀、自闭合形式
都**不是**契约；任何位置/顺序假设都会在真实 Excel 产物上失败。
解析必须顺序无关，且"没写成"必须是**硬失败**而不是静默成功。

### Phase 8 R3 登记（OOXML 命名空间保持）

复审对 head `fec8fd0ddbcc64e861e05a6ad204463a6d7fcc0c` 再次给出 `PHASE_8_BLOCKED`，
本轮 blocker 是 namespace 语义被破坏。

| issue_id | 表面 | 状态 | 说明 |
|---|---|---|---|
| `QA-P8-007` | `OOXML_DEFAULT_NAMESPACE_DECISION` | **CLOSED（Phase 8 R3）** | `_has_default_namespace()` 只判断"是否存在 `xmlns="…"`"，不判断 URI，于是把「存在任意默认 namespace」当成「已是 SpreadsheetML」。在 `xmlns="别的URI"` + `xmlns:x="MAIN_NS"` 的合法工作表上，Writer 删掉了 `x:` 前缀与 `xmlns:x`，让**全部** SpreadsheetML 元素落进别的命名空间。已改为 `_default_namespace_uri()` 取得真实 URI，并按 A（无默认）/ B（==MAIN）/ C（!=MAIN）三分法决策：**仅 A/B 允许去前缀，C 必须保留**。回归：`test_phase8r3_namespace_preservation` |
| `QA-P8-008` | `WRITER_CELL_CHILD_NAMESPACE` | **CLOSED（Phase 8 R3）** | `_cell_element_xml` 只给 `c` 加前缀，内容元素 `<v>/<is>/<t>` 未加；在默认命名空间非 MAIN 的工作表里，新插入单元格的**值**会落进别的命名空间。已改为前缀应用到该单元格全部子元素。回归：同上（语义门禁会直接拒绝此类输出） |

**新增最终语义门禁**：`_assert_main_namespace_semantics` 用真正的 namespace-aware
解析器（`ElementTree` 展开 QName）校验 `worksheet`/`sheetData`/`row`/`c`/`v`
等核心元素仍属 MAIN_NS。仅"XML 良构"不再算通过；门禁失败 = Writer 硬失败 =
不产出结果文件、不保存成功 `batch_record`。

**教训**：namespace 正确性不能靠字符串判断（"有没有 xmlns=" 不等于"绑定对不对"），
必须用能解析 QName 的解析器做最终门禁。

### Phase 8 R4 登记（全面诊断的清单外独立发现）

诊断对象 head `5fea7fa0b79789d49277c504b0913266518416da`（`PHASE_8_BLOCKED`）。
本轮不再按已知反例逐项扩展正则，而是把**身份判定集中到真正的 XML 词法/命名空间
模型**（`xml_model.py`），并用**独立解析器**做输入→输出校验
（`result_invariants.py`）。

| issue_id | 级别 | 表面 | 状态 | 说明 |
|---|---|---|---|---|
| `QA-P8-009` | P1 | `WRITER_ATTR_QUOTING` | **CLOSED（R4）** | 合法单引号属性 `r='U4'` 绕过唯一性门禁：输出出现 **2 个真实 `{MAIN}c[@r='U4']`**（一个空、一个 79.786165），仍保存成功 `batch_record`。词法层现按 XML 规范同时支持单/双引号与实体解码。回归：`test_phase8r4_writer_identity` |
| `QA-P8-010` | P1 | `WRITER_ATTR_NAMESPACE` | **CLOSED（R4）** | 属性按 local-name 取用，`r` 与扩展命名空间的 `e:r` 被合并成同一个键，后者覆盖前者：真正的 U4 被漏掉 → 重复坐标，且正式 Reader reopen 后 U4 **为空**（正式限值静默丢失）。属性身份现包含 namespace（未加前缀的属性**没有** namespace）。回归：同上 |
| `QA-P8-011` | P2 | `NAMESPACE_GATE_SCOPE` | **CLOSED（R4）** | 语义门禁遍历整棵树、按 local-name 要求 `t/c/row` 全属 MAIN_NS，误拒合法扩展内容（`extLst` 内同名 `e:t`），整批无法完成。门禁现只沿**正式路径** `worksheet/sheetData/row/c/v` 检查，且只下探 MAIN_NS 子树。回归：同上 |
| `QA-P8-012` | P2 | `ATOMIC_FILE_COMMIT` | **CLOSED（R4）** | 直接 `ZipFile(destination, 'w')` 落盘；磁盘写失败会在**最终文件名**留下残缺 Workbook（仅 1 个 entry），重试还得到 `ResultWorkbookExistsError`。现改为**临时文件 → 重新打开复验 → `os.replace` 原子提交**，任何失败都清理半成品。回归：同上 |
| `QA-P8-013` | P2 | `QT_BATCH_BLOCKING` | **CLOSED（R4）** | 整批评价在 Qt 主线程同步执行（10,000 行实测约 559s），界面在此期间无法处理事件。现改为工作线程执行 + 进行中状态 + 按钮守卫；计算/统计/数据库语义未变。回归：`test_phase8r4_qt_background` |
| `QA-P8-014` | P1 | `WRITER_NESTED_PREFIX_SCOPE` | **CLOSED（R4）** | 前缀归一化按**根层声明**推全局；后代重绑定同一前缀时扩展 payload 被静默改写进 SpreadsheetML 命名空间。现按**逐元素词法作用域**判定，且开/闭合标记配对同进退。回归：`test_phase8r4_writer_identity` |

### 性能缺陷（本轮自行引入并修掉）

`WorksheetPatch.apply` 原先逐次拼接字符串（`out = out[:s] + r + out[e:]`），
在上万个编辑时是 O(n²)：实测 1,000 行补丁阶段 18.7s 中有 15.6s 花在这里，
5,000 行整批达 460s。改为收集片段后**一次 `join`**，并改为**一次解析、收集全部
编辑、单遍应用**（不再逐行重解析整份 XML）。修复后线性：

```text
500 行 3.4s   2,000 行 12.8s   5,000 行 31.8s   10,000 行 63.8s
```

**教训（已落到实现约定）**：

1. 身份判定必须来自真正的 XML 词法/命名空间解析：属性顺序、单/双引号、命名空间
   前缀、**属性命名空间**、**嵌套重绑定**都是独立的正确性维度，不能用"假设 + 正则"。
2. 解析与判定要**顺序无关**、**作用域正确**；命名空间决策必须区分
   「无默认／== MAIN_NS／!= MAIN_NS」三种情况。
3. 自检必须**独立**：不要用 Writer 自己的扫描器证明 Writer 正确；输出校验用
   expat（QName + 无命名空间 `r`）与 ElementTree（路径 + 命名空间语义）。
4. "没写成"必须是**硬失败**：定位不到行、坐标不唯一、命名空间错误、文件未原子提交，
   都不得保存成功批次记录，也不得留下残缺结果文件。
5. 大批量性能要用**真实规模**测量；字符串拼接与"逐行重解析"是两个已经踩到的 O(n²) 陷阱。
