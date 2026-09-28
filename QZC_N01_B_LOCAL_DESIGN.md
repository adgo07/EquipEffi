# QZC-N01-B — EquipEffi Transcendental Numeric Pilot 本地设计

**状态：DESIGN ONLY / NOT EXECUTED**  
**Pilot ID：** `N01-B`  
**业务仓：** `adgo07/EquipEffi`  
**默认分支：** `master`  
**Design baseline SHA：** `b336fd313ea8e3ee1c688786c05d126d76dc2699`  
**Module ID：** `qz.equipment_efficiency`  
**代表 Profile：** GB 19762—2025 离心泵（`pump_water` / `pump_chemical`）  
**中央 Foundation baseline：** `contracts-v0.1.0` → `0cd74d783fa23add6dc881b408a8c8ba8503f8e8`  
**中央 Pilot 分发来源：** `Qingzhou-contracts main@47a268dcebdc43c582f451b2004c9e63b46502a3`

> 本文只做静态设计与现有实现审计。没有修改离心泵算法，没有运行本 Pilot 的新测试，没有生成/执行 Conformance Vectors，没有实现 Kotlin / Swift / ArkTS，也没有冻结任何平台 Numeric 规则。

---

## 0. 中央文件读取与命名核实

本设计已读取中央当前真实文件：

- `docs/architecture/ARCHITECTURE_V2.1_FROZEN.md`
- `contracts/numeric/NUMERIC_CONTRACT_V1_DRAFT.md`
- `DECISIONS_NEEDED.md`
- `pilots/numeric/QZC_N01_MASTER_PLAN.md`
- `pilots/numeric/N01_B_EQUIPEFFI_DISTRIBUTION.md`
- `pilots/numeric/N01_PILOT_RETURN_TEMPLATE.md`

任务文字中的 `contracts/numeric/NUMERIC_CONTRACT_DRAFT.md` 在当前中央仓已不是实际文件名；当前真实文件为 `NUMERIC_CONTRACT_V1_DRAFT.md`。本文以当前真实文件为准，不把名称差异解释成 Contract 已冻结。

中央约束对本设计的直接含义：

1. Numeric Contract 仍为 `DRAFT / NOT YET RELEASED`；
2. `sqrt / ln / fractional pow` 的 reference procedure 仍是 D-001 OPEN；
3. Conformance Vector 最终 Schema 仍是 D-004 OPEN；
4. tolerance 与 exact comparison 的公共边界仍是 D-012 OPEN；
5. 单个业务仓可以提出 candidate，但不得把 Decimal50、ROUND_HALF_EVEN 或 tolerance 私自升级成全平台规则；
6. N01-B 必须把现有离心泵实现作为 candidate/reference evidence，而不是重新设计 GB 19762—2025 算法。

---

## 1. 本阶段证据等级

| Evidence item | 本设计状态 |
|---|---|
| Static code audit completed | `YES` |
| Existing tests inspected | `YES` |
| Tests actually executed for this design task | `NO` |
| Numerical results actually recomputed for this design task | `NO` |
| Boundary cases actually executed for this design task | `NO` |
| Conformance vectors actually executed | `NO` |
| Cross-language implementation actually executed | `NO / NOT IN SCOPE` |

因此，本文中的数值字符串若来自现有 Approved Golden / 已有测试，只作为**现有仓库证据**引用；不得写成“本任务重新运行验证”。

---

# 2. 实际代码证据

