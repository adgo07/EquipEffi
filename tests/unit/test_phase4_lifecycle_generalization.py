"""Phase 4 G02 / G03：生命周期通用化的零漂移与解耦证据。

覆盖：

- **架构门禁**：`infrastructure` 不得依赖任何具体 `*_analysis_service` 产品模块；
- **向后兼容**：Phase 3 时期结构的 Workspace fixture 在 Phase 4 代码中仍可
  `load → rebuild PumpAnalysisRequest → evaluate → finalize`；
- **指纹单一事实源**：`PumpAnalysisRequest` 与 `WorkspaceSnapshot` 同源，
  且与 Phase 3 算法逐字节一致（含 `None` / 空串语义）；
- **持久化根因保留**：保存失败必须抛出带根因的生命周期错误，
  不得让调用方以为保存成功。
"""
from __future__ import annotations

import ast
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from importlib.util import resolve_name

from equipeffi.application.lifecycle import (
    LifecycleError,
    LifecyclePersistenceError,
    RecordConflictError,
    WorkspaceSnapshot,
    business_key_names,
    business_keys_metadata,
    stable_fingerprint,
)
from equipeffi.application.services.centrifugal_pump_analysis_service import (
    PUMP_FINGERPRINT_KEYS,
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
WATER = "单级单吸清水离心泵"
CHEMICAL = "单级石油化工离心泵"
AS_OF = date(2026, 8, 23)
VALUES = {"QBEP": "100", "HBEP": "50", "speed": "2900",
          "efficiency": "90", "suction": "单吸", "stages": "1"}


def _service(db: Path) -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"),
        SqliteWorkspaceRepository(db), SqliteRecordRepository(db))


class InfrastructureDecouplingGateTests(unittest.TestCase):
    """G03 架构门禁：infrastructure 不得依赖具体产品 service 模块。"""

    ROOT = ROOT

    @staticmethod
    def _imported_modules(path: Path, source_root: Path) -> list[str]:
        relative = path.relative_to(source_root).with_suffix("")
        package = ".".join(relative.parts[:-1])
        modules: list[str] = []
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    module = resolve_name("." * node.level + module, package)
                modules.extend(module + "." + alias.name for alias in node.names)
        return modules

    def test_infrastructure_does_not_import_any_product_analysis_service(self):
        directory = self.ROOT / "src" / "equipeffi" / "infrastructure"
        offenders: list[str] = []
        for path in directory.rglob("*.py"):
            for module in self._imported_modules(path, self.ROOT / "src"):
                leaf = module.rsplit(".", 1)[-1]
                # 只禁止"具体产品分析服务"这一族，不禁止 lifecle 契约本身。
                if leaf.endswith("_analysis_service"):
                    offenders.append(f"{path.relative_to(self.ROOT)} -> {module}")
        self.assertEqual(
            offenders, [],
            "infrastructure 不得依赖具体 *_analysis_service 产品模块：\n  "
            + "\n  ".join(offenders))

    def test_persistence_repositories_import_device_neutral_lifecycle_only(self):
        path = self.ROOT / "src/equipeffi/infrastructure/persistence/sqlite_records_repository.py"
        modules = self._imported_modules(path, self.ROOT / "src")
        application_imports = [m for m in modules if m.startswith("equipeffi.application")]
        self.assertTrue(application_imports, "仓储必须依赖 application 契约")
        for module in application_imports:
            with self.subTest(module=module):
                self.assertTrue(
                    module.startswith("equipeffi.application.lifecycle"),
                    f"仓储只允许依赖 application.lifecycle，实际依赖: {module}")

    def test_lifecycle_module_does_not_import_product_or_outer_layers(self):
        directory = self.ROOT / "src/equipeffi/application/lifecycle"
        forbidden = ("equipeffi.infrastructure", "equipeffi.presentation",
                     "equipeffi.domain", "sqlite3", "PySide6")
        for path in directory.rglob("*.py"):
            for module in self._imported_modules(path, self.ROOT / "src"):
                for token in forbidden:
                    with self.subTest(path=path.name, module=module):
                        self.assertFalse(module == token or module.startswith(token + "."))


