"""Small R4 native evidence set; reuse R3 isolation and failure lifecycle."""
from ui_capture_runtime import CaptureSession, arguments, require
from PySide6.QtWidgets import QScrollArea
from openpyxl import load_workbook
from equipeffi.composition import (create_settings_runtime, create_pump_analysis_service,
    create_transformer_analysis_service, create_batch_evaluation_service)
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.presentation.qt.shell import MainWindow


def perform(session):
    paths = AppDataPaths(session.args.data_root)
    settings, session.logger = create_settings_runtime(paths=paths)
    pump = create_pump_analysis_service(paths=paths)
    transformer = create_transformer_analysis_service(paths=paths)
    batch = create_batch_evaluation_service(paths=paths)
    window = MainWindow(settings, pump, transformer=transformer, batch=batch, data_location=paths.root)
    session.attach(window)
    window.resize(1000, 700)
    window.show()
    session.evidence["mode"] = "Qt自动操作；platform=windows才表示原生，非人工DPI验收"

    def capture(name, size=(1000, 700), table=None):
        window.resize(*size)
        session.settle(80)
        window.resize(*size)
        session.settle(80)
        item = {"file": name + ".png", "logical_size": [window.width(), window.height()],
                "dpr": window.devicePixelRatioF()}
        require(item["logical_size"] == list(size), "窗口尺寸不符")
        if table is not None:
            if size[0] < 1000:
                window.records_page.list_scroll_area.ensureWidgetVisible(table, 0, 10)
                session.settle(50)
            columns = [table.columnWidth(i) for i in range(table.columnCount())]
            item.update({"viewport_width": table.viewport().width(), "column_widths": columns,
                "horizontal_max": table.horizontalScrollBar().maximum(), "row_height": table.rowHeight(0),
                "full_text": [table.item(0, i).text() if table.item(0, i) else None for i in range(table.columnCount())],
                "tooltips": [table.item(0, i).toolTip() if table.item(0, i) else None for i in range(table.columnCount())]})
            if size[0] >= 1000:
                require(item["horizontal_max"] == 0 and sum(columns) == table.viewport().width(), "默认窗口表格未完整适配")
        session.save(item["file"])
        session.evidence["captures"].append(item)

    window.open_home()
    capture("home-empty")
    window.open_analysis(standard_code="GB 19762-2025")
    page = window.analysis_page
    page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
    page.project_name.setText("R4隔离测试 · 超长企业与设备能效分析项目名称，完整保留供历史查询")
    page.equipment_no.setText("R4-P-001")
    for key, value in dict(QBEP="100", HBEP="50", speed="2900", efficiency="90").items():
        page.point_inputs[key].setText(value)
    result = page.evaluate()
    require(result is not None and page.last_saved_record_id is not None, "正式单台记录未形成")
    session.evidence["record_id"] = page.last_saved_record_id
    window.open_home()
    capture("home-records", table=window.home_page.records)
    window.open_standards()
    capture("standards", table=window.standards_page.table)
    window.open_records()
    history = window.records_page
    history.single_button.click()
    capture("single-records", table=history.list)
    capture("single-records-small", (560, 420), table=history.list)

    source = paths.root / "R4隔离测试_很长的批量输入工作簿文件名称_结果必须另存为新文件.xlsx"
    batch.export_blank_template(source)
    book = load_workbook(source)
    for cell, value in {"B4": "R4测试泵", "D4": 1, "F4": "其他类别"}.items():
        book["离心泵"][cell] = value
    book.save(source)
    book.close()
    outcome = batch.evaluate_workbook(source, destination=paths.root / "R4独立输出.xlsx")
    require(outcome.batch_record_saved, "正式批次记录未形成")
    session.evidence["batch_record_id"] = outcome.batch_record_id
    window.open_records()
    history.batch_button.click()
    capture("batch-records", table=history.batch_list)

    window.open_analysis(standard_code="GB 20052-2024")
    page = window.transformer_analysis_page
    page.category.setCurrentIndex(page.category.findData("GB20052-T02"))
    page.field_inputs["standard_conditions"].setCurrentIndex(1)
    page.field_inputs["capacity_kva"].setText("0")
    invalid = page.evaluate()
    require(invalid is None and page.last_saved_record_id is None, "非法容量误形成记录")
    session.settle(60)
    scroll = page.findChild(QScrollArea)
    scroll.ensureWidgetVisible(page.field_inputs["capacity_kva"].numeric_error, 0, 20)
    session.settle(60)
    session.evidence["numeric_feedback"] = {"field_text": page.field_inputs["capacity_kva"].text(),
        "error": page.field_inputs["capacity_kva"].numeric_error.text(), "saved_id": page.last_saved_record_id,
        "condition_group": page.conditions_group.title()}
    capture("transformer-numeric-feedback")


def main():
    return CaptureSession(arguments(), "operations.json").run(perform)


if __name__ == "__main__":
    raise SystemExit(main())
