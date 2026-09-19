"""在激活包通过校验后，将PMSM标准包登记为active。

该工具要求激活包与manifest中的pack_id、标准编号和源文件一致，并将原
manifest复制到指定备份路径后再写回。它不修改其它标准包，也不覆盖激活包
的数值内容。
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path
from typing import Sequence


PACK_ID = "gb30253_2024_pdf_verified_v1"
STANDARD_CODE = "GB 30253-2024"


def promote(manifest_path: Path, pack_path: Path, backup_path: Path, *, reviewer: str, review_date: str) -> dict[str, object]:
    manifest_path = Path(manifest_path).resolve()
    pack_path = Path(pack_path).resolve()
    backup_path = Path(backup_path).resolve()
    if manifest_path == backup_path:
        raise ValueError("manifest备份路径必须与源文件不同")
    if not manifest_path.is_file() or not pack_path.is_file():
        raise FileNotFoundError("manifest或激活包不存在")
    reviewer = str(reviewer).strip()
    review_date = str(review_date).strip()
    if not reviewer:
        raise ValueError("reviewer不能为空")
    try:
        date.fromisoformat(review_date)
    except ValueError as exc:
        raise ValueError("review_date必须为YYYY-MM-DD") from exc
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    if pack.get("pack_id") != PACK_ID or pack.get("standard_code") != STANDARD_CODE:
        raise ValueError("激活包pack_id或标准编号不匹配")
    if pack.get("status") != "active" or pack.get("verified_table_count") != 29:
        raise ValueError("激活包必须为active且包含29张表")
    review = pack.get("activation_review") or {}
    if review.get("all_cells_reviewed") is not True or review.get("reviewer") != reviewer or review.get("review_date") != review_date:
        raise ValueError("激活包缺少与用户确认一致的activation_review")
    entries = manifest.get("packs")
    if not isinstance(entries, list):
        raise ValueError("manifest缺少packs列表")
    matches = [entry for entry in entries if entry.get("pack_id") == PACK_ID]
    if len(matches) != 1:
        raise ValueError("manifest中的PMSM包不存在或重复")
    entry = matches[0]
    expected_source = Path(entry.get("source", ""))
    if expected_source.name != "gb30253_2024_pdf_verified_v1.json":
        raise ValueError("manifest的PMSM源文件不是规范PDF重建包")
    if entry.get("standard_code") != STANDARD_CODE:
        raise ValueError("manifest标准编号不匹配")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, backup_path)
    entry["status"] = "active"
    entry["data_version"] = "pdf-rebuild-2026.08.23-user-reviewed-2026.08.30"
    entry.pop("unavailable_reason", None)
    entry["reviewer"] = reviewer
    entry["review_date"] = review_date
    entry["reviewed_efficiency_cell_count"] = review.get("reviewed_efficiency_cell_count")
    # 运行时资源可从wheel/pyz加载，不能把当前工作区的绝对路径写进
    # manifest；绝对路径既不可移植，也可能泄露构建机目录。保留与
    # manifest source一致的包内相对引用，具体源文件哈希仍由标准包和
    # activation_review.source_sha256追溯。
    entry["activation_source"] = str(entry.get("source") or f"resources/standards/{pack_path.name}")
    manifest["generated_at"] = review_date
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "manifest": str(manifest_path),
        "backup": str(backup_path),
        "pack_id": PACK_ID,
        "status": entry["status"],
        "data_version": entry["data_version"],
        "reviewer": reviewer,
        "review_date": review_date,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="登记已完成用户复核的PMSM标准包")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("pack", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--reviewer", default="用户确认")
    parser.add_argument("--review-date", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(promote(args.manifest, args.pack, args.backup, reviewer=args.reviewer, review_date=args.review_date), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
