"""核对《产业结构调整指导目录（2024年本）》设备相关淘汰条目。

本工具只读取原始PDF，不修改标准资源；它验证当前产业目录资源中的11项
设备原文条目（拆分为13条受控匹配规则）是否能在PDF第134～137页找到对应原文，
并输出人可读报告。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Sequence

try:
    import pymupdf as fitz  # PyMuPDF新名称（仅工具环境依赖）
except ImportError:  # 兼容旧版PyMuPDF
    try:
        import fitz  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover - 工具环境缺少PDF依赖时给出明确提示
        fitz = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path(r"G:\标准  规范\04_政策法规\国家政策\关键政策\产业结构调整指导目录（2024年本）.pdf")
DEFAULT_OUTPUT = ROOT / "outputs" / "final_20260828_web_latest" / "产业结构调整目录_2024_设备条目原文核对.md"

EXPECTED = (
    ("IND2024-MOTOR-YB", 134, "YB 系列（机座号 63～355mm，额定电压 660V 及以下）"),
    ("IND2024-MOTOR-YBF", 134, "YBF 系列（机座号 63～160mm，额定电压 380、660V 或 380/660V）"),
    ("IND2024-MOTOR-YBK", 134, "YBK 系列（机座号 100～355mm，额定电压 380/660V、660/1140V）"),
    ("IND2024-PUMP-BA", 134, "B 型、BA 型单级单吸悬臂式离心泵系列"),
    ("IND2024-PUMP-F", 134, "F 型单级单吸耐腐蚀泵系列"),
    ("IND2024-PUMP-JD", 134, "JD 型长轴深井泵"),
    ("IND2024-COMPRESSOR-3W", 135, "3W-0.9/7（环状阀）空气压缩机"),
    ("IND2024-PUMP-BOILER-FEED", 136, "GC 型低压锅炉给水泵，DG270-140、DG500-140、DG375-185锅炉给水泵"),
    ("IND2024-BOILER-FIXED-GRATE", 136, "固定炉排燃煤锅炉"),
    ("IND2024-COMPRESSOR-L10", 136, "L-10/8、L-10/7 型动力用往复式空气压缩机"),
    ("IND2024-FAN-HIGH-PRESSURE", 136, "8-18 系列、9-27 系列高压离心通风机"),
    ("IND2024-BOILER-COAL-10T", 137, "每小时 10 蒸吨及以下燃煤锅炉"),
    ("IND2024-BOILER-BIOMASS-2T", 137, "每小时 2 蒸吨及以下生物质锅炉"),
)


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value).replace("．", "．")


def verify(pdf: Path = DEFAULT_PDF, resource: Path | None = None) -> dict[str, object]:
    pdf = Path(pdf).resolve()
    if fitz is None:
        raise RuntimeError("缺少PyMuPDF（fitz），无法读取产业目录PDF")
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest().upper()
    document = fitz.open(pdf)
    results: list[dict[str, object]] = []
    try:
        for entry_id, page_number, snippet in EXPECTED:
            page_text = document[page_number - 1].get_text()
            found = _compact(snippet) in _compact(page_text)
            results.append({
                "entry_id": entry_id,
                "page": page_number,
                "snippet": snippet,
                "found": found,
                "evidence": " ".join(line.strip() for line in page_text.splitlines() if line.strip()),
            })
    finally:
        document.close()
    resource_path = Path(resource) if resource is not None else ROOT / "src" / "equipeffi" / "resources" / "elimination_catalog_industry_2024.json"
    expected_ids = {item[0] for item in EXPECTED}
    resource_ids: set[str] = set()
    resource_id_list: list[str] = []
    if resource_path.is_file():
        payload = json.loads(resource_path.read_text(encoding="utf-8"))
        resource_id_list = [
            str(item.get("entry_id", ""))
            for item in payload.get("entries", [])
            if item.get("entry_id")
        ]
        resource_ids = set(resource_id_list)
    missing_resource_ids = sorted(expected_ids - resource_ids)
    extra_resource_ids = sorted(resource_ids - expected_ids)
    duplicate_resource_ids = sorted(
        entry_id for entry_id in resource_ids if resource_id_list.count(entry_id) > 1
    )
    return {
        "pdf": str(pdf),
        "sha256": digest,
        "expected_count": len(EXPECTED),
        "verified_count": sum(bool(item["found"]) for item in results),
        "resource_entry_count": len(resource_id_list),
        "missing_resource_ids": missing_resource_ids,
        "extra_resource_ids": extra_resource_ids,
        "duplicate_resource_ids": duplicate_resource_ids,
        "results": results,
    }


def render_report(result: dict[str, object]) -> str:
    lines = [
        "# 《产业结构调整指导目录（2024年本）》设备条目原文核对",
        "",
        f"- 原始PDF：`{result['pdf']}`",
        f"- SHA-256：`{result['sha256']}`",
        f"- PDF核对结果：{result['verified_count']}/{result['expected_count']} 项在指定页找到原文",
        f"- 机器资源规则数：{result['resource_entry_count']}；清单缺失ID：{len(result['missing_resource_ids'])}；多余ID：{len(result.get('extra_resource_ids', []))}；重复ID：{len(result.get('duplicate_resource_ids', []))}",
        "- 说明：本报告只验证当前已纳入17类设备范围的13条受控规则对应的11项原文条目，不代表目录全文已结构化。",
        "",
        "| 数据ID | PDF页码 | 资源条目原文片段 | 找到 |",
        "|---|---:|---|---|",
    ]
    for item in result["results"]:
        lines.append(f"| {item['entry_id']} | {item['page']} | {item['snippet']} | {'是' if item['found'] else '否'} |")
    lines.extend(["", "## 页面证据", ""])
    for item in result["results"]:
        lines.extend([f"### {item['entry_id']}（第{item['page']}页）", "", str(item["evidence"]), ""])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="核对2024年产业目录设备淘汰条目原文")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = verify(args.pdf)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(result), encoding="utf-8")
    print(f"核对：{result['verified_count']}/{result['expected_count']}")
    print(output)
    return 0 if (
        result["verified_count"] == result["expected_count"]
        and not result["missing_resource_ids"]
        and not result.get("extra_resource_ids", [])
        and not result.get("duplicate_resource_ids", [])
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
