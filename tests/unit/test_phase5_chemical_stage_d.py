"""Phase 5：pump_chemical Stage D 支持提升候选与发布门禁收口。

覆盖：

- **发布门禁**：统一正式产品路径（Qt `--qt` 所用入口）对 `pump_chemical`
  返回 `SUPPORTED`（支持提升候选），且分类目录/未定 Profile 不受影响；
- **业务行为不变**：单级/多级石化泵 × 正常等级 / OUT_OF_STANDARD_SCOPE /
  INSUFFICIENT_DATA / INVALID_INPUT 的 `evaluation_status` 与等级不受门禁影响；
- **历史 Record 冻结**：Phase 3/4 期间形成的、`result_snapshot.support_status`
  为 `NOT_IN_RELEASE_SCOPE` 的 chemical Record，Reopen 后仍为原值，
  不得追溯改成 `SUPPORTED`、不得重算、不得改写 snapshot；
- **Stage D E2E 证据**：11 条 Approved Golden 的历史业务真值经当前正式
  Application 链一致复现，且 Golden 的 `evaluation_layer` 未被改写；
- **UI 文案**：内部英文枚举不出现在普通 UI；历史 Record 显示
  "当时状态：当前版本未支持"，新结果显示"支持状态：正式支持"。
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
import sqlite3
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
)
from equipeffi.infrastructure.persistence.records_migrations import migrate_records_database
from equipeffi.infrastructure.persistence.sqlite_records_repository import (
    SqliteRecordRepository,
    SqliteWorkspaceRepository,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from equipeffi.presentation.qt.labels import (
    SUPPORT_STATUS_LABELS,
    support_status_text,
)

ROOT = Path(__file__).resolve().parents[2]
WATER = "单级单吸清水离心泵"
CHEMICAL_SINGLE = "单级石油化工离心泵"
CHEMICAL_MULTI = "多级石油化工离心泵"
AS_OF = date(2026, 8, 23)
EVIDENCE = ROOT / "specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json"
CHEMICAL_GOLDEN_DIR = ROOT / "specs/equipment_efficiency/golden/pump_chemical"

SINGLE_NORMAL = {"QBEP": "100", "HBEP": "14", "speed": "2900",
                 "efficiency": "73", "suction": "单吸", "stages": "1"}
#: 多级石化泵：级数必须 > 1（单级要求 stages=1）。
MULTI_NORMAL = {"QBEP": "100", "HBEP": "150", "speed": "2900",
                "efficiency": "71", "suction": "单吸", "stages": "3"}


def _service(db: Path | None = None) -> CentrifugalPumpAnalysisService:
    standards = JsonStandardRepository(ROOT / "src" / "equipeffi")
    if db is None:
        return CentrifugalPumpAnalysisService(standards)
    return CentrifugalPumpAnalysisService(
        standards, SqliteWorkspaceRepository(db), SqliteRecordRepository(db))


def _request(category: str, **overrides) -> PumpAnalysisRequest:
    values = dict(SINGLE_NORMAL)
    values.update(overrides)
    return PumpAnalysisRequest(category, AS_OF, **values)


class ReleaseGatePromotionTests(unittest.TestCase):
    """G02：统一正式产品路径的发布门禁提升为支持候选。"""

    def setUp(self):
        self.service = _service()

    def test_chemical_single_stage_is_supported(self):
        result = self.service.evaluate(_request(CHEMICAL_SINGLE))
        self.assertEqual(result.rule_profile, "pump_chemical")
        self.assertEqual(result.support_status, "SUPPORTED")
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.grade, "2")

    def test_chemical_multistage_is_supported(self):
        result = self.service.evaluate(
            PumpAnalysisRequest(CHEMICAL_MULTI, AS_OF, **MULTI_NORMAL))
        self.assertEqual(result.rule_profile, "pump_chemical")
        self.assertEqual(result.support_status, "SUPPORTED")
        self.assertIn(result.evaluation_status, ("SUCCESS", "OUT_OF_STANDARD_SCOPE"))

    def test_support_status_does_not_change_business_conclusions(self):
        """发布门禁维度不得改写业务判定维度。"""

        cases = {
            "normal": (_request(CHEMICAL_SINGLE), "SUCCESS"),
            "out of scope": (
                _request(CHEMICAL_SINGLE, QBEP="100", HBEP="10"), "OUT_OF_STANDARD_SCOPE"),
            "insufficient": (
                _request(CHEMICAL_SINGLE, efficiency=None), "INSUFFICIENT_DATA"),
            "invalid": (_request(CHEMICAL_SINGLE, stages="2"), "INVALID_INPUT"),
        }
        for label, (request, expected) in cases.items():
            with self.subTest(case=label):
                result = self.service.evaluate(request)
                self.assertEqual(result.support_status, "SUPPORTED")
                self.assertEqual(result.evaluation_status, expected)

    def test_water_is_unchanged(self):
        result = self.service.evaluate(_request(WATER, HBEP="50", efficiency="90"))
        self.assertEqual(result.support_status, "SUPPORTED")
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.grade, "1")

    def test_category_level_results_have_no_support_status(self):
        """类别级结论没有具体 rule profile，因此没有发布门禁取值。"""

        result = self.service.evaluate(PumpAnalysisRequest("其他类别", AS_OF))
        self.assertIsNone(result.support_status)

    def test_release_gate_decision_is_explicit(self):
        """门禁决策必须显式冻结，避免被静默改动。"""

        self.assertEqual(CentrifugalPumpAnalysisService._release_support("pump_water"),
                         "SUPPORTED")
        self.assertEqual(CentrifugalPumpAnalysisService._release_support("pump_chemical"),
                         "SUPPORTED")
        self.assertIsNone(
            CentrifugalPumpAnalysisService._release_support("transformer"))


class HistoricalRecordFreezeTests(unittest.TestCase):
    """G03：历史 Record 必须冻结当时的发布支持事实。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.db, app_version="test")
        self.service = _service(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _insert_phase3_chemical_record(self, record_id: str = "R-phase3-chem") -> str:
        """插入一条 Phase 3/4 期间形态的 chemical Record。

        当时统一门禁对 `pump_chemical` 返回 `NOT_IN_RELEASE_SCOPE`。
        """

        request = _request(CHEMICAL_SINGLE)
        current = self.service.evaluate(request)
        # 以当前结果骨架构造历史 Record，只把那时的门禁事实写回历史值
        snapshot = current.as_snapshot()
        snapshot["support_status"] = "NOT_IN_RELEASE_SCOPE"
        self.assertTrue(current.finalizable)
        record = self.service.finalize(record_id=record_id, workspace_id=None,
                                       request=request, result=current)
        # finalize 写的是当前门禁值；这里直接改库以模拟历史行
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                "UPDATE record SET result_snapshot_json = ? WHERE record_id = ?",
                (json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")), record_id),
            )
        return record_id

    def test_historical_support_status_is_not_rewritten(self):
        record_id = self._insert_phase3_chemical_record()
        reopened = self.service.open_record(record_id)
        self.assertEqual(reopened.result_snapshot["support_status"],
                         "NOT_IN_RELEASE_SCOPE",
                         "历史 Record 的支持状态不得被追溯改成 SUPPORTED")

    def test_reopen_does_not_recalculate_or_rewrite_snapshot(self):
        record_id = self._insert_phase3_chemical_record()
        with sqlite3.connect(self.db) as connection:
            before = connection.execute(
                "SELECT result_snapshot_json FROM record WHERE record_id = ?",
                (record_id,)).fetchone()[0]

        reopened = self.service.open_record(record_id)
        # Reopen 两次，且当前门禁已是 SUPPORTED，仍未改写历史快照
        self.service.open_record(record_id)

        with sqlite3.connect(self.db) as connection:
            after = connection.execute(
                "SELECT result_snapshot_json FROM record WHERE record_id = ?",
                (record_id,)).fetchone()[0]
        self.assertEqual(after, before, "Reopen 不得改写不可变 Record 快照")
        self.assertEqual(reopened.result_snapshot["support_status"],
                         "NOT_IN_RELEASE_SCOPE")
        # 业务结论仍是历史值
        self.assertEqual(reopened.evaluation_status, "SUCCESS")
        self.assertEqual(reopened.grade, "2")

    def test_new_record_carries_supported_while_history_keeps_old_value(self):
        """同一类别：新 Record 为 SUPPORTED，历史 Record 仍为旧值。"""

        historical = self._insert_phase3_chemical_record("R-historical")
        request = _request(CHEMICAL_SINGLE)
        result = self.service.evaluate(request)
        fresh = self.service.finalize(record_id="R-fresh", workspace_id=None,
                                      request=request, result=result)

        self.assertEqual(fresh.result_snapshot["support_status"], "SUPPORTED")
        self.assertEqual(self.service.open_record(historical).result_snapshot["support_status"],
                         "NOT_IN_RELEASE_SCOPE")


class SupportStatusLabelTests(unittest.TestCase):
    """G03：UI 文案。"""

    def test_labels_map_internal_values_to_chinese(self):
        self.assertEqual(support_status_text("SUPPORTED"), "正式支持")
        self.assertEqual(support_status_text("NOT_IN_RELEASE_SCOPE"), "当前版本未支持")

    def test_labels_never_expose_internal_english_enums(self):
        for value in SUPPORT_STATUS_LABELS:
            with self.subTest(value=value):
                self.assertNotIn(value, support_status_text(value))

    def test_unknown_and_missing_values_render_as_placeholder(self):
        self.assertEqual(support_status_text(None), "—")
        self.assertEqual(support_status_text(""), "—")
        self.assertEqual(support_status_text("SOMETHING_ELSE"), "—")

    def test_not_in_release_scope_enum_is_preserved(self):
        """该枚举仍服务历史 Record、其他未发布 Profile 与已登记 deviation。"""

        from equipeffi.domain.common.enums import Conclusion

        self.assertEqual(Conclusion.NOT_IN_RELEASE_SCOPE.value, "当前版本未支持")
        self.assertIn("NOT_IN_RELEASE_SCOPE", SUPPORT_STATUS_LABELS)


class StageDEvidenceTests(unittest.TestCase):
    """G04：11 条 Approved Golden 经正式 Application 链一致复现。"""

    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_evidence_covers_all_eleven_approved_cases(self):
        self.assertEqual(self.evidence["golden_case_count"], 11)
        self.assertEqual(len(self.evidence["cases"]), 11)
        case_ids = [entry["case_id"] for entry in self.evidence["cases"]]
        on_disk = sorted(path.stem for path in CHEMICAL_GOLDEN_DIR.glob("*.json"))
        self.assertEqual(sorted(case_ids), on_disk)

    def test_every_case_is_business_truth_consistent(self):
        for entry in self.evidence["cases"]:
            with self.subTest(case=entry["case_id"]):
                self.assertTrue(entry["business_truth_consistent"])

    def test_every_case_reports_supported_on_the_formal_path(self):
        for entry in self.evidence["cases"]:
            with self.subTest(case=entry["case_id"]):
                self.assertEqual(entry["formal_application_e2e"]["support_status"],
                                 "SUPPORTED")

    def test_evidence_declares_candidate_not_effective_support(self):
        self.assertEqual(self.evidence["support_promotion_status"],
                         "SUPPORT_PROMOTION_CANDIDATE")
        self.assertEqual(self.evidence["support_status_expectation"], "SUPPORTED")

    def test_historical_golden_layer_and_provenance_are_untouched(self):
        """Golden 继续表示历史批准来源：层级与 support 保持原样。"""

        for entry in self.evidence["cases"]:
            with self.subTest(case=entry["case_id"]):
                self.assertEqual(entry["golden_evaluation_layer"],
                                 "PROFILE_EVALUATOR_TECHNICAL")
                self.assertIsNone(entry["golden_support_status"])

    def test_recorded_golden_hash_still_matches_the_file(self):
        """证据记录的 Golden 文本哈希必须与当前文件一致（防真值被改写）。"""

        from hashlib import sha256

        for entry in self.evidence["cases"]:
            path = ROOT / entry["source_golden_file"]
            actual = sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest().upper()
            with self.subTest(case=entry["case_id"]):
                self.assertEqual(entry["source_golden_text_sha256"], actual)

    def test_evidence_matches_a_live_run(self):
        """证据必须能被当前代码实时复现，而不是陈旧记录。"""

        service = _service()
        for entry in self.evidence["cases"]:
            case = json.loads((ROOT / entry["source_golden_file"]).read_text("utf-8"))
            raw = case["raw_inputs"]
            request = PumpAnalysisRequest(
                raw["product_type"], AS_OF, QBEP=raw.get("QBEP"), HBEP=raw.get("HBEP"),
                speed=raw.get("speed"), efficiency=raw.get("efficiency"),
                suction=raw.get("suction"), stages=raw.get("stages"))
            result = service.evaluate(request)
            with self.subTest(case=entry["case_id"]):
                self.assertEqual(result.evaluation_status,
                                 entry["formal_application_e2e"]["evaluation_status"])
                self.assertEqual(result.grade, entry["formal_application_e2e"]["grade"])
                self.assertEqual(result.support_status, "SUPPORTED")


class QtChemicalStageDTests(unittest.TestCase):
    """G03：Qt 正式产品路径的石化泵 E2E 与支持状态展示。"""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from equipeffi.presentation.qt.pages.analysis import AnalysisPage
        from equipeffi.presentation.qt.pages.records import RecordsPage

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.db, app_version="test")
        self.service = _service(self.db)
        self.page = AnalysisPage(self.service)
        self.records = RecordsPage(self.service)

    def tearDown(self):
        self.tmp.cleanup()

    def _fill(self, category: str, values: dict) -> None:
        self.page.category.setCurrentIndex(self.page.category.findData(category))
        self.page.as_of.setText(AS_OF.isoformat())
        for key, value in values.items():
            if value is None:
                continue
            if key in self.page.point_inputs:
                self.page.point_inputs[key].setText(value)
            elif key == "stages":
                # 单级类别会把级数锁定为 1；多级类别可编辑。
                self.page.stages.setText(value)
            elif key == "suction":
                self.page.suction.setCurrentIndex(self.page.suction.findData(value))

    def test_chemical_single_and_multistage_through_the_page(self):
        for category, values in ((CHEMICAL_SINGLE, SINGLE_NORMAL),
                                 (CHEMICAL_MULTI, MULTI_NORMAL)):
            with self.subTest(category=category):
                self._fill(category, values)
                result = self.page.evaluate()
                self.assertEqual(result.rule_profile, "pump_chemical")
                self.assertEqual(result.support_status, "SUPPORTED")
                self.assertIn("支持状态：正式支持", self.page.technical.text())

    def test_chemical_support_status_is_read_only_auxiliary_information(self):
        """support_status 不得成为主业务结论。"""

        self._fill(CHEMICAL_SINGLE, SINGLE_NORMAL)
        self.page.evaluate()
        ordinary = "\n".join([self.page.conclusion.text(), self.page.summary.text(),
                              self.page.basis.text()])
        self.assertNotIn("支持状态", ordinary)
        self.assertIn("支持状态：正式支持", self.page.technical.text())

    def test_chemical_conclusion_variants_through_the_page(self):
        variants = (
            ("normal", dict(SINGLE_NORMAL), "SUCCESS"),
            ("out of scope", dict(SINGLE_NORMAL, HBEP="10"), "OUT_OF_STANDARD_SCOPE"),
            ("invalid", dict(SINGLE_NORMAL, stages="2"), "INVALID_INPUT"),
        )
        for label, values, expected in variants:
            with self.subTest(case=label):
                self._fill(CHEMICAL_SINGLE, values)
                result = self.page.evaluate()
                self.assertEqual(result.evaluation_status, expected)
                self.assertEqual(result.support_status, "SUPPORTED")

    def test_chemical_insufficient_data_through_the_page(self):
        self._fill(CHEMICAL_SINGLE, dict(SINGLE_NORMAL, efficiency=None))
        result = self.page.evaluate()
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(result.support_status, "SUPPORTED")
        self.assertTrue(result.finalizable)

    def test_historical_record_shows_the_recorded_support_state(self):
        """历史 Record 显示快照里记录的**当时**状态，不被追溯改写。"""

        request = _request(CHEMICAL_SINGLE)
        result = self.service.evaluate(request)
        record = self.service.finalize(record_id="R-qt-history", workspace_id=None,
                                       request=request, result=result)
        snapshot = result.as_snapshot() | {"support_status": "NOT_IN_RELEASE_SCOPE"}
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                "UPDATE record SET result_snapshot_json = ? WHERE record_id = ?",
                (json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")), record.record_id))

        self.records.show_record(record.record_id)
        text = self.records.technical.text()
        self.assertIn("支持状态：当前版本未支持", text)
        self.assertNotIn("正式支持", text)

    def test_new_record_shows_supported(self):
        request = _request(CHEMICAL_SINGLE)
        result = self.service.evaluate(request)
        record = self.service.finalize(record_id="R-qt-new", workspace_id=None,
                                       request=request, result=result)
        self.records.show_record(record.record_id)
        text = self.records.technical.text()
        self.assertIn("支持状态：正式支持", text)
        self.assertNotIn("未支持", text)

    def test_ordinary_page_text_does_not_expose_internal_enums(self):
        self._fill(CHEMICAL_SINGLE, SINGLE_NORMAL)
        self.page.evaluate()
        blob = "\n".join([self.page.summary.text(), self.page.basis.text(),
                          self.page.conclusion.text(), self.page.category_help.text()])
        for forbidden in ("SUPPORTED", "NOT_IN_RELEASE_SCOPE", "pump_chemical"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main()
