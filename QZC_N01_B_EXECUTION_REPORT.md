# QZC-N01-B — EquipEffi Transcendental Numeric Pilot Execution Report

> 状态：`HISTORICAL-SUPERSEDED`
> 用途：`QZC-N01-B` Transcendental Numeric Pilot 的历史审计证据（记录当时真实执行与数值结果）
> 注意：不得作为当前正式规则依据。本报告的 `Central lock：0cd74d783fa23add6dc881b408a8c8ba8503f8e8` 与“READY FOR INDEPENDENT ACCEPTANCE / Gate 2 NOT YET DECIDED”均为当时状态，已被后续 Numeric Contract v1 Adoption 与独立验收结论取代；历史正文与当时结论不得改写。
> 当前权威：`platform-lock.json` / `PLATFORM_BASELINE.md`（locked `ee5feb0cc34dbd99790500fadd0c4c932e202a20`）、`docs/governance/NUMERIC_CONTRACT_V1_ADOPTION_REPORT.md`、`REFERENCE_STANDARD_ROADMAP.md`、`TASK_STATE.md`。

状态：**EXECUTION COMPLETE / READY FOR INDEPENDENT ACCEPTANCE**
Pilot：`QZC-N01-B`
代表 Profile：GB 19762—2025 离心泵
执行分支：`qzc-n01-b/transcendental-execution`
Execution tested head：`96db30a4c63730c8693f0fc1fbebb5301e1809b7`
Execution report/vector-only follow-up：报告提交后 head 高于 tested head；正式独立验收应以 PR 最终固定 SHA 与实际 diff 为准。
Design baseline：`b336fd313ea8e3ee1c688786c05d126d76dc2699`
Execution start master：`77acc7d31a687dbe43c878b809109afe2bd13ae0`
Golden：`golden-case-0.4`（Approved pump_water Golden 保持不变）
Current local numeric profile：`EQUIPEFFI_PUMP_DECIMAL50_V2`
Reference procedure candidate：`PUMP-RP-0.1`
Central lock：`0cd74d783fa23add6dc881b408a8c8ba8503f8e8`，本任务未修改 `platform-lock.json`。

> 本报告记录真实 Windows/Python 3.12 GitHub Actions 数值执行。没有修改中央 Contract 仓，没有启动 Phase 2，没有修改 GB 19762—2025 正式业务算法、Canonical 或 Approved Golden。

---

## 1. Characterization：当前 Pump Profile 的真实行为

真实代码与 Local Design 的核心描述一致：

- working precision = `50`；
- working rounding = `ROUND_HALF_EVEN`；
- authoritative Pump numeric input = decimal text / `Decimal` / exact integer；
- raw Python `float` = rejected；
- Pump standard JSON decimal lexeme = `parse_float=Decimal`；
- `ns_raw` = full working value，不做 `ROUND(ns,6)`；
- rule/bucket/grade comparison = full-value Decimal comparison；
- hidden epsilon = none；
- display limit 使用既有 `rounded(..., 6)` / `ROUND_HALF_UP`，但 grade 仍使用未显示修约的 internal threshold。

本轮没有发现 float 泄露、display rounding 回流、math helper 绕过 Pump context 或 `ns_raw` 被隐藏修约的问题，因此**没有修改正式 Pump 业务实现**。

---

## 2. PUMP-RP-0.1 executable reference procedure

新增 `tools/qzc_n01_b_reference.py`，不是只写文字。其 candidate procedure 明确：

```text
canonical input -> strict exact decimal parse
context        -> precision=N, ROUND_HALF_EVEN
S              -> 1(single) / 2(double)
Q_ns_m3h       -> QBEP / S
Q_ns           -> Q_ns_m3h / 3600
H_ns           -> HBEP / stages
sqrt_Q         -> Decimal.sqrt(Q_ns)
H_pow_0_75     -> Decimal Context.power(H_ns, 0.75)
ns_raw         -> 3.65 * speed * sqrt_Q / H_pow_0_75
ln             -> Decimal.ln()
threshold      -> current Pump expression tree
comparison     -> exact/full-value business comparison
normalization  -> no implicit rounding before business comparison
output         -> reference intermediate + business output
```

同时实现只用于 sensitivity experiment 的数学等价 alternate tree：

- `H^0.75 = sqrt(H) * sqrt(sqrt(H))`；
- 清水公式 regrouping；
- 石化 `ηb` current sum-of-powers vs Horner polynomial。

这些 alternate procedure **没有替换 production evaluator**。

