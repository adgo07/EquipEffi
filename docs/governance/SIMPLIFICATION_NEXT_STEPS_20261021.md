# 软件简化下一步方案（2026-10-21）

状态：方案已落档；本次完成 PR #24 合并与文档提交，不自动启动下一批代码实施。沿用首批任务书及 Owner 已确认的产品边界，不新增审批流程。

## 1 当前基线与平台预检查

- 仓库：adgo07/EquipEffi，默认分支 master。PR #24 已于 2026-10-21 按 Owner 指令合并，合并 SHA `0d4eae855e16c99d0ef96bda3b39bfc5b26b4641`；验收 Head `017362f8adb6e1314b8e160b8656f5621e61cd92`。
- 首批已完成共享结果投影、标准/计算器身份、Excel 模板契约和兼容校验、批次来源记录、运行资源与原文排除。详细事实见[验收记录](SIMPLIFICATION_ACCEPTANCE_20261019.md)。
- 最终 PR CI：Windows 1,580 run / 1,564 pass / 9 fail / 4 error / 3 skip，exact-ID 无新增回归；Pump Conformance 196/196、架构/元数据 113/113。已有基线问题继续保留，不称全量全通过。
- 中央 locked SHA `ee5feb0cc34dbd99790500fadd0c4c932e202a20`，Architecture V2.1 / Numeric v1 FROZEN；ACTIVE 指南依已核验中央 `c5fc6d438c9200060649e47c016b9b48218de72c` 的 GUIDE_INDEX 路由。开工时重新核对中央当前已合并指南，不自动升级 Frozen。
- 本次仅提交计划与状态，不涉及中央公共 Contract 变更。下一批继续遵守 Domain 不依赖 UI/Excel/SQLite、Presentation 经 Application、Excel 无第二套算法、Numeric 全值比较、历史快照不可变、系统错误不伪装业务终态等 MUST/MUST NOT。
- 现存问题按 LOCAL DEFECT 或已登记 REGISTERED_DEVIATION 处理；Pump Decimal50 是 ALLOWED PROJECT DIFFERENCE。若发现 CENTRAL CONTRACT GAP，先带证据返回中央，不私造公共协议。
- Standard Issue：本计划不新增或改变标准解释；既有台账仍是唯一权威。新问题先登记，影响正式结论时再按仓规处理。

## 2 推荐顺序与每批交付

### 第二批：小范围统一 Application 入口（优先）

目标：减少单台/批量入口之间的重复路由、参数组装和结果处理，仍以已经验证的离心泵链为唯一业务实现。

1. 先盘点 Qt 单台、Excel 批次和 compatibility 入口实际调用关系。以现有 service、路由元数据与结果契约为起点，只列有证据的重复和差异；明确哪些本来就不同（单台自动 Record、批次仅一条 batch_record）。
2. 选择一条可独立验收的公共调用路径，提取最少的应用层协调职责。标准身份、Profile 与支持状态显式传递；不靠设备名称子串猜路由，不将标准元数据重复写入页面/Excel常量。
3. Qt 与 Excel 接线到同一既有业务链；核心 Calculator、Numeric Profile、Canonical 与 Golden 保持。只复用真正公共的部分，保留单台/批次各自持久化策略。
4. 在同一批移除已经替代的重复实现，必要兼容入口保留薄转接与回归；不先搭通用插件系统、通用审计框架或新数据库。

交付：一张调用关系/重复点对照表、最小代码改动、相关回归与一份简短执行摘要。没有证据表明需要新增抽象时，可仅收拢重复调用，不以建框架作为完成指标。

### 第三批：字段定义与页面共用部分

以第二批稳定接口为前提，收拢已有输入字段、单位、必填提示和结果展示的重复定义。优先复用现有元数据及投影，不另造一套业务 Schema。只整理真实重复的组件，保持五个正式 Qt 页面与用户流程；不借机重做导航或预建未支持设备页面。UI 任务执行前按中央当前 UI 指南及对应验收清单检查。

