# GB 29541—2013 标准档案

本目录为2026-10-13建立的Stage A标准整理资料。当前唯一主映射及配套表值如下；未独立验收、未冻结，不代表软件正式支持或Phase推进。

- [主映射](STANDARD_MAPPING.md)：适用范围、字段、9源行路由、等级/限定值/节能值、标注核查及试验依赖。
- [标准表值工作簿](data/GB29541_2013_标准表值.xlsx)：完整表1（9行×5等级，共45个值）及11个条款数字、相关条件。工作簿无业务算法。
- [原文及官方元数据定位](evidence/SOURCE_REGISTER.md)、[结构与数值核验](evidence/VERIFICATION.md)、[逐格复核CSV](evidence/cell_verification.csv)、[机器核验摘要](evidence/verification_results.json)。
- [边界候选](evidence/BOUNDARY_CANDIDATES.md)：22组候选，含全表135个阈值邻域取点说明；非Approved Golden，未运行生产测试。
- [问题登记请求](ISSUE_REGISTRATION_REQUEST.md)：供总协调入[根问题台账](../../../STANDARD_ISSUES_REGISTER.md)；本目录不是第二状态台账。
- [交接](HANDOFF.md)、[修订记录](CHANGELOG.md)。

原文是用户提供的仓库相对文件 `标准原文/14. GB 29541 2013 热泵热水机（器）能效限定值及能效等级.pdf`，未复制到本目录、未上传、未覆盖。封面核实GB 29541—2013《热泵热水机（器）能效限定值及能效等级》，共5个PDF物理页。

PDF SHA256：`94d5f6cc5502e76da01fc030a00d2acd54f40dd83cb967886149fb6b158e15df`。

当前工作簿SHA256：`a7f92d9ab87aa90d44d80d72754d3ee1ce63266276d5ed06cdded9f4380e4b54`。本次表值为原文转录，已有执行者逐格自核验；没有独立验收结论。

范围/支持状态仅以[V1_SCOPE](../../../V1_SCOPE.md)、[ROADMAP](../../../ROADMAP.md)为准。当前尚需处理静态加热10 kW边界、低温静态、COP修约与引用测试标准证据。`tmp/`是本地渲染/作者脚本工作区，由总协调提交前分类，不作为原文替代源。