---

## 3. Exact cases

真实执行通过：

1. `sqrt(16) = 4` exact；
2. `ln(1) = 0` exact；
3. `16^0.75 = 8` exact；
4. exact specific-speed construct：
   - `QBEP=7200 m³/h`
   - 双吸 `S=2`
   - `HBEP=32 m`
   - `stages=2`
   - `speed=10 r/min`
   - `Q_ns=1 m³/s`
   - `H_ns=16 m`
   - `sqrt(Q_ns)=1`
   - `H_ns^0.75=8`
   - `ns_raw=4.5625`
   - precision 28/34/40/50/60 全部 exact；
5. direct threshold `T-δ / T / T+δ`，`δ=1E-48`：
   - `T-δ -> 2级`
   - `T -> 1级`
   - `T+δ -> 1级`
   - epsilon = false。

这证明 business threshold equality 仍是 exact/full-value，而不是 tolerance equality。

---

## 4. Precision sensitivity：28 / 34 / 40 / 50 / 60

代表性清水泵案例在所有五种工作精度下均保持相同业务结果；没有选择性省略低精度结果。

### WATER-TYPICAL

`Q=100, H=50, n=2900, 单吸, N=1`

```text
p28 ns = 93.82360344860450750501470111
p34 ns = 93.82360344860450750501470108313662
p40 ns = 93.82360344860450750501470108313662242356
p50 ns = 93.823603448604507505014701083136622423532335781578
p60 ns = 93.8236034486045075050147010831366224235323357815764624706762
```

全部得到 `GB19762-T3-01 / 1级`。p50 vs p60 `ns` 差为 `1.5375293238E-48`。

### WATER-MULTI

`Q=100, H=150, n=2900, 双吸, N=3`

全部 precision 得到 `GB19762-T3-07 / 1级`。p50 vs p60 `ns` 差为 `9.867517704E-49`。

### WATER-HIGH-FLOW

`Q=5000, H=90, n=1480, 双吸, N=1`

全部 precision 得到 `GB19762-T3-04 / 3级`。p50 vs p60 `ns` 差为 `3.070442911E-48`。

### Precision 结论

Execution **没有证明 precision=50 是得到正确业务等级的最低必要位数**。在已执行代表向量中，28/34/40/50/60 的 rule/grade 都一致。

但也**没有证据支持现在降低 production precision**：

- p50 已与 p60 高度收敛；
- 当前性能没有显示 Decimal50 构成实际瓶颈；
- 未来 Kotlin/Swift/ArkTS 尚未执行，无法用单一 Python 实验决定跨平台最低 precision；
- 降低 precision 会无必要地改变当前已批准 reference trace。

因此保留 Decimal50，定位为 **Pump-specific conservative safety margin / reference candidate**，不是平台全局最低要求，也不是被实证证明的数学最小值。

---

## 5. Operation-order sensitivity

实验证明：数学等价的表达式顺序在有限 precision 下**确实产生非零末位差异**。

### specific speed / fractional power / clean thresholds

WATER-TYPICAL current vs alternate：

- p28 `ns` difference：`2E-26`；
- p34：`5E-32`；
- p40：约 `0E-38`；
- p50：`6E-48`；
- p60：`1E-58`。

p50 清水 threshold current vs regrouped 最大差：`1E-47`。

### chemical ηb

`QBEP=100`，current sum-of-powers vs Horner：

```text
p28 diff = 8E-26
p34 diff = 4E-32
p40 diff = 3E-38
p50 diff = 3E-48
p60 diff = 1.0E-57
```

p50：

```text
current = 72.994964439329567466446659598229238364944975446517
Horner  = 72.994964439329567466446659598229238364944975446520
```

这些差异在当前向量中没有改变 rule、bucket 或 grade，但已经足以证明：

> **operation order 应进入 Pump reference procedure / conformance semantics。**

这不是因为当前表达式错误，而是为了防止未来语言/编译器“数学等价重排”后产生无法解释的跨实现末位漂移。

---

## 6. Tolerance experiment

Local Design 的 seed：

```text
T-NL-ATOM      = max(1E-13, 1E-13 * |reference|)
T-NL-COMPOSITE = max(1E-10, 1E-12 * |reference|)
```

实测表明它们作为当前高精度 Python reference 的验收阈值**明显过宽**。

典型 observed differences：

- p50 vs p60 composite：约 `1E-48`；
- p50 operation-order difference：约 `1E-47 ~ 1E-48`；
- chemical ηb p50 current vs Horner：`3E-48`；
- 而 seed limit 为约 `1E-10`。

