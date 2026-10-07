import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.check_windows_regressions import compare, compare_recorded


def _silenced(func, *args, **kwargs):
    """执行比较步骤并吞掉其控制台输出，便于断言返回码。"""

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(*args, **kwargs)


class RegressionComparatorTests(unittest.TestCase):
    def compare(self, failures=(), errors=(), skips=(), seen=("known.fail", "known.error", "known.skip")):
        actual = {"failure_ids": failures, "error_ids": errors, "skip_ids": skips, "executed_ids": seen}
        baseline = {"known_failure_ids": ["known.fail"], "known_error_ids": ["known.error"], "known_skip_ids": ["known.skip"]}
        return compare(actual, baseline)

    def test_known_failures_allowed(self):
        self.assertEqual(self.compare(["known.fail"], ["known.error"], ["known.skip"])["gate"], "PASS")

    def test_fixed_failures_pass_with_tightening_hint(self):
        result = self.compare(skips=["known.skip"])
        self.assertEqual(result["gate"], "PASS")
        self.assertEqual(result["fixed_known_tests"], ["known.error", "known.fail"])
        self.assertTrue(result["baseline_tightening_hint"])

    def test_new_failure_same_count_fails(self):
        result = self.compare(["new.fail"], ["known.error"], ["known.skip"])
        self.assertEqual(result["gate"], "FAIL")
        self.assertEqual(result["new_failures"], ["new.fail"])

    def test_new_error_fails(self):
        self.assertEqual(self.compare(errors=["new.error"])["gate"], "FAIL")

    def test_failure_to_error_is_worsening(self):
        result = self.compare(errors=["known.fail", "known.error"])
        self.assertEqual(result["gate"], "FAIL")
        self.assertEqual(result["worsened_failure_to_error"], ["known.fail"])

    def test_error_to_failure_is_improvement(self):
        self.assertEqual(self.compare(failures=["known.error"])["gate"], "PASS")

    def test_unexpected_skip_fails_even_when_former_failure(self):
        self.assertEqual(self.compare(skips=["known.fail"])["gate"], "FAIL")

    def test_missing_test_not_reported_as_fixed(self):
        self.assertEqual(self.compare(seen=["known.skip"])["gate"], "FAIL")

    def test_expected_failure_cannot_hide_new_regression(self):
        actual = {"failure_ids": [], "error_ids": [], "skip_ids": [], "executed_ids": ["hidden"],
                  "expected_failure_ids": ["hidden"]}
        baseline = {"known_failure_ids": [], "known_error_ids": [], "known_skip_ids": []}
        self.assertEqual(compare(actual, baseline)["gate"], "FAIL")


class RunCompareSplitTests(unittest.TestCase):
    """M1 CI 纯去重：比较步骤只消费已执行结果，绝不自己重新 full discover。

    这四条锁住不变量：结果缺失 / 结果为空 → fail closed；结果存在 → 按 ID 判定，
    既放行已知失败，也不放过新增回归。
    """

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.out = Path(temporary.name)
        self.baseline = self.out / "baseline.json"
        self.baseline.write_text(json.dumps({
            "known_failure_ids": ["known.fail"],
            "known_error_ids": ["known.error"],
            "known_skip_ids": ["known.skip"],
        }), encoding="utf-8")

    def _write_actual(self, payload: dict) -> None:
        (self.out / "actual.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_compare_fails_closed_when_no_results_were_executed(self):
        self.assertEqual(_silenced(compare_recorded, self.out, self.baseline), 2)
        self.assertFalse((self.out / "comparison.json").exists())

    def test_compare_fails_closed_on_empty_execution_record(self):
        self._write_actual({"executed_ids": [], "failure_ids": [], "error_ids": [], "skip_ids": []})
        self.assertEqual(_silenced(compare_recorded, self.out, self.baseline), 2)

    def test_compare_consumes_previously_recorded_results(self):
        self._write_actual({
            "executed_ids": ["known.fail", "known.error", "known.skip", "other.test"],
            "failure_ids": ["known.fail"],
            "error_ids": ["known.error"],
            "skip_ids": ["known.skip"],
            "unexpected_success_ids": [],
            "expected_failure_ids": [],
        })
        self.assertEqual(_silenced(compare_recorded, self.out, self.baseline), 0)
        comparison = json.loads((self.out / "comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(comparison["gate"], "PASS")

    def test_recorded_new_failure_still_fails_the_gate(self):
        self._write_actual({
            "executed_ids": ["known.fail", "known.error", "known.skip", "new.fail"],
            "failure_ids": ["new.fail"],
            "error_ids": ["known.error"],
            "skip_ids": ["known.skip"],
            "unexpected_success_ids": [],
            "expected_failure_ids": [],
        })
        self.assertEqual(_silenced(compare_recorded, self.out, self.baseline), 1)
        comparison = json.loads((self.out / "comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(comparison["gate"], "FAIL")
        self.assertEqual(comparison["new_failures"], ["new.fail"])
