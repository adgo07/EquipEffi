# GB 30254—2024 Stage A 交接

2026-10-13。范围仅本目录。交付入口：[README](README.md)。

已交付：主映射；六表完整静态工作簿；原文来源及SHA；结构与数值核验记录；3582条逐格机械核验CSV；可复现提取/工作簿创建/只读核验脚本；30个边界候选；两项问题登记请求。

- 6表，共204功率行、3093个效率数值、285个原表破折号。
- 3582格保存XLSX值/显示精度比较无差异；第二PDF解析器204行原字形序列匹配。全部表页结构视觉检查、25行字形锚点及数字抽查已做。**未完成独立纯图像/第二人员的全量数值复核，未独立验收、未冻结。**
- 原PDF封面确认为2024版，SHA `53a6d2e8098fea9f81adf6a12fe3298707bf6b22cc8c972110aacdcd8a168135`。工作簿SHA `b3755111a4f20a7f4cf1a6e37e48a4e17d4e0dcb8cea2ab88211fc67cf822912`。未覆盖或上传原件。

## 总协调待办

1. 将 [ISSUE_REGISTRATION_REQUEST](ISSUE_REGISTRATION_REQUEST.md) 两项登记根台账，前缀 `EQP-STD-GB30254-`：GB/T755容差判定语义；总范围与极数表值覆盖差异。本文不分配正式ID、不建立状态台账。对应解释仍需确认，禁止自行阈值下调、补0或跨分支外推。
2. 根标准索引、BASELINE、HANDOFF、TASK_STATE等由总协调维护；本会话均未修改。Stage A整理材料已备，是否通过出口由协调核查疑点登记及审核情况，不以本交付自动宣布READY_FOR_IMPLEMENTATION。
3. 若需独立全量数值验收，以原PDF图像重新转录/逐格复核，不能把两个文字层解析器一致当成独立图像真值。

## 环境与文件分类

开工HEAD为 `2c7807f32ef08d18554014328efd4ceaa356726f`，origin验证一致，fetch已完成，默认分支master；本地master落后origin/master 46提交。共享分支一直为 `codex/six-standard-mappings`。执行中只读观察到共享HEAD由总协调更新为 `d9f711068bde583138a7f3dded6f64dcaa339761`；本会话没有Git写入操作（fetch远端引用除外），没有stage、commit、push、切换分支或worktree。

建议提交本目录除被忽略 `_work/`、`node_modules/`、`__pycache__/` 之外的成套文件。`_work/`是原文提取、旋转PDF、原页图像、工作簿预览及临时检查，不应上传；`node_modules/`为指向bundled依赖的junction，不是本项目依赖变更。证据脚本保留在evidence，精确重跑说明在核验记录。

未修改Calculator/生产JSON/数据库/Golden/UI；未提升scope/support；未修改中央锁；未进入其他Phase。生产测试、compileall、smoke和性能未运行，原因是本轮仅标准整理；本目录数据检查已执行。Knowledge capture：无独立条目。