因此本次 Execution **拒绝把设计 seed 升级为正式 tolerance**。它可以保留为历史 experiment seed，但不能成为平台或 Pump 正式允许误差。

当前能确认的正式语义只有：

1. business comparison 继续 exact/full-value；
2. tolerance 只能用于 cross-implementation numerical conformance；
3. 即使 numerical value 落在 tolerance 内，只要 `rule_id / bucket / grade / status / conclusion` 任一不同，仍必须 FAIL；
4. Kotlin/Swift/ArkTS 尚未真实实现，因此合理的跨语言 tolerance 仍为 OPEN，应由后续真实平台向量测量再冻结。

---

## 7. Candidate Conformance Vectors

新增并真实执行：

- executable generator：`tools/run_qzc_n01_b_pilot.py`；
- executable tests：`tests/unit/test_qzc_n01_b_transcendental.py`；
- durable candidate vector snapshot：`specs/equipment_efficiency/numeric/qzc_n01_b_vectors_candidate_0_1.json`；
- CI evidence artifact：`qzc-n01-b-evidence`。

当前 durable snapshot 覆盖：

- Exact specific speed；
- Composite water typical；
- Composite multistage；
- Composite high flow；
- chemical ηb operation-order sensitivity；
- business boundary `T-δ/T/T+δ`。

另外 executable tests 覆盖 binary-float/non-finite rejection、sqrt/ln/fractional power、Approved Golden replay、precision sensitivity、operation-order sensitivity。

Vector 字段已经包含：`inputs / profile / operation / reference / acceptance_mode / tolerance_purpose / business_output`。这是 N01-B candidate schema，不冻结中央 D-004。

---

## 8. Real test execution

最终 tested head：`96db30a4c63730c8693f0fc1fbebb5301e1809b7`。
GitHub Actions run：`36680958245`，Windows latest / Python 3.12。

| Test group | Actual result |
|---|---:|
| PUMP-RP-0.1 / N01-B new tests | `8 / 8 PASS` |
| Pump numeric + generated boundary + rule integrity | `15 / 15 PASS` |
| Evaluator matrix + Application API | `408 / 408 PASS` |
| Golden + schema + metadata + architecture | `138 / 138 PASS` |
| compileall + diff check | `PASS` |
| targeted N01-B CI gate | `PASS` |
| full suite command | `939 run; 9 failures; 6 errors; 3 skipped` |

### Full suite 解释

Workflow 中 full-suite step 使用 `continue-on-error` 以保证无论历史 suite 是否绿都能上传完整 evidence；因此 GitHub step UI 显示 completed/success，但 artifact 的 `step_outcomes.txt` 和 `full_suite.log` 记录真实命令结果为 `fullsuite=failure`。

本轮 full suite 的失败/错误集中在既有非 N01-B 范围，例如：

- build lock / isolated entrypoint / JSONL smoke；
- release audit；
- zipapp；
- desktop template path；
- V4 reader/template/writer。

本任务没有修改这些业务路径。与此同时，Pump Numeric、Pump evaluator/Application、Golden/Phase1、compile/static 和新增 N01-B tests 均独立通过。因此本轮不借 Numeric Pilot 顺手修这些 unrelated failures，也不把 full suite 写成 PASS。

---

# 9. Execution Report 必答 11 项

### 1. Decimal50 是否保留？

**保留。**

### 2. 为什么？

实测 28/34/40/50/60 的代表业务输出一致，说明 50 位不是已证明的最低需求；但 50 与 60 高度收敛、当前没有实际性能问题、跨语言最低精度尚无证据，且现有 Approved reference trace 已基于 Decimal50。因此目前把 50 位保留为 Pump-specific conservative safety margin 最合理，不无证据降为 40/34/28。

### 3. HALF_EVEN 是否仅属于 working context？

**是。** 当前证据支持 `ROUND_HALF_EVEN` 是 Pump authoritative working context 的运算舍入模式，不是全平台 rounding rule，也不是 display rule。

### 4. display HALF_UP 是否仍完全隔离？

**是，针对当前 Pump 路径。** `rounded(...,6)` / HALF_UP 只生成 display/limits；等级仍以未显示修约的 full internal thresholds 比较。T-δ/T/T+δ 和 existing threshold tests 均通过。

### 5. current operation tree 是否稳定？

