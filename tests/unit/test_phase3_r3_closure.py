"""Phase 3 R3：独立验收阻塞点修复的针对性证据。

覆盖独立验收要求但此前缺失的证明：
- Finalize 不得把"新输入 + 旧结果"写入同一 Record（指纹 + 草稿修订号）
- Workspace 跨进程恢复覆盖 water、重新装配 Application、全部原始输入
- records 迁移：已有正式 Record 在 forward-only 升级后保留；失败事务回滚
- 化学生成边界：Q=3000 / >3000、ns 20/60/120/210/300 各 ±ε、16 行唯一命中
- `as_of` 新建页面默认本机当前日期
- EXECUTION_ERROR 不得 Finalize
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    AnalysisError,
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
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

WATER_DEFAULTS = {"QBEP": "100", "HBEP": "50", "speed": "2900",
                  "efficiency": "90", "suction": "单吸", "stages": "1"}


def _service(workspaces=None, records=None) -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"), workspaces, records)


def _request(category: str = WATER, **overrides) -> PumpAnalysisRequest:
    values = dict(WATER_DEFAULTS)
    values.update(overrides)
    return PumpAnalysisRequest(category, AS_OF, **values)


class _DbCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"

    def tearDown(self):
        self.tmp.cleanup()

    def _migrated_service(self) -> CentrifugalPumpAnalysisService:
        migrate_records_database(self.db, app_version="test")
        return _service(SqliteWorkspaceRepository(self.db),
                        SqliteRecordRepository(self.db))


class FinalizeConsistencyTests(_DbCase):
    """旧结果与新输入错配必须被拒绝。"""

    def test_finalize_rejects_result_whose_input_changed(self):
        service = self._migrated_service()
        result = service.evaluate(_request(efficiency="90"))
        with self.assertRaises(AnalysisError):
            service.finalize(record_id="R1", workspace_id=None,
                             request=_request(efficiency="70"), result=result)

    def test_finalize_rejects_result_whose_as_of_changed(self):
        service = self._migrated_service()
        result = service.evaluate(_request())
        with self.assertRaises(AnalysisError):
            service.finalize(
                record_id="R2", workspace_id=None,
                request=PumpAnalysisRequest(WATER, date(2026, 9, 1), **WATER_DEFAULTS),
                result=result)

    def test_finalize_rejects_result_whose_category_changed(self):
        service = self._migrated_service()
        result = service.evaluate(_request(WATER))
        with self.assertRaises(AnalysisError):
            service.finalize(record_id="R3", workspace_id=None,
                             request=_request(CHEMICAL, HBEP="14"), result=result)

    def test_finalize_rejects_stale_workspace_revision(self):
        service = self._migrated_service()
        service.create_workspace("W1", _request())
        result = service.evaluate_workspace("W1")
        # 分析之后草稿被改动 → revision 递增 → 结果过期
        service.update_workspace("W1", _request(efficiency="70"))
        stale = service.load_workspace("W1")
        with self.assertRaises(AnalysisError):
            service.finalize(record_id="R4", workspace_id="W1",
                             request=service.request_from_workspace(stale), result=result)

    def test_finalize_rejects_result_not_bound_to_workspace(self):
        """结果未绑定草稿修订号时不得写入绑定草稿的 Record。"""

        service = self._migrated_service()
        service.create_workspace("W1", _request())
        unbound = service.evaluate(_request())  # workspace_revision is None
        with self.assertRaises(AnalysisError):
            service.finalize(record_id="R5", workspace_id="W1",
                             request=service.request_from_workspace(
                                 service.load_workspace("W1")),
                             result=unbound)

    def test_finalize_accepts_matching_input_and_workspace(self):
        service = self._migrated_service()
        workspace = service.create_workspace("W1", _request())
        result = service.evaluate_workspace("W1")
        record = service.finalize(
            record_id="R6", workspace_id="W1",
            request=service.request_from_workspace(workspace), result=result)
        self.assertEqual(record.record_id, "R6")
        # 固化的是产生结果的那次输入，且带指纹与修订号
        self.assertEqual(record.input_snapshot["efficiency"], "90")
        self.assertEqual(record.input_snapshot["workspace_revision"], 1)
        self.assertEqual(record.input_snapshot["request_fingerprint"],
                         result.request_fingerprint)
        self.assertEqual(record.input_snapshot["as_of"], AS_OF.isoformat())

    def test_workspace_revision_increments_on_each_update(self):
        service = self._migrated_service()
        first = service.create_workspace("W1", _request())
        second = service.update_workspace("W1", _request(efficiency="80"))
        third = service.update_workspace("W1", _request(efficiency="70"))
        self.assertEqual([first.revision, second.revision, third.revision], [1, 2, 3])

    def test_revision_and_fingerprint_survive_reload(self):
        service = self._migrated_service()
        service.create_workspace("W1", _request(efficiency="70"))
        reloaded = service.load_workspace("W1")
        self.assertEqual(reloaded.revision, 1)
        self.assertEqual(reloaded.request_fingerprint(),
                         _request(efficiency="70").request_fingerprint())


class FinalizeExecutionErrorTests(_DbCase):
    """执行异常必须既不能伪装成业务结论，也不能 Finalize。"""

    def test_execution_error_result_is_not_finalizable(self):
        service = self._migrated_service()
        request = _request()
        result = service.evaluate(request)
        broken = result.__class__(
            **{**{f: getattr(result, f) for f in result.__dataclass_fields__},
               "evaluation_status": "EXECUTION_ERROR", "finalizable": False,
               "not_finalizable_reason": "系统执行异常，不能伪装为业务结论，也不能形成正式记录。"})
        self.assertFalse(broken.finalizable)
        with self.assertRaises(AnalysisError):
            service.finalize(record_id="E1", workspace_id=None,
                             request=request, result=broken)

    def test_finalize_flags_mapping(self):
        from equipeffi.application.services.centrifugal_pump_analysis_service import (
            FINALIZABLE_STATUSES,
        )

        self.assertEqual(FINALIZABLE_STATUSES,
                         {"SUCCESS", "OUT_OF_STANDARD_SCOPE", "INSUFFICIENT_DATA"})
        self.assertNotIn("INVALID_INPUT", FINALIZABLE_STATUSES)
        self.assertNotIn("EXECUTION_ERROR", FINALIZABLE_STATUSES)


class InsufficientDataSnapshotTests(_DbCase):
    """INSUFFICIENT_DATA 的 Record 必须自带缺失项与 issue codes。"""

    def test_insufficient_record_carries_missing_fields_and_issue_codes(self):
        service = self._migrated_service()
        request = _request(efficiency=None)  # 缺少泵效率
        result = service.evaluate(request)
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertTrue(result.finalizable)
        self.assertTrue(result.missing_fields, "缺少必填项时应给出 missing_fields")
        self.assertTrue(result.issue_codes, "缺少必填项时应给出 issue_codes")

        record = service.finalize(record_id="I1", workspace_id=None,
                                  request=request, result=result)
        snapshot = record.result_snapshot
        self.assertTrue(snapshot["missing_fields"])
        self.assertTrue(snapshot["issue_codes"])
        self.assertTrue(snapshot["explanation"])


class WorkspaceCrossProcessTests(_DbCase):
    """跨进程恢复：覆盖 water、重新装配 Application、核对全部原始输入。"""

    SENTINEL = {
        "QBEP": "123.5", "HBEP": "45.25", "speed": "2950", "efficiency": "82.5",
        "suction": "单吸", "stages": "1",
        "project_name": "跨进程-清水", "equipment_no": "P-W-001",
    }

    def _child_script(self) -> str:
        """在全新解释器中重新装配 Application 并读回草稿。

        使用 `types.SimpleNamespace` 作为 AppDataPaths 形状（不依赖 dataclass
        装饰器在 `-c` 单行脚本中的行为），并用真实文件而非 `-c` 传参。
        """

        return (
            "import json, sys\n"
            "from pathlib import Path\n"
            "from types import SimpleNamespace\n"
            f"sys.path.insert(0, r'{ROOT / 'src'}')\n"
            "from equipeffi.composition import create_pump_analysis_service\n"
            f"base = Path(r'{self.tmp.name}')\n"
            "paths = SimpleNamespace(\n"
            "    user_db=base / 'user.sqlite',\n"
            "    catalog_db=base / 'catalog.sqlite',\n"
            f"    records_db=Path(r'{self.db}'),\n"
            "    logs_dir=base / 'logs',\n"
            ")\n"
            "svc = create_pump_analysis_service(paths=paths)\n"
            f"ws = svc.load_workspace({self.WORKSPACE_ID!r})\n"
            "print(json.dumps({\n"
            "    'category': ws.product_category, 'as_of': ws.as_of,\n"
            "    'rule_profile': ws.rule_profile, 'revision': ws.revision,\n"
            "    'payload': ws.payload, 'fingerprint': ws.request_fingerprint(),\n"
            "}, ensure_ascii=False))\n"
        )

    WORKSPACE_ID = "W-water"

    def _run_child(self) -> dict:
        script = Path(self.tmp.name) / "child_reader.py"
        script.write_text(self._child_script(), encoding="utf-8", newline="\n")
        completed = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(
            completed.returncode, 0,
            f"子进程装配/读取失败:\nstdout={completed.stdout}\nstderr={completed.stderr}")
        return json.loads(completed.stdout)

    def test_water_workspace_fully_restored_in_fresh_process(self):
        service = self._migrated_service()
        request = _request(**self.SENTINEL)
        service.create_workspace(self.WORKSPACE_ID, request)
        expected_fingerprint = request.request_fingerprint()

        payload = self._run_child()

        self.assertEqual(payload["category"], WATER)
        self.assertEqual(payload["as_of"], AS_OF.isoformat())
        self.assertEqual(payload["rule_profile"], "pump_water")
        self.assertEqual(payload["revision"], 1)
        self.assertEqual(payload["fingerprint"], expected_fingerprint)
        for key, value in self.SENTINEL.items():
            with self.subTest(field=key):
                self.assertEqual(payload["payload"][key], value)

    def test_water_workspace_survives_and_can_be_evaluated_in_the_same_process(self):
        """进程内：保存草稿 → 载入 → 评价 → 固化（**不**声称跨进程）。"""

        service = self._migrated_service()
        service.create_workspace("W-rt", _request(**self.SENTINEL))
        result = service.evaluate_workspace("W-rt")
        record = service.finalize(
            record_id="R-rt", workspace_id="W-rt",
            request=service.request_from_workspace(service.load_workspace("W-rt")),
            result=result)
        self.assertEqual(record.ui_conclusion, "1级")
        reopened = service.open_record("R-rt")
        self.assertEqual(reopened.input_snapshot["equipment_no"], "P-W-001")
        self.assertEqual(reopened.input_snapshot["efficiency"], "82.5")


class ChemicalWorkspaceCrossProcessTests(_DbCase):
    """chemical 也必须具备"重新装配 Application + 全部输入"的跨进程证明。"""

    CHEMICAL_SENTINEL = {
        "QBEP": "123.5", "HBEP": "14.25", "speed": "2950", "efficiency": "73.5",
        "suction": "单吸", "stages": "1",
        "project_name": "跨进程-石化", "equipment_no": "P-C-002",
    }

    def _child_script(self, workspace_id: str) -> str:
        return (
            "import json, sys\n"
            "from pathlib import Path\n"
            "from types import SimpleNamespace\n"
            f"sys.path.insert(0, r'{ROOT / 'src'}')\n"
            "from equipeffi.composition import create_pump_analysis_service\n"
            f"base = Path(r'{self.tmp.name}')\n"
            "paths = SimpleNamespace(\n"
            "    user_db=base / 'user.sqlite',\n"
            "    catalog_db=base / 'catalog.sqlite',\n"
            f"    records_db=Path(r'{self.db}'),\n"
            "    logs_dir=base / 'logs',\n"
            ")\n"
            "svc = create_pump_analysis_service(paths=paths)\n"
            f"ws = svc.load_workspace({workspace_id!r})\n"
            # 在子进程里真的评价一次，证明恢复后的输入可驱动计算
            f"result = svc.evaluate_workspace({workspace_id!r})\n"
            "print(json.dumps({\n"
            "    'category': ws.product_category, 'as_of': ws.as_of,\n"
            "    'rule_profile': ws.rule_profile, 'revision': ws.revision,\n"
            "    'payload': ws.payload, 'fingerprint': ws.request_fingerprint(),\n"
            "    'evaluation_status': result.evaluation_status,\n"
            "    'ui_conclusion': result.ui_conclusion,\n"
            "    'grade': result.grade,\n"
            "    'missing_fields': list(result.missing_fields),\n"
            "}, ensure_ascii=False))\n"
        )

    def _run_child(self, workspace_id: str) -> dict:
        script = Path(self.tmp.name) / "chemical_child.py"
        script.write_text(self._child_script(workspace_id), encoding="utf-8", newline="\n")
        completed = subprocess.run([sys.executable, str(script)],
                                   capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(
            completed.returncode, 0,
            f"子进程失败:\nstdout={completed.stdout}\nstderr={completed.stderr}")
        return json.loads(completed.stdout)

    def test_chemical_workspace_fully_restored_in_fresh_process(self):
        service = self._migrated_service()
        request = _request(CHEMICAL, **self.CHEMICAL_SENTINEL)
        service.create_workspace("W-chem", request)

        payload = self._run_child("W-chem")

        self.assertEqual(payload["category"], CHEMICAL)
        self.assertEqual(payload["as_of"], AS_OF.isoformat())
        self.assertEqual(payload["rule_profile"], "pump_chemical")
        self.assertEqual(payload["revision"], 1)
        self.assertEqual(payload["fingerprint"], request.request_fingerprint())
        # 逐一核对**全部**输入字段，不只看其中几个
        for key, value in self.CHEMICAL_SENTINEL.items():
            with self.subTest(field=key):
                self.assertEqual(payload["payload"][key], value)
        # 恢复后的输入必须能真正驱动石化泵评价
        self.assertEqual(payload["evaluation_status"], "SUCCESS")
        self.assertEqual(payload["ui_conclusion"], "2级")
        self.assertEqual(payload["grade"], "2")
        self.assertEqual(payload["missing_fields"], [])


class RecordsMigrationPreservationTests(_DbCase):
    """forward-only 升级必须保留已有正式 Record，且失败事务整体回滚。"""

    def _seed_v1(self) -> None:
        """只应用 001，模拟迁移 002 出现之前的既有数据库。"""

        migrate_records_database(self.db, app_version="v1",
                                 migrations=(RECORDS_MIGRATIONS[0],))
        connection = sqlite3.connect(self.db)
        try:
            connection.execute(
                "INSERT INTO workspace VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("W-legacy", "GB 19762-2025", "centrifugal_pump", WATER, "pump_water",
                 AS_OF.isoformat(), json.dumps({"QBEP": "100"}, ensure_ascii=False),
                 1, "t0", "t0"))
            connection.execute(
                f"INSERT INTO record VALUES ({','.join('?' * 23)})",
                ("R-legacy", "W-legacy", "GB 19762-2025", "v1", "centrifugal_pump",
                 WATER, "pump_water", AS_OF.isoformat(), "SUCCESS", "1", "1级",
                 "{}", "{}", "{}", "pump_water", "pump_water",
                 "EQUIPEFFI_PUMP_DECIMAL50_V2", "v1", "h", "1.0", 1, "t0", "t0"))
            connection.commit()
        finally:
            connection.close()

    def test_forward_only_upgrade_preserves_existing_records(self):
        self._seed_v1()
        migrate_records_database(self.db, app_version="v2")

        connection = sqlite3.connect(self.db)
        try:
            history = connection.execute(
                f"SELECT schema_version, migration_id FROM {RECORDS_HISTORY_TABLE} "
                "ORDER BY schema_version").fetchall()
            records = connection.execute(
                "SELECT record_id, ui_conclusion, grade FROM record").fetchall()
            workspaces = connection.execute(
                "SELECT workspace_id, revision FROM workspace").fetchall()
            checksum_001 = connection.execute(
                f"SELECT checksum FROM {RECORDS_HISTORY_TABLE} WHERE schema_version = 1"
            ).fetchone()[0]
        finally:
            connection.close()

        # 历史必须与当前迁移清单逐项一致（不硬编码版本号：Phase 8 新增了
        # additive 迁移 003）；同时强制 001/002 的身份与顺序不变。
        expected_history = [(m.schema_version, m.migration_id)
                            for m in RECORDS_MIGRATIONS]
        self.assertEqual(history, expected_history)
        self.assertEqual(history[0], (1, "001_create_workspace_and_record"))
        self.assertEqual(history[1], (2, "002_add_workspace_revision"))
        self.assertEqual(records, [("R-legacy", "1级", "1")])
        self.assertEqual(workspaces, [("W-legacy", 1)])
        self.assertEqual(checksum_001, RECORDS_MIGRATIONS[0].checksum,
                         "001 的 checksum 不得改变，否则旧库会被拒绝打开")

    def test_upgrade_is_idempotent_after_002(self):
        self._seed_v1()
        migrate_records_database(self.db, app_version="v2")
        migrate_records_database(self.db, app_version="v2")
        connection = sqlite3.connect(self.db)
        try:
            count = connection.execute(
                f"SELECT COUNT(*) FROM {RECORDS_HISTORY_TABLE}").fetchone()[0]
            records = connection.execute("SELECT COUNT(*) FROM record").fetchone()[0]
        finally:
            connection.close()
        # 幂等：重复迁移不得重复登记历史（条数等于迁移清单长度，而不是固定 2）。
        self.assertEqual(count, len(RECORDS_MIGRATIONS))
        self.assertEqual(records, 1)

    def test_legacy_record_is_still_reopenable_after_upgrade(self):
        self._seed_v1()
        migrate_records_database(self.db, app_version="v2")
        service = _service(SqliteWorkspaceRepository(self.db),
                           SqliteRecordRepository(self.db))
        reopened = service.open_record("R-legacy")
        self.assertEqual(reopened.record_id, "R-legacy")
        self.assertEqual(reopened.ui_conclusion, "1级")

    def test_failed_migration_rolls_back_without_partial_state(self):
        """迁移语句中途失败时，整批不得留下半套结构或历史。"""

        bad = RecordsMigration(2, "002_broken", (
            "ALTER TABLE workspace ADD COLUMN revision INTEGER NOT NULL DEFAULT 1",
            "THIS IS NOT VALID SQL",
        ))
        migrate_records_database(self.db, app_version="v1",
                                 migrations=(RECORDS_MIGRATIONS[0],))
        with self.assertRaises(sqlite3.Error):
            migrate_records_database(self.db, app_version="v2",
                                     migrations=(RECORDS_MIGRATIONS[0], bad))

        connection = sqlite3.connect(self.db)
        try:
            history = connection.execute(
                f"SELECT schema_version FROM {RECORDS_HISTORY_TABLE}").fetchall()
            columns = [row[1] for row in connection.execute(
                "PRAGMA table_info(workspace)")]
        finally:
            connection.close()

        self.assertEqual(history, [(1,)], "失败迁移不得登记历史")
        self.assertNotIn("revision", columns, "失败迁移不得留下半套列")

    def test_migration_refuses_to_touch_other_database_names(self):
        with self.assertRaises(RecordsMigrationError):
            migrate_records_database(Path(self.tmp.name) / "user.sqlite",
                                     app_version="v2")


class ChemicalGeneratedBoundaryTests(unittest.TestCase):
    """化学表 2 的 Q / ns 生成边界与 16 行唯一命中。

    `level_offsets` 是 `单级/多级 × {5<Q≤300, Q>300} × 4 个 ns 档` 的 16 行。
    Q 分档与 ns 分档**不是独立约束**：ns 由 Q、H、n 与级数派生，所以"Q 增大"
    会改变 ns。测试必须通过反推 H 把 ns 固定在目标档位，才能真正检验 Q 分档。
    """

    @classmethod
    def setUpClass(cls):
        cls.service = _service()
        pack = JsonStandardRepository(ROOT / "src" / "equipeffi").get_pack("pump_chemical")
        cls.chemical = pack["chemical"]

    #: 类别 → (用户可见类别名, 级数)
    SINGLE = ("单级石油化工离心泵", "1")
    MULTI = ("多级石油化工离心泵", "3")

    def _evaluate(self, *, q: str, h: str, pump=None, efficiency: str = "80"):
        category, stages = pump or self.SINGLE
        return self.service.evaluate(PumpAnalysisRequest(
            category, AS_OF, QBEP=q, HBEP=h, speed="2900",
            efficiency=efficiency, suction="单吸", stages=stages))

    # -- Q 区间 ------------------------------------------------------------

    def test_flow_q5_lower_endpoint_is_exclusive(self):
        at = self._evaluate(q="5", h="50")
        above = self._evaluate(q="5.000001", h="50")
        self.assertEqual(at.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertNotEqual(above.evaluation_status, "OUT_OF_STANDARD_SCOPE")

    def test_flow_q300_boundary_separates_the_two_q_bands(self):
        """Q≤300 与 Q>300 是两条不同规则行。"""

        below = self._evaluate(q="299.999999", h="50")
        at = self._evaluate(q="300", h="50")
        above = self._evaluate(q="300.000001", h="50")
        for label, result in (("299.999999", below), ("300", at), ("300.000001", above)):
            with self.subTest(q=label):
                self.assertEqual(result.evaluation_status, "SUCCESS", label)
        self.assertEqual(at.matched_rule_id, "GB19762-R000013")
        self.assertEqual(above.matched_rule_id, "GB19762-R000017")

    def test_flow_q3000_is_in_scope_when_ns_is_held_in_band(self):
        """独立验收要求的 Q=3000 / >3000 边界。

        Q>300 档**没有 Q 上界**；但 ns 仍必须在 20~300 内。因此必须把 ns
        固定在目标档位（反推 H），否则 Q 增大会把 ns 推过 300，得到的是
        "ns 超出范围"而不是"Q 超出范围"。
        """

        for q in ("3000", "3000.000001", "30000"):
            for ns in (40.0, 90.0, 165.0, 255.0):
                head = self._head_for_ns(ns, q=float(q))
                with self.subTest(q=q, ns=ns):
                    result = self._evaluate(q=q, h=head)
                    self.assertEqual(result.evaluation_status, "SUCCESS",
                                     f"Q={q}, ns={ns} 应命中 Q>300 档")
                    self.assertIn(result.matched_rule_id,
                                  {"GB19762-R000015", "GB19762-R000016",
                                   "GB19762-R000017", "GB19762-R000018"})

    def test_large_flow_with_constant_head_falls_out_of_scope_by_ns(self):
        """Q 很大而 H 不变时，真正超范围的是 ns，不是 Q——必须在结果中体现。"""

        result = self._evaluate(q="3000", h="50")
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(result.ui_conclusion, "不适用")
        self.assertIsNone(result.matched_rule_id)

    # -- ns 端点 / ±ε：必须断言**具体规则行** -------------------------------

    #: 端点采样相对带宽的偏移量。必须远大于可达到的构造精度，否则样本落入数值噪声。
    NS_EPSILON = Decimal("1e-15")

    #: 端点构造容差。HBEP 字符串与 Decimal 计算链使端点无法被精确命中，
    #: 实测偏差可达约 2e-25；这里留一个数量级余量。仍远小于 NS_EPSILON，
    #: 因此 ±ε 样本与端点样本都无歧义。
    NS_TOLERANCE = Decimal("1e-24")

    #: "精确端点"探针相对端点的偏移。取 NS_EPSILON 的一半，既能落进目标档，
    #: 又明显不同于 ±ε 样本（避免两个用例退化成同一个点）。
    NS_EXACT_PROBE = Decimal("5e-16")

    #: 表 2 的 ns 开闭语义（标准原文）：
    #:   [20,60) ∪ [60,120) ∪ [120,210] ∪ (210,300]
    #: 即 20 含、60 不含、60 含、120 不含、120 含、210 含、210 不含、300 含。
    NS_BAND_EDGES = (20, 60, 120, 210, 300)

    #: (级数标签, Q 档标签) -> 4 个 ns 档对应的规则行。
    NS_RULE_TABLE = {
        ("单级", "q_le_300"): ("GB19762-R000011", "GB19762-R000012",
                               "GB19762-R000013", "GB19762-R000014"),
        ("单级", "q_gt_300"): ("GB19762-R000015", "GB19762-R000016",
                               "GB19762-R000017", "GB19762-R000018"),
        ("多级", "q_le_300"): ("GB19762-R000019", "GB19762-R000020",
                               "GB19762-R000021", "GB19762-R000022"),
        ("多级", "q_gt_300"): ("GB19762-R000023", "GB19762-R000024",
                               "GB19762-R000025", "GB19762-R000026"),
    }

    @classmethod
    def _ns_band_rules(cls) -> tuple[dict, dict]:
        """返回 (区间标志映射 {(min,max): flag}, 规则行映射 {data_id: (min,max)})。"""

        boundaries = cls.chemical["interval_boundaries"]["specific_speed_ns"]
        flags = {(b["min"], b["max"]): b for b in boundaries}
        spans = {row["data_id"]: (row["ns_min"], row["ns_max"])
                 for row in cls.chemical["level_offsets"]}
        return flags, spans

    @staticmethod
    def _canonical_band_index(ns: Decimal, flags: dict) -> int:
        """按 Canonical 开闭标志把 ns 归到 0..3 档——测试的独立 oracle。

        四个 ns 档恰好覆盖 [20,300] 且不重叠（端点按开闭归属相邻档），
        因此给定 ns 必须**唯一**命中一档；命中多档或不命中都是数据缺陷。
        """

        band_order = [(20, 60), (60, 120), (120, 210), (210, 300)]
        hits = []
        for index, span in enumerate(band_order):
            flag = flags.get(span)
            if flag is None:
                continue
            low, high = Decimal(span[0]), Decimal(span[1])
            lower_ok = (ns >= low) if flag.get("min_inclusive", True) else (ns > low)
            upper_ok = (ns <= high) if flag.get("max_inclusive", True) else (ns < high)
            if lower_ok and upper_ok:
                hits.append(index)
        if len(hits) != 1:
            raise AssertionError(
                f"Canonical ns 区间未唯一覆盖 ns={ns}（命中档位={hits}）")
        return hits[0]

    def _ns_of(self, *, q: str, h: str, pump) -> Decimal | None:
        result = self._evaluate(q=q, h=h, pump=pump)
        raw = result.calculation_trace["derived"].get("比转速 ns")
        return None if raw is None else Decimal(raw)

    def _head_for_exact_ns(self, target: Decimal, *, q: str, pump) -> str:
        """二分搜索 HBEP，使实际 Decimal ns 尽量接近 ``target``。

        以完整精度字符串迭代（``.50f``），避免 float 反推造成的端点漂移。
        受 HBEP 字符串与 Decimal 计算链限制，实际无法精确命中端点；
        因此期望行由 `_canonical_band_index` 对**实际达成的 ns** 推导。
        """

        low, high = Decimal("0.5"), Decimal("1000000")
        for _ in range(220):
            mid = (low + high) / 2
            ns = self._ns_of(q=q, h=f"{mid:.50f}", pump=pump)
            if ns is None:
                break
            if ns > target:
                low = mid
            else:
                high = mid
        return f"{(low + high) / 2:.50f}"

    def _assert_band_rule(self, *, target_ns: Decimal, q: str, pump,
                          rule_key: tuple[str, str], expected_band: int,
                          flags: dict) -> None:
        """在构造出的目标 ns 上断言**具体规则行**。

        期望档位由标准开闭语义显式给出（`expected_band`），期望规则行由
        `NS_RULE_TABLE` 给出——不写死绝对 rule id，从而同时校验
        "档位归属"与"档位→规则行"两层。

        同时用 `_canonical_band_index` 独立复核该 ns 确实唯一落在期望档位内。
        """

        head = self._head_for_exact_ns(target_ns, q=q, pump=pump)
        result = self._evaluate(q=q, h=head, pump=pump)
        actual = self._ns_of(q=q, h=head, pump=pump)
        detail = (f"target_ns={target_ns} actual_ns={actual} "
                  f"rule={result.matched_rule_id} status={result.evaluation_status}")
        self.assertIsNotNone(actual, f"未产生比转速：{detail}")
        self.assertLessEqual(abs(actual - target_ns), self.NS_TOLERANCE,
                             f"端点构造精度不足，样本无效：{detail}")
        self.assertEqual(self._canonical_band_index(actual, flags), expected_band,
                         f"Canonical 档位与期望不符：{detail}")
        expected = self.NS_RULE_TABLE[rule_key][expected_band]
        self.assertEqual(result.evaluation_status, "SUCCESS", detail)
        self.assertEqual(result.matched_rule_id, expected, detail)

    def test_ns_endpoints_and_epsilon_bands(self):
        """ns 端点与 ±ε 的档位归属必须与标准开闭语义一致。

        每个端点检查三个点：端点下方、端点上方（各 NS_EXACT_PROBE）、
        以及 ±NS_EPSILON 的相邻档样本。期望档位显式给出，规则行由
        NS_RULE_TABLE 推出，因此"60/120/210 附近被误分到相邻行"必然失败。
        """

        flags, _spans = self._ns_band_rules()
        pumps = {"单级": self.SINGLE, "多级": self.MULTI}
        # (端点, 下方档位, 上方档位)
        edges = ((60, 0, 1), (120, 1, 2), (210, 2, 3))
        for pump_label, q_label in self.NS_RULE_TABLE:
            q = "100" if q_label == "q_le_300" else "3000"
            pump = pumps[pump_label]
            rule_key = (pump_label, q_label)
            for edge, lower_band, upper_band in edges:
                samples = (
                    ("端点下方", Decimal(edge) - self.NS_EXACT_PROBE, lower_band),
                    ("端点上方", Decimal(edge) + self.NS_EXACT_PROBE, upper_band),
                    ("低 ε", Decimal(edge) - self.NS_EPSILON, lower_band),
                    ("高 ε", Decimal(edge) + self.NS_EPSILON, upper_band),
                )
                for label, target, band in samples:
                    with self.subTest(级数=pump_label, Q档=q_label, ns=edge, 样本=label):
                        self._assert_band_rule(target_ns=target, q=q, pump=pump,
                                               rule_key=rule_key, expected_band=band,
                                               flags=flags)
            # 下界 20 含：20-ε 超出标准范围，20+ε 属第 0 档
            with self.subTest(级数=pump_label, Q档=q_label, ns=20, 样本="低 ε"):
                self._assert_out_of_scope(Decimal(20) - self.NS_EPSILON,
                                          q=q, pump=pump)
            with self.subTest(级数=pump_label, Q档=q_label, ns=20, 样本="高 ε"):
                self._assert_band_rule(target_ns=Decimal(20) + self.NS_EPSILON, q=q,
                                       pump=pump, rule_key=rule_key,
                                       expected_band=0, flags=flags)
            # 上界 300 含：300-ε 属第 3 档，300+ε 超出标准范围
            with self.subTest(级数=pump_label, Q档=q_label, ns=300, 样本="低 ε"):
                self._assert_band_rule(target_ns=Decimal(300) - self.NS_EPSILON, q=q,
                                       pump=pump, rule_key=rule_key,
                                       expected_band=3, flags=flags)
            with self.subTest(级数=pump_label, Q档=q_label, ns=300, 样本="高 ε"):
                self._assert_out_of_scope(Decimal(300) + self.NS_EPSILON,
                                          q=q, pump=pump)

    def _assert_out_of_scope(self, target_ns: Decimal, *, q: str, pump) -> None:
        head = self._head_for_exact_ns(target_ns, q=q, pump=pump)
        result = self._evaluate(q=q, h=head, pump=pump)
        actual = self._ns_of(q=q, h=head, pump=pump)
        detail = (f"target_ns={target_ns} actual_ns={actual} status={result.evaluation_status}")
        self.assertIsNotNone(actual, detail)
        self.assertLessEqual(abs(actual - target_ns), self.NS_TOLERANCE,
                             f"端点构造精度不足，样本无效：{detail}")
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE", detail)
        self.assertEqual(result.ui_conclusion, "不适用", detail)
        self.assertIsNone(result.grade, detail)
        self.assertIsNone(result.matched_rule_id, detail)

    def test_ns_canonical_interval_flags_match_the_published_open_closed_semantics(self):
        """Canonical 的 ns 开闭标志必须与标准原文一致（防止静默翻转端点）。"""

        boundaries = self.chemical["interval_boundaries"]["specific_speed_ns"]
        expected = (
            (20, True, 60, False),
            (60, True, 120, False),
            (120, True, 210, True),
            (210, False, 300, True),
        )
        actual = tuple((b["min"], b["min_inclusive"], b["max"], b["max_inclusive"])
                       for b in boundaries)
        self.assertEqual(actual, expected)

    def test_chemical_boundary_predicate_implements_the_flags(self):
        """直接用 Canonical 端点调用区间判定，逐端点核对开闭语义。"""

        from equipeffi.domain.evaluation.evaluators.shared import _explicit_boundary_hit

        boundaries = self.chemical["interval_boundaries"]["specific_speed_ns"]
        rows = {(b["min"], b["max"]): b for b in boundaries}
        # (值, 区间下界, 区间上界, 是否命中)
        cases = (
            (Decimal("20"), 20, 60, True),      # 20 含
            (Decimal("59.999999"), 20, 60, True),
            (Decimal("60"), 20, 60, False),     # 60 不含（下一档下界含）
            (Decimal("60"), 60, 120, True),
            (Decimal("120"), 60, 120, False),   # 120 不含
            (Decimal("120"), 120, 210, True),
            (Decimal("210"), 120, 210, True),   # 210 含（本档上界闭）
            (Decimal("210"), 210, 300, False),  # 210 不含（下一档下界开）
            (Decimal("300"), 210, 300, True),   # 300 含
        )
        for value, low, high, expected in cases:
            with self.subTest(value=str(value), band=f"{low}-{high}"):
                self.assertTrue((low, high) in rows, f"缺少 {low}-{high} 区间标志")
                self.assertEqual(
                    _explicit_boundary_hit(value, low, high, boundaries), expected)

    def test_ns_inside_range_has_grade_and_rule(self):
        for ns in (20.0001, 59.9999, 60.0001, 119.9999, 120.0001,
                   209.9999, 210.0001, 299.9999):
            with self.subTest(ns=ns):
                result = self._evaluate(q="100", h=self._head_for_ns(ns))
                self.assertEqual(result.evaluation_status, "SUCCESS")
                self.assertIsNotNone(result.grade)
                self.assertIsNotNone(result.matched_rule_id)

    # -- 16 行唯一命中 ------------------------------------------------------

    def test_all_sixteen_rule_rows_are_uniquely_reachable(self):
        """16 个 offset 行必须全部可达且各自唯一命中。"""

        rows = self.chemical["level_offsets"]
        expected_ids = {row["data_id"] for row in rows}
        self.assertEqual(len(expected_ids), 16)

        ns_probes = {"ns_20_60": 40.0, "ns_60_120": 90.0,
                     "ns_120_210": 165.0, "ns_210_300": 255.0}
        q_probes = {"q_le_300": "100", "q_gt_300": "3000"}

        hits: dict[str, list[str]] = {}
        for pump_label, pump in (("单级", self.SINGLE), ("多级", self.MULTI)):
            for q_label, q in q_probes.items():
                for ns_label, ns in ns_probes.items():
                    head = self._head_for_ns(ns, q=float(q), pump=pump)
                    result = self._evaluate(q=q, h=head, pump=pump)
                    combo = f"{pump_label}/{q_label}/{ns_label}"
                    with self.subTest(combo=combo):
                        self.assertEqual(result.evaluation_status, "SUCCESS", combo)
                        self.assertIsNotNone(result.matched_rule_id, combo)
                    hits.setdefault(result.matched_rule_id, []).append(combo)

        self.assertEqual(set(hits), expected_ids,
                         f"未覆盖的规则行: {expected_ids - set(hits)}")
        for rule_id, combos in hits.items():
            with self.subTest(rule=rule_id):
                self.assertEqual(len(combos), 1, f"{rule_id} 被多个组合命中: {combos}")

    def test_stage_conflict_is_reported_not_guessed(self):
        """单级类别 + stages>1 必须报冲突，不得静默按某一级数计算。"""

        result = self._evaluate(q="100", h="50", pump=(self.SINGLE[0], "2"))
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertIn("STAGE_CATEGORY_CONFLICT", result.issue_codes)
        self.assertFalse(result.finalizable)

    def test_delta_eta_applies_only_above_210(self):
        above = self._evaluate(q="100", h=self._head_for_ns(255.0))
        middle = self._evaluate(q="100", h=self._head_for_ns(165.0))
        self.assertEqual(above.evaluation_status, "SUCCESS")
        self.assertEqual(middle.evaluation_status, "SUCCESS")
        self.assertTrue(self.chemical_uses_delta("GB19762-R000014"))
        self.assertFalse(self.chemical_uses_delta("GB19762-R000013"))
        self.assertNotEqual(above.matched_rule_id, middle.matched_rule_id)

    def chemical_uses_delta(self, rule_id: str) -> bool:
        for row in self.chemical["level_offsets"]:
            if row["data_id"] == rule_id:
                return bool(row["eta0_uses_delta"])
        raise AssertionError(f"未知规则行 {rule_id}")

    def test_single_and_multistage_use_different_rule_rows(self):
        h_single = self._head_for_ns(90.0, pump=self.SINGLE)
        h_multi = self._head_for_ns(90.0, pump=self.MULTI)
        single = self._evaluate(q="100", h=h_single, pump=self.SINGLE)
        multi = self._evaluate(q="100", h=h_multi, pump=self.MULTI)
        detail = (
            f"h_single={h_single} ns={single.calculation_trace['derived'].get('比转速 ns')} "
            f"rule={single.matched_rule_id} | "
            f"h_multi={h_multi} ns={multi.calculation_trace['derived'].get('比转速 ns')} "
            f"rule={multi.matched_rule_id} stage_count="
            f"{multi.calculation_trace['derived'].get('级数')}"
        )
        self.assertEqual(single.evaluation_status, "SUCCESS", detail)
        self.assertEqual(multi.evaluation_status, "SUCCESS", detail)
        self.assertEqual(single.matched_rule_id, "GB19762-R000012", detail)
        self.assertEqual(multi.matched_rule_id, "GB19762-R000020", detail)

    @staticmethod
    def _head_for_ns(ns: float, *, q: float = 100.0, pump=None) -> str:
        """由目标 ns 反推 HBEP（单吸 S=1，n=2900 r/min）。

        领域实现为：
            q_ns   = Q / suction_factor / 3600        （**不**除以级数）
            h_ns   = H_total / stage_count
            ns     = 3.65 · n · sqrt(q_ns) / h_ns^0.75
        因此 H_total = stage_count · h_ns。
        """

        _category, stages = pump or ChemicalGeneratedBoundaryTests.SINGLE
        stage_number = float(stages)
        q_ns = q / 3600.0
        h_ns = (3.65 * 2900.0 * (q_ns ** 0.5) / ns) ** (4.0 / 3.0)
        return f"{h_ns * stage_number:.10f}"


if __name__ == "__main__":
    unittest.main()
