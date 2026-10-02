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
| QA-P0-001 | BASELINE-TEST-001 | motor_lv | `tests/unit/test_v4_reader.py::test_copied_v4_row_is_read_and_evaluated` | 7.5 kW 电机 V4 行期望 `1级`，实际 `无法判定` | 可能错误结论 | H | NOT_SHIPPED | P0 | Phase 1/8 | OPEN | Python 3.13 全量重跑 | 先核对标准日期、输入映射和 fixture；不在 0A 修 |
| QA-P0-002 | BASELINE-TEST-002 | motor_lv | `tests/unit/test_v4_writer.py` 两个结果写回测试 | V4 写回的等级/三个等级指标为空或为 `无法判定` | 可能错误结论 | H | NOT_SHIPPED | P0 | Phase 1/8 | OPEN | Python 3.13 全量重跑 | V4 为冻结端口；进入发布前必须关闭或有明确不发布决策 |
| QA-P1-003 | BASELINE-TEST-003 | shared | `tests/unit/test_release_audit.py` | Release audit 结果缺少 `wheel_pmsm_status` 键 | 影响发布审计完整性，不直接改变评价结论 | M | DEV_ONLY | P1 | Phase 8 | OPEN | Python 3.13 全量重跑 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：先修复审计契约/fixture，再作为发布门禁 |
| QA-P1-004 | BASELINE-TEST-004 | shared | `.venv_build` | 3.11 构建环境缺 `openpyxl`、`python-docx`、`pytest`，导致 10 error | 结果不可完整复验 | M | DEV_ONLY | P1 | Phase 0 follow-up | EVIDENCE | BASELINE.md | 保留完整 Python 3.13 结果；不把缺依赖误报为源码 PASS |
| QA-P1-005 | BASELINE-TEST-005 | shared | tests inventory | 历史审计声称 60 个真实 unittest；Phase 0 实测 54 个 test module、887 项 unittest | 治理数字漂移 | M | DEV_ONLY | P1 | Phase 1 | OPEN | 第三方 #55 + unittest | 以可重跑命令和本次数字为当前事实，历史数字仅作 Historical Evidence |
| QA-P1-006 | BASELINE-SMOKE-001 | shared | `standard_manifest.json` / resource packs | 17 pack 报告 `active`，但 active 不等于来源/边界/Golden 已验收 | 可能把可加载误认为业务可信 | M | V1_RUNTIME | P1 | Phase 1 | OPEN | status smoke + ASSET_AUDIT | Phase 1 逐 pack 冻结 Canonical/source/readiness |
| QA-P1-007 | BASELINE-PERF-001 | shared | `JsonStandardRepository.get_pack` | 同一 pack 重复读取仍 read_text + json.loads + deepcopy | 性能退化，不直接改结论 | M | V1_RUNTIME | P1 | Future (原 Phase 2) | OPEN | 3.225 ms 首读；1.947 ms 重读 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：Phase 0 只记录，不缓存重构 |

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
| QA-AUD-001 | AUD-001 | shared | `domain/devices/` | 8 个空壳与 `domain/evaluation` 并存；误认第二正式实现 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Future (原 Phase 2) | OPEN | CSV#1 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：标为 DELETE_CANDIDATE，先完成动态/构建/外部契约证明 |
| QA-AUD-002 | AUD-002 | shared | `device_evaluators.py` + evaluators | 兼容门面与延迟反向导入；维护变化可能影响评价 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Future (原 Phase 2) | OPEN | CSV#2 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：当前仍是运行依赖，禁止 0A 删除 |
| QA-AUD-003 | AUD-003 | motor | `evaluators/motor.py` | 字符串 `getattr` 动态 helper；改名可能静默失效 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Future (原 Phase 2) | OPEN | CSV#3 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：改为静态契约前保留回归 |
| QA-AUD-004 | AUD-004 | shared | `evaluation_engine.py` | `inspect.signature` 兼容 2/3 参数掩盖契约错误 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 4 | OPEN | CSV#4 | DEFER_TO_P4：真实样板后再通用化；不在薄壳阶段重构业务；原决定：唯一 evaluate 契约留 Phase 2 |
| QA-AUD-005 | AUD-005 | shared | `device_types.py` | 15 公共类型、17 Profile 和旧 fan 入口并存；路由理解成本高 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 1/2 | OPEN | CSV#5 | Phase 0 已确认映射权威，暂不合并 |
| QA-AUD-006 | AUD-006 | shared | `domain/common/models.py` | `EvaluationResult` 混合结果、轨迹、淘汰和质量 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 3 | OPEN | CSV#6 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：保持现有契约，未来按职责拆分 |
| QA-AUD-007 | AUD-007 | shared | `metadata.py` | 1687 行混合枚举、V4 映射、展示和 profile 构建 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 1/2 | OPEN | CSV#7 | 已在 ASSET_AUDIT 完成职责分类，暂不迁移 |
| QA-AUD-008 | AUD-008 | shared | `device_specs.py:179-188` | 导入时就地修改 `DEVICE_SPECS` | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 4 | OPEN | CSV#8 | DEFER_TO_P4：真实样板后再通用化；不在薄壳阶段重构业务；原决定：记录为导入副作用，不在 0A 重写 |
| QA-AUD-009 | AUD-009 | all | `device_specs.py`、`metadata.py`、`entrypoint.py` | 标准/字段/示例硬编码多份，可能产生数据漂移 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 1/2 | OPEN | CSV#9 | Python 数据先盘点，不能直接删除 |
| QA-AUD-010 | AUD-010 | shared | `evaluators/shared.py:_interval_hit` | 核心区间解析难验证，边界错误可能给错结论 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | Phase 1 | VERIFY | CSV#10 + source；Phase 1 已执行 12 个开闭端点 probe，全部符合预期 | Phase 1 review=`NEEDS_MORE_EVIDENCE`；现有 probe 未发现错误，但尚缺跨标准/Golden 的完整覆盖；不进入 Hotfix |
| QA-AUD-011 | AUD-011 | shared | `v4_validation.py` / `input_normalization.py` | 规范化重复实现，差异可能改变输入含义 | 可能影响业务结论；需标准/Golden 证据 | H | NOT_SHIPPED | P0 | Phase 1/2 | VERIFY | CSV#11；pump_water 的完整别名与 canonical 输入输出一致，V4 validation valid/invalid probe 有预期结果 | Phase 1 review=`NEEDS_MORE_EVIDENCE`；样板证据不能代表全 Profile 的共享风险；不重构 |
| QA-AUD-012 | AUD-012 | shared | `evaluation_service.py:148-426` | 279 行上帝方法，门禁分支难审计 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 3 | OPEN | CSV#12 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：结构债务，不因严重度直接 Hotfix |
| QA-AUD-013 | AUD-013 | shared | `v4_validation.py` | 882 行、多 sheet 特例链，新增规则易漏 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 8 | OPEN | CSV#13 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：Import Contract 冻结后拆分 |
| QA-AUD-014 | AUD-014 | shared | `input_normalization.py` | 226 行、16 类转换硬编码，输入错误风险 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 1/2 | OPEN | CSV#14 | 先建立 Product/Profile Schema |
| QA-AUD-015 | AUD-015 | shared | `application_api.py` / `main_window.py` | fallback 表单构建重复，UI 可能与 API 不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | H | PROTOTYPE | P2 | Phase 3 | OPEN | CSV#15 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：暂由 `metadata_projection` 共享，UI 非 V1 门禁 |
| QA-AUD-016 | AUD-016 | shared | 多处 conclusion label | 同一结论列标题重复，展示可能漂移 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | Phase 3 | OPEN | CSV#16 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：Presentation 清理阶段处理 |
| QA-AUD-017 | AUD-017 | shared | `application_api.py` / `main_window.py` | 基础信息字段元组重复 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | Phase 3 | OPEN | CSV#17 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：不影响当前核心评价 |
| QA-AUD-018 | AUD-018 | shared | `main_window.py` / `web/server.py` | 结果摘要 Python/JS 重复，说明可能不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | Phase 3 | OPEN | CSV#18 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：API 摘要结构化后处理 |
| QA-AUD-019 | AUD-019 | shared | `infrastructure/excel/v4_writer.py` | 完整 writer 生产链 0 引用，V4 结果可能无法交付 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 8 | OPEN | CSV#19 + QA-P0-002 | V4 未纳入当前首发，不接线 |
| QA-AUD-020 | AUD-020 | shared | `excel/legacy_*`、`report_exporter.py`、`template_builder.py` | 4 个 FeatureNotEnabled 空桩，制造能力错觉 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 8 | OPEN | CSV#20 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：DELETE_CANDIDATE，先查契约/构建/测试 |
| QA-AUD-021 | AUD-021 | shared | `strict_importer.py` | 3 行别名子类无 runtime 引用 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 8 | OPEN | CSV#21 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：暂保兼容名，后续统一 |
| QA-AUD-022 | AUD-022 | shared | SQLite repositories | 两个空桩仓储，实际持久化不存在 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 1/2/3 | OPEN | CSV#22 + ADR-005 | 按已批准三库方向设计，不在 0A 删除 |
| QA-AUD-023 | AUD-023 | shared | `cleaning_service.py` / `import_service.py` | 0 引用服务，可能是未完成能力或死代码 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Future (原 Phase 2) | OPEN | CSV#23 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：DELETE_CANDIDATE，先查外部契约 |
| QA-AUD-024 | AUD-024 | shared | `application/ports/*.py` | Protocol 0 引用，实际实现未显式接入 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 2/3 | OPEN | CSV#24 | PARTIAL_IN_P2：仅完成 settings 端口/存储；原业务仓储与其他端口仍开放；原决定：保留契约方向，阶段性补接线 |
| QA-AUD-025 | AUD-025 | shared | `v4_template_audit.py` / `config/settings.py` | 0 引用包装和默认设置 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Future (原 Phase 2) | OPEN | CSV#25 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：不影响 V1，删除前做动态引用检查 |
| QA-AUD-026 | AUD-026 | shared | `v4_input_adapter.py` | `adapt_many`、`validate_draft` 未接线 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 1/2 | OPEN | CSV#26 | Import Contract 确认后接入或删除 |
| QA-AUD-027 | AUD-027 | shared | OOXML 解析三处 | sheet 名和 rels 解析重复，修复容易不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 8 | OPEN | CSV#27 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：不在冻结 V4 端口中重构 |
| QA-AUD-028 | AUD-028 | shared | `ooxml_reader.py` / `v4_writer.py` | 列号互换换算重复 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 8 | OPEN | CSV#28 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：归入 OOXML 工具清理 |
| QA-AUD-029 | AUD-029 | shared | `template_resource.py` / `v4_template_contract.py` | 模板名、sheet 清单和说明重复配置 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 1/2 | OPEN | CSV#29 | Import Contract 单一来源 |
| QA-AUD-030 | AUD-030 | shared | `v4_validation.py` | 手工规则表和 metadata 派生规则双真相源 | 可能影响业务结论；需标准/Golden 证据 | M | NOT_SHIPPED | P0 | Phase 1 | VERIFY | CSV#30；pump_water 元数据字段约束与 V4 valid/zero/fraction/percent probes 未发现当前输入差异 | Phase 1 review=`NEEDS_MORE_EVIDENCE`；样板路径未证明全 Profile 无差异；待 Import/Profile 矩阵；未授权 Hotfix |
| QA-AUD-031 | AUD-031 | shared | 多处默认判定日期 | 日期硬编码可能选错标准生效状态 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | Phase 1/2 | VERIFY | CSV#31；default/explicit `2026-08-23` 一致，`2026-02-28` 与 `2026-03-01` 明确跨过实施日期 | Phase 1 review=`NEEDS_MORE_EVIDENCE`；Golden 已显式填写 `as_of`，但默认日期是否允许仍需产品/业务决策；不改实现 |
| QA-AUD-032 | AUD-032 | shared | `__init__.py`、`pyproject.toml`、`build_msi.py` | 版本号 0.2.1 多处硬编码，追溯可能漂移 | 当前未确认影响 V1 业务结论；维护风险待证 | M | DEV_ONLY | P2 | Future (原 Phase 2) | OPEN | CSV#32 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：版本模型由 ADR-003 进入 Phase 1 |
| QA-AUD-033 | AUD-033 | shared | `main_window.py:339` | UI 写死公共类型数量 15 | 当前未确认影响 V1 业务结论；维护风险待证 | L | PROTOTYPE | P2 | Future (原 Phase 2) | OPEN | CSV#33 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：非业务结论问题 |
| QA-AUD-034 | AUD-034 | shared | `application/bootstrap.py` | Application 直接导入 infrastructure | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#34 | CLOSE_IN_P2：按 docs/31 实施；通过对应测试后才关闭，当前 OPEN；原决定：装配方向重做时处理 |
| QA-AUD-035 | AUD-035 | shared | `application/bootstrap.py` / API | Application 反向导入 Presentation，包级环 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#35 | CLOSE_IN_P2：按 docs/31 实施；通过对应测试后才关闭，当前 OPEN；原决定：不在 Phase 0 改结构 |
| QA-AUD-036 | AUD-036 | shared | `bootstrap.load_v4_contract` | `except Exception` 静默降级，模板损坏难诊断 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 2 | OPEN | CSV#36 | CLOSE_IN_P2：按 docs/31 实施；通过对应测试后才关闭，当前 OPEN；原决定：V4 发布前必须限定异常并记录 |
| QA-AUD-037 | AUD-037 | shared | `config/logging.py` | 日志占位，关键路径无可用日志 | 可能影响发布可靠性或长期维护；业务影响待证 | M | DEV_ONLY | P1 | Phase 2 | OPEN | CSV#37 | CLOSE_IN_P2：按 docs/31 实施；通过对应测试后才关闭，当前 OPEN；原决定：安全/发布阶段补齐 |
| QA-AUD-038 | AUD-038 | shared | writer / JSON repository | 损坏文件异常根因可能丢失 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 3 | OPEN | CSV#38 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：统一异常模型，保留根因 |
| QA-AUD-039 | AUD-039 | shared | `evaluation_service.py` / `v4_validation.py` | 裸 KeyError/ValueError 可能中断整批 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 3 | OPEN | CSV#39 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：改为领域 issue 需 Golden 保护 |
| QA-AUD-040 | AUD-040 | shared | `JsonStandardRepository.get_pack` | 每次解析完整 JSON，批量性能随数据量增长 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Future (原 Phase 2) | OPEN | CSV#40 + QA-P1-007 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：先保留实测，再设计缓存 |
| QA-AUD-041 | AUD-041 | shared | `json_repository.py` | manifest 缺键直接 KeyError；缺文件静默空记录；find 线性 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 1/2 | OPEN | CSV#41 | Schema/错误语义进入 Phase 1 |
| QA-AUD-042 | AUD-042 | shared | `v4_writer.py` / `template_resource.py` | 整体读写 xlsx 内存高、临时目录生命周期隐含 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 8 | OPEN | CSV#42 | Excel 后置，不在 0A 优化 |
| QA-AUD-043 | AUD-043 | shared | `web/server.py` / `entrypoint.py` | `--host 0.0.0.0` 无鉴权，可暴露服务 | 可能影响发布可靠性或长期维护；业务影响待证 | M | PROTOTYPE | P1 | Future (原 Phase 2/9) | OPEN | CSV#43 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：Web 非当前 V1 入口，仍需安全处理 |
| QA-AUD-044 | AUD-044 | shared | Web upload `X-Filename` | 文件名拼接宿主路径，存在路径穿越风险 | 可能影响发布可靠性或长期维护；业务影响待证 | M | PROTOTYPE | P1 | Future (原 Phase 2/9) | OPEN | CSV#44 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：上传功能未作为 V1 发布，但不得带风险发布 |
| QA-AUD-045 | AUD-045 | shared | `desktop/main_window.py` | 窗口混合表单、IO、结果展示，270 行上帝窗口 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | Phase 3 | OPEN | CSV#45 | DEFER_TO_P3：依赖正式设备分析 use-case 与业务证据；本轮保持旧路径；原决定：AppShell 以后用真实样板验证 |
| QA-AUD-046 | AUD-046 | shared | `docs/` | 27 个编号清单和多份 HANDOFF 重叠，调度来源不清 | 可能影响发布可靠性或长期维护；业务影响待证 | M | LEGACY | P1 | Phase 0 | MAPPED | CSV#46 + ROADMAP | 本次冻结权威入口，暂不批量移动 |
| QA-AUD-047 | AUD-047 | shared | repository root | 缺 LICENSE/CHANGELOG；README 偏交接文档 | 当前未确认影响 V1 业务结论；维护风险待证 | M | DEV_ONLY | P2 | Future (原 Phase 2/9) | OPEN | CSV#47 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：不影响 Phase 1 业务契约 |
| QA-AUD-048 | AUD-048 | shared | `equip_test.spec` / `build_native.py` | spec 引用旧 standards，和构建脚本重复 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Future (原 Phase 2) | OPEN | CSV#48 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：构建清理前保留 |
| QA-AUD-049 | AUD-049 | shared | `tools/extract_*.py` | G 盘绝对路径，换环境可能误读本机资源 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Future (原 Phase 2) | OPEN | CSV#49 | KEEP_OPEN_FUTURE：当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭；原决定：标记 legacy 或参数化 |
| QA-AUD-050 | AUD-050 | shared | `v4_template_audit.py` | 16 个国标号、GB 28381-2026 和状态字符串硬编码 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Phase 8 | OPEN | CSV#50 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：标准事实不得继续散落 |
| QA-AUD-051 | AUD-051 | shared | OOXML reader / template audit | inline 字符串和 namespace 重复实现 | 当前未确认影响 V1 业务结论；维护风险待证 | L | NOT_SHIPPED | P2 | Phase 8 | OPEN | CSV#51 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：V4 后置处理 |
| QA-AUD-052 | AUD-052 | shared | `v4_writer.py:450-451` | 恒假分支，维护噪音 | 当前未确认影响 V1 业务结论；维护风险待证 | L | NOT_SHIPPED | P2 | Phase 8 | OPEN | CSV#52 | DEFER_TO_P8：Excel/发布外围不属于 settings 工程切片；保留发布前门禁；原决定：不得在 0A 顺手删除 |
| QA-AUD-053 | AUD-053 | shared | `application/ports/__init__.py` | 端口导出策略不一致，外部导入可能遗漏 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Phase 4 | OPEN | CSV#53 | DEFER_TO_P4：真实样板后再通用化；不在薄壳阶段重构业务；原决定：契约整理时修 |
| QA-AUD-054 | AUD-054 | shared | `schema_constraints.py` 等 | 缺专门单测，死代码也缺验证 | 可能影响发布可靠性或长期维护；业务影响待证 | M | DEV_ONLY | P1 | Phase 1/2 | OPEN | CSV#54 | Golden/契约测试规划时补齐 |
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
| `QA-AUD-010` | `AUD-010` | shared | `evaluators/shared.py:_interval_hit` | 核心区间解析可能造成边界结论错误 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | Phase 1 | VERIFY | `NEEDS_MORE_EVIDENCE` | 复跑既有 12 个标准区间 probe：`0.25`、`0.95`、`3.15`、`10`、`17700`、`21000`、`700`、`700.01`、`1000`、`1000.01` 及严格开区间样例，实际结果全部符合预期 | 尚未证明错误；保持 P0/VERIFY，不因 probe 通过而自报关闭 | 以标准原文区间和 Golden Case 扩大覆盖，再决定是否需要最小修复 |
| `QA-AUD-011` | `AUD-011` | shared | `v4_validation.py` / `input_normalization.py` | 规范化重复实现，差异可能改变输入含义 | 可能影响业务结论；需标准/Golden 证据 | H | NOT_SHIPPED | P0 | Phase 1/2 | VERIFY | `NEEDS_MORE_EVIDENCE` | `pump_water` 的短类别和完整 V4 别名均归一化为同一字段；同一输入得到相同等级、指标、限值和查表命中；V4 validation 对合法、零值、分数级数和效率越界分别给出预期问题 | 样板路径未显示业务结论差异，但证据不足以对共享风险作整体 `NOT_P0` 判断；保持 P0/VERIFY，不重构 | 将其他 V1 Profile 纳入 Import Contract/Golden 矩阵；未完成前不删除重复实现 |
| `QA-AUD-030` | `AUD-030` | shared | `v4_validation.py` metadata/manual constraints | 手工规则表和 metadata 派生规则可能形成双真相源 | 可能影响业务结论；需标准/Golden 证据 | M | NOT_SHIPPED | P0 | Phase 1 | VERIFY | `NEEDS_MORE_EVIDENCE` | 元数据字段：流量/扬程/转速为正、级数为整数、效率 1–100；V4 probe 对 0、分数级数、0/101 效率均按预期拒绝；未发现样板输入差异 | 样板未复现错误，不能外推到所有 Profile；保持 P0/VERIFY | 完成各 V1 Profile 的字段约束对照和 Golden 证据；不在 Phase 1 重构校验器 |
| `QA-AUD-031` | `AUD-031` | shared | 默认 `as_of` 与标准实施日期 | 多处默认判定日期可能选择错误的标准生效状态 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | Phase 1/2 | VERIFY | `NEEDS_MORE_EVIDENCE` | 默认/显式 `2026-08-23` 均判为 1 级；显式 `2026-02-28` 在 `2026-03-01` 实施日前拒绝使用该标准；Golden Cases 全部显式记录 `as_of` | 当前未证明错误结论；默认日期是否允许、默认来源和审计展示仍是业务决策 | 在 Result Contract/产品决策中确认 `as_of` 必填或兼容默认，并要求结果带默认来源；不改实现 |

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
> - `pump_chemical` 的 8 条候选**仍未获 V1 Golden 批准**，其 `support_status` 保持 `NOT_IN_RELEASE_SCOPE`。
>
> 历史正文保留不改写；当前权威状态见 [ROADMAP.md](ROADMAP.md)、[TASK_STATE.md](TASK_STATE.md) 与 [V1_SCOPE.md](V1_SCOPE.md)。