| Path / component | 实际位置 / 规则 | 审计发现 |
|---|---|---|
| `src/equipeffi/domain/evaluation/evaluators/pump.py` | `PUMP_NUMERIC_PRECISION` / `PUMP_DECIMAL_CONTEXT` | 离心泵定义 `precision=50`、`ROUND_HALF_EVEN` 的专用 Decimal Context |
| 同上 | `_pump_status()` | `WaterPumpEvaluator.evaluate()` 与 `ChemicalPumpEvaluator.evaluate()` 整个业务计算方法体均包在 `localcontext(PUMP_DECIMAL_CONTEXT)` 内；离开后再做状态 finalize |
| 同上 | `_strict_pump_decimal()` | 接受 `Decimal`、十进制字符串、精确整数；拒绝 Python `float`、`bool`、NaN/Infinity |
| 同上 | `_pump_binary_float_gate()` | 正式泵入口在执行公式前检查 Q/H/n/stages/efficiency 各别名，发现 raw binary float 即返回非法输入 |
| 同上 | `_specific_speed_in_context()` | `Q/S/3600`、`H/N`、`sqrt()`、`Context.power(..., 0.75)`、`ns_raw` 全在 Pump Decimal50 链内；无 `ROUND(ns,6)` |
| 同上 | 清水泵公式 | `ln(ns_raw)` 与 `ln(QBEP)` 后按当前表达式顺序计算公式(2)/(3)，生成 full-value thresholds |
| 同上 | 石化泵公式 | `ln(min(QBEP,3000))`、多项式 `ηb`、按 `ns_raw` 的 `Δη`、`η0` 和 offsets，均在 Decimal50 方法体内 |
| `src/equipeffi/infrastructure/standards/json_repository.py` | `JsonStandardRepository.get_pack()` | 仅 `pump_water` / `pump_chemical` 使用 `json.loads(..., parse_float=Decimal)`，避免标准小数先进入 binary float |
| `src/equipeffi/domain/evaluation/decimal_math.py` | `rounded()` | 显示/输出辅助函数固定 `ROUND_HALF_UP`、默认 6 位；它与 Pump 运算 Context 的 `ROUND_HALF_EVEN` 是不同职责 |
| `src/equipeffi/domain/evaluation/grading.py` | `compare()` / `grade_three()` | 等级判断直接使用 Decimal `>=` / `<=`，没有 epsilon、没有显示值参与 |
| `tests/unit/test_pump_numeric_contract_v2.py` | Pump Numeric V2 tests | 已有 Decimal50、局部 context、exact special functions、float rejection、full threshold compare、化工泵 Decimal50 公式测试 |
| `tests/unit/test_pump_generated_boundaries_v2.py` | Generated boundaries | 已有流量与 ns 边界 exact/inside/outside 测试，并验证 `59.9999999` 与 `60.0000004` 直接按 `ns_raw` 分档 |
| `specs/equipment_efficiency/golden/pump_water/` | Approved Golden 0.4 | 已有 18 条已批准 `pump_water` 业务 Oracle，可作为 N01-B 真实 E2E conformance case 来源，但不能被重新计算后静默改写 |
| `docs/PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md` | 项目级 Numeric Contract | 已明确 Decimal50、raw decimal text、binary float rejection、`ns_raw`、full-value comparison、无 epsilon；其范围仅为离心泵项目契约 |

---

# 3. Current Numeric Profile（真实现状）

本设计把当前实现命名为候选：

`EQUIPEFFI_PUMP_DECIMAL50_V2`（**candidate local profile，非中央正式 ID**）。

| 维度 | 当前真实行为 |
|---|---|
| Scope | 仅 `pump_water` / `pump_chemical` |
| Authoritative raw numeric input | Decimal text / `Decimal` / exact integer |
| Raw Python float | `REJECT` |
| Non-finite | `REJECT` |
| Standard decimal constants | Pump JSON decimal lexeme → `Decimal`；代码常数使用 `Decimal("...")` 或精确整数 |
| Working precision | 50 significant digits |
| Arithmetic context rounding | `ROUND_HALF_EVEN` |
| Transcendental/nonlinear | Python Decimal `sqrt()` / `ln()` / `Context.power(..., Decimal("0.75"))` |
| `ns_raw` | full Decimal value；不做 ROUND6；直接用于范围、分档、公式和阈值 |
| Grade comparison | full-value Decimal `actual >= threshold` |
| Hidden epsilon | 无 |
| Display threshold | `rounded(..., 6)`，显式 `ROUND_HALF_UP`；只用于 display/limits，不参与 grade |
| Operation order | 当前 `pump.py` 表达式顺序即事实实现；尚未抽成语言无关公共 procedure |
| Cross-language guarantee | 尚未建立 |

### 3.1 Decimal50 的真实覆盖范围

`@_pump_status(...)` 在调用 evaluator 方法时建立 `localcontext(PUMP_DECIMAL_CONTEXT)`，因此离心泵 evaluator 方法体内的验证后算术、输出功率、比转速、`ln`、fractional power、阈值计算和 `grade_three()` 调用均处于 Pump Decimal50 context 中。

`_specific_speed()` 自身又显式建立同一 local context，因此独立调用比转速 helper 时也保持 Decimal50。

**它不是 EquipEffi 全局 Decimal policy。** `decimal_math.decimal()` 仍是通用历史工具，其他 Profile 不自动获得 Pump 的 float rejection 或 precision=50。

### 3.2 ROUND_HALF_EVEN 的真实覆盖范围

当前 `ROUND_HALF_EVEN` 是 **Pump Decimal 工作 Context 的运算舍入模式**，不是“所有结果最终修约规则”，也不是 UI 显示规则。

必须区分：

```text
Pump calculation context:
precision=50 + ROUND_HALF_EVEN

business comparison:
full-value exact >= / <=

current display helper:
6 decimal places + ROUND_HALF_UP
```

因此中央 Pilot 不应把“代码里存在 ROUND_HALF_EVEN”误写成“EquipEffi 所有数值、显示、显式修约都使用 HALF_EVEN”。

### 3.3 binary float rejection 的真实覆盖范围

