# PR33 / PR34 独立验收意见核实与修复

2026-10-25。核实对象：PR33 `e5aa673c`、PR34 `1c53d5d4`，并比对产品 PR35 `00e27733` 已有实现。意见来源为 Owner 提供的两份独立验收报告。本记录不代替 Stage D，不提升 SUPPORTED，不构成正式发布。

平台预检查：本仓 origin 为 adgo07/EquipEffi；locked central SHA 为 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`。适用 Architecture V2.1、Numeric Contract v1、Numeric Profiles v1、Conformance Vector v1 及其 Common Core schema。MUST 保持精确比较、显式 Profile/显示舍入声明、输入与来源追溯及依赖方向；MUST NOT 让外部 Decimal context 或显示舍入改变业务值，或让 Domain 依赖 Excel/UI/数据库。本轮为 LOCAL DEFECT 与已有实现证据补齐，无需修改中央 Contract 或锁。既有 Standard Issues 001—008 解释不变；源映射 A.2、源表 A.1、Approved Golden 不改。

| 意见 | 核实结论与处理 |
|---|---|
| 设计 QA 登记在后续 PR | 成立。在 PR33 前置同一 QA-MOTOR-001/002 编号；后续沿用，不重复造号。 |
| G 列“有限正数”与非适用字段 0 冲突 | 成立。统一为有限数值；适用类别正数，非适用类别非负留痕。 |
| 旧链迁移职责冲突 | 成立。内核 PR 核查调用方和迁移范围；产品 PR 负责实际切换与旧链退出。PR34 只验收核心库，不能宣称产品已接通。 |
| 空 category_id 抛 MotorPackError | 已复现并修复。空类别规范化为缺失；非法类别或 NaN 等非法数值仍为输入错误。 |
| builder 受 ambient Decimal context 影响 | 已复现并修复。改用十进制元组精确尺度转换；prec=2、ROUND_CEILING 下完整派生结果不变。 |
| test_basis_hint 被 pytest 收集 | 成立。改名 efficiency_basis_hint，调用方随产品集成同步更新。 |
| Conformance 语义和 schema 自动验证不足 | 成立。补显式显示舍入、ambient context、冲突 Profile 和真实 half-up tie，并按 locked schema 自动验证。 |
| Numeric Profile 的 kV→V 声明 | 成立。按实际实现写为 kW→W 精确转换、电压按 kV 比较；不修改算法单位。 |
| 源格显示精度 | 成立。派生 display_text 保留源表 0.0 格式；不改变 source_text、value 或正式比较。 |
| 口径阻断丢查表来源 | 成立。保留已查得的 trace；仍为无法判定，不输出等级/限值。 |
| PR35 新路由和包完整性 | 产品分支已完成：motor_lv 路由到新 evaluator，新加载层校验包内容摘要及身份，旧低压包已退出。无需在 Domain 重复加载层职责。 |
| 表1结构条件提示 | 产品 Qt 已在选类时显示共享 scope_hint；集成回归检查实际页面包含单速、封闭自扇冷、N设计、连续工作制。 |
| 模板身份、迁移和入口开关 | 属产品 PR 验收；核查实际 V6.2 资产、旧模板识别、固定输出区、保护与候选入口，不能由设计文档代替实现。 |
| 旧报告全量环境错误 | 不将权限失败归为业务失败，也不据定向测试宣称全量通过；最终 CI 按固定提交记录，Qt 退出问题另由 QA-MOTOR-004 跟踪。 |

派生包旧内容摘要：`506DDAD282F09F89CD5F467E34DC552010FABA41714F1AAB5B4DCBBDA0391A85`；新内容摘要：`E0F4A9DC83742CFB22CA746F824DD5398909713064E5EC795828B3EF57AB0EA3`。108 条功率行与 1182 个阈值的全部既有字段不变（1149 数值、32 横杠、1 空白）；只增加 1149 个 display_text，其中 482 个整数值按源格式补 .0。旧记录不重算或回填。

主会话复验：motor unittest 26 项通过（FAIL=0、ERROR=0、SKIP=0）；核心四文件 pytest 24 项、45 个 subtest 通过；11 条 Conformance 向量通过 locked schema 与计算结果核验。包移除新 display_text/integrity 后与旧包全部字段逐项一致。干净 Windows 仍为 NOT_RUN，Owner 已接受先做本机隔离验证的限制。Knowledge capture：无。
