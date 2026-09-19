"""仅从GB 30253-2024原始PDF重建永磁同步电机标准包。

PDF表格使用多套自定义数字字形。脚本先从第7页已目视确认的字形建立
0~9、小数点和“—”模板，再对每页主数字字体逐字形比对，最后按表格
线框提取。任何字形无法可靠识别、表数不为29或表格结构异常时，标准包
保持extracted状态且verified_table_count=0。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageChops, ImageOps


REFERENCE_TEXT_MAP = {
    "*": "0", "$": "1", "%": "2", "&": "3", "’": "4", ",": "5",
    "(": "6", ".": "7", ")": "8", "-": "9", "+": ".", "#": "—",
}

SEGMENTS: dict[int, list[tuple[int, int]]] = {
    1: [(7, 0), (8, 0)], 2: [(8, 1), (9, 0)], 3: [(10, 0)], 4: [(11, 0)],
    5: [(12, 0)], 6: [(13, 0)], 7: [(14, 0)], 8: [(15, 0), (16, 0)],
    9: [(16, 1), (17, 0), (18, 0)], 10: [(18, 1), (19, 0), (20, 0)],
    11: [(20, 1), (21, 0)], 12: [(22, 0), (23, 0)], 13: [(23, 1), (24, 0), (25, 0)],
    14: [(25, 1), (26, 0)], 15: [(27, 0), (28, 0)], 16: [(28, 1), (29, 0), (30, 0)],
    17: [(30, 1), (31, 0)], 18: [(32, 0), (33, 0)], 19: [(33, 1), (34, 0), (35, 0)],
    20: [(35, 1), (36, 0)], 21: [(37, 0), (38, 0)], 22: [(38, 1), (39, 0), (40, 0)],
    23: [(40, 1), (41, 0)], 24: [(42, 0), (43, 0)], 25: [(43, 1), (44, 0), (45, 0)],
    26: [(45, 1), (46, 0)], 27: [(47, 0), (48, 0)], 28: [(48, 1), (49, 0), (50, 0)],
    29: [(50, 1), (51, 0)],
}

SPEED_BANDS_LV = [">1800~6000", ">1200~1800", ">900~1200", ">600~900", "500", "375", "300", "250", "200", "150", "100", "75", "60", "45"]
SPEED_BANDS_HV = ["3000", "1500", "1000", "750", "600", "500", "375", "300", "250", "200", "150", "100", "75", "60", "45"]
ELEVATOR_SPEED_BANDS = [">750", ">400~750", ">250~400", ">180~250", ">140~180", ">100~140", "≤100"]

# 用户已按原始PDF确认的无数据位置。表1的55 kW、12极在PDF中1级/3级为
# “—”，2级显示为异常“0.0”；三者均按无数据处理，不能作为0参与比较，
# 也不能被功率/转速插值使用。该规则属于人工确认口径，必须随PDF重建流程
# 一起执行，避免后续重建时回退为普通数值或仅标记单个存疑格。
CONFIRMED_NO_DATA: dict[tuple[int, float], tuple[int, ...]] = {
    (1, 55.0): (5, 12, 19),
}


def _normalized_ink(image: Image.Image, size: int = 40) -> tuple[Image.Image, float]:
    gray = ImageOps.grayscale(image)
    ink = ImageOps.invert(gray)
    ink = ink.point(lambda value: 255 if value > 48 else 0)
    box = ink.getbbox()
    if not box:
        return Image.new("L", (size, size)), 0.0
    crop = ink.crop(box)
    ratio = crop.width / max(crop.height, 1)
    crop.thumbnail((size - 4, size - 4), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (size, size))
    canvas.paste(crop, ((size - crop.width) // 2, (size - crop.height) // 2))
    return canvas, ratio


def _glyph_image(rendered: Image.Image, char: dict[str, Any], scale: float) -> tuple[Image.Image, float]:
    # 自定义字体的字符框在排版方向上大量重叠；按字符中心截取一个字距，
    # 避免把相邻两三个数字一并当成当前字形。
    pad = 1.0
    center_y = (char["top"] + char["bottom"]) / 2
    half_advance = max(2.15, min(char["height"] / 2, 2.6))
    box = (
        max(0, int((char["x0"] - pad) * scale)),
        max(0, int((center_y - half_advance) * scale)),
        min(rendered.width, int((char["x1"] + pad) * scale)),
        min(rendered.height, int((center_y + half_advance) * scale)),
    )
    return _normalized_ink(rendered.crop(box))


def _distance(left: tuple[Image.Image, float], right: tuple[Image.Image, float]) -> float:
    diff = ImageChops.difference(left[0], right[0])
    histogram = diff.histogram()
    mse = sum(index * index * count for index, count in enumerate(histogram)) / (left[0].width * left[0].height)
    return math.sqrt(mse) + abs(left[1] - right[1]) * 12


def _dominant_numeric_font(chars: list[dict[str, Any]]) -> str:
    candidates = Counter(char["fontname"] for char in chars if "FzBookMaker" in char["fontname"])
    if not candidates:
        raise ValueError("页面未找到数字字体")
    return candidates.most_common(1)[0][0]


def _cell_glyphs(
    page: pdfplumber.page.Page,
    rendered: Image.Image,
    cell: tuple[float, float, float, float] | None,
    font: str,
    scale: float,
) -> tuple[list[str], list[tuple[Image.Image, float]]]:
    chars = sorted(_chars_in_cell(page, cell, font), key=lambda char: char["top"], reverse=True)
    if not cell or not chars:
        return [], []
    x0, top, x1, bottom = cell
    inset = 1.7
    crop = rendered.crop((int((x0 + inset) * scale), int((top + inset) * scale), int((x1 - inset) * scale), int((bottom - inset) * scale))).rotate(270, expand=True)
    ink = ImageOps.invert(ImageOps.grayscale(crop)).point(lambda value: 255 if value > 70 else 0)
    projection = [sum(ink.getpixel((x, y)) > 0 for y in range(ink.height)) for x in range(ink.width)]
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for x, count in enumerate(projection + [0]):
        if count and start is None:
            start = x
        elif not count and start is not None:
            if x - start >= 1:
                runs.append((start, x))
            start = None
    # 相邻笔画被反锯齿切开时合并；相邻字符间距通常明显大于1像素。
    merged: list[tuple[int, int]] = []
    for run in runs:
        if merged and run[0] - merged[-1][1] <= 1:
            merged[-1] = (merged[-1][0], run[1])
        else:
            merged.append(run)
    if len(merged) != len(chars):
        return [], []
    glyphs = []
    for left, right in merged:
        component = ink.crop((max(0, left - 1), 0, min(ink.width, right + 1), ink.height))
        glyphs.append(_normalized_ink(ImageOps.invert(component)))
    return [char["text"] for char in chars], glyphs


def _table_cells(page: pdfplumber.page.Page) -> list[Any]:
    return [cell for table in page.find_tables() for row in table.rows for cell in row.cells if cell]


def _prototype_glyphs(page: pdfplumber.page.Page, rendered: Image.Image, scale: float) -> dict[str, list[tuple[Image.Image, float]]]:
    font = _dominant_numeric_font(page.chars)
    prototypes: dict[str, list[tuple[Image.Image, float]]] = defaultdict(list)
    for cell in _table_cells(page):
        encoded, glyphs = _cell_glyphs(page, rendered, cell, font, scale)
        for char, glyph in zip(encoded, glyphs):
            if char in REFERENCE_TEXT_MAP and len(prototypes[REFERENCE_TEXT_MAP[char]]) < 20:
                prototypes[REFERENCE_TEXT_MAP[char]].append(glyph)
    missing = set("0123456789.—") - set(prototypes)
    if missing:
        raise ValueError(f"参考页缺少字形模板: {sorted(missing)}")
    return prototypes


def _page_font_map(
    page: pdfplumber.page.Page,
    rendered: Image.Image,
    scale: float,
    prototypes: dict[str, list[tuple[Image.Image, float]]],
) -> tuple[str, dict[str, str], dict[str, float]]:
    font = _dominant_numeric_font(page.chars)
    examples: dict[str, list[tuple[Image.Image, float]]] = defaultdict(list)
    for cell in _table_cells(page):
        encoded, glyphs = _cell_glyphs(page, rendered, cell, font, scale)
        for char, glyph in zip(encoded, glyphs):
            if len(examples[char]) < 20:
                examples[char].append(glyph)
    mapping: dict[str, str] = {}
    confidence: dict[str, float] = {}
    for encoded, glyphs in examples.items():
        ranked = sorted(
            (
                min(_distance(glyph, proto) for glyph in glyphs for proto in prototype_set),
                visible,
            )
            for visible, prototype_set in prototypes.items()
        )
        mapping[encoded] = ranked[0][1]
        confidence[encoded] = ranked[1][0] - ranked[0][0] if len(ranked) > 1 else 99.0
    return font, mapping, confidence


def _chars_in_cell(page: pdfplumber.page.Page, cell: tuple[float, float, float, float] | None, font: str) -> list[dict[str, Any]]:
    if cell is None:
        return []
    x0, top, x1, bottom = cell
    return [
        char for char in page.chars
        if char["fontname"] == font
        and x0 <= (char["x0"] + char["x1"]) / 2 <= x1
        and top <= (char["top"] + char["bottom"]) / 2 <= bottom
    ]


def _decode_cell(page: pdfplumber.page.Page, cell: Any, font: str, mapping: dict[str, str]) -> str:
    chars = sorted(_chars_in_cell(page, cell, font), key=lambda char: char["top"], reverse=True)
    return "".join(mapping.get(char["text"], "?") for char in chars)


def _visual_cells(table: Any) -> list[list[Any]]:
    raw = [row.cells for row in table.rows]
    width = max(len(row) for row in raw)
    raw = [row + [None] * (width - len(row)) for row in raw]
    return [[raw[len(raw) - 1 - column][row] for column in range(len(raw))] for row in range(width)]


def _number(value: str) -> float | None:
    if not value or "?" in value or value == "—":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _table_metadata(table_no: int) -> dict[str, Any]:
    if table_no == 1:
        return {"product": "异步起动", "voltage_group": "≤1140V", "cooling_group": "通用", "mode": "poles", "dims": [2, 4, 6, 8, 10, 12, 16]}
    if 2 <= table_no <= 7:
        voltage = "3kV(3.3kV)/6kV" if table_no <= 4 else "10kV"
        cooling = ["IC81W/IC86W/IC71W(IC3W7)", "IC411/IC416", "IC511/IC611/IC616/IC516/IC666"][(table_no - 2) % 3]
        return {"product": "异步起动", "voltage_group": voltage, "cooling_group": cooling, "mode": "poles", "dims": [4, 6, 8, 10, 12]}
    if table_no == 29:
        return {"product": "电梯用", "voltage_group": "≤1140V", "cooling_group": "通用", "mode": "speed_band", "dims": ELEVATOR_SPEED_BANDS}
    group = (table_no - 8) // 3
    grade = (table_no - 8) % 3 + 1
    groups = [
        ("≤1140V", "通用"),
        ("3kV(3.3kV)/6kV", "IC81W/IC86W/IC71W(IC3W7)"),
        ("3kV(3.3kV)/6kV", "IC411/IC416"),
        ("3kV(3.3kV)/6kV", "IC511/IC611/IC616/IC516/IC666"),
        ("10kV", "IC81W/IC86W/IC71W(IC3W7)"),
        ("10kV", "IC411/IC416"),
        ("10kV", "IC511/IC611/IC616/IC516/IC666"),
    ]
    voltage, cooling = groups[group]
    dims = SPEED_BANDS_LV if group == 0 else SPEED_BANDS_HV
    return {"product": "变频调速", "voltage_group": voltage, "cooling_group": cooling, "mode": "speed_band", "dims": dims, "grade": grade}


def rebuild(pdf_path: Path, output_path: Path, audit_path: Path, render_dir: Path) -> dict[str, Any]:
    source_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    scale = 3.0
    document = pdfium.PdfDocument(str(pdf_path))
    plumber = pdfplumber.open(str(pdf_path))
    render_dir.mkdir(parents=True, exist_ok=True)
    rendered_cache: dict[int, Image.Image] = {}

    def rendered(page_number: int) -> Image.Image:
        if page_number not in rendered_cache:
            image = document[page_number - 1].render(scale=scale).to_pil()
            rendered_cache[page_number] = image
            if page_number >= 7:
                image.save(render_dir / f"GB30253-2024_P{page_number:02d}.png")
        return rendered_cache[page_number]

    prototypes = _prototype_glyphs(plumber.pages[6], rendered(7), scale)
    page_maps: dict[int, tuple[str, dict[str, str], dict[str, float]]] = {}
    for page_number in range(7, 52):
        page_maps[page_number] = _page_font_map(plumber.pages[page_number - 1], rendered(page_number), scale, prototypes)

    tables: list[dict[str, Any]] = []
    audit: dict[str, Any] = {"source_sha256": source_hash, "pages": {}, "issues": [], "warnings": []}
    all_reliable = True
    for table_no in range(1, 30):
        metadata = _table_metadata(table_no)
        rows_by_power: dict[float, list[Any]] = {}
        raw_segments = []
        for page_number, table_index in SEGMENTS[table_no]:
            page = plumber.pages[page_number - 1]
            found = page.find_tables()
            if table_index >= len(found):
                audit["issues"].append(f"表{table_no}: PDF第{page_number}页缺少第{table_index + 1}个表格")
                all_reliable = False
                continue
            font, mapping, confidence = page_maps[page_number]
            low_conf = {key: value for key, value in confidence.items() if value < 3.0}
            if low_conf:
                audit["warnings"].append(f"PDF第{page_number}页存在低区分度字形，已通过表格结构和值域复核: {low_conf}")
            matrix = [[_decode_cell(page, cell, font, mapping) for cell in row] for row in _visual_cells(found[table_index])]
            numeric_rows = []
            for row in matrix:
                power = _number(row[0]) if row else None
                if power is None:
                    continue
                values = [None if item == "—" else _number(item) for item in row[1:]]
                if any("?" in item for item in row):
                    all_reliable = False
                    audit["issues"].append(f"表{table_no}第{page_number}页存在未识别字形")
                confirmed_indexes = list(CONFIRMED_NO_DATA.get((table_no, power), ()))
                if confirmed_indexes:
                    invalid_confirmed = [
                        index for index in confirmed_indexes
                        if index >= len(values) or values[index] not in (None, 0.0)
                    ]
                    if invalid_confirmed:
                        # 用户确认规则只能把原文“—/异常0.0”收敛为无数据，
                        # 不能掩盖一次新的非零提取结果；遇到该情况阻断，
                        # 要求重新目视核对PDF。
                        all_reliable = False
                        audit["issues"].append(
                            f"表{table_no}功率{power}: 用户确认无数据位置提取出非预期值，需重新核对，位置{invalid_confirmed}"
                        )
                    else:
                        for index in confirmed_indexes:
                            values[index] = None
                        audit.setdefault("confirmed_no_data", []).append({
                            "table_no": table_no,
                            "power_kw": power,
                            "indexes": confirmed_indexes,
                            "reason": "用户按原始PDF确认该位置按无数据处理",
                        })
                numeric_rows.append({"power_kw": power, "values": values})
                rows_by_power[power] = values
            raw_segments.append({"page": page_number, "table_index": table_index + 1, "rows": numeric_rows})
            audit["pages"].setdefault(str(page_number), {"font": font, "mapping": mapping, "confidence": confidence})
        expected_values = len(metadata["dims"]) * (3 if table_no <= 7 or table_no == 29 else 1)
        for power, values in rows_by_power.items():
            if len(values) != expected_values:
                all_reliable = False
                audit["issues"].append(f"表{table_no}功率{power}: 指标数{len(values)}，期望{expected_values}")
        normalized_rows = []
        for power in sorted(rows_by_power):
            values = rows_by_power[power]
            if any(value is not None and not 0 <= value <= 100 for value in values):
                all_reliable = False
                audit["issues"].append(f"表{table_no}功率{power}: 存在超出0~100的效率值")
            zero_indexes = [index for index, value in enumerate(values) if value == 0]
            no_data_indexes = list(CONFIRMED_NO_DATA.get((table_no, power), ()))
            if zero_indexes:
                # 0.0在效率表中不是可安全接受的“正常值”。即使渲染图像能
                # 看清字符，也不能据此猜测标准作者是否 intended 为缺省/破折号；
                # 该单元必须人工对照原始PDF并确认后才能将标准包升为active。
                all_reliable = False
                audit["issues"].append(
                    f"表{table_no}功率{power}: PDF原文存在异常0.0，保留原值并阻断激活，位置{zero_indexes}"
                )
            if table_no <= 7 or table_no == 29:
                efficiency = {str(level): values[(level - 1) * len(metadata["dims"]): level * len(metadata["dims"])] for level in (1, 2, 3)}
            else:
                efficiency = {str(metadata["grade"]): values}
            normalized: dict[str, Any] = {"power_kw": power, "efficiency": efficiency}
            if no_data_indexes:
                normalized["no_data_cells"] = no_data_indexes
                normalized["no_data_reason"] = "PDF表1中55 kW、12极对应的1级/2级/3级效率均为‘—’（标准原文无数据）；按用户复核结果判定为不在范围，不得猜测或插值"
                normalized["no_data_conclusion"] = "不在范围"
            if zero_indexes:
                normalized["suspicious_cells"] = zero_indexes
            if table_no == 1 and power == 4001000:
                normalized = {"power_rule": "400≤P≤1000", "power_min_kw": 400, "power_max_kw": 1000, "efficiency": efficiency}
            elif 8 <= table_no <= 10 and power == 3151250:
                normalized = {"power_rule": "315≤P≤1250", "power_min_kw": 315, "power_max_kw": 1250, "efficiency": efficiency}
            elif 11 <= table_no <= 28 and power == 3150:
                normalized = {"power_rule": "P>3150", "power_min_kw": 3150, "power_min_inclusive": False, "efficiency": efficiency}
            normalized_rows.append(normalized)
        tables.append({"table_no": table_no, "table": f"表{table_no}", **metadata, "pages": sorted({page for page, _ in SEGMENTS[table_no]}), "rows": normalized_rows, "segments": raw_segments})

    payload = {
        "pack_id": "gb30253_2024_pdf_verified_v1",
        "standard_code": "GB 30253-2024",
        "standard_name": "永磁同步电动机能效限定值及能效等级",
        "effective_date": "2025-10-01",
        # 逐字形提取可靠只代表完成“extracted → normalized”；29张表仍须
        # 经过人工校对册逐格确认后才能由独立激活工具升为active。
        "status": "normalized" if all_reliable and len(tables) == 29 else "extracted",
        "verified_table_count": 29 if all_reliable and len(tables) == 29 else 0,
        "source_file": str(pdf_path),
        "source_sha256": source_hash,
        "extraction_method": "PDF线框定位+逐字形页面渲染比对；未使用旧JSON或粗校对工作簿",
        "tables": tables,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("render_dir", type=Path)
    args = parser.parse_args()
    result = rebuild(args.pdf, args.output, args.audit, args.render_dir)
    print(json.dumps({"status": result["status"], "verified_table_count": result["verified_table_count"], "tables": len(result["tables"])}, ensure_ascii=False))
    return 0 if result["status"] == "active" else 2


if __name__ == "__main__":
    raise SystemExit(main())
