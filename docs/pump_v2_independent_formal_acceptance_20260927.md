# 离心泵 Phase 1 Numeric & Decision Contract V2 独立正式验收

日期：2026-09-27；审查人：本会话独立审查代理，非执行者，非王玮业务审批代理。

**结论：BLOCKED。** 数值核心复算通过，但状态实现、Golden业务覆盖、契约验证入口及治理一致性存在实质缺口，剩余事项并非仅具名审批。不得转 READY_FOR_SOL_REVIEW，不宣布 Phase 1 PASS/APPROVED，不启动 Phase 2。审查结束停止，等待王玮具名指示。

## 1. 版本、实际差异和审查方法

HEAD：`9e413051177fbfa7f1b217de17d344f33176b152`。验收针对该HEAD上的未提交工作树，不能以HEAD单独复现。原始diff、status和逐文件SHA保存在本会话证据01/start_*及07/start_*；测试期间追踪文件未改变（changed_during_run为空）。

已读取AGENTS、ROADMAP、TASK_STATE、HANDOFF、BASELINE、QA、ASSET_AUDIT、V1_SCOPE、IMPLEMENTATION_REPORT、V2契约、两Profile映射、Canonical water/chemical、旧/新Golden schemas、23候选及正式实现和相关测试。执行报告只作待核验陈述，不充当算法Oracle。独立脚本 `docs/pump_v2_independent_acceptance_20260927.py` 不导入执行runner；Oracle系数与16组增量独立录入，Decimal50复算，不从运行结果生成预期。

实际diff包括：泵evaluator、Application输入/路由/结果、枚举/模型/metadata、API/web输入适配、repository泵小数解析、manifest、schema/候选、新测试及Phase1治理。`pump.py`相对HEAD为413新增/23删除；Canonical相对HEAD仅此前获授权T3-08 C2修正，不能算作本次V2新增标准事实。旧7文件各2行变更为此前来源版本/hash，身份/输入/审核状态未被覆盖。其他HEAD差异详见diff，不能将全部历史未提交修改归为本轮。

范围判断：未发现新设备evaluator扩展、完整UI/SQLite/报告等Phase2产品功能；未伪造Golden批准或Phase1通过。**另有非泵发布审计测试行为变更**：`tests/unit/test_release_audit.py` 在wheel缺失时不再验wheel而仍报测试通过。这不是Phase2，但超出纯泵数值收口意图，应单独处置，不能据此声称wheel已验证。

## 2. 数值契约和唯一真值路径

正式泵入口拒绝Python float；十进制文本/精确整数/Decimal直接解析。泵Canonical JSON使用parse_float=Decimal；其他设备loader维持旧行为。未发现正式泵公式混入math.log、float sqrt/pow、binary float中间量。常数为Decimal文本或精确整数；localcontext precision50/ROUND_HALF_EVEN；显示限值舍入不进入判级；grade_three完整Decimal按>=比较，没有epsilon。

清水、石化均经同一_specific_speed正式实现；旧兼容符号转发，不另建一套浮点公式。审查确认的是**当前repository装配的泵路径**，不是接受调用者随意传入已经float化的标准包。

独立42组复算：清水10行（覆盖单吸/双吸/管道/多级/轻型立卧）、石化16主分段、Q3500以及15个边界反算输入。ns、Q_ns/H_ns、清水三级阈值、石化ηb/Δη/η0/三级阈值，全部与实际evaluator Decimal精确一致；42/42，输入未改写。不是用epsilon掩盖差异，也不是Oracle自比较。

## 3. ns_raw、总Q/H及边界

正式范围/表2行/连续公式已取消业务ROUND(ns,6)。独立直接区间测试60断言：20/60/120/210/300各取−0.0000004、等于、+0.0000004，对四区间逐一验证，按raw大小归属。集成反算输入另验证实际ns；反算到名义等号可能出现Decimal50末位偏差，预期基于实际重算ns，不把反算目标当严格数学等号。

特别点59.9999996/60.0000004、119.9999996/120.0000004、209.9999996/210.0000004均按真实大小分行。既有70边界原始输入另独立重放，ns 70/70一致；只作为historical diagnostic。原4个half-micro争议输入随此来源重放，不再采用旧六位比较真值，也不批准其旧预期。

Q/H仍为原始总QBEP/HBEP；S=1/2、N=stages；Q_ns=Q/S/3600，H_ns=H/N。无需用户额外填写单级扬程。双吸Q800命中按总Q的清水高流量行，不按Q400分档；Q200双吸多级仍按总Q用T3-08 C2=142.33。公式(2)–(5)的lnQ保留总Q。Q3500石化只ηb取3000，其ns、表2Q分组仍用3500。

## 4. 决策/类别/OOS：通过项与阻塞

未知/缺类别→UNRESOLVED/无法判定；明确OTHER→NOT_APPLICABLE/OOS/不适用；均无标准公式计算。类别-单双吸、类别-级数冲突不补值，不继续ns；缺suction/stages不默认。OOS仍是既定范围政策，UI不适用，未借机改名或重评该政策。