离心泵正式数值入口有双层保护：

1. `_pump_binary_float_gate()` 在公式前检查原始数值别名；
2. `_strict_pump_decimal()` 再次拒绝 `float`。

标准 Pump JSON 的小数字面量通过 `parse_float=Decimal` 直接进入 Decimal。

但这个策略**目前是 Pump-specific**。通用 `decimal_math.decimal()` 会执行 `Decimal(str(value))`，所以不能据此宣布“EquipEffi 全局已禁止 binary float”。

### 3.4 Decimal constants

当前 Pump 权威链中的典型代码常数为：

- `Decimal("3.65")`
- `Decimal("3600")` / 精确整数 `Decimal(3600)`
- `Decimal("0.75")`
- `Decimal("9.81")`
- `Decimal("3000")`

标准公式系数与表2/表3小数通过 Pump JSON 的 decimal lexeme 直接解析为 `Decimal`。这部分可以作为中央“Canonical 数字不先经过 binary float”的正面证据。

---

# 4. ns_raw、非线性函数与 operation order

## 4.1 当前 ns_raw procedure

现有代码真实运算顺序为：

```text
S = 2 if suction == 双吸 else 1
N = stages
q_ns_m3h = QBEP / S
q_ns = q_ns_m3h / 3600
h_ns = HBEP / N
head_power = pow(h_ns, 0.75)
ns_raw = ((3.65 * speed) * sqrt(q_ns)) / head_power
```

其中 `QBEP` 与 `HBEP` 保留为原始总流量、总扬程；只有比转速派生量使用 S/N 换算。

## 4.2 sqrt

当前调用：

`q_ns.sqrt()`

运行于 Pump Decimal50 context。对于 `sqrt(16)=4` 等特殊可精确表示场景，现有测试要求 exact Decimal equality；对于一般泵参数得到的无理数，不应由此推导出未来跨语言也必须末位完全一致。

## 4.3 ln

当前清水泵：

```text
ln_ns = ln(ns_raw)
ln_q  = ln(QBEP)
```

当前石化泵：

```text
ln_q = ln(min(QBEP, 3000))
```

一般 `ln` 结果属于 nonlinear numerical domain。

## 4.4 fractional power

当前使用：

`PUMP_DECIMAL_CONTEXT.power(h_ns, Decimal("0.75"))`

这是 N01-B 最需要跨语言验证的能力之一。Kotlin/Swift/ArkTS 后续不要求复制 Python API，但必须满足同一 procedure/vector 的输入、数值误差和业务结果要求。

## 4.5 清水泵当前 expression order

当前公式树按代码保留：

```text
ln_ns = ln(ns_raw)
ln_q  = ln(QBEP)

base =
    a * ln_ns^2
  + b * ln_q^2
  + c * ln_ns * ln_q
  + d * ln_ns
  + e * ln_q

threshold_i = base - C_i
```

N01-B 不把它代数重排成 Horner 或其他形式，因为重排可能改变有限精度末位；是否允许等价重排属于未来 Contract 问题。

## 4.6 石化泵当前 expression order

```text
ln_q = ln(min(QBEP, 3000))

eta_b = sum(coeff[idx] * ln_q^(6-idx), idx from 0 upward)

delta_eta = 0
if selected table row requires delta:
    select coefficient set by ns_raw branch
    delta_eta = sum(coeff[idx] * ns_raw^(6-idx), idx from 0 upward)

eta_0 = eta_b - delta_eta
threshold_i = eta_0 + offset_i
```

当前 Python `sum(...)` 的迭代顺序属于候选 reference procedure 需要记录的 operation-order evidence；本 Pilot 不改写为其他多项式算法。

---

# 5. 哪些可以 exact compare，哪些需要 numerical tolerance

## 5.1 Exact domain

下列内容应继续要求 exact，而不是 tolerance：

1. 十进制文本/整数到 Decimal 的值语义；
2. 标准表行、区间端点、C1/C2/C3、offset、公式系数等十进制常数；
3. `suction_factor`、`stage_count` 等离散/整数派生量；
4. 明确可精确表示的构造计算，例如现有测试：`QBEP=7200, HBEP=32, speed=10, 双吸, stages=2` → `q_ns=1`、`h_ns=16`、`sqrt=1`、`16^0.75=8`、`ns_raw=4.5625`；
5. 特殊函数精确特例：`ln(1)=0`、`sqrt(16)=4`、`16^0.75=8`；
6. 直接 Decimal 边界输入的 `< <= > >= eq`；
7. rule/data_id/category/status/grade/conclusion 等业务离散结果；
8. binary-float rejection / invalid-input 行为。

注意：不能把“Decimal 加减乘除”整体都标成 exact。若中间结果超出工作 precision 或除法不终止，仍会受到 Decimal50 context 舍入。

