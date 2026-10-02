import unittest

from tools.check_windows_regressions import compare


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
