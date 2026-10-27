"""R2 记录列表原生 Windows 布局与真实 Qt 操作证据，显式隔离数据。"""
from ui_capture_runtime import CaptureSession, arguments, require

from PySide6.QtCore import QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QScrollArea

from equipeffi.composition import (create_settings_runtime, create_pump_analysis_service,
                                  create_transformer_analysis_service, create_batch_evaluation_service)
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.presentation.qt.shell import MainWindow


def perform(session):
    args, app = session.args, session.app
    paths = AppDataPaths(args.data_root.resolve())
    settings, logger = create_settings_runtime(paths=paths)
    session.logger = logger
    pump = create_pump_analysis_service(paths=paths)
    transformer = create_transformer_analysis_service(paths=paths)
    batch = create_batch_evaluation_service(paths=paths)
    window = MainWindow(settings, pump, transformer=transformer, batch=batch, data_location=paths.root)
    session.attach(window)
    window.show()
    session.evidence.update({"platform": app.platformName(), "mode": "Qt自动操作，原生平台见platform；非人工验收",
                "data_root": str(paths.root),
                "captures": [], "roundtrips": []})
    evidence = session.evidence

    def settle():
        session.settle(60)

    def click(button):
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        settle()

    def size(width, height):
        window.resize(width, height)
        settle()
        window.resize(width, height)
        settle()
        require([window.width(), window.height()] == [width, height], '[window.width(), window.height()] == [width, height]')

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
    require(form.last_record_status == "RECORDED", 'form.last_record_status == "RECORDED"')
    window.open_records()
    page = window.records_page
    page.search.setText("19762")
    page.date_filter.setText(pump.open_record(form.last_saved_record_id).as_of)
    scroll, table = page.list_scroll_area, page.list
    evidence["record_id"] = form.last_saved_record_id

    def rect(value):
        return [value.x(), value.y(), value.width(), value.height()]

    def context():
        current = table.currentRow()
        return {"search": page.search.text(), "date": page.date_filter.text(),
                "category": page.category_filter.currentData(),
                "conclusion": page.conclusion_filter.currentIndex(),
                "row": current, "column": table.currentColumn(),
                "record_id": page._visible[current].record_id if current >= 0 else None,
                "outer_scroll": scroll.verticalScrollBar().value(),
                "table_scroll": table.verticalScrollBar().value(),
                "table_horizontal_scroll": table.horizontalScrollBar().value()}
    for width, height in ((560, 420), (1000, 700)):
        size(width, height)
        scroll.ensureWidgetVisible(table, 0, 10)
        settle()
        row = table.visualItemRect(table.item(0, 0))
        outer_row = QRect(table.viewport().mapTo(scroll.viewport(), row.topLeft()), row.size())
        row_visible = table.viewport().rect().contains(row) and scroll.viewport().rect().contains(outer_row)
        if width == 560:
            require(scroll.verticalScrollBar().maximum() > 0, 'scroll.verticalScrollBar().maximum() > 0')
        else:
            require(scroll.verticalScrollBar().maximum() == 0, 'scroll.verticalScrollBar().maximum() == 0')
        filename = f"single-records-{width}x{height}.png"
        session.save(filename)
        evidence["captures"].append({"file": filename, "logical_size": [width, height],
            "device_pixel_ratio": window.devicePixelRatioF(),
            "logical_dpi": window.screen().logicalDotsPerInch(),
            "table_size": [table.width(), table.height()],
            "table_viewport": [table.viewport().width(), table.viewport().height()],
            "row_height": table.rowHeight(0), "complete_row_visible": row_visible,
            "first_cell_rect": rect(row), "table_viewport_rect": rect(table.viewport().rect()),
            "first_cell_in_outer_viewport": rect(outer_row), "outer_viewport_rect": rect(scroll.viewport().rect()),
            "outer_scroll_max": scroll.verticalScrollBar().maximum()})
        require(row_visible, "记录行被裁切")
        for method in ("鼠标单击后双击", "键盘Enter"):
            table.setCurrentCell(0, 0)
            before = context()
            if method == "鼠标单击后双击":
                QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=row.center())
                QTest.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=row.center())
            else:
                table.setFocus()
                QTest.keyClick(table, Qt.Key.Key_Return)
            settle()
            detail = {"stack_index": page.stack.currentIndex(), "text": page.detail.text(),
                      "tabs": [page.detail_tabs.tabText(i) for i in range(page.detail_tabs.count())],
                      "current_tab": page.detail_tabs.currentIndex()}
            opened = detail["stack_index"] == 1 and "R2隔离测试项目" in detail["text"]
            click(page.back_button)
            after = context()
            preserved = before == after and page.stack.currentIndex() == 0
            evidence["roundtrips"].append({"logical_size": [width, height], "method": method,
                "detail": detail, "before": before, "after": after,
                "detail_opened": opened, "context_preserved": preserved})
            require(opened and len(detail["tabs"]) == 2 and preserved, "记录详情往返失败")


def main():
    args = arguments()
    return CaptureSession(args, 'operations.json').run(perform)


if __name__ == "__main__":
    raise SystemExit(main())
