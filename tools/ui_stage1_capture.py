"""第一阶段可复核 Qt 截图；数据目录必须显式注入并为空目录。"""
from ui_capture_runtime import CaptureSession, arguments, require
import os
import sys
from unittest.mock import patch

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
    window = MainWindow(settings, create_pump_analysis_service(paths=paths),
        transformer=create_transformer_analysis_service(paths=paths),
        batch=create_batch_evaluation_service(paths=paths), data_location=paths.root)
    session.attach(window)
    page = window.analysis_page
    page.project_name.setText("测试数据 · 青舟示例项目")
    page.equipment_no.setText("测试泵 P-001")
    page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
    for field, value in dict(QBEP="100", HBEP="50", speed="2900", efficiency="90").items():
        page.point_inputs[field].setText(value)
    result = page.evaluate()
    require(result is not None, "泵分析没有结果")
    require(page.last_saved_record_id, 'page.last_saved_record_id')
    window.show()
    session.evidence.update({"platform": app.platformName(), "python": sys.version,
        "data_root": str(paths.root), "scale_factor_override": os.environ.get("QT_SCALE_FACTOR"),
        "screens": [], "captures": []})
    evidence = session.evidence
    evidence["analysis"] = {"record_id": page.last_saved_record_id,
                            "record_status": page.last_record_status,
                            "result_present": result is not None}
    for screen in app.screens():
        evidence["screens"].append({"name": screen.name(), "logical_dpi": screen.logicalDotsPerInch(),
            "device_pixel_ratio": screen.devicePixelRatio()})

    tasks = [(1440, 1000, name) for name in ("home", "standards", "standard-detail", "pump")]
    tasks += [(1000, 700, "home"), (1000, 700, "pump-result"),
              (560, 420, "standards"), (560, 420, "pump"), (560, 420, "standard-detail"),
              (560, 420, "standard-reopened"), (1000, 700, "standard-unavailable"),
              (1000, 700, "standard-read-failure")]

    def step():
        width, height, name = tasks.pop(0)
        window.resize(width, height)
        if name == "home":
            window.open_home()
        elif name.startswith("standard"):
            window.open_standards()
            standards = window.standards_page
            standards.show_list()
            if name == "standard-detail":
                standards.open_detail(0)
            elif name == "standard-reopened":
                standards.open_detail(0)
                app.processEvents()
                standards.detail_scroll.verticalScrollBar().setValue(standards.detail_scroll.verticalScrollBar().maximum())
                standards.back_button.click()
                standards.open_detail(1)
            elif name == "standard-unavailable":
                standards.open_detail(1)
                standards.start_button.click()
                window.open_analysis(standard_code="UNKNOWN")
            elif name == "standard-read-failure":
                standards.open_detail(0)
                with patch.object(standards.services[-1], "standard_overview", side_effect=OSError("截图故障注入测试")):
                    standards.refresh()
        else:
            window.open_analysis(standard_code="GB 19762-2025")
            scroll = page.findChild(QScrollArea)
            scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum() if name == "pump-result" else 0)

        def capture():
            window.resize(width, height)
            app.processEvents()
            # 给布局一次事件循环后再定位结果，避免 resize 后旧滚动范围。
            if name.startswith("pump"):
                scroll = page.findChild(QScrollArea)
                if name == "pump-result":
                    scroll.ensureWidgetVisible(page.conclusion, 0, 20)
                else:
                    scroll.verticalScrollBar().setValue(0)
            app.processEvents()
            filename = f"{name}-{width}x{height}.png"
            session.save(filename)
            item = {"file": filename, "logical_size": [window.width(), window.height()],
                "device_pixel_ratio": window.devicePixelRatioF(), "sample": "隔离测试数据"}
            if name.startswith("standard"):
                standards = window.standards_page
                item.update({"detail": standards.stack.currentIndex() == 1,
                    "standard_code": standards.standard_code,
                    "detail_scroll": standards.detail_scroll.verticalScrollBar().value(),
                    "table_viewport_width": standards.table.viewport().width(),
                    "column_widths": [standards.table.columnWidth(i) for i in range(5)],
                    "visible_feedback": standards.list_status.text() if standards.list_status.isVisible() else None,
                    "failure_injection": name == "standard-read-failure"})
                if name == "standards" and width == 1440:
                    require(sum(item["column_widths"]) == item["table_viewport_width"], 'sum(item["column_widths"]) == item["table_viewport_width"]')
                if name == "standard-reopened":
                    require(item["detail_scroll"] == 0, 'item["detail_scroll"] == 0')
                if name in ("standard-unavailable", "standard-read-failure"):
                    require(not item["detail"] and item["visible_feedback"], 'not item["detail"] and item["visible_feedback"]')
            evidence["captures"].append(item)

        session.settle(250)
        capture()

    while tasks:
        session.check()
        step()


def main():
    args = arguments()
    return CaptureSession(args, 'capture.json').run(perform)


if __name__ == "__main__":
    raise SystemExit(main())
