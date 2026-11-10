# UI局部收口（2026-11-10）

基线为 `origin/master@b1d04a3`，中央当前指南读取 `origin/main@829853a943c421e0b9864d84f3d94970d2ddf688` 的 GUIDE_INDEX、产品家族规格、UI指南v0.2、验收清单和正式资产说明；不修改platform-lock。

首页、标准库及分析表单删除复述文字，三设备分析按钮附近直接说明自动生成记录与再次分析新增记录，查看记录使用次动作。电机标准详情按已批准额定效率、V和1～100口径展示，历史记录仍读原快照。记录列表直接区分无记录、筛选无结果和读取失败，加载更多失败保留已载记录及重试位置。设置按应用信息、数据位置、高级运行信息分组；补充说明使用可点击及键盘开关的就近气泡，Esc关闭并返回入口焦点。

保留现有窗口、品牌、侧栏、控件、48行高和长中文动态增高；五列标准、三分区详情、两页签记录和四区导入保持原结构。没有算法、映射、Golden、模板、schema、migration、支持范围、历史数据或lock改动。

定向离屏测试使用独立临时目录，覆盖空态动作、筛选恢复、读取失败与重试、单台分页偏移、批次加载上限、说明气泡键盘操作，以及既有业务快照/数值输入/批量反馈回归。原生界面及打包结果由独立验收另记；本记录不宣称发布或阶段通过。

## 独立复核

主会话逐项审查 `3069390` 相对 `b1d04a3` 的差异，改动限Presentation、对应测试及说明；受保护业务文件无差异。最终11个相关模块独立执行：145 passed、157 subtests passed，61.07秒，exit0。覆盖新增空态/气泡、既有家族布局、三设备Qt、单台与批次历史、批量失败反馈。此前101项/113子测试为中途结果，不累计为最终测试数。

命令：`python -m pytest tests/unit/test_ui_local_polish.py tests/unit/test_ui_family_20261028.py tests/unit/test_ui_family_r4.py tests/unit/test_ui_family_stage1.py tests/unit/test_ui_family_stage2.py tests/unit/test_phase3_qt_unified.py tests/unit/test_phase7_analysis_history.py tests/unit/test_batch_records_history.py tests/unit/test_motor_qt.py tests/unit/test_transformer_qt.py tests/unit/test_phase8r5_qt_batch_feedback.py -q --tb=short -p no:cacheprovider`。使用独立TEMP及`QT_QPA_PLATFORM=offscreen`，未操作用户数据库。

主会话检查6个离屏视图：首页、记录空态、标准详情、设置、说明气泡、960×600记录页。中文与主要操作可读，无新增裁切；这是离屏源码证据，不是原生桌面或DPI验收。代表图见本目录 `local-polish-20261110/`。

原生候选使用Python 3.12.14、PySide6 6.12.0、PyInstaller 6.22.3构建，源代码为 `3069390`；构建及最终目录自检exit0、ready=true，资源审计通过。EXE SHA256：`1a9d814ff112043075f009b9caa4bc27e6cb164e2111dff4cbc43c6f545670ca`。候选独立启动器隔离PATH与test-data，旧包和用户数据未覆盖。保留已有非阻断警告“标准来源追溯尚未覆盖全部记录：motor_lv”。首次审计控制台GBK输出失败，以UTF-8重跑成功，不改审计逻辑。

原生交互仍OPEN：GPT-6-astra medium尝试启动专属窗口，窗口枚举成功，但首次读取窗口未返回，被中断，未取得原生点击或截图证据。离屏图与包自检不能替代该项。真实125%缩放、跨物理屏幕、另一台干净Windows亦未验证。PR以草稿交付，补齐实际窗口验收后再决定是否可合并；本轮不合并、不发布、不提升支持状态。

本机独立证据位于仓库父目录 `UI_review_20261110`：`final-independent.log`、`native-build.json`、`native-audit.json`、`candidate-status.json`及`offscreen-review`；路径仅用于本机定位。候选目录为同级 `EquipEffi_UI候选版_20261110`，运行“开始测试.cmd”。

本地验证：首轮4模块33项通过；最终9模块组合96项中唯一失败为首页旧文案断言（“尚无”改为“暂无”），修正后该模块与新增回归共19项通过，新增7项独立运行也通过；git diff --check通过。失败场景测试主动记录异常日志，未触碰真实用户数据。
