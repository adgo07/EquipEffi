"""当前代码的原生Qt自动操作与代表截图；只使用显式隔离目录。"""
from ui_capture_runtime import CaptureSession, arguments, require
from hashlib import sha256
import os
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QComboBox, QScrollArea, QLabel
from openpyxl import load_workbook
from equipeffi.composition import (create_settings_runtime, create_pump_analysis_service,
    create_transformer_analysis_service, create_motor_analysis_service, create_batch_evaluation_service)
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.presentation.qt.shell import MainWindow


def perform(session):
    args, app = session.args, session.app
    paths = AppDataPaths(args.data_root.resolve())
    settings, logger = create_settings_runtime(paths=paths)
    session.logger = logger
    pump = create_pump_analysis_service(paths=paths)
    transformer = create_transformer_analysis_service(paths=paths)
    motor = create_motor_analysis_service(paths=paths)
    batch = create_batch_evaluation_service(paths=paths, motor_candidate=True)
    window = MainWindow(settings, pump, transformer=transformer, motor=motor, batch=batch, data_location=paths.root)
    window.resize(1000, 700)
    session.attach(window)
    window.show()
    session.evidence.update({"platform": app.platformName(), "mode": "Qt自动操作；原生平台见platform，非人工桌面验收",
        "motor_candidate": True, "template_version": batch.template_identity.get("template_version"),
        "data_root": str(paths.root), "scale_factor_override": os.environ.get("QT_SCALE_FACTOR"),
        "screens": [{"name": s.name(), "logical_dpi": s.logicalDotsPerInch(),
                     "device_pixel_ratio": s.devicePixelRatio()} for s in app.screens()],
        "operations": [], "captures": []})
    evidence = session.evidence
    records = {}
    result_id = None
    source = paths.root / "测试数据_三设备输入.xlsx"

    def settle():
        session.settle(30)

    def click(button):
        # 滚动到控件后发原生Qt鼠标事件，走正式clicked信号与服务。
        for scroll in window.pages.currentWidget().findChildren(QScrollArea):
            if scroll.isAncestorOf(button):
                scroll.ensureWidgetVisible(button, 0, 20)
        settle()
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        settle()

    def capture(name, width=1000, height=700):
        window.resize(width, height)
        settle()
        window.resize(width, height)
        settle()
        filename = f"{name}-{width}x{height}.png"
        session.save(filename)
        item = {"file": filename,
            "logical_size": [window.width(), window.height()], "device_pixel_ratio": window.devicePixelRatioF(),
            "sample": "隔离测试数据", "business_sidebar": not window.sidebar.isHidden()}
        if window.pages.currentWidget() is window.records_page:
            history = window.records_page
            table = history.list if history.lists.currentIndex() == 0 else history.batch_list
            item["history"] = {"stack_index": history.stack.currentIndex(),
                "classification": history.lists.currentIndex(), "selected_row": table.currentRow(),
                "selected_column": table.currentColumn(), "search": history.search.text(),
                "batch_search": history.batch_search.text(), "date": history.date_filter.text(),
                "category": history.category_filter.currentData(),
                "conclusion": history.conclusion_filter.currentIndex(),
                "single_record_ids": [r.record_id for r in history._visible],
                "batch_record_ids": [r.batch_record_id for r in history._batch_visible],
                "tabs": [history.detail_tabs.tabText(i) for i in range(history.detail_tabs.count())],
                "current_tab": history.detail_tabs.currentIndex(),
                "detail_text": history.detail.text() if history.stack.currentIndex() == 1 else None}
        evidence["captures"].append(item)

    def fill(page, values):
        for key, value in values.items():
            control = page.field_inputs[key]
            if isinstance(control, QComboBox):
                control.setCurrentIndex(control.findData(value))
            else:
                control.setText(value)

    def operations():
        nonlocal result_id
        window.open_home()
        capture("home", 1440, 1000)
        window.open_standards()
        capture("standards", 1440, 1000)
        window.standards_page.open_detail(0)
        capture("standard-detail", 1440, 1000)
        window.open_analysis(standard_code="GB 19762-2025")
        page = window.analysis_page
        page.project_name.setText("测试数据 · 当前Qt验证项目")
        page.equipment_no.setText("测试泵 P-001")
        page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
        for key, value in dict(QBEP="100", HBEP="50", speed="2900", efficiency="90").items():
            page.point_inputs[key].setText(value)
        click(page.evaluate_button)
        require(page.last_record_status == "RECORDED", 'page.last_record_status == "RECORDED"')
        records["pump"] = page.last_saved_record_id
        evidence["operations"].append({"action": "泵单台鼠标点击分析并自动记录",
            "record_id": page.last_saved_record_id, "record_status": page.last_record_status,
            "saved": page.last_saved_record_id is not None and page.last_record_status == "RECORDED"})
        page.findChild(QScrollArea).verticalScrollBar().setValue(0)
        capture("pump")

        window.open_analysis(standard_code="GB 20052-2024")
        page = window.transformer_analysis_page
        page.project_name.setText("测试数据 · 变压器项目")
        page.equipment_no.setText("测试变压器 T-001")
        page.category.setCurrentIndex(page.category.findData("GB20052-T03"))
        fill(page, dict(capacity_kva="3150", no_load_loss_w="1700", load_loss_w="20700"))
        click(page.evaluate_button)
        require(page.last_record_status == "SAVED", 'page.last_record_status == "SAVED"')
        records["transformer"] = page.last_saved_record_id
        evidence["operations"].append({"action": "变压器单台鼠标点击分析并自动记录",
            "record_id": page.last_saved_record_id, "record_status": page.last_record_status,
            "saved": page.last_saved_record_id is not None and page.last_record_status == "SAVED"})
        page.findChild(QScrollArea).verticalScrollBar().setValue(0)
        capture("transformer", 1180, 800)
        page.findChild(QScrollArea).ensureWidgetVisible(page.conclusion, 0, 20)
        capture("transformer-result", 1180, 800)

        for label, name in (("其他类别", "transformer-other"), ("不确定类别", "transformer-uncertain")):
            page.category.setCurrentIndex(page.category.findText(label))
            settle()
            notes = [w for w in page.fields_group.findChildren(QLabel) if "没有可填写" in w.text()]
            require(len(notes) == 1, "特殊类别提示缺失")
            page.findChild(QScrollArea).ensureWidgetVisible(notes[0], 0, 20)
            settle()
            visible = notes[0].isVisible() and page.fields_group.isVisible()
            evidence["operations"].append({"action": "特殊类别提示", "category": page.category.currentData(),
                "label": label, "note": notes[0].text(), "group_visible": page.fields_group.isVisible(),
                "note_visible": visible, "field_ids": list(page.field_inputs)})
            require(visible, "特殊类别提示不可见")
            capture(name, 1000, 700)
        page.category.setCurrentIndex(page.category.findData("GB20052-T03"))
        settle()
        restored = list(page.field_inputs)
        evidence["operations"].append({"action": "切回普通类别", "category": page.category.currentData(),
                                      "field_ids": restored})
        require("capacity_kva" in restored, "普通类别字段未恢复")

        window.open_analysis(standard_code="GB 18613-2020")
        page = window.motor_analysis_page
        page.category.setCurrentIndex(page.category.findData("three_phase_induction"))
        fill(page, dict(rated_voltage_kv="0.38", rated_frequency_hz="50", rated_output_power_kw="0.14",
                        poles="4", measured_efficiency_pct="71.43"))
        click(page.evaluate_button)
        require(page.last_record_status == "SAVED", 'page.last_record_status == "SAVED"')
        records["motor"] = page.last_saved_record_id
        evidence["operations"].append({"action": "候选电机单台鼠标点击分析并自动记录",
            "record_id": page.last_saved_record_id, "record_status": page.last_record_status,
            "saved": page.last_saved_record_id is not None and page.last_record_status == "SAVED"})
        page.findChild(QScrollArea).verticalScrollBar().setValue(0)
        capture("motor-candidate", 1180, 800)
        capture("motor-candidate-small", 560, 420)
        window.resize(1180, 800)
        settle()
        page.findChild(QScrollArea).ensureWidgetVisible(page.conclusion, 0, 20)
        capture("motor-result", 1180, 800)

        batch.export_blank_template(source)
        workbook = load_workbook(source)
        pump_values = {"B4": "测试数据·泵", "D4": 2, "F4": "其他类别"}
        transformer_values = {"B4": "测试数据·变压器", "D4": 3, "F4": transformer.input_contract.categories[2].label,
                               "G4": 3150, "J4": 1700, "K4": 20700}
        motor_values = {"B4": "测试数据·电机", "D4": 4, "F4": next(c.label for c in motor.input_contract.categories if c.category_id == "three_phase_induction"),
                        "G4": 0.38, "H4": 50, "J4": 0.14, "K4": 4, "M4": 71.43}
        for sheet, values in (("离心泵", pump_values), ("变压器", transformer_values), ("电动机", motor_values)):
            for cell, value in values.items():
                workbook[sheet][cell] = value
        workbook.save(source)
        workbook.close()
        input_hash = sha256(source.read_bytes()).hexdigest()
        single_ids_before = [r.record_id for r in pump.list_records()]
        batch_ids_before = [r.batch_record_id for r in batch.list_batch_records()]
        window.open_batch()
        page = window.batch_page
        page.set_source(source)
        require(page.last_check is not None, 'page.last_check is not None')
        evidence["operations"].append({"action": "选文件自动检查", "recognized_sheets": list(page.last_check.sheets)})
        capture("batch-check", 1180, 800)
        click(page.run_button)
        waited = page.wait_for_run(120000)
        session.check()
        require(waited, "批量任务未按时结束")
        result = page.last_result
        require(result and result.batch_record_saved, 'result and result.batch_record_saved')
        result_id = result.batch_record_id
        single_ids_after = [r.record_id for r in pump.list_records()]
        batch_ids_after = [r.batch_record_id for r in batch.list_batch_records()]
        single_unchanged = single_ids_before == single_ids_after
        one_batch = (set(batch_ids_after) - set(batch_ids_before) == {result_id}
                     and len(batch_ids_after) == len(batch_ids_before) + 1)
        input_hash_after = sha256(source.read_bytes()).hexdigest()
        separate_output = Path(result.result_workbook).resolve() != source.resolve()
        evidence["operations"].append({"action": "后台三设备批量评价完成并线程退出", "data_rows": result.summary.data_row_count,
            "total_quantity": result.summary.total_quantity, "single_records_unchanged": single_unchanged,
            "one_batch_record": one_batch, "single_ids_before": single_ids_before, "single_ids_after": single_ids_after,
            "single_count_before": len(single_ids_before), "single_count_after": len(single_ids_after),
            "batch_ids_before": batch_ids_before, "batch_ids_after": batch_ids_after,
            "batch_count_before": len(batch_ids_before), "batch_count_after": len(batch_ids_after),
            "batch_record_id": result_id, "wait_completed": waited,
            "input_sha256_before": input_hash, "input_sha256_after": input_hash_after,
            "input": str(source), "output": str(result.result_workbook), "separate_output": separate_output,
            "worker_present": page._thread is not None})
        require(single_unchanged and one_batch and input_hash == input_hash_after and separate_output
                and page._thread is None, "批次保存、另存或线程退出边界不符合预期")
        page.findChild(QScrollArea).verticalScrollBar().setValue(page.findChild(QScrollArea).verticalScrollBar().maximum())
        capture("batch-result", 1180, 800)
        with patch("equipeffi.presentation.qt.pages.batch.QFileDialog.getOpenFileName", return_value=("", "")):
            page._pick_source()
        cancel_preserved = page.last_result is result
        page.set_source(source)
        selection_cleared = page.last_result is None and not page.open_result_button.isEnabled()
        evidence["operations"].append({"action": "取消保留结果；重新选择同一源也使旧结果失效",
            "cancel_preserved": cancel_preserved, "selection_cleared": selection_cleared,
            "last_result_id": getattr(page.last_result, "batch_record_id", None),
            "open_result_enabled": page.open_result_button.isEnabled(),
            "passed": cancel_preserved and selection_cleared})
        require(cancel_preserved and selection_cleared, "取消或重选后的结果关联错误")

        window.open_records()
        page = window.records_page
        capture("single-records", 1180, 800)
        window.open_records(records["transformer"])
        capture("single-detail-result", 1180, 800)
        page.detail_tabs.setCurrentIndex(1)
        capture("single-detail-basis", 1180, 800)
        click(page.back_button)
        click(page.batch_button)
        capture("batch-records", 1180, 800)
        page.show_batch_record(result_id)
        capture("batch-detail-result", 1180, 800)
        page.detail_tabs.setCurrentIndex(1)
        capture("batch-detail-basis", 1000, 700)
        capture("batch-detail-small", 560, 420)
        require(page.detail_tabs.count() == 2, 'page.detail_tabs.count() == 2')
        evidence["operations"].append({"action": "打开单台与批次两页签独立详情", "detail_tabs": [page.detail_tabs.tabText(i) for i in range(2)]})
        window.open_settings()
        settings.set("last.directory", str(paths.root / "测试长路径" / "设备分析资料" / "输入工作簿"))
        window.settings_page.refresh()
        capture("settings", 1000, 700)
        window.settings_page.runtime_section.set_expanded(True)
        window.resize(560, 420)
        settle()
        window.settings_page.scroll_area.ensureWidgetVisible(window.settings_page.runtime)
        capture("settings-small", 560, 420)

    operations()


def main():
    args = arguments()
    return CaptureSession(args, 'operations.json').run(perform)


if __name__ == "__main__":
    raise SystemExit(main())
