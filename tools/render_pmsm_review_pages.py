"""渲染GB 30253-2024永磁同步电动机表格页面，生成可读复核索引。

该工具只读取原始PDF和当前(normalized)重建包，不修改标准JSON、校对册或
激活状态。输出每张包含标准表的PDF页面PNG，以及按表号/页码/行数/无数据
单元格汇总的Markdown索引，供人工逐表复核时使用。

示例：
    python tools/render_pmsm_review_pages.py \\
      --pdf "G:\\标准  规范\\02_能耗限额_终端产品\\用能设备\\重点设备能效标准\\4. GB 30253-2024 永磁同步电动机能效限定值及能效等级.pdf" \\
      --output-dir outputs/final_20260829_trace5/GB30253-2024_PMSM_PDF页面复核
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

try:
    import pypdfium2 as pdfium
except ImportError:  # pragma: no cover - 仅在工具环境缺依赖时触发
    pdfium = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"
DEFAULT_PDF = Path(
    r"G:\标准  规范\02_能耗限额_终端产品\用能设备\重点设备能效标准\4. GB 30253-2024 永磁同步电动机能效限定值及能效等级.pdf"
)
DEFAULT_OUTPUT = ROOT / "outputs" / "final_20260829_trace5" / "GB30253-2024_PMSM_PDF页面复核"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load_pack(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("pack_id") != "gb30253_2024_pdf_verified_v1":
        raise ValueError("输入标准包不是本轮GB 30253-2024 PDF重建包")
    tables = payload.get("tables")
    if not isinstance(tables, list) or len(tables) != 29:
        raise ValueError("标准包必须包含29张表")
    return payload


def _page_table_map(pack: dict[str, Any]) -> tuple[list[int], dict[int, list[dict[str, Any]]]]:
    table_pages: dict[int, list[dict[str, Any]]] = {}
    for table in pack["tables"]:
        table_no = int(table["table_no"])
        pages = table.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError(f"表{table_no}缺少PDF页码")
        for page in pages:
            page_no = int(page)
            table_pages.setdefault(page_no, []).append(table)
    return sorted(table_pages), table_pages


def _table_summary(table: dict[str, Any]) -> dict[str, Any]:
    suspicious = 0
    no_data = 0
    for row in table.get("rows", []):
        suspicious += len(row.get("suspicious_cells") or [])
        no_data += len(row.get("no_data_cells") or [])
    return {
        "table_no": int(table["table_no"]),
        "table": str(table.get("table", f"表{table['table_no']}")),
        "product": str(table.get("product", "")),
        "mode": str(table.get("mode", "")),
        "pages": [int(page) for page in table.get("pages", [])],
        "row_count": len(table.get("rows", [])),
        "suspicious_cell_count": suspicious,
        "no_data_cell_count": no_data,
    }


def render(pdf: Path, pack_path: Path, output_dir: Path, *, dpi: int = 120) -> dict[str, Any]:
    if pdfium is None:
        raise RuntimeError("缺少pypdfium2，无法渲染PDF页面")
    pdf = Path(pdf).resolve()
    pack_path = Path(pack_path).resolve()
    output_dir = Path(output_dir).resolve()
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    if not pack_path.is_file():
        raise FileNotFoundError(pack_path)
    if dpi < 72 or dpi > 300:
        raise ValueError("dpi必须位于72～300")
    pack = _load_pack(pack_path)
    page_numbers, page_tables = _page_table_map(pack)
    output_dir.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(str(pdf))
    try:
        if len(document) < max(page_numbers):
            raise ValueError(f"PDF页数不足：需要第{max(page_numbers)}页，实际{len(document)}页")
        rendered_pages: list[dict[str, Any]] = []
        scale = dpi / 72.0
        for page_number in page_numbers:
            page = document[page_number - 1]
            image = page.render(scale=scale).to_pil()
            filename = f"P{page_number:02d}.png"
            target = output_dir / filename
            image.save(target, format="PNG", optimize=True)
            rendered_pages.append({
                "page": page_number,
                "file": filename,
                "sha256": _sha256(target),
                "tables": [int(item["table_no"]) for item in page_tables[page_number]],
                "width": image.width,
                "height": image.height,
            })
            page.close()
    finally:
        document.close()

    table_summaries = [_table_summary(table) for table in pack["tables"]]
    manifest = {
        "standard_code": pack.get("standard_code", "GB 30253-2024"),
        "pack_id": pack.get("pack_id", ""),
        "pack_status": pack.get("status", ""),
        "source_pdf": str(pdf),
        "source_pdf_sha256": _sha256(pdf),
        "pack_path": str(pack_path),
        "render_dpi": dpi,
        "table_count": len(table_summaries),
        "page_count": len(rendered_pages),
        "pages": rendered_pages,
        "tables": table_summaries,
    }
    (output_dir / "复核页面清单.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# GB 30253-2024 永磁同步电动机 PDF 页面复核索引",
        "",
        f"- 标准包：`{manifest['pack_id']}`（当前状态：`{manifest['pack_status']}`）",
        f"- 原始PDF：`{manifest['source_pdf']}`",
        f"- PDF SHA-256：`{manifest['source_pdf_sha256']}`",
        f"- 渲染分辨率：{dpi} DPI；页面数：{len(rendered_pages)}；标准表数：{len(table_summaries)}",
        "- 本索引仅用于人工复核，不代表标准包已完成逐格确认或可以激活。",
        "",
        "## 按标准表",
        "",
        "| 表号 | 产品/模式 | PDF页码 | 功率行数 | 存疑单元格 | 已确认无数据 |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for item in table_summaries:
        pages = ", ".join(str(page) for page in item["pages"])
        lines.append(
            f"| {item['table_no']} | {item['product']} / {item['mode']} | {pages} | "
            f"{item['row_count']} | {item['suspicious_cell_count']} | {item['no_data_cell_count']} |"
        )
    lines.extend(["", "## 按PDF页面", "", "| PDF页码 | 页面图像 | 包含表号 | 图像SHA-256 |", "|---:|---|---|---|"])
    for item in rendered_pages:
        tables = ", ".join(f"表{number}" for number in item["tables"])
        lines.append(f"| {item['page']} | [{item['file']}]({item['file']}) | {tables} | `{item['sha256']}` |")
    (output_dir / "复核页面索引.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="渲染GB30253-2024 PMSM人工复核页面")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dpi", type=int, default=120)
    args = parser.parse_args(argv)
    manifest = render(args.pdf, args.pack, args.output_dir, dpi=args.dpi)
    print(json.dumps({
        "output_dir": str(Path(args.output_dir).resolve()),
        "page_count": manifest["page_count"],
        "table_count": manifest["table_count"],
        "source_pdf_sha256": manifest["source_pdf_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
