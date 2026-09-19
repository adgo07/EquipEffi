from __future__ import annotations

from decimal import Decimal
from html import escape
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

from ...application.ports.v4_workbook import V4WorkbookEvaluationRow, V4WorkbookWriter
from ...application.services.v4_template_contract import V4FieldDefinition
from .ooxml_reader import OOXMLReadError, OOXMLWorkbook
from .template_resource import V4TemplateResource
from .v4_reader import V4WorkbookReaderImpl, _header_name


class V4WorkbookWriteError(ValueError):
    """V4结果工作簿无法安全写回。"""


TRACE_HEADERS: tuple[str, ...] = (
    "记录ID", "设备sheet", "Excel行号", "步骤序号", "步骤类型", "规则/输入", "输出", "单位",
    "表号", "匹配条件", "插值端点", "插值系数", "比较方向", "阈值", "是否通过", "标准条款",
    "淘汰口径", "数据版本",
)


def _column_letters(index: int) -> str:
    value = index + 1
    letters = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _safe_text(value: Any) -> str:
    text = str(value)
    return "".join(char for char in text if ord(char) in {9, 10, 13} or ord(char) >= 32)


def _xml_value(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, ""
    if isinstance(value, bool):
        return True, "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return True, str(value)
    return False, _safe_text(value)


def _normalize_key(value: Any) -> str:
    return re.sub(r"[\s\r\n（）()\[\]【】]", "", str(value or "")).strip()


def _base_metric_key(key: str) -> str:
    # 评价器常用“显示名称_单位”记录；只取显示名称便于匹配V4结果列。
    return str(key).split("_", 1)[0]


def _metric_value(result: Any, field: V4FieldDefinition) -> Any:
    if field.field_id == "conclusion" or field.display_name == "能效等级":
        return result.conclusion.value
    if field.field_id in {"reference_grade", "reference_conclusion"} or field.display_name == "参考能效等级":
        return result.reference_conclusion.value if result.reference_conclusion else ""
    if field.display_name == "判定说明":
        return result.explanation
    if field.display_name == "缺失信息":
        return "、".join(result.missing_fields)
    if field.field_id == "auto_note" or field.display_name == "自动备注":
        issues = getattr(result, "data_quality_issues", ())
        if not issues:
            return None
        return "；".join(str(item.get("message", "")) for item in issues if item.get("message"))

    if field.field_id in {"standard_code", "adopted_standard"}:
        return result.standard_reference.get("standard_code", "")
    if field.field_id == "standard_table":
        return result.standard_reference.get("table", "")
    if field.field_id in {"primary_metric_name", "query_metric_name"}:
        # HVAC评价器以实际指标名称作为actual_metrics的键，例如SEER/APF/IPLV。
        for key in result.actual_metrics:
            if key and not str(key).endswith(("_%", "_W", "_kW")):
                return key
    # 配置sheet中的显示名与评价器内部键有少量不可通过下划线/括号
    # 自动匹配的情况，显式保留这些跨层字段映射。
    field_aliases: dict[str, tuple[str, ...]] = {
        "b2_d2": ("b2/D2", "b₂/D₂"),
        "compression_correction": ("压缩性修正系数",),
        "circum_speed": ("叶轮圆周速度", "叶轮圆周速度_m/s"),
        "specific_speed": ("比转速", "轮毂比", "轮毂比标准分档"),
        "limit_value": ("限定值", "能效限定值"),
        "saving_value": ("节能评价值",),
        "fuel_factor": ("燃料系数", "燃料折标系数_kgce每原单位"),
        "electric_specific": ("电炉可比单耗",),
        "fuel_specific": ("燃料炉可比单耗",),
        "cop_minus12_limit": ("COP(-12℃)", "固定门槛:COP(-12℃)"),
        "cop_minus20_limit": ("COP(-20℃)", "固定门槛:COP(-20℃)"),
        "eer_min_l1": ("1级EERmin",),
        "eer_min_l2": ("2级EERmin",),
        "eer_min_l3": ("3级EERmin",),
    }
    aliases = field_aliases.get(field.field_id, ())
    for alias in aliases:
        alias_key = _normalize_key(alias)
        for mapping in (result.limits, result.calculated_metrics, result.actual_metrics):
            for key, value in mapping.items():
                normalized_key = _normalize_key(str(key))
                if normalized_key == alias_key or _base_metric_key(normalized_key) == alias_key:
                    return value
    # 对已有显式映射的字段不再进行宽松的“子串”匹配，避免把电炉
    # 可比单耗误写到燃料炉列（或把某个结构结果写入相邻结果列）。
    if aliases:
        return None

    mappings: tuple[Mapping[str, Any], ...] = (result.limits, result.calculated_metrics, result.actual_metrics)
    display = _normalize_key(field.display_name)
    for mapping in mappings:
        for key, value in mapping.items():
            base = _normalize_key(_base_metric_key(str(key)))
            if base == display or base in display or display in base:
                return value

    # V4字段“1级对应效率指标”等与评价器的“1级效率”键存在“对应/指标”文字差异。
    level_match = re.search(r"([1-5])级", display)
    if level_match:
        level = level_match.group(1)
        for mapping in mappings:
            for key, value in mapping.items():
                if str(key).startswith(f"{level}级") or f"-{level}级" in str(key):
                    if "指标" in display or "效率" in display or field.field_id.startswith(("grade", "no_load", "load")):
                        return value
    return None


def _replace_type(attrs: str, string_value: bool) -> str:
    attrs = re.sub(r'\s+t="[^"]*"', "", attrs)
    if string_value:
        attrs = f'{attrs} t="inlineStr"'
    return attrs


def _cell_fragment(reference: str, value: Any, style_attrs: str = "") -> str:
    numeric, text = _xml_value(value)
    attrs = re.sub(r'\s+r="[^"]*"', "", style_attrs)
    attrs = _replace_type(attrs, not numeric)
    attrs = f'{attrs} r="{reference}"'
    if numeric:
        body = f"<v>{escape(text, quote=False)}</v>" if text != "" else ""
    else:
        body = f"<is><t>{escape(text, quote=False)}</t></is>" if text != "" else ""
    return f'<c{attrs}>{body}</c>'


def _set_cell(sheet_xml: str, row_number: int, column_index: int, value: Any) -> str:
    reference = f"{_column_letters(column_index)}{row_number}"
    cell_start = 0
    while True:
        cell_start = sheet_xml.find("<c", cell_start)
        if cell_start < 0:
            break
        if cell_start + 2 < len(sheet_xml) and sheet_xml[cell_start + 2] not in {" ", "\t", ">", "/"}:
            cell_start += 2
            continue
        open_end = sheet_xml.find(">", cell_start)
        if open_end < 0:
            break
        open_tag = sheet_xml[cell_start : open_end + 1]
        if f'r="{reference}"' not in open_tag:
            cell_start = open_end + 1
            continue
        attrs = open_tag[2:-1]
        if attrs.endswith("/"):
            attrs = attrs[:-1]
            return sheet_xml[:cell_start] + _cell_fragment(reference, value, attrs) + sheet_xml[open_end + 1 :]
        close_end = sheet_xml.find("</c>", open_end + 1)
        if close_end < 0:
            raise V4WorkbookWriteError(f"单元格XML不完整: {reference}")
        return sheet_xml[:cell_start] + _cell_fragment(reference, value, attrs) + sheet_xml[close_end + 4 :]

    row_pattern = re.compile(rf'<row\b(?=[^>]*\br="{row_number}"[^>]*)[^>]*>')
    row_match = row_pattern.search(sheet_xml)
    if row_match:
        row_close = sheet_xml.find("</row>", row_match.end())
        if row_close < 0:
            raise V4WorkbookWriteError(f"数据行XML不完整: {row_number}")
        return sheet_xml[:row_close] + _cell_fragment(reference, value) + sheet_xml[row_close:]
    sheet_data_close = sheet_xml.find("</sheetData>")
    if sheet_data_close < 0:
        raise V4WorkbookWriteError("sheet缺少sheetData")
    new_row = f'<row r="{row_number}">{_cell_fragment(reference, value)}</row>'
    return sheet_xml[:sheet_data_close] + new_row + sheet_xml[sheet_data_close:]


def _set_cell_in_row(row_xml: str, row_number: int, column_index: int, value: Any) -> str:
    """在已定位的row片段内修改单元格，避免对整张sheet重复扫描。"""
    reference = f"{_column_letters(column_index)}{row_number}"
    cell_start = 0
    while True:
        cell_start = row_xml.find("<c", cell_start)
        if cell_start < 0:
            break
        if cell_start + 2 < len(row_xml) and row_xml[cell_start + 2] not in {" ", "\t", ">", "/"}:
            cell_start += 2
            continue
        open_end = row_xml.find(">", cell_start)
        if open_end < 0:
            break
        open_tag = row_xml[cell_start : open_end + 1]
        if f'r="{reference}"' not in open_tag:
            cell_start = open_end + 1
            continue
        attrs = open_tag[2:-1]
        if attrs.endswith("/"):
            attrs = attrs[:-1]
            return row_xml[:cell_start] + _cell_fragment(reference, value, attrs) + row_xml[open_end + 1 :]
        close_end = row_xml.find("</c>", open_end + 1)
        if close_end < 0:
            raise V4WorkbookWriteError(f"数据行单元格XML不完整: {reference}")
        return row_xml[:cell_start] + _cell_fragment(reference, value, attrs) + row_xml[close_end + 4 :]
    row_close = row_xml.rfind("</row>")
    if row_close < 0:
        raise V4WorkbookWriteError(f"数据行XML不完整: {row_number}")
    return row_xml[:row_close] + _cell_fragment(reference, value) + row_xml[row_close:]


def _set_row_cells(sheet_xml: str, row_number: int, updates: Sequence[tuple[int, Any]]) -> str:
    """一次定位行并写入多个结果列，性能明显优于逐单元格扫描整张sheet。"""
    row_pattern = re.compile(rf'<row\b(?=[^>]*\br="{row_number}"[^>]*)[^>]*>')
    row_match = row_pattern.search(sheet_xml)
    if not row_match:
        for column, value in updates:
            sheet_xml = _set_cell(sheet_xml, row_number, column, value)
        return sheet_xml
    row_close = sheet_xml.find("</row>", row_match.end())
    if row_close < 0:
        raise V4WorkbookWriteError(f"数据行XML不完整: {row_number}")
    row_xml = sheet_xml[row_match.start() : row_close + 6]
    for column, value in updates:
        row_xml = _set_cell_in_row(row_xml, row_number, column, value)
    return sheet_xml[:row_match.start()] + row_xml + sheet_xml[row_close + 6 :]


def _set_rows_cells(sheet_xml: str, updates_by_row: Mapping[int, Sequence[tuple[int, Any]]]) -> str:
    """单次遍历sheetData写入多行，避免1500行时反复从XML开头查找。"""
    if not updates_by_row:
        return sheet_xml
    row_pattern = re.compile(r'<row\b[^>]*\br="(\d+)"[^>]*>.*?</row>', re.DOTALL)
    chunks: list[str] = []
    cursor = 0
    found: set[int] = set()
    for match in row_pattern.finditer(sheet_xml):
        row_number = int(match.group(1))
        chunks.append(sheet_xml[cursor : match.start()])
        row_xml = match.group(0)
        if row_number in updates_by_row:
            for column, value in updates_by_row[row_number]:
                row_xml = _set_cell_in_row(row_xml, row_number, column, value)
            found.add(row_number)
        chunks.append(row_xml)
        cursor = match.end()
    chunks.append(sheet_xml[cursor:])
    output = "".join(chunks)
    for row_number, updates in updates_by_row.items():
        if row_number not in found:
            output = _set_row_cells(output, row_number, updates)
    return output


def _trace_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _metric_unit(name: str) -> str:
    """从评价结果键提取常见单位，供隐藏轨迹表阅读；不改变原始数值。"""
    for suffix, unit in (("_%", "%"), ("_W", "W"), ("_kW", "kW"), ("_m3h", "m³/h"), ("_Pa", "Pa"), ("_m", "m")):
        if str(name).endswith(suffix):
            return unit
    return ""


def _build_trace_sheet(evaluations: Sequence[V4WorkbookEvaluationRow]) -> str:
    rows: list[str] = []
    rows.append('<row r="1">' + "".join(_cell_fragment(f"{_column_letters(i)}1", header) for i, header in enumerate(TRACE_HEADERS)) + "</row>")
    excel_row = 2
    for item in evaluations:
        result = item.result
        synthetic = [
            {"step_type": "计算结果", "rule": key, "output": value, "unit": _metric_unit(str(key))}
            for key, value in (*result.calculated_metrics.items(), *result.actual_metrics.items())
        ]
        for step_number, trace in enumerate([*synthetic, *result.trace], start=1):
            comparison = trace.get("comparison", trace)
            rule_input = trace.get("rule", trace.get("changes", trace.get("input", "")))
            matching_condition = trace.get("matching_condition", trace.get("condition", ""))
            if trace.get("step_type") == "淘汰检查":
                # 轨迹表没有额外的目录字段，复用“规则/输入”列保存完整可审计摘要，
                # 同时保留“匹配条件”列中的目录原文条件。
                rule_input = "；".join(
                    f"{label}={trace.get(key, '')}"
                    for label, key in (
                        ("目录", "catalog"),
                        ("批次", "batch"),
                        ("条目号", "item_no"),
                        ("命中原因", "reason"),
                    )
                    if trace.get(key, "") not in (None, "")
                ) or rule_input
            values = [
                item.row.record_id,
                item.row.sheet_name,
                item.row.row_number,
                step_number,
                trace.get("step_type", ""),
                rule_input,
                trace.get("output", trace.get("value", "")),
                trace.get("unit", ""),
                trace.get("table", trace.get("standard_table", "")),
                matching_condition,
                trace.get("endpoints", trace.get("interpolation_endpoints", "")),
                trace.get("factor", trace.get("interpolation_factor", "")),
                comparison.get("direction", trace.get("direction", "")) if isinstance(comparison, dict) else "",
                comparison.get("threshold", trace.get("threshold", "")) if isinstance(comparison, dict) else "",
                comparison.get("passed", trace.get("passed", "")) if isinstance(comparison, dict) else "",
                trace.get("clause", result.standard_reference.get("clause", "")),
                result.elimination_scope.value,
                result.standard_reference.get("data_version", ""),
            ]
            rows.append('<row r="{}">{}</row>'.format(excel_row, "".join(_cell_fragment(f"{_column_letters(i)}{excel_row}", _trace_text(value)) for i, value in enumerate(values))))
            excel_row += 1
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheetProtection sheet="1" objects="1" scenarios="1"/>'
        '<sheetData>' + "".join(rows) + "</sheetData></worksheet>"
    )