## 5.2 Nonlinear / tolerance domain

跨语言时，下列一般结果不应默认要求 50 位字符串完全相同：

- `sqrt(q_ns)`（非完全平方场景）；
- `ln(ns_raw)`；
- `ln(QBEP)`；
- `h_ns^0.75`；
- 由上述值复合形成的 `ns_raw`；
- 清水泵 `base` 与三级效率阈值；
- 石化泵 `eta_b`、`delta_eta`、`eta_0` 与三级阈值。

当前 Python 测试对某些化工泵中间值使用 exact equality，是因为“被测实现”和“测试期望重算”使用同一 Python Decimal50 procedure。它证明当前 Python 实现一致性，**不能直接作为跨 Kotlin/Swift/ArkTS exact-match 的证据**。

---

# 6. tolerance 应放在哪一层

建议 N01-B 明确三层，并保持中央 D-012 OPEN：

| Layer | 是否允许 N01-B candidate tolerance | 说明 |
|---|---|---|
| Business algorithm / grade decision | **NO** | 当前正式业务继续 full-value compare；不得增加 epsilon 或“接近即相等” |
| Reference algorithm convergence | **本 Pilot 不新增** | 当前 Python Decimal 已有自己的 context；不为 Pilot 重写算法或加 convergence epsilon |
| Cross-implementation numerical conformance test | **YES, candidate only** | 仅比较 nonlinear intermediate/reference outputs；不反向改变业务算法 |
| Display formatting | 不属于 numerical tolerance | 现有 display 是显式 HALF_UP 6 位，单独测即可 |

核心规则：

> **numerical tolerance 可以容许不同实现的非线性末位差异，但不能容许业务 branch / rule_id / grade / conclusion 不一致。**

若某 candidate 数值在 tolerance 内、但导致不同 ns 分档或等级，仍应判 Conformance FAIL，而不是用 tolerance 掩盖业务差异。

---

# 7. tolerance proposal（仅试验候选，不冻结）

由于本 Design 阶段没有运行 Kotlin/Swift/ArkTS，下面数值只作为 Execution 阶段收集漂移数据的**初始试验带**，不得写入中央 FROZEN Contract：

### T-NL-ATOM — 单一非线性函数

适用于 `sqrt` / `ln` / fractional `pow` 的独立 reference output：

```text
pass if:
abs(candidate - reference)
<= max(1E-13, 1E-13 * abs(reference))
```

### T-NL-COMPOSITE — 复合泵公式

适用于 `ns_raw`、`base`、`eta_b`、`delta_eta`、`eta_0`、nonlinear-derived threshold：

```text
pass if:
abs(candidate - reference)
<= max(1E-10, 1E-12 * abs(reference))
```

含单位字段的绝对 tolerance 与该字段同量纲，例如效率阈值的 `1E-10` 表示 percentage-point 数值误差。

### 试验带的治理限制

1. 这些值不是标准要求；
2. 不是 EquipEffi 业务判定 epsilon；
3. 不是平台统一 tolerance；
4. Execution 必须至少比较不同 precision 的漂移，再决定是否需要收紧/放宽 candidate；
5. 真正跨语言 runner 未执行前，不得据此关闭 D-001/D-012；
6. Gate 4 应结合 N01-A/N01-C 再决定是否形成公共 taxonomy，而不是直接采用本表数值。

---

# 8. Proposed Conformance Vectors

建议本地 candidate schema：`n01-b-pump-numeric-vector-0.1`。最终公共 Schema 仍由 D-004 决定。

每条 vector 至少包含：

```text
vector_id
profile_id
layer                       # parse / atomic / derived / decision / e2e
numeric_profile_id
inputs                      # decimal text + unit + typed-input-kind
constants / rule_id
operation_order_id
reference_intermediates
reference_output
comparison_mode             # exact_decimal / abs_rel_tolerance
abs_tolerance / rel_tolerance
expected_rule_id
expected_grade / expected_status
business_decision_must_match
boundary_sensitivity
provenance                  # repo sha / standard / canonical data_id
```

## 8.1 Exact cases

| Vector | 目的 | 输入/依据 | 期望 |
|---|---|---|---|
| `N01B-EX-001` | decimal parse | `"100.100"` 等 decimal text | Decimal 值 exact；不得先经 binary float |
| `N01B-EX-002` | binary float rejection | typed binary float `100.1` 进入 QBEP | `INVALID_INPUT`，公式不执行 |
| `N01B-EX-003` | exact specific-speed chain | Q=7200,H=32,n=10,双吸,N=2 | `q_ns=1`、`h_ns=16`、`head_power=8`、`ns_raw=4.5625` exact |
| `N01B-EX-004` | special-function exact | `ln(1)`, `sqrt(16)`, `16^0.75` | `0 / 4 / 8` exact |
| `N01B-EX-005` | full threshold compare | 现有 47 位 Decimal threshold 与 `±1E-48` | below/equal/above 业务等级 exact |
| `N01B-EX-006` | canonical constant | T3-08 C2=`142.33`、公式系数等 | source decimal exact |