**作为当前 Pump reference candidate：稳定，应显式保留。** 数学等价重排会造成有限精度末位差异，因此 operation tree 需要进入 PUMP-RP/conformance；当前未发现它导致错误业务结果，无证据改写 production tree。

### 6. nonlinear reference procedure 是否可以跨语言复现？

**已经达到“可执行候选规范”的程度，但尚未完成跨语言实证。** `PUMP-RP-0.1` 已给出严格输入、constants、operation sequence、sqrt/ln/fractional pow、precision/rounding、normalization、outputs 与 business comparison，并有 executable vectors；但 Kotlin/Swift/ArkTS 本阶段没有实现和执行，所以不能声称已跨语言验证。

### 7. candidate tolerance 是否合理？

**设计 seed 不合理地偏宽，不能冻结。** 当前 p50/p60 和 operation-order 实测差约 `1E-47~1E-48`，而 seed 约 `1E-10`。未来跨语言 tolerance 应在真实 Kotlin/Swift/ArkTS 实现后从 evidence 重新估计；business output 永远 exact。

### 8. 哪些是 platform candidate？

建议提交中央 Gate 4 review，但不冻结：

- Canonical decimal text / authoritative chain 不接受 binary float business truth；
- calculation / comparison / display 分离；
- business boundary 默认 full-value exact comparison；
- transcendental capability 必须有 reference procedure + numerical conformance vectors；
- numerical tolerance 与 business equality 分层；
- tolerance 不能挽救不同的 rule/bucket/grade/status/conclusion；
- operation-order-sensitive formula 应声明 expression semantics。

### 9. 哪些必须是 Pump-specific profile？

当前证据只能支持 Pump-specific：

- precision=50；
- Pump working context `ROUND_HALF_EVEN`；
- `3.65`、`Q/S/3600`、`H/N`、`sqrt`、`H^0.75`、GB19762 ln/polynomial 的具体 operation tree；
- `PUMP-RP-0.1`；
- Pump display helper 的 `ROUND_HALF_UP / 6 places`；
- GB 19762 的 rule/bucket/threshold business semantics。

### 10. 有没有修改正式业务代码？

**没有。** 未修改 `src/.../pump.py`、`decimal_math.py`、Canonical、Application business route、Approved Golden 或 platform lock。

### 11. 若修改，结果变化是什么？

**N/A。** 没有 production business change。Execution 期间修正过两处新测试/证据生成器自身问题：一处 T-δ 构造曾落在 ambient Decimal context；一处 Golden replay 初版错误选中了历史旧 schema 文件。修复后没有改变 production 输出，只使 Pilot evidence 正确反映既有 Pump Numeric semantics。

---

## 10. Future Kotlin / Swift / ArkTS acceptance candidate（本阶段未实现）

未来平台验收建议至少要求：

1. 使用完全相同 canonical decimal input lexeme；
2. Exact vectors 必须 exact；
3. nonlinear atomic/composite 对 PUMP-RP reference 值采用未来正式冻结的 numerical tolerance；
4. `rule_id / bucket / grade / status / conclusion` 必须 exact；
5. 数值落在 tolerance 内但业务输出不同仍 FAIL；
6. 必须运行 low/medium/high、near-branch、chemical、Approved Golden derived vectors；
7. operation tree 与 PUMP-RP 相同，或替代实现必须证明数值 conformance + business exact；
8. 每个平台保存真实工具链、precision/decimal library、运行结果和 fixed SHA。

本 Execution 不实现 Kotlin/Swift/ArkTS，因此 D-001/D-004/D-012 仍不能由 N01-B 单独关闭。

---

## 11. Final execution statement

- **Static implementation audit:** YES
- **Tests actually executed:** YES
- **Numerical results actually recomputed:** YES
- **Precision 28/34/40/50/60 actually executed:** YES
- **Operation-order alternatives actually executed:** YES
- **Boundary cases actually executed:** YES
- **Approved Golden replay actually executed:** YES
- **Conformance vectors actually executed:** YES
- **Cross-language implementation actually executed:** NO / NOT IN SCOPE
- **Production Pump algorithm changed:** NO
- **Central Contract changed:** NO
- **platform-lock changed:** NO
- **Platform-wide Numeric rule frozen:** NO
- **QZC-N01-B Execution status:** `COMPLETE / READY FOR INDEPENDENT ACCEPTANCE`
- **Gate 2 business acceptance:** `NOT YET DECIDED` — 必须由后续独立验收任务基于最终固定 SHA、真实 diff、Actions 和 evidence 给出。
