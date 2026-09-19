"""为GB 19762-2025离心泵机器记录补录已核对的PDF表页范围。

清水泵 ``water.ci`` 是表3记录（第9—10页），石油化工泵 ``chemical`` 的
16条分档记录是表2（第8—9页）。映射只补来源元数据，不修改计算系数、
多项式、边界或单位；默认预览，传入 ``--apply`` 才写回。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "pump.json"
WATER_PAGE = "9-10"
CHEMICAL_PAGE = "8-9"


def _records(payload: dict[str, Any], scope: str) -> list[dict[str, Any]]:
    if scope == "water":
        return list(payload.get("water", {}).get("ci", []))
    # 化工泵记录在标准化机器包中是level_offsets列表。
    return list(payload.get("chemical", {}).get("level_offsets", []))


def enrich_payload(payload: dict[str, Any]) -> dict[str, int]:
    added = 0
    unchanged = 0
    unknown = 0
    for scope, page in (("water", WATER_PAGE), ("chemical", CHEMICAL_PAGE)):
        for row in _records(payload, scope):
            if not isinstance(row, dict) or row.get("data_id") in (None, ""):
                unknown += 1
                continue
            if row.get("source_pages") not in (None, "", [], {}):
                unchanged += 1
            else:
                row["source_pages"] = page
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
        "water_table3_pages": WATER_PAGE,
        "chemical_table2_pages": CHEMICAL_PAGE,
        **counts,
        "payload_changed": bool(apply and before != after),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补录GB 19762-2025离心泵记录来源页范围")
    parser.add_argument("--resource", type=Path, default=RESOURCE)
    parser.add_argument("--apply", action="store_true", help="写回source_pages元数据")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.resource, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
