"""Phase 7 — GB19762 分析流程与历史记录最终收口（专项证据）。

产品流程（Owner，Phase 7）：

```text
选择泵型 → 填写参数 → 点击「分析」 → 显示清晰结果
         → 合法业务终态**自动**形成不可变历史记录
         → 之后从「分析记录」打开查看当时的输入、结果与依据
```
"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from equipeffi.application.lifecycle.errors import (
    AnalysisError,
    LifecyclePersistenceError,
)
from equipeffi.application.services.centrifugal_pump_analysis_service import (
    PUMP_CATEGORIES,
    PumpAnalysisRequest,
    category_field_constraints,
)
from equipeffi.composition import create_pump_analysis_service
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.presentation.qt.pages.analysis import (
    SYSTEM_FAILURE_TEXT,
    AnalysisPage,
    format_display_number,
)
from equipeffi.presentation.qt.pages.records import RecordsPage

ROOT = Path(__file__).resolve().parents[2]

#: 8 个正式泵型（不含"其他类别"/"不确定类别"）。
FORMAL_CATEGORIES: tuple[str, ...] = tuple(
    c.visible_name for c in PUMP_CATEGORIES if c.special is None)

SINGLE_STAGE_LOCKED = (
    "单级单吸清水离心泵", "单级双吸清水离心泵",
    "管道清水离心泵", "单级石油化工离心泵")
SUCTION_LOCKED = {
    "单级单吸清水离心泵": "单吸",
    "单级双吸清水离心泵": "双吸",
    "单级石油化工离心泵": "单吸",
}
STAGES_FREE = (
    "多级清水离心泵", "轻型多级清水离心泵（立式）",
    "轻型多级清水离心泵（卧式）", "多级石油化工离心泵")

#: 每个正式泵型的一组可用取值。
CATEGORY_VALUES: dict[str, dict[str, str]] = {
    "单级单吸清水离心泵": {"QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "80"},
    "单级双吸清水离心泵": {"QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "80"},
    "管道清水离心泵": {"QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "80"},
    "多级清水离心泵": {"QBEP": "100", "HBEP": "100", "speed": "2900",
                       "efficiency": "80", "stages": "2"},
    "轻型多级清水离心泵（立式）": {"QBEP": "100", "HBEP": "100", "speed": "2900",
                                   "efficiency": "80", "stages": "2"},
    "轻型多级清水离心泵（卧式）": {"QBEP": "100", "HBEP": "100", "speed": "2900",
                                   "efficiency": "80", "stages": "2"},
    "单级石油化工离心泵": {"QBEP": "100", "HBEP": "14", "speed": "2900", "efficiency": "73"},
    "多级石油化工离心泵": {"QBEP": "100", "HBEP": "30", "speed": "2900",
                           "efficiency": "73", "stages": "2"},
}


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


class Phase7TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.paths = AppDataPaths(Path(self.tmp.name))
        self.service = create_pump_analysis_service(paths=self.paths)
        self.addCleanup(self.tmp.cleanup)

    def page(self, **kwargs) -> AnalysisPage:
        page = AnalysisPage(self.service, **kwargs)
        self.addCleanup(page.deleteLater)
        return page

    def fill(self, page: AnalysisPage, category: str) -> None:
        values = CATEGORY_VALUES[category]
        page.category.setCurrentIndex(page.category.findData(category))
        for key in ("QBEP", "HBEP", "speed", "efficiency"):
            page.point_inputs[key].setText(values.get(key, ""))
        suction = SUCTION_LOCKED.get(category, "单吸")
        page.suction.setCurrentIndex(page.suction.findData(suction))
        if page.stages.isEnabled():
            page.stages.setText(values.get("stages", "1"))


# --------------------------------------------------------------------------
# 1. 8 个正式泵型的类别联动
# --------------------------------------------------------------------------

class CategoryFieldLockingTests(Phase7TestCase):
    def test_all_eight_formal_categories_are_locked_correctly(self):
        page = self.page()
        for category in FORMAL_CATEGORIES:
            with self.subTest(category=category):
                page.category.setCurrentIndex(page.category.findData(category))
                constraints = category_field_constraints(category)

                if category in SINGLE_STAGE_LOCKED:
                    self.assertFalse(page.stages.isEnabled())
                    self.assertEqual(page.stages.text(), "1")
                    self.assertEqual(constraints.get("stages"), "1")
                else:
                    # 多级泵的级数由用户填写（类别未唯一决定具体级数）
                    self.assertTrue(page.stages.isEnabled())
                    self.assertNotIn("stages", constraints)

                locked_suction = SUCTION_LOCKED.get(category)
                if locked_suction is not None:
                    self.assertFalse(page.suction.isEnabled())
                    self.assertEqual(page.suction.currentData(), locked_suction)
                else:
                    # 管道清水泵 / 多级泵：类别未唯一决定吸入方式
                    self.assertTrue(page.suction.isEnabled())
                    self.assertNotIn("suction", constraints)

    def test_locked_values_cannot_be_overridden_by_the_user(self):
        """锁定字段的输入被忽略：不依赖控件状态，请求里强制取权威值。"""

        page = self.page()
        page.category.setCurrentIndex(page.category.findData("单级双吸清水离心泵"))
        # 试图把吸入方式改成"单吸"、级数改成 3
        page.suction.setCurrentIndex(page.suction.findData("单吸"))
        page.stages.setText("3")
        request = page._collect_request()
        self.assertEqual(request.suction, "双吸")
        self.assertEqual(request.stages, "1")

    def test_pipeline_pump_keeps_stage_locked_but_suction_selectable(self):
        """"管道清水离心泵"类别名不含单吸/双吸 → 只锁级数，不猜吸入方式。"""

        page = self.page()
        page.category.setCurrentIndex(page.category.findData("管道清水离心泵"))
        self.assertFalse(page.stages.isEnabled())
        self.assertTrue(page.suction.isEnabled())
        self.assertEqual(category_field_constraints("管道清水离心泵"), {"stages": "1"})

    def test_lock_notice_is_shown_to_the_user(self):
        page = self.page()
        page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
        hint = page.locked_hint.text()
        self.assertIn("级数 = 1", hint)
        self.assertIn("吸入方式 = 单吸", hint)

    def test_every_formal_category_can_complete_an_analysis(self):
        page = self.page()
        for category in FORMAL_CATEGORIES:
            with self.subTest(category=category):
                self.fill(page, category)
                result = page.evaluate()
                self.assertIsNotNone(result, category)
                self.assertIn(result.evaluation_status,
                              ("SUCCESS", "OUT_OF_STANDARD_SCOPE", "INSUFFICIENT_DATA"))


# --------------------------------------------------------------------------
# 2/3/4. 普通页面没有草稿 / 日期输入 / 保存按钮 / 技术详情
# --------------------------------------------------------------------------

class OrdinaryPageSurfaceTests(Phase7TestCase):
    def test_page_has_no_draft_concept(self):
        page = self.page()
        for name in ("draft_name", "draft_list", "draft_status", "save_draft",
                     "new_draft", "refresh_drafts", "load_selected_draft",
                     "delete_selected_draft", "save_draft_button",
                     "new_draft_button", "load_draft_button",
                     "delete_draft_button", "refresh_drafts_button"):
            with self.subTest(attribute=name):
                self.assertFalse(hasattr(page, name))

    def test_page_has_no_evaluation_date_input(self):
        page = self.page()
        self.assertFalse(hasattr(page, "as_of"))
        labels = [w.text() for w in page.findChildren(QLabel)]
        self.assertNotIn("评价日期", "\n".join(labels))

    def test_page_has_no_manual_save_button(self):
        page = self.page()
        self.assertFalse(hasattr(page, "finalize_button"))
        self.assertFalse(hasattr(page, "finalize"))
        buttons = [b.text() for b in page.findChildren(QPushButton)]
        self.assertNotIn("保存为正式记录", buttons)

    def test_page_has_no_technical_detail_section(self):
        page = self.page()
        self.assertFalse(hasattr(page, "technical_box"))
        self.assertFalse(hasattr(page, "technical"))

    def test_no_draft_wording_is_visible_anywhere(self):
        page = self.page()
        blob = "\n".join([w.text() for w in page.findChildren(QLabel)]
                         + [b.text() for b in page.findChildren(QPushButton)])
        for word in ("草稿", "保存草稿", "新建草稿", "载入", "技术详情"):
            with self.subTest(word=word):
                self.assertNotIn(word, blob)


# --------------------------------------------------------------------------
# 5. as_of 自动取本机当天
# --------------------------------------------------------------------------

class EvaluationDateTests(Phase7TestCase):
    def test_as_of_defaults_to_local_today(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        request = page._collect_request()
        self.assertEqual(request.as_of, date.today())

    def test_as_of_is_recorded_for_traceability(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        page.evaluate()
        record = self.service.open_record(page.last_saved_record_id)
        self.assertEqual(record.as_of, date.today().isoformat())

    def test_mismatched_date_only_warns_and_never_blocks(self):
        """评价日期不是业务门禁：早于实施日仍计算、仍记录。"""

        page = self.page(as_of=date(2026, 2, 28))
        self.fill(page, "单级单吸清水离心泵")
        result = page.evaluate()
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertIn("该标准尚未实施", result.warnings)
        self.assertEqual(page.last_record_status, "RECORDED")


# --------------------------------------------------------------------------
# 6/7. 自动形成 Record / 非法与异常不形成 / 连续分析不覆盖
# --------------------------------------------------------------------------

class AutoRecordTests(Phase7TestCase):
    def test_legal_terminal_state_is_recorded_automatically(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        page.evaluate()
        self.assertEqual(page.last_record_status, "RECORDED")
        self.assertIsNotNone(page.last_saved_record_id)
        self.assertEqual(len(self.service.list_records()), 1)
        self.assertIn("已自动保存为历史记录", page.record_label.text())

    def test_out_of_standard_scope_is_recorded(self):
        """「其他类别」是类别级正式结论（白名单内），也应自动形成记录。"""

        page = self.page()
        page.category.setCurrentIndex(page.category.findData("其他类别"))
        result = page.evaluate()
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(page.last_record_status, "RECORDED")
        self.assertEqual(len(self.service.list_records()), 1)

    def test_insufficient_data_is_recorded(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        page.point_inputs["efficiency"].clear()
        result = page.evaluate()
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(page.last_record_status, "RECORDED")

    def test_invalid_input_is_not_recorded(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        page.point_inputs["efficiency"].setText("abc")
        result = page.evaluate()
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertEqual(page.last_record_status, "NOT_RECORDED")
        self.assertEqual(self.service.list_records(), [])

    def test_unresolved_category_is_not_recorded(self):
        page = self.page()
        page.category.setCurrentIndex(page.category.findData("不确定类别"))
        page.evaluate()
        self.assertEqual(page.last_record_status, "NOT_RECORDED")
        self.assertEqual(self.service.list_records(), [])

    def test_consecutive_analyses_create_distinct_records(self):
        page = self.page()
        ids = []
        for efficiency in ("80", "85", "90"):
            self.fill(page, "单级单吸清水离心泵")
            page.point_inputs["efficiency"].setText(efficiency)
            page.evaluate()
            ids.append(page.last_saved_record_id)
        self.assertEqual(len(set(ids)), 3)
        records = self.service.list_records()
        self.assertEqual(len(records), 3)
        # 历史记录不被覆盖：每条都保留当时的输入
        self.assertEqual(
            {self.service.open_record(i).input_snapshot["efficiency"] for i in ids},
            {"80", "85", "90"})

    def test_record_save_failure_is_distinguished_from_success(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        with patch.object(self.service, "finalize",
                          side_effect=LifecyclePersistenceError("disk full")):
            result = page.evaluate()
        self.assertIsNotNone(result)                       # 计算结果确实产生了
        self.assertEqual(page.last_record_status, "SAVE_FAILED")
        self.assertIsNone(page.last_saved_record_id)
        self.assertIn("保存失败", page.record_label.text())
        self.assertNotIn("已自动保存", page.record_label.text())
        self.assertEqual(self.service.list_records(), [])

    def test_stale_result_protection_is_preserved_in_the_application(self):
        """自动固化不放宽任何既有安全门禁（指纹 / 白名单 / provenance）。"""

        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        request = page._collect_request()
        result = self.service.evaluate(request)
        page.point_inputs["efficiency"].setText("70")
        changed = page._collect_request()
        with self.assertRaises(AnalysisError):
            self.service.finalize(record_id="R-stale", workspace_id=None,
                                  request=changed, result=result)


# --------------------------------------------------------------------------
# 8. 2 位小数显示，不改底层精度
# --------------------------------------------------------------------------

class DisplayPrecisionTests(Phase7TestCase):
    def test_display_formatter_keeps_two_decimals(self):
        from decimal import Decimal

        self.assertEqual(format_display_number("79.786165"), "79.79")
        self.assertEqual(format_display_number(Decimal("13.6250")), "13.62")
        self.assertEqual(format_display_number("100"), "100.00")
        self.assertEqual(format_display_number(None), "—")
        self.assertEqual(format_display_number("abc"), "abc")

    def test_ordinary_result_uses_two_decimals(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        result = page.evaluate()
        raw = (result.extra_metrics or {}).get("泵效率_%")
        self.assertIsNotNone(raw)
        self.assertIn(format_display_number(raw), page.values_label.text())

    def test_underlying_precision_is_unaffected(self):
        """显示格式化不得回写业务值：Result / 快照保持完整精度。"""

        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        result = page.evaluate()
        record = self.service.open_record(page.last_saved_record_id)
        derived_result = (result.calculation_trace or {}).get("derived") or {}
        derived_snapshot = (record.result_snapshot.get("calculation_trace") or {}).get("derived") or {}
        self.assertEqual(derived_result, derived_snapshot)
        # 至少存在一个超过 2 位小数的真实派生值（证明未被提前 ROUND）
        long_values = [str(v) for v in derived_result.values() if "." in str(v)]
        self.assertTrue(any(len(str(v).split(".")[1]) > 2 for v in long_values),
                        derived_result)

    def test_thresholds_keep_original_precision_in_snapshot(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        result = page.evaluate()
        record = self.service.open_record(page.last_saved_record_id)
        self.assertEqual(record.result_snapshot.get("thresholds"), result.thresholds)
        # 某个阈值应保留超过 2 位小数（标准原始精度）
        self.assertTrue(any(len(str(v).split(".")[-1]) > 2
                            for v in result.thresholds.values()), result.thresholds)


# --------------------------------------------------------------------------
# 9/10. 历史 Record 自足、Reopen 不重算、系统异常不伪装
# --------------------------------------------------------------------------

class HistoryRecordTests(Phase7TestCase):
    def _make_record(self, record_id: str = "P7-H1") -> str:
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        page.project_name.setText("示例项目")
        page.equipment_no.setText("P-001")
        page.evaluate()
        return page.last_saved_record_id

    def test_record_detail_is_self_sufficient(self):
        record_id = self._make_record()
        page = RecordsPage(self.service)
        text = page.show_record(record_id)
        for expected in ("评价日期", "企业/项目名称：示例项目", "设备编号：P-001",
                         "设备类别：单级单吸清水离心泵", "评价结论", "能效等级",
                         "规定点流量", "原标准依据", "标准表", "标准条款"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_record_detail_hides_internal_identifiers(self):
        record_id = self._make_record()
        page = RecordsPage(self.service)
        text = page.show_record(record_id)
        for token in ("pump_water", "pump_chemical", "rule_profile",
                      "matched_rule_id", "pack_hash", "numeric_profile_id",
                      "workspace_id", "schema_version"):
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_reopen_never_calls_the_evaluator(self):
        """Reopen 硬规则：把 evaluator 工厂 patch 为 raise，open_record 仍必须成功。"""

        record_id = self._make_record()
        page = RecordsPage(self.service)
        with patch("equipeffi.domain.evaluation.evaluator_registry.EVALUATOR_FACTORIES",
                   side_effect=AssertionError("Reopen 不得调用 evaluator")):
            text = page.show_record(record_id)
        self.assertIn(record_id, text)

    def test_frozen_result_survives_canonical_changes(self):
        """旧 Record 按原快照展示，不因当前 Canonical / evaluator 改动而漂移。"""

        record_id = self._make_record()
        before = self.service.open_record(record_id)
        with patch.object(self.service, "evaluate",
                          side_effect=AssertionError("Reopen 不得重算")):
            after = self.service.open_record(record_id)
        self.assertEqual(before.result_snapshot, after.result_snapshot)
        self.assertEqual(before.input_snapshot, after.input_snapshot)

    def test_legacy_record_without_basis_fields_degrades_gracefully(self):
        """历史旧 Record 缺少新依据字段：可正常打开并降级显示，不崩溃。"""

        from types import SimpleNamespace

        page = RecordsPage(self.service)
        snapshot = SimpleNamespace(
            record_id="LEGACY-1", standard_code="GB 19762-2025",
            product_category="单级单吸清水离心泵", as_of="2026-08-23",
            ui_conclusion="1级", grade="1",
            input_snapshot={"QBEP": "100", "HBEP": "50", "speed": "2900",
                            "efficiency": "80", "suction": "单吸", "stages": "1",
                            "request_fingerprint": "FP"},
            result_snapshot={"thresholds": {}, "calculation_trace": {},
                             "evaluation_status": "SUCCESS",
                             "support_status": "SUPPORTED"},
            reference_snapshot={"standard": {}},      # 旧 Record：没有依据字段
            evaluation_status="SUCCESS", ruleset_version="pump_water",
            canonical_version="", numeric_profile_id="",
            canonical_package_hash="", result_contract_version="",
            finalized_at_utc="2026-08-23T00:00:00+00:00")
        with patch.object(self.service, "open_record", return_value=snapshot):
            text = page.show_record("LEGACY-1")
        self.assertIn("LEGACY-1", text)
        self.assertIn("该历史记录保存时未包含完整标准依据。", text)


class SystemFailureSeparationTests(Phase7TestCase):
    def test_system_exception_is_not_disguised_as_a_business_state(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")

        def _boom(_request):
            raise RuntimeError("模拟内部执行错误")

        page.service.evaluate = _boom
        self.assertIsNone(page.evaluate())
        self.assertEqual(page.summary.text(), SYSTEM_FAILURE_TEXT)
        for forbidden in ("无法判定", "资料不足", "不适用"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, page.summary.text())

    def test_system_exception_creates_no_record(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")

        def _boom(_request):
            raise RuntimeError("模拟内部执行错误")

        page.service.evaluate = _boom
        page.evaluate()
        self.assertEqual(self.service.list_records(), [])

    def test_insufficient_data_user_text_is_about_missing_material(self):
        page = self.page()
        self.fill(page, "单级单吸清水离心泵")
        page.point_inputs["efficiency"].clear()
        result = page.evaluate()
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertNotEqual(page.summary.text(), SYSTEM_FAILURE_TEXT)
        # 资料不足是业务终态：可以形成记录
        self.assertEqual(page.last_record_status, "RECORDED")


# --------------------------------------------------------------------------
# Phase 7 不得引入的东西
# --------------------------------------------------------------------------

class Phase7ScopeGuardTests(Phase7TestCase):
    def test_no_migration_or_schema_change(self):
        import subprocess

        changed = subprocess.run(
            ["git", "diff", "--name-only",
             "6ead21fb6757d5d92ba81851f23e3c41d86598af", "HEAD",
             "--", "src/equipeffi/infrastructure/persistence/"],
            cwd=ROOT, capture_output=True, text=True, check=False).stdout.split()
        self.assertEqual(changed, [], f"records 持久化层被改动：{changed}")

    def test_no_reproduce_attempt_or_audit_framework(self):
        qt_dir = ROOT / "src" / "equipeffi" / "presentation" / "qt"
        names = {p.stem for p in qt_dir.rglob("*.py")}
        for forbidden in ("reproduce", "attempt", "lineage", "audit_framework"):
            with self.subTest(name=forbidden):
                self.assertNotIn(forbidden, names)

    def test_records_page_has_no_recalculate_entry(self):
        page = RecordsPage(self.service)
        buttons = [b.text() for b in page.findChildren(QPushButton)]
        for forbidden in ("重新计算", "重新分析", "基于此记录"):
            with self.subTest(word=forbidden):
                self.assertFalse(any(forbidden in text for text in buttons), buttons)


if __name__ == "__main__":
    unittest.main()
