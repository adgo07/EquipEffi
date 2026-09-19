"""审计 HVAC 标准数据中的数值分档边界。

该工具只读取 ``hvac_thresholds.json``，按产品、表号、条件和指标分组，
检查相邻容量区间的开闭端点、重叠、空档及反向区间。它不推断标准原文，
也不修改任何机器数据；发现问题后由人工回到PDF核对。
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "hvac_thresholds.json"


def _number(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def _inclusive(record: dict[str, Any], key: str) -> bool:
    # 数据生成器仅在原文明确为开区间时写入False；缺失或None表示默认闭合。
    return record.get(key) is not False


def _group_key(device: str, record: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    conditions = json.dumps(record.get("conditions", {}), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    gates = json.dumps(record.get("fixed_gates", []), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        device,
        str(record.get("table", "")),
        str(record.get("range_metric", "")),
        str(record.get("metric_field", "")),
        str(record.get("metric_name", "")),
        conditions + "|gates=" + gates,
    )


def audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for device, section in (payload.get("devices", {}) or {}).items():
        if not isinstance(section, dict):
            continue
        for record in section.get("records", []) or []:
            if isinstance(record, dict) and record.get("range_metric"):
                groups[_group_key(str(device), record)].append(record)

    findings: list[dict[str, Any]] = []
    records_checked = 0
    groups_checked = 0
    for key, records in groups.items():
        if len(records) < 2:
            continue
        groups_checked += 1
        parsed: list[tuple[Decimal | None, Decimal | None, dict[str, Any]]] = []
        for record in records:
            lower = _number(record.get("min"))
            upper = _number(record.get("max"))
            if record.get("min") not in (None, "") and lower is None:
                findings.append({"type": "invalid_bound", "group": key, "data_id": record.get("data_id"), "bound": "min", "value": record.get("min")})
                continue
            if record.get("max") not in (None, "") and upper is None:
                findings.append({"type": "invalid_bound", "group": key, "data_id": record.get("data_id"), "bound": "max", "value": record.get("max")})
                continue
            if lower is not None and upper is not None:
                if lower > upper or (lower == upper and not (_inclusive(record, "min_inclusive") and _inclusive(record, "max_inclusive"))):
                    findings.append({"type": "empty_or_reversed", "group": key, "data_id": record.get("data_id"), "min": str(lower), "max": str(upper)})
                    continue
            parsed.append((lower, upper, record))
        parsed.sort(key=lambda item: (item[0] is not None, item[0] if item[0] is not None else Decimal(0)))
        records_checked += len(parsed)
        for previous, current in zip(parsed, parsed[1:]):
            previous_min, previous_max, previous_record = previous
            current_min, current_max, current_record = current
            if previous_max is None:
                findings.append({"type": "overlap_or_unordered", "group": key, "previous_data_id": previous_record.get("data_id"), "data_id": current_record.get("data_id")})
                continue
            if current_min is None:
                findings.append({"type": "overlap_or_unordered", "group": key, "previous_data_id": previous_record.get("data_id"), "data_id": current_record.get("data_id")})
                continue
            if previous_max < current_min:
                relation = "gap"
            elif previous_max > current_min:
                relation = "overlap"
            elif _inclusive(previous_record, "max_inclusive") and _inclusive(current_record, "min_inclusive"):
                relation = "overlap"
            elif not _inclusive(previous_record, "max_inclusive") and not _inclusive(current_record, "min_inclusive"):
                relation = "gap"
            else:
                relation = "contiguous"
            if relation != "contiguous":
                findings.append({
                    "type": relation,
                    "group": key,
                    "boundary": str(previous_max),
                    "previous_data_id": previous_record.get("data_id"),
                    "data_id": current_record.get("data_id"),
                    "previous_max_inclusive": _inclusive(previous_record, "max_inclusive"),
                    "current_min_inclusive": _inclusive(current_record, "min_inclusive"),
                })
    return {
        "source": str(DEFAULT_SOURCE),
        "group_count": len(groups),
        "groups_checked": groups_checked,
        "records_checked": records_checked,
        "finding_count": len(findings),
        "findings": findings,
        "is_valid": not findings,
    }


def audit(path: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    source = Path(path).resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    result = audit_payload(payload)
    result["source"] = str(source)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="审计HVAC容量分档边界")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.source)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(text, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0 if result["is_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
