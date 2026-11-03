# 三设备 Windows 候选包收口（2026-11-03）

Owner授权：更新状态文档，从最新主线构建并验证 Windows 包，暂不正式发布。

## 基线与边界

- 源码基线：`e596ee33546ce340b01e0bb83a76c5fd6d782c6c`（master，PR #40 已合并）。
- 工作分支：`codex/three-device-candidate-20261103`；原工作区未提交内容保持原位。
- 沿用源码版本 `0.2.2`，交付标识另附候选日期和源码短SHA；不创建正式Release或版本标签。
- 三设备：GB19762清水/石化离心泵、GB20052变压器、GB18613电动机；沿用主线SUPPORTED配置。
- 默认模板V6.3；新电机输入为额定效率和电压V，旧V6/V6.1/V6.2沿用已实现兼容语义。
- 高压及永磁仍只为设计，其他标准不开放；不改业务算法、标准解释、Golden、冻结映射、数据库迁移或用户历史。
- Phase 8保持EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE，不生成独立验收PASS。

## 平台预检查

中央锁：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`；Architecture V2.1 / Numeric v1 FROZEN保持不变。已按当前GUIDE_INDEX读取产品交付规则。本任务不涉及中央公共Contract语义变更，不需要升级锁或修改中央Contract；冲突分类N/A。既有数值及Excel契约通过现有全量测试回归验证。

界面验证按当前中央产品家族规格v0.1、UI指南v0.2及验收清单v0.1选取首页、三设备分析、表格导入、记录详情进行实际操作与截图核对；这些ACTIVE文件不是Frozen升级，不授权UI重构。本轮不修改UI生产实现。

相关Standard Issue：EQP-STD-MOTOR-009（额定效率/V输入）、既有泵与变压器解释；本轮不改变既有软件解释。必须保持Excel调用同一内核、输出另存、历史快照不重算。Knowledge capture：无。

## 验证

原始日志存放在本工作树 `artifacts/candidate-20261103/`。本轮只更新文档及截图验证工具，不修改 `src/`、模板、Golden、锁或依赖版本；原生包仍对应上述主线源码。

| 检查 | 结果与证据 |
|---|---|
| 编译检查 | `compileall -q src tools tests`通过，exit0 |
| 固定主线远端CI | [Windows Core 40886169616](https://github.com/adgo07/EquipEffi/actions/runs/40886169616) success；对应e596ee33，不冒充本轮文档分支CI |
| 本机完整测试 | 1255项，2203.374秒：pass1251 / fail0 / error4 / skip0 / not_run0，原始exit1；4项全部为BuildInProgressError，后续11项串行复验exit0。保留首次完整结果，不改写为一次全绿；`full-suite.log` |
| 构建锁复验 | 构建与全量测试并行导致4个校对工具测试遇到互斥锁；构建结束后串行复验两个模块，11项通过、失败0/错误0/跳过0，exit0，`lock-recheck.log` |
| 原生构建 | Python 3.12.14 x64、PySide6 6.11.2、PyInstaller 6.22.3；Windows 10 build19045；exit0，`native-build.json`/`build.log` |
| 包审计 | `audit_release.py --native-report ...`通过，错误0；保留1条非阻断警告“标准来源追溯尚未覆盖全部记录：motor_lv”；`audit.json` |
| ZIP及解压资源 | ZIP CRC及资源审计通过；解压EXE哈希与构建一致；PE Subsystem=2，无控制台原生程序 |
| 解压EXE状态 | exit0，ready=true；泵两Profile、变压器、电动机均SUPPORTED，电机enabled=true，V6.3 available=true；`unpacked-status-python.json` |
| 候选启动器 | 中文解压路径实际运行`启动候选版.cmd`，主窗口创建、启动器exit0，候选独立数据目录正常。首轮捕获管道等待GUI后代而超时，改用DEVNULL后成功；`launcher-check.json`、`launcher-window-r2.json`。此前PowerShell Start-Process探测未返回而取消，后续Python原生状态探测exit0；不丢弃失败记录 |
| Qt源码完整操作 | 修正工具样例后offscreen和windows平台各一次通过、exit0；1.25应用缩放；三设备单台自动记录、混合批量、历史/详情、错误输入和取消操作等；`ui-captures-r2/operations.json`、`ui-windows-captures/operations.json` |
| 混合批量事实 | 3行/9台，变压器1级3台、电机3级4台、泵不在范围2台；输入错误/执行失败0行；输入哈希不变、输出另存；单台3条记录不增加、批次仅新增1条 |
| 图像核对 | windows平台首页、电机额定效率/380 V结果页、批量结果页中文正常；offscreen图片缺少字体，仅作为流程证据，不作为中文视觉通过依据 |
| 实际EXE界面交互 | 已启动并发现主窗口，Computer Use首次`FrameArrived timed out`，刷新激活后仍`window capture timed out`；未取得EXE截图/点击验收，不冒充通过。专用探测进程随后结束，不作为正常关闭证据 |

验证工具缺陷QA-CAND-001：V6.3电机批量截图样例误用0.38（旧kV），修正为380 V，并新增结果Workbook电机Q4必须为3级的断言。原生产输入回归已使用380 V；修正不进入原生运行代码。首次截图流程虽返回exit0，但未验证正确样例，最终以修正后的R2/windows证据为准。

万行性能（源码泵批量，启用tracemalloc，非EXE整机峰值）：100行5.096秒/24.6 MB；1000行33.910秒/110.3 MB；10000行275.609秒/1000.7 MB，均未丢行，输入/执行错误为0。此为本机实测，不与不同环境直接归因比较，不开展性能重构。

## 候选交付

- 文件：`EquipEffi-0.2.2-candidate-20261103-e596ee33-windows-x64.zip`，49,543,858字节。
- ZIP SHA256：`08bc5101efb5386e9b53b4eb3b8a5f0b2cae166d26a652359020df3879df16b7`。
- EXE SHA256：`c6fb1d837055d6a12ae170e51c3e70ebdbfe5a5f904c03da773366bb7edb2b6e`。
- 完整解压后运行`启动候选版.cmd`，独立数据位于包目录`candidate-data/EquipEffi`；不要直接运行EXE使用默认正式数据目录。
- 随包候选使用说明与Qt/PySide6/shiboken许可；不含用户数据、标准原始PDF或扫描件。
- 未创建Release、版本标签、安装器、签名或自动更新；正式发布仍为v0.2.1。

另一台干净Windows、真实125%系统缩放尚未取得证据。应用级缩放或本机隔离测试不替代这两项。
