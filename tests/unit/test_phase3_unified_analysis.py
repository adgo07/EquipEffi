"""Phase 3 P3-G01/G03：统一分析契约、类别路由、records 迁移、Workspace/Record/History/Reopen。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
import sqlite3

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    AnalysisError,
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
    UNCERTAIN_CATEGORY,
    category_names,
    formal_category_names,
    resolve_rule_profile,
)
from equipeffi.infrastructure.persistence.records_migrations import (
    RECORDS_HISTORY_TABLE,
    RECORDS_MIGRATIONS,
    RecordsMigration,
    RecordsMigrationError,
    migrate_records_database,
)
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
        JsonStandardRepository(ROOT / "src" / "equipeffi"), workspaces, records
    )


def _water_request(**overrides) -> PumpAnalysisRequest:
    values = dict(QBEP="100", HBEP="50", speed="2900", efficiency="90",
                  suction="单吸", stages="1")
    values.update(overrides)
    return PumpAnalysisRequest(WATER, AS_OF, **values)


class UnifiedCategoryRoutingTests(unittest.TestCase):
    def test_eight_formal_categories_are_exposed(self):
        self.assertEqual(len(formal_category_names()), 8)
        self.assertEqual(len(category_names()), 10)

    def test_each_formal_category_routes_to_exactly_one_internal_profile(self):
        expected = {
            "单级单吸清水离心泵": "pump_water",
            "单级双吸清水离心泵": "pump_water",
            "管道清水离心泵": "pump_water",
            "多级清水离心泵": "pump_water",
            "轻型多级清水离心泵（立式）": "pump_water",
            "轻型多级清水离心泵（卧式）": "pump_water",
            "单级石油化工离心泵": "pump_chemical",
            "多级石油化工离心泵": "pump_chemical",
        }
        for name, profile in expected.items():
            with self.subTest(category=name):
                self.assertEqual(resolve_rule_profile(name), profile)

    def test_routing_never_uses_substring_guessing(self):
        """未登记的合成文本不得因含“清水/化工/多级/管道”子串被猜测为任一 profile。"""

        for text in ("某多级清水化工离心泵", "清水化工两用泵", "多级清水化工泵",
                     "石油化工清水泵", "多级复合泵", "超级多级泵"):
            with self.subTest(text=text):
                self.assertIsNone(resolve_rule_profile(text), text)

    def test_registered_legacy_aliases_still_route_exactly(self):
        """已登记别名是精确匹配项，不是子串猜测；UI 不提供它们，但路由必须保持。"""

        for alias, profile in (("多级", "pump_water"), ("管道", "pump_water"),
                               ("单级单吸", "pump_water"), ("单级双吸", "pump_water"),
                               ("多级石油化工离心泵", "pump_chemical")):
            with self.subTest(alias=alias):
                self.assertEqual(resolve_rule_profile(alias), profile)

    def test_formal_categories_are_all_registered_in_domain_routing(self):
        from equipeffi.domain.evaluation.device_types import _PUMP_PRODUCT_TYPE_PROFILES

        for name in formal_category_names():
            with self.subTest(category=name):
                self.assertIn(name, _PUMP_PRODUCT_TYPE_PROFILES)

    def test_special_items_do_not_route(self):
        self.assertIsNone(resolve_rule_profile("其他类别"))
        self.assertIsNone(resolve_rule_profile(UNCERTAIN_CATEGORY))
        self.assertIsNone(resolve_rule_profile(None))
        self.assertIsNone(resolve_rule_profile(""))


class UnifiedAnalysisContractTests(unittest.TestCase):
    def setUp(self):
        self.service = _service()

    def test_water_success_uses_unified_skeleton(self):
        result = self.service.evaluate(_water_request())
        self.assertEqual(result.rule_profile, "pump_water")
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.support_status, "SUPPORTED")
        self.assertEqual(result.ui_conclusion, "1级")
        self.assertEqual(result.grade, "1")
        self.assertEqual(result.matched_rule_id, "GB19762-T3-01")
        self.assertTrue(result.finalizable)
        self.assertEqual(result.as_of, AS_OF)

    def test_chemical_computes_through_unified_service_but_stays_out_of_release_scope(self):
        """统一入口可完整评价石化泵；但 Phase 3 不得提升其 support_status。"""

        result = self.service.evaluate(PumpAnalysisRequest(
            CHEMICAL, AS_OF, QBEP="100", HBEP="14", speed="2900",
            efficiency="73", suction="单吸", stages="1"))
        self.assertEqual(result.rule_profile, "pump_chemical")
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.ui_conclusion, "2级")
        self.assertEqual(result.grade, "2")
        self.assertEqual(result.matched_rule_id, "GB19762-R000014")
        # Phase 3 硬约束：不得自行提升为 SUPPORTED
        self.assertEqual(result.support_status, "NOT_IN_RELEASE_SCOPE")

    def test_chemical_out_of_standard_scope_is_a_valid_conclusion(self):
        result = self.service.evaluate(PumpAnalysisRequest(
            CHEMICAL, AS_OF, QBEP="100", HBEP="10", speed="2900",
            efficiency="80", suction="单吸", stages="1"))
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(result.ui_conclusion, "不适用")
        self.assertIsNone(result.grade)
        self.assertTrue(result.finalizable)

    def test_uncertain_category_runs_no_calculation_and_asks_for_confirmation(self):
        result = self.service.evaluate(PumpAnalysisRequest(UNCERTAIN_CATEGORY, AS_OF))
        self.assertIsNone(result.evaluation_status)
        self.assertTrue(result.requires_category_confirmation)
        self.assertFalse(result.finalizable)
        self.assertEqual(result.calculation_trace, {})
        self.assertIn("CATEGORY_UNCERTAIN", result.issue_codes)

    def test_other_category_is_not_applicable(self):
        result = self.service.evaluate(PumpAnalysisRequest("其他类别", AS_OF))
        self.assertEqual(result.category_status, "NOT_APPLICABLE")
        self.assertEqual(result.ui_conclusion, "不适用")
        self.assertFalse(result.finalizable)

    def test_unknown_category_is_invalid_input(self):
        """填了但不认识的类别 = INVALID_INPUT（与“未填写”区分）。"""

        result = self.service.evaluate(PumpAnalysisRequest("某未知泵", AS_OF))
        self.assertEqual(result.category_status, "UNRESOLVED")
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertIn("CATEGORY_UNRESOLVED", result.issue_codes)
        self.assertNotIn("CATEGORY_MISSING", result.issue_codes)
        self.assertEqual(result.missing_fields, ())

    def test_missing_category_is_insufficient_data(self):
        """未填写类别 = INSUFFICIENT_DATA + CATEGORY_MISSING。"""

        result = self.service.evaluate(PumpAnalysisRequest("", AS_OF))
        self.assertEqual(result.category_status, "UNRESOLVED")
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertIn("CATEGORY_MISSING", result.issue_codes)
        self.assertIn("产品类别", result.missing_fields)

    def test_as_of_earlier_than_effective_date_does_not_calculate(self):
        result = self.service.evaluate(_water_request())
        self.assertTrue(result.finalizable)
        early = self.service.evaluate(PumpAnalysisRequest(
            WATER, date(2026, 2, 28), QBEP="100", HBEP="50", speed="2900",
            efficiency="90", suction="单吸", stages="1"))
        self.assertEqual(early.evaluation_status, "INSUFFICIENT_DATA")
        self.assertIn("STANDARD_NOT_YET_EFFECTIVE", early.issue_codes)
        self.assertEqual(early.calculation_trace, {})

    def test_trace_uses_user_readable_names_not_internal_keys(self):
        result = self.service.evaluate(_water_request())
        derived = result.calculation_trace["derived"]
        self.assertIn("比转速 ns", derived)
        self.assertNotIn("ns_raw", derived)
        self.assertIn("输出功率（kW）", derived)
        self.assertNotIn("output_power_kw", derived)

    def test_as_of_is_mandatory_without_implicit_default(self):
        """构造契约本身不允许省略 as_of。"""

        with self.assertRaises(TypeError):
            PumpAnalysisRequest(WATER)  # type: ignore[call-arg]


class FinalizeMatrixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.dbfile = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.dbfile, app_version="test")
        self.service = _service(SqliteWorkspaceRepository(self.dbfile),
                                SqliteRecordRepository(self.dbfile))

    def tearDown(self):
        self.tmp.cleanup()

    def test_finalize_allowed_for_success_and_out_of_scope(self):
        for label, request in (
            ("success", _water_request()),
            ("oos", PumpAnalysisRequest(CHEMICAL, AS_OF, QBEP="100", HBEP="10",
                                        speed="2900", efficiency="80",
                                        suction="单吸", stages="1")),
        ):
            with self.subTest(case=label):
                result = self.service.evaluate(request)
                self.assertTrue(result.finalizable, label)
                record = self.service.finalize(record_id=f"R-{label}", workspace_id=None,
                                               request=request, result=result)
                self.assertEqual(record.record_id, f"R-{label}")

    def test_finalize_allowed_for_insufficient_data(self):
        request = PumpAnalysisRequest(WATER, AS_OF, QBEP="100", HBEP="50",
                                      speed="2900", suction="单吸", stages="1")
        result = self.service.evaluate(request)
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertTrue(result.finalizable)
        record = self.service.finalize(record_id="R-insufficient", workspace_id=None,
                                       request=request, result=result)
        self.assertEqual(record.evaluation_status, "INSUFFICIENT_DATA")

    def test_finalize_rejected_for_invalid_input(self):
        request = _water_request(efficiency="0")
        result = self.service.evaluate(request)
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertFalse(result.finalizable)
        with self.assertRaises(AnalysisError):
            self.service.finalize(record_id="R-invalid", workspace_id=None,
                                  request=request, result=result)

    def test_finalize_rejected_for_uncertain_category(self):
        request = PumpAnalysisRequest(UNCERTAIN_CATEGORY, AS_OF)
        result = self.service.evaluate(request)
        with self.assertRaises(AnalysisError):
            self.service.finalize(record_id="R-uncertain", workspace_id=None,
                                  request=request, result=result)

    def test_record_is_immutable_and_cannot_be_overwritten(self):
        request = _water_request()
        result = self.service.evaluate(request)
        self.service.finalize(record_id="R-1", workspace_id=None, request=request, result=result)
        with self.assertRaises(AnalysisError):
            self.service.finalize(record_id="R-1", workspace_id=None,
                                  request=request, result=result)

    def test_history_lists_water_and_chemical_in_one_list(self):
        for label, request in (("water", _water_request()),
                               ("chemical", PumpAnalysisRequest(
                                   CHEMICAL, AS_OF, QBEP="100", HBEP="14", speed="2900",
                                   efficiency="73", suction="单吸", stages="1"))):
            result = self.service.evaluate(request)
            self.service.finalize(record_id=f"R-{label}", workspace_id=None,
                                  request=request, result=result)
        records = self.service.list_records()
        self.assertEqual(len(records), 2)
        profiles = {record.rule_profile for record in records}
        self.assertEqual(profiles, {"pump_water", "pump_chemical"})

    def test_reopen_does_not_call_the_evaluator(self):
        """把 evaluator 工厂替换为抛错实现后，open_record 仍必须成功。"""

        request = _water_request()
        result = self.service.evaluate(request)
        self.service.finalize(record_id="R-reopen", workspace_id=None,
                              request=request, result=result)

        from equipeffi.application.services import centrifugal_pump_analysis_service as mod

        def _boom(_rule_profile):
            raise RuntimeError("evaluator must not be called on reopen")

        original = mod.build_pump_evaluator
        mod.build_pump_evaluator = _boom
        try:
            reopened = self.service.open_record("R-reopen")
        finally:
            mod.build_pump_evaluator = original

        self.assertEqual(reopened.record_id, "R-reopen")
        self.assertEqual(reopened.ui_conclusion, "1级")
        self.assertEqual(reopened.as_of, AS_OF.isoformat())
        self.assertEqual(reopened.result_snapshot["matched_rule_id"], "GB19762-T3-01")

    def test_reopen_preserves_original_as_of_and_result_snapshot(self):
        request = _water_request()
        result = self.service.evaluate(request)
        self.service.finalize(record_id="R-asof", workspace_id=None,
                              request=request, result=result)
        snapshot = self.service.open_record("R-asof")
        self.assertEqual(snapshot.as_of, "2026-08-23")
        self.assertEqual(snapshot.result_snapshot["as_of"], "2026-08-23")
        self.assertEqual(snapshot.input_snapshot["as_of"], "2026-08-23")


class RecordsMigrationTests(unittest.TestCase):
    def setUp(self):
        # ignore_cleanup_errors: Windows 上 sqlite 文件句柄释放可能滞后于用例结束，
        # 临时目录清理不应把成功的断言变成 error。
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _db(self) -> Path:
        return Path(self.tmp.name) / "records.sqlite"

    def test_migration_is_forward_only_and_records_history(self):
        db = self._db()
        migrate_records_database(db, app_version="test")
        connection = sqlite3.connect(db)
        try:
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            history = connection.execute(
                f"SELECT schema_version, migration_id FROM {RECORDS_HISTORY_TABLE}"
            ).fetchall()
        finally:
            connection.close()
        self.assertIn("workspace", tables)
        self.assertIn("record", tables)
        self.assertIn(RECORDS_HISTORY_TABLE, tables)
        self.assertEqual(history, [(1, "001_create_workspace_and_record"),
                                   (2, "002_add_workspace_revision")])

    def test_migration_is_idempotent(self):
        db = self._db()
        migrate_records_database(db, app_version="test")
        first = _history_rows(db)
        migrate_records_database(db, app_version="test")
        migrate_records_database(db, app_version="test")
        self.assertEqual(_history_rows(db), first)

    def test_migration_refuses_other_database_names(self):
        with self.assertRaises(RecordsMigrationError):
            migrate_records_database(Path(self.tmp.name) / "user.sqlite", app_version="test")

    def test_migration_rejects_destructive_statements(self):
        destructive = RecordsMigration(2, "002_drop_record",
                                       ("DROP TABLE record",))
        with self.assertRaises(RecordsMigrationError):
            destructive.assert_additive()
        with self.assertRaises(RecordsMigrationError):
            migrate_records_database(
                self._db(), app_version="test",
                migrations=(*RECORDS_MIGRATIONS, destructive))

    def test_migration_rejects_unknown_newer_version(self):
        db = self._db()
        migrate_records_database(db, app_version="test")
        with self.assertRaises(RecordsMigrationError):
            migrate_records_database(db, app_version="test", migrations=())

    def test_migration_rejects_changed_checksum(self):
        db = self._db()
        migrate_records_database(db, app_version="test")
        tampered = (RecordsMigration(1, "001_create_workspace_and_record",
                                     ("CREATE TABLE something_else (x TEXT)",)),)
        with self.assertRaises(RecordsMigrationError):
            migrate_records_database(db, app_version="test", migrations=tampered)

    def test_records_are_not_deleted_by_workspace_delete(self):
        db = self._db()
        migrate_records_database(db, app_version="test")
        service = _service(SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
        service.create_workspace("W-1", _water_request())
        # 从草稿评价：结果绑定草稿修订号，Finalize 才能核对一致性。
        result = service.evaluate_workspace("W-1")
        service.finalize(
            record_id="R-keep", workspace_id="W-1",
            request=service.request_from_workspace(service.load_workspace("W-1")),
            result=result)
        service._workspaces.delete_workspace("W-1")
        self.assertIsNone(service.load_workspace("W-1"))
        self.assertIsNotNone(service.open_record("R-keep"))


class WorkspaceRoundTripTests(unittest.TestCase):
    def test_workspace_save_load_and_restore_all_inputs(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = Path(tmp) / "records.sqlite"
            migrate_records_database(db, app_version="test")
            service = _service(SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
            request = PumpAnalysisRequest(
                WATER, AS_OF, QBEP="123.5", HBEP="45.25", speed="2950",
                efficiency="82", suction="单吸", stages="1",
                project_name="示例项目", equipment_no="P-001")
            service.create_workspace("W-round", request)
            loaded = service.load_workspace("W-round")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.as_of, "2026-08-23")
            self.assertEqual(loaded.product_category, WATER)
            self.assertEqual(loaded.rule_profile, "pump_water")
            self.assertEqual(loaded.payload["QBEP"], "123.5")
            self.assertEqual(loaded.payload["HBEP"], "45.25")
            self.assertEqual(loaded.payload["project_name"], "示例项目")
            self.assertEqual(loaded.payload["equipment_no"], "P-001")

    def test_workspace_update_keeps_created_at(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = Path(tmp) / "records.sqlite"
            migrate_records_database(db, app_version="test")
            service = _service(SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
            first = service.create_workspace("W-upd", _water_request())
            updated = service.update_workspace(
                "W-upd", PumpAnalysisRequest(CHEMICAL, AS_OF, QBEP="100", HBEP="14",
                                             speed="2900", efficiency="73",
                                             suction="单吸", stages="1"))
            self.assertEqual(updated.created_at_utc, first.created_at_utc)
            self.assertEqual(updated.product_category, CHEMICAL)
            self.assertEqual(updated.rule_profile, "pump_chemical")

    def test_workspace_inputs_survive_a_separate_process(self):
        """跨进程恢复：进程 A 写入，进程 B 在全新解释器中读回。"""

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = Path(tmp) / "records.sqlite"
            migrate_records_database(db, app_version="test")
            service = _service(SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
            request = PumpAnalysisRequest(
                CHEMICAL, AS_OF, QBEP="100", HBEP="14", speed="2900",
                efficiency="73", suction="单吸", stages="1",
                project_name="跨进程项目", equipment_no="P-777")
            service.create_workspace("W-proc", request)

            script = (
                "import json,sys;"
                "from pathlib import Path;"
                f"sys.path.insert(0, r'{ROOT / 'src'}');"
                "from equipeffi.infrastructure.persistence.sqlite_records_repository import "
                "SqliteWorkspaceRepository;"
                f"ws = SqliteWorkspaceRepository(Path(r'{db}')).load_workspace('W-proc');"
                "print(json.dumps({'category': ws.product_category, 'as_of': ws.as_of,"
                " 'profile': ws.rule_profile, 'payload': ws.payload}, ensure_ascii=False))"
            )
            completed = subprocess.run(
                [sys.executable, "-c", script], capture_output=True, text=True,
                encoding="utf-8", check=True)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["category"], CHEMICAL)
            self.assertEqual(payload["as_of"], "2026-08-23")
            self.assertEqual(payload["profile"], "pump_chemical")
            self.assertEqual(payload["payload"]["HBEP"], "14")
            self.assertEqual(payload["payload"]["project_name"], "跨进程项目")
            self.assertEqual(payload["payload"]["equipment_no"], "P-777")


def _history_rows(db: Path):
    with sqlite3.connect(db) as connection:
        return connection.execute(
            f"SELECT schema_version, migration_id, checksum, applied_at_utc "
            f"FROM {RECORDS_HISTORY_TABLE} ORDER BY schema_version"
        ).fetchall()


if __name__ == "__main__":
    unittest.main()
