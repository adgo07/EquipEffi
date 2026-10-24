# 设备类已确认问题修复交接单

## 最新范围纠正（用户确认，优先于历史交接）

正式范围仅15个新编标准版本、128表。泵和变压器此前已确认，维持原确认状态；下文B、D保留为历史额外查漏记录，**撤销其本轮必修/复验身份，不阻断15项验收，不重开原验收**。停止修改既有定稿，已产生的新版本候选/备份仅保留候选，不替换原确认资产。继续A（GB/T36561四项）及C（48项既有请求登记）；后续复验不再包含泵/变压器。


范围日：北京时间2026-10-13。当前只收已确认事实，不把未核实推断混入。供父会话新建的Sol/medium修复任务使用；修复后必须交Astra/medium按新SHA复验。未全部通过，不合并、不发布、不改业务代码。验收组不另建修复会话，也不再重复发送原会话。

仓库：`G:\Python Project\EquipEffi`；origin=`https://github.com/adgo07/EquipEffi.git`；共享分支`codex/six-standard-mappings`；HEAD=`d9f711068bde583138a7f3dded6f64dcaa339761`。原文/映射/XLSX的修复前SHA和绝对路径见`preflight_inventory.json`及各组manifest。52个主要输入在22:17:31复算全未变化。提交SHA不含大部分新编文件，因此不得仅按HEAD复验。

## A. GB/T36561—2018：四项确定转录/事实层缺陷