## 8.2 Nonlinear cases

| Vector | 目的 | 真实业务来源 | 比较方式 |
|---|---|---|---|
| `N01B-NL-001` | 完整 `sqrt + pow + ns` | Approved Golden `GC-PUMP-V4-WATER-SINGLE-SUCTION-L1`：Q=100,H=50,n=2900,单吸,N=1 | `ns_raw` 用 T-NL-COMPOSITE；grade/rule exact |
| `N01B-NL-002` | water `ln(ns)+ln(Q)` | 同一 Approved Golden | `ln_ns/ln_q/base/thresholds` numerical tolerance；最终 grade exact |
| `N01B-NL-003` | multistage/suction transform + nonlinear | 从 18 条 Approved Golden 中选双吸或多级代表例 | nonlinear tolerance；S/N/rule exact |
| `N01B-NL-004` | chemical `eta_b` | 现有 `test_chemical_eta_b_and_delta_eta_use_decimal50_formula_inputs` 的单级 Q=100,H=50,n=2900 技术 Profile | numerical tolerance；不冒充 V1 release Golden |
| `N01B-NL-005` | chemical `delta_eta` | 选择 `eta0_uses_delta=true` 真实表2规则 | numerical tolerance；ns interval/rule exact |
| `N01B-NL-006` | Q>3000 eta_b cap | 现有化工泵技术 candidate 中选 Q>3000 案例 | `ln(3000)` 路径 exact branch；数值 tolerance |
| `N01B-NL-007` | precision sensitivity | 同一真实 pump case，在 test/reference runner 内比较 p=28/34/40/50 | 记录 drift，不改 production precision |
| `N01B-NL-008` | operation-order sensitivity | 清水 base 或化工多项式：current expression tree vs 一个只用于诊断的重排版本 | 记录差异，正式 expected 仍以 current procedure 为准 |

Approved Golden `GC-PUMP-V4-WATER-SINGLE-SUCTION-L1` 当前已保存的现有 reference evidence 包括：

```text
q_for_ns_m3s = 0.027777777777777777777777777777777777777777777777778
h_for_ns_m   = 50
ns_raw       = 93.823603448604507505014701083136622423532335781578
threshold L1 = 79.78616520331852907378831138801700817769648093823
threshold L2 = 77.78616520331852907378831138801700817769648093823
threshold L3 = 72.78616520331852907378831138801700817769648093823
expected grade = 1
```

这些是已批准 Golden 中的既有数据，不是本 Design 新重算结果。

## 8.3 Boundary cases

| Vector | 边界 | 设计要求 |
|---|---|---|
| `N01B-BD-001` | water 表3 Q min/max | 从 Canonical 自动生成 exact edge、inside、outside；保持 ±1E-6 现有测试策略 |
| `N01B-BD-002` | chemical ns interval | 覆盖 20/60/120/210/300 开闭边界，direct Decimal 输入时 branch exact |
| `N01B-BD-003` | `59.9999999` vs `60.0000004` | 必须分别命中当前不同 rule，证明不使用 ROUND6 |
| `N01B-BD-004` | efficiency threshold T−δ/T/T+δ | comparator 层 exact，不经 Q/H/n 反算 |
| `N01B-BD-005` | E2E safe-margin | 真实 Approved Golden，actual 与 threshold 保留明显 margin；数值可 tolerance，grade 必须 exact |
| `N01B-BD-006` | E2E reference-sensitive | actual 人为贴近 nonlinear threshold；标记 `REFERENCE_SENSITIVE`，用于暴露跨语言 branch flip 风险，不在 D-001 未冻结前把它当作普通 tolerance PASS 案例 |
| `N01B-BD-007` | invalid domain guard | Q≤0 / H≤0 / speed≤0 等应在业务验证阶段 `INVALID_INPUT`，不得让 `sqrt/ln/pow` 接收到非法 domain |

`BD-006` 是本 Pilot 的关键：若不同实现的 threshold 均在数值 tolerance 内，但一边判 1级、一边判 2级，**业务一致性仍失败**。这类案例正是 D-001 是否需要更强 reference procedure 的证据。

---

# 9. Candidate Reference Procedure — `PUMP-RP-0.1`

建议 N01-B 在 Execution 阶段把以下 procedure 固化为**本地候选 reference procedure**，仅用于生成/验证 vectors：

## 9.1 Input

- 接收 finite decimal text / exact integer；
- 禁止 binary float 进入 authoritative path；
- Canonical decimal constants 从十进制 source lexeme 构造；
- 不做隐式 scale normalization 后再参与业务判断。

