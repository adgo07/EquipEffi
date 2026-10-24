# GB 19761—2020 Stage A 交接

日期2026-10-13。执行者Codex。本会话仅写`docs/standards/gb19761_2020/`，保留共享分支与其他任务改动；未stage、commit、push、切分支或建worktree。

## 已交付

- [README唯一入口](README.md)、[主映射](../../../standards/gb19761_2020/STANDARD_MAPPING.md)，覆盖第1～6章、4表、7式、11规范性引用、完整适用/排除和修正分项。
- [表1～4工作簿](../../../standards/gb19761_2020/data/GB19761_2020_表1-4核对工作簿.xlsx)及生成的CSV/JSON：135个分支行，402个具体效率值；一个合并破折号源格，展开三级3个槽。
- [来源定位](evidence/SOURCE.md)、[结构与数值分别记录](evidence/VERIFICATION.md)、405项自核CSV及1350格导出比对。
- [22条边界候选](BOUNDARY_CANDIDATES.md)、[3项问题登记请求](ISSUE_REGISTRATION_REQUEST.md)。

源PDF SHA-256：`4ff8e7dd5b7adb86e33bcce49b60879e8c037f7178bb8f9091f1b5294d40f301`。
XLSX SHA-256：`2a290e6e19c19fa2e5fd729e52da9551dbc87998ca4a7e33083d292c12f1442d`。
其他交付文件哈希见`evidence/artifact_hashes.json`，请总协调用于公共BASELINE。

## 需要总协调处理

1. 根台账登记3项2020版请求：多修正并存（REQ-GB19761-2020-01）、轴流扩散筒及特殊条款优先关系（02）、5.3总句机组效率与表1～3ηr口径（03）。正式ID/状态只在根台账，本目录不私定。登记前相关解释仍需确认。
2. 公共标准索引、BASELINE、根HANDOFF/TASK_STATE等按协调规则统一维护。本目录入口与数据成套交付。
3. 独立审核原页/逐格数值及解释决定后，再判断Stage A出口；本会话不宣布其批准、不进入Stage B/C/D、不冻结或提升SUPPORTED。

## 检查与限制

源402数值+3个同源破折号槽比对405/405；导出A:J数据格1350/1350一致，fail/error均0。4张表+表2特殊末段共5个Artifact预览已查看。源8页图像均核阅。

这些是执行者自核，独立逐格复核NOT_RUN；原生Excel打开NOT_RUN；正式unittest/compileall/smoke/性能均NOT_RUN（无生产变更）。外部11项引用标准的全文及kp求值程序未核，本地PDF下载渠道未提供，官方元数据已核但未进行官方全文同一性认证。3项业务解释未获Owner批准。Knowledge capture：无。

## 环境/预检查

初始HEAD `d9f711068bde583138a7f3dded6f64dcaa339761`，分支`codex/six-standard-mappings`，origin与canonical一致。fetch初次权限失败、一次TLS失败后重试成功；origin/master=`2c7807f32ef08d18554014328efd4ceaa356726f`，当时HEAD ahead1/behind0；本地master落后origin/master 46提交，未移动它。

中央ACTIVE指南从实核main `854b544563260f9e79c73e714c85f6589e0f19b3`读取。locked SHA=`ee5feb0cc34dbd99790500fadd0c4c932e202a20`，platform-lock文件SHA-256=`b45cb389605c367f8f6bde528da4d01616a1e5151b6631f13bd1440882175d53`。本任务不涉及中央公共Contract，Frozen文件读取不适用，无锁升级、无中央冲突。

## 复现

使用Codex bundled Python运行`build_data.py`（依赖pdfplumber），使用bundled Node与`@oai/artifact-tool`运行`build_workbook.mjs`，再用bundled Python运行`verify_export.py`（openpyxl仅只读检查）。脚本均相对自身目录定位，不固化盘符。Node模块由本目录忽略的`node_modules` junction指向运行时依赖。源PDF需按SOURCE.md相对路径存在且SHA吻合。

不得把`_tmp/`页图/全文文本、`node_modules/`或`*.inspect.ndjson`加入提交。保留三个复现脚本、data文件、evidence校验记录和文档。哈希清单不包含自身，避免自引用。
