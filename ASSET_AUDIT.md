# EquipEffi Phase 0 资产审计

**状态：** Phase 0A 完成；Phase 0B 未执行  
**审计日期：** 2026-09-21  
**审计原则：** 先证明运行意义，再决定迁移或删除；第三方严重度不直接等于业务发布优先级。

## 分类和发布表面

资产分类使用：`KEEP`、`VERIFY`、`MIGRATE`、`REWORK`、`DEPRECATE`、`DELETE_CANDIDATE`、`OBSOLETE`。

发布表面使用：

- `V1_RUNTIME`：当前核心评价/标准运行链候选；
- `DEV_ONLY`：构建、审计、提取和开发工具；
- `PROTOTYPE`：当前 Tk/Web 窗口或诊断原型；
- `LEGACY`：历史兼容路径；
- `NOT_SHIPPED`：当前未接入 Windows V1 发布链。

## 当前真实运行链

代码和 smoke 共同确认的主路径为：

```text
equipeffi.entrypoint.main
  ↓
application.bootstrap.create_application_api
  ↓
presentation.api.ApplicationApi
  ↓
application.services.EvaluationFacade
  ↓
application.services.EvaluationService
  ↓
domain.evaluation.device_types.resolve_device_type
  ↓
domain.evaluation.evaluator_registry.EVALUATOR_FACTORIES
  ↓
domain.evaluation.evaluators.*
  ↓
infrastructure.standards.JsonStandardRepository
  ↓
domain.common.models.EvaluationResult
  ↓
ApplicationApi / JSON / JSONL / Web / Tk projection
```

关键证据位置：`entrypoint.py:16,109`、`application/bootstrap.py:53-88`、`application/services/evaluation_facade.py:30-114`、`evaluation_service.py:148-396`、`evaluator_registry.py:23-42`、`json_repository.py:17-104`。

### Authoritative implementation 决策

| 能力 | AUTHORITATIVE | LEGACY / EMPTY_SHELL | Phase 0 决策 |
|---|---|---|---|
| 设备类型路由 | `domain/evaluation/device_types.py` | `domain/devices/` | 路由以 15 公共类型→17 内部 Profile 的显式映射为准 |
| 评价器绑定 | `domain/evaluation/evaluator_registry.py` + `evaluators/*.py` | `domain/evaluation/device_evaluators.py` 兼容门面 | evaluator 类是权威业务入口；兼容门面暂保留并标记 `DEPRECATE` |
| 标准加载 | `JsonStandardRepository` + `standard_manifest.json` + resources JSON | `SqliteStandardRepository` 空桩 | 当前运行使用 JSON；SQLite 仅为已批准后续方向 |
| API | `ApplicationApi` / `EvaluationFacade` | 旧 UI 自己拼结果的路径 | API 契约为当前展示层边界；V4 适配器仍是冻结端口 |
| V4 写回 | 测试可实例化 `V4WorkbookWriterImpl` | 生产链 0 引用 | `NOT_SHIPPED`；问题入 QA，不在 Phase 0 接线 |
| Workspace/Record | 当前不存在完整权威实现 | `SqliteProjectRepository` 抛 `FeatureNotEnabledError` | 按 ADR-002 登记为 Phase 1/2/3 输入 |

`domain/devices/` 在 `src`、`tests`、`tools` 中无引用，目录内 transformer 类为空壳；但因动态导入/外部契约尚未做完证明，当前分类是 `DELETE_CANDIDATE`，不在 Phase 0 删除。

## 分层资产清单