## 9.2 Working arithmetic

```text
precision = 50
rounding  = ROUND_HALF_EVEN
```

不改变现有 production profile。

## 9.3 Specific speed expression tree

严格按 4.1 当前运算树，不做 algebraic reassociation。

## 9.4 Water expression tree

严格按 4.5 当前表达式树。总流量 `QBEP` 进入公式中的 `ln(Q)`；`Q/S/3600` 只服务 specific speed。

## 9.5 Chemical expression tree

严格按 4.6 当前表达式树；`min(QBEP,3000)` 只用于 `eta_b` 的 `ln(Q)`，不改变标准适用范围；多项式按当前 coefficient order 左到右累加。

## 9.6 Comparison

```text
actual_efficiency >= full_internal_threshold
```

禁止在 comparison 前应用 conformance tolerance、display rounding 或 epsilon。

## 9.7 Output normalization

- exact vector：序列化十进制值供 exact decimal comparison；
- nonlinear vector：reference value 保存为十进制字符串，但跨语言 runner 先解析为高精度数再按 vector tolerance 比较，不要求字符串字节相等；
- decision fields：rule_id/status/grade/conclusion exact；
- display fields：若单独测试，按现有 HALF_UP/6 places 规则，不与 calculation value 混合。

### 为什么需要 reference procedure

**需要。** 只有 tolerance 而没有 operation tree/reference procedure，会无法判断两个都“接近”的实现哪一个代表被批准的业务算法；尤其 near-boundary 时会出现数值差很小但业务 branch 不同。

但 `PUMP-RP-0.1` 只应作为 N01-B candidate。是否上升为公共 Transcendental reference procedure，必须等待 D-001 的跨 Pilot / 跨语言证据。

---

# 10. Decimal50 是否应成为平台全局规则

本设计建议：**NO。当前只把 Decimal50 保留为 Pump Numeric Profile candidate。**

理由：

1. 当前真实证据只覆盖离心泵；
2. 中央 Numeric DRAFT 已明确不统一固定全局 precision=40/50；
3. N01-A / N01-C 的运算复杂度、rounding/tolerance 语义不同；
4. 50 位对 Python 离心泵实现已稳定，但尚无 Kotlin/Swift/ArkTS 成本/收益证据；
5. 平台真正需要冻结的是“声明 precision + 可验证 business outcome + conformance”语义，不必先冻结所有 Calculator 同一 precision。

候选定位：

```text
profile_id: EQUIPEFFI_PUMP_DECIMAL50_V2
scope: pump_water + pump_chemical numerical reference
platform_status: CANDIDATE / NOT FROZEN
```

---

# 11. 跨语言 Kotlin / Swift / ArkTS Conformance 设计

本阶段**不实现这些平台**。未来验收建议统一要求：

## 11.1 每个平台必须声明

- language/runtime version；
- decimal implementation/library 与版本；
- `sqrt / ln / fractional pow` backend/algorithm；
- working precision；
- rounding mode；
- operation-order implementation；
- decimal serialization/normalization 方法。

## 11.2 输入要求

Canonical/vector 数值必须从 decimal text 进入权威链，不能先读取为 `Double` / `Number` 再恢复十进制。

若某语言原生 Decimal 不提供 `ln/pow`，允许使用其他高精度实现；**本 Pilot 不指定库**，由 Conformance Vectors 验收行为。

## 11.3 验收层级

1. exact vectors：exact decimal/result/decision；
2. nonlinear atomic vectors：candidate tolerance；
3. composite pump vectors：candidate tolerance；
4. rule_id / interval / grade / status / conclusion：必须 exact；
5. binary-float typed-input negative vector：必须拒绝或在正式 adapter 层证明不会进入 authoritative calculator；
6. precision sensitivity/stress vector：必须记录结果；
7. `REFERENCE_SENSITIVE` vector：即使 numerical error 在 tolerance 内，只要业务 decision 不同仍 FAIL。

## 11.4 当前不得宣称

在 Kotlin/Swift/ArkTS runner 真正实现并执行前，不得写：

- “跨语言一致性已验证”；
- “Decimal50 足以覆盖所有平台”；
- “T-NL-ATOM / T-NL-COMPOSITE 已被跨语言证明”；
- “D-001 可以关闭”。

---

# 12. Minimal implementation changes（后续 Execution，当前不执行）

N01-B Execution 应尽量**零业务算法改动**。候选最小范围：

1. 新增本地 candidate vector 文件，例如：  
   `specs/equipment_efficiency/conformance/numeric/pump_n01_b_vectors_v0_1.jsonl`
2. 可新增一个**本地 candidate schema**，明确不是中央 v1：  
   `specs/equipment_efficiency/conformance/numeric/pump_n01_b_vector_candidate.schema.json`
