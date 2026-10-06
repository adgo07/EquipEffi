# PR #16 全面诊断：Excel 输出可靠性与反复验收失败

日期：2026-10-06（Asia/Shanghai）。任务性质：只读诊断，不代替正式独立验收，不修改实现、不合并、不进入 Phase 9。

## 结论

**问题比“最新一轮只是测试夹具错误”更严重。** 指定 head 仍可生成重复坐标的结果 Workbook，并保存成功 `batch_record`；其中一个独立反例重新读取后，正式 U4 限值为空。严重性在输出数据完整性与成功证据失真。

**现有证据不支持“整个软件业务算法已失控”或“必须推倒全仓”。** 本轮 29 Approved Golden 经 Excel 重放零漂移，原四项 blocker 回归通过，模板机械门禁通过。应针对 Writer 的解析、补丁边界、独立校验与文件落盘做集中修复，随后再交独立验收。

本 head 不具备 merge-ready 条件；Phase 8 保持 IN_PROGRESS。本文不宣布任何 Phase PASS。

## 1. 对象与平台预检查

| 项目 | 实测事实 |
|---|---|
| 仓库 | `https://github.com/adgo07/EquipEffi.git`，origin 核对一致 |
| PR | [#16](https://github.com/adgo07/EquipEffi/pull/16)，open、merged=false |
| 基线 | `79ea075967ace07aa9880369220d8bff9b53d9e8`，远端 master |
| 诊断唯一对象 | `5fea7fa0b79789d49277c504b0913266518416da`，远端 PR 分支 |
| 原工作区 | `phase8/gb19762-excel-batch@55167ee27bbcc5b4a73667c1cb4d07107d2aa07a`，未切换或修改 |
| 原既有未跟踪文件 | `docs/planning/`、`标准原文/`，未改动 |
| 执行方式 | fetch 后 git archive 指定 head 到 `.diagnosis-head/`；测试与夹具均在隔离快照或临时目录 |
| 默认分支同步 | origin 默认分支 master；本地 master 比 origin/master 落后 63 提交，不能作为当前验收对象 |
| 本地运行环境 | Windows，Python 3.13.3；远端 CI 为 Python 3.12.10，二者不混报 |
| 中央锁 | `ee5feb0cc34dbd99790500fadd0c4c932e202a20`，未升级 |
| 中央 origin | 已验证 `https://github.com/adgo07/Qingzhou-contracts.git` |
| Frozen 读取 | locked SHA 的 Numeric Contract v1 |
| ACTIVE 读取 | 当前已合并 `origin/main@b4738e9` 的 GUIDE_INDEX、Product Delivery Policy、UI Guidelines |
| 适用 MUST | 十进制权威链；显示与业务比较隔离；Excel 调用同一 Application；保留用户输入与其他 Sheet；输出新的 Workbook；成功记录基于真实成功输出 |
| 适用 MUST NOT | 不改 Golden/Canonical/业务真值；不复制 Excel 第二算法；不升级锁；不自行宣布 PASS/合并/进入 Phase 9 |
| 冲突分类 | 当前新增缺陷为 LOCAL DEFECT；未发现需要中央契约升级的需求 |
| Standard Issue | 已读台账；`EQP-STD-GB19762-001` 为既有日期产品规则，本轮未改变其解释；新增发现属于载体实现缺陷，不是标准解释变化 |

Base→Head 实际 diff：59 文件，+9496/−249；Writer 为 1229 行新模块。Domain、Approved Golden、Canonical、Numeric 与 platform-lock 没有本 PR 改动。Application 原泵服务的增量为用户文案与展示格式辅助函数，批量计算调用既有 `evaluate()`。

## 2. “验收”会话给出的失败轨迹

已通过 read_thread 读取 EquipEffi 的“验收”会话（`01a0e8e9-c201-73a1-ac4c-3779578ec005`），未向该会话发送消息。

| 验收 head | 失败内容 | 本轮理解 |
|---|---|---|
| `8cb6eec` | U/V/W 漏写；INVALID_INPUT 污染数量；输入精度改写；引用串批 | 真业务输出与批次语义缺陷，已有针对性修复 |
| `348a199` | row/c 属性顺序变化引发漏写或重复坐标 | Writer 误把一种 XML 序列化形式当作固定格式 |
| `f2518a9` | 前缀化 c 漏识别；“前缀测试”为 no-op | 解析身份错误叠加夹具假覆盖 |
| `fec8fd0` | 默认 namespace 为其他 URI 时错误去前缀 | 前缀字面值被当成 namespace 语义 |
| `55167ee` | 嵌套前缀重绑定改变扩展 payload 的 namespace | 根层声明代替词法作用域；成功证据未覆盖扩展保真 |
| `5fea7fa` | QName 门禁拒绝错误的混合前缀夹具，Required CI 失败 | 直接失败确为夹具问题；不能据此推论当前 Writer 已可靠 |

多轮后续问题主要属于同一缺陷族：手写扫描器对 XML 身份和序列化形式认识不完整；修复按已知反例逐项扩展，后置条件仍共享其盲区。

## 3. 本 head 新增独立发现

### D01 / P1：合法单引号属性绕过唯一性门禁，重复 U4 被当作成功

对真实 V6 输入，仅将已有 U4 的 `r="U4"` 改为 `r='U4'`，其余业务输入不动。

实测：正式 Reader 读取 1 行；输出包含 **2 个真实 `{MAIN_NS}c[@r='U4']`**，一个空 cell、一个 `79.786165`；输出文件存在；`evaluated_quantity=1`；成功批次记录新增 1 条。

根因：Writer 第 239 行 `_ATTR_RE` 只解析双引号；第 275 行 `_parse_attrs` 因而漏掉坐标。插入逻辑认为 U4 不存在，自检又使用同一 `_scan_cells`，再次漏掉原单引号坐标。XML 良构与元素 QName 比较不会发现重复业务坐标。

这不是非法 XML。XML 属性值允许单引号与双引号，见 [W3C XML AttValue](https://www.w3.org/TR/xml/#NT-AttValue)。用户常规 Excel 输出通常用双引号，故发生概率不能由此反例推断；但这是明确的合法输入与数据完整性缺陷。

### D02 / P1：属性命名空间被抹掉，重复坐标并导致正式限值静默丢失

给 U4 添加扩展属性 `e:r="ZZ999"`；根声明扩展 namespace 与 `mc:Ignorable="e"`。原无前缀 `r="U4"` 保留，所有正式业务输入不动。

实测：正式 Reader 读取 1 行；输出出现两个真实 U4；**正式 OOXML Reader reopen 后 U4 为空**；软件仍输出文件并保存 1 条成功批次记录。

根因：`_parse_attrs` 对所有属性取 local-name，把 `r` 与 `{urn:independent}r` 合并为同一个键，后者覆盖前者；扫描和唯一性检查看到的是 ZZ999，真正的 U4 被漏掉。属性身份必须包含 namespace，参见 [W3C Namespaces 属性唯一性规则](https://www.w3.org/TR/xml-names/#uniqAttrs)。

此反例包含人工扩展，本文证明其 namespace 语义与正式 Reader 行为，不声称已用桌面 Excel 或完整 OOXML XSD/MC 验证器验证所有兼容性。**D01 不依赖任何扩展即可独立成立，足以阻断。**

### D03 / P2：namespace 门禁误拒绝合法扩展内容

在工作表 `extLst/ext` 中放入独立 namespace 的 payload，其子元素名为 `e:t`、文本为 sentinel。

实测：正式 Reader 读取 1 行；Writer 以“核心元素不属于 SpreadsheetML”拒绝 `{urn:independent}t`；不产出结果、不保存记录。这次没有静默数据损坏，但合法扩展可使整批无法完成。

根因：第 1050 行 `_assert_main_namespace_semantics` 遍历整个树，按 local-name 为 t/c/row 等要求其全部属于 MAIN_NS，未限定实际 worksheet/sheetData/row/c 路径。扩展 namespace 恰好同名并不使它成为 SpreadsheetML 元素。[Microsoft Open XML Extension](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.extension?view=openxml-3.0.1)说明扩展容器可含任意 namespace 的 XML 内容并应整体保留。

### D04 / P2：磁盘写失败留下最终文件名的残缺 Workbook

独立注入第二个 ZIP entry 的 `writestr` 抛出 OSError，模拟磁盘写失败；不是实际制造磁盘故障。

实测：抛出系统异常、没有新增 batch_record；但最终目标文件已存在，ZIP 仅剩 1 个 entry；相同目标重试得到 `ResultWorkbookExistsError`。

根因：第 1216 行直接 `ZipFile(destination, 'w')` 落盘；“先完成 XML 校验”只覆盖内存阶段，不能保证实际 I/O 完整写入。没有临时文件提交或异常清理。报告“写失败不留下假成功结果文件”的概括超过代码实际保障范围。

### D05 / P2：大批量在 Qt 主线程同步执行，存在长时间无响应风险

`presentation/qt/pages/batch.py:211–221` 的按钮处理直接调用整批 `evaluate_workbook()`，没有后台任务或事件循环让出。指定 head 的 CI 日志实测 10,000 行耗时 **559.504 秒**、峰值约 **246.3 MB**。

因此在同等负载下，主线程可能约 9 分钟不能处理界面事件。本文没有在可见桌面进行 10,000 行交互复现；该结论为同步调用结构结合真实性能数据的推断。它是产品可用性风险，不是算法错误。先登记并测量，不能借此扩成缓存/Repository 重构。

## 4. 当前 CI 与本地测试事实

指定 head：Windows Core **failure**，Pump Conformance **success**。Windows Core Required Job 的 Phase 组 **441 run / 440 pass / 0 fail / 1 error / 0 skip**。唯一 error 为混合前缀夹具用例。

[失败 Job 与日志](https://github.com/adgo07/EquipEffi/actions/runs/37427173015/job/112149363580)。后续 comparator 与 package/resource smoke 未完成，不能把较早 head 的 green 移用为本 head 证据。

混合夹具问题已独立确认：先将全表改成 x: 前缀且移除默认 namespace，再将 N4 改回裸 c，得到的是**无 namespace 的 N4**。新增 QName 门禁拒绝语义变化是合理行为。仅在诊断脚本中给根补上默认 MAIN_NS，原用例独立通过；未修改正式测试或产品代码。

本轮本地独立验证（全在指定 head 快照）：

| 检查 | run | pass | fail | error | skip | not_run |
|---|---:|---:|---:|---:|---:|---|
| R2/R3/R1W Writer 专项 | 35 | 34 | 0 | 1 | 0 | 0 |
| 8A Reader/模板 + R1 原 blocker + 8B 批量 + 架构边界 | 113 | 113 | 0 | 0 | 0 | 0 |
| Golden/结论/边界一致性（排除 LargeVolumeTests 类） | 9 | 9 | 0 | 0 | 0 | LargeVolumeTests 未运行 |
| 正确 namespace 的混合前缀诊断用例 | 1 | 1 | 0 | 0 | 0 | 0 |
| 合计 unittest | 158 | 157 | 0 | 1 | 0 | 全量 suite / 本地 gating 全列表未运行 |

9 项一致性测试含 **29/29 Approved Golden Excel 重放零漂移**，不是“只有 9 条 Golden”。

其他实际检查：正式模板机械门禁 **PASS**；compileall src/tests/tools exit 0；Base→Head diff --check exit 0；4 个独立故障/边界 probe 已执行，结果见 JSON。这些 probe 用来证明缺陷，不计入上述通过测试数。

本轮没有重新运行完整 unittest、完整 conformance、完整 10,000 行性能测试，也没有进行所有 Qt 页面的可见桌面视觉验收。相关历史/CI证据与本次执行已分开。

## 5. 为什么几百项测试通过仍反复失败

1. **补丁与门禁共用扫描器**。写回漏掉的属性/坐标，自检也会漏掉；自检看起来严格，但缺乏独立性。
2. **local-name 不等于元素/属性身份**。主命名空间作用域、父子路径、属性 namespace 是不同问题；已有修复只覆盖其中部分。
3. **QName 门禁范围不足**。比较的是“结果补丁之后、namespace 归一化之前”和“归一化之后”的元素名序列，不证明原始非结果内容完整、不检查 cell 坐标/数值/属性。
4. **测试夹具没有系统验证前置语义**。历史 no-op 与本轮无默认 namespace 混合夹具均说明，“构造了字符串”不等于“构造了有效且等价的输入”。
5. **证据与 head 脱节**。执行报告仍称 R3 后仅文档变更、439 项全绿；指定 head 实际又有 `a34da73` 产品代码与 `5fea7fa` 测试提交，Required CI 441 项有 error。旧报告应保留为历史，但当前状态不能继续复用。
6. **治理状态本身有残留矛盾**。TASK_STATE/HANDOFF 同时出现 Phase 5 PASS 与 chemical SUPPORT_PROMOTION_CANDIDATE/Stage D pending、已关闭入口问题与旧 deviation 描述。不能据此推翻既有独立验收，但说明状态文件不应充当未经核对的结论来源。

这是一组集中在 Excel adapter 的结构性实现与验证问题，而非本轮有证据证明的 Domain 算法崩溃。

## 6. 建议的最小整改顺序

1. **先固化 D01/D02 独立回归并登记 QA**：输入用真正 XML 解析器验证；输出以独立解析器检查 `{MAIN_NS}sheetData/{MAIN_NS}row/{MAIN_NS}c` 的无前缀 r，要求坐标唯一、结果值等于正式 Application payload。不要再用 Writer 扫描器证明 Writer 正确。
2. **集中修复 Writer 身份解析与补丁边界**：元素按 expanded QName + 正式父子路径识别；属性保留 namespace 身份；遵守单/双引号与 entity 语义。保留不重序列化用户输入与其他 ZIP part 的精度要求。技术方案先以反例做小型验证，不强行换库或建立通用 XML 框架。
3. **用输入→输出的独立不变量兜底**：授权结果位置外输入值/属性/扩展保真；每个结果坐标恰好一次；thresholds/derived/结论文案与 Application 完全相同；再持久化 batch_record。QName 列表相等只是一项检查。
4. **修文件提交**：先在目标目录写临时完整文件，验证后提交最终文件；失败清理半成品、保留禁止覆盖输入与已有目标语义。补 I/O 故障回归。
5. **修合法夹具并统一覆盖矩阵**：属性顺序、两类引号、prefix/default/nested namespace、同名扩展元素与属性、实体、空/已有/重复 cell；每个变体先证明业务输入语义等价。无须建立大型 fuzz 框架。
6. **登记 Qt 性能风险并做产品实测**：后台执行与简单进度反馈是候选方向；不改计算、统计或数据库。不要只增加 CI timeout 来说明用户体验合格。
7. **按最终 head 重建交付证据**：先跑定向回归与 29 Golden，再过 required gating/conformance、实际容量/Qt交互与故障恢复；报告完整记录 fail/error/skip/not_run，并清理当前状态残留。最后固定唯一 final head 交独立验收。

无需修改标准解释、Golden 业务真值、中央 Frozen Contract 或既有单台 Record 语义；不建议推倒核心算法、扩大标准范围或进入 Phase 9。

## 7. 留存证据与复现

仓库根的 `.diagnosis-head/` 是指定 commit 的隔离快照；不是当前分支工作区代码。新增诊断脚本不属于原 commit。

- `.diagnosis-head/diagnose_independent.py`：四项独立反例/故障注入。
- `.diagnosis-head/independent-results.json`：输出坐标、reopen U4、成功记录数与残缺文件事实。
- `.diagnosis-head/independent-evidence/`：输入/输出 Workbook 与残缺结果文件（诊断样本，不是正式结果）。
- `.diagnosis-head/diagnose_valid_mixed.py`：只在测试运行时修正夹具 namespace，证明直接 CI error 的成因。
- `.diagnosis-head/diagnostic-tests.log`、`diagnostic-broad-tests.log`、`diagnostic-golden-tests.log`、`diagnostic-valid-mixed.log`、`diagnostic-template.log`。

复现：在该快照目录设置 `PYTHONPATH=src`、`QT_QPA_PLATFORM=offscreen`，运行 `python diagnose_independent.py`。脚本只产生临时输入/数据库与诊断证据，不访问正式用户 records.sqlite。

Knowledge capture：无。本文新增报告与诊断证据；未修改 tracked 实现、正式模板、QA 台账、BASELINE/HANDOFF、受保护资产或原用户 Workbook；未提交、未推送、未合并。
