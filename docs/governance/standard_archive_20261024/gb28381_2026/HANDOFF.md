# GB 28381—2026 专属交接

2026-10-13。Stage A材料已建立，等待总协调统一审阅/提交及后续独立复核；未stage、commit、push，未切换分支/worktree。仅写`docs/standards/gb28381_2026/`。

入口[README](README.md)，主成果[STANDARD_MAPPING](../../../standards/gb28381_2026/STANDARD_MAPPING.md)+[六表工作簿](../../../standards/gb28381_2026/GB28381_2026_TABLE_VALUES.xlsx)；源证据、逐格CSV、转录JSON、34格图像抽核、检查计数、30条边界候选及复现脚本均在本目录。

- 源PDF SHA-256：`64a8ef7934933eff49874c5f121db5a1f32f69ff1a16295cd1abe4d740b80d35`，27物理页，印刷正文1~20。官方元数据确认2026-03-31发布、2027-04-01实施、全部代替2012版；本地PDF上游取得链和官方逐字节一致性未证明。
- 六表343数据行、173分表流量点、2970限值位置=2847数值+123“—”；双路径token 2970一致；XLSX全部真实坐标回读一致；图像抽核34格一致；附录2例有理数复算等级一致。详见VERIFICATION及CHECK_RESULTS。
- 问题R2026-01～06已由总协调登记为`EQP-STD-GB28381-001`～`006`，仅2026版。状态权威在根台账；登记不批准公式修正、偏差方向、缺端点插值或舍入策略。映射未改变现有解释。
- 独立逐格验收、原生Excel打开、生产测试未执行；其余2816数值未逐格人工图像复核。双提取同源、执行者自核不能替代独立验收。
- 稳定文件哈希见`DELIVERY_SHA256.json`；总协调据此维护公共BASELINE/HANDOFF/索引。原PDF、全页渲染、提取全文及依赖junction不提交。
- 支持状态/范围不变，未建Canonical/Calculator/数据库/UI，不冻结，不宣布SUPPORTED/Phase PASS，不进入Phase 9。Knowledge capture：无。

后续工作：总协调核对入口和哈希，保留2012/2026版本独立；安排专业复核及六项解释决定。原文事实、技术判断、候选实现已分开，不以待确认建议代替Owner批准。