3. 新增定向测试：  
   `tests/unit/test_pump_numeric_conformance_n01_b.py`
4. 如需要批量生成 reference evidence，可新增只读工具：  
   `tools/export_pump_numeric_conformance_n01_b.py`
5. 新增 Execution report：  
   `QZC_N01_B_EXECUTION_REPORT.md`

默认禁止修改：

- `src/equipeffi/domain/evaluation/evaluators/pump.py`
- `src/equipeffi/domain/evaluation/grading.py`
- `src/equipeffi/domain/evaluation/decimal_math.py`
- `src/equipeffi/resources/standards/pump.json`
- 18 条 Approved Golden 0.4
- `platform-lock.json`
- GB 19762—2025 业务算法/表值/边界

如果 Execution 发现现有实现无法产生必要证据，应先报告 BLOCKED/变更理由，再单独批准生产代码变更；不得为了让 vectors 通过而改算法。

---

# 13. Regression Plan（后续 Execution，当前未运行）

Execution 至少应真实运行并记录：

```text
python -m unittest \
  tests.unit.test_pump_numeric_contract_v2 \
  tests.unit.test_pump_rule_integrity_v2 \
  tests.unit.test_pump_generated_boundaries_v2 \
  tests.unit.test_golden_case_0_4_approval -q
```

再运行：

```text
python -m unittest \
  tests.unit.test_application_api \
  tests.contract.test_device_metadata \
  tests.contract.test_architecture_boundaries \
  tests.unit.test_device_evaluator_matrix -q
```

以及：

```text
python -m compileall -q src tools tests
git diff --check
```

N01-B 新增 vector runner 必须单独报告：

- exact vector count / pass / fail；
- nonlinear vector count / max absolute error / max relative error；
- boundary vector count / decision mismatches；
- precision sensitivity table；
- reference-sensitive branch flips（如有）。

若运行 full suite，必须把既有基线失败与本 Pilot 新回归分开，不能隐藏或顺手修复非 Numeric 问题。

---

# 14. Execution Prompt Draft

以下提示词供用户后续**单独授权 Execution**时使用；本设计阶段不执行：

```text
仓库：
https://github.com/adgo07/EquipEffi.git

任务：
QZC-N01-B — EquipEffi Transcendental Numeric Pilot Execution

先完整读取：
- QZC_N01_B_LOCAL_DESIGN.md
- docs/PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md
- src/equipeffi/domain/evaluation/evaluators/pump.py
- src/equipeffi/infrastructure/standards/json_repository.py
- tests/unit/test_pump_numeric_contract_v2.py
- tests/unit/test_pump_generated_boundaries_v2.py
- 18 条 Approved pump_water Golden 0.4
以及中央 N01-B Distribution / Numeric Contract DRAFT / DECISIONS_NEEDED。

从用户验收后的 Design fixed SHA 开始。

本轮目标只有：
1. 建立 N01-B candidate conformance vectors；
2. 建立本地 candidate vector schema/runner；
3. 用当前 Decimal50 实现生成 reference evidence；
4. 实际运行 exact / nonlinear / boundary / precision-sensitivity tests；
5. 形成 QZC_N01_B_EXECUTION_REPORT.md。

严格禁止：
- 重写 GB 19762—2025 离心泵算法；
- 修改 pump.py 数值公式、ns_raw、Decimal50、Q/H/S/N 语义；
- 给业务等级比较增加 epsilon/tolerance；
- 修改 pump.json 标准值；
- 修改 Approved Golden；
- 修改 platform-lock.json；
- 实现 Kotlin / Swift / ArkTS；
- 把 candidate tolerance/Decimal50 宣布成平台规则；
- 顺手做 UI、Excel、数据库、Phase 2 架构重构。

向量必须至少覆盖：
- decimal parse；
- binary float rejection；
- exact specific-speed constructed case；
- sqrt；
- ln；
- fractional pow；
- real water Golden E2E；
- chemical eta_b/delta technical case；
- flow/ns boundary；
- threshold T-delta/T/T+delta；
- operation-order sensitivity；
- precision sensitivity；
- reference-sensitive near-boundary diagnostic；
- invalid-domain guard。

所有 nonlinear tolerance 只允许存在于 conformance/test 层。
rule_id / status / grade / conclusion 必须 exact match。
若 numerical value 在 tolerance 内但业务 decision 不同，判 FAIL。

输出：
- Execution head SHA
- actual diff
- vector location/schema/count
- actual commands/results
- max abs/rel drift
- precision sensitivity results
- boundary decision results
- candidate rules vs pump-specific rules
- D-001/D-004/D-012 evidence
- QZC_N01_B_EXECUTION_REPORT.md

完成后停止，等待独立验收。
```

---

