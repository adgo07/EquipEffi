"""Legacy 桌面启动器。

**Phase 6 起本模块不再是任何用户产品入口。** Owner 决定：Tk GUI 不再使用；
无参数启动、``--gui`` 与 ``--qt`` 都进入同一正式 Windows Desktop Shell
（PySide6 Qt，见 `equipeffi.composition.launch_qt`）。

本模块与 `main_window.py` 的 Tk 窗口实现**保留但不接线**：

- 它仍被 `tests/unit/test_desktop_form_model.py` 引用（110 项表单模型/回调契约
  测试，其中既含非 Tk 的表单模型，也含 1 项 Tk 实例测试），
  因此不是"零引用可盲删"的代码；
- 按 Owner 规则"若仍有真实兼容依赖，只断开正式运行路径并登记，不得盲删"，
  本 Phase 只断开入口，并把删除/迁移登记为 `QA-P6-001`（disposition：Phase 8
  随 V4 / Excel 收口一并处置）。

**已移除**：Tk 不可用时自动切换到浏览器窗口的旧回退行为。
正式 Shell 是 Qt；任何 Tk 可用性问题都不得把用户带到 Web。
"""
from __future__ import annotations
