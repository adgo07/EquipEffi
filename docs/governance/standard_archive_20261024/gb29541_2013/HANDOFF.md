# GB 29541—2013 Stage A交接

> 2026-10-23更新：已答问题的当前项目口径见[主映射](../../../standards/gb29541_2013/STANDARD_MAPPING.md)“Owner回复落实”章节；本文件原2026-10-13请求/交接为历史记录，其“待批准”不代表今日状态。当前问题状态仅查[根台账](../../../../STANDARD_ISSUES_REGISTER.md)。源值工作簿未改，解释覆盖须与主映射配套使用。

2026-10-13；本会话仅写`docs/standards/gb29541_2013/`。开工HEAD `2c7807f32ef08d18554014328efd4ceaa356726f`，分支`codex/six-standard-mappings`，origin核实且fetch成功；未stage、commit、push、切分支或建worktree。

收尾只读复核时共享HEAD已由总协调推进到`d9f711068bde583138a7f3dded6f64dcaa339761`（六标准会话与协调分工文档），origin/master仍为开工基线。属于并行协作预期，本会话没有修改Git状态。最终本目录8个Markdown文件的本地链接检查无断链；临时node_modules junction已移除，重新运行作者脚本须按Spreadsheets技能重建依赖连接。

已完成资料：README唯一入口、完整主映射、表1全部9源行45限值和11条款数字的工作簿、源页及合并结构证据、56项逐格核验CSV、机器检查摘要、22组边界候选、CHANGELOG。本会话表值自核验完成；不是独立验收，未宣布Stage A出口全部通过或READY_FOR_IMPLEMENTATION。

**原四项请求待总协调登记，本轮另补本地请求005**，详细事实、技术判断、建议实现、影响及候选均见`ISSUE_REGISTRATION_REQUEST.md`。以下是本地请求序号，不是正式Issue编号：

1. 本地请求001：静态加热恰好10 kW路由缺口。
2. 本地请求002：低温型静态加热无明确阈值分支。
3. 本地请求003：COP保留两位小数的修约方法未明确。
4. 本地请求004：两份2008版引用测试标准未取得核验，工况/术语/测定依赖尚缺。
5. 本地请求005：额定/实测制热量选组及4.3范围核查。

上述均保持需确认，不替Owner决定。根台账未登记前不形成已批准解释；可先审阅无依赖的完整原表值。本任务不涉及中央公共 Contract；锁不变，不改范围/支持状态，不改生产或批准Golden。

原PDF SHA `94d5f6cc5502e76da01fc030a00d2acd54f40dd83cb967886149fb6b158e15df`；工作簿SHA `a7f92d9ab87aa90d44d80d72754d3ee1ce63266276d5ed06cdded9f4380e4b54`。总协调负责根索引、BASELINE、HANDOFF/TASK_STATE及提交。

初次交付资料自动检查pass=7/fail=0/error=0/skip=0；56数值格全部一致；两Sheet视觉通过。初次交付not_run：引用原文复核、独立验收、Excel桌面原生打开、生产测试/编译/smoke/性能（本次无生产改动）。新增独立证据见下节，初次自核记录不冒充独立验收。

`tmp/`包含本地PDF整页渲染、Workbook预览及中间数据，不随库交付；不要上传原PDF或整页渲染作为新源文件。作者/核验脚本已移到`evidence/`。`data/*.inspect.ndjson`是自动输出中间检查文件，本地.gitignore已排除。Knowledge capture：无。

## 第一轮验收反馈处理（2026-10-13补充）

第一轮独立验收认定整理稿有条件通过；表1全部45个等级限值独立一致。已核对45个唯一坐标F6:J14及工作簿快照SHA，数值未变。此结论不包含11条款数字全部验收、显示精度全验、外部试验依赖或全部Stage A出口。详细回应见[evidence/ACCEPTANCE_RESPONSE.md](evidence/ACCEPTANCE_RESPONSE.md)。

原四项请求仍未查到根台账登记，不预设正式编号或状态。另依据专项复核R-06/R-07合并补本地请求005；相关主映射/B-11改为需确认候选，不是已批准解释。

已补本地.gitignore，复现脚本落evidence；同作者自核方法表述已澄清，原验收/复核报告未改。根台账、总索引、BASELINE及共享文件仍交总协调维护。本轮未提交、未重存工作簿、未提升产品状态或冻结。
