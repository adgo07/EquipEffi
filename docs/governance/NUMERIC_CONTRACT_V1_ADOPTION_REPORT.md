# Numeric Contract v1 Adoption Report

状态：**EXECUTION COMPLETE / READY FOR INDEPENDENT ACCEPTANCE**
任务：`Numeric Contract v1 Adoption`
仓库：`adgo07/EquipEffi`
执行分支：`chore/numeric-contract-v1-adoption`
起始 `master`：`9efc6260b03d9e0a895abdb294a70cda39aa7598`
中央仓：`adgo07/Qingzhou-contracts`
中央冻结基线：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`
技术验证 head：`b1683e89ee72fa6ae5e5be7f073c123590fc2a23`
技术验证 Actions：Numeric Adoption push `36811317025`；PR checks `36811320886 / 36811320889 / 36811320954`

> 本任务是 Frozen Numeric Contract v1 的采用与兼容性验证，不是新的 Numeric Pilot，不重新设计 GB 19762—2025 离心泵，不启动 Phase 2，也不授权合并。

---

## 1. Central Frozen baseline

已核实中央 `ee5feb0cc34dbd99790500fadd0c4c932e202a20` 为 QZC-N01-E Numeric Contract v1 Freeze 的合并基线。

正式采用：

- `contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md`
- Numeric Contract version：`v1`
- Numeric Contract status：`FROZEN`

Frozen v1 的关键公共义务包括：

- authoritative calculation scope 必须声明有效 Numeric Profile；
- declared-profile consistency 与 ambient independence 分开验收；
- 默认正式业务比较为 full-value exact comparison；
- implicit rounding 默认禁止；display rounding 不得反馈正式 comparison；
- tolerance 必须按 purpose 分类，禁止 platform-global epsilon；
- numerical tolerance 不得掩盖 rule/bucket/grade/status/conclusion mismatch；
- transcendental/nonlinear capability 必须有 reference procedure，并固定 operation order、normalization、reference output 与 conformance 语义；
- 正式结果必须可追溯 Numeric Contract version、Numeric Profile ID、calculator/rule version；允许通过等价不可变 trace/reference 结构实现；
- 不冻结全平台统一 precision、统一 rounding mode、统一 epsilon 或统一 transcendental tolerance。

中央仍明确保持 OPEN / NOT FROZEN 的内容，本仓没有擅自冻结：Unit Contract、完整 Quantity/coefficient schema、Kotlin/Swift/ArkTS transcendental 实测、平台 minimum precision、universal tolerance、最终统一 Result/Record 字段位置等。

---

## 2. platform lock adoption

`platform-lock.json` 已从旧中央 SHA：

`0cd74d783fa23add6dc881b408a8c8ba8503f8e8`

显式升级到：

`ee5feb0cc34dbd99790500fadd0c4c932e202a20`

Numeric 项更新为：

```text
version = v1
status  = FROZEN
path    = contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md
```

没有连带升级：

- Unit Contract：仍 `draft-v1 / DRAFT`；
- Module/Capability：仍 `draft-v1 / DRAFT`；
- Record/Result：仍 `draft-v1 / DRAFT`；
- qzpack/Package：仍 `draft-v1 / DRAFT`。

Architecture 继续为 `V2.1 FROZEN`。中央后续 main 变化仍不会自动进入本仓，升级继续要求显式修改 `PLATFORM_BASELINE.md` 与 `platform-lock.json`。

---

## 3. Pump Numeric Profile adoption

新增机器可读本地声明：

`specs/equipment_efficiency/numeric/equipeffi_pump_numeric_profile_v1.json`

正式保留 N01-B 已验证 Profile：

```text
numeric_profile_id       = EQUIPEFFI_PUMP_DECIMAL50_V2
numeric_contract_version = v1
representation           = strict Decimal text / Decimal / exact integer
working_precision        = 50
working_rounding         = ROUND_HALF_EVEN
business_comparison      = full-value exact
implicit_pregrade_round  = forbidden
transcendental           = PUMP-RP-0.1
operation_order          = explicit Pump reference procedure/current production tree
numerical_tolerance      = purpose-specific conformance only
display_rounding         = ROUND_HALF_UP / 6 places / presentation only
binary_float             = rejected for authoritative Pump input
```

明确：

> `Decimal50 + ROUND_HALF_EVEN` 是 EquipEffi Pump Profile 的具体配置，不是 Numeric Contract v1 的平台全局默认。

变压器、电机、风机和未来设备没有因本任务被迁移到 Decimal50；未来每个 authoritative Calculator 按自身标准/算法证据声明有效 Numeric Profile。

---

## 4. Frozen Contract compatibility result

| Frozen Numeric v1 requirement | EquipEffi Pump evidence | Result |
|---|---|---|
| Explicit Numeric Profile | machine-readable `EQUIPEFFI_PUMP_DECIMAL50_V2` declaration | PASS |
| Exact decimal authoritative ingress | strict Decimal text/Decimal/exact integer; float/non-finite rejected | PASS |
| Declared-profile consistency | production Pump precision/context constants match profile declaration | PASS |
| Ambient independence | evaluator wraps authoritative path in Pump Decimal context; altered ambient contexts reproduce identical result | PASS |
| Full-value business comparison | Pump comparison uses full Decimal value; no business epsilon | PASS |
| Rounding separation | working HALF_EVEN; display HALF_UP isolated from grade/rule/bucket | PASS |
| Nonlinear procedure | `PUMP-RP-0.1` covers sqrt/ln/fractional pow | PASS |
| Operation-order semantics | N01-B reference procedure/current expression tree explicitly retained | PASS |
| Numerical tolerance separation | conformance-only; business mismatch remains FAIL | PASS |
| Traceability | profile declaration + exact `platform-lock` + existing `EvaluationResult.standard_reference` / lookup/trace rule IDs | PASS |
| No global precision/rounding default | Decimal50 explicitly Pump-specific | PASS |

### Traceability implementation note

Frozen Numeric v1 允许将 `numeric_contract_version / numeric_profile_id / calculator-or-rule version` 直接放进 Result/Record，也允许使用等价不可变 trace/reference，只要结果可审计。

本次采用后者：

1. machine-readable Pump Profile 固定 Numeric Contract v1、Profile ID、rule version 与中央 SHA；
2. `platform-lock.json` 固定中央 Frozen Contract；
3. Pump 现有 `EvaluationResult.standard_reference` 固定标准/pack/data version；
4. lookup/trace 继续携带实际 table/data IDs。

因此本任务没有为了 Numeric adoption 先行设计统一 Result Envelope，也没有声称当前每个 `EvaluationResult` 都新增了直接字段 `numeric_profile_id`。统一 Result/Record 字段位置仍服从中央尚未冻结的 Record/Result 治理。

---

## 5. Production business code decision

**没有修改正式 Pump evaluator、Decimal math、Canonical、Approved Golden、Application route 或业务公式。**

原因：兼容性执行没有发现 Frozen Numeric v1 与现有 Pump production numeric semantics 的真实冲突。现有实现已经满足：

- Decimal50 declared working profile；
- HALF_EVEN authoritative context；
- binary float rejection；
- full-precision `ns_raw`；
- `sqrt / ln / fractional pow`；
- operation-order reference；
- full-value threshold comparison；
- display isolation；
- numerical tolerance/business result separation。

本任务新增的是 adoption governance、machine-readable Profile declaration、conformance test 和 CI，不重写已经正确工作的 Pump 算法。

执行过程中曾出现两处**新 adoption test 自身**问题：

1. 首版 T−δ 构造在 ambient Decimal context 下发生测试数据自身修约；改为在 Pump context 中构造边界值。该问题没有触及 production evaluator；
2. Profile declaration 测试要求字符串显式包含 `conformance`，而首版声明写作 `purpose-specific only`；将声明澄清为 `purpose-specific conformance only`。这只是治理语义明确化，不改变任何数值输出。

---

## 6. Real execution evidence

技术验证 head：`b1683e89ee72fa6ae5e5be7f073c123590fc2a23`。

Windows / Python 3.12 Actions 实际结果：

| Test group | Actual result |
|---|---:|
| Numeric v1 adoption/profile consistency | `6 / 6 PASS` |
| QZC-N01-B transcendental tests | `8 / 8 PASS` |
| Pump Numeric + generated boundaries + rule integrity | `15 / 15 PASS` |
| Pump evaluator + Application API | `408 / 408 PASS` |
| Golden + relevant Phase/metadata/architecture | `138 / 138 PASS` |
| compileall + diff check | `PASS` |
| Numeric Contract v1 Adoption workflow targeted gates | `PASS` |
| Phase 1 pump Windows checks | `PASS` |
| QZC-N01-B existing workflow | `PASS` |
| full suite command | `945 run; 9 failures; 6 errors; 3 skipped` |

### Full suite baseline interpretation

full suite 的真实命令结果仍为 failure；workflow 为保证证据上传，对该 step 使用 `continue-on-error`，因此不能把 UI step 的 completed/success 误写成 full suite 全绿。

N01-B 合并前基线为：

`939 run; 9 failures; 6 errors; 3 skipped`

本次加入 6 条 adoption tests 后为：

`945 run; 9 failures; 6 errors; 3 skipped`

因此本任务**新增 6 tests，新增 0 failure，新增 0 error，新增 0 skip**。

现存 9 failures / 6 errors 仍集中于既有、与 Numeric v1 adoption 无关的 build lock、isolated entrypoint/JSONL smoke、release audit/zipapp、desktop template、V4 reader/template/writer 等路径。本任务没有借 adoption 越界修复这些历史问题。

---

## 7. Actual diff boundary

相对起始 `master@9efc6260b03d9e0a895abdb294a70cda39aa7598`，本任务允许的 diff 仅包括：

- `platform-lock.json`；
- `PLATFORM_BASELINE.md`；
- `AGENTS.md`；
- `TASK_STATE.md`；
- `ROADMAP.md`；
- Numeric v1 adoption report；
- machine-readable Pump Numeric Profile declaration；
- adoption conformance tests；
- adoption CI workflow。

明确不应出现：

- Pump production evaluator / formula rewrite；
- `decimal_math.py` 改动；
- Canonical/standard data 改动；
- Approved Golden 改动；
- Unit/Record/Package Contract 升级；
- transformer/motor/fan Decimal50 批量迁移；
- Phase 2 实现。

---

## 8. Adoption conclusion

### Frozen Numeric Contract v1

**ADOPTED on this branch, pending independent acceptance and user-controlled merge.**

### Pump Profile

**COMPATIBLE with Frozen Numeric Contract v1.**

### Production algorithm change

**NONE.**

### Other devices

**NOT migrated to Decimal50.**

### Phase 2

**NOT STARTED / NOT AUTHORIZED by this task.**

### Merge

**NOT PERFORMED.**

下一步仅为：以 PR 最新固定 SHA、实际 diff、最终 CI 和本报告进行 **Numeric Contract v1 Adoption Independent Acceptance**。独立验收通过后仍由用户决定是否合并。
