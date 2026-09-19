from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from equipeffi.application.ports.v4_workbook import V4WorkbookRow
from equipeffi.application.services.evaluation_facade import EvaluationFacade
from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.application.services.v4_workbook_service import V4WorkbookService
from equipeffi.domain.common.enums import Conclusion
from equipeffi.domain.common.enums import EliminationScope
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]


class _Reader:
    def read_rows(self, source: Path):
        return [V4WorkbookRow(
            record_id="ROW-1",
            sheet_name="电动机",
            values={
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 98,
            },
        )]


class _Writer:
    def write_results(self, source: Path, destination: Path, results):
        self.source = source
        self.destination = destination
        self.results = tuple(results)
        destination.write_text("writer-port", encoding="utf-8")
        return destination


class _ScopedReader(_Reader):
    def read_settings(self, source: Path):
        return {"elimination_scope": "仅产业结构调整指导目录"}


class _InvalidScopedReader(_Reader):
    def read_settings(self, source: Path):
        return {"elimination_scope": "不存在的淘汰口径"}


class V4WorkbookServiceTests(unittest.TestCase):
    def test_batch_evaluation_uses_same_v4_facade(self):
        service = V4WorkbookService(
            EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))),
            _Reader(),
        )
        result = service.evaluate(Path("input.xlsx"))
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.results[0].public_device_type, "motor")

    def test_writer_is_required_to_create_a_different_output_file(self):
        service = V4WorkbookService(
            EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))),
            _Reader(),
        )
        writer = _Writer()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.xlsx"
            destination = Path(directory) / "result.xlsx"
            output = service.evaluate_and_write(source, destination, writer=writer)
            self.assertEqual(output, destination)
            self.assertEqual(writer.results[0].result.internal_device_type, "motor_lv")
            with self.assertRaises(ValueError):
                service.evaluate_and_write(source, source, writer=writer)

    def test_workbook_setting_is_used_when_scope_is_not_explicitly_overridden(self):
        service = V4WorkbookService(
            EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))),
            _ScopedReader(),
        )
        result = service.evaluate(Path("input.xlsx"))
        self.assertEqual(result.elimination_scope.value, "仅产业结构调整指导目录")
        self.assertEqual(result.results[0].elimination_scope.value, "仅产业结构调整指导目录")

    def test_explicit_string_scope_is_normalized_in_batch_envelope(self):
        service = V4WorkbookService(
            EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))),
            _Reader(),
        )
        result = service.evaluate(Path("input.xlsx"), elimination_scope=EliminationScope.INDUSTRY_ONLY.value)
        self.assertIs(result.elimination_scope, EliminationScope.INDUSTRY_ONLY)
        self.assertIs(result.results[0].elimination_scope, EliminationScope.INDUSTRY_ONLY)

    def test_invalid_workbook_setting_is_rejected(self):
        service = V4WorkbookService(
            EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))),
            _InvalidScopedReader(),
        )
        with self.assertRaises(ValueError):
            service.evaluate(Path("input.xlsx"))


if __name__ == "__main__":
    unittest.main()
