# Qt 家族界面统一执行说明（2026-10-28）

状态：实现候选，等待协调者独立验收；未创建PR、未合并、未发布，不改变Phase状态。

- 基线：`origin/master@e140283b110e77992099836fddcb34f018e01009`，已fetch并用远端HEAD核对默认分支master。原项目脏目录未修改。
- 分支：`codex/ui-family-20261028`；隔离worktree由本任务创建，路径见交付消息（路径仅表示本机环境）。
- 实施依据：本轮Owner授权及中央候选 `e1486fb20c1dda33b7344ca860ff8f303c2183ee`；候选尚未合并，不称为已发布指南。中央已合并导航/指南核查于 `a389ac1de63c4f331f3b04e5e7b7a17ef02ed111`。
- 平台预检查：locked central SHA `ee5feb0cc34dbd99790500fadd0c4c932e202a20` 未变。本任务不涉及中央公共 Contract。适用边界：Presentation经现有Application调用；展示不得改变Decimal、标准解释、算法、支持范围、历史快照、保存规则或数据库。冲突：无；无需改中央Contract。
- 标准问题：未产生新Issue，不改变既有软件解释。生命周期保留“已实施/尚未实施/未提供实施日期”，未凭实施日推断“现行”；变压器列表基于IMPLEMENTED显示“已实现，待验收”，电机仍显式“验收候选”；当前正式支持范围依V1_SCOPE。

## 本轮变更

窗口首次客户区目标1280×800、非最大化并居中，显示后按真实系统边框约束工作区；保留geometry/state恢复，屏幕工作区变化/移除/切换后收回可用区。启动首页及业务数据恢复规则不变。业务侧栏242，导航/底部设置46，图标18；首页设置保持无侧栏，返回首页可达，业务设置保留侧栏。

统一40 DIP普通输入/按钮、36 DIP页签、字体/配色/按钮状态与2px稳定焦点；修复primary禁用覆盖。QGroupBox标题放入卡片内部独立留白；统一页头与动态外边距，实际正文最多1440，无设备子页嵌套外边距。已有运行信息折叠和设置能力保留，未新增备份能力。

表格默认48 DIP、长中文动态增高并保留全文；记录的两个页签以转义后的可读段落展示原快照，字段信息不删，加载更多保留，计数和加载控制放底部。导入四区域统一名称，无文件处理禁用，忙碌/失败后依前置条件恢复。未增加确认框或改系统选择器。

首页/侧栏Logo180 DIP，从3060×759原图按当前DPR生成，SVG按目标DPR绘制；原始PNG和15图形SVG字节均未变。来源与哈希见assets/README.md。没有改冻结资源、标准模板、Contract、Golden、持久化或版本号。

## 实际验证

Python3.12.14 / PySide6 6.11.2，全部Qt检查使用offscreen与独立临时数据库，不操作真实桌面。

- 最终相关回归：125 passed，127 subtests passed，fail/error/skip=0，exit=0（141.28秒）。
- 2×DPR抽查：本轮7项定向测试通过，fail/error/skip=0（覆盖Logo实际DPR、SVG物理尺寸、输入文本、窗口/控件/长中文与批量状态）；其后新增的颜色/最大化2项在普通DPR覆盖。
- 实测最终外框：普通输入/按钮40；导航46；侧栏设置46且图标18；页签36。SVG `QIcon.pixmap(QSize(18,18),2.0)`=36×36物理像素、18×18 DIP。2000业务可用宽下实际正文1440。
- compileall与git diff --check通过，fail/error=0。未跑全量业务回归或性能基线，未改算法；未构建/验收EXE。
- 首页/标准库/新建/记录详情四个离屏代表视图已自查，offscreen测试显式加载本机中文字体，仅用于该测试进程。真实桌面外框、系统字体、跨物理DPI屏与掉屏操作由协调者验收，不以离屏图冒称通过。
- 初轮曾出现旧尺寸/设置上下文/纯文本格式断言失败，以及长中文行高实测失败；已更新已授权行为断言、验证HTML转义，并修复实际行高问题。最终结果以下方命令为准。

最终命令：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONPATH='src'
& 'G:/Python Project/EquipEffi/.venv/Scripts/python.exe' -m pytest tests/unit/test_ui_family_20261028.py tests/unit/test_ui_family_stage1.py tests/unit/test_ui_family_stage2.py tests/unit/test_ui_family_r4.py tests/unit/test_phase2_qt.py tests/unit/test_phase6_product_shell.py tests/unit/test_phase8r4_qt_background.py tests/unit/test_phase8r5_qt_batch_feedback.py -q --tb=short
```

## 协调者源码验收

提供了必须显式注入数据目录的`tools/launch_ui_review.py`，复用正式装配链。首次用全新`--data-root`验证默认窗口；关闭后复用同一目录核对恢复。`--motor-candidate`只启用现有候选开关，删去它即正常默认构建，不提升软件支持状态。

操作：确认无侧栏首页→右上设置→返回首页→标准库及三分区详情→新建分析（泵100/50/2900/90，合法分析自动记录）→分析记录及两页签→业务侧栏设置→表格导入（无文件禁用、取消选择、失败恢复）。正文滚动及主要动作可达；按需检查已实现的变压器/显式电机候选，不扩大范围。

Knowledge capture：无。

