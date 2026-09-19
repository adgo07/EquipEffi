"""为低压/高压电动机标准包补录已核对的PDF页码上下文。

页码来自标准原文的表格页面图像核对，采用显式表级映射，不按数值趋势、
标准编号或相邻记录推断。该工具只写入 ``source_page``/``source_pages`` 元数据，
不修改效率、功率、极数、等级或任何其它标准值；默认只预览，传入 ``--apply``
才写回机器包。

用法：
    python tools/enrich_motor_source_pages.py
    python tools/enrich_motor_source_pages.py --apply
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LV_RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "motor_lv.json"
HV_RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "motor_hv.json"

# PDF页码从1开始。GB 18613-2020的机器包只收录表1三相异步电动机，
# 该表完整位于PDF第4页。
LV_SOURCE_PAGE = 4

# GB 30254-2024的表格可能跨页；范围包含该表在PDF中的起止页。
# 页范围已逐页渲染核对表题、续表标识和表格边界。
HV_TABLE_PAGES = {
    "表1": "7-9",
    "表2": "9-11",
    "表3": "11-13",
    "表4": "14-15",
    "表5": "16-17",
    "表6": "17-18",
}


def enrich_lv_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """为低压包登记表1页码，返回计数且不触碰标准值。"""

    if str(payload.get("standard_code", "")) != "GB 18613-2020":
        raise ValueError("低压资源standard_code不是GB 18613-2020")
    current = payload.get("source_page")
    if current not in (None, "", [], {}):
        return {"added": 0, "unchanged": 1, "source_page": current}
    payload["source_page"] = LV_SOURCE_PAGE
    return {"added": 1, "unchanged": 0, "source_page": LV_SOURCE_PAGE}


def enrich_hv_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """为高压包的六张表登记PDF页范围。"""

    if str(payload.get("standard_code", "")) != "GB 30254-2024":
        raise ValueError("高压资源standard_code不是GB 30254-2024")
    added = 0
    unchanged = 0
    unknown = 0
    for index, table in enumerate(payload.get("tables", []) or [], start=1):
        title = str(table.get("title", ""))
        table_name = f"表{index}"
        pages = HV_TABLE_PAGES.get(table_name)
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


def _update(path: Path, enrich) -> dict[str, Any]:
    path = Path(path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    before = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    counts = enrich(payload)
    after = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return {
        "resource": str(path),
        **counts,
        "payload_changed": before != after,
        "payload": payload,
    }


def run(
    lv_path: Path = LV_RESOURCE,
    hv_path: Path = HV_RESOURCE,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    lv = _update(lv_path, enrich_lv_payload)
    hv = _update(hv_path, enrich_hv_payload)
    if apply:
        for item in (lv, hv):
            if item["payload_changed"]:
                Path(item["resource"]).write_text(
                    json.dumps(item["payload"], ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
    return {
        "apply": apply,
        "low_voltage": {key: value for key, value in lv.items() if key != "payload"},
        "high_voltage": {key: value for key, value in hv.items() if key != "payload"},
        "pdf_page_basis": "GB 18613-2020表1第4页；GB 30254-2024表1～表6的显式起止页范围，PDF页码从1开始",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补录低压/高压电动机标准来源页码")
    parser.add_argument("--lv-resource", type=Path, default=LV_RESOURCE)
    parser.add_argument("--hv-resource", type=Path, default=HV_RESOURCE)
    parser.add_argument("--apply", action="store_true", help="写回来源页码元数据")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.lv_resource, args.hv_resource, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
