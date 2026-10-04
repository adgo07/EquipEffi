"""Phase 4 验证工具：用 **base 代码**写真实数据库，再用当前代码读回并走完整 Use Case。

对应独立验收的复现路径：

```text
base 提交代码写 records.sqlite（含 workspace 行，且**不含** Phase 4 的业务键元数据）
  → 当前代码 load_workspace
  → request_from_workspace 重建输入
  → evaluate_workspace
  → finalize
  → open_record（Reopen 不重算）
```

断言：

- 无参指纹与 base 记录值**逐字节一致**（不得漂移）；
- 重建输入的指纹与 base 记录值一致；
- Finalize 写入的 `input_snapshot["request_fingerprint"]` 与 base 记录值一致；
- Reopen 返回原结论；
- 更新一次草稿后带上业务键元数据，指纹仍与 base 一致。

用法：

```powershell
$env:PYTHONPATH='src'
python tools/verify_phase4_fingerprint_compat.py
```

退出码 0 = 全部通过；1 = 存在漂移或 Use Case 失败。

Python 3.12；只读 base 提交（`git worktree`，临时目录，运行后清理）。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_SHA = "87d9ef1bf32fb3f765d4f8ef3f97aa222913152a"
ROOT = Path(__file__).resolve().parents[1]
WORKTREE = Path(tempfile.gettempdir()) / "equipeffi-phase4-base-wt"

_CASE = (
    ("W-base-water", "单级单吸清水离心泵",
     {"QBEP": "100", "HBEP": "50", "speed": "2900",
      "efficiency": "90", "suction": "单吸", "stages": "1"}),
    ("W-base-chem", "单级石油化工离心泵",
     {"QBEP": "100", "HBEP": "14", "speed": "2900",
      "efficiency": "73", "suction": "单吸", "stages": "1"}),
)

_BASE_WRITER = r'''
import json, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, r"{src}")
from equipeffi.application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService, PumpAnalysisRequest)
from equipeffi.infrastructure.persistence.records_migrations import migrate_records_database
from equipeffi.infrastructure.persistence.sqlite_records_repository import (
    SqliteWorkspaceRepository, SqliteRecordRepository)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

db = Path(r"{db}")
migrate_records_database(db, app_version="base")
svc = CentrifugalPumpAnalysisService(
    JsonStandardRepository(Path(r"{src}") / "equipeffi"),
    SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
out = {{}}
for wid, category, values in json.loads(r"""{cases}"""):
    request = PumpAnalysisRequest(category, date(2026, 8, 23), **values)
    svc.create_workspace(wid, request)
    out[wid] = request.request_fingerprint()
print(json.dumps(out))
'''


def _fail(message: str) -> int:
    print("FAIL:", message)
    return 1


def main() -> int:
    if WORKTREE.exists():
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(WORKTREE)],
                       capture_output=True)
    subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)
    added = subprocess.run(
        ["git", "worktree", "add", "--detach", str(WORKTREE), BASE_SHA],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if added.returncode != 0:
        return _fail(f"无法创建 base worktree: {added.stderr[:300]}")

    tmp = Path(tempfile.mkdtemp(prefix="p4-compat-"))
    db = tmp / "records.sqlite"
    try:
        writer = _BASE_WRITER.format(
            src=WORKTREE / "src", db=db,
            cases=json.dumps(_CASE, ensure_ascii=False))
        base_run = subprocess.run([sys.executable, "-c", writer], capture_output=True,
                                  text=True, encoding="utf-8")
        if base_run.returncode != 0:
            return _fail(f"base 写库失败: {base_run.stderr[-500:]}")
        expected = json.loads(base_run.stdout)
        print(f"base ({BASE_SHA[:8]}) 写入 {len(expected)} 个草稿")

        sys.path.insert(0, str(ROOT / "src"))
        from equipeffi.application.services.centrifugal_pump_analysis_service import (
            CentrifugalPumpAnalysisService,
        )
        from equipeffi.infrastructure.persistence.sqlite_records_repository import (
            SqliteRecordRepository,
            SqliteWorkspaceRepository,
        )
        from equipeffi.infrastructure.standards.json_repository import (
            JsonStandardRepository,
        )

        service = CentrifugalPumpAnalysisService(
            JsonStandardRepository(ROOT / "src" / "equipeffi"),
            SqliteWorkspaceRepository(db), SqliteRecordRepository(db))

        failures = 0
        for workspace_id, _, _ in _CASE:
            recorded = expected[workspace_id]
            print(f"--- {workspace_id}  base fingerprint = {recorded}")
            workspace = service.load_workspace(workspace_id)
            if workspace is None:
                failures += 1
                print("    !! 草稿读不回来")
                continue
            print(f"    payload keys       = {sorted(workspace.payload)}")

            noarg = workspace.request_fingerprint()
            print(f"    no-arg fingerprint = {noarg}")
            if noarg != recorded:
                failures += 1
                print("    !! 无参指纹漂移")

            request = service.request_from_workspace(workspace)
            if request.request_fingerprint() != recorded:
                failures += 1
                print("    !! 重建输入指纹漂移")

            result = service.evaluate_workspace(workspace_id)
            print(f"    evaluation_status  = {result.evaluation_status} "
                  f"grade={result.grade}")
            record = service.finalize(record_id=f"R-{workspace_id}",
                                      workspace_id=workspace_id,
                                      request=request, result=result)
            if record.input_snapshot["request_fingerprint"] != recorded:
                failures += 1
                print("    !! Record 指纹漂移")

            reopened = service.open_record(record.record_id)
            if reopened.result_snapshot["evaluation_status"] != result.evaluation_status:
                failures += 1
                print("    !! Reopen 结论不一致")
            print(f"    reopen             = "
                  f"{reopened.result_snapshot['evaluation_status']} "
                  f"as_of={reopened.as_of}")

            updated = service.update_workspace(workspace_id, request)
            if updated.request_fingerprint() != recorded:
                failures += 1
                print("    !! 更新后无参指纹漂移")
            print(f"    after update keys  = {sorted(updated.payload)}")

        if failures:
            return _fail(f"{failures} 项漂移/失败")
        print("\nOK: base 数据库在当前代码下指纹与 Use Case 全部一致")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        subprocess.run(["git", "worktree", "remove", "--force", str(WORKTREE)],
                       cwd=ROOT, capture_output=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)


if __name__ == "__main__":
    sys.exit(main())
