"""Excel 导入（批量输入/输出）页 — Phase 8。

产品流程（Owner Phase 8B / G08；M2 简化）
----------------------------------------
```text
输出空白模板 → 选择 Excel（自动轻检查 + 自动输出路径）→ 批量评价
             → 自动生成新结果文件 → 打开结果 / 打开所在文件夹
```

M2 起**不再要求**用户先点一次独立的「导入检查」：选择文件时自动完成同一个检查，
检查结果直接显示在界面上。检查本身仍然存在，只是自动发生（不新增填写项、
不把提醒变成确认框）。

刻意保持简单：**不**询问"泵多少行？变压器多少行？电机多少行？"，
**不**逐 Sheet 扩容——模板本身承担统一容量机制（Excel Table + 语义式 Reader）。

Excel 是**批量输入/输出载体**，不是业务计算引擎：本页把「离心泵」Sheet 逐行交给
正式 Application 评价，把结果写入一个**新的**结果工作簿，
并形成**一条**批次总结记录。
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ....application.services.pump_batch_evaluation_service import (
    PUMP_DEVICE_TYPE,
    PumpBatchEvaluationService,
)
from ..labels import user_facing_issue_kind
from ..tokens import TOKENS

SYSTEM_FAILURE_TEXT = "批量评价未能完成，请检查工作簿或联系技术人员。"


def _open_path(path: Path) -> bool:
    """用系统默认方式打开文件或目录（跨平台，不依赖 Windows-only API）。"""

    try:
        return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))))
    except Exception:  # noqa: BLE001 - 打不开不是业务失败
        logging.getLogger("equipeffi.qt.batch").exception("打开路径失败：%s", path)
        return False

class _BatchWorker(QObject):
    """在**后台线程**执行整批评价（诊断 D05）。

    大批量（实测 10,000 行可达约 9 分钟）此前在 Qt 主线程同步执行，界面在此期间
    完全无法处理事件。这里把整批评价移到工作线程，主线程只负责显示状态与结果；
    **不改动**任何计算、统计或数据库语义。
    """

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, batch, source: Path, destination):
        super().__init__()
        self._batch = batch
        self._source = source
        self._destination = destination

    def run(self) -> None:
        try:
            result = self._batch.evaluate_workbook(
                self._source, destination=self._destination)
        except Exception as error:  # noqa: BLE001 - 真实原因进日志，界面只提示
            logging.getLogger("equipeffi.qt.batch").exception("批量评价失败")
            self.failed.emit(type(error).__name__)
            return
        self.finished.emit(result)



class BatchPage(QWidget):
    """Excel 导入 / 批量评价页。"""

    #: 后台线程**真正退出**后发出；主窗口用它完成延迟关闭。
    background_idle = Signal()

    #: 记住上次使用目录的设置键。**复用既有设置键**（`SettingsService.KEYS`
    #: 已包含 `last.directory`），不新增设置 schema、不建最近文件系统。
    LAST_DIR_SETTING = "last.directory"

    def __init__(self, batch: PumpBatchEvaluationService, navigator=None,
                 settings=None):
        super().__init__()
        self.batch = batch
        self.navigator = navigator
        #: 可选的设置服务：只用于记住上次选择的目录
        self.settings = settings
        self.last_result = None
        #: 后台执行状态（None 表示空闲）
        self._thread = None
        self._worker = None
        self._build()

    # -- 构建 --------------------------------------------------------------

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
        layout.setSpacing(TOKENS.spacing)

        # 一级页面标题与导航名一致（与其余页面相同的约定）。
        title = QLabel("Excel导入")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(f"{PUMP_DEVICE_TYPE}（Excel）批量输入 / 输出")
        layout.addWidget(subtitle)

        hint = QLabel(
            "Excel 用于批量填写与批量输出，正式计算由软件完成。\n"
            "先输出一份空白模板填写，再回到这里选择文件即可直接批量评价——"
            "软件会自动检查文件并自动生成新的结果文件（不会覆盖你的输入文件）。"
            "想填多少台就填多少台，软件会自动适应，无需事先设置。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 1) 输出空白模板（一次操作，绝不逐 Sheet 询问容量）
        template_box = QGroupBox("第 1 步：输出空白模板")
        template_layout = QHBoxLayout(template_box)
        self.template_label = QLabel("输出软件内置的正式空白模板（全设备统一）。")
        self.template_label.setWordWrap(True)
        template_layout.addWidget(self.template_label, 1)
        self.template_button = QPushButton("输出空白模板")
        self.template_button.clicked.connect(self.export_blank_template)
        template_layout.addWidget(self.template_button)
        layout.addWidget(template_box)

        # 2) 选择 Excel（选中即自动轻检查 + 自动输出路径）
        picker = QGroupBox("第 2 步：选择要批量评价的 Excel")
        picker_layout = QVBoxLayout(picker)

        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("输入工作簿"))
        self.source_edit = QLineEdit()
        self.source_edit.setReadOnly(True)
        source_row.addWidget(self.source_edit, 1)
        self.source_button = QPushButton("选择…")
        self.source_button.clicked.connect(self._pick_source)
        source_row.addWidget(self.source_button)
        picker_layout.addLayout(source_row)

        # 自动检查结果（不再需要用户点一次「导入检查」）
        self.check_label = QLabel("选择 Excel 后会自动检查。")
        self.check_label.setWordWrap(True)
        picker_layout.addWidget(self.check_label)

        # 输出位置：默认自动生成，只有想改时才展开
        self.target_row_widget = QWidget()
        target_row = QHBoxLayout(self.target_row_widget)
        target_row.setContentsMargins(0, 0, 0, 0)
        target_row.addWidget(QLabel("结果保存为"))
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("留空则自动生成带时间戳的新文件，不会覆盖输入")
        target_row.addWidget(self.target_edit, 1)
        self.target_button = QPushButton("另存为…")
        self.target_button.clicked.connect(self._pick_target)
        target_row.addWidget(self.target_button)
        self.target_row_widget.setVisible(False)
        picker_layout.addWidget(self.target_row_widget)

        target_toggle_row = QHBoxLayout()
        self.target_toggle = QPushButton("更改输出位置…")
        self.target_toggle.setCheckable(True)
        self.target_toggle.toggled.connect(self._toggle_target_row)
        target_toggle_row.addWidget(self.target_toggle)
        self.target_hint = QLabel("默认自动保存为新文件（带时间戳），不会覆盖输入。")
        self.target_hint.setWordWrap(True)
        target_toggle_row.addWidget(self.target_hint, 1)
        picker_layout.addLayout(target_toggle_row)
        layout.addWidget(picker)

        # 3) 批量评价 + 完成后快捷操作
        actions = QHBoxLayout()
        self.run_button = QPushButton("批量评价")
        self.run_button.clicked.connect(self.start_run)
        actions.addWidget(self.run_button)
        # 完成后的一步操作；未完成前不可用
        self.open_result_button = QPushButton("打开结果")
        self.open_result_button.clicked.connect(self.open_result)
        self.open_result_button.setEnabled(False)
        actions.addWidget(self.open_result_button)
        self.open_folder_button = QPushButton("打开所在文件夹")
        self.open_folder_button.clicked.connect(self.open_result_folder)
        self.open_folder_button.setEnabled(False)
        actions.addWidget(self.open_folder_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        # 4) 批次总结
        result_box = QGroupBox("批次总结")
        result_layout = QVBoxLayout(result_box)
        self.summary_label = QLabel("尚未开始。")
        self.summary_label.setWordWrap(True)
        result_layout.addWidget(self.summary_label)
        self.conclusion_label = QLabel("")
        self.conclusion_label.setWordWrap(True)
        result_layout.addWidget(self.conclusion_label)
        self.issue_label = QLabel("")
        self.issue_label.setWordWrap(True)
        result_layout.addWidget(self.issue_label)
        layout.addWidget(result_box, 1)

    # -- 输出空白模板 ------------------------------------------------------

    def export_blank_template(self) -> str | None:
        """一次操作复制 package 内正式 V6 模板；**不**询问任何行数。"""

        default = Path.home() / "设备能效分析空白模板.xlsx"
        chosen, _ = QFileDialog.getSaveFileName(
            self, "输出空白模板", str(default), "Excel 工作簿 (*.xlsx)")
        if not chosen:
            return None
        try:
            target = self.batch.export_blank_template(Path(chosen))
        except Exception as error:  # noqa: BLE001 - UI 只提示，真实原因进日志
            import logging

            logging.getLogger("equipeffi.qt.batch").exception("输出空白模板失败")
            self.template_label.setText(f"输出失败：{type(error).__name__}")
            return None
        self.template_label.setText(f"已输出空白模板：{target}")
        return str(target)

    # -- 选择与检查 --------------------------------------------------------

    def _last_directory(self) -> str:
        """上次使用过的目录（复用既有 settings，不新增最近文件系统）。"""

        if self.settings is None:
            return ""
        try:
            return self.settings.get(self.LAST_DIR_SETTING) or ""
        except Exception:  # noqa: BLE001 - 设置不可用不影响主流程
            return ""

    def _remember_directory(self, path: str | Path) -> None:
        if self.settings is None:
            return
        try:
            self.settings.set(self.LAST_DIR_SETTING, str(Path(path).parent))
        except Exception:  # noqa: BLE001 - 记住偏好失败不阻塞用户操作
            logging.getLogger("equipeffi.qt.batch").exception("记住上次目录失败")

    def _pick_source(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self, "选择要批量评价的工作簿", self._last_directory(),
            "Excel 工作簿 (*.xlsx)")
        if chosen:
            self.set_source(chosen)

    def _pick_target(self) -> None:
        chosen, _ = QFileDialog.getSaveFileName(
            self, "选择结果工作簿保存位置", str(self.default_target_name()),
            "Excel 工作簿 (*.xlsx)")
        if chosen:
            self.target_edit.setText(chosen)
            self._remember_directory(chosen)

    def _toggle_target_row(self, shown: bool) -> None:
        """展开输出位置输入框；只在为空时填入建议路径（不覆盖用户已选）。"""

        self.target_row_widget.setVisible(bool(shown))
        if shown and not self.target_edit.text().strip():
            self.target_edit.setText(str(self.default_target_name()))

    def set_source(self, path: str | Path) -> None:
        """选中输入工作簿：**自动**轻检查并自动生成默认输出路径。

        M2：不再要求用户先点一次独立的「导入检查」；同一个检查在选中时自动执行，
        结果直接显示。检查只读取文件，不写任何东西、不产生批次记录。
        """

        self.source_edit.setText(str(path))
        self._remember_directory(path)
        # 输出路径**不在选中时预填**：留空即表示"自动生成"，运行时才计算。
        # 这样用户手动设置过的位置永远不会被静默覆盖。
        self._reset_quick_actions()
        self.check_import()

    def resolve_target(self) -> Path | None:
        """本次实际写入的目标路径：用户指定优先，否则自动生成。

        `None` 表示交给批量服务按默认规则命名（带时间戳，绝不覆盖输入）。
        """

        explicit = self.target_edit.text().strip()
        return Path(explicit) if explicit else None

    def default_target_name(self) -> Path:
        source = self.source_edit.text().strip()
        if not source:
            return Path("结果.xlsx")
        return Path(self.batch.writer.default_destination(Path(source)))

    def check_import(self):
        """轻检查：只读取并报告，不写任何文件、不产生批次记录。

        可以由「选择文件」自动触发，也可以由测试/调用方直接调用。
        """

        source = self.source_edit.text().strip()
        if not source:
            self.check_label.setText("请先选择要批量评价的工作簿。")
            return None
        if not Path(source).exists():
            self.check_label.setText("找不到该文件，请重新选择。")
            return None
        try:
            workbook = self.batch.reader.read(Path(source))
        except Exception as error:  # noqa: BLE001 - UI 只提示，真实原因进日志
            import logging

            logging.getLogger("equipeffi.qt.batch").exception("导入检查失败")
            self.check_label.setText(
                f"无法读取该工作簿（{type(error).__name__}）。"
                "请确认选择的是软件输出的空白模板。")
            return None
        self.last_check = workbook
        self.check_label.setText(
            f"检查通过：发现 {len(workbook.rows)} 行需要评价的数据"
            f"（另有 {workbook.skipped_blank_rows} 行完全空白，已跳过）。"
            "可以直接点「批量评价」。")
        return workbook

    # -- 完成后快捷操作 ----------------------------------------------------

    def _reset_quick_actions(self) -> None:
        self.open_result_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)

    def result_path(self) -> Path | None:
        """上次成功生成的结果工作簿路径（没有则 None）。"""

        result = self.last_result
        path = getattr(result, "result_workbook", None) if result is not None else None
        return Path(path) if path else None

    def open_result(self) -> bool:
        """用系统默认程序打开结果工作簿。"""

        path = self.result_path()
        if path is None or not path.exists():
            self.check_label.setText("还没有可打开的结果文件，请先完成一次批量评价。")
            return False
        return _open_path(path)

    def open_result_folder(self) -> bool:
        """在文件管理器中定位结果工作簿（只打开目录，不做最近文件系统）。"""

        path = self.result_path()
        if path is None or not path.exists():
            self.check_label.setText("还没有可打开的结果文件，请先完成一次批量评价。")
            return False
        return _open_path(path.parent)

    # -- 执行 --------------------------------------------------------------

    #: 批量评价进行中（供测试与界面守卫使用）
    busy = False

    def run(self):
        """**同步**执行一次批量评价；返回结果对象（失败返回 None）。

        保留同步内核供测试与非交互场景使用；普通用户点击按钮走
        `start_run()`（后台线程），避免大批量时界面长时间无响应。
        """

        source = self.source_edit.text().strip()
        if not source:
            self._show_error("请先选择要批量评价的输入工作簿。")
            return None
        target = self.resolve_target()
        self.last_result = None
        try:
            result = self.batch.evaluate_workbook(Path(source), destination=target)
        except Exception as error:  # noqa: BLE001 - UI 只提示，真实原因进日志
            import logging

            logging.getLogger("equipeffi.qt.batch").exception("批量评价失败")
            self._show_error(f"{SYSTEM_FAILURE_TEXT}\n（{type(error).__name__}）")
            return None
        self.last_result = result
        self._render(result)
        path = self.result_path()
        available = bool(path is not None and path.exists())
        self.open_result_button.setEnabled(available)
        self.open_folder_button.setEnabled(available)
        return result

    def start_run(self):
        """用户点击「批量评价」：在**后台线程**执行，主线程保持可响应。"""

        if self.busy:
            return None
        source = self.source_edit.text().strip()
        if not source:
            self._show_error("请先选择要批量评价的输入工作簿。")
            return None
        target = self.resolve_target()
        self.last_result = None
        self._set_busy(True, "正在批量评价，请稍候…（大批量可能需要几分钟）")

        thread = QThread(self)
        worker = _BatchWorker(self.batch, Path(source), target)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._on_thread_finished)
        self._thread, self._worker = thread, worker
        thread.start()
        return thread

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.busy = busy
        self.run_button.setEnabled(not busy)
        if message:
            self.check_label.setText(message)

    def _on_finished(self, result) -> None:
        self.last_result = result
        self._render(result)
        # 完成即提供"打开结果 / 打开所在文件夹"（结果文件确实存在时才可用）
        path = self.result_path()
        available = bool(path is not None and path.exists())
        self.open_result_button.setEnabled(available)
        self.open_folder_button.setEnabled(available)
        self._set_busy(False)

    def _on_failed(self, error_name: str) -> None:
        self._show_error(f"{SYSTEM_FAILURE_TEXT}\n（{error_name}）")
        self._set_busy(False)

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self.background_idle.emit()

    def has_active_run(self) -> bool:
        """后台 QThread 是否仍在运行。

        关闭窗口时必须看**线程真实状态**，不能只看 busy：worker 已发 finished
        但 QThread 尚未退出的窄窗口内，销毁页面仍可能触发
        "QThread: Destroyed while thread is still running"。
        """

        thread = self._thread
        return bool(thread is not None and thread.isRunning())

    def notify_close_deferred(self) -> None:
        """告知用户：为保证结果/数据库完整性，任务结束后自动关闭。"""

        if self.has_active_run():
            self.check_label.setText(
                "批量评价仍在运行。为避免损坏结果，任务结束后软件将自动退出。")

    def wait_for_run(self, timeout_ms: int = 120000) -> bool:
        """等待后台批量评价结束（测试用；不改变产品行为）。

        必须**边转事件循环边等**：工作线程结束时会 emit 信号给主线程，若主线程
        阻塞在 `thread.wait()` 就无法投递信号，`thread.quit` 也不会被处理，
        从而永远等不到线程结束。
        """

        from PySide6.QtCore import QCoreApplication, QDeadlineTimer

        deadline = QDeadlineTimer(timeout_ms)
        while not deadline.hasExpired():
            thread = self._thread
            if thread is None:
                break
            QCoreApplication.processEvents()
            # 局部引用：processEvents 期间线程可能已完成并把 _thread 置空
            thread.wait(20)
        QCoreApplication.processEvents()
        return self._thread is None

    def _render(self, result) -> None:
        summary = result.summary
        lines = [
            f"数据行数 {summary.data_row_count} 行；"
            f"设备数量总计 {summary.total_quantity} 台；"
            f"完成正式评价 {summary.evaluated_quantity} 台。",
            f"输入错误 {summary.input_error_rows} 行；"
            f"执行失败 {summary.execution_error_rows} 行；"
            f"未形成正式结论 {summary.unevaluated_rows} 行。",
            f"结果工作簿：{result.result_workbook or '（未输出）'}",
        ]
        if result.batch_record_saved:
            lines.append(f"已保存批次总结记录：{result.batch_record_id}")
        else:
            # 结果文件已生成但历史记录保存失败：必须明确告知，不得静默吞错。
            lines.append(
                "结果文件已生成，但软件历史记录保存失败："
                f"{result.batch_record_error}")
        self.summary_label.setText("\n".join(lines))

        quantities = summary.conclusion_quantities
        self.conclusion_label.setText(
            "按数量统计：" + ("；".join(f"{name} {count} 台"
                                     for name, count in quantities.items())
                          if quantities else "无"))
        if summary.issues:
            # 界面只出现中文类别；内部 kind（INPUT_ERROR 等）不展示给普通用户。
            lines = [f"第 {issue.row_number} 行 · {user_facing_issue_kind(issue.kind)}："
                     f"{issue.reason}" for issue in summary.issues[:10]]
            more = "" if len(summary.issues) <= 10 else (
                f"\n…共 {len(summary.issues)} 行需要关注。")
            self.issue_label.setText("需要关注的行：\n" + "\n".join(lines) + more)
        else:
            self.issue_label.setText("")

    def _show_error(self, message: str) -> None:
        self.summary_label.setText(message)
        self.conclusion_label.setText("")
        self.issue_label.setText("")
