# EquipEffi QA_BACKLOG

**状态：** Phase 0 已入库；未执行 Phase 0B Hotfix  
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
| QA-P1-003 | BASELINE-TEST-003 | shared | `tests/unit/test_release_audit.py` | Release audit 结果缺少 `wheel_pmsm_status` 键 | 影响发布审计完整性，不直接改变评价结论 | M | DEV_ONLY | P1 | Phase 2/8 | OPEN | Python 3.13 全量重跑 | 先修复审计契约/fixture，再作为发布门禁 |
| QA-P1-004 | BASELINE-TEST-004 | shared | `.venv_build` | 3.11 构建环境缺 `openpyxl`、`python-docx`、`pytest`，导致 10 error | 结果不可完整复验 | M | DEV_ONLY | P1 | Phase 0 follow-up | EVIDENCE | BASELINE.md | 保留完整 Python 3.13 结果；不把缺依赖误报为源码 PASS |
| QA-P1-005 | BASELINE-TEST-005 | shared | tests inventory | 历史审计声称 60 个真实 unittest；Phase 0 实测 54 个 test module、887 项 unittest | 治理数字漂移 | M | DEV_ONLY | P1 | Phase 1 | OPEN | 第三方 #55 + unittest | 以可重跑命令和本次数字为当前事实，历史数字仅作 Historical Evidence |
| QA-P1-006 | BASELINE-SMOKE-001 | shared | `standard_manifest.json` / resource packs | 17 pack 报告 `active`，但 active 不等于来源/边界/Golden 已验收 | 可能把可加载误认为业务可信 | M | V1_RUNTIME | P1 | Phase 1 | OPEN | status smoke + ASSET_AUDIT | Phase 1 逐 pack 冻结 Canonical/source/readiness |
| QA-P1-007 | BASELINE-PERF-001 | shared | `JsonStandardRepository.get_pack` | 同一 pack 重复读取仍 read_text + json.loads + deepcopy | 性能退化，不直接改结论 | M | V1_RUNTIME | P1 | Phase 2 | OPEN | 3.225 ms 首读；1.947 ms 重读 | Phase 0 只记录，不缓存重构 |

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
| QA-AUD-001 | AUD-001 | shared | `domain/devices/` | 8 个空壳与 `domain/evaluation` 并存；误认第二正式实现 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 2 | OPEN | CSV#1 | 标为 DELETE_CANDIDATE，先完成动态/构建/外部契约证明 |
| QA-AUD-002 | AUD-002 | shared | `device_evaluators.py` + evaluators | 兼容门面与延迟反向导入；维护变化可能影响评价 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#2 | 当前仍是运行依赖，禁止 0A 删除 |
| QA-AUD-003 | AUD-003 | motor | `evaluators/motor.py` | 字符串 `getattr` 动态 helper；改名可能静默失效 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#3 | 改为静态契约前保留回归 |
| QA-AUD-004 | AUD-004 | shared | `evaluation_engine.py` | `inspect.signature` 兼容 2/3 参数掩盖契约错误 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#4 | 唯一 evaluate 契约留 Phase 2 |
| QA-AUD-005 | AUD-005 | shared | `device_types.py` | 15 公共类型、17 Profile 和旧 fan 入口并存；路由理解成本高 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 1/2 | OPEN | CSV#5 | Phase 0 已确认映射权威，暂不合并 |
| QA-AUD-006 | AUD-006 | shared | `domain/common/models.py` | `EvaluationResult` 混合结果、轨迹、淘汰和质量 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 2/3 | OPEN | CSV#6 | 保持现有契约，未来按职责拆分 |
| QA-AUD-007 | AUD-007 | shared | `metadata.py` | 1687 行混合枚举、V4 映射、展示和 profile 构建 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 1/2 | OPEN | CSV#7 | 已在 ASSET_AUDIT 完成职责分类，暂不迁移 |
| QA-AUD-008 | AUD-008 | shared | `device_specs.py:179-188` | 导入时就地修改 `DEVICE_SPECS` | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#8 | 记录为导入副作用，不在 0A 重写 |
| QA-AUD-009 | AUD-009 | all | `device_specs.py`、`metadata.py`、`entrypoint.py` | 标准/字段/示例硬编码多份，可能产生数据漂移 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 1/2 | OPEN | CSV#9 | Python 数据先盘点，不能直接删除 |
| QA-AUD-010 | AUD-010 | shared | `evaluators/shared.py:_interval_hit` | 核心区间解析难验证，边界错误可能给错结论 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | Phase 1 | VERIFY | CSV#10 + source | 需边界标准证据/Golden 后决定 Hotfix |
| QA-AUD-011 | AUD-011 | shared | `v4_validation.py` / `input_normalization.py` | 规范化重复实现，差异可能改变输入含义 | 可能影响业务结论；需标准/Golden 证据 | H | NOT_SHIPPED | P0 | Phase 1/2 | VERIFY | CSV#11 | 先对照 Golden/Import Contract，不做重构 |
| QA-AUD-012 | AUD-012 | shared | `evaluation_service.py:148-426` | 279 行上帝方法，门禁分支难审计 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#12 | 结构债务，不因严重度直接 Hotfix |
| QA-AUD-013 | AUD-013 | shared | `v4_validation.py` | 882 行、多 sheet 特例链，新增规则易漏 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 2 | OPEN | CSV#13 | Import Contract 冻结后拆分 |
| QA-AUD-014 | AUD-014 | shared | `input_normalization.py` | 226 行、16 类转换硬编码，输入错误风险 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 1/2 | OPEN | CSV#14 | 先建立 Product/Profile Schema |
| QA-AUD-015 | AUD-015 | shared | `application_api.py` / `main_window.py` | fallback 表单构建重复，UI 可能与 API 不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | H | PROTOTYPE | P2 | Phase 2 | OPEN | CSV#15 | 暂由 `metadata_projection` 共享，UI 非 V1 门禁 |
| QA-AUD-016 | AUD-016 | shared | 多处 conclusion label | 同一结论列标题重复，展示可能漂移 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | Phase 2 | OPEN | CSV#16 | Presentation 清理阶段处理 |
| QA-AUD-017 | AUD-017 | shared | `application_api.py` / `main_window.py` | 基础信息字段元组重复 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | Phase 2 | OPEN | CSV#17 | 不影响当前核心评价 |
| QA-AUD-018 | AUD-018 | shared | `main_window.py` / `web/server.py` | 结果摘要 Python/JS 重复，说明可能不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | Phase 2 | OPEN | CSV#18 | API 摘要结构化后处理 |
| QA-AUD-019 | AUD-019 | shared | `infrastructure/excel/v4_writer.py` | 完整 writer 生产链 0 引用，V4 结果可能无法交付 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 8 | OPEN | CSV#19 + QA-P0-002 | V4 未纳入当前首发，不接线 |
| QA-AUD-020 | AUD-020 | shared | `excel/legacy_*`、`report_exporter.py`、`template_builder.py` | 4 个 FeatureNotEnabled 空桩，制造能力错觉 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 2 | OPEN | CSV#20 | DELETE_CANDIDATE，先查契约/构建/测试 |
| QA-AUD-021 | AUD-021 | shared | `strict_importer.py` | 3 行别名子类无 runtime 引用 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 2 | OPEN | CSV#21 | 暂保兼容名，后续统一 |
| QA-AUD-022 | AUD-022 | shared | SQLite repositories | 两个空桩仓储，实际持久化不存在 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 1/2/3 | OPEN | CSV#22 + ADR-005 | 按已批准三库方向设计，不在 0A 删除 |
| QA-AUD-023 | AUD-023 | shared | `cleaning_service.py` / `import_service.py` | 0 引用服务，可能是未完成能力或死代码 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 2 | OPEN | CSV#23 | DELETE_CANDIDATE，先查外部契约 |
| QA-AUD-024 | AUD-024 | shared | `application/ports/*.py` | Protocol 0 引用，实际实现未显式接入 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#24 | 保留契约方向，阶段性补接线 |
| QA-AUD-025 | AUD-025 | shared | `v4_template_audit.py` / `config/settings.py` | 0 引用包装和默认设置 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Phase 2 | OPEN | CSV#25 | 不影响 V1，删除前做动态引用检查 |
| QA-AUD-026 | AUD-026 | shared | `v4_input_adapter.py` | `adapt_many`、`validate_draft` 未接线 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 1/2 | OPEN | CSV#26 | Import Contract 确认后接入或删除 |
| QA-AUD-027 | AUD-027 | shared | OOXML 解析三处 | sheet 名和 rels 解析重复，修复容易不一致 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 2 | OPEN | CSV#27 | 不在冻结 V4 端口中重构 |
| QA-AUD-028 | AUD-028 | shared | `ooxml_reader.py` / `v4_writer.py` | 列号互换换算重复 | 当前未确认影响 V1 业务结论；维护风险待证 | M | NOT_SHIPPED | P2 | Phase 2 | OPEN | CSV#28 | 归入 OOXML 工具清理 |
| QA-AUD-029 | AUD-029 | shared | `template_resource.py` / `v4_template_contract.py` | 模板名、sheet 清单和说明重复配置 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 1/2 | OPEN | CSV#29 | Import Contract 单一来源 |
| QA-AUD-030 | AUD-030 | shared | `v4_validation.py` | 手工规则表和 metadata 派生规则双真相源 | 可能影响业务结论；需标准/Golden 证据 | M | NOT_SHIPPED | P0 | Phase 1 | VERIFY | CSV#30 | 需确认是否存在实际输入差异，未授权 Hotfix |
| QA-AUD-031 | AUD-031 | shared | 多处默认判定日期 | 日期硬编码可能选错标准生效状态 | 可能影响业务结论；需标准/Golden 证据 | M | V1_RUNTIME | P0 | Phase 1/2 | VERIFY | CSV#31 | 先用 Golden 明确 as-of 语义 |
| QA-AUD-032 | AUD-032 | shared | `__init__.py`、`pyproject.toml`、`build_msi.py` | 版本号 0.2.1 多处硬编码，追溯可能漂移 | 当前未确认影响 V1 业务结论；维护风险待证 | M | DEV_ONLY | P2 | Phase 2 | OPEN | CSV#32 | 版本模型由 ADR-003 进入 Phase 1 |
| QA-AUD-033 | AUD-033 | shared | `main_window.py:339` | UI 写死公共类型数量 15 | 当前未确认影响 V1 业务结论；维护风险待证 | L | PROTOTYPE | P2 | Phase 2 | OPEN | CSV#33 | 非业务结论问题 |
| QA-AUD-034 | AUD-034 | shared | `application/bootstrap.py` | Application 直接导入 infrastructure | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#34 | 装配方向重做时处理 |
| QA-AUD-035 | AUD-035 | shared | `application/bootstrap.py` / API | Application 反向导入 Presentation，包级环 | 可能影响发布可靠性或长期维护；业务影响待证 | H | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#35 | 不在 Phase 0 改结构 |
| QA-AUD-036 | AUD-036 | shared | `bootstrap.load_v4_contract` | `except Exception` 静默降级，模板损坏难诊断 | 可能影响发布可靠性或长期维护；业务影响待证 | H | NOT_SHIPPED | P1 | Phase 2/8 | OPEN | CSV#36 | V4 发布前必须限定异常并记录 |
| QA-AUD-037 | AUD-037 | shared | `config/logging.py` | 日志占位，关键路径无可用日志 | 可能影响发布可靠性或长期维护；业务影响待证 | M | DEV_ONLY | P1 | Phase 2 | OPEN | CSV#37 | 安全/发布阶段补齐 |
| QA-AUD-038 | AUD-038 | shared | writer / JSON repository | 损坏文件异常根因可能丢失 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#38 | 统一异常模型，保留根因 |
| QA-AUD-039 | AUD-039 | shared | `evaluation_service.py` / `v4_validation.py` | 裸 KeyError/ValueError 可能中断整批 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#39 | 改为领域 issue 需 Golden 保护 |
| QA-AUD-040 | AUD-040 | shared | `JsonStandardRepository.get_pack` | 每次解析完整 JSON，批量性能随数据量增长 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 2 | OPEN | CSV#40 + QA-P1-007 | 先保留实测，再设计缓存 |
| QA-AUD-041 | AUD-041 | shared | `json_repository.py` | manifest 缺键直接 KeyError；缺文件静默空记录；find 线性 | 可能影响发布可靠性或长期维护；业务影响待证 | M | V1_RUNTIME | P1 | Phase 1/2 | OPEN | CSV#41 | Schema/错误语义进入 Phase 1 |
| QA-AUD-042 | AUD-042 | shared | `v4_writer.py` / `template_resource.py` | 整体读写 xlsx 内存高、临时目录生命周期隐含 | 可能影响发布可靠性或长期维护；业务影响待证 | M | NOT_SHIPPED | P1 | Phase 8 | OPEN | CSV#42 | Excel 后置，不在 0A 优化 |
| QA-AUD-043 | AUD-043 | shared | `web/server.py` / `entrypoint.py` | `--host 0.0.0.0` 无鉴权，可暴露服务 | 可能影响发布可靠性或长期维护；业务影响待证 | M | PROTOTYPE | P1 | Phase 2/9 | OPEN | CSV#43 | Web 非当前 V1 入口，仍需安全处理 |
| QA-AUD-044 | AUD-044 | shared | Web upload `X-Filename` | 文件名拼接宿主路径，存在路径穿越风险 | 可能影响发布可靠性或长期维护；业务影响待证 | M | PROTOTYPE | P1 | Phase 2/9 | OPEN | CSV#44 | 上传功能未作为 V1 发布，但不得带风险发布 |
| QA-AUD-045 | AUD-045 | shared | `desktop/main_window.py` | 窗口混合表单、IO、结果展示，270 行上帝窗口 | 当前未确认影响 V1 业务结论；维护风险待证 | M | PROTOTYPE | P2 | Phase 2/6 | OPEN | CSV#45 | AppShell 以后用真实样板验证 |
| QA-AUD-046 | AUD-046 | shared | `docs/` | 27 个编号清单和多份 HANDOFF 重叠，调度来源不清 | 可能影响发布可靠性或长期维护；业务影响待证 | M | LEGACY | P1 | Phase 0 | MAPPED | CSV#46 + ROADMAP | 本次冻结权威入口，暂不批量移动 |
| QA-AUD-047 | AUD-047 | shared | repository root | 缺 LICENSE/CHANGELOG；README 偏交接文档 | 当前未确认影响 V1 业务结论；维护风险待证 | M | DEV_ONLY | P2 | Phase 2/9 | OPEN | CSV#47 | 不影响 Phase 1 业务契约 |
| QA-AUD-048 | AUD-048 | shared | `equip_test.spec` / `build_native.py` | spec 引用旧 standards，和构建脚本重复 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Phase 2 | OPEN | CSV#48 | 构建清理前保留 |
| QA-AUD-049 | AUD-049 | shared | `tools/extract_*.py` | G 盘绝对路径，换环境可能误读本机资源 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Phase 2 | OPEN | CSV#49 | 标记 legacy 或参数化 |
| QA-AUD-050 | AUD-050 | shared | `v4_template_audit.py` | 16 个国标号、GB 28381-2026 和状态字符串硬编码 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Phase 2/8 | OPEN | CSV#50 | 标准事实不得继续散落 |
| QA-AUD-051 | AUD-051 | shared | OOXML reader / template audit | inline 字符串和 namespace 重复实现 | 当前未确认影响 V1 业务结论；维护风险待证 | L | NOT_SHIPPED | P2 | Phase 2/8 | OPEN | CSV#51 | V4 后置处理 |
| QA-AUD-052 | AUD-052 | shared | `v4_writer.py:450-451` | 恒假分支，维护噪音 | 当前未确认影响 V1 业务结论；维护风险待证 | L | NOT_SHIPPED | P2 | Phase 2/8 | OPEN | CSV#52 | 不得在 0A 顺手删除 |
| QA-AUD-053 | AUD-053 | shared | `application/ports/__init__.py` | 端口导出策略不一致，外部导入可能遗漏 | 当前未确认影响 V1 业务结论；维护风险待证 | L | DEV_ONLY | P2 | Phase 2 | OPEN | CSV#53 | 契约整理时修 |
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