### 第四批：旧路径退出与维护收口

按 KEEP / VERIFY / MIGRATE / REWORK / DEPRECATE / DELETE_CANDIDATE / OBSOLETE 逐项分类；只有替代路径接通、有兼容证据的旧逻辑才退出。零引用不是删除理由；JSON/Web/Tk/Android/V4 现存兼容表面按登记差异处置。源工作区个人资料、用户工作簿、标准原件不混入清理提交。

将当前 9 fail / 4 error / 3 skip 按精确 ID、环境/夹具/真实功能原因归入 QA_BACKLOG，优先修复会妨碍正式泵链或交付验收的项。已修复项有重复证据后才能收紧基线；不得扩大允许名单、删除测试或改 Golden 制造绿灯。不要求普通重构前一次清零所有历史问题。

### 后续：第二标准与正式交付

变压器以冻结 V2.1 主映射和35表工作簿为成套依据，先完成 Stage B 接入设计与待决条件清单；当前仍 POST_V1 / NOT_IN_RELEASE_SCOPE，不在第二批实现，不改冻结双文件。进入实现或调整支持范围时沿用现有 Owner 决策边界，Stage D 独立验收后才可提升 SUPPORTED。

正式发布前另做原生 Windows 构建及离线实机验收：验证实际 EXE 启动、数据/模板资源、批量输入输出、原文排除与用户数据路径。当前 PyInstaller 原生构建仍 NOT_RUN。Word 功能在应用接口稳定后再明确真实报告需求，不为占位能力造接口。

## 3 Excel 版本管理贯穿所有批次

- 工作簿修订、各设备 Sheet 契约、实际标准/数据/计算器版本分开；模板识别来源单独记录，不拿模板身份冒充业务版本。
- 全设备统一 Workbook；清水/化工泵共用离心泵 Sheet。原始基线不覆盖，结构真正改变才生成新修订，给旧版明确兼容或迁移路径。
- 新设备逐项接通；每次同时验证新增设备及全部已支持 Sheet，未处理 Sheet 内容和顺序不漂移。仅有 Sheet 不等于软件已支持。
- 输出始终另存；不固定 Table 行数、不要求用户逐 Sheet 扩容。读写/容量路径修改才重跑少量、100、1,000、10,000 行场景；纯文档不重复压力测试。

## 4 执行分工与验收

继续由主会话设计和独立验收，原 C/X/P 子会话使用 gpt-6-luna / max 执行。第二批先由 C 线给出最小接口及重复点说明；X 可并行准备 Excel 契约/兼容回归，接口稳定后接线；P 可并行盘点已登记测试与交付问题。各线不共同写同一文件，共享治理文档由主会话收口。当前只提交本方案，不在此轮下发实现任务。

每批一个明确范围、固定 Head、一个 PR；执行方只提交准确差异和实测证据，不自行宣布通过。主会话验收至少核对：

- 已批准29条 Golden、边界、Decimal50与全值比较不漂移；输入错误/执行失败/业务终态不混淆。
- 单台每次合法分析独立保存，批次不造逐行单台记录；历史恢复不重算、不改写。
- Qt/Excel 同输入核心结果一致，模板兼容/单位拒绝/输出限值/来源证据正确；未处理 Sheet 不变。
- 受保护资产和中央锁不变；依赖边界通过；测试按真实 pass/fail/error/skip/not_run 记录，exact-ID 无新增回归。
- 一旦改动标准解释、Approved Golden、Scope、Frozen、破坏性迁移、正式发布或 SUPPORTED 提升，遵守已有明确决策边界；普通重构与 Bug 修复无需反复审批。

Phase 8 仍为 EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE；本方案及 PR #24 合并都不构成 PHASE_8_PASS，不进入 Phase 9。Knowledge capture：无新增专业知识条目。
