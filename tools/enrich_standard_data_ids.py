"""为标准机器数据记录补录稳定的内部 ``data_id``。

该工具只补录记录标识，不推断或修改任何标准数值、单位、页码和区间。
已有 ``data_id`` 保持不变；默认只预览，必须显式传 ``--apply`` 才会写回
标准资源。ID按标准文件中的稳定集合顺序生成，便于人工校对册、查表轨迹
和后续版本比较。

用法：
    python tools/enrich_standard_data_ids.py
    python tools/enrich_standard_data_ids.py --apply
    python tools/enrich_standard_data_ids.py --apply --manifest path/to/standard_manifest.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable

try:
    from .audit_standard_provenance import MANIFEST, _iter_records
except ImportError:  # 直接执行 python tools/enrich_standard_data_ids.py
    from audit_standard_provenance import MANIFEST, _iter_records


def _prefix(standard_code: str, source: Path) -> str:
    """返回人可读的标准短码；未知文件使用安全文件名。"""

    match = re.search(r"GB(?:/T)?\s*(\d{5})", str(standard_code).upper())
    if match:
        return "GB" + match.group(1)
    stem = re.sub(r"[^A-Za-z0-9]+", "-", source.stem).strip("-").upper()
    return stem or "STANDARD"


def _unique_id(prefix: str, sequence: int, used: set[str]) -> str:
    candidate = f"{prefix}-R{sequence:06d}"
    suffix = 1
    while candidate in used:
        suffix += 1
        candidate = f"{prefix}-R{sequence:06d}-{suffix}"
    return candidate


def _records_for_file(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """取得与来源审计相同的记录集合，避免给根元数据加ID。"""

    return [record for record, _page in _iter_records(payload)]


def enrich_payload(payload: dict[str, Any], standard_code: str, source: Path) -> int:
    """向当前JSON对象的标准记录添加ID并返回新增数量。"""

    prefix = _prefix(standard_code, source)
    records = _records_for_file(payload)
    used = {
        str(record.get("data_id"))
        for record in records
        if record.get("data_id") not in (None, "")
    }
    added = 0
    # ``_iter_records``按稳定的JSON遍历顺序返回记录；这个顺序也是审计、
    # 校对册和版本比较所使用的顺序。不要按数值趋势重排或重编号已有ID。
    for sequence, record in enumerate(records, start=1):
        if record.get("data_id") not in (None, ""):
            continue
        record["data_id"] = _unique_id(prefix, sequence, used)
        used.add(str(record["data_id"]))
        added += 1
    return added


def enrich_manifest(manifest_path: Path, apply: bool = False) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources: dict[Path, tuple[str, list[str]]] = {}
    for entry in manifest.get("packs", []):
        source = (manifest_path.parent / str(entry.get("source", ""))).resolve()
        if source not in sources:
            sources[source] = (str(entry.get("standard_code", "")), [str(entry.get("device_type", ""))])
        else:
            sources[source][1].append(str(entry.get("device_type", "")))

    results: list[dict[str, Any]] = []
    total_added = 0
    for source, (standard_code, device_types) in sorted(sources.items(), key=lambda item: str(item[0])):
        if not source.is_file():
            results.append({"source": str(source), "device_types": device_types, "status": "missing", "added": 0})
            continue
        payload = json.loads(source.read_text(encoding="utf-8"))
        before = len([record for record in _records_for_file(payload) if record.get("data_id") not in (None, "")])
        added = enrich_payload(payload, standard_code, source)
        after = len([record for record in _records_for_file(payload) if record.get("data_id") not in (None, "")])
        if apply and added:
            source.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results.append({
            "source": str(source),
            "device_types": device_types,
            "status": "applied" if apply and added else "preview" if added else "unchanged",
            "records_with_id_before": before,
            "records_with_id_after": after,
            "added": added,
        })
        total_added += added
    return {"manifest": str(manifest_path), "apply": apply, "total_added": total_added, "sources": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="为标准机器数据记录补录稳定data_id")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--apply", action="store_true", help="写回标准JSON；不传则只预览")
    args = parser.parse_args(argv)
    print(json.dumps(enrich_manifest(args.manifest, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