**V2-R01：非法值被误标缺失。** 独立技术层及Application实测suction='bogus'、stages='0'/'1.5'、Q=-1、H=-1、efficiency=101均INSUFFICIENT_DATA，而不是INVALID_INPUT。非法单双吸甚至带SUCTION_MISSING。定位pump.py finalize按missing_fields归类，而通用数值校验把非法值放入missing_fields。与business_spec缺失/非法分离及chemical Profile明确要求不一致。不能通过业务批准忽略。

**V2-R02：公共support_status空缺。** centrifugal_pump公共入口的类别缺失/未知/OTHER结果support_status=None；V2定义该维度只有SUPPORTED/NOT_IN_RELEASE_SCOPE且来自发布门禁。当前契约未明确“无法路由时允许null”，必须统一契约/输出，不能偷偷从技术evaluator的SUPPORTED推断发布支持。

## 5. 等级等号和诊断

独立直接比较器9点T−1e−35/T/T+1e−35，三级等号均>=，无显示舍入。公式测试与比较器测试分开；集成输入为普通十进制，超长小数不作为主要E2E严格等号Oracle。

旧6个EFF-EXACT未出现在0.3候选；从旧核心/补充原输入只读重放6条，记录为诊断，不以旧Excel末位批准等级。旧12等号来源及4half-micro保留历史身份。0.3文档分层方向正确，实际覆盖与端到端定义仍未合格。

## 6. Golden分层与候选ID

新schema单独jsonschema验证23/23合法，全部DRAFT/PENDING；旧schema字节与HEAD一致；旧7身份、input、review_status与HEAD一致；原341文件SHA=`1642848D47903EF444B9CB3A14EA4695DE8CEB1F69C89E5CE829D7AE4E0CDEDF`与冻结来源一致。

不是73例全部人工Golden。文档已分Canonical/rule、mathematical、generated、E2E以及historical diagnostic；但**当前23条全是PROFILE_EVALUATOR_TECHNICAL重放，正式Application E2E候选数量不能报成23**。其中15条water，8条chemical为TECHNICAL_DIAGNOSTIC_ONLY，公开Application应返回未支持。

**V2-R03：业务覆盖虚假满足。** 两例WATER-LIGHT-VERTICAL-L2/HORIZONTAL-L3输入使用未映射的泵型名字，实际预期UNRESOLVED/INVALID_INPUT，无公式、无等级；不能代表轻型泵2/3级。清水无成功2/3级候选，也缺管道泵。已知候选错误可以被“重放一致”测试掩盖，应修订候选输入/独立预期，而不是让evaluator迁就错误名字。全部技术层候选还需形成真正Application E2E覆盖及明确发布门禁期待。

23个DRAFT ID如下（不是批准清单）：

```text
GC-PUMP-V3-WATER-SINGLE-SUCTION-L1
GC-PUMP-V3-WATER-DOUBLE-SUCTION-L1
GC-PUMP-V3-WATER-MULTISTAGE-C2-142-33
GC-PUMP-V3-WATER-LIGHT-VERTICAL-L2
GC-PUMP-V3-WATER-LIGHT-HORIZONTAL-L3
GC-PUMP-V3-WATER-BELOW-MINIMUM
GC-PUMP-V3-WATER-FLOW-OOS
GC-PUMP-V3-WATER-MISSING-EFFICIENCY
GC-PUMP-V3-WATER-MISSING-SUCTION
GC-PUMP-V3-WATER-MISSING-STAGES
GC-PUMP-V3-WATER-SUCTION-CONFLICT
GC-PUMP-V3-WATER-STAGE-CONFLICT
GC-PUMP-V3-WATER-CATEGORY-MISSING
GC-PUMP-V3-WATER-CATEGORY-UNKNOWN
GC-PUMP-V3-WATER-CATEGORY-OTHER
GC-PUMP-V3-CHEMICAL-SINGLE-L1
GC-PUMP-V3-CHEMICAL-DOUBLE-SUCTION
GC-PUMP-V3-CHEMICAL-MULTISTAGE-L2
GC-PUMP-V3-CHEMICAL-GRADE3
GC-PUMP-V3-CHEMICAL-BELOW-MINIMUM
GC-PUMP-V3-CHEMICAL-Q-ABOVE-3000-CAP
GC-PUMP-V3-CHEMICAL-FLOW-OOS
GC-PUMP-V3-CHEMICAL-STAGE-CONFLICT
```

**V2-R04：正式contract validator不支持0.3。** 独立运行tools/validate_phase1_contracts.py拒绝23条，unsupported case_schema_version。原7中3例CURRENT_IMPLEMENTATION的pump.py引用hash过时；负例探针4错误而期待3，入口退出1。旧不可变证据应显式版本化/历史化，不能就地刷新旧hash伪造当时实现。source_sidecar标准路径是占位符，虽然其他映射有真实PDF路径/hash，也应补到可直接复核的来源映射。

