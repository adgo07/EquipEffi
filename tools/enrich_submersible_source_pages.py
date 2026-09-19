"""为GB 32030-2022潜水电泵表级记录补录已核对的PDF页范围。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "submersible.json"
TABLE_PAGES = {"表1": "4", "表2": "4-5", "表3": "5-6", "表4": "6", "表6": "7-8"}


def enrich_payload(payload: dict[str, Any]) -> dict[str, int]:
    added = 0
    unchanged = 0
    unknown = 0
    for table in payload.get("tables", []):
        name = str(table.get("name", ""))
        page = TABLE_PAGES.get(name)
        if page is None:
            unknown += 1
        elif table.get("source_pages") not in (None, "", [], {}):
            unchanged += 1
        else:
            table["source_pages"] = page
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
    return {"resource": str(path), "apply": apply, "table_pages": TABLE_PAGES, **counts, "payload_changed": bool(apply and before != after)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补录GB 32030-2022潜水电泵来源页范围")
    parser.add_argument("--resource", type=Path, default=RESOURCE)
    parser.add_argument("--apply", action="store_true", help="写回source_pages元数据")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.resource, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
