"""批量评价（Excel 批量输入/输出）页 — Phase 8。

产品语义
--------
Excel 是**批量输入/输出载体**，不是业务计算引擎：本页把选中工作簿的
「离心泵」Sheet 逐行交给正式 Application 评价，然后把结果写入一个**新的**
结果工作簿，并形成**一条**批次总结记录。

界面上刻意保持简单：选输入 → 选输出 → 开始。**不**询问每种设备需要多少行，
**不**逐 Sheet 扩容（容量由模板的 Excel Table 与语义式 Reader 承担）。
"""
from __future__ import annotations

from pathlib import Path

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
from ..tokens import TOKENS

#: 结果工作簿默认文件名后缀（绝不覆盖输入文件）。
RESULT_SUFFIX = "_批量评价结果.xlsx"

SYSTEM_FAILURE_TEXT = "批量评价未能完成，请检查工作簿或联系技术人员。"


class BatchPage(QWidget):
    """Excel 批量评价页。"""

    def __init__(self, batch: PumpBatchEvaluationService, navigator=None):
        super().__init__()
        self.batch = batch
        self.navigator = navigator
        self.last_result = None
        self._build()

    # -- 构建 --------------------------------------------------------------

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
        layout.setSpacing(TOKENS.spacing)

        # 一级页面标题与导航名一致（与其余页面相同的约定）。
        title = QLabel("批量评价")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(f"{PUMP_DEVICE_TYPE}（Excel）批量输入 / 输出")
        layout.addWidget(subtitle)

        hint = QLabel(
            "选择填写好的空白模板，软件会用正式 GB 19762 计算链逐台评价，"
            "并输出一份新的结果工作簿。\n"
            "结果工作簿不会覆盖你的原始文件；想填多少台就填多少台，软件会自动适应。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        picker = QGroupBox("文件")
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

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("输出工作簿"))
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("留空则在输入文件旁生成新的结果工作簿")
        target_row.addWidget(self.target_edit, 1)
        self.target_button = QPushButton("另存为…")
        self.target_button.clicked.connect(self._pick_target)
        target_row.addWidget(self.target_button)
        picker_layout.addLayout(target_row)

        picker_layout.addWidget(self._template_hint())
        layout.addWidget(picker)

        actions = QHBoxLayout()
        self.run_button = QPushButton("开始批量评价")
        self.run_button.clicked.connect(self.run)
        actions.addWidget(self.run_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        result_box = QGroupBox("批量评价结果")
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

    def _template_hint(self) -> QLabel:
        label = QLabel(
            "提示：请使用软件提供的空白模板填写。类别、单吸/双吸、级数、数量等"
            "字段都已按正式口径校验，填写多少行都可以。")
        label.setWordWrap(True)
        return label

    # -- 选择文件 ----------------------------------------------------------

    def _pick_source(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self, "选择要批量评价的工作簿", "", "Excel 工作簿 (*.xlsx)")
        if chosen:
            self.set_source(chosen)

    def _pick_target(self) -> None:
        chosen, _ = QFileDialog.getSaveFileName(
            self, "选择结果工作簿保存位置", self.default_target_name(),
            "Excel 工作簿 (*.xlsx)")
        if chosen:
            self.target_edit.setText(chosen)

    def set_source(self, path: str | Path) -> None:
        self.source_edit.setText(str(path))
        if not self.target_edit.text().strip():
            self.target_edit.setText(str(self.default_target_name()))

    def default_target_name(self) -> Path:
        source = self.source_edit.text().strip()
        if not source:
            return Path(RESULT_SUFFIX)
        path = Path(source)
        return path.with_name(path.stem + RESULT_SUFFIX)

    # -- 执行 --------------------------------------------------------------

    def run(self):
        """执行一次批量评价；返回结果对象（失败返回 None）。"""

        source = self.source_edit.text().strip()
        if not source:
            self._show_error("请先选择要批量评价的输入工作簿。")
            return None
        target = self.target_edit.text().strip() or str(self.default_target_name())
        self.last_result = None
        try:
            result = self.batch.evaluate_workbook(
                Path(source), destination=Path(target))
        except Exception as error:  # noqa: BLE001 - UI 只提示，真实原因进日志
            import logging

            logging.getLogger("equipeffi.qt.batch").exception("批量评价失败")
            self._show_error(f"{SYSTEM_FAILURE_TEXT}\n（{type(error).__name__}）")
            return None
        self.last_result = result
        self._render(result)
        return result

    def _render(self, result) -> None:
        summary = result.summary
        self.summary_label.setText(
            f"已处理 {summary.total_rows} 行；"
            f"已评价 {summary.evaluated_rows} 行，"
            f"未评价 {summary.unevaluated_rows} 行，"
            f"失败 {summary.invalid_rows} 行。\n"
            f"本次未生成单台分析记录，仅形成批次总结记录：{result.batch_record_id}。\n"
            f"结果工作簿：{result.result_workbook or '（未输出）'}")
        counts = summary.conclusion_counts
        self.conclusion_label.setText(
            "结论分布：" + ("；".join(f"{name} {count} 台" for name, count in counts.items())
                          if counts else "无"))
        if summary.issues:
            lines = [f"第 {issue.row_number} 行：{issue.reason}" for issue in summary.issues[:10]]
            more = "" if len(summary.issues) <= 10 else (
                f"\n…共 {len(summary.issues)} 行需要关注。")
            self.issue_label.setText("需要关注的行：\n" + "\n".join(lines) + more)
        else:
            self.issue_label.setText("")

    def _show_error(self, message: str) -> None:
        self.summary_label.setText(message)
        self.conclusion_label.setText("")
        self.issue_label.setText("")
