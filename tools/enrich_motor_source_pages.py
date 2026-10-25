"""为高压电动机标准包补录已核对的PDF页码上下文。

页码来自标准原文表格页面图像核对，采用显式表级映射，不按数值趋势、
标准编号或相邻记录推断。该工具只写来源页范围，不修改标准数值。
用法：python tools/enrich_motor_source_pages.py [--apply]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HV_RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "motor_hv.json"

# PDF页码从1开始，范围包含跨页表格的续表。
HV_TABLE_PAGES = {
    "表1": "7-9",
    "表2": "9-11",
    "表3": "11-13",
    "表4": "14-15",
    "表5": "16-17",
    "表6": "17-18",
}


def enrich_hv_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """为GB30254高压包的六张表登记PDF页范围。"""
    if str(payload.get("standard_code", "")) != "GB 30254-2024":
        raise ValueError("高压资源standard_code不是GB 30254-2024")
    added = 0
    unchanged = 0
    unknown = 0
    for index, table in enumerate(payload.get("tables", []) or [], start=1):
        pages = HV_TABLE_PAGES.get(f"表{index}")
        if pages is None:
            unknown += 1
            continue
        if table.get("source_pages") not in (None, "", [], {}):
            unchanged += 1
            continue
        table["source_pages"] = pages
        added += 1
    return {
        "added": added,
        "unchanged": unchanged,
        "unknown_table": unknown,
        "table_pages": dict(HV_TABLE_PAGES),
    }


def _update(path: Path) -> dict[str, Any]:
    path = Path(path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    before = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    counts = enrich_hv_payload(payload)
    after = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return {
        "resource": str(path),
        **counts,
        "payload_changed": before != after,
        "payload": payload,
    }


def run(hv_path: Path = HV_RESOURCE, *, apply: bool = False) -> dict[str, Any]:
    hv = _update(hv_path)
    if apply and hv["payload_changed"]:
        Path(hv["resource"]).write_text(
            json.dumps(hv["payload"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return {
        "apply": apply,
        "high_voltage": {key: value for key, value in hv.items() if key != "payload"},
        "pdf_page_basis": "GB 30254-2024表1～表6的显式起止页范围，PDF页码从1开始",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补录高压电动机标准来源页码")
    parser.add_argument("--hv-resource", type=Path, default=HV_RESOURCE)
    parser.add_argument("--apply", action="store_true", help="写回来源页码元数据")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.hv_resource, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