def _ensure_trace_sheet(files: dict[str, bytes], evaluations: Sequence[V4WorkbookEvaluationRow]) -> str:
    workbook_xml = files.get("xl/workbook.xml", b"").decode("utf-8")
    rels_xml = files.get("xl/_rels/workbook.xml.rels", b"").decode("utf-8")
    content_types_xml = files.get("[Content_Types].xml", b"").decode("utf-8")

    existing = re.search(r'<sheet\b(?=[^>]*\bname="判定轨迹"[^>]*)([^>]*)/?>', workbook_xml)
    if existing:
        attrs = existing.group(1)
        rel_match = re.search(r'\br:id="([^"]+)"', attrs)
        if not rel_match:
            raise V4WorkbookWriteError("判定轨迹sheet缺少关系ID")
        rel_id = rel_match.group(1)
        relation = re.search(r'<Relationship\b(?=[^>]*\bId="' + re.escape(rel_id) + r'"[^>]*)[^>]*\bTarget="([^"]+)"[^>]*/?>', rels_xml)
        if not relation:
            raise V4WorkbookWriteError("判定轨迹sheet关系不存在")
        target = relation.group(1)
        target = target[1:] if target.startswith("/") else (target if target.startswith("xl/") else "xl/" + target)
        # 轨迹是技术输出，不应成为用户可编辑数据；即使输入工作簿中
        # 已存在同名sheet，也强制保持隐藏状态。
        existing_tag = existing.group(0)
        if re.search(r'\bstate="[^"]*"', existing_tag):
            existing_tag = re.sub(r'\bstate="[^"]*"', 'state="hidden"', existing_tag, count=1)
        else:
            existing_tag = existing_tag.replace("<sheet ", '<sheet state="hidden" ', 1)
        workbook_xml = workbook_xml[:existing.start()] + existing_tag + workbook_xml[existing.end():]
    else:
        sheet_ids = [int(value) for value in re.findall(r'\bsheetId="(\d+)"', workbook_xml)]
        rel_ids = [int(value) for value in re.findall(r'\bId="rId(\d+)"', rels_xml)]
        sheet_id = max(sheet_ids or [0]) + 1
        rel_id = f"rId{max(rel_ids or [0]) + 1}"
        target = f"xl/worksheets/sheet{sheet_id}.xml"
        sheet_entry = f'<sheet name="判定轨迹" sheetId="{sheet_id}" state="hidden" r:id="{rel_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        if "</sheets>" not in workbook_xml:
            raise V4WorkbookWriteError("workbook缺少sheets节点")
        workbook_xml = workbook_xml.replace("</sheets>", sheet_entry + "</sheets>", 1)
        relation = f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{sheet_id}.xml"/>'
        if "</Relationships>" not in rels_xml:
            raise V4WorkbookWriteError("workbook关系缺少Relationships节点")
        rels_xml = rels_xml.replace("</Relationships>", relation + "</Relationships>", 1)
        override = f'<Override PartName="/xl/worksheets/sheet{sheet_id}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        if override not in content_types_xml:
            content_types_xml = content_types_xml.replace("</Types>", override + "</Types>", 1)

    files["xl/workbook.xml"] = workbook_xml.encode("utf-8")
    files["xl/_rels/workbook.xml.rels"] = rels_xml.encode("utf-8")
    files["[Content_Types].xml"] = content_types_xml.encode("utf-8")
    files[target] = _build_trace_sheet(evaluations).encode("utf-8")
    return target


