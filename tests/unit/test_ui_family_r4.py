"""R4 actual Qt event, Decimal text and table viewport regressions."""
from dataclasses import replace
import unittest
from unittest.mock import patch
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent, QValidator
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QScrollArea
from tests.unit import test_ui_family_stage2 as fixtures
from tests.unit.test_batch_records_history import _snapshot
from equipeffi.infrastructure.persistence.sqlite_batch_record_repository import SqliteBatchRecordRepository
from equipeffi.composition import create_records_runtime
from equipeffi.presentation.qt.widgets.numeric_input import NumericValidator


def wheel(widget, amount=-120):
    point = widget.rect().center()
    event = QWheelEvent(QPointF(point), QPointF(widget.mapToGlobal(point)), QPoint(), QPoint(0, amount),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)
    QTest.qWait(30)


def wait_popup(combo, visible=True):
    # Windows' native combo animation delays the actual view visibility.
    for attempt in range(20):
        if combo.view().isVisible() == visible:
            return
        QTest.qWait(30)


class R4Tests(unittest.TestCase):
    setUpClass = classmethod(fixtures.UiFamilyStage2Tests.setUpClass.__func__)
    tearDown = fixtures.UiFamilyStage2Tests.tearDown
    _pump_record = fixtures.UiFamilyStage2Tests._pump_record
    _fill = fixtures.UiFamilyStage2Tests._fill

    def setUp(self):
        fixtures.UiFamilyStage2Tests.setUp(self)
        self.window.activateWindow()
        QTest.qWait(80)

    def test_category_whole_field_arrow_keyboard_and_closed_wheel(self):
        self.window.resize(560, 420)
        for code, name in (("GB 19762-2025", "analysis_page"), ("GB 20052-2024", "transformer_analysis_page"),
                           ("GB 18613-2020", "motor_analysis_page")):
            with self.subTest(code=code):
                self.window.open_analysis(standard_code=code)
                page = getattr(self.window, name)
                combo = page.category
                combo.setCurrentIndex(combo.findData("单级单吸清水离心泵") if code == "GB 19762-2025" else 1)
                scroll = page.findChild(QScrollArea)
                scroll.ensureWidgetVisible(combo, 0, 0)
                QTest.qWait(30)
                QTest.mouseClick(combo.lineEdit(), Qt.MouseButton.LeftButton, pos=combo.lineEdit().rect().center())
                wait_popup(combo)
                self.assertTrue(combo.view().isVisible())
                QTest.keyClick(combo.view(), Qt.Key.Key_Escape)
                QTest.mouseClick(combo, Qt.MouseButton.LeftButton, pos=QPoint(combo.width() - 12, combo.height() // 2))
                wait_popup(combo)
                self.assertTrue(combo.view().isVisible())
                if code == "GB 20052-2024":
                    bar = combo.view().verticalScrollBar()
                    before = bar.value()
                    wheel(combo.view().viewport())
                    self.assertGreater(bar.value(), before)
                QTest.keyClick(combo.view(), Qt.Key.Key_Escape)
                before_index = combo.currentIndex()
                before_scroll = scroll.verticalScrollBar().value()
                wheel(combo.lineEdit())
                self.assertEqual(combo.currentIndex(), before_index)
                self.assertGreater(scroll.verticalScrollBar().value(), before_scroll)
                combo.setFocus()
                QTest.keyClick(combo, Qt.Key.Key_Down)
                self.assertNotEqual(combo.currentIndex(), before_index)
                self.assertTrue(combo.isEnabled())
                combo.showPopup()
                wait_popup(combo)
                QTest.keyClick(combo.view(), Qt.Key.Key_Down)
                QTest.keyClick(combo.view(), Qt.Key.Key_Return)
                wait_popup(combo, False)
                self.assertFalse(combo.view().isVisible())
                QTest.keyClick(combo, Qt.Key.Key_Tab)
                self.assertFalse(combo.hasFocus())

    def test_numeric_actual_typing_paste_edit_and_no_invalid_record(self):
        for code, name, key in (("GB 19762-2025", "analysis_page", "QBEP"),
                                ("GB 20052-2024", "transformer_analysis_page", "capacity_kva"),
                                ("GB 18613-2020", "motor_analysis_page", "rated_output_power_kw")):
            with self.subTest(code=code):
                self.window.open_analysis(standard_code=code)
                page = getattr(self.window, name)
                page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵") if code == "GB 19762-2025" else 1)
                controls = page.point_inputs if code == "GB 19762-2025" else page.field_inputs
                edit = controls[key]
                page.findChild(QScrollArea).ensureWidgetVisible(edit, 0, 20)
                QTest.qWait(80)
                edit.clear()
                edit.setFocus()
                QTest.qWait(40)
                QTest.keyClicks(edit, "abcNaNInf")
                self.assertEqual(edit.text(), "")
                QTest.keyClicks(edit, "-1")
                self.assertEqual(edit.text(), "-")  # Never silently turns a rejected -1 into +1.
                edit.clear()
                for text in ("abc", "-2", "NaN", "Inf", "1.2.3"):
                    self.app.clipboard().setText(text)
                    QTest.qWait(25)
                    QTest.keyClick(edit, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
                    QTest.qWait(10)
                    self.assertEqual(edit.text(), "", text)
                QTest.keyClicks(edit, "0.125")
                self.assertEqual(edit.text(), "0.125")
                edit.selectAll()
                QTest.keyClick(edit, Qt.Key.Key_Backspace)
                precise = "1.1234567890123456789012345678"  # 29 digits; motor contract allows <=30.
                self.app.clipboard().setText(precise)
                QTest.qWait(25)
                QTest.keyClick(edit, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
                QTest.qWait(10)
                self.assertEqual(edit.text(), precise)
                before = [r.record_id for r in self.pump.list_records()]
                for text in ("0", "-1", "1e", "NaN", "abc"):
                    edit.setText(text)  # Programmatic/IME bypass must still be checked on analysis.
                    self.assertIsNone(page.evaluate(), text)
                    self.assertIsNone(page.last_saved_record_id)
                    self.assertTrue(edit.numeric_error.isVisibleTo(page))
                    self.assertEqual(before, [r.record_id for r in self.pump.list_records()])
                edit.setText("0")
                edit.setFocus()
                QTest.keyClick(edit, Qt.Key.Key_Tab)
                self.assertIn("大于0", edit.numeric_error.text())

    def test_existing_zero_integer_frequency_and_precision_contracts(self):
        cases = (("positive", "0", False), ("positive", "0.1", True), ("integer", "1.5", False),
                 ("integer", "1.0", True), ("even", "3", False), ("even", "10", True),
                 ("nonnegative", "0", True), ("pump_percent", "0", True), ("pump_percent", "101", False),
                 ("motor_percent", "0.5", False), ("motor_percent", "100", True))
        for mode, value, accepted in cases:
            with self.subTest(mode=mode, value=value):
                validator = NumericValidator(mode)
                self.assertEqual(validator.issue(value) is None, accepted)
        for value in ("5～120", "变频", "50/60 Hz", "5-120"):
            validator = NumericValidator("frequency", motor_field="rated_frequency_hz")
            self.assertIsNone(validator.issue(value))
            self.assertEqual(validator.validate(value, len(value))[0], QValidator.State.Acceptable)
        self.window.analysis_page.project_name.setText("名称NaN Inf都允许")
        self.assertEqual(self.window.analysis_page.project_name.text(), "名称NaN Inf都允许")
        for value in ("1e31", "1" * 31):
            self.assertIsNotNone(NumericValidator(motor_field="rated_output_power_kw").issue(value))
        long = "1." + "1234567890" * 10
        for code, page, key in (("GB 19762-2025", self.window.analysis_page, "QBEP"),
                                ("GB 20052-2024", self.window.transformer_analysis_page, "capacity_kva")):
            self.window.open_analysis(standard_code=code)
            page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵") if code == "GB 19762-2025" else 1)
            controls = page.point_inputs if code.startswith("GB 19762") else page.field_inputs
            edit = controls[key]
            page.findChild(QScrollArea).ensureWidgetVisible(edit, 0, 20)
            QTest.qWait(50)
            edit.clear()
            edit.setFocus()
            self.app.clipboard().setText(long)
            QTest.qWait(40)
            QTest.keyClick(edit, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
            QTest.qWait(20)
            self.assertEqual(controls[key].text(), long)
            self.assertTrue(controls[key].hasAcceptableInput())
        transformer = self.window.transformer_analysis_page
        for key in ("no_load_loss_w", "load_loss_w"):
            transformer.field_inputs[key].setText("0")
            self.assertTrue(transformer.field_inputs[key].hasAcceptableInput())
        self.assertEqual(transformer.conditions_group.title(), "铁芯材质和绝缘等级")
        self.window.open_analysis(standard_code="GB 18613-2020")
        motor = self.window.motor_analysis_page
        motor.category.setCurrentIndex(1)
        frequency = motor.field_inputs["rated_frequency_hz"]
        for text in ("NaN", "Inf"):
            frequency.clear()
            QTest.keyClicks(frequency, text)
            self.assertIsNone(motor.evaluate())
            self.assertIsNone(motor.last_saved_record_id)
            self.assertIn("拒绝", frequency.numeric_error.text())
            motor.category.setCurrentIndex(motor.category.findData("capacitor_start"))
            motor.category.setCurrentIndex(motor.category.findData("three_phase_induction"))
            frequency = motor.field_inputs["rated_frequency_hz"]
            self.assertIsNone(motor.evaluate())
            self.assertIn("拒绝", frequency.numeric_error.text())
            frequency.setText("5～120")
            self.assertIsNone(frequency.validator().issue(frequency.text()))

    def test_integer_editing_zero_losses_and_legal_missing_data(self):
        self.window.open_analysis(standard_code="GB 19762-2025")
        page = self.window.analysis_page
        page.category.setCurrentIndex(page.category.findData("多级清水离心泵"))
        self.assertTrue(page.stages.isEnabled())
        page.findChild(QScrollArea).ensureWidgetVisible(page.stages, 0, 20)
        QTest.qWait(60)
        page.stages.clear()
        QTest.keyClicks(page.stages, "1.5")
        self.assertIsNone(page.evaluate())
        self.assertIn("正整数", page.stages.numeric_error.text())
        page.stages.setText("2")
        # Blank point data still goes through the original legitimate missing-data path.
        result = page.evaluate()
        self.assertIsNotNone(result)
        self.assertEqual(page.last_record_status, "RECORDED")
        self.window.open_analysis(standard_code="GB 20052-2024")
        page = self.window.transformer_analysis_page
        page.category.setCurrentIndex(page.category.findData("GB20052-T03"))
        page.field_inputs["capacity_kva"].setText("3150")
        for key in ("no_load_loss_w", "load_loss_w"):
            edit = page.field_inputs[key]
            edit.clear()
            QTest.keyClicks(edit, "0")
            self.assertEqual(edit.text(), "0")
            self.assertTrue(edit.hasAcceptableInput())
        self.assertIsNotNone(page.evaluate())
        self.assertEqual(page.last_record_status, "SAVED")

    def test_frequency_ranges_keep_each_keystroke_paste_and_saved_original(self):
        self.window.open_analysis(standard_code="GB 18613-2020")
        page = self.window.motor_analysis_page
        page.category.setCurrentIndex(page.category.findData("three_phase_induction"))
        self._fill(page, dict(rated_output_power_kw="0.14", rated_voltage_kv="0.38",
                              poles="4", measured_efficiency_pct="71.43"))
        edit = page.field_inputs["rated_frequency_hz"]
        page.findChild(QScrollArea).ensureWidgetVisible(edit, 0, 20)
        QTest.qWait(80)

        def check_saved(original, analyze):
            result = page.evaluate()
            self.assertIsNotNone(result)
            self.assertEqual(result.ui_conclusion, "不在范围")
            self.assertEqual(analyze.call_args.args[0].values["rated_frequency_hz"], original)
            self.assertEqual(page.last_record_status, "SAVED")
            record = self.pump.open_record(page.last_saved_record_id)
            self.assertEqual(record.input_snapshot["rated_frequency_hz"], original)

        with patch.object(self.motor, "analyze_and_record", wraps=self.motor.analyze_and_record) as analyze:
            for original in ("5-120", "5~120", "50/60 Hz", "1e-3"):
                with self.subTest(method="keys", original=original):
                    edit.clear()
                    edit.setFocus()
                    for index, character in enumerate(original):
                        QTest.keyClicks(edit, character)
                        self.assertEqual(edit.text(), original[:index + 1])
                    check_saved(original, analyze)
            for original in ("5-120", "5～120"):
                with self.subTest(method="paste", original=original):
                    edit.clear()
                    edit.setFocus()
                    self.app.clipboard().setText(original)
                    QTest.qWait(40)
                    QTest.keyClick(edit, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
                    QTest.qWait(20)
                    self.assertEqual(edit.text(), original)
                    check_saved(original, analyze)
            edit.clear()
            QTest.keyClicks(edit, "5-120")
            for unused in range(3):
                QTest.keyClick(edit, Qt.Key.Key_Backspace)
            self.assertEqual(edit.text(), "5-")
            self.assertFalse(edit.hasAcceptableInput())
            before = [record.record_id for record in self.pump.list_records()]
            analyze.reset_mock()
            self.assertIsNone(page.evaluate())
            analyze.assert_not_called()
            self.assertIsNone(page.last_saved_record_id)
            self.assertIn("未填写完整", edit.numeric_error.text())
            self.assertEqual(before, [record.record_id for record in self.pump.list_records()])
            QTest.keyClicks(edit, "60")
            self.assertEqual(edit.text(), "5-60")
            check_saved("5-60", analyze)
        positive = self.window.transformer_analysis_page
        self.window.open_analysis(standard_code="GB 20052-2024")
        positive.category.setCurrentIndex(positive.category.findData("GB20052-T03"))
        capacity = positive.field_inputs["capacity_kva"]
        QTest.keyClicks(capacity, "-1")
        self.assertEqual(capacity.text(), "-")
        self.assertIsNone(positive.evaluate())
        self.assertIsNone(positive.last_saved_record_id)

    def test_tables_fit_all_columns_compact_and_preserve_full_long_text(self):
        record = self._pump_record()
        long_name = "超长项目名称" * 35
        record = replace(record, record_id="R4-LONG", input_snapshot=dict(record.input_snapshot, project_name=long_name))
        create_records_runtime(paths=self.paths)[1].append_record(record)
        batch_repository = SqliteBatchRecordRepository(self.paths.records_db)
        batch_repository.append_batch_record(replace(_snapshot(1), source_file_name="超长输入文件" * 35 + ".xlsx"))
        self.window.open_records()
        records = self.window.records_page
        for width, height in ((1000, 700), (1180, 800), (1440, 1000)):
            self.window.resize(width, height)
            for table, navigate in ((self.window.standards_page.table, self.window.open_standards),
                                     (records.list, lambda: (self.window.open_records(), records.single_button.click())),
                                     (records.batch_list, lambda: (self.window.open_records(), records.batch_button.click()))):
                navigate()
                for attempt in range(10):
                    QTest.qWait(30)
                    if table.horizontalScrollBar().maximum() == 0 and sum(table.columnWidth(i) for i in range(table.columnCount())) == table.viewport().width():
                        break
                self.assertEqual(table.horizontalScrollBar().maximum(), 0, (width, table.columnCount()))
                self.assertEqual(sum(table.columnWidth(i) for i in range(table.columnCount())), table.viewport().width())
                self.assertGreaterEqual(table.rowHeight(0), 48)
                self.assertTrue(table.wordWrap())
                for column in range(table.columnCount()):
                    header = table.horizontalHeaderItem(column).text()
                    self.assertLessEqual(table.horizontalHeader().fontMetrics().horizontalAdvance(header) + 8,
                                         table.columnWidth(column), header)
                last = table.columnCount() - 1
                self.assertLessEqual(table.columnViewportPosition(last) + table.columnWidth(last), table.viewport().width())
                self.assertEqual(table.item(0, 0).toolTip(), table.item(0, 0).text())
                if table.cellWidget(0, last):
                    self.assertTrue(table.cellWidget(0, last).isVisible())
        records.show_record(record.record_id)
        self.assertIn(long_name, records.detail.text())
        index = next(i for i, row in enumerate(records._visible) if row.record_id == record.record_id)
        self.assertEqual(records.list.item(index, 0).text(), long_name)
        self.assertEqual(records.list.item(index, 0).toolTip(), long_name)
        self.assertEqual(records.list.textElideMode(), Qt.TextElideMode.ElideNone)
        self.assertGreater(records.list.rowHeight(index), 48)

    def test_home_four_vertical_cards_empty_recent_table_and_navigation(self):
        self.window.resize(1000, 700)
        self.window.open_home()
        home = self.window.home_page
        QTest.qWait(40)
        self.assertEqual(home._columns, 4)
        self.assertEqual(len({button.y() for button in home.task_buttons}), 1)
        for button in home.task_buttons:
            from PySide6.QtWidgets import QLabel
            labels = button.findChildren(QLabel)
            lefts = [label.mapTo(button, QPoint()).x() for label in labels]
            self.assertEqual(set(lefts), {16})
            self.assertTrue(all(label.alignment() & Qt.AlignmentFlag.AlignLeft for label in labels))
        self.assertFalse(home.records.isVisible())
        self.assertTrue(home.record_status.isVisible())
        self.assertTrue(home.recent_card.isVisible())
        record = self._pump_record()
        self.window.open_home()
        self.assertEqual(home.records.rowCount(), 1)
        self.assertEqual(home.records.item(0, 0).text(), "历史测试项目")
        self.assertTrue(home.records.isVisible())
        QTest.mouseClick(home.records.cellWidget(0, 4), Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.records_page.stack.currentIndex(), 1)
        self.assertEqual(home._record_ids, [record.record_id])
        self.assertIn("历史测试项目", self.window.records_page.detail.text())
        self.window.open_home()
        QTest.mouseClick(home.task_buttons[0], Qt.MouseButton.LeftButton)
        self.assertTrue(self.window.standards_page.isVisible())
