# EquipEffi QA_BACKLOG

本页仅登记当前仍需跟踪的工程风险与已登记偏差；详细历史处置不在这里重复归档。

**当前状态：** Phase 1–7 保持已记录的独立验收状态；Phase 8 为 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE`，不得自行标为 PASS。Phase 0B = `NOT_EXECUTED`；当前无获准的 Phase 1 Hotfix。

**本轮退役说明：** 旧 API / JSON / JSONL / Web / Android / V4 执行链已退出。仅依赖这些执行表面的缺陷条目从当前台账移除，因为该路径不再属于当前产品；这不代表旧业务算法已修复、复核或获得正确性认证。非泵 Calculator 候选与数值断言、完整设备元数据、`domain/devices` 候选目录、`config/settings.py`、历史记录及标准证据继续保留。

OPEN / VERIFY / REGISTERED_DEVIATION 都按原状态保留，不自动授权代码修改。标准解释、Canonical、Approved Golden、Frozen Contract、历史 Record 与数据库语义不在本轮退役中变更。

## 当前风险与偏差

| issue_id | 原状态 | 当前表面 / 目标 | 当前风险与证据边界 |
|---|---|---|---|
| QA-RET-001 | VERIFY | Qt 批量评价验收 | Owner 实测结果 Workbook 正常但完成文案残留、批次历史不可见、打开 WPS 崩溃及文件夹 ShellExecute error 5。已修复完成/失败状态与可复制的打开失败提示；接通既有 batch_record 只读历史、加载更多；真实旧批次 2 行/4台/1级可见且原库哈希不变。补充 frozen Windows 外部启动的 DLL/PATH/Qt 插件路径清理并恢复（PyInstaller 官方说明），69 项集成定向检查通过。WPS/Explorer 正常桌面启动实测仍待确认，不能把根因候选当作已验证结论。无标准解释、算法、Golden 或数据库 schema 变更。 |
| QA-P1-006 | OPEN | V1_RUNTIME / Future | 资源包标为 `active` 只代表可加载，不等于其来源、范围、Golden 和支持状态均已验收；具体支持范围仍以 `V1_SCOPE.md` 为准。 |
| QA-AUD-001 | OPEN | NOT_SHIPPED / Future | `domain/devices/` 中的候选壳与 `domain/evaluation` 并存；保留供后续边界/调用证据判断，本轮不据此删除专业候选。 |
| QA-AUD-002 | OPEN | V1_RUNTIME / Future | `device_evaluators.py` 兼容门面与延迟反向导入仍增加维护和调用理解成本；保留其现有运行依赖。 |
| QA-AUD-003 | OPEN | V1_RUNTIME / Future | 电机 evaluator 使用字符串 `getattr` 调用 helper；重命名可能静默失效，需静态契约前继续保留回归。 |
| QA-AUD-005 | OPEN | V1_RUNTIME / Future | 公共设备类型、内部 Profile 与旧风机入口的路由可读性仍有结构债务；当前无错误结论证据，不合并映射。 |
| QA-AUD-006 | OPEN | V1_RUNTIME / Future | `EvaluationResult` 仍混合结果、轨迹、淘汰与质量信息；职责收敛属于独立重构，不在本轮改变契约。 |
| QA-AUD-007 | OPEN | V1_RUNTIME / Future | `metadata.py` 体量较大且混合枚举、字段映射、展示元数据与 Profile 构建；保留非泵专业字段和既有外部映射值。 |
| QA-AUD-008 | OPEN | V1_RUNTIME / Future | `device_specs.py` 导入时会就地修改 `DEVICE_SPECS`；目前作为结构风险跟踪，不扩大为规则或算法重写。 |
| QA-AUD-009 | OPEN | V1_RUNTIME / Future | 标准、字段与示例仍有多处 Python 表达，存在数据漂移风险；Canonical 仍是标准数据权威，不因台账而静默删除或改写业务数据。 |
| QA-AUD-010 | VERIFY | V1_RUNTIME / VERIFY_BEFORE_PHASE9 | **P0：** `evaluators/shared.py:_interval_hit` 的边界判定仍需标准原文与跨案例覆盖。既有 12 个开闭端点 probe 未发现错误，但不足以证明所有标准 / Golden 场景安全；无 Hotfix 授权。 |
| QA-AUD-024 | OPEN | V1_RUNTIME / Future | Application ports 的 Protocol、实现接线和导出约定尚未全部统一；保留正式批量链使用的现有端口。 |
| QA-AUD-025 | OPEN | DEV_ONLY / Future | `config/settings.py` 仍保留，但目前仅有架构边界测试读取、无运行时调用；继续跟踪该配置入口的实际用途，不把它与已退役的 V4 模板审计混为一项。 |
| QA-AUD-032 | OPEN | DEV_ONLY / Future | `src/equipeffi/__init__.py`、`pyproject.toml` 与构建入口仍有版本声明分散，可能造成追溯漂移。 |
| QA-AUD-038 | OPEN | V1_RUNTIME / Future | Writer / JSON repository 的异常路径可能丢失底层根因；诊断质量风险，不把执行错误转成业务不可判定。 |
| QA-AUD-041 | OPEN | V1_RUNTIME / VERIFY_BEFORE_PHASE9 | `json_repository.py` 缺键可能抛裸 `KeyError`，缺文件语义与线性查找仍需发布前给出结论；现有发布审计检查只构成部分缓解。 |
| QA-AUD-042 | OPEN | V1_RUNTIME / VERIFY_BEFORE_PHASE9 | V6 批量 Workbook 的高峰内存历史测量需要在最终发布候选复测。基线记录的 10,000 行结果曾达 952.0 MB、266.357 / 287.861 s；固定参考为 [332d79c](https://github.com/adgo07/EquipEffi/commit/332d79c7d999feb4047c920ecb4359655bf9440e)。旧测量不代替当前候选测量。 |
| QA-AUD-047 | OPEN | DEV_ONLY / Future | 仓库发布文档仍缺正式 LICENSE / CHANGELOG 或存在交接式说明，作为发布与维护资料风险跟踪。 |
| QA-AUD-049 | OPEN | DEV_ONLY / Future | `tools/extract_*.py` 中仍有本机 G 盘路径，换环境可能误读本地资料；通用人工校对工具未因 V4 退役而自动删除。 |
| QA-AUD-053 | OPEN | DEV_ONLY / Future | `application/ports/__init__.py` 的导出策略与子端口模块不完全一致；保留具体差异待统一。 |
| QA-P3-002 | OPEN | V1_RUNTIME / 标准映射 | Canonical pack 目前提供 `effective_date`，未提供 `superseded_by` / 废止日期等生命周期字段；软件不应私造标准生命周期规则。补齐须走标准映射流程。 |
| QA-P5-005 | OPEN | Phase 9 | 正式安装包、代码签名与正式发布产物尚未完成；本轮不宣称可发布。 |
| QA-P7-001 | REGISTERED_DEVIATION | RECORD_VERSION_FIELDS | 存量历史记录中的版本字段不一定能追溯到真实源指纹；当前泵版本指纹由 pump_calculator_version.py 提供。不得为历史记录编造或回填版本，沿用既有降级展示。 |
| QA-P7-002 | REGISTERED_DEVIATION | LEGACY_RECORD_BASIS | 较早历史记录缺少完整标准依据字段。不得回填当前版本、重算或追溯改写；按既有降级文案展示。 |
| QA-P1-008 | OPEN | V1_RUNTIME / Owner 决定是否进入 M4 | `get_pack` 每次仍对整包 dict 执行 `deepcopy`；10,000 行实测约 5.759 s、约占端到端 13.6%。在审计调用方不修改返回值之前不得移除复制；固定性能参考同 [332d79c](https://github.com/adgo07/EquipEffi/commit/332d79c7d999feb4047c920ecb4359655bf9440e)。 |

## P0 / Hotfix 状态

当前仍列为 P0 的活动项只有 `QA-AUD-010`，状态 `VERIFY`。未登记获准 Hotfix；该项需补足标准原文与 Golden 证据后再判断是否需要最小修复。

## 退役与历史记录边界

本轮从当前台账移除仅对应已删除旧入口、V4 读写/校验链、Web/Android 上传与旧 JSON/JSONL 服务的问题，以及重复的 Phase 处置、旧 blocker 和已结束复验流水。退役表示不再维护该表面，不表示历史候选算法、非泵计算器、标准数据或旧记录已被重新计算或认证。Approved Golden、Canonical、冻结标准资产及历史记录保持原样。