| 层 | 资产 | 分类 | 发布表面 | 当前判断 |
|---|---|---|---|---|
| Domain | `domain/evaluation/` | KEEP + REWORK | V1_RUNTIME | 当前唯一正式评价域；需后续收敛 helper、契约和元数据职责 |
| Domain | `domain/evaluation/evaluators/*.py` | KEEP | V1_RUNTIME | 由 registry 绑定的 17 个 evaluator；不在 Phase 0 批量重写 |
| Domain | `domain/evaluation/device_evaluators.py` | DEPRECATE | LEGACY | 被多个 evaluator 延迟导入，当前仍为运行依赖；不得直接删除 |
| Domain | `domain/evaluation/evaluation_engine.py` | REWORK | V1_RUNTIME | 使用 `inspect.signature` 兼容 2/3 参数，契约需要 Phase 2 收敛 |
| Domain | `domain/evaluation/metadata.py` | REWORK | V1_RUNTIME | 当前 1687 行，混合输入契约、V4 映射、枚举、展示和 profile 构建 |
| Domain | `domain/evaluation/device_specs.py` | MIGRATE + REWORK | V1_RUNTIME | 17 Profile 的字段、示例和标准引用仍写在 Python 中，并有导入副作用 |
| Domain | `domain/common/models.py` | KEEP + REWORK | V1_RUNTIME | `EvaluationResult` 当前有效；结果、轨迹、淘汰和质量职责待后续拆分 |
| Domain | `domain/devices/` | DELETE_CANDIDATE | NOT_SHIPPED | 空壳垂直迁移；0 引用；Phase 2 再做删除证明 |
| Application | `EvaluationFacade` / `EvaluationService` | KEEP + REWORK | V1_RUNTIME | 当前所有单条/批量/V4 评价入口；服务方法过长但不在 Phase 0 重构 |
| Application | `bootstrap.py` | REWORK | V1_RUNTIME | 直接导入 infrastructure 和 presentation，存在分层穿透/包级环审计项 |
| Application | `services/v4_*` | VERIFY + DEPRECATE | NOT_SHIPPED | V4 合同和适配端口可用，正式 Excel 读写仍冻结 |
| Presentation | `presentation/api/` | KEEP | V1_RUNTIME | JSON、JSONL 和批量入口复用 facade |
| Presentation | `presentation/desktop/` | DEPRECATE | PROTOTYPE | Tk 可用时显示；不是 Phase 0 的 Windows V1 产品 Shell |
| Presentation | `presentation/web/` | DEPRECATE | PROTOTYPE | 诊断/回退窗口；`--host`、上传路径问题进入 QA |
| Infrastructure | `standards/json_repository.py` | KEEP + REWORK | V1_RUNTIME | 当前正式标准加载器；重复 JSON 解析已实测登记 |
| Infrastructure | `standards/pack_validator.py` | KEEP | V1_RUNTIME | 标准包结构验证；Schema 仍未冻结 |
| Infrastructure | `standards/sqlite_repository.py` | DEPRECATE | NOT_SHIPPED | 空桩；未来由 catalog.sqlite 方向替代，但 Phase 0 不建表 |
| Infrastructure | `excel/v4_reader.py` / `ooxml_reader.py` | VERIFY | NOT_SHIPPED | V4 读取测试使用，需等 Import Contract 和发布范围决定 |
| Infrastructure | `excel/v4_writer.py` | VERIFY | NOT_SHIPPED | 完整实现但生产 0 引用；当前测试有 2 个结果失败 |
| Infrastructure | `excel/legacy_*`、`report_exporter.py`、`template_builder.py` | DELETE_CANDIDATE | NOT_SHIPPED | 受控 FeatureNotEnabled 空桩；不能仅凭 0 引用删除 |
| Persistence | `persistence/sqlite_project_repository.py` | DEPRECATE | NOT_SHIPPED | Workspace/Record 尚未实现；与 ADR-002/005 对齐但不在 Phase 0 建设 |
| Data | `standard_manifest.json` | KEEP | V1_RUNTIME | 当前运行选择清单；不是所有标准事实的 Canonical Schema |
| Data | `resources/standards/*.json` | VERIFY + MIGRATE | V1_RUNTIME | 17 pack 可加载，格式不统一；需 Phase 1 Canonical 复核 |
| Data | `resources/elimination_catalog*.json` | VERIFY | V1_RUNTIME | 第一至第四批 402 条和产业目录 11 条用户受控子集；产业目录非全文 |
| Data | V4 模板 `.xlsx` | VERIFY + MIGRATE | NOT_SHIPPED | 当前 Import Contract 候选；原文件受哈希保护，不覆盖 |
| Tests | `tests/unit`、`contract`、`integration` | KEEP | DEV_ONLY | Legacy Regression；当前 54 个测试模块，Python 3.13 实跑 887 项 |
| Tests | `tests/golden/` | MIGRATE | DEV_ONLY | 只有说明文件，尚无 Approved Golden Case；候选见 `V1_SCOPE.md` |
| Tools | `tools/*.py`、`scripts/*` | KEEP + VERIFY | DEV_ONLY | 构建/审计/提取工具；绝对路径和旧 spec 进入 QA |
| Docs | V2.2 与本组 Phase 0 文档 | KEEP | DEV_ONLY | 当前唯一治理入口 |
| Docs | v7-v15、T04.xx、旧 HANDOFF、编号执行清单 | DEPRECATE | LEGACY | 保留事实；`HISTORICAL / NOT AUTHORITATIVE FOR NEXT TASK` |

