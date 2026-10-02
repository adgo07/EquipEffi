"""按 unittest 编号与类型比较，不将已有全量失败冒充全量 PASS。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import unittest


def compare(actual: dict, baseline: dict) -> dict:
    failures = set(actual["failure_ids"])
    errors = set(actual["error_ids"])
    skips = set(actual["skip_ids"])
    old_failures = set(baseline["known_failure_ids"])
    old_errors = set(baseline["known_error_ids"])
    old_skips = set(baseline["known_skip_ids"])
    seen = set(actual["executed_ids"])
    known = old_failures | old_errors | old_skips
    problems = {
        "new_failures": sorted(failures - old_failures - old_errors),
        "new_errors": sorted(errors - old_errors - old_failures),
        "worsened_failure_to_error": sorted(errors & old_failures),
        "unexpected_skips": sorted(skips - old_skips),
        "missing_baseline_tests": sorted(known - seen),
        "unexpected_successes": sorted(actual.get("unexpected_success_ids", [])),
        "unexpected_expected_failures": sorted(actual.get("expected_failure_ids", [])),
    }
    fixed = sorted((old_failures | old_errors) & seen - failures - errors - skips)
    return {"gate": "FAIL" if any(problems.values()) else "PASS", **problems,
            "fixed_known_tests": fixed, "improved_error_to_failure": sorted(failures & old_errors),
            "baseline_tightening_hint": bool(fixed)}


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_ids = set()

    def startTest(self, test):
        self.executed_ids.add(test.id())
        super().startTest(test)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.executed_ids.add(subtest.id())
        super().addSubTest(test, subtest, err)


def run_suite(output: Path, baseline: Path) -> int:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Phase 2 正式证据必须使用 Python 3.12")
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py", top_level_dir=".")
    with (output / "full_suite.log").open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult).run(suite)
    actual = {
        "executable": sys.executable, "python_version": sys.version, "duration_seconds": time.perf_counter() - start,
        "run": result.testsRun,
        "pass": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped) - len(result.expectedFailures) - len(result.unexpectedSuccesses),
        "fail": len(result.failures), "error": len(result.errors), "skip": len(result.skipped),
        "expected_fail": len(result.expectedFailures), "unexpected_success": len(result.unexpectedSuccesses),
        "failure_ids": sorted({test.id() for test, _ in result.failures}),
        "error_ids": sorted({test.id() for test, _ in result.errors}),
        "skip_ids": sorted({test.id() for test, _ in result.skipped}),
        "unexpected_success_ids": sorted(test.id() for test in result.unexpectedSuccesses),
        "expected_failure_ids": sorted(test.id() for test, _ in result.expectedFailures),
        "executed_ids": sorted(result.executed_ids),
        "raw_suite_success": result.wasSuccessful(),
    }
    known = json.loads(baseline.read_text(encoding="utf-8"))
    comparison = compare(actual, known)
    (output / "actual.json").write_text(json.dumps(actual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in actual.items() if not k.endswith("_ids")}, ensure_ascii=False, indent=2))
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    return 0 if comparison["gate"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path("tests/baselines/windows_full_suite_known.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/phase2-regression"))
    args = parser.parse_args()
    return run_suite(args.output, args.baseline)


if __name__ == "__main__":
    raise SystemExit(main())
