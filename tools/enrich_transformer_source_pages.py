"""为GB 20052-2024变压器记录补录已核对的PDF页码。

页码来自原标准PDF的表题所在页，映射是显式维护的，不按相邻记录、数值
趋势或标准编号推断。该工具只补充 ``source_page`` 元数据，不修改任何标准
数值、单位、区间或等级；默认只预览，传入 ``--apply`` 才写回机器包。

用法：
    python tools/enrich_transformer_source_pages.py
    python tools/enrich_transformer_source_pages.py --apply
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "transformer.json"

# 原PDF按PDF页码（从1开始）定位表题。一个页面可能承载多张表，属于已
# 通过原文表题核对的来源定位；不把此映射扩展到其他标准包。
TABLE_PAGE = {
    "表1": 7,
    "表2": 8,
    "表3": 9,
    "表4": 9,
    "表5": 10,
    "表6": 10,
    "表7": 11,
    "表8": 11,
    "表9": 12,
    "表10": 12,
    "表11": 13,
    "表12": 13,
    "表13": 14,
    "表14": 14,
    "表15": 15,
    "表16": 15,
    "表17": 16,
    "表18": 16,
    "表19": 16,
    "表20": 17,
    "表21": 17,
    "表22": 17,
    "表23": 18,
    "表24": 18,
    "表25": 18,
    "表26": 19,
    "表27": 19,
    "表28": 20,
    "表29": 20,
    "表30": 21,
    "表31": 22,
    "表32": 23,
    "表33": 24,
    "表34": 25,
    "表35": 26,
}


def enrich_payload(payload: dict[str, Any]) -> dict[str, int]:
    """只向缺少来源页的变压器记录写入显式表题页码。"""

    rows = payload.get("rows", [])
    added = 0
    unchanged = 0
    unknown = 0
    for row in rows:
        table = str(row.get("table", ""))
        page = TABLE_PAGE.get(table)
        if page is None:
            unknown += 1
            continue
        if row.get("source_page") not in (None, "", [], {}):
            unchanged += 1
            continue
        row["source_page"] = page
        added += 1
    return {"added": added, "unchanged": unchanged, "unknown_table": unknown}


def run(path: Path = RESOURCE, apply: bool = False) -> dict[str, Any]:
    path = Path(path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    before = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    counts = enrich_payload(payload)
    candidate = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if apply and counts["added"]:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "resource": str(path),
        "apply": apply,
        "table_mapping_count": len(TABLE_PAGE),
        **counts,
        # 预览不会触碰文件；该标记表示磁盘文件是否实际改变，而不是
        # 候选内存对象是否包含待补元数据。
        "payload_changed": bool(apply and before != candidate),
        "pdf_page_basis": "GB 20052-2024原PDF表题所在页，PDF页码从1开始",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补录GB 20052-2024变压器记录来源页码")
    parser.add_argument("--resource", type=Path, default=RESOURCE)
    parser.add_argument("--apply", action="store_true", help="写回source_page元数据")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.resource, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