## 元数据职责盘点

Phase 0 只回答“未来应该属于哪里”，不迁移 `metadata.py` / `device_specs.py`。

| 当前位置/内容 | 现有职责 | 目标职责 | 当前分类 |
|---|---|---|---|
| `metadata.py` 的 profile 字段、类型、必填和稳定字段名 | 产品输入结构 | Product/Profile Schema | MIGRATE |
| `metadata.py` 的 V4 field id、sheet、列名、别名 | 外部工作簿映射 | Import Contract | MIGRATE |
| `metadata.py` 的中文名、帮助、排序、UI 提示 | 展示信息 | UI Metadata | MIGRATE |
| `metadata.py` 的枚举值 | 混合；部分标准枚举，部分产品输入枚举 | Canonical Catalog 或 Product/Profile Schema，逐项复核 | VERIFY |
| `device_specs.py` 的 17 个 `example` | 示例/测试输入 | Golden Candidate fixture 或 Product Schema example | VERIFY |
| `device_specs.py` 的 `standard` 字段 | 标准引用 | Canonical provenance reference | VERIFY |
| evaluator 中的公式、查表选择、边界、插值、缺失和结论分支 | 业务行为 | Ruleset / Domain | KEEP now, MIGRATE later |
| `entrypoint._public_example` | 重复示例 | 单一 example source | DELETE_CANDIDATE / LEGACY_DUPLICATE |

### 当前不混淆的边界

```text
标准阈值/表格/条款/来源 → Canonical Catalog
稳定 field key、类型、必填、profile → Product/Profile Schema
V4 Sheet、列名、别名、模板版本 → Import Contract
查表、边界、插值、单位转换、比较、缺失语义 → Ruleset / Domain
中文名、帮助、排序、提示 → UI Metadata
```

## Canonical 候选数据盘点

这张表只盘点现有数据，不冻结最终 Schema，也不把当前 `active` 标志解释成“已批准 Canonical”。`record_count` 按当前文件容器记录，不能直接跨 pack 比较。

