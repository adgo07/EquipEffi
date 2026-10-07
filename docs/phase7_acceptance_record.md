# Phase 7 Acceptance Record

轻量验收落档：**只记录验收事实，不复制验收报告**。
格式沿用 `docs/phase3_acceptance_record.md` 起沿用的同一格式，不建立重治理流程。

| 字段 | 值 |
|---|---|
| phase | `Phase 7` — GB19762 分析流程与历史记录最终收口 |
| verdict | `PHASE_7_PASS` |
| acceptance date | 2026-10-05 |
| accepted head | `7d6f46c05eb1a6ad7a72dd2dc4a3bf964f29cf62` |
| PR | `#15` |
| merge SHA | `79ea075967ace07aa9880369220d8bff9b53d9e8`（master） |
| independent acceptance 来源说明 | 见下 |

## independent acceptance 来源说明

**Phase 7 PASS 为产品负责人收到独立验收后作出的验收决定，不是执行者自行宣告 PASS。**

- 独立验收**第一轮**对 head `515229e2e08c8685bed7f8b7c4d0ee28e539f89d` 给出
  `PHASE_7_BLOCKED`，三项阻断（595 项保护测试与 Required CI 均通过，
  但未覆盖这三项，执行报告相关 PASS 声明与实测不符）：
  1. **类别联动改变合法输入**：`CATEGORY_FIELD_CONSTRAINTS` 把
     `单级石油化工离心泵` 强制锁为 `单吸`；已批准 Golden
     `GC-PUMP-V5-CHEMICAL-DOUBLE-SUCTION` 的合法输入正是
     「单级石油化工离心泵 + 双吸」，锁定后 Record 被写成单吸，
     比转速由 `135.8439…` 变为 `192.1123…`。
  2. **两位小数显示未落实**：`analysis.py` 的格式化名单与实际派生量名称不匹配，
     普通结果仍显示数十位小数。
  3. **历史详情不完整**：记录详情未展示冻结的缺失信息与判定解释，
     资料不足 Record 只显示「无法判定」；派生参数丢失名称，仅显示数值串。
- 执行者逐项修复：石化类**不再约束吸入方式**（域层石化分支无类别↔吸入方式一致性
  检查），显示格式化改为**基于数值类型**判定，记录详情补出
  「缺失信息」「判定说明」并保留派生参数名称；并新增 8 项针对性回归
  （其中一项直接回放该 Golden 的原输入断言比转速）。
- 修复后 head 为 `7d6f46c05eb1a6ad7a72dd2dc4a3bf964f29cf62`，其 Required CI 全绿
  （`Windows Core` / `Pump Conformance` / `Whitespace check` / `Full suite baseline`）。
- 产品负责人在收到独立验收结论后作出 `PHASE_7_PASS` 决定，并授权以 PR #15
  合并于 `79ea075967ace07aa9880369220d8bff9b53d9e8`。
- 仓库内未另存独立验收报告正文，故以产品负责人验收决定 + PR #15 合并事实
  为记录来源。

## 说明

- 本 Record **不构成** Phase 7 执行报告的副本，也不替代
  `PHASE7_EXECUTION_REPORT.md`（其中含复验修复的完整记录）。
- `Phase 7 implementation = EXECUTION_COMPLETE`（执行状态）与
  `Phase 7 = PHASE_7_PASS`（独立验收结论）是两个维度，不得混用。
- **`PHASE_8_PASS` 尚未产生，不得提前书写。**
- Phase 7 遗留的 `QA-P7-001`（`ruleset_version` / `calculator_version` 实际存
  profile 标识）与 `QA-P7-002`（旧 Record 未冻结完整标准依据）保持
  `REGISTERED_DEVIATION`，不因本次验收而关闭。
- 本次验收暴露的一条经验已落到执行方式上：**阶段关闭事实应落在不可变的
  acceptance record 中，而「当前状态」文件会随后续 Phase 演进，
  不得被当作永久记录来断言。**
