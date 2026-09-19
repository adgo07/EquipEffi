"""为GB 19153-2019空压机记录补录已核对的PDF表页范围。

仅覆盖机器包当前收录的表1～表4。页码来自原PDF的表题/续表标识；表5～表7
虽然存在于标准中，但不因本工具而给当前机器包增加或推断记录。默认预览，
传入 ``--apply`` 才会写回 ``source_pages`` 元数据。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "compressor.json"

# PDF页码从1开始；范围包含表格起始页和最后一页续表。
TABLE_PAGES = {
    "表1": "5-7",
    "表2": "8-10",
    "表3": "11-12",
    "表4": "12-13",
}


def enrich_payload(payload: dict[str, Any]) -> dict[str, int]:
    rows = payload.get("rows", [])
    added = 0
    unchanged = 0
    unknown_table = 0
    for row in rows:
        table = str(row.get("table", ""))
        pages = TABLE_PAGES.get(table)
        if pages is None:
            unknown_table += 1
            continue
        if row.get("source_pages") not in (None, "", [], {}):
            unchanged += 1
            continue
        row["source_pages"] = pages
        added += 1
    return {"added": added, "unchanged": unchanged, "unknown_table": unknown_table}


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
        "table_mapping": TABLE_PAGES,
        **counts,
        "payload_changed": bool(apply and before != after),
        "pdf_page_basis": "GB 19153-2019原PDF表题及续表页码，PDF页码从1开始",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补录GB 19153-2019空压机记录来源页范围")
    parser.add_argument("--resource", type=Path, default=RESOURCE)
    parser.add_argument("--apply", action="store_true", help="写回source_pages元数据")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.resource, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
