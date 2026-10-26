"""第一阶段可复核 Qt 截图；数据目录必须显式注入并为空目录。"""
import argparse
import json
import os
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
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
        parser.error("截图数据目录必须为空；不允许使用已有用户数据。")
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    paths = AppDataPaths(args.data_root.resolve())
    settings, logger = create_settings_runtime(paths=paths)
    window = MainWindow(settings, create_pump_analysis_service(paths=paths),
        transformer=create_transformer_analysis_service(paths=paths),
        batch=create_batch_evaluation_service(paths=paths), data_location=paths.root)
    page = window.analysis_page
    page.project_name.setText("测试数据 · 青舟示例项目")
    page.equipment_no.setText("测试泵 P-001")
    page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
    for field, value in dict(QBEP="100", HBEP="50", speed="2900", efficiency="90").items():
        page.point_inputs[field].setText(value)
    assert page.evaluate() is not None
    assert page.last_saved_record_id
    window.show()
    evidence = {"platform": app.platformName(), "python": sys.version,
        "data_root": str(paths.root), "scale_factor_override": os.environ.get("QT_SCALE_FACTOR"),
        "screens": [], "captures": []}
    for screen in app.screens():
        evidence["screens"].append({"name": screen.name(), "logical_dpi": screen.logicalDotsPerInch(),
            "device_pixel_ratio": screen.devicePixelRatio()})

    tasks = [(1440, 1000, name) for name in ("home", "standards", "standard-detail", "pump")]
    tasks += [(1000, 700, "home"), (1000, 700, "pump-result"),
              (560, 420, "standards"), (560, 420, "pump"), (560, 420, "standard-detail")]

    def step():
        if not tasks:
            (args.output / "capture.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            window.close()
            app.quit()
            return
        width, height, name = tasks.pop(0)
        window.resize(width, height)
        if name == "home":
            window.open_home()
        elif name.startswith("standard"):
            window.open_standards()
            window.standards_page.stack.setCurrentIndex(0)
            if name == "standard-detail":
                window.standards_page.open_detail(0)
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
            assert window.grab().save(str(args.output / filename))
            evidence["captures"].append({"file": filename, "logical_size": [window.width(), window.height()],
                "device_pixel_ratio": window.devicePixelRatioF(), "sample": "隔离测试数据"})
            QTimer.singleShot(100, step)
        QTimer.singleShot(250, capture)

    QTimer.singleShot(100, step)
    try:
        return app.exec()
    finally:
        close_logging(logger)


if __name__ == "__main__":
    raise SystemExit(main())
