"""Qt 投影回归：变压器表单、只读历史与多工作表摘要。"""
from __future__ import annotations

import os
import unittest
from decimal import Decimal
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from equipeffi.domain.devices.transformer.input_contract import (
    TRANSFORMER_INPUT_CONTRACT,
)
from equipeffi.presentation.qt.pages.batch import BatchPage
from equipeffi.presentation.qt.pages.records import RecordsPage
from equipeffi.presentation.qt.pages.standards import StandardsPage
from equipeffi.presentation.qt.pages.transformer_analysis import (
    DeviceAnalysisPage,
    TransformerAnalysisPage,
)


class _TransformerService:
    input_contract = TRANSFORMER_INPUT_CONTRACT

    def __init__(self, record_status="SAVED"):
        self.record_status = record_status
        self.requests = []
        self.open_count = 0
        self.missing_fields = ()
        self.raise_on_analysis = None

    def standard_overview(self):
        return {
            "standard_code": "GB 20052-2024",
            "name": "电力变压器能效限定值及能效等级",
            "edition": "2024",
            "effective_date": "2025-02-01",
            "support_status": "IMPLEMENTED",
            "scope_text": "变压器产品目录",
            "notes": "等待正式支持验收。",
        }

    def analyze_and_record(self, request):
        if self.raise_on_analysis is not None:
            raise self.raise_on_analysis
        self.requests.append(request)
        result = SimpleNamespace(
            product_category=request.values["category"],
            as_of=request.as_of,
            evaluation_status="SUCCESS",
            grade="1",
            ui_conclusion="符合能效1级要求",
            thresholds={
                "no_load_loss_1": Decimal("100.123"),
                "load_loss_1": Decimal("200"),
                "no_load_loss_2": Decimal("110"),
                "load_loss_2": Decimal("210"),
                "no_load_loss_3": Decimal("120"),
                "load_loss_3": Decimal("220"),
            },
            explanation="测试说明",
            missing_fields=self.missing_fields,
            raw_values=request.values,
            references={},
            support_status="IMPLEMENTED",
        )
        record = SimpleNamespace(record_id="private-record-id") if self.record_status == "SAVED" else None
        return SimpleNamespace(result=result, record=record,
                               record_status=self.record_status,
                               record_error="写入失败" if self.record_status == "SAVE_FAILED" else "")


class _PumpService:
    record = None

    def standard_overview(self):
        return {
            "standard_code": "GB 19762-2025",
            "standard_name": "离心泵能效限定值及能效等级",
            "status": "现行",
            "effective_date": "2026-02-01",
            "data_version": "泵标准数据",
            "source_file": "",
            "scopes": [],
            "supported_categories": ["单级单吸清水离心泵"],
            "special_categories": ["其他类别", "不确定类别"],
            "supersession_note": "当前未提供替代关系。",
            "lifecycle_warning": "",
            "lifecycle_state": "EFFECTIVE",
            "as_of_policy": "评价日期用于记录与追溯。",
        }

    def record_categories(self):
        return ()

    def search_records(self, query):
        return SimpleNamespace(records=(), total=0, offset=query.offset)

    def list_records(self, limit=5):
        return ()

    def open_record(self, record_id):
        return self.record


class _Settings:
    LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

    def get(self, _key, default=None):
        return default

    def set(self, _key, _value):
        return None


class _BatchRecords:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def list_batch_records(self, limit=51):
        return ()

    def open_batch_record(self, record_id):
        return self.snapshot


class _EmptyBatchRecords:
    def list_batch_records(self, limit=51):
        return ()


def _record_snapshot():
    option = TRANSFORMER_INPUT_CONTRACT.categories[0]
    condition = TRANSFORMER_INPUT_CONTRACT.condition_options(option.category_id)[0]
    return SimpleNamespace(
        record_id="TR-private",
        standard_code="GB 20052-2024",
        device_type="transformer",
        product_category=option.category_id,
        as_of="2026-10-23",
        grade="1",
        evaluation_status="SUCCESS",
        ui_conclusion="符合能效1级要求",
        input_snapshot={
            "category_id": option.category_id,
            "category_label": option.label,
            "category": option.label,
            "capacity_kva": "630",
            "no_load_loss_w": "123.450",
            "load_loss_w": "456",
            "standard_conditions": dict(condition.values),
            "project_name": "示例项目",
            "equipment_no": "T-01",
        },
        result_snapshot={
            "missing_fields": [],
            "explanation": "来自保存快照的解释。",
            "support_status": "IMPLEMENTED",
            "thresholds": {"no_load_loss_1": "100.123"},
        },
        reference_snapshot={},
        finalized_at_utc="2026-10-23T00:00:00Z",
    )


class TransformerQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        self.app.processEvents()

    def _track(self, widget):
        self.widgets.append(widget)
        return widget

    def test_contract_builds_fields_and_raw_values_are_forwarded(self):
        service = _TransformerService()
        page = self._track(TransformerAnalysisPage(service))
        category = service.input_contract.categories[0]
        page.category.setCurrentIndex(page.category.findData(category.category_id))
        self.assertIn("capacity_kva", page.field_inputs)
        self.assertIn("no_load_loss_w", page.field_inputs)
        self.assertIn("standard_conditions", page.field_inputs)

        page.field_inputs["capacity_kva"].setText("0630.00")
        page.field_inputs["no_load_loss_w"].setText("00123.450")
        page.field_inputs["load_loss_w"].setText("456")
        condition = service.input_contract.condition_options(category.category_id)[1]
        page.field_inputs["standard_conditions"].setCurrentIndex(
            page.field_inputs["standard_conditions"].findData(condition.condition_id))

        result = page.evaluate()
        self.assertEqual(result.ui_conclusion, "符合能效1级要求")
        values = service.requests[0].values
        self.assertEqual(values["capacity_kva"], "0630.00")
        self.assertEqual(values["no_load_loss_w"], "00123.450")
        self.assertEqual(values["standard_conditions"], condition.condition_id)
        self.assertIn("尚待正式支持验收", page.summary.text())
        self.assertNotIn("IMPLEMENTED", page.summary.text())
        self.assertNotIn("private-record-id", page.record_label.text())
        self.assertIn("空载损耗限值（1级）", page.thresholds_label.text())
        service.missing_fields = ("capacity_kva",)
        page.evaluate()
        self.assertIn("额定容量", page.summary.text())
        self.assertNotIn("capacity_kva", page.summary.text())

    def test_category_contract_selects_transformer_fields_and_h_conditions(self):
        service = _TransformerService()
        page = self._track(TransformerAnalysisPage(service))
        page.category.setCurrentIndex(page.category.findData("GB20052-T27"))
        self.assertTrue({"uk_hm_rated_percent", "uk_hl_rated_percent",
                         "uk_ml_rated_percent"}.issubset(page.field_inputs))
        self.assertNotIn("standard_conditions", page.field_inputs)

        page.category.setCurrentIndex(page.category.findData("GB20052-T32"))
        self.assertIn("standard_conditions", page.field_inputs)
        self.assertIn("hv_rated_voltage_kv", page.field_inputs)
        self.assertIn("lv_rated_voltage_kv", page.field_inputs)
        condition = next(option for option in service.input_contract.condition_options(
            "GB20052-T32") if option.values.get("thermal_class") == "H")
        control = page.field_inputs["standard_conditions"]
        control.setCurrentIndex(control.findData(condition.condition_id))
        self.assertIn("H级", control.currentText())

    def test_record_outcomes_have_distinct_user_messages(self):
        for status, expected in (("SAVE_FAILED", "保存失败"),
                                 ("NOT_ELIGIBLE", "未形成可保存")):
            with self.subTest(status=status):
                service = _TransformerService(status)
                page = self._track(TransformerAnalysisPage(service))
                category = service.input_contract.categories[0]
                page.category.setCurrentIndex(page.category.findData(category.category_id))
                page.evaluate()
                self.assertIn(expected, page.record_label.text())

    def test_device_switch_defaults_to_pump_and_keeps_original_widget(self):
        pump = QWidget()
        transformer = TransformerAnalysisPage(_TransformerService())
        page = self._track(DeviceAnalysisPage(pump, transformer))
        self.assertEqual(page.device_selector.currentData(), "centrifugal_pump")
        self.assertIs(page.pages.currentWidget(), pump)
        page.device_selector.setCurrentIndex(page.device_selector.findData("transformer"))
        self.assertIs(page.pages.currentWidget(), transformer)
        page.select_standard("GB 19762-2025")
        self.assertEqual(page.device_selector.currentData(), "centrifugal_pump")

    def test_shell_keeps_pump_analysis_page_and_routes_standard_selection(self):
        from equipeffi.presentation.qt.pages.analysis import AnalysisPage
        from equipeffi.presentation.qt.shell import MainWindow

        window = self._track(MainWindow(
            _Settings(), _PumpService(), batch=_EmptyBatchRecords(),
            transformer=_TransformerService()))
        self.assertIsInstance(window.analysis_page, AnalysisPage)
        self.assertIsNot(window._page_widgets["新建分析"], window.analysis_page)
        window.open_analysis(standard_code="GB 20052-2024")
        self.assertEqual(window.device_analysis_page.device_selector.currentData(),
                         "transformer")

    def test_transformer_standard_is_marked_implemented_not_supported(self):
        transformer = _TransformerService()
        navigator = SimpleNamespace(open_analysis=lambda **kwargs: setattr(
            navigator, "selected", kwargs.get("standard_code")))
        page = self._track(StandardsPage(
            _PumpService(), navigator, transformer=transformer))
        page.open_detail(1)
        visible = "\n".join(label.text() for label in page.section_labels) + page.table.item(1, 4).text()
        self.assertIn("GB 20052-2024", visible)
        self.assertIn("已接入，待正式支持验收", visible)
        self.assertNotIn("本版本已正式支持", visible)
        page._start_analysis()
        self.assertEqual(navigator.selected, "GB 20052-2024")

    def test_transformer_record_renders_chinese_labels_from_snapshot_only(self):
        service = _PumpService()
        service.record = _record_snapshot()
        page = self._track(RecordsPage(service, transformer=_TransformerService()))
        text = page.show_record("TR-private")
        self.assertIn("额定容量（kVA）：630", text)
        self.assertIn("空载损耗（W）：123.450", text)
        self.assertIn("示例项目", text)
        self.assertIn("标准条件：", text)
        self.assertIn("空载损耗限值（1级）", text)
        self.assertNotIn("TR-private", text)
        self.assertNotIn("GB20052-T01", text)
        self.assertNotIn("capacity_kva", text)
        self.assertNotIn("IMPLEMENTED", text)

    def test_mixed_batch_replaces_multi_marker_with_readable_details(self):
        batch_snapshot = SimpleNamespace(
            standard_code="MULTI", sheet_name="MULTI", evaluation_date="2026-10-23",
            source_file_name="input.xlsx", output_file_name="output.xlsx",
            data_row_count=2, total_quantity=2, evaluated_count=2,
            evaluated_quantity=2, unevaluated_count=0, invalid_count=0,
            created_at_utc="2026-10-23T00:00:00Z",
            summary={"sheets": [
                {"sheet_name": "离心泵", "standard_code": "GB 19762-2025",
                 "data_row_count": 1, "evaluated_quantity": 1,
                 "sheet_id": "centrifugal_pump"},
                {"sheet_name": "变压器", "standard_code": "GB 20052-2024",
                 "data_row_count": 1, "evaluated_quantity": 4, "total_quantity": 4,
                 "conclusion_quantities": {"1级": 4}, "sheet_id": "transformer"},
            ], "unprocessed_sheets": ["电动机"]},
        )
        page = self._track(RecordsPage(
            _PumpService(), transformer=_TransformerService(),
            batch=_BatchRecords(batch_snapshot)))
        text = page.show_batch_record("batch-id")
        self.assertNotIn("MULTI", text)
        self.assertIn("GB 19762-2025、GB 20052-2024", text)
        self.assertIn("离心泵、变压器", text)
        self.assertIn("未处理工作表：电动机", text)
        self.assertIn("变压器：共 4 台（数据 1 行）", text)
        self.assertIn("1级 4 台；2级 0 台；3级 0 台", text)
        self.assertIn("总台数未记录", text)  # 旧泵快照不得由行数补造台数。

    def test_batch_summary_names_sheet_for_issues_and_reports_unprocessed(self):
        page = self._track(BatchPage(object()))
        summary = SimpleNamespace(
            data_row_count=2,
            total_quantity=2,
            evaluated_quantity=1,
            input_error_rows=1,
            execution_error_rows=0,
            unevaluated_rows=1,
            conclusion_quantities={"符合能效1级要求": 1},
            sheets=[{"sheet_name": "变压器", "data_row_count": 1,
                     "evaluated_quantity": 6, "total_quantity": 6,
                     "conclusion_quantities": {"2级": 6}, "sheet_id": "transformer"}],
            unprocessed_sheets=("电动机",),
            issues=[SimpleNamespace(row_number=8, kind="INPUT_ERROR",
                                    reason="额定容量无效", sheet_name="变压器")],
        )
        result = SimpleNamespace(
            summary=summary, result_workbook="result.xlsx",
            batch_record_saved=True, batch_record_id="batch-id",
        )
        page._render(result)
        text = page.summary_label.text() + page.issue_label.text()
        self.assertIn("变压器", text)
        self.assertIn("未处理工作表：电动机", text)
        self.assertIn("变压器 · 第 8 行", text)
        self.assertIn("变压器：共 6 台（数据 1 行）", text)
        self.assertIn("1级 0 台；2级 6 台；3级 0 台", text)
        self.assertNotIn("transformer", text)
        self.assertNotIn("MULTI", text)


if __name__ == "__main__":
    unittest.main()