class WorkspaceSnapshotIsDeviceNeutralTests(unittest.TestCase):
    """G02：生命周期模型不得知道泵专属字段。"""

    def test_lifecycle_model_source_has_no_pump_field_names(self):
        for name in ("models.py", "ports.py", "errors.py", "__init__.py"):
            source = (ROOT / "src/equipeffi/application/lifecycle" / name).read_text("utf-8")
            for token in ("QBEP", "HBEP", "suction", "stages", "pump_water",
                          "pump_chemical", "GB19762", "GB 19762"):
                with self.subTest(file=name, token=token):
                    self.assertNotIn(token, source, f"生命周期层不得出现泵专属标识 {token}")

    def test_business_key_set_is_declared_exactly_once(self):
        """业务字段集合只声明一处：pump service 的 PUMP_FINGERPRINT_KEYS。"""

        service_source = (ROOT / "src/equipeffi/application/services/"
                          "centrifugal_pump_analysis_service.py").read_text("utf-8")
        self.assertEqual(service_source.count("PUMP_FINGERPRINT_KEYS: tuple[str, ...]"), 1)
        # 字段名不得在模块里再被硬编码成第二个字面量清单
        self.assertEqual(service_source.count('"QBEP", "HBEP", "speed"'), 1)
        # 生命周期层不得出现第二处业务字段清单
        for name in ("models.py", "ports.py", "errors.py", "__init__.py"):
            lifecycle_source = (ROOT / "src/equipeffi/application/lifecycle"
                                / name).read_text("utf-8")
            self.assertNotIn('"QBEP"', lifecycle_source)

    def test_workspace_model_only_touches_keys_it_is_given(self):
        snapshot = WorkspaceSnapshot(
            workspace_id="W-neutral", standard_code="GB 19762-2025",
            device_type="centrifugal_pump", product_category="X", rule_profile=None,
            as_of=AS_OF.isoformat(), payload={"anything": "1", "else": None},
            schema_version=2, created_at_utc="c", updated_at_utc="u")
        values = snapshot.business_key_values(("anything", "else"))
        self.assertEqual(values, {"product_category": "X", "as_of": AS_OF.isoformat(),
                                  "anything": "1", "else": None})


