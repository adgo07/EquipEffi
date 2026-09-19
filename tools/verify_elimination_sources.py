"""核对第一至第四批机电淘汰目录 DOCX 与机器目录的一致性。

该工具只读外部 DOCX 和仓库中的 JSON，不会改写标准仓库。它用于发布前确认
四个来源文件仍是生成机器目录时使用的文件，并同时检查批次条目数。产业结构
调整目录不属于本工具的输入范围。

示例：
    python tools/verify_elimination_sources.py \
      --source-dir "G:\\标准  规范\\03_清洁生产与环保\\淘汰目录与推荐目录"
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .extract_elimination_catalogs import extract_raw_entries
except ImportError:  # direct execution: ``python tools/verify_elimination_sources.py``
    from extract_elimination_catalogs import extract_raw_entries


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "src" / "equipeffi" / "resources" / "elimination_catalog_batches_1_4.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(source_dir: Path, catalog_path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    """返回可序列化的来源核对报告。

    ``is_valid`` 只有在四个文件均存在、哈希与 JSON 中记录一致，且 DOCX 重新
    抽取出的条目数与来源元数据一致时才为真。机器目录自身的批次计数也会单独
    核对，防止误把相邻批次合并或漏载。
    """

    source_dir = Path(source_dir).resolve()
    catalog_path = Path(catalog_path).resolve()
    errors: list[str] = []
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "is_valid": False,
            "source_dir": str(source_dir),
            "catalog": str(catalog_path),
            "errors": [f"无法读取机器目录: {exc}"],
            "sources": [],
        }

    entries = catalog.get("entries", [])
    by_batch: dict[str, int] = {}
    for item in entries:
        batch = str(item.get("batch", ""))
        by_batch[batch] = by_batch.get(batch, 0) + 1

    rows: list[dict[str, Any]] = []
    sources = catalog.get("sources", [])
    if len(sources) != 4:
        errors.append(f"机器目录sources应有4项，实际{len(sources)}项")
    seen_batches: set[int] = set()
    for source in sorted(sources, key=lambda item: int(item.get("batch", 0))):
        batch = int(source.get("batch", 0))
        seen_batches.add(batch)
        name = str(source.get("file", ""))
        path = source_dir / name
        row: dict[str, Any] = {
            "batch": batch,
            "file": name,
            "exists": path.is_file(),
            "expected_sha256": source.get("sha256", ""),
            "expected_entry_count": source.get("entry_count"),
            "machine_entry_count": by_batch.get(f"第{'一二三四'[batch - 1]}批", 0) if 1 <= batch <= 4 else 0,
        }
        if not path.is_file():
            row["actual_sha256"] = None
            row["extracted_entry_count"] = None
            errors.append(f"第{batch}批来源文件不存在: {path}")
        else:
            actual_hash = _sha256(path)
            row["actual_sha256"] = actual_hash
            row["hash_match"] = actual_hash == row["expected_sha256"]
            if not row["hash_match"]:
                errors.append(f"第{batch}批来源文件SHA-256不一致: {name}")
            try:
                extracted = len(extract_raw_entries(path, batch))
            except Exception as exc:  # pragma: no cover - malformed third-party DOCX
                extracted = None
                row["extract_error"] = f"{type(exc).__name__}: {exc}"
                errors.append(f"第{batch}批DOCX无法重新抽取: {name}")
            row["extracted_entry_count"] = extracted
            if extracted is not None and extracted != row["expected_entry_count"]:
                errors.append(f"第{batch}批条目数与机器目录来源元数据不一致: {name}")
            if extracted is not None and extracted != row["machine_entry_count"]:
                errors.append(f"第{batch}批条目数与机器目录实际批次数不一致: {name}")
        rows.append(row)
    if seen_batches != {1, 2, 3, 4}:
        errors.append(f"sources批次必须为1至4，实际为{sorted(seen_batches)}")
    return {
        "is_valid": not errors,
        "source_dir": str(source_dir),
        "catalog": str(catalog_path),
        "catalog_status": catalog.get("status", ""),
        "catalog_entry_count": len(entries),
        "batch_entry_counts": by_batch,
        "errors": errors,
        "sources": rows,
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 第一至第四批机电淘汰目录来源核对",
        "",
        f"- 结果：**{'通过' if report['is_valid'] else '未通过'}**",
        f"- 机器目录：`{report['catalog']}`",
        f"- 来源目录：`{report['source_dir']}`",
        f"- 机器目录条目数：{report['catalog_entry_count']}",
        "",
        "| 批次 | 文件 | 存在 | SHA-256一致 | DOCX抽取条目 | 机器目录条目 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in report["sources"]:
        lines.append(
            f"| 第{row['batch']}批 | `{row['file']}` | "
            f"{'是' if row['exists'] else '否'} | "
            f"{'是' if row.get('hash_match') else '否'} | "
            f"{row.get('extracted_entry_count', '')} | {row.get('machine_entry_count', '')} |"
        )
    if report["errors"]:
        lines.extend(["", "## 问题", ""])
        lines.extend(f"- {error}" for error in report["errors"])
    lines.extend(["", "产业结构调整目录未纳入本次核对。", ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="核对第一至第四批机电淘汰目录DOCX来源")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, help="可选：写出人可读Markdown报告")
    args = parser.parse_args(argv)
    report = verify(args.source_dir, args.catalog)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["is_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
