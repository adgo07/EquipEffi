"""审计机器标准包的来源追溯覆盖情况。

该工具是只读的。它不会根据标准编号猜测页码，也不会改写标准JSON；
它只统计标准包、数据记录、data_id和来源页码的现有覆盖情况，便于后续
逐包补录PDF页码时校对。PMSM的29张表仍由其专用复核/激活工具负责。

用法：
    python tools/audit_standard_provenance.py
    python tools/audit_standard_provenance.py --output outputs/provenance.json
    python tools/audit_standard_provenance.py --source-dir "G:\\标准  规范\\02_能耗限额_终端产品\\用能设备\\重点设备能效标准"
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MANIFEST = SRC / "equipeffi" / "standard_manifest.json"

# 只做文件名提示，不把这些提示当作已核验页码或数据来源。文件名来自
# 项目标准目录，实际存在性只有在传入 --source-dir 时才检查。
SOURCE_HINTS = {
    "GB 20052-2024": "GB 20052-2024",
    "GB 18613-2020": "GB+18613-2020",
    "GB 30254-2024": "GB 30254-2024",
    "GB 30253-2024": "GB 30253-2024",
    "GB 19153-2019": "GB 19153-2019",
    "GB 19762-2025": "GB 19762-2025",
    "GB 19761-2020": "GB+19761-2020",
    "GB 28381-2012": "GB 28381-2012",
    "GB 32030-2022": "GB 32030-2022",
    "GB 24500-2020": "24500-2020",
    "GB/T 36561-2018": "36561-2018",
    "GB 19577-2024": "GB 19577-2024",
    "GB 29541-2013": "GB 29541",
    "GB 37479-2019": "37479-2019",
    "GB 19576-2019": "19576",
    "GB 21454-2021": "21454-2021",
}

PAGE_KEYS = ("source_page", "source_pages", "pdf_page", "pages")
ID_KEYS = ("data_id", "record_id", "rule_id")
# 这些字段是人工复核/激活的门禁元数据，不是标准值记录。尤其是
# GB 30253-2024 的 activation_review 会为表1/55 kW/12极的三个无数据
# 单元格保留复核证据；若把它们再次遍历，会造成记录数和缺失ID统计重复。
NON_RECORD_KEYS = frozenset({"activation_review", "review_log", "no_data_cells"})
METRIC_KEYS = frozenset(
    {
        "efficiency", "thresholds", "specific_power", "no_load_kw", "load_kw",
        "limits", "values", "ci", "cop", "cop_values", "metric_value",
        "primary_metric_value", "eta", "eta_db", "offsets", "level", "eff",
    }
)


@dataclass(frozen=True)
class PackProvenance:
    device_type: str
    standard_code: str
    pack_id: str
    status: str
    resource: str
    source_hint: str
    source_hint_matches: list[str]
    record_count: int
    records_with_id: int
    records_with_page: int
    records_with_id_and_page: int
    package_level_page: str
    missing_record_id_count: int
    missing_record_page_count: int
    note: str


def _page_value(value: dict[str, Any], inherited: str = "") -> str:
    for key in PAGE_KEYS:
        current = value.get(key)
        if current not in (None, "", [], {}):
            return str(current)
    return inherited


def _iter_records(value: Any, inherited_page: str = "") -> Iterable[tuple[dict[str, Any], str]]:
    """遍历标准值记录，并把表级页码继承给没有单独页码的行。"""

    if isinstance(value, dict):
        page = _page_value(value, inherited_page)
        if _is_record(value):
            yield value, page
            # 记录中的fixed_gates/efficiency等嵌套对象不是独立标准记录，
            # 到此停止，避免把阈值字典重复计数。
            return
        for key, child in value.items():
            if key in NON_RECORD_KEYS:
                continue
            yield from _iter_records(child, page)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_records(child, inherited_page)


def _has_page(value: dict[str, Any]) -> bool:
    return any(value.get(key) not in (None, "", [], {}) for key in PAGE_KEYS)


def _is_record(value: dict[str, Any]) -> bool:
    """识别可能承载标准值的对象，避免把根元数据算作记录。"""

    # 表/容器对象本身可能同时带有表号和页码；真正的记录在其rows、
    # records或segments子列表中，不能把容器再算一遍。
    if any(key in value for key in ("rows", "records", "segments", "tables", "devices", "table8")):
        return False
    if isinstance(value.get("ci"), list) and not any(value.get(key) not in (None, "") for key in ID_KEYS):
        # 清水泵根对象的ci是记录列表；单条ci记录通常带有data_id。
        return False
    if any(value.get(key) not in (None, "") for key in ID_KEYS):
        return True
    keys = set(value)
    if keys & METRIC_KEYS:
        return True
    # 传统抽取包的行记录通常至少包含表号/分类和一个数值字段。
    if (keys & {"table", "name", "type", "category", "power_kw", "capacity_kva"}) and any(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in value.values()
    ):
        return True
    return False


def _source_matches(source_dir: Path | None, hint: str) -> list[str]:
    if source_dir is None or not hint:
        return []
    try:
        candidates = sorted(path.name for path in source_dir.rglob("*.pdf") if hint.lower() in path.name.lower())
    except OSError:
        return []
    return candidates


def audit(manifest_path: Path = MANIFEST, source_dir: Path | None = None) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows: list[PackProvenance] = []
    warnings: list[str] = []
    for entry in manifest.get("packs", []):
        device_type = str(entry.get("device_type", ""))
        source = (manifest_path.parent / str(entry.get("source", ""))).resolve()
        standard_code = str(entry.get("standard_code", ""))
        hint = SOURCE_HINTS.get(standard_code, "")
        matches = _source_matches(source_dir, hint)
        if not source.is_file():
            warnings.append(f"{device_type}:机器标准包不存在：{source}")
            payload: dict[str, Any] = {}
        else:
            payload = json.loads(source.read_text(encoding="utf-8"))
        # 多个内部类型会复用一个JSON。按manifest内部类型取子树，避免把
        # HVAC五类或离心泵水/化工两类重复计入同一个标准包。
        scoped_payload: Any = payload
        devices = payload.get("devices") if isinstance(payload, dict) else None
        if isinstance(devices, dict) and device_type in devices:
            scoped_payload = devices[device_type]
        elif device_type == "pump_water" and isinstance(payload, dict) and "water" in payload:
            scoped_payload = payload["water"]
        elif device_type == "pump_chemical" and isinstance(payload, dict) and "chemical" in payload:
            scoped_payload = payload["chemical"]
        record_pairs = list(_iter_records(scoped_payload))
        records = [item for item, _ in record_pairs]
        with_ids = sum(1 for item in records if any(item.get(key) not in (None, "") for key in ID_KEYS))
        with_pages = sum(1 for item, inherited_page in record_pairs if _has_page(item) or inherited_page)
        package_pages = next((str(payload.get(key)) for key in PAGE_KEYS if payload.get(key) not in (None, "", [], {})), "")
        with_id_and_page = sum(
            1 for (item, inherited_page) in record_pairs
            if any(item.get(key) not in (None, "") for key in ID_KEYS)
            and (_has_page(item) or inherited_page)
        )
        missing_id = len(records) - with_ids
        missing_page = len(records) - with_pages
        note_parts: list[str] = []
        if not records:
            note_parts.append("未识别到标准值记录")
        if missing_id:
            note_parts.append("部分记录没有显式data_id（校对册可使用稳定路径ID，机器包仍建议补录）")
        if missing_page:
            note_parts.append("部分记录没有记录级PDF页码；未据此推断页码")
        if str(entry.get("status", "")) == "normalized":
            note_parts.append("标准包未激活，来源覆盖不改变激活门禁")
        rows.append(
            PackProvenance(
                device_type=device_type,
                standard_code=standard_code,
                pack_id=str(entry.get("pack_id", "")),
                status=str(entry.get("status", payload.get("status", ""))),
                resource=str(source),
                source_hint=hint,
                source_hint_matches=matches,
                record_count=len(records),
                records_with_id=with_ids,
                records_with_page=with_pages,
                records_with_id_and_page=with_id_and_page,
                package_level_page=package_pages,
                missing_record_id_count=missing_id,
                missing_record_page_count=missing_page,
                note="；".join(note_parts),
            )
        )
    complete = [row for row in rows if row.record_count and row.records_with_id_and_page == row.record_count]
    return {
        "manifest": str(manifest_path),
        "source_dir": str(Path(source_dir).resolve()) if source_dir else "",
        "pack_count": len(rows),
        "packs_with_complete_record_id_and_page": len(complete),
        "warnings": warnings,
        "packs": [asdict(row) for row in rows],
        "interpretation": (
            "本报告只反映机器标准包中已经登记的来源字段；缺少页码不代表标准值错误，"
            "也不允许按标准编号或相邻表格猜测页码。"
        ),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 标准数据来源覆盖审计",
        "",
        "本报告为只读统计，不改写标准JSON；缺少记录级页码时不作猜测。",
        "",
        f"- 标准包数：{report['pack_count']}",
        f"- 记录ID和记录级页码均完整的标准包：{report['packs_with_complete_record_id_and_page']}",
        f"- 外部来源目录：{report.get('source_dir') or '未指定'}",
        "",
        "| 内部类型 | 标准 | 状态 | 记录数 | 有ID | 有页码 | ID+页码 | 待补记录ID | 待补记录页码 | 来源文件提示 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in report["packs"]:
        matches = "、".join(item["source_hint_matches"]) or item["source_hint"] or "未配置"
        lines.append(
            f"| {item['device_type']} | {item['standard_code']} | {item['status']} | "
            f"{item['record_count']} | {item['records_with_id']} | {item['records_with_page']} | "
            f"{item['records_with_id_and_page']} | {item['missing_record_id_count']} | "
            f"{item['missing_record_page_count']} | {matches} |"
        )
        if item["note"]:
            lines.append(f"| 备注 | {item['note']} | | | | | | | | |")
    if report["warnings"]:
        lines.extend(["", "## 审计警告", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="审计标准包来源追溯覆盖")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--source-dir", type=Path, help="可选：标准PDF目录，仅用于文件名存在性提示")
    parser.add_argument("--output", type=Path, help="可选：输出JSON报告")
    parser.add_argument("--markdown", type=Path, help="可选：输出人可读Markdown报告")
    args = parser.parse_args(argv)
    report = audit(args.manifest, args.source_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
