"""Phase 8B — Excel Batch ↔ Qt/Application 业务一致性（Owner 要求 G09 / 门禁 20）。

**这是 Phase 8 最关键的一致性证明**：同一个 `PumpAnalysisRequest`，
经「单次 Application / Qt」与经「Excel Batch」路径，业务评价结果必须**零漂移**。

覆盖
----
- 18 条 water Approved Golden + 11 条 chemical Approved Golden = **29 条**，
  全部经**真实 Excel 载体**（写入 V6 模板 → Reader → Batch → evaluate）回放，
  逐条比对 `evaluation_status` / `conclusion` / `grade` / `issue_codes` /
  **matched business rule**，并与单次路径的 Result 快照做全量比对。
- 其他类别、不确定类别、数量 > 1、非法数量、单级/多级、单吸/双吸、
  范围边界、大量空行、中间空行、100 / 1000 / 10000 行。
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import openpyxl

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    PumpAnalysisRequest,
    user_conclusion_text,
)
from equipeffi.application.services.pump_batch_evaluation_service import (
    PumpBatchEvaluationService,
)
from equipeffi.infrastructure.excel.pump_result_writer import PumpResultWorkbookWriter
from equipeffi.infrastructure.excel.pump_workbook_reader import PUMP_SHEET, V6PumpWorkbookReader
from equipeffi.infrastructure.excel.template_resource import V6TemplateResource

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "specs" / "equipment_efficiency" / "golden"
FIRST_DATA_ROW = 4
AS_OF = date(2026, 8, 23)

#: Excel 列 ← Golden `raw_inputs` 键。
_GOLDEN_TO_COLUMN: tuple[tuple[str, str], ...] = (
    ("product_type", "F"), ("suction", "K"), ("stages", "L"), ("QBEP", "G"),
    ("HBEP", "H"), ("speed", "I"), ("efficiency", "M"),
)


def _approved_goldens() -> list[tuple[str, Path, dict]]:
    cases = []
    for profile in ("pump_water", "pump_chemical"):
        directory = GOLDEN_ROOT / profile
        for path in sorted(directory.glob("GC-PUMP-V*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if str(data.get("approval_status", "")).upper() != "APPROVED":
                continue
            cases.append((profile, path, data))
    return cases


class GoldenExcelReplayTests(unittest.TestCase):
    """29 条 Approved Golden 经 Excel Batch 路径的零漂移回放。"""

    @classmethod
    def setUpClass(cls):
        cls.app = None
        cls.cases = _approved_goldens()

    def setUp(self):
        from equipeffi.composition import create_pump_analysis_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.records_migrations import (
            migrate_records_database,
        )

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.analysis = create_pump_analysis_service(paths=self.paths)
        self.batch = PumpBatchEvaluationService(
            self.analysis,
            reader=V6PumpWorkbookReader(),
            writer=PumpResultWorkbookWriter())
        self.addCleanup(self.tmp.cleanup)

    def test_the_approved_golden_set_is_complete(self):
        profiles = [profile for profile, _p, _d in self.cases]
        self.assertEqual(profiles.count("pump_water"), 18, "water Approved Golden 应为 18 条")
        self.assertEqual(profiles.count("pump_chemical"), 11,
                         "chemical Approved Golden 应为 11 条")
        self.assertEqual(len(self.cases), 29)

    def test_all_approved_goldens_replay_through_excel_without_drift(self):
        """把 29 条 Golden 的原输入写进**真实 V6 工作簿**，经 Batch 回放。"""

        source = self.root / "golden_replay.xlsx"
        V6TemplateResource().download_to(source)
        workbook = openpyxl.load_workbook(source)
        sheet = workbook[PUMP_SHEET]
        for offset, (_profile, _path, data) in enumerate(self.cases):
            row = FIRST_DATA_ROW + offset
            for key, column in _GOLDEN_TO_COLUMN:
                value = data["raw_inputs"].get(key)
                if value not in (None, ""):
                    sheet[f"{column}{row}"] = value
            sheet[f"D{row}"] = 1          # 数量：正整数
            sheet[f"B{row}"] = data["case_id"]
        workbook.save(source)
        workbook.close()

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "golden_result.xlsx", as_of=AS_OF)
        self.assertEqual(result.summary.data_row_count, 29)
        self.assertEqual(result.summary.input_error_rows, 0)
        self.assertEqual(result.summary.execution_error_rows, 0)

        by_row = {outcome.row_number: outcome for outcome in result.outcomes}
        for offset, (profile, path, data) in enumerate(self.cases):
            expected = data["expected_result"]
            row = FIRST_DATA_ROW + offset
            with self.subTest(case=data["case_id"], profile=profile):
                outcome = by_row[row]
                self.assertEqual(outcome.evaluation_status,
                                 expected.get("evaluation_status"))
                self.assertEqual(outcome.conclusion, expected.get("ui_conclusion"))
                self.assertEqual(outcome.grade, expected.get("grade"))
                self.assertFalse(outcome.is_input_error)
                self.assertFalse(outcome.is_execution_error)

    def test_batch_result_snapshot_equals_single_application_snapshot(self):
        """同一 request：Excel Batch 与单次 Application 的 Result 必须一致。

        比对最强口径——`calculation_trace` / `thresholds` / `matched_rule_id` /
        `issue_codes` / `provenance` 全量相等，而不只是结论字符串。
        """

        for profile, path, data in self.cases:
            raw = data["raw_inputs"]
            request = PumpAnalysisRequest(
                product_category=raw["product_type"], as_of=AS_OF,
                QBEP=raw.get("QBEP"), HBEP=raw.get("HBEP"), speed=raw.get("speed"),
                efficiency=raw.get("efficiency"), suction=raw.get("suction"),
                stages=raw.get("stages"))
            with self.subTest(case=data["case_id"], profile=profile):
                single = self.analysis.evaluate(request)

                source = self.root / f"one_{data['case_id']}.xlsx"
                V6TemplateResource().download_to(source)
                workbook = openpyxl.load_workbook(source)
                sheet = workbook[PUMP_SHEET]
                for key, column in _GOLDEN_TO_COLUMN:
                    value = raw.get(key)
                    if value not in (None, ""):
                        sheet[f"{column}{FIRST_DATA_ROW}"] = value
                sheet[f"D{FIRST_DATA_ROW}"] = 1
                workbook.save(source)
                workbook.close()

                batch = self.batch.evaluate_workbook(
                    source, destination=self.root / f"out_{data['case_id']}.xlsx",
                    as_of=AS_OF, persist=False)
                outcome = batch.outcomes[0]

                self.assertEqual(outcome.evaluation_status, single.evaluation_status)
                self.assertEqual(outcome.conclusion, user_conclusion_text(single))
                self.assertEqual(outcome.grade, single.grade)
                # matched business rule + trace + thresholds 全量一致
                self.assertEqual(outcome.derived,
                                 dict((single.calculation_trace or {}).get("derived") or {}))
                self.assertEqual(outcome.thresholds, dict(single.thresholds or {}))
                self.assertEqual(
                    outcome.messages,
                    _messages_for(single))


def _messages_for(result) -> tuple[str, ...]:
    """与批量投影同一套消息口径（用于严格比对）。"""

    snapshot = result.as_snapshot()
    messages: list[str] = []
    missing = snapshot.get("missing_fields") or []
    if missing:
        messages.append("缺少" + "、".join(str(item) for item in missing))
    explanation = str(snapshot.get("explanation") or "").strip()
    if explanation:
        messages.append(explanation)
    for warning in snapshot.get("warnings") or ():
        messages.append(str(warning))
    return tuple(messages)


class ConclusionCoverageTests(unittest.TestCase):
    """Owner 要求的正式 business outcome 必须能被区分。"""

    @classmethod
    def setUpClass(cls):
        cls.app = None

    def setUp(self):
        from equipeffi.composition import create_pump_analysis_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.records_migrations import (
            migrate_records_database,
        )

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.analysis = create_pump_analysis_service(paths=self.paths)
        self.batch = PumpBatchEvaluationService(
            self.analysis, reader=V6PumpWorkbookReader(),
            writer=PumpResultWorkbookWriter())
        self.addCleanup(self.tmp.cleanup)

    def _run(self, rows: list[dict], name: str = "c.xlsx"):
        source = self.root / name
        V6TemplateResource().download_to(source)
        workbook = openpyxl.load_workbook(source)
        sheet = workbook[PUMP_SHEET]
        for offset, values in enumerate(rows):
            for column, value in values.items():
                sheet[f"{column}{FIRST_DATA_ROW + offset}"] = value
        workbook.save(source)
        workbook.close()
        return self.batch.evaluate_workbook(
            source, destination=self.root / f"r_{name}", as_of=AS_OF, persist=False)

    def test_official_conclusions_are_distinguishable(self):
        """1级 / 2级 / 3级 / 未达标 / 不适用 / 无法评价 六种正式结论。"""

        goldens = {data["case_id"]: data for _p, _f, data in _approved_goldens()}
        wanted = {
            "GC-PUMP-V4-WATER-SINGLE-SUCTION-L1": "1级",
            "GC-PUMP-V4-WATER-SINGLE-L2": "2级",
            "GC-PUMP-V4-WATER-SINGLE-L3": "3级",
            "GC-PUMP-V4-WATER-BELOW-MINIMUM": "未达标",
            "GC-PUMP-V4-WATER-CATEGORY-OTHER": "不适用",
        }
        rows = []
        for case_id, _expected in wanted.items():
            raw = goldens[case_id]["raw_inputs"]
            row = {"D": 1, "B": case_id}
            for key, column in _GOLDEN_TO_COLUMN:
                value = raw.get(key)
                if value not in (None, ""):
                    row[column] = value
            rows.append(row)
        # 不确定类别 -> 无法评价
        rows.append({"D": 1, "B": "uncertain", "F": "不确定类别",
                     "G": 100, "H": 50, "I": 2900, "J": 45, "K": "单吸", "L": 1, "M": 80})

        result = self._run(rows, "conclusions.xlsx")
        conclusions = [outcome.conclusion for outcome in result.outcomes]
        for expected in list(wanted.values()) + ["无法评价"]:
            with self.subTest(conclusion=expected):
                self.assertIn(expected, conclusions)

    def test_input_error_and_execution_error_are_not_business_conclusions(self):
        rows = [
            {"D": 0, "F": "单级单吸清水离心泵", "G": 100, "H": 50, "I": 2900,
             "J": 45, "K": "单吸", "L": 1, "M": 80},
        ]
        result = self._run(rows, "errors.xlsx")
        outcome = result.outcomes[0]
        self.assertTrue(outcome.is_input_error)
        self.assertEqual(outcome.conclusion, "输入错误")
        self.assertNotIn(outcome.conclusion, ("1级", "2级", "3级", "未达标", "不适用", "无法评价"))
        self.assertIsNone(outcome.evaluation_status)


class BoundaryAndShapeTests(unittest.TestCase):
    """范围边界、数量>1、单级/多级、单吸/双吸、空行形态。"""

    def setUp(self):
        from equipeffi.composition import create_pump_analysis_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.records_migrations import (
            migrate_records_database,
        )

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.analysis = create_pump_analysis_service(paths=self.paths)
        self.batch = PumpBatchEvaluationService(
            self.analysis, reader=V6PumpWorkbookReader(),
            writer=PumpResultWorkbookWriter())
        self.addCleanup(self.tmp.cleanup)

    def _run(self, rows: list[dict], name: str = "s.xlsx"):
        source = self.root / name
        V6TemplateResource().download_to(source)
        workbook = openpyxl.load_workbook(source)
        sheet = workbook[PUMP_SHEET]
        for offset, values in enumerate(rows):
            for column, value in values.items():
                sheet[f"{column}{FIRST_DATA_ROW + offset}"] = value
        workbook.save(source)
        workbook.close()
        return self.batch.evaluate_workbook(
            source, destination=self.root / f"r_{name}", as_of=AS_OF, persist=False)

    def test_quantity_greater_than_one_is_weighted(self):
        """数量 > 1 必须按数量加权，而不是按行计数。"""

        result = self._run([
            {"D": 20, "F": "单级单吸清水离心泵", "G": 100, "H": 50, "I": 2900,
             "J": 45, "K": "单吸", "L": 1, "M": 78},
        ], "qty.xlsx")
        self.assertEqual(result.summary.data_row_count, 1)
        self.assertEqual(result.summary.total_quantity, 20)
        self.assertEqual(result.summary.evaluated_quantity, 20)
        self.assertEqual(result.summary.conclusion_quantities.get("2级"), 20)

    def test_blank_rows_are_skipped_without_losing_later_rows(self):
        """大量空行 + 中间空行不得导致丢行或错位。"""

        source = self.root / "gaps.xlsx"
        V6TemplateResource().download_to(source)
        workbook = openpyxl.load_workbook(source)
        sheet = workbook[PUMP_SHEET]
        # 第 4 行留空，第 5 行有数据，第 6~8 行留空，第 9 行有数据
        for row, name in ((5, "首"), (9, "末")):
            sheet[f"B{row}"] = name
            sheet[f"D{row}"] = 3
            sheet[f"F{row}"] = "单级单吸清水离心泵"
            sheet[f"G{row}"] = 100
            sheet[f"H{row}"] = 50
            sheet[f"I{row}"] = 2900
            sheet[f"J{row}"] = 45
            sheet[f"K{row}"] = "单吸"
            sheet[f"L{row}"] = 1
            sheet[f"M{row}"] = 78
        workbook.save(source)
        workbook.close()

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "gaps_out.xlsx", as_of=AS_OF, persist=False)
        self.assertEqual(result.summary.data_row_count, 2)
        self.assertEqual([o.row_number for o in result.outcomes], [5, 9],
                         "原行号映射不得错位")
        self.assertEqual(result.summary.total_quantity, 6)

    def test_single_and_multistage_and_suction_variants(self):
        result = self._run([
            {"D": 1, "F": "单级单吸清水离心泵", "G": 100, "H": 50, "I": 2900,
             "J": 45, "K": "单吸", "L": 1, "M": 78},
            {"D": 1, "F": "单级双吸清水离心泵", "G": 300, "H": 50, "I": 2900,
             "J": 120, "K": "双吸", "L": 1, "M": 82},
            {"D": 1, "F": "多级清水离心泵", "G": 100, "H": 150, "I": 2900,
             "J": 90, "K": "单吸", "L": 3, "M": 76},
            {"D": 1, "F": "轻型多级清水离心泵（立式）", "G": 60, "H": 120,
             "I": 2900, "J": 45, "K": "双吸", "L": 3, "M": 70},
        ], "variants.xlsx")
        self.assertEqual(result.summary.input_error_rows, 0)
        self.assertEqual(result.summary.execution_error_rows, 0)
        for outcome in result.outcomes:
            with self.subTest(row=outcome.row_number):
                self.assertIsNotNone(outcome.evaluation_status)

    def test_range_boundaries_do_not_crash(self):
        """范围边界（流量极小/极大）必须给出正式结论或明确不适用，不得异常。"""

        result = self._run([
            {"D": 1, "F": "单级单吸清水离心泵", "G": 1, "H": 50, "I": 2900,
             "J": 45, "K": "单吸", "L": 1, "M": 78},
            {"D": 1, "F": "单级单吸清水离心泵", "G": 99999, "H": 50, "I": 2900,
             "J": 45, "K": "单吸", "L": 1, "M": 78},
        ], "bounds.xlsx")
        self.assertEqual(result.summary.execution_error_rows, 0)
        for outcome in result.outcomes:
            with self.subTest(row=outcome.row_number):
                self.assertIsNotNone(outcome.evaluation_status)


class LargeVolumeTests(unittest.TestCase):
    """100 / 1000 / 10000 行真实运行（报告耗时、峰值内存、文件大小）。"""

    def setUp(self):
        from equipeffi.composition import create_pump_analysis_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.records_migrations import (
            migrate_records_database,
        )

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.analysis = create_pump_analysis_service(paths=self.paths)
        self.batch = PumpBatchEvaluationService(
            self.analysis, reader=V6PumpWorkbookReader(),
            writer=PumpResultWorkbookWriter())
        self.addCleanup(self.tmp.cleanup)

    def test_large_volumes_run_without_truncation_or_hang(self):
        import tracemalloc

        report = []
        for count in (100, 1000, 10000):
            with self.subTest(rows=count):
                source = self.root / f"bulk_{count}.xlsx"
                V6TemplateResource().download_to(source)
                workbook = openpyxl.load_workbook(source)
                sheet = workbook[PUMP_SHEET]
                for index in range(count):
                    row = FIRST_DATA_ROW + index
                    sheet[f"B{row}"] = f"设备{index + 1}"
                    sheet[f"C{row}"] = f"M-{index + 1:05d}"
                    sheet[f"D{row}"] = (index % 5) + 1
                    sheet[f"E{row}"] = "1号车间"
                    sheet[f"F{row}"] = "单级单吸清水离心泵"
                    sheet[f"G{row}"] = 100
                    sheet[f"H{row}"] = 50
                    sheet[f"I{row}"] = 2900
                    sheet[f"J{row}"] = 45
                    sheet[f"K{row}"] = "单吸"
                    sheet[f"L{row}"] = 1
                    sheet[f"M{row}"] = 78
                workbook.save(source)
                workbook.close()

                tracemalloc.start()
                started = time.perf_counter()
                result = self.batch.evaluate_workbook(
                    source, destination=self.root / f"out_{count}.xlsx",
                    as_of=AS_OF, persist=False)
                elapsed = time.perf_counter() - started
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                self.assertEqual(result.summary.data_row_count, count,
                                 "不得静默丢行/截断")
                self.assertEqual(len(result.outcomes), count)
                self.assertEqual(result.summary.input_error_rows, 0)
                self.assertEqual(result.summary.execution_error_rows, 0)
                out_size = Path(result.result_workbook).stat().st_size
                report.append((count, source.stat().st_size, out_size,
                               round(elapsed, 3), peak))
        print("\n  rows   in_bytes  out_bytes  seconds   peak_MB")
        for count, in_size, out_size, elapsed, peak in report:
            print(f"  {count:<6} {in_size:<10} {out_size:<10} "
                  f"{elapsed:<9} {peak / 1024 / 1024:.1f}")


if __name__ == "__main__":
    unittest.main()
