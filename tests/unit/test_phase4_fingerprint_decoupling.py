"""Phase 4 回归：指纹**不得**依赖产品 service 的导入副作用。

独立验收在 head `855f259` 上复现的阻塞：

```text
只 import Repository 的新进程（不 import 泵 service）里：
  业务键注册为空
  → water / chemical 旧 Workspace 的无参指纹全部漂移
  → 不同业务输入（efficiency 90 与 70）得到**相同**指纹
  → 只有 import 泵 service 后指纹才恢复（运行时耦合）
```

本模块把该复现固定为回归，覆盖：

- 只加载 Repository 时无参指纹不漂移；
- 不同业务输入不得碰撞；
- 业务键集合随快照持久化，而非进程内注册；
- 生命周期层不存在任何全局可变注册点；
- 未携带元数据的旧快照仍由**快照自身**确定性推出指纹（含跨进程一致）。
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import date

from equipeffi.application.lifecycle import (
    BUSINESS_KEYS_METADATA_KEY,
    RESERVED_PAYLOAD_KEYS,
    WorkspaceSnapshot,
    business_key_names,
    business_keys_metadata,
)
from equipeffi.application.services.centrifugal_pump_analysis_service import (
    PUMP_FINGERPRINT_KEYS,
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
PRODUCT_MODULE = "equipeffi.application.services.centrifugal_pump_analysis_service"


def _service(db: Path) -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"),
        SqliteWorkspaceRepository(db), SqliteRecordRepository(db))


class FingerprintImportDecouplingTests(unittest.TestCase):
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

    def _seed_three_workspaces(self) -> dict[str, str]:
        expected: dict[str, str] = {}
        for workspace_id, category, overrides in (
            ("W-water", WATER, {}),
            ("W-chem", CHEMICAL, {"HBEP": "14", "efficiency": "73"}),
            # 同一 rule profile、仅 efficiency 不同 → 必须得到不同指纹
            ("W-water-b", WATER, {"efficiency": "70"}),
        ):
            request = self._request(category, **overrides)
            self.service.create_workspace(workspace_id, request)
            expected[workspace_id] = request.request_fingerprint()
        return expected

    def test_repository_only_process_reproduces_expected_fingerprints(self):
        expected = self._seed_three_workspaces()
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
            f"assert {PRODUCT_MODULE!r} not in sys.modules,"
            " 'pump service must not be imported'\n"
            "print(json.dumps(out))\n"
        )
        completed = subprocess.run([sys.executable, "-c", child], capture_output=True,
                                   text=True, encoding="utf-8")
        # 这条断言本身就是修复的核心：只加载 Repository 也必须可用
        self.assertEqual(completed.returncode, 0,
                         f"子进程失败:\n{completed.stdout}\n{completed.stderr}")
        actual = json.loads(completed.stdout)
        for workspace_id, value in expected.items():
            with self.subTest(workspace=workspace_id):
                self.assertEqual(actual[workspace_id], value,
                                 "只加载 Repository 时指纹不得漂移")

    def test_different_business_inputs_never_collide(self):
        """旧实现下 efficiency 90 与 70 会得到同一指纹；现在必须不同。"""

        expected = self._seed_three_workspaces()
        self.assertNotEqual(expected["W-water"], expected["W-water-b"])

    def test_workspace_persists_its_own_business_key_metadata(self):
        self.service.create_workspace("W-meta", self._request(WATER))
        workspace = self.service.load_workspace("W-meta")
        self.assertEqual(business_key_names(workspace.payload), PUMP_FINGERPRINT_KEYS)
        self.assertIn(BUSINESS_KEYS_METADATA_KEY, workspace.payload)
        self.assertEqual(workspace.request_fingerprint(),
                         workspace.request_fingerprint(PUMP_FINGERPRINT_KEYS))

    def test_legacy_snapshot_without_metadata_is_derived_from_the_snapshot(self):
        """旧快照（无元数据）：无参指纹由快照自身确定性推出，且等于写入当次值。"""

        request = self._request(WATER)
        payload = request.raw_values() | {
            "project_name": request.project_name,
            "equipment_no": request.equipment_no,
        }
        self.assertNotIn(BUSINESS_KEYS_METADATA_KEY, payload)
        legacy = WorkspaceSnapshot(
            workspace_id="W-legacy", standard_code="GB 19762-2025",
            device_type="centrifugal_pump", product_category=WATER,
            rule_profile="pump_water", as_of=AS_OF.isoformat(), payload=payload,
            schema_version=2, created_at_utc="c", updated_at_utc="u")
        self.assertEqual(legacy.request_fingerprint(), request.request_fingerprint())

    def test_legacy_workspace_can_still_finalize_and_reopen(self):
        """真实旧库路径：无元数据草稿必须仍能 evaluate → finalize → Reopen。"""

        request = self._request(WATER)
        payload = request.raw_values() | {
            "project_name": request.project_name,
            "equipment_no": request.equipment_no,
        }
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                """
                INSERT INTO workspace (
                    workspace_id, standard_code, device_type, product_category,
                    rule_profile, as_of, payload_json, schema_version,
                    created_at_utc, updated_at_utc, revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("W-legacy", "GB 19762-2025", "centrifugal_pump", WATER, "pump_water",
                 AS_OF.isoformat(),
                 json.dumps(payload, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")),
                 2, "2026-08-23T00:00:00Z", "2026-08-23T00:00:00Z", 1),
            )

        workspace = self.service.load_workspace("W-legacy")
        rebuilt = self.service.request_from_workspace(workspace)
        self.assertEqual(rebuilt.request_fingerprint(), request.request_fingerprint())
        result = self.service.evaluate_workspace("W-legacy")
        self.assertEqual(result.evaluation_status, "SUCCESS")
        record = self.service.finalize(record_id="R-legacy", workspace_id="W-legacy",
                                       request=rebuilt, result=result)
        self.assertEqual(record.input_snapshot["request_fingerprint"],
                         request.request_fingerprint())
        reopened = self.service.open_record("R-legacy")
        self.assertEqual(reopened.result_snapshot["evaluation_status"], "SUCCESS")

    def test_legacy_fallback_is_deterministic_across_processes(self):
        """回退分支不得依赖导入顺序：子进程只加载 lifecycle 也得到同一指纹。"""

        payload = self._request(WATER).raw_values()
        expected_ws = WorkspaceSnapshot(
            workspace_id="W", standard_code="GB 19762-2025",
            device_type="centrifugal_pump", product_category=WATER,
            rule_profile="pump_water", as_of=AS_OF.isoformat(), payload=payload,
            schema_version=2, created_at_utc="c", updated_at_utc="u")
        expected = expected_ws.request_fingerprint()

        child = (
            "import json, sys\n"
            f"sys.path.insert(0, r'{ROOT / 'src'}')\n"
            "from equipeffi.application.lifecycle import WorkspaceSnapshot\n"
            "payload = json.loads(" + repr(json.dumps(payload, ensure_ascii=False)) + ")\n"
            "ws = WorkspaceSnapshot(workspace_id='W', standard_code='GB 19762-2025',\n"
            "    device_type='centrifugal_pump', product_category=" + repr(WATER) + ",\n"
            "    rule_profile='pump_water', as_of='2026-08-23', payload=payload,\n"
            "    schema_version=2, created_at_utc='c', updated_at_utc='u')\n"
            f"assert {PRODUCT_MODULE!r} not in sys.modules\n"
            "print(ws.request_fingerprint())\n"
        )
        completed = subprocess.run([sys.executable, "-c", child], capture_output=True,
                                   text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr[-600:])
        self.assertEqual(completed.stdout.strip(), expected)

    def test_reserved_keys_are_device_neutral(self):
        """生命周期级登记键必须是设备无关的通用字段名。"""

        self.assertEqual(RESERVED_PAYLOAD_KEYS,
                         frozenset({BUSINESS_KEYS_METADATA_KEY, "project_name",
                                    "equipment_no", "product_type"}))

    def test_lifecycle_module_has_no_ambient_registration(self):
        """生命周期层不得再提供全局可变注册点。"""

        for name in ("models.py", "ports.py", "errors.py", "__init__.py"):
            source = (ROOT / "src/equipeffi/application/lifecycle" / name).read_text("utf-8")
            with self.subTest(file=name):
                self.assertNotIn("register_business_keys", source)
                self.assertNotIn("_registered_business_keys", source)
                self.assertNotIn("global ", source)


if __name__ == "__main__":
    unittest.main()