| source | current_file | standard | record_count | review_status | provenance | known_issue | candidate_for_canonical |
|---|---|---|---:|---|---|---|---|
| `standard_manifest.json` | `src/equipeffi/standard_manifest.json` | 17 pack entries | 17 | active mapping | pack_id、standard_code、effective_date、data_version | manifest 是运行选择清单，不是统一数据 schema | YES, after Phase 1 schema |
| `resources/standards/transformer.json` | 同左 | GB 20052-2024 | 546 rows | active; boundary review pending | row source pages/data ids present | flat rows and source fields need canonical names | YES, after normalization |
| `resources/standards/motor_lv.json` | 同左 | GB 18613-2020 | 42 rows | active; review status not explicit | `source_page` and mode/dims fields | V4 motor result defect; schema differs from tables | YES, after Golden review |
| `resources/standards/motor_hv.json` | 同左 | GB 30254-2024 | 6 tables | active; boundary review pending | table/source fields present | table shape and data ids need contract | YES, after normalization |
| `resources/standards/gb30253_2024_pdf_verified_v1.json` | 同左 | GB 30253-2024 | 29 tables / 10803 reviewed cells | PDF reviewed and activated | activation_review、source_sha256、table count | no-data “—” semantics must remain explicit | YES, highest readiness |
| `resources/standards/compressor.json` | 同左 | GB 19153-2019 | 2469 rows | active; source review pending | row source fields present | large flat pack; schema/indices not frozen | YES, after normalization |
| `resources/standards/pump.json` | 同左 | GB 19762-2025 | water CI 10；chemical 5 top-level entries | active; source pages present | formula note、source_pages、data_id | water/chemical nested shapes share one file | YES, Phase 1 sample candidate |
| `resources/standards/fan.json` | 同左 | GB 19761-2020 | 4 tables | active; boundary review pending | table source fields | one internal fan profile serves two public types | YES, after public/profile decision |
| `resources/standards/blower.json` | 同左 | GB 28381-2012 | 8 tables | active; source review pending | table source fields | 2026 standard not activated; missing-input branches need Golden | YES, after review |
| `resources/standards/submersible.json` | 同左 | GB 32030-2022 | 5 tables | active; calculation review pending | table/source fields | derived Appendix calculation not separately versioned | YES, after ruleset split |
| `resources/standards/boiler.json` | 同左 | GB 24500-2020 | 4 tables | active; input gate review pending | table/source fields | electric limit and normal tables have special semantics | YES, after schema |
| `resources/standards/heat_treatment.json` | 同左 | GB/T 36561-2018 | fuel coefficients + table8 | active; review status not uniform | table8 source page and coefficient fields | mixed coefficient/rule data | YES, after fact/ruleset split |
| `resources/standards/hvac_thresholds.json` | 同左 | GB 19577/29541/37479/19576/21454 | 5 devices / 8 verified tables | chiller PDF-verified; others active | source_files、source_note、verified_table_count | five profiles share one nested pack; no uniform record count | YES, after per-profile extraction |
| `resources/standards/hvac_thresholds.json` | 同左 | GB 19577-2024 | shared nested device section | PDF verified | source files and verified tables | product-standard applicability is conditional | YES, after applicability contract |
| `resources/standards/hvac_thresholds.json` | 同左 | GB 29541-2013 | shared nested device section | active; review pending | shared source note | canonical boundary with UI metric aliases unresolved | YES, after review |
| `resources/standards/hvac_thresholds.json` | 同左 | GB 37479-2019 / GB 19576-2019 / GB 21454-2021 | shared nested device sections | active; review pending | shared source note | public fields and dynamic metrics need separate Import Contract | YES, after review |

当前唯一可直接称为“高来源质量”的标准包是 PMSM PDF 独立重建并激活包；其余包的 `active` 表示运行时可加载，不替代原文、条款、页码和人工复核。`pump_water` 被选为样板，是因为它已经具备公式、分档、来源页、data_id 和边界资产，但仍必须在 Phase 1 完成 Canonical Schema 复核。

## Persistence 基线

| 当前对象 | Phase 0 事实 | 已批准方向 |
|---|---|---|
| Standard repository | JSON 正式运行，SQLite repository 空桩 | `catalog.sqlite` 可由 Canonical JSON 重建 |
| User settings/profile | 未形成正式 user repository | `user.sqlite` |
| Workspace/Record | 仅 `DeviceDraft` 和 API result；没有跨启动保存/Finalize | `records.sqlite`；Workspace 可变，Record 不可变 |
| Excel ports/writer | Port 和 V4 writer 存在，正式读写冻结 | 必须经 Import Contract，不建立 Excel 专用算法 |
| lineage/audit/transaction | 尚不存在完整实现 | Phase 1/2/3 设计并由样板验证 |

## Phase 0 资产结论

- 当前正式实现已经唯一化到 `domain/evaluation` 运行链；空壳和兼容门面没有获得正式实现资格。
- 17 个标准包“可加载”不等于 17 个 Profile 已业务验收；Canon、来源、Golden 和 V1 Scope 仍需 Phase 1。
- 所有第三方 55 项均已进入 `QA_BACKLOG.md`，并重新区分工程严重度、业务风险和发布表面。
- 没有业务代码 Hotfix、目录搬迁或大规模删除混入 Phase 0。
