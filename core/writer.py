"""
core/writer.py - zip补丁写回引擎（图片/格式保留的关键）

原理：xlsx 本质是 zip 包。本模块只在 zip 层替换目标单元格的 XML 值，
其余条目（xl/media/ 图片、样式、图表、批注、DISPIMG 公式）原样复制，
因此图片/格式 100% 保留。这是"铭牌照片必须保留"需求的技术根基。

用法：
    patch_cells(输入.xlsx, 输出.xlsx, {
        "变压器": {"T4": "3级", "N4": 10600},
        "低压电动机": {"P5": "无法判定"},
    })

注意：
- 输出路径不能等于输入路径（先复制再改，或直接指定新文件）
- 数值用 repr 写入（Excel XML 数字格式）；文本用 inlineStr（Excel/WPS 均支持）
- 只改值，绝不动样式属性（s=）、图片、公式列
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

M_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _q(tag: str) -> str:
    """主命名空间限定名"""
    return f"{{{M_NS}}}{tag}"


def _col_num(ref: str) -> int:
    """'AB12' -> 28（列字母转数字，1基）"""
    m = re.match(r"([A-Z]+)(\d+)", ref)
    col = 0
    for ch in m.group(1):
        col = col * 26 + (ord(ch) - 64)
    return col


def _sheet_paths(xlsx: Path) -> dict:
    """sheet名 -> zip内xml路径（如 xl/worksheets/sheet1.xml）"""
    with zipfile.ZipFile(xlsx) as z:
        wb_root = ET.fromstring(z.read("xl/workbook.xml"))
        rel_root = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.get("Id"): rel.get("Target", "") for rel in rel_root}
    paths = {}
    for sh in wb_root.find(_q("sheets")) or []:
        name = sh.get("name")
        r_id = sh.get(f"{{{R_NS}}}id")
        target = rel_map.get(r_id, "")
        if not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        paths[name] = target
    return paths


def _set_cell(xml_bytes: bytes, ref: str, value) -> bytes:
    """在sheet XML中设置一个单元格的值，返回新XML字节。

    - 已存在的单元格：清空旧值（v/f/is/t子元素与t属性），写入新值
    - 不存在的单元格：按行列序在正确位置新建
    - 数字 -> <v>repr</v>；文本 -> inlineStr；bool -> t="b"
    """
    root = ET.fromstring(xml_bytes)
    sheet_data = root.find(_q("sheetData"))
    if sheet_data is None:
        raise ValueError("sheet 无 sheetData 节点")

    m = re.match(r"([A-Z]+)(\d+)", ref)
    row_num, col_num = int(m.group(2)), _col_num(ref)

    # 定位已有单元格
    target = None
    for c in sheet_data.iter(_q("c")):
        if c.get("r") == ref:
            target = c
            break

    if target is None:
        # 新建：定位/创建行
        row_el = None
        for r in sheet_data.findall(_q("row")):
            if int(r.get("r", 0)) == row_num:
                row_el = r
                break
        if row_el is None:
            row_el = ET.Element(_q("row"), {"r": str(row_num)})
            rows = sheet_data.findall(_q("row"))
            pos = 0
            for i, r in enumerate(rows):
                pos = i + 1
                if int(r.get("r", 0)) > row_num:
                    pos = i
                    break
            sheet_data.insert(pos, row_el)
        # 新建：插入列的正确位置
        target = ET.Element(_q("c"), {"r": ref})
        cells = row_el.findall(_q("c"))
        pos = 0
        for i, c in enumerate(cells):
            pos = i + 1
            if _col_num(c.get("r", "A1")) > col_num:
                pos = i
                break
        row_el.insert(pos, target)

    # 清空旧内容（保留样式属性 s=）
    for child in list(target):
        if child.tag in (_q("v"), _q("f"), _q("is"), _q("t")):
            target.remove(child)
    target.attrib.pop("t", None)

    # 写入新值
    if isinstance(value, bool):
        target.set("t", "b")
        v = ET.SubElement(target, _q("v"))
        v.text = "1" if value else "0"
    elif isinstance(value, (int, float)):
        v = ET.SubElement(target, _q("v"))
        v.text = repr(value)
    else:
        target.set("t", "inlineStr")
        is_el = ET.SubElement(target, _q("is"))
        t = ET.SubElement(is_el, _q("t"))
        t.set(XML_SPACE, "preserve")
        t.text = str(value)

    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def patch_cells(xlsx_path, out_path, changes: dict) -> dict:
    """批量修改单元格值，其余内容（图片/格式/公式列）原样保留。

    Args:
        xlsx_path: 输入文件路径
        out_path:  输出文件路径（不能等于输入）
        changes:   {sheet名: {单元格引用: 值}}，如 {"变压器": {"T4": "3级"}}

    Returns:
        {"patched_sheets": {sheet名: 单元格数}, "media_count": 图片数}
    """
    xlsx_path = Path(xlsx_path)
    out_path = Path(out_path)
    if xlsx_path.resolve() == out_path.resolve():
        raise ValueError("输出路径不能与输入路径相同")

    paths = _sheet_paths(xlsx_path)
    patched = {}

    with zipfile.ZipFile(xlsx_path) as zin, \
         zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            for sheet_name, cells in changes.items():
                if item.filename == paths.get(sheet_name):
                    xml = data
                    for ref, value in cells.items():
                        xml = _set_cell(xml, ref, value)
                    data = xml
                    patched[sheet_name] = len(cells)
                    break
            zout.writestr(item, data)

    # 统计图片数
    with zipfile.ZipFile(out_path) as z:
        media = [n for n in z.namelist() if n.startswith("xl/media/")]

    return {"patched_sheets": patched, "media_count": len(media)}
