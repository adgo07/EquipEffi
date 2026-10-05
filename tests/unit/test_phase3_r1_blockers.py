"""Phase 3 R1：独立验收确认的 5 个 blocker 的对抗性证据。

覆盖：
- B1 Finalize 独立按 `evaluation_status` 白名单判断，与 `finalizable` 矛盾时 fail closed
- B2 Qt 每次 evaluate 前作废旧结果；异常后 finalize 必须失败且 Record 不增加
- B3 Canonical `pack_hash` 为真实 SHA-256，且 Record 的 `canonical_package_hash` 非空、
     缺失时 Finalize 拒绝
- B4 技术详情为真实可折叠控件，默认隐藏并可展开/收起
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    FINALIZABLE_STATUSES,
    AnalysisError,
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
    PumpAnalysisResult,
)
from equipeffi.infrastructure.persistence.records_migrations import migrate_records_database
from equipeffi.infrastructure.persistence.sqlite_records_repository import (
    SqliteRecordRepository,
    SqliteWorkspaceRepository,
)
from equipeffi.infrastructure.standards.json_repository import (
    JsonStandardRepository,
    repository_text_sha256,
)

ROOT = Path(__file__).resolve().parents[2]
AS_OF = date(2026, 8, 23)
WATER = "单级单吸清水离心泵"
CHEMICAL = "单级石油化工离心泵"
PUMP_JSON = ROOT / "src" / "equipeffi" / "resources" / "standards" / "pump.json"


def _service(workspaces=None, records=None) -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"), workspaces, records)


def _request(category: str = WATER, **overrides) -> PumpAnalysisRequest:
    values = {"QBEP": "100", "HBEP": "50", "speed": "2900",
              "efficiency": "90", "suction": "单吸", "stages": "1"}
    values.update(overrides)
    return PumpAnalysisRequest(category, AS_OF, **values)


def _dependent_hash() -> str:
    """独立计算 pump.json 的 SHA-256（UTF-8、CRLF→LF），不依赖被测代码。"""

    return hashlib.sha256(PUMP_JSON.read_bytes().replace(b"\r\n", b"\n")).hexdigest().upper()


def _spoof(result: PumpAnalysisResult, **changes) -> PumpAnalysisResult:
    """构造"结果对象自报与真实状态不一致"的病态结果（对抗性输入）。"""

    return replace(result, **changes)


from equipeffi.presentation.qt.pages.analysis import (  # noqa: E402
    SYSTEM_FAILURE_TEXT,
)


class _DbCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.db, app_version="test")

    def tearDown(self):
        self.tmp.cleanup()

    def _migrated_service(self) -> CentrifugalPumpAnalysisService:
        return _service(SqliteWorkspaceRepository(self.db), SqliteRecordRepository(self.db))


class FinalizeStatusWhitelistTests(_DbCase):
    """B1：Finalize 必须独立按状态白名单判断，不得只信 `result.finalizable`。"""

    def test_whitelist_contents(self):
        self.assertEqual(FINALIZABLE_STATUSES,
                         {"SUCCESS", "OUT_OF_STANDARD_SCOPE", "INSUFFICIENT_DATA"})

    def test_whitelisted_statuses_are_accepted(self):
        """白名单内的真实状态可以固化（含 OUT_OF_STANDARD_SCOPE 与 INSUFFICIENT_DATA）。"""

        service = self._migrated_service()
        cases = (
            ("success", _request(), "SUCCESS"),
            ("insufficient", _request(efficiency=None), "INSUFFICIENT_DATA"),
            ("out-of-scope", PumpAnalysisRequest(CHEMICAL, AS_OF, QBEP="100", HBEP="10",
                                                 speed="2900", efficiency="80",
                                                 suction="单吸", stages="1"),
             "OUT_OF_STANDARD_SCOPE"),
        )
        for label, request, expected in cases:
            with self.subTest(case=label):
                result = service.evaluate(request)
                self.assertEqual(result.evaluation_status, expected)
                self.assertTrue(result.finalizable)
                record = service.finalize(record_id=f"R-{label}", workspace_id=None,
                                          request=request, result=result)
                self.assertEqual(record.evaluation_status, expected)

    def test_invalid_input_with_finalizable_true_is_rejected(self):
        """INVALID_INPUT + finalizable=True → 必须拒绝（fail closed）。"""

        service = self._migrated_service()
        request = _request(efficiency="0")
        result = service.evaluate(request)
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertFalse(result.finalizable)

        forged = _spoof(result, finalizable=True)
        with self.assertRaises(AnalysisError) as ctx:
            service.finalize(record_id="R-forged-invalid", workspace_id=None,
                             request=request, result=forged)
        self.assertIn("INVALID_INPUT", str(ctx.exception))
        self.assertEqual(service.list_records(), [])

    def test_execution_error_with_finalizable_true_is_rejected(self):
        """EXECUTION_ERROR + finalizable=True → 必须拒绝。"""

        service = self._migrated_service()
        request = _request()
        result = service.evaluate(request)
        forged = _spoof(result, evaluation_status="EXECUTION_ERROR", finalizable=True)
        with self.assertRaises(AnalysisError) as ctx:
            service.finalize(record_id="R-forged-error", workspace_id=None,
                             request=request, result=forged)
        self.assertIn("EXECUTION_ERROR", str(ctx.exception))
        self.assertEqual(service.list_records(), [])

    def test_unknown_status_with_finalizable_true_is_rejected(self):
        service = self._migrated_service()
        request = _request()
        result = service.evaluate(request)
        forged = _spoof(result, evaluation_status="TOTALLY_MADE_UP", finalizable=True)
        with self.assertRaises(AnalysisError) as ctx:
            service.finalize(record_id="R-forged-unknown", workspace_id=None,
                             request=request, result=forged)
        self.assertIn("TOTALLY_MADE_UP", str(ctx.exception))
        self.assertEqual(service.list_records(), [])

    def test_none_status_with_finalizable_true_is_rejected(self):
        """None（不确定类别路径）即使自报可固化也必须拒绝。"""

        service = self._migrated_service()
        request = PumpAnalysisRequest("不确定类别", AS_OF)
        result = service.evaluate(request)
        self.assertIsNone(result.evaluation_status)
        forged = _spoof(result, finalizable=True)
        with self.assertRaises(AnalysisError):
            service.finalize(record_id="R-forged-none", workspace_id=None,
                             request=request, result=forged)
        self.assertEqual(service.list_records(), [])

    def test_success_with_finalizable_false_is_rejected(self):
        """SUCCESS + finalizable=False → 必须拒绝（矛盾时 fail closed）。"""

        service = self._migrated_service()
        request = _request()
        result = service.evaluate(request)
        forged = _spoof(result, finalizable=False, not_finalizable_reason="")
        with self.assertRaises(AnalysisError):
            service.finalize(record_id="R-forged-false", workspace_id=None,
                             request=request, result=forged)
        self.assertEqual(service.list_records(), [])

    def test_context_less_status_alone_cannot_bypass_other_checks(self):
        """白名单通过后，其余一致性检查仍然生效（顺序不得被短路）。"""

        service = self._migrated_service()
        result = service.evaluate(_request(efficiency="90"))
        with self.assertRaises(AnalysisError):
            service.finalize(record_id="R-mismatch", workspace_id=None,
                             request=_request(efficiency="70"), result=result)
        self.assertEqual(service.list_records(), [])


class CanonicalHashTests(_DbCase):
    """B3：Canonical source SHA-256 必须真实注入并进入 Record。"""

    def test_repository_hash_equals_independent_computation(self):
        expected = _dependent_hash()
        self.assertEqual(len(expected), 64)
        self.assertEqual(repository_text_sha256(PUMP_JSON.read_bytes()), expected)
        for device_type in ("pump_water", "pump_chemical"):
            with self.subTest(device=device_type):
                pack = JsonStandardRepository(ROOT / "src" / "equipeffi").get_pack(device_type)
                self.assertEqual(pack.get("pack_hash"), expected)

    def test_hash_helper_is_crlf_insensitive(self):
        """仓库既有文本哈希规则：CRLF→LF 后 SHA-256。"""

        lf = b'{\n  "a": 1\n}\n'
        crlf = b'{\r\n  "a": 1\r\n}\r\n'
        self.assertEqual(repository_text_sha256(lf), repository_text_sha256(crlf))
        self.assertNotEqual(repository_text_sha256(lf),
                            hashlib.sha256(crlf).hexdigest().upper())

    def test_record_canonical_hash_is_non_empty_and_matches(self):
        service = self._migrated_service()
        expected = _dependent_hash()
        cases = (
            ("water", _request()),
            ("chemical", PumpAnalysisRequest(CHEMICAL, AS_OF, QBEP="100", HBEP="14",
                                             speed="2900", efficiency="73",
                                             suction="单吸", stages="1")),
        )
        for label, request in cases:
            with self.subTest(case=label):
                result = service.evaluate(request)
                record = service.finalize(record_id=f"R-hash-{label}", workspace_id=None,
                                          request=request, result=result)
                self.assertTrue(record.canonical_package_hash)
                self.assertEqual(record.canonical_package_hash, expected)
                reopened = service.open_record(f"R-hash-{label}")
                self.assertEqual(reopened.canonical_package_hash, expected)
                self.assertEqual(reopened.reference_snapshot["standard"]["pack_hash"], expected)

    def test_finalize_rejects_result_without_canonical_hash(self):
        """实际执行规则集的结果若缺 hash，Finalize 必须拒绝。"""

        service = self._migrated_service()
        request = _request()
        result = service.evaluate(request)
        self.assertTrue(result.references["standard"]["pack_hash"])

        stripped_refs = dict(result.references)
        stripped_refs["standard"] = dict(result.references["standard"])
        stripped_refs["standard"]["pack_hash"] = ""
        forged = _spoof(result, references=stripped_refs)
        with self.assertRaises(AnalysisError) as ctx:
            service.finalize(record_id="R-no-hash", workspace_id=None,
                             request=request, result=forged)
        self.assertIn("Canonical", str(ctx.exception))
        self.assertEqual(service.list_records(), [])


class QtStaleResultTests(_DbCase):
    """B2：Qt 重新分析前必须作废旧结果；异常后不得保留旧 SUCCESS。"""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _page(self, category: str = WATER, service=None):
        from equipeffi.presentation.qt.pages.analysis import AnalysisPage

        svc = service or self._migrated_service()
        page = AnalysisPage(svc, as_of=AS_OF)
        page.category.setCurrentIndex(page.category.findData(category))
        return page, svc

    def _fill_water(self, page) -> None:
        page.point_inputs["QBEP"].setText("100")
        page.point_inputs["HBEP"].setText("50")
        page.point_inputs["speed"].setText("2900")
        page.point_inputs["efficiency"].setText("90")
        page.suction.setCurrentIndex(page.suction.findData("单吸"))

    def test_evaluate_clears_previous_result_before_reanalysing(self):
        """一次失败的新分析不得保留旧结果（否则旧结果会被当作新输入固化）。"""

        page, _ = self._page()
        self._fill_water(page)
        first = page.evaluate()
        self.assertEqual(first.evaluation_status, "SUCCESS")
        self.assertEqual(page.last_record_status, "RECORDED")

        # 让下一次分析在收集阶段就失败（取消产品类别）
        page.category.setCurrentIndex(0)
        self.assertIsNone(page.evaluate())
        self.assertIsNone(page._last_request)
        self.assertIsNone(page._last_result)
        self.assertIsNone(page.last_saved_record_id)
        self.assertIn("请先选择产品类别", page.summary.text())

    def test_failed_reanalysis_does_not_leave_old_success(self):
        """新分析失败后旧 SUCCESS 必须作废，且不能据此新增 Record。

        Phase 7：合法分析会自动形成 Record，因此第一次成功就已产生 1 条记录；
        关键不变量是**失败的那一次不得新增记录**。
        """

        page, svc = self._page()
        self._fill_water(page)
        self.assertEqual(page.evaluate().evaluation_status, "SUCCESS")
        self.assertEqual(len(svc.list_records()), 1)
        first_record = page.last_saved_record_id

        # 改成非法输入（效率 0 → INVALID_INPUT 路径），重新分析
        page.point_inputs["efficiency"].setText("0")
        stale = page.evaluate()
        self.assertIsNotNone(stale)
        self.assertEqual(stale.evaluation_status, "INVALID_INPUT")
        self.assertEqual(page.last_record_status, "NOT_RECORDED")
        self.assertIsNone(page.last_saved_record_id)
        # 失败的分析不得新增记录
        self.assertEqual(len(svc.list_records()), 1)
        self.assertEqual(svc.open_record(first_record).evaluation_status, "SUCCESS")

    def test_exception_during_evaluate_clears_state_and_creates_no_record(self):
        """系统异常（evaluator 崩溃）不得伪装成业务结论，也不得生成 Record。"""

        page, svc = self._page()
        self._fill_water(page)
        self.assertEqual(page.evaluate().evaluation_status, "SUCCESS")
        self.assertEqual(len(svc.list_records()), 1)

        def _boom(_request):
            raise RuntimeError("模拟 evaluator 崩溃")

        page.service.evaluate = _boom
        self.assertIsNone(page.evaluate())
        self.assertIsNone(page._last_result)
        self.assertIsNone(page.last_saved_record_id)
        # 明确显示为系统失败，而不是"无法判定"/"资料不足"
        self.assertEqual(page.summary.text(), SYSTEM_FAILURE_TEXT)
        self.assertNotIn("无法判定", page.summary.text())
        self.assertEqual(len(svc.list_records()), 1)

    def test_chemical_failed_reanalysis_does_not_leave_old_success(self):
        page, svc = self._page(CHEMICAL)
        page.point_inputs["QBEP"].setText("100")
        page.point_inputs["HBEP"].setText("14")
        page.point_inputs["speed"].setText("2900")
        page.point_inputs["efficiency"].setText("73")
        page.suction.setCurrentIndex(page.suction.findData("单吸"))
        self.assertEqual(page.evaluate().evaluation_status, "SUCCESS")
        self.assertEqual(len(svc.list_records()), 1)

        page.point_inputs["efficiency"].setText("0")
        self.assertEqual(page.evaluate().evaluation_status, "INVALID_INPUT")
        self.assertEqual(page.last_record_status, "NOT_RECORDED")
        self.assertEqual(len(svc.list_records()), 1)

    def test_chemical_exception_creates_no_record_and_is_not_a_business_state(self):
        page, svc = self._page(CHEMICAL)
        page.point_inputs["QBEP"].setText("100")
        page.point_inputs["HBEP"].setText("14")
        page.point_inputs["speed"].setText("2900")
        page.point_inputs["efficiency"].setText("73")
        page.suction.setCurrentIndex(page.suction.findData("单吸"))
        self.assertEqual(page.evaluate().evaluation_status, "SUCCESS")
        before = len(svc.list_records())

        def _boom(_request):
            raise RuntimeError("模拟 evaluator 崩溃")

        page.service.evaluate = _boom
        self.assertIsNone(page.evaluate())
        self.assertEqual(page.summary.text(), SYSTEM_FAILURE_TEXT)
        self.assertEqual(len(svc.list_records()), before)


class CollapsibleTechnicalDetailTests(_DbCase):
    """B4：技术详情必须是真实可折叠控件，默认隐藏。"""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _pages(self):
        # Owner Phase 8 R1 / UI03：记录详情也不再展示「审计信息」折叠区，
        # 因此这里没有可断言的折叠控件；底层审计数据仍保存在 Record 中
        # （由 test_phase8r1_blockers 的 UIRecordsAuditRemovalTests 证明）。
        return ()

    def test_analysis_page_has_no_technical_detail_section(self):
        """Phase 7：普通新建分析页不再展示技术详情（审计信息归记录页）。"""

        from equipeffi.presentation.qt.pages.analysis import AnalysisPage

        page = AnalysisPage(self._migrated_service(), as_of=AS_OF)
        self.assertFalse(hasattr(page, "technical_box"))
        self.assertFalse(hasattr(page, "technical"))

    def test_audit_detail_is_not_shown_on_the_records_page(self):
        """Owner Phase 8 R1 / UI03：记录详情不再展示「审计信息」区域。

        原 B4 断言的是"技术详情默认为折叠控件"。普通产品界面现在完全不再展示
        该区域，因此这里改为断言"它不存在"——底层数据仍保存在 Record 中。
        """

        from PySide6.QtWidgets import QLabel
        from equipeffi.presentation.qt.pages.records import RecordsPage

        page = RecordsPage(self._migrated_service())
        self.assertIsNone(getattr(page, "technical_box", None),
                          "不得再有可展开的审计信息折叠区")
        blob = "\n".join(label.text() for label in page.findChildren(QLabel))
        self.assertNotIn("审计信息", blob)
        self.assertNotIn("技术详情", blob)

    def test_default_visible_page_has_no_internal_identifiers(self):
        """B4 追加要求：普通默认页面不得显示内部标识。"""

        from equipeffi.presentation.qt.pages.analysis import AnalysisPage

        svc = self._migrated_service()
        page = AnalysisPage(svc, as_of=AS_OF)
        page.show()
        self.app.processEvents()
        visible_text = "\n".join([
            page.conclusion.text(), page.summary.text(), page.basis.text(),
            page.values_label.text(), page.reason_label.text(),
            page.category_help.text(), page.locked_hint.text(),
        ])
        for forbidden in ("pump_water", "pump_chemical", "profile_id", "rule_id",
                          "GB19762-T3-01", "EQUIPEFFI_PUMP_DECIMAL50_V2"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, visible_text)


if __name__ == "__main__":
    unittest.main()