## Excel Decimal Ingress（2026-10-02 登记）

本节登记 Excel 数值入口的 Decimal 保真风险。**只登记，不在本轮修改任何 Python 实现。**

| issue_id | legacy_id/audit_id | profile_id | location | description | business_risk | engineering_risk | release_surface | classification | target_phase | status | evidence | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `QA-EXCEL-001` | `V2.3-CLEANUP-R1` | `pump_water`（`pump_chemical` 同路径） | `src/equipeffi/infrastructure/excel/ooxml_reader.py::_parse_number`（第 35–45 行），调用点 `ooxml_reader.py:144`；上层 `v4_reader.OOXMLV4Reader.read_rows`（`v4_reader.py:62`）、`v4_writer.py:421` | 该函数先 `Decimal(text)` 解析单元格词法文本，再 `return float(number)`，在可无损的位置物化为 binary float。xlsx 数值本身是 XML 词法文本，`Decimal` 已在手，转 float 是纯损失 | 可能影响业务结论：若该 float 进入权威链并参与 full-value 比较或表 3 边界，存在翻转分档的可能 | M | `NOT_SHIPPED` | P1（暂定；视影响面验证结果可上调） | Phase 8 前 | OPEN | 源码定位；`git grep` 确认 `src` 内无 openpyxl，该链路为自研标准库读取器，入口完全可控 | 保留登记；**Phase 8 前必须关闭**。不因本条目在治理任务中修改 Python |

