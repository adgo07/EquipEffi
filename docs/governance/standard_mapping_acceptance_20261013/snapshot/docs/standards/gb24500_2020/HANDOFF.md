# GB 24500—2020 Stage A交接

2026-10-13；本会话仅写`docs/standards/gb24500_2020/`，没有stage/commit/push、切换分支或创建worktree。共享分支产生的其他改动未清理。

- 当前交付入口：[README](README.md)。主映射与4表工作簿配套，覆盖6章、4表、脚注、高低位效率、低热值生物质、有机热载体和电加热限定值。
- 原PDF SHA=`e270072e4d3cdefc9a9969524870a50bd454c5405a729c993b2e2584551cf285`，6页；封面已核对，原文件未改动/上传。
- 结构：4表，57展开等级行；数值：78/78效率值逐格与PDF坐标匹配，另核对5.2的97%；5个Sheet均渲染检查。最新XLSX SHA及统计见[校验摘要](evidence/verification_summary.json)。没有独立验收。
- **协调待办**：[登记请求](ISSUE_REGISTRATION_REQUEST.md)含A特殊限定值与等级组合、B排放前提证据口径。请分配`EQP-STD-GB24500-`稳定编号并写根台账。对应软件解释未批准；可继续审阅无依赖事实，但不可宣布Stage A全部出口条件通过/正式支持。
- [25组边界候选](BOUNDARY_CANDIDATES.md)不是Approved Golden。没有改Calculator/生产JSON/数据库/Golden/UI或范围/支持状态。
- 总协调独占维护根台账、总索引、BASELINE、根HANDOFF、TASK_STATE；本目录哈希以校验摘要为准供汇总。
- `tmp/`含原文提取、原页PNG、工作簿预览、builder/verify脚本、运行期node_modules junction。本目录`.gitignore`排除原页/提取/依赖junction及`data/*.inspect.ndjson`，仅允许builder、verify和expected_cells复现材料进入Git；没有提交原PDF。重建工作簿前按Spreadsheets技能重新建立本目录tmp/node_modules指向运行期依赖的junction。
- Knowledge capture：无单独条目。剩余边界：引用试验标准全文与原生Excel桌面未核验；最终软件状态设计和Owner解释留后续。
