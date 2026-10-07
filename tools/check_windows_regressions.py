"""按 unittest 编号与类型比较，不将已有全量失败冒充全量 PASS。

M1 拆分（单人维护简化）：把「执行一次完整测试套件」与「按 ID 比较已知基线」
拆成两个可独立调用的步骤，使 CI 中的比较步骤**消费已经执行过的结果**，
不再自己重新 full discover。

- ``--mode run``     ：只执行一次 full suite，写出 ``full_suite.log`` /
  ``actual.json`` / ``summary.txt``。执行完成即返回 0（真实失败/错误由
  下一步比较判断）；发现 0 条测试视为执行失败，返回非 0（fail closed）。
- ``--mode compare`` ：只读取已生成的 ``actual.json`` 与已知基线比较，
  写出 ``comparison.json``；gate FAIL 返回非 0。不执行任何测试。
- ``--mode all``     ：run + compare，等价于 M1 拆分前的旧行为（本地/手工调用）。

无论哪一步，**真实计数都会完整落盘**；workflow 绿灯只表示「没有新增回归」，
仓库仍存在已知 baseline failure，绝不等同于「全量测试全部通过」。
"""
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


def _counts(actual: dict) -> dict:
    return {k: v for k, v in actual.items() if not k.endswith("_ids")}


def build_actual(result: unittest.TestResult, *, duration_seconds: float) -> dict:
    """把一次已完成 suite 的结果转成落盘记录（纯函数，便于回归测试）。

    注意 ``unittest.TestResult`` 的字段结构并不一致：
      * ``failures`` / ``errors`` / ``skipped`` / ``expectedFailures`` 是
        ``(test, traceback)`` 元组列表；
      * ``unexpectedSuccesses`` 是 ``test`` 对象列表。
    两者混淆会在 ``@unittest.expectedFailure`` 出现时抛 ``AttributeError``，
    而且是在落盘之前抛——既丢了证据又绕过了门禁。这里用 ``_expected_failure_ids``
    统一处理，并由单元测试锁死。
    """

    return {
        "executable": sys.executable,
        "python_version": sys.version,
        "duration_seconds": duration_seconds,
        "run": result.testsRun,
        "pass": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
        - len(result.expectedFailures) - len(result.unexpectedSuccesses),
        "fail": len(result.failures),
        "error": len(result.errors),
        "skip": len(result.skipped),
        "expected_fail": len(result.expectedFailures),
        "unexpected_success": len(result.unexpectedSuccesses),
        "failure_ids": sorted({test.id() for test, _ in result.failures}),
        "error_ids": sorted({test.id() for test, _ in result.errors}),
        "skip_ids": sorted({test.id() for test, _ in result.skipped}),
        "expected_failure_ids": _expected_failure_ids(result),
        "unexpected_success_ids": sorted(test.id() for test in result.unexpectedSuccesses),
        "executed_ids": sorted(getattr(result, "executed_ids", set())),
        "raw_suite_success": result.wasSuccessful(),
    }


def _expected_failure_ids(result: unittest.TestResult) -> list[str]:
    """``expectedFailures`` 是 ``(test, traceback)`` 元组列表，必须解包。"""

    return sorted(test.id() for test, _ in result.expectedFailures)


def record_suite(output: Path) -> dict:
    """执行一次完整 suite 并落盘真实结果，返回 actual 记录。"""

    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Phase 2 正式证据必须使用 Python 3.12")
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py", top_level_dir=".")
    with (output / "full_suite.log").open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult).run(suite)
    actual = build_actual(result, duration_seconds=time.perf_counter() - start)

    (output / "actual.json").write_text(json.dumps(actual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [
        "===== FULL SUITE (single execution; real counts) =====",
        f"executable={actual['executable']}",
        f"python_version={actual['python_version'].splitlines()[0]}",
        f"duration_seconds={actual['duration_seconds']:.3f}",
        f"run={actual['run']} pass={actual['pass']} fail={actual['fail']} "
        f"error={actual['error']} skip={actual['skip']} "
        f"expected_fail={actual['expected_fail']} unexpected_success={actual['unexpected_success']}",
        f"raw_suite_success={actual['raw_suite_success']}",
        "说明：真实失败/错误/跳过已如实记录；是否新增回归由 compare 步骤按 ID 判定。",
        "本记录不表示『全量测试全部通过』。",
        "",
    ]
    (output / "summary.txt").write_text("\n".join(summary), encoding="utf-8")
    print("\n".join(summary))
    if actual["run"] == 0:
        # 发现 0 条测试一定是环境/发现故障，不能当成成功。
        print("ERROR: full suite 执行到 0 条测试，按 fail closed 处理", file=sys.stderr)
        return actual
    return actual


def compare_recorded(output: Path, baseline: Path) -> int:
    """读取已落盘的 actual.json 与基线比较，不重新执行测试。"""

    actual_path = output / "actual.json"
    if not actual_path.is_file():
        print(
            f"ERROR: 未找到已执行结果 {actual_path}；比较步骤不得自行重新执行 full suite（fail closed）",
            file=sys.stderr,
        )
        return 2
    actual = json.loads(actual_path.read_text(encoding="utf-8"))
    if not actual.get("executed_ids"):
        print("ERROR: 已执行结果为空，按 fail closed 处理", file=sys.stderr)
        return 2
    known = json.loads(baseline.read_text(encoding="utf-8"))
    comparison = compare(actual, known)
    (output / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(_counts(actual), ensure_ascii=False, indent=2))
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    return 0 if comparison["gate"] == "PASS" else 1


def run_suite(output: Path, baseline: Path) -> int:
    """旧行为：一次执行 + 一次比较（M1 之前的调用方式仍然可用）。"""

    if record_suite(output) is None:
        return 2
    return compare_recorded(output, baseline)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path("tests/baselines/windows_full_suite_known.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/phase2-regression"))
    parser.add_argument(
        "--mode",
        choices=("run", "compare", "all"),
        default="all",
        help="run=只执行一次并落盘；compare=只比较已落盘结果（不执行测试）；all=执行+比较",
    )
    args = parser.parse_args()
    if args.mode == "run":
        try:
            actual = record_suite(args.output)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        return 2 if actual is None or actual["run"] == 0 else 0
    if args.mode == "compare":
        return compare_recorded(args.output, args.baseline)
    return run_suite(args.output, args.baseline)


if __name__ == "__main__":
    raise SystemExit(main())
