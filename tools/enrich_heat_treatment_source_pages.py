"""为GB/T 36561-2018热处理设备表8记录补录明确的PDF页码。

资源已登记表8位于原PDF第11页；燃料系数记录已有第12页，本工具只为缺少
页码的表8记录增加 ``source_page=11``，不改动任何指标、单位或燃料系数。
默认预览，传入 ``--apply`` 才写回机器包。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "heat_treatment.json"
TABLE8_PAGE = 11


def enrich_payload(payload: dict[str, Any]) -> dict[str, int]:
    rows = payload.get("table8", [])
    added = 0
    unchanged = 0
    for row in rows:
        if row.get("source_page") not in (None, "", [], {}):
            unchanged += 1
        else:
            row["source_page"] = TABLE8_PAGE
            added += 1
    return {"added": added, "unchanged": unchanged}


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
        "table8_source_page": TABLE8_PAGE,
        **counts,
        "payload_changed": bool(apply and before != after),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补录GB/T 36561-2018表8来源页码")
    parser.add_argument("--resource", type=Path, default=RESOURCE)
    parser.add_argument("--apply", action="store_true", help="写回source_page元数据")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.resource, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
