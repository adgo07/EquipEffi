"""R2 记录列表原生 Windows 布局与真实 Qt 操作证据，显式隔离数据。"""
import argparse
import json
import os
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QScrollArea

from equipeffi.composition import (create_settings_runtime, create_pump_analysis_service,
                                  create_transformer_analysis_service, create_batch_evaluation_service)
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.runtime_logging import close_logging
from equipeffi.presentation.qt.shell import MainWindow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.data_root.exists() and any(args.data_root.iterdir()):
        parser.error("必须使用新的空隔离数据目录")
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    assert app.platformName() == "windows", "证据必须来自 Windows 原生 Qt"
    assert not os.environ.get("QT_SCALE_FACTOR"), "不得覆盖系统缩放"
    paths = AppDataPaths(args.data_root.resolve())
    settings, logger = create_settings_runtime(paths=paths)
    pump = create_pump_analysis_service(paths=paths)
    transformer = create_transformer_analysis_service(paths=paths)
    batch = create_batch_evaluation_service(paths=paths)
    window = MainWindow(settings, pump, transformer=transformer, batch=batch, data_location=paths.root)
    window.show()
    evidence = {"platform": app.platformName(), "mode": "原生Qt自动操作，非人工验收",
                "data_root": str(paths.root), "scale_factor_override": None,
                "captures": [], "roundtrips": []}

    def settle():
        QTest.qWait(60)

    def click(button):
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        settle()

    def size(width, height):
        window.resize(width, height)
        settle()
        window.resize(width, height)
        settle()
        assert [window.width(), window.height()] == [width, height]

    try:
        size(1000, 700)
        window.open_analysis(standard_code="GB 19762-2025")
        form = window.analysis_page
        form.project_name.setText("R2隔离测试项目")
        form.equipment_no.setText("测试泵 P-001")
        form.category.setCurrentIndex(form.category.findData("单级单吸清水离心泵"))
        for key, value in dict(QBEP="100", HBEP="50", speed="2900", efficiency="90").items():
            form.point_inputs[key].setText(value)
        form.findChild(QScrollArea).ensureWidgetVisible(form.evaluate_button)
        settle()
        click(form.evaluate_button)
        assert form.last_record_status == "RECORDED"
        window.open_records()
        page = window.records_page
        page.search.setText("19762")
        page.date_filter.setText(pump.open_record(form.last_saved_record_id).as_of)
        scroll, table = page.list_scroll_area, page.list
        for width, height in ((560, 420), (1000, 700)):
            size(width, height)
            scroll.ensureWidgetVisible(table, 0, 10)
            settle()
            row = table.visualItemRect(table.item(0, 0))
            outer_row = QRect(table.viewport().mapTo(scroll.viewport(), row.topLeft()), row.size())
            assert table.viewport().rect().contains(row)
            assert scroll.viewport().rect().contains(outer_row)
            if width == 560:
                assert scroll.verticalScrollBar().maximum() > 0
            else:
                assert scroll.verticalScrollBar().maximum() == 0
            filename = f"single-records-{width}x{height}.png"
            assert window.grab().save(str(args.output / filename))
            evidence["captures"].append({"file": filename, "logical_size": [width, height],
                "device_pixel_ratio": window.devicePixelRatioF(),
                "logical_dpi": window.screen().logicalDotsPerInch(),
                "table_size": [table.width(), table.height()],
                "table_viewport": [table.viewport().width(), table.viewport().height()],
                "row_height": table.rowHeight(0), "complete_row_visible": True,
                "outer_scroll_max": scroll.verticalScrollBar().maximum()})
            context = (page.search.text(), page.date_filter.text(), scroll.verticalScrollBar().value())
            for method in ("鼠标单击后双击", "键盘Enter"):
                table.setCurrentCell(0, 0)
                if method == "鼠标单击后双击":
                    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=row.center())
                    QTest.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=row.center())
                else:
                    table.setFocus()
                    QTest.keyClick(table, Qt.Key.Key_Return)
                settle()
                assert page.stack.currentIndex() == 1
                assert "R2隔离测试项目" in page.detail.text()
                assert page.detail_tabs.count() == 2
                click(page.back_button)
                assert page.stack.currentIndex() == 0
                assert context == (page.search.text(), page.date_filter.text(), scroll.verticalScrollBar().value())
                evidence["roundtrips"].append({"logical_size": [width, height], "method": method,
                                               "detail_opened": True, "context_preserved": True})
        (args.output / "operations.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        window.close()
        app.processEvents()
        close_logging(logger)


if __name__ == "__main__":
    main()