# 15. Acceptance Criteria（供后续独立验收）

N01-B Execution 只有同时满足以下条件，才有资格进入独立验收；是否 PASS 仍由独立验收决定：

1. 基于固定 Design baseline / Execution head SHA；
2. 实际 diff 没有未经授权的业务算法、Canonical、Golden、platform-lock 变更；
3. exact vectors 对 exact fields 全部 exact pass；
4. raw binary float negative vector 确实在正式泵入口被拒绝；
5. nonlinear vectors 输出 actual/reference/error/tolerance，不只写 PASS；
6. tolerance 只存在于 conformance/test，不进入 production grade logic；
7. `ns_raw` 继续未经 ROUND6/显示修约参与 branch；
8. rule_id / interval / status / grade / conclusion 全部 exact；
9. boundary vectors 覆盖 exact/inside/outside 和 T−δ/T/T+δ；
10. `REFERENCE_SENSITIVE` 若发生 business branch flip，必须显式 FAIL/BLOCKED，不得用 tolerance 豁免；
11. precision sensitivity 至少比较多个 test-only working precisions，并证明 production 50 未被降低；
12. operation-order-sensitive case 有实际差异报告；
13. Approved Golden 不被重算后覆盖；
14. current Python tests 与新增 vector tests 有真实命令和退出码；
15. 静态审计、真实运行、真实数值重算、跨语言执行四类证据明确分开；
16. 未执行 Kotlin/Swift/ArkTS 时明确写 `NOT EXECUTED`；
17. 不宣布 Decimal50 / HALF_EVEN / candidate tolerance 为平台 FROZEN；
18. 回报可映射到 `N01_PILOT_RETURN_TEMPLATE.md`，并对 D-001 / D-004 / D-012 给出 evidence，而不是直接关闭它们。

---

# 16. 对中央 OPEN Decisions 的本地建议

| Decision | N01-B 可提供的新证据 | 当前建议 | 本 Design 可冻结吗？ |
|---|---|---|---|
| D-001 Transcendental reference procedure | Pump-RP-0.1、真实 sqrt/ln/pow、operation-order、near-boundary branch risk | 进入 Execution 收集真实 drift，后续再做跨语言 | **NO** |
| D-004 Conformance Vector schema | exact/nonlinear/boundary 三类字段、intermediate/tolerance/decision/provenance | 形成 `n01-b-pump-numeric-vector-0.1` candidate | **NO** |
| D-012 tolerance vs exact | full-value business compare + nonlinear conformance tolerance 分层 | 候选原则为“算法/业务无 epsilon；跨实现数值层可显式 tolerance；业务 outcome exact” | **NO** |

本 Pilot 对 Unit Contract 暂无变更建议：`No change proposed`。Q/H 单位与 standard formula coefficient 的关系保持现有业务契约，不在 N01-B 扩展为 Unit Contract 重构。

---

# 17. 设计结论

1. **Decimal50 当前是离心泵专用 Numeric Profile，而不是 EquipEffi/青舟全局 Numeric Policy。**
2. **ROUND_HALF_EVEN 当前覆盖 Pump Decimal 工作 Context；显示 `rounded()` 仍是 HALF_UP/6 位，二者必须分开。**
3. **Pump authoritative input 已有 binary float rejection；Pump 标准小数也通过 JSON lexeme → Decimal 隔离 binary float。**
4. **`ns_raw`、sqrt、ln、fractional pow、water/chemical nonlinear formulas 都已有明确 Python Decimal50 事实实现，但尚无跨语言 conformance guarantee。**
5. **业务阈值继续 full-value exact compare；不得把 numerical tolerance 注入 grade algorithm。**
6. **一般 nonlinear outputs 跨语言应采用显式 numerical conformance tolerance，而离散业务 outcome 必须 exact。**
7. **需要 candidate reference procedure；否则 operation-order 和 near-boundary 差异无法审计。**
8. **`EQUIPEFFI_PUMP_DECIMAL50_V2` 应暂时保持 Pump-specific candidate，不升级为全平台 precision=50 规则。**
9. **Kotlin/Swift/ArkTS 未来按同一 vectors 验收，但本阶段不实现、不宣称已验证。**
10. **本设计只完成静态审计与 Execution/Acceptance 方案，N01-B Gate 2 尚未开始，更没有 PASS。**

---

## Explicit final statement

- **Business project acceptance:** `NOT YET PERFORMED`
- **Static audit completed:** `YES`
- **Numerical results actually executed in this design task:** `NO`
- **Conformance vectors actually executed:** `NO`
- **Cross-language implementation actually executed:** `NO / NOT IN SCOPE`
- **This design freezes a platform-wide Numeric/Unit rule:** `NO`
- **Business code modified:** `NO`
- **GB 19762—2025 algorithm redesigned:** `NO`