## 7. 石化真实状态

| 维度 | 实际状态 |
|---|---|
| target scope | IN_V1_PENDING_GATES，已纳入V1目标 |
| implementation | 有Decimal50技术evaluator；正式公开入口受门禁阻止 |
| test | 独立16主分段、raw边界、Q3500等技术计算通过；发布支持E2E未批准 |
| approval | DRAFT/PENDING，NOT_IN_RELEASE_SCOPE，不是已发布支持 |

源码与package-resource fallback各一次双Profile smoke：water可计算；chemical明确当前版本未支持。此验证不是新构建wheel验证，更不是原生Excel/WPS兼容验证。

## 8. 全部独立测试结果

Windows/.venv CPython3.12.14 x64，PYTHONPATH=src；命令、stdout/stderr、耗时在证据01/test_results.json。串行运行，无业务文件编辑。

| 检查 | pass/fail/error/skip | 墙钟秒 |
|---|---|---:|
| 正式contract/schema CLI及负例 | exit1：旧7中3hash错误、0.3候选23拒绝、负例4而非3 | 4.112 |
| Canonical integrity | 3/0/0/0 | 1.025 |
| mathematical numeric | 8/0/0/0 | 2.311 |
| generated boundary unittest | 3/0/0/0 | 0.281 |
| Golden+旧0.2 schema unittest | 9/0/0/0 | 0.670 |
| pump matrix/engine/source pages | 325/0/0/0 | 6.417 |
| architecture+device metadata contract | 109/1/0/0 | 7.827 |
| 全量项目 | 904/3/0/3，总910 | 169.223 |
| compileall src/tools/tests | exit0 | 3.426 |
| git diff --check | exit0 | 0.203 |
| 独立Decimal Oracle | 42/42精确一致；60raw区间断言；9比较器探针 | 07检查运行约2.4秒（含快照） |
| 独立historical diagnostics | 70边界ns一致；6旧EFF-EXACT只读诊断 | 同07原始证据 |
| 独立schema0.3 | 23合法，不代表业务预期正确 | 同07原始证据 |
| 源码/package-resource smoke | 两loader×两Profile结果一致 | 同07原始证据 |

**V2-R05：metadata契约失败。** 实际EV_SUCTION仅单吸/双吸，冻结V4契约还含不适用/其他；contract.test_device_metadata直接失败。全量discover只从tests顶层载入部分包，不能替代单独contract运行。要同步版本化枚举投影/兼容责任，不能单改断言消除失败。

全量3失败均V4 motor reader/writer断言（reader copied row、writer1500 rows、writer locked results）。它们不证明泵公式错误；本次未修电机，也不根据执行报告直接认定已豁免。3skip及每条失败原始栈在日志。性能NOT_RUN；用户已撤销10%及Office门槛。

## 9. 治理、未解决项和交接

**V2-R06：治理未同步完整缺陷。** HANDOFF/TASK_STATE把下一步写为等待独立审查或只余审批；chemical Profile要求非法K/L为INVALID_INPUT而代码不一致；V2支持状态空值未定义；执行报告未覆盖正式contract入口失败。需要同步当前独立BLOCKED事实。历史73/v07结论不能代替V2验收。另需具名决定wheel验证范围变化，不将缺产物测试通过伪装为实际wheel证据。

Phase0保持PHASE_0_PASS不可变，0B/Phase1Hotfix均NOT_EXECUTED；Phase0遗留V4电机失败和原生Office/发布产物证据按既有QA保留，建议分开跟踪，不扩到本次泵修复。Phase1技术缺陷先处理再审批；没有Phase2越界事实，但不能进入Phase2。

建议最小修订顺序：R01/R02状态语义 → R03真正E2E/轻型/管道覆盖 → R04版本化schema入口及来源引用 → R05枚举兼容 → R06报告/治理及wheel范围决定；不增加第二套正式算法、不改标准常数/范围政策、不批量重构。修订后由本会话再次独立验收。

王玮当前需要决定：是否授权上述定点修正；是否同意将非泵wheel审计变更退回或独立立项；旧证据版本化读取方案。**现在不建议批准这23条全部业务预期。** 修正后按新产物版本/hash及明确case_id具名审批Golden、石化发布门禁和Solution/Product Review。以上只是建议，不是实施授权。

可复现命令：PowerShell设置 `$env:PYTHONPATH='src'; $env:PYTHONIOENCODING='utf-8'`，运行 `.venv/Scripts/python.exe docs/pump_v2_independent_acceptance_20260927.py --tests`，再 `--checks`。脚本创建新编号目录不覆盖旧产物。脚本首次Oracle规则ID标签修正和package-loader调用修正的中间记录02–06全部保留；最终以07为准，01为正式回归结果。审查脚本不是业务runner，不应用到生产计算。

最终状态仍BLOCKED；无业务代码、schema、候选、Canonical编辑。停止，等待王玮具名审批/方向。
