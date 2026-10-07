"""M3 低风险批量性能优化：标准包重复读取开销的端到端实测。

固定条件（同一机器 / 同一 commit / 同一正式 V6 模板 / 同一 representative data /
同一测试方法）：

- Python 3.12（M1 建立的正式 ``.venv``）；
- representative data **直接复用** ``tools/measure_v6_capacity.py`` 的同一行生成规则
  （不复制第二套样例数据，避免"同一 representative data"失效）；
- 场景：100 / 1,000 / 10,000 行。

测量项（全部实测，不外推）：

- ``total``          整批 ``evaluate_workbook``（**不含** SQLite ``batch_record`` 持久化）
- ``reader``         ``V6PumpWorkbookReader.read``
- ``application``    逐行 ``CentrifugalPumpAnalysisService.evaluate`` 累计
- ``get_pack``       其中 ``JsonStandardRepository.get_pack`` 累计（application 的子集）
- ``writer``         ``PumpResultWorkbookWriter.write``
- ``peak_memory``    整批 ``tracemalloc`` 峰值
- 输入 / 输出文件大小
- ``result_digest``  逐行结论摘要（before / after 业务一致性核对用）

两个 pass：计时 pass 关闭 ``tracemalloc``（避免内存跟踪扭曲耗时），内存 pass 单独
开启 ``tracemalloc`` 只取峰值。两个 pass 使用同一输入文件、同一装配方式、同一方法。

用法::

    python tools/measure_m3_batch_performance.py --label before \
        --json docs/diagnostics/m3_batch_before.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import tracemalloc
from datetime import date
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# representative data 只此一份：直接复用容量实测工具的生成规则。
from measure_v6_capacity import (  # noqa: E402
    FIRST_DATA_ROW,
    PUMP_SHEET,
    TEMPLATE,
    _fill,
)

import openpyxl  # noqa: E402

DEFAULT_SCENARIOS: tuple[int, ...] = (100, 1000, 10000)
AS_OF = date(2026, 8, 23)


class _Timer:
    """累计某个阶段的真实耗时（秒）与调用次数。"""

    def __init__(self) -> None:
        self.seconds = 0.0
        self.calls = 0

    def add(self, seconds: float) -> None:
        self.seconds += seconds
        self.calls += 1

    def as_dict(self) -> dict:
        return {"seconds": round(self.seconds, 6), "calls": self.calls}


class _TimedReader:
    def __init__(self, inner, timer: _Timer) -> None:
        self._inner = inner
        self._timer = timer

    def read(self, source):
        start = time.perf_counter()
        try:
            return self._inner.read(source)
        finally:
            self._timer.add(time.perf_counter() - start)


class _TimedWriter:
    def __init__(self, inner, timer: _Timer) -> None:
        self._inner = inner
        self._timer = timer

    def default_destination(self, source):
        return self._inner.default_destination(source)

    def write(self, source, outcomes, destination):
        start = time.perf_counter()
        try:
            return self._inner.write(source, outcomes, destination)
        finally:
            self._timer.add(time.perf_counter() - start)


class _TimedAnalysis:
    def __init__(self, inner, timer: _Timer) -> None:
        self._inner = inner
        self._timer = timer

    def evaluate(self, request):
        start = time.perf_counter()
        try:
            return self._inner.evaluate(request)
        finally:
            self._timer.add(time.perf_counter() - start)


def _instrument_repository(analysis, timer: _Timer) -> None:
    """在真实装配出来的 repository 实例上计时 ``get_pack``。

    只包一层计时，不改变调用协议与异常语义。
    """

    repository = analysis._standards  # noqa: SLF001 - 正式装配注入的同一实例
    original = repository.get_pack

    def timed_get_pack(device_type, pack_id=None):
        start = time.perf_counter()
        try:
            return original(device_type, pack_id)
        finally:
            timer.add(time.perf_counter() - start)

    repository.get_pack = timed_get_pack


def _build_source(rows: int, workdir: Path) -> Path:
    """按 ``measure_v6_capacity`` 的同一规则把 representative data 写入 V6 模板。"""

    target = workdir / f"pump_{rows}.xlsx"
    workbook = openpyxl.load_workbook(TEMPLATE, data_only=False)
    _fill(workbook, rows)
    workbook.save(target)
    workbook.close()
    return target


def _result_digest(result) -> dict:
    """逐行结论摘要：用于 before / after 业务一致性核对。"""

    rows = []
    for outcome in result.outcomes:
        rows.append({
            "row": outcome.row_number,
            "conclusion": outcome.conclusion,
            "evaluation_status": outcome.evaluation_status,
            "grade": outcome.grade,
            "quantity": outcome.quantity,
            "evaluated": outcome.evaluated,
            "is_input_error": outcome.is_input_error,
            "is_execution_error": outcome.is_execution_error,
            "derived": outcome.derived,
        })
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {
        "digest": digest,
        "row_count": len(rows),
        "conclusion_rows": dict(result.summary.conclusion_rows),
        "conclusion_quantities": dict(result.summary.conclusion_quantities),
        "data_row_count": result.summary.data_row_count,
        "total_quantity": result.summary.total_quantity,
        "evaluated_quantity": result.summary.evaluated_quantity,
        "input_error_rows": result.summary.input_error_rows,
        "execution_error_rows": result.summary.execution_error_rows,
    }


def _assemble(workdir: Path):
    """正式装配路径：与 Qt / Excel 产品路径同一套 service 与 repository。"""

    from equipeffi.application.services.pump_batch_evaluation_service import (
        PumpBatchEvaluationService,
    )
    from equipeffi.composition import create_pump_analysis_service
    from equipeffi.infrastructure.excel.pump_result_writer import (
        PumpResultWorkbookWriter,
    )
    from equipeffi.infrastructure.excel.pump_workbook_reader import (
        V6PumpWorkbookReader,
    )
    from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
    from equipeffi.infrastructure.persistence.records_migrations import (
        migrate_records_database,
    )

    paths = AppDataPaths(workdir / "app")
    migrate_records_database(paths.records_db, app_version="m3-benchmark")
    analysis = create_pump_analysis_service(paths=paths)
    reader = V6PumpWorkbookReader()
    writer = PumpResultWorkbookWriter()
    return analysis, reader, writer, (lambda a, r, w: PumpBatchEvaluationService(
        a, reader=r, writer=w))


def _run_pass(rows: int, source: Path, destination: Path, *, track_memory: bool) -> dict:
    analysis, reader, writer, make_batch = _assemble(source.parent)

    reader_timer, writer_timer, app_timer, pack_timer = (
        _Timer(), _Timer(), _Timer(), _Timer())
    _instrument_repository(analysis, pack_timer)

    batch = make_batch(
        _TimedAnalysis(analysis, app_timer),
        _TimedReader(reader, reader_timer),
        _TimedWriter(writer, writer_timer),
    )

    if track_memory:
        tracemalloc.start()
    start = time.perf_counter()
    result = batch.evaluate_workbook(
        source, destination=destination, as_of=AS_OF, persist=False)
    total = time.perf_counter() - start
    peak = 0
    if track_memory:
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    return {
        "total": total,
        "peak_memory_bytes": peak,
        "reader": reader_timer.as_dict(),
        "application": app_timer.as_dict(),
        "get_pack": pack_timer.as_dict(),
        "writer": writer_timer.as_dict(),
        "result": _result_digest(result),
        "output_size_bytes": destination.stat().st_size if destination.exists() else 0,
    }


def measure(rows: int, workdir: Path) -> dict:
    source = _build_source(rows, workdir)
    input_size = source.stat().st_size

    timed = _run_pass(rows, source, workdir / f"timed_{rows}.xlsx", track_memory=False)
    memory = _run_pass(rows, source, workdir / f"memory_{rows}.xlsx", track_memory=True)

    digest_matches = timed["result"]["digest"] == memory["result"]["digest"]
    return {
        "rows": rows,
        "input_size_bytes": input_size,
        "output_size_bytes": timed["output_size_bytes"],
        "total_seconds": round(timed["total"], 6),
        "total_seconds_with_tracemalloc": round(memory["total"], 6),
        "reader_seconds": round(timed["reader"]["seconds"], 6),
        "application_seconds": round(timed["application"]["seconds"], 6),
        "application_calls": timed["application"]["calls"],
        "get_pack_seconds": round(timed["get_pack"]["seconds"], 6),
        "get_pack_calls": timed["get_pack"]["calls"],
        "writer_seconds": round(timed["writer"]["seconds"], 6),
        "peak_memory_bytes": memory["peak_memory_bytes"],
        "result_digest": timed["result"]["digest"],
        "result_digest_matches_memory_pass": digest_matches,
        "summary": timed["result"],
    }


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - 环境信息缺失不阻断测量
        return ""


def _template_sha256() -> str:
    import equipeffi.infrastructure.standards.json_repository as repo_module

    return repo_module.canonical_source_sha256(TEMPLATE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="run")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--rows", type=int, nargs="*", default=list(DEFAULT_SCENARIOS))
    parser.add_argument("--workdir", type=Path, default=None,
                        help="临时工作目录；默认用仓库内被忽略的 tmp/（本机系统临时目录可能不可写）")
    args = parser.parse_args(argv)

    if args.workdir is not None:
        workdir = Path(args.workdir)
        workdir.mkdir(parents=True, exist_ok=True)
    else:
        # 中间文件必须落在仓库内被忽略的 tmp/：正式运行环境里系统临时目录不一定可写。
        # 目录用普通 mkdir 建立（tempfile.mkdtemp 会收紧目录权限，受限运行环境下不可写）。
        scratch_root = REPO_ROOT / "tmp"
        scratch_root.mkdir(parents=True, exist_ok=True)
        workdir = scratch_root / f"m3-bench-{uuid4().hex[:10]}"
        workdir.mkdir(parents=True, exist_ok=True)
    scenarios = []
    try:
        for rows in args.rows:
            scenario = measure(rows, workdir)
            scenarios.append(scenario)
            print(f"  rows={rows:<6} total={scenario['total_seconds']:>8.3f}s "
                  f"reader={scenario['reader_seconds']:>7.3f}s "
                  f"application={scenario['application_seconds']:>8.3f}s "
                  f"get_pack={scenario['get_pack_seconds']:>7.3f}s "
                  f"writer={scenario['writer_seconds']:>7.3f}s "
                  f"peak={scenario['peak_memory_bytes'] / 1024 / 1024:>7.1f}MB "
                  f"digest_ok={scenario['result_digest_matches_memory_pass']}")
    finally:
        import shutil

        if args.workdir is None:
            shutil.rmtree(workdir, ignore_errors=True)

    payload = {
        "label": args.label,
        "python": sys.version,
        "executable": sys.executable,
        "head": _git_head(),
        "template": str(TEMPLATE),
        "template_sha256": _template_sha256(),
        "method": {
            "as_of": AS_OF.isoformat(),
            "persist_batch_record": False,
            "timing_pass_tracemalloc": False,
            "memory_pass_tracemalloc": True,
            "representative_data": "tools/measure_v6_capacity.py::_fill",
        },
        "scenarios": scenarios,
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    raise SystemExit(main())