class FingerprintSingleSourceTests(unittest.TestCase):
    """G02：单一算法 + 单一业务键来源，且与 Phase 3 逐字节一致。"""

    @staticmethod
    def _phase3_reference(values: dict) -> str:
        """Phase 3 原实现（golden 回放所用算法）的逐字复制，作为漂移基准。"""

        blob = json.dumps(values, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"))
        return sha256(blob.encode("utf-8")).hexdigest()

    def _request(self, **overrides) -> PumpAnalysisRequest:
        values = dict(VALUES)
        values.update(overrides)
        return PumpAnalysisRequest(WATER, AS_OF, **values)

    def _keys(self) -> tuple[str, ...]:
        return ("product_category", "as_of", *PUMP_FINGERPRINT_KEYS)

    def test_request_fingerprint_matches_phase3_algorithm(self):
        request = self._request()
        reference = self._phase3_reference(
            {key: str(getattr(request, key)) for key in self._keys()})
        self.assertEqual(request.request_fingerprint(), reference)

    def test_none_and_empty_string_keep_phase3_semantics(self):
        for value in (None, "", "0"):
            with self.subTest(efficiency=value):
                request = self._request(efficiency=value)
                reference = self._phase3_reference(
                    {key: str(getattr(request, key)) for key in self._keys()})
                self.assertEqual(request.request_fingerprint(), reference)
        self.assertNotEqual(self._request(efficiency=None).request_fingerprint(),
                            self._request(efficiency="").request_fingerprint())

    def test_request_and_workspace_agree_through_the_same_implementation(self):
        request = self._request()
        payload = {key: getattr(request, key) for key in PUMP_FINGERPRINT_KEYS}
        snapshot = WorkspaceSnapshot(
            workspace_id="W-same", standard_code=request.standard_code,
            device_type="centrifugal_pump", product_category=request.product_category,
            rule_profile="pump_water", as_of=request.as_of.isoformat(), payload=payload,
            schema_version=2, created_at_utc="c", updated_at_utc="u")
        self.assertEqual(snapshot.request_fingerprint(PUMP_FINGERPRINT_KEYS),
                         request.request_fingerprint())

    def test_helper_normalizes_none_exactly_like_phase3(self):
        self.assertEqual(stable_fingerprint({"a": None}),
                         self._phase3_reference({"a": "None"}))


class FingerprintHasNoProductImportCouplingTests(unittest.TestCase):
    """Phase 4 阻塞回归：指纹**不得**依赖产品 service 的导入副作用。

    独立验收在 head `855f259` 上的复现：只 import Repository 的新进程里，
    业务键注册为空 → 旧 Workspace 无参指纹漂移，且不同业务输入得到相同指纹。

    本类把该复现固定为回归：子进程**断言泵 service 未被导入**，并核对
    无参指纹与"带产品模块计算"的期望值逐字节一致、且互不碰撞。
    """

    #: Phase 4 阻塞修复后，业务键集合随快照一起持久化在该保留键下。
    GENERIC_PAYLOAD_KEYS = ("project_name", "equipment_no", "product_type")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.db, app_version="test")
        self.service = _service(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _request(self, category: str, **overrides) -> PumpAnalysisRequest:
        values = dict(VALUES)
        values.update(overrides)
        return PumpAnalysisRequest(category, AS_OF, **values)

    def test_repository_only_process_reproduces_expected_fingerprints(self):
        """新进程只加载 Repository：无参指纹必须与产品侧一致且互不碰撞。"""

        expected: dict[str, str] = {}
        for workspace_id, category, overrides in (
            ("W-water", WATER, {}),
            ("W-chem", CHEMICAL, {"HBEP": "14", "efficiency": "73"}),
            # 同一 rule profile、不同业务输入：必须得到**不同**指纹
            ("W-water-b", WATER, {"efficiency": "70"}),
        ):
            request = self._request(category, **overrides)
            self.service.create_workspace(workspace_id, request)
            expected[workspace_id] = request.request_fingerprint()

        self.assertEqual(len(set(expected.values())), 3,
                         "三种业务输入必须得到三个不同指纹（防碰撞）")

        child = (
            "import json, sys\n"
            "from pathlib import Path\n"
            f"sys.path.insert(0, r'{ROOT / 'src'}')\n"
            "from equipeffi.infrastructure.persistence.sqlite_records_repository"
            " import SqliteWorkspaceRepository\n"
            f"repo = SqliteWorkspaceRepository(Path(r'{self.db}'))\n"
            "out = {}\n"
            "for wid in ('W-water', 'W-chem', 'W-water-b'):\n"
            "    out[wid] = repo.load_workspace(wid).request_fingerprint()\n"
            "assert 'equipeffi.application.services.centrifugal_pump_analysis_service'"
            " not in sys.modules, 'pump service must not be imported'\n"
            "print(json.dumps(out))\n"
        )
        completed = subprocess.run([sys.executable, "-c", child], capture_output=True,
                                   text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0,
                         f"子进程失败:\n{completed.stdout}\n{completed.stderr}")
        actual = json.loads(completed.stdout)
        for workspace_id, value in expected.items():
            with self.subTest(workspace=workspace_id):
                self.assertEqual(actual[workspace_id], value,
                                 "只加载 Repository 时指纹不得漂移")

    def test_workspace_persists_its_own_business_key_metadata(self):
        """业务键集合必须随快照持久化，而不是靠进程内注册。"""

        self.service.create_workspace("W-meta", self._request(WATER))
        workspace = self.service.load_workspace("W-meta")
        self.assertEqual(business_key_names(workspace.payload), PUMP_FINGERPRINT_KEYS)
        self.assertEqual(workspace.request_fingerprint(), workspace.request_fingerprint(
            PUMP_FINGERPRINT_KEYS))

    def test_legacy_snapshot_requires_explicit_keys_instead_of_guessing(self):
        """Phase 4 之前的旧快照无参调用必须显式报错，而不是猜一个投影。

        缺失字段应计入 `"None"` 还是不属于该设备，从载荷无法区分；
        猜测会静默改变历史指纹（实测会拒绝 Base 本可合法固化的
        `INSUFFICIENT_DATA` 草稿）。因此必须由拥有业务知识的调用方显式传键。
        """

        request = self._request(WATER)
        payload = request.raw_values() | {
            "project_name": request.project_name,
            "equipment_no": request.equipment_no,
        }
        self.assertNotIn("_business_keys", payload)
        legacy = WorkspaceSnapshot(
            workspace_id="W-legacy", standard_code="GB 19762-2025",
            device_type="centrifugal_pump", product_category=WATER,
            rule_profile="pump_water", as_of=AS_OF.isoformat(), payload=payload,
            schema_version=2, created_at_utc="c", updated_at_utc="u")
        with self.assertRaises(LifecycleError):
            legacy.request_fingerprint()
        self.assertEqual(legacy.request_fingerprint(PUMP_FINGERPRINT_KEYS),
                         request.request_fingerprint())

    def test_lifecycle_module_has_no_ambient_registration(self):
        """生命周期层不得再提供全局可变注册点。"""

        for name in ("models.py", "ports.py", "errors.py", "__init__.py"):
            source = (ROOT / "src/equipeffi/application/lifecycle" / name).read_text("utf-8")
            with self.subTest(file=name):
                self.assertNotIn("register_business_keys", source)
                self.assertNotIn("_registered_business_keys", source)
                self.assertNotIn("global ", source)


class Phase3WorkspaceFixtureCompatibilityTests(unittest.TestCase):
    """G02 向后兼容：Phase 3 结构的 Workspace fixture 必须仍然可用。"""

    #: Phase 3 P3-G03 建库时的 workspace 建表语句（逐字复制，不随 Phase 4 变化）。
    PHASE3_WORKSPACE_DDL = """
        CREATE TABLE workspace (
            workspace_id TEXT PRIMARY KEY,
            standard_code TEXT NOT NULL,
            device_type TEXT NOT NULL,
            product_category TEXT NOT NULL,
            rule_profile TEXT,
            as_of TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1
        )
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        # 用**真实 migration** 建库，确认 schema 未变
        migrate_records_database(self.db, app_version="test")

    def tearDown(self):
        self.tmp.cleanup()

    def test_recorded_phase3_workspace_schema_is_unchanged(self):
        """当前 migration 建出的 workspace 列必须与 Phase 3 fixture 完全一致。"""

        with sqlite3.connect(self.db) as connection:
            actual = [row[1] for row in
                      connection.execute("PRAGMA table_info(workspace)").fetchall()]
        expected = ["workspace_id", "standard_code", "device_type", "product_category",
                    "rule_profile", "as_of", "payload_json", "schema_version",
                    "created_at_utc", "updated_at_utc", "revision"]
        self.assertEqual(actual, expected)
        with sqlite3.connect(self.db) as connection:
            version = connection.execute(
                "SELECT MAX(schema_version) FROM record_schema_migration_history"
            ).fetchone()[0]
        # Phase 4 的语义不变量是「既有 workspace / record 列契约不变、
        # Phase 3 已创建的数据库仍可打开」。Phase 8 经 Owner 授权新增了
        # **additive** 迁移（003 `batch_record` 表、004 扩充其列），
        # 因此最高版本等于迁移链长度；这不违反 Phase 4 的不变量。
        # 依据迁移清单推导，避免每次新增 additive 迁移都产生假回归。
        from equipeffi.infrastructure.persistence.records_migrations import (
            RECORDS_MIGRATIONS,
        )

        self.assertEqual(int(version), len(RECORDS_MIGRATIONS),
                         "records schema_version 应等于迁移链长度")
        self.assertEqual([(m.schema_version, m.migration_id)
                          for m in RECORDS_MIGRATIONS][:2],
                         [(1, "001_create_workspace_and_record"),
                          (2, "002_add_workspace_revision")])
        with sqlite3.connect(self.db) as connection:
            record_columns = [row[1] for row in
                              connection.execute("PRAGMA table_info(record)").fetchall()]
        self.assertEqual(len(record_columns), 23, "record 表列契约不得改变")

    def _insert_phase3_workspace_row(self, workspace_id: str, revision: int = 1) -> None:
        """直接写入 Phase 3 形态的行，模拟"Phase 3 已创建数据库"。

        载荷额外带上 Phase 4 起持久化的业务键元数据（`_business_keys`），
        这与 Phase 3 同属既有 `payload_json` 列，**不涉及新增列或迁移**。
        """

        request = PumpAnalysisRequest(WATER, AS_OF, **VALUES)
        payload = {key: getattr(request, key) for key in PUMP_FINGERPRINT_KEYS}
        payload.update(business_keys_metadata(PUMP_FINGERPRINT_KEYS))
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                """
                INSERT INTO workspace (
                    workspace_id, standard_code, device_type, product_category,
                    rule_profile, as_of, payload_json, schema_version,
                    created_at_utc, updated_at_utc, revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, "GB 19762-2025", "centrifugal_pump", WATER, "pump_water",
                 AS_OF.isoformat(),
                 json.dumps(payload, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")),
                 2, "2026-08-23T00:00:00Z", "2026-08-23T00:00:00Z", revision),
            )

    def test_phase3_workspace_loads_rebuilds_evaluates_and_finalizes(self):
        """Phase 3 Workspace fixture：load → rebuild → evaluate → finalize 全通。"""

        self._insert_phase3_workspace_row("W-phase3")
        service = _service(self.db)

        workspace = service.load_workspace("W-phase3")
        self.assertIsNotNone(workspace, "Phase 3 结构的历史草稿必须能被读回")
        self.assertEqual(workspace.workspace_id, "W-phase3")
        self.assertEqual(workspace.payload["QBEP"], "100")
        self.assertEqual(workspace.revision, 1)

        request = service.request_from_workspace(workspace)
        self.assertEqual(request.product_category, WATER)
        self.assertEqual(request.as_of, AS_OF)
        self.assertEqual(request.efficiency, "90")

        # 指纹必须与 Phase 3 逐字节一致，否则历史草稿会被判成"已改动"
        expected = PumpAnalysisRequest(WATER, AS_OF, **VALUES).request_fingerprint()
        self.assertEqual(workspace.request_fingerprint(), expected)
        self.assertEqual(request.request_fingerprint(), expected)

        result = service.evaluate_workspace("W-phase3")
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.grade, "1")

        record = service.finalize(record_id="R-phase3", workspace_id="W-phase3",
                                  request=request, result=result)
        self.assertEqual(record.record_id, "R-phase3")
        self.assertEqual(record.as_of, AS_OF.isoformat())
        self.assertEqual(record.input_snapshot["request_fingerprint"], expected)
        self.assertEqual(record.input_snapshot["workspace_revision"], 1)

        # Reopen 完全依赖不可变快照，不重算
        reopened = service.open_record("R-phase3")
        self.assertEqual(reopened.result_snapshot["evaluation_status"], "SUCCESS")
        self.assertEqual(reopened.grade, "1")

    def test_phase3_workspace_with_higher_revision_still_loads(self):
        self._insert_phase3_workspace_row("W-phase3-r3", revision=3)
        workspace = _service(self.db).load_workspace("W-phase3-r3")
        self.assertEqual(workspace.revision, 3)