专属修改范围：`G:\Python Project\EquipEffi\docs\standards\gbt36561_2018\`；原编制会话`01a13342-438a-7001-820e-ff5f2fbfc969`。原会话发送及状态路由失败回执见`REPAIR_DISPATCH_RECEIPT.md`，未确认送达，不得据此宣称已修。

完整问题证据绝对路径：`G:\Python Project\EquipEffi\docs\governance\device_full_acceptance_20261013\fans_submersible\gbt36561_2018\CONFIRMED_FINDINGS.md`；修复前受影响文件SHA见同目录`defect_input_hashes.json`。原PDF SHA256=`f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37`。

|ID|原文事实|当前错误|修复范围|
|---|---|---|---|
|FS-36561-01|PDF物理8/印5，表6注a：距主轴端面300 mm|正文表值!H90写500 mm，记录T6-0089|回到同源构建数据修条件，同步CSV/JSON/XLSX/坐标证据，0.3阈值不改|
|FS-36561-02|同页表6注b：直径>φ300 mm|H91写≥φ300 mm，记录T6-0090|保留严格大于边界，同步派生数据，不把等号保留为软件新解释|
|FS-36561-03|PDF物理14/印11，表11井式炉950℃、0.2～1.0m³：升温时间≤1.0 h|F294写1.5，记录T11-0293|修真实阈值及所有同源产物，复验等号及相邻容量/温度行|
|FS-36561-04|PDF物理17/印14，表15两行原引用GB/T30829.4|H354:H361静默写成GB/T30839.4|恢复原文事实层；如认为原文疑误，另登记原文/技术判断/拟软件口径，不把技术纠错冒充标准明文|

不要只改Excel导致下次构建回退；独立复验将同时对照构建源、CSV、JSON、工作簿和页图。图像证据在同目录table6_note_zoom.png、table11_zoom.png、table15_reference_zoom.png。仅本地审计，不上传原标准页图。

## B. GB19762—2025：确定映射完整性和定位缺口

主范围：`G:\Python Project\EquipEffi\docs\standards\gb19762_2025\`。原编制会话尚未确认，勿猜接收者。完整证据：`G:\Python Project\EquipEffi\docs\governance\device_full_acceptance_20261013\pump\PUMP_ACCEPTANCE.md`。

- PUMP-A01：§1/PDF7，补非金属泵、无轴封回转动力泵排除，化工洁净液体/闭式叶轮条件。
- PUMP-A02：§3.1注/PDF7，补全(最大)叶轮直径、设计基型转速规定点前提；不要新增未经决定的用户门禁。
- PUMP-A03：§7/PDF11，补GB/T3216中2级试验要求及相关引用定位。
- PUMP-A04：附录A.2/PDF12，条件2950与代入2960的原文矛盾应登记并区分事实/判断；不改原PDF、正式公式或Approved Golden。
- PUMP-A05：补表1/2印2物理8、表3印3—4物理9—10的双页码映射；涉及Canonical source_pages的旧定位可在文档解释，不借此修改运行时Canonical或业务代码。

数值/公式262项本轮无差异。修复应补文档事实及台账，不能以此扩大到既有支持状态、产品字段、业务门禁、算法或Golden调整。

## C. 已确认疑点登记出口缺口

共同事实：以下各标准专属目录已存在ISSUE_REGISTRATION_REQUEST.md，但验收时根`STANDARD_ISSUES_REGISTER.md`未见对应稳定条目。**登记本身不要求解释全部关闭**。由父会话指定的唯一公共文件负责人修改根台账及必要回链，避免并行覆盖；各专属目录仅同步本标准请求映射，不替Owner批准解释。

|标准|本地请求|证据报告|
|---|---|---|
|GB18613—2020|R01—R04（4）|motors/GB18613_2020_ACCEPTANCE.md|
|GB30254—2024|2项请求|motors/GB30254_2024_ACCEPTANCE.md|
|GB30253—2024|R1—R3（3）|motors/GB30253_2024_ACCEPTANCE.md|
|GB19153—2019|R01—R04（4）|compressor_boiler/ACCEPTANCE_REPORT.md|
|GB24500—2020|A/B（2）|compressor_boiler/ACCEPTANCE_REPORT.md|
|GB29541—2013|001—005（5）|hvac/ACCEPTANCE_REPORT.md|
|GB19576—2019|R01/R02（2）|hvac/ACCEPTANCE_REPORT.md|
|GB37479—2019|A/B/C（3）|hvac/ACCEPTANCE_REPORT.md|
|GB21454—2021|R1—R4（4）|hvac/ACCEPTANCE_REPORT.md|
|GB19761—2020|3项既有请求|fans_submersible/ACCEPTANCE_REPORT.md|
|GB28381—2012|6项既有请求|fans_submersible/ACCEPTANCE_REPORT.md|
|GB/T36561—2018|10项既有请求；加本次明确转录缺陷的联动记录|fans_submersible/ACCEPTANCE_REPORT.md及CONFIRMED_FINDINGS.md|

根台账当前已有GB28381—2026的001—006、GB19577—2024的001—006、GB32030—2022的001，不能覆盖/复用这些编号。2012/2026鼓风机必须按版本区分。共有48项既有请求待登记（不是48项数值错误）；写入前再次核对根台账以防父会话已处理。

## D. 冻结变压器：仅列待批准修订候选

证据绝对路径：`G:\Python Project\EquipEffi\docs\governance\device_full_acceptance_20261013\transformer\ACCEPTANCE_REPORT.md`；逐表缺口：同目录`technical_parameter_coverage.csv`。

TR-F01：24表辅助阻抗数值/分段未完整进入冻结二件套。确定例：表3（PDF9）3150—6300kVA为7%、8000—20000为8%、25000—31500为10%；表4为7/7.5/8/10%四段；XLSX表03/04的P4:P14空，MD仅概述随容量变化。全部4712项损耗/单位检查通过，不能把辅助覆盖缺口误写为损耗错误。

该候选只补标准原文转录遗漏，不拟改Owner已批准的插值、±10%阻抗选组、多组同阈值可判、表外状态或D-06温度换算DEFERRED。**当前没有对具体冻结文件变更的Owner批准记录，不直接改/重存V2.1。** 先形成具体新版本修订方案和原文证据，按父会话/Owner批准边界执行；旧版SHA必须保留。TR-N01旧段落由后记批准决定覆盖，只作未来可读性提示，不重新要求Owner决定同一口径。

## 修复交还验收的最低材料

实际变更文件列表、每份旧/新SHA、原页/真实单元格与前后值、影响和未改范围、同步的构建/CSV/JSON/XLSX证据。只报告执行完成，不自称独立验收通过。Astra按新SHA定向复验并检查同源及相邻边界，最终汇总仍由父会话分别归入设备/能耗两类。