class V4WorkbookWriterImpl(V4WorkbookWriter):
    """V4结果写回器。

    只对结果列做定点OOXML修改，保留原工作簿其余压缩包部件；输入文件永不覆盖。
    """

    def __init__(self, *, require_template_structure: bool = True):
        self.require_template_structure = require_template_structure

    def write_results(
        self,
        source: Path,
        destination: Path,
        evaluations: Sequence[V4WorkbookEvaluationRow],
    ) -> Path:
        source = Path(source)
        destination = Path(destination)
        if source.resolve() == destination.resolve():
            raise V4WorkbookWriteError("结果工作簿不能覆盖输入文件")
        if self.require_template_structure:
            validation = V4TemplateResource().validate(source)
            if not validation.is_valid:
                raise V4WorkbookWriteError(validation.message)
        reader = V4WorkbookReaderImpl(require_template_structure=False)
        contract = reader.read_contract(source)
        try:
            with OOXMLWorkbook(source) as workbook:
                sheet_targets = dict(workbook._sheets)
                header_maps: dict[str, dict[str, int]] = {}
                for sheet_name in {item.row.sheet_name for item in evaluations}:
                    matrix = workbook.rows(sheet_name)
                    header_index = reader._find_header_row(matrix)
                    if header_index is None:
                        raise V4WorkbookWriteError(f"V4设备sheet缺少正式表头: {sheet_name}")
                    header_maps[sheet_name] = reader._header_map(matrix[header_index])
            with ZipFile(source, "r") as archive:
                files = {name: archive.read(name) for name in archive.namelist()}
        except (OSError, KeyError) as exc:
            raise V4WorkbookWriteError(f"读取输入工作簿失败: {exc}") from exc

        sheet_xml_cache: dict[str, str] = {}
        pending_updates: dict[str, dict[int, list[tuple[int, Any]]]] = {}
        for evaluation in evaluations:
            row = evaluation.row
            result = evaluation.result
            target = sheet_targets.get(row.sheet_name)
            if not target:
                raise V4WorkbookWriteError(f"结果行对应sheet不存在: {row.sheet_name}")
            if row.row_number <= 0:
                raise V4WorkbookWriteError(f"结果行缺少有效Excel行号: {row.record_id}")
            if target not in sheet_xml_cache:
                try:
                    sheet_xml_cache[target] = files[target].decode("utf-8")
                except (KeyError, UnicodeDecodeError) as exc:
                    raise V4WorkbookWriteError(f"无法读取sheet XML: {row.sheet_name}") from exc
            if target not in sheet_xml_cache:
                continue
            # 用配置字段的显示名称定位列，不使用固定列号；同一sheet只解析一次表头。
            header_map = header_maps[row.sheet_name]
            for field in contract.fields_for_sheet(row.sheet_name):
                if field.editable or field.field_id == "seq" or (field.data_type == "公式" and field.field_id != "auto_note"):
                    continue
                header = _header_name(field.display_name)
                column = header_map.get(header)
                if column is None:
                    continue
                value = _metric_value(result, field)
                if value is None:
                    continue
                pending_updates.setdefault(target, {}).setdefault(row.row_number, []).append((column, value))

        for target, rows in pending_updates.items():
            xml = sheet_xml_cache[target]
            xml = _set_rows_cells(xml, rows)
            files[target] = xml.encode("utf-8")
        _ensure_trace_sheet(files, evaluations)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return destination