class PersistenceRootCauseTests(unittest.TestCase):
    """G03：持久化失败必须保留根因，不得假报成功。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"

    def tearDown(self):
        self.tmp.cleanup()

    def _unmigrated_repository(self):
        # 未建表 → sqlite3.OperationalError
        return SqliteWorkspaceRepository(self.db), SqliteRecordRepository(self.db)

    def test_workspace_save_failure_preserves_root_cause(self):
        workspaces, _ = self._unmigrated_repository()
        snapshot = WorkspaceSnapshot(
            workspace_id="W", standard_code="GB 19762-2025",
            device_type="centrifugal_pump", product_category=WATER,
            rule_profile="pump_water", as_of=AS_OF.isoformat(), payload={},
            schema_version=2, created_at_utc="c", updated_at_utc="u")
        with self.assertRaises(LifecyclePersistenceError) as ctx:
            workspaces.save_workspace(snapshot)
        self.assertIsInstance(ctx.exception.__cause__, sqlite3.Error)
        self.assertIsInstance(ctx.exception, LifecycleError)

    def test_record_append_failure_preserves_root_cause(self):
        _, records = self._unmigrated_repository()
        from equipeffi.application.lifecycle import RecordSnapshot

        snapshot = RecordSnapshot(
            record_id="R", workspace_id=None, standard_code="GB 19762-2025",
            standard_version="2025", device_type="centrifugal_pump",
            product_category=WATER, rule_profile="pump_water",
            as_of=AS_OF.isoformat(), evaluation_status="SUCCESS", grade="1",
            ui_conclusion="合格", input_snapshot={}, result_snapshot={},
            reference_snapshot={}, ruleset_version="", calculator_version="",
            numeric_profile_id="", canonical_version="", canonical_package_hash="",
            result_contract_version="", schema_version=2,
            created_at_utc="c", finalized_at_utc="f")
        with self.assertRaises(LifecyclePersistenceError) as ctx:
            records.append_record(snapshot)
        self.assertIsInstance(ctx.exception.__cause__, sqlite3.Error)

    def test_duplicate_record_raises_record_conflict_error(self):
        migrate_records_database(self.db, app_version="test")
        service = _service(self.db)
        request = PumpAnalysisRequest(WATER, AS_OF, **VALUES)
        result = service.evaluate(request)
        service.finalize(record_id="R-dup", workspace_id=None,
                         request=request, result=result)
        with self.assertRaises(RecordConflictError) as ctx:
            service.finalize(record_id="R-dup", workspace_id=None,
                             request=request, result=result)
        # 既有调用方按 AnalysisError 捕获，必须继续成立
        self.assertIsInstance(ctx.exception, AnalysisError)


if __name__ == "__main__":
    unittest.main()
