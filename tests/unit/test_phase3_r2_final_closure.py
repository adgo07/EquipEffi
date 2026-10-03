"""Phase 3 R2：Golden 历史 provenance 解耦与 Finalize 全状态矩阵。

两个 Gate 分别独立验证：

- **historical provenance valid**：Approved/Review Golden 中
  `CURRENT_IMPLEMENTATION` 的 `artifact_sha256` 按 `provenance.source_baseline_sha`
  对应的**历史**文件校验，不要求当前 HEAD 保持同一源码 hash；
- **current Golden replay valid**：当前 HEAD 的实现正确性由 18/18 water +
  11/11 chemical Golden replay 验证（见 test_phase3_golden_and_boundaries）。

另含表驱动的 Finalize 全状态矩阵，覆盖全部真实 result producer。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
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
GOLDEN_DIRS = (
    ROOT / "specs/equipment_efficiency/golden/pump_water",
    ROOT / "specs/equipment_efficiency/golden/pump_chemical",
)
#: 审批时锁定了实现快照的 schema 版本。
LINEAGE_VERSIONS = {"golden-case-0.3", "golden-case-0.4", "golden-case-0.4-review"}


def _service(workspaces=None, records=None) -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"), workspaces, records)


def _repo_text_sha256(data: bytes) -> str:
    """仓库既有文本哈希规则：UTF-8、CRLF→LF 后 SHA-256（大写）。"""

    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest().upper()


def _load_cases() -> list[dict]:
    cases = []
    for directory in GOLDEN_DIRS:
        for path in sorted(directory.glob("*.json")):
            cases.append(json.loads(path.read_text(encoding="utf-8")))
    return cases


def _baseline_sha(case: dict) -> str | None:
    provenance = case.get("provenance")
    if isinstance(provenance, dict):
        value = str(provenance.get("source_baseline_sha", "") or "").strip()
        return value or None
    return None


def _references(case: dict) -> list[dict]:
    sidecar = case.get("source_sidecar")
    if isinstance(sidecar, dict) and isinstance(sidecar.get("source_references"), list):
        return sidecar["source_references"]
    references = case.get("source_reference")
    return references if isinstance(references, list) else []


class GoldenHistoricalProvenanceTests(unittest.TestCase):
    """Gate 1：历史 provenance 必须对 `source_baseline_sha` 的历史文件校验。"""

    @classmethod
    def setUpClass(cls):
        cls.cases = _load_cases()

    def test_cases_with_pinned_baseline_exist(self):
        """18 条 water 0.4 与 8 条候选派生 chemical 0.5 都锁定 source_baseline_sha。

        C9–C11 是 **owner-defined** 案例，没有候选来源，因此按设计**不带**
        `source_baseline_sha`；它们的历史 provenance 由 owner 批准证据承载。
        """

        water = [c for c in self.cases if c.get("case_schema_version") == "golden-case-0.4"]
        chemical = [c for c in self.cases if c.get("case_schema_version") == "golden-case-0.5"]
        self.assertEqual(len(water), 18)
        self.assertEqual(len(chemical), 11)
        self.assertTrue(all(_baseline_sha(c) for c in water),
                        "18 条 water 0.4 必须全部锁定 source_baseline_sha")
        candidate_derived = [
            c for c in chemical
            if (c.get("provenance") or {}).get("provenance_kind") == "CANDIDATE_DERIVED"
            or c.get("provenance", {}).get("source_candidate_case_id")
        ]
        self.assertEqual(len(candidate_derived), 8)
        self.assertTrue(all(_baseline_sha(c) for c in candidate_derived),
                        "候选派生的 chemical 案例必须锁定 source_baseline_sha")
        owner_defined = [c for c in chemical
                         if (c.get("provenance") or {}).get("provenance_kind") == "OWNER_DEFINED"]
        self.assertEqual(len(owner_defined), 3)
        self.assertTrue(all(_baseline_sha(c) is None for c in owner_defined),
                        "owner-defined 案例不得伪造 source_baseline_sha")
        self.assertEqual(sum(1 for c in self.cases if _baseline_sha(c)), 26)

    def test_implementation_hashes_verify_against_their_pinned_baseline(self):
        """逐条核对 CURRENT_IMPLEMENTATION 与历史 blob 一致。"""

        checked = 0
        for case in self.cases:
            baseline = _baseline_sha(case)
            if baseline is None:
                continue
            for reference in _references(case):
                if reference.get("evidence_role") != "CURRENT_IMPLEMENTATION":
                    continue
                if reference.get("artifact_kind") != "REPOSITORY_FILE":
                    continue
                path = str(reference["artifact_path"])
                recorded = str(reference["artifact_sha256"]).upper()
                completed = subprocess.run(
                    ["git", "show", f"{baseline}:{path}"],
                    cwd=ROOT, capture_output=True)
                with self.subTest(case=case["case_id"], artifact=path):
                    self.assertEqual(
                        completed.returncode, 0,
                        f"无法读取历史基线 {baseline}:{path}；"
                        "CI 必须使用 fetch-depth: 0 取得完整历史")
                    self.assertEqual(_repo_text_sha256(completed.stdout), recorded)
                checked += 1
        self.assertGreater(checked, 0, "未发现可校验的历史实现引用")

    def test_historical_hashes_are_not_bulk_rewritten_to_current_head(self):
        """历史 provenance 不得被批量更新成当前 HEAD 的源码 hash。

        至少存在一条实现文件：其记录 hash 等于历史 blob 且**不等于**当前工作树，
        这证明解耦真实生效（当前 HEAD 已合法演进）。
        """

        diverged = []
        for case in self.cases:
            baseline = _baseline_sha(case)
            if baseline is None:
                continue
            for reference in _references(case):
                if reference.get("evidence_role") != "CURRENT_IMPLEMENTATION":
                    continue
                if reference.get("artifact_kind") != "REPOSITORY_FILE":
                    continue
                path = str(reference["artifact_path"])
                recorded = str(reference["artifact_sha256"]).upper()
                local = ROOT / path
                if not local.is_file():
                    continue
                current = _repo_text_sha256(local.read_bytes())
                if current != recorded:
                    historical = subprocess.run(
                        ["git", "show", f"{baseline}:{path}"],
                        cwd=ROOT, capture_output=True)
                    if historical.returncode == 0 and _repo_text_sha256(historical.stdout) == recorded:
                        diverged.append((case["case_id"], path))
        self.assertTrue(
            diverged,
            "没有任何实现文件的记录 hash 与当前 HEAD 不同——"
            "若刚做过批量更新，历史 provenance 已被破坏")

    def test_validator_reports_no_errors_for_repository_evidence(self):
        """Validator 的 Gate 1 必须在无外部 evidence root 时也通过。"""

        completed = subprocess.run(
            [sys.executable, "tools/validate_phase1_contracts.py", "--skip-external-evidence"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(
            completed.returncode, 0,
            f"validator 失败：\n{completed.stdout[-3000:]}\n{completed.stderr[-2000:]}")
        self.assertIn("errors=0", completed.stdout)
        self.assertNotIn(" ERROR ", completed.stdout)


class FinalizeStateMatrixTests(unittest.TestCase):
    """Gate 2：表驱动覆盖全部真实 result producer 的 Finalize 状态矩阵。"""

    #: 唯一不受「finalizable == 状态在白名单内」约束的具名例外。
    #: 理由：评价日期早于标准实施日期时，本版本标准对该日期不可用，
    #: 结果虽有 INSUFFICIENT_DATA 状态，但**未执行任何计算**，
    #: 固化它会产生"标准尚未实施却已出正式结论"的记录。
    WHITELIST_EXCEPTIONS = frozenset({"as_of before effective date"})

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
            ("as_of before effective date", PumpAnalysisRequest(
                WATER, date(2026, 2, 28), QBEP="100", HBEP="50", speed="2900",
                efficiency="90", suction="单吸", stages="1"),
             "INSUFFICIENT_DATA", False, False),
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
                # 统一 policy：finalizable == (evaluation_status 在白名单内)。
                # 唯一的**具名例外**见 WHITELIST_EXCEPTIONS：
                #   "as_of before effective date" 的状态是 INSUFFICIENT_DATA，
                #   但评价日期早于标准实施日期、本版本标准对该日期不可用、
                #   未执行任何计算，因此不构成可固化的正式结论。
                if label in self.WHITELIST_EXCEPTIONS:
                    self.assertFalse(finalizable, label)
                    self.assertFalse(result.provenance["ruleset_executed"], label)
                    self.assertTrue(
                        str(result.provenance.get("no_ruleset_reason") or "").strip(), label)
                else:
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
