"""为四类空调标准记录补录已核对的原PDF表题页码。

只处理 ``hvac_thresholds.json`` 中的热泵热水机、风管送风式空调、单元式
空调和多联式空调记录。页码来自原PDF表题/续表，不改动任何阈值、条件或
指标名称；默认预览，传入 ``--apply`` 才写回 ``source_page`` 元数据。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "hvac_thresholds.json"

DEVICE_TABLE_PAGES = {
    "heat_pump_water_heater": {"表1": "PDF第4页"},
    "duct_ac": {"表1": "PDF第4页", "表2": "PDF第4页"},
    "unitary_ac": {"表1": "PDF第3-4页"},
    "multi_split_ac": {"表1": "PDF第4页", "表2": "PDF第4页", "表3": "PDF第5页", "表4": "PDF第5页"},
}


def enrich_payload(payload: dict[str, Any]) -> dict[str, int]:
    added = 0
    unchanged = 0
    unknown = 0
    devices = payload.get("devices", {})
    for device, table_pages in DEVICE_TABLE_PAGES.items():
        records = devices.get(device, {}).get("records", [])
        for row in records:
            if not isinstance(row, dict) or row.get("data_id") in (None, ""):
                unknown += 1
                continue
            page = table_pages.get(str(row.get("table", "")))
            if page is None:
                unknown += 1
            elif row.get("source_page") not in (None, "", [], {}):
                unchanged += 1
            else:
                row["source_page"] = page
                added += 1
    return {"added": added, "unchanged": unchanged, "unknown": unknown}


def run(path: Path = RESOURCE, apply: bool = False) -> dict[str, Any]:
    path = Path(path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    before = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    counts = enrich_payload(payload)
    after = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if apply and counts["added"]:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "resource": str(path),
        "apply": apply,
        "device_table_pages": DEVICE_TABLE_PAGES,
        **counts,
        "payload_changed": bool(apply and before != after),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补录空调标准记录来源页码")
    parser.add_argument("--resource", type=Path, default=RESOURCE)
    parser.add_argument("--apply", action="store_true", help="写回source_page元数据")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.resource, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