```text
QA-EXCEL-001
表面            = NOT_SHIPPED（V4 Excel 读写路径，生产链 0 引用）
authoritative path impact = 尚待验证
  —— 需先确认该 float 是否经 V4 输入适配器进入权威数值链；
     若适配器已转为 Decimal 字符串，则属潜在缺陷；若直接消费，则属活跃缺陷
最小修法候选    = 保留 Decimal 或返回词法文本，不转 float（不需改架构）
关闭时点        = Phase 8 正式 Excel 实现前
本轮约束        = 不改 Python 实现、不改测试期望、不改 V4 行为
关联            = Numeric Contract v1 §2.1 ingress boundary；
                  docs/28_EquipEffi 后续开发总体路线 V2.3.md 第 7.1 节
```

该条目与 `QA-P0-002`（V4 writer 写回测试失败）同属 `NOT_SHIPPED` 表面，但**根因不同**：`QA-P0-002` 是结果写回，`QA-EXCEL-001` 是数值入口保真。两者不得合并关闭。

## Phase 2 最小工程切片处置（2026-10-02）

来源：本次用户执行授权与 docs/31；下表覆盖起点所有 target_phase 含 Phase 2 的 OPEN/VERIFY 项。延期项保持 OPEN/VERIFY。

| issue_id | disposition | target_phase | decision |
|---|---|---|---|
| QA-P1-003 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-P1-007 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-001 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-002 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-003 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-004 | DEFER_TO_P4 | Phase 4 | 真实样板后再通用化；不在薄壳阶段重构业务 |
| QA-AUD-006 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-008 | DEFER_TO_P4 | Phase 4 | 真实样板后再通用化；不在薄壳阶段重构业务 |
| QA-AUD-012 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-013 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-015 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-016 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-017 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-018 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-020 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-021 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-023 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-024 | PARTIAL_IN_P2 | Phase 2/3 | 仅完成 settings 端口/存储；原业务仓储与其他端口仍开放 |
| QA-AUD-025 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-027 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-028 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-032 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-033 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-034 | CLOSE_IN_P2 | Phase 2 | 按 docs/31 实施；通过对应测试后才关闭，当前 OPEN |
| QA-AUD-035 | CLOSE_IN_P2 | Phase 2 | 按 docs/31 实施；通过对应测试后才关闭，当前 OPEN |
| QA-AUD-036 | CLOSE_IN_P2 | Phase 2 | 按 docs/31 实施；通过对应测试后才关闭，当前 OPEN |
| QA-AUD-037 | CLOSE_IN_P2 | Phase 2 | 按 docs/31 实施；通过对应测试后才关闭，当前 OPEN |
| QA-AUD-038 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-039 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-040 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-043 | KEEP_OPEN_FUTURE | Future (原 Phase 2/9) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-044 | KEEP_OPEN_FUTURE | Future (原 Phase 2/9) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-045 | DEFER_TO_P3 | Phase 3 | 依赖正式设备分析 use-case 与业务证据；本轮保持旧路径 |
| QA-AUD-047 | KEEP_OPEN_FUTURE | Future (原 Phase 2/9) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-048 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-049 | KEEP_OPEN_FUTURE | Future (原 Phase 2) | 当前范围未授权该清理/安全/打包/性能事项，保留风险，不虚假关闭 |
| QA-AUD-050 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-051 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-052 | DEFER_TO_P8 | Phase 8 | Excel/发布外围不属于 settings 工程切片；保留发布前门禁 |
| QA-AUD-053 | DEFER_TO_P4 | Phase 4 | 真实样板后再通用化；不在薄壳阶段重构业务 |
