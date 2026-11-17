"""V6.7锅炉输入；保留XML十进制原词法和O输入来源。"""
from pathlib import Path
from ...application.ports.batch_workbook import BatchSourceRow, BatchSourceWorkbook
from ...domain.devices.boiler.input_contract import CATEGORIES, REVISION, is_low_biomass
from .ooxml_reader import OOXMLWorkbook, OOXMLReadError
from .boiler_row_source import context, resolve_design_input

from .boiler_sheet_contract import COLUMNS as SHEET_COLUMNS
COLUMNS = {col: field_id for col, _label, _unit, field_id, role in SHEET_COLUMNS if role == "input"}



class BoilerWorkbookReader:
    def read(self, source, *, template_identity=None):
        from .template_resource import validate_v6_template
        from .unified_workbook_reader import _cell
        validation = validate_v6_template(Path(source), check_pump_sheet=False)
        if not validation.is_valid:
            raise OOXMLReadError(validation.message)
        if validation.identity.get("template_version") != "V6.7":
            raise OOXMLReadError("旧锅炉字段语义不同，请使用V6.7模板重新填写。")
        with OOXMLWorkbook(source) as book:
            grid = book.rows("工业锅炉")
            metadata = book.cell_metadata("工业锅炉", columns=set(COLUMNS) | {"O"})
            notes = book.rows("模板说明")
        is_result = len(notes) >= 34 and _cell(notes[33], "B") == "EQUIPEFFI_BATCH_OUTPUT_V1"
        categories = {v: c.category_id for c in CATEGORIES for v in (c.label, c.category_id)}
        rows, blank = [], 0
        for number, raw in enumerate(grid[3:], 4):
            values = {key: _cell(raw, col) for col, key in COLUMNS.items()}
            raw_o = _cell(raw, "O")
            # 元数据保留XML原始词法，整数90.0也不被通用Reader折成90。
            for col in "DHIJKLO":
                meta = metadata.get(f"{col}{number}")
                if meta and meta.cell_type in ("", "n") and meta.raw_value and not meta.has_formula:
                    if col == "O":
                        raw_o = meta.raw_value
                    else:
                        values[COLUMNS[col]] = meta.raw_value
            low = is_low_biomass(categories.get(values["category_id"]), values["qnet_kj_kg"])
            errors = []
            # O只在低热值分支是输入；普通输出不参与行启用或输入验证。
            for col in (*COLUMNS, *(("O",) if low else ())):
                meta = metadata.get(f"{col}{number}")
                if meta and (meta.has_formula or meta.cell_type == "e" or meta.is_date or meta.is_percentage):
                    errors.append(f"{col}{number}请填写固定输入值，不接受公式、错误、日期或百分比格式。")
            if not any(v not in (None, "") for v in values.values()) and not errors:
                blank += 1
                continue
            values["category_raw"] = values["category_id"]
            values["category_id"] = categories.get(values["category_id"], values["category_id"])
            values["input_contract_revision"] = REVISION
            source_kind = "TABLE_OUTPUT"
            if low:
                has_outputs = any(_cell(raw, c) not in (None, "") for c in "MNPS")
                design, source_kind = resolve_design_input(values, raw_o, _cell(raw, "S"), has_outputs=has_outputs, is_result_workbook=is_result)
                values["design_limit_pct"] = design
                if source_kind == "SOURCE_AMBIGUOUS":
                    errors.append(f"O{number}来源不明或类别/热值条件已变化；请在空白V6.7模板补录设计限定值，不沿用旧输出。")
            values["excel_o_source"] = dict(context=context(values), o_kind=source_kind,
                design_input=values.get("design_limit_pct", ""), original_o=raw_o)
            rows.append(BatchSourceRow(number, values, input_errors=tuple(errors), source_values=dict(values)))
        identity = dict(template_identity or validation.identity)
        identity.update(sheet_id="industrial_boiler", sheet_contract_revision=REVISION)
        return BatchSourceWorkbook(str(source), tuple(rows), blank, identity)
