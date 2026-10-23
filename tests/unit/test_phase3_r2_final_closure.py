"""Phase 3 R2：正式分析结果的 Finalize 全状态矩阵。

表驱动覆盖全部真实 result producer；评价日期不是标准执行门禁，Finalize 权限
严格依据统一 evaluation_status 白名单。
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    FINALIZABLE_STATUSES,
    AnalysisError,
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
)
from equipeffi.infrastructure.persistence.records_migrations import migrate_records_database
from equipeffi.infrastructure.persistence.sqlite_records_repository import (
    SqliteRecordRepository,
    SqliteWorkspaceRepository,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[2]
AS_OF = date(2026, 8, 23)
WATER = "单级单吸清水离心泵"
CHEMICAL = "单级石油化工离心泵"
def _service(workspaces=None, records=None) -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"), workspaces, records)


class FinalizeStateMatrixTests(unittest.TestCase):
    """Gate 2：表驱动覆盖全部真实 result producer 的 Finalize 状态矩阵。

    **不存在任何 as_of 例外。** Owner 决定（2026-10-02）：评价日期不是标准执行门禁，
    因此 `finalizable` 严格等价于「`evaluation_status` 在统一白名单内」，
    对 15 条真实 producer 一律成立。
    """

    #: (用例标签, 请求工厂, 期望 evaluation_status, 期望 finalizable, 是否执行了 ruleset)
    def _cases(self):
        def water(**kw):
            base = {"QBEP": "100", "HBEP": "50", "speed": "2900",
                    "efficiency": "90", "suction": "单吸", "stages": "1"}
            base.update(kw)
            return PumpAnalysisRequest(WATER, AS_OF, **base)

        def chem(**kw):
            base = {"QBEP": "100", "HBEP": "14", "speed": "2900",
                    "efficiency": "73", "suction": "单吸", "stages": "1"}
            base.update(kw)
            return PumpAnalysisRequest(CHEMICAL, AS_OF, **base)

        return [
            ("water normal level 1", water(), "SUCCESS", True, True),
            ("water below minimum", water(efficiency="50"), "SUCCESS", True, True),
            ("water flow out of range", water(QBEP="3"), "OUT_OF_STANDARD_SCOPE", True, True),
            ("water missing efficiency", water(efficiency=None), "INSUFFICIENT_DATA", True, True),
            ("water missing stages", water(stages=None), "INSUFFICIENT_DATA", True, True),
            ("water missing suction", water(suction=None), "INSUFFICIENT_DATA", True, True),
            ("water stage conflict", water(stages="2"), "INVALID_INPUT", False, True),
            ("chemical normal level 2", chem(), "SUCCESS", True, True),
            ("chemical ns out of range", chem(HBEP="10", efficiency="80"),
             "OUT_OF_STANDARD_SCOPE", True, True),
            ("chemical missing stages", chem(stages=None), "INSUFFICIENT_DATA", True, True),
            ("other category", PumpAnalysisRequest("其他类别", AS_OF),
             "OUT_OF_STANDARD_SCOPE", True, False),
            ("category missing", PumpAnalysisRequest("", AS_OF),
             "INSUFFICIENT_DATA", True, False),
            ("unknown category", PumpAnalysisRequest("某未知泵", AS_OF),
             "INVALID_INPUT", False, False),
            ("uncertain category", PumpAnalysisRequest("不确定类别", AS_OF),
             None, False, False),
            # Owner 决定（2026-10-02）：评价日期不是执行门禁。
            # as_of 早于实施日期时**照常执行同一 ruleset**，业务状态与等级不变，
            # 因此它不是 INSUFFICIENT_DATA，也不构成任何 Finalize 例外。
            ("as_of before effective date", PumpAnalysisRequest(
                WATER, date(2026, 2, 28), QBEP="100", HBEP="50", speed="2900",
                efficiency="90", suction="单吸", stages="1"),
             "SUCCESS", True, True),
        ]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.db, app_version="test")
        self.service = _service(SqliteWorkspaceRepository(self.db),
                                SqliteRecordRepository(self.db))

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_producer_row_matches_status_finalizable_and_finalize(self):
        for index, (label, request, status, finalizable, ruleset) in enumerate(self._cases()):
            with self.subTest(case=label):
                result = self.service.evaluate(request)
                self.assertEqual(result.evaluation_status, status, label)
                self.assertEqual(result.finalizable, finalizable, label)
                # 统一 policy，无任何例外：
                #   finalizable == (evaluation_status 在统一白名单内)
                # `as_of` 不参与该判定（Owner 决定：评价日期不是标准执行门禁）。
                self.assertEqual(finalizable, status in FINALIZABLE_STATUSES, label)

                before = len(self.service.list_records())
                if finalizable:
                    record = self.service.finalize(
                        record_id=f"R-{index}", workspace_id=None,
                        request=request, result=result)
                    self.assertEqual(record.evaluation_status, status, label)
                    self.assertEqual(len(self.service.list_records()), before + 1, label)
                else:
                    with self.assertRaises(AnalysisError, msg=label):
                        self.service.finalize(record_id=f"R-{index}", workspace_id=None,
                                              request=request, result=result)
                    self.assertEqual(len(self.service.list_records()), before, label)

    def test_no_ruleset_rows_carry_explicit_provenance_and_no_hash(self):
        """无 ruleset 的类别级结论必须显式记录原因，且不得携带 Canonical hash。"""

        checked = 0
        for label, request, _status, _finalizable, ruleset in self._cases():
            if ruleset:
                continue
            with self.subTest(case=label):
                result = self.service.evaluate(request)
                provenance = result.provenance or {}
                self.assertFalse(provenance.get("ruleset_executed"), label)
                self.assertTrue(
                    str(provenance.get("no_ruleset_reason") or "").strip(),
                    f"{label}: 无 ruleset 时必须记录 no_ruleset_reason")
                self.assertIsNone(provenance.get("rule_profile"), label)
                self.assertFalse(
                    str(result.references.get("standard", {}).get("pack_hash", "") or "").strip(),
                    f"{label}: 未执行规则集不得携带 Canonical 包哈希")
                checked += 1
        self.assertGreater(checked, 0)

    def test_ruleset_rows_carry_hash_and_provenance(self):
        for label, request, _status, _finalizable, ruleset in self._cases():
            if not ruleset:
                continue
            with self.subTest(case=label):
                result = self.service.evaluate(request)
                provenance = result.provenance or {}
                self.assertTrue(provenance.get("ruleset_executed"), label)
                self.assertTrue(str(provenance.get("rule_profile") or "").strip(), label)
                self.assertTrue(
                    str(result.references.get("standard", {}).get("pack_hash", "") or "").strip(),
                    f"{label}: 执行了规则集就必须携带 Canonical 包哈希")

    def test_finalize_rejects_ruleset_result_without_hash(self):
        from dataclasses import replace

        request = PumpAnalysisRequest(WATER, AS_OF, QBEP="100", HBEP="50", speed="2900",
                                      efficiency="90", suction="单吸", stages="1")
        result = self.service.evaluate(request)
        references = dict(result.references)
        references["standard"] = dict(result.references["standard"])
        references["standard"]["pack_hash"] = ""
        forged = replace(result, references=references)
        with self.assertRaises(AnalysisError):
            self.service.finalize(record_id="R-nohash", workspace_id=None,
                                  request=request, result=forged)
        self.assertEqual(self.service.list_records(), [])

    def test_finalize_rejects_category_result_carrying_a_fake_hash(self):
        """无 ruleset 的结果若携带 hash，说明 provenance 被伪造，必须拒绝。"""

        from dataclasses import replace

        request = PumpAnalysisRequest("其他类别", AS_OF)
        result = self.service.evaluate(request)
        references = dict(result.references)
        references["standard"] = {"pack_hash": "DEADBEEF" * 8}
        forged = replace(result, references=references)
        with self.assertRaises(AnalysisError):
            self.service.finalize(record_id="R-fakehash", workspace_id=None,
                                  request=request, result=forged)
        self.assertEqual(self.service.list_records(), [])

    def test_finalize_rejects_category_result_without_no_ruleset_reason(self):
        from dataclasses import replace

        request = PumpAnalysisRequest("其他类别", AS_OF)
        result = self.service.evaluate(request)
        forged = replace(result, provenance={"ruleset_executed": False})
        with self.assertRaises(AnalysisError):
            self.service.finalize(record_id="R-noreason", workspace_id=None,
                                  request=request, result=forged)
        self.assertEqual(self.service.list_records(), [])

    def test_saved_category_records_expose_no_ruleset_provenance(self):
        request = PumpAnalysisRequest("其他类别", AS_OF)
        result = self.service.evaluate(request)
        record = self.service.finalize(record_id="R-other", workspace_id=None,
                                       request=request, result=result)
        snapshot = record.result_snapshot
        self.assertFalse(snapshot["provenance"]["ruleset_executed"])
        self.assertTrue(snapshot["provenance"]["no_ruleset_reason"])
        self.assertFalse(record.canonical_package_hash)
        self.assertFalse(record.rule_profile)


if __name__ == "__main__":
    unittest.main()
