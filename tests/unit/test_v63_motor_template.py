from __future__ import annotations

import hashlib
import runpy
from decimal import Decimal
from pathlib import Path
import posixpath
import tempfile
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from equipeffi.application.ports.batch_workbook import BatchRowOutcome
from equipeffi.domain.devices.motor.input_contract import MOTOR_CATEGORIES
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook
from equipeffi.infrastructure.excel.pump_result_writer import _sheet_target
from equipeffi.infrastructure.excel.template_resource import (
    DEFAULT_V62_TEMPLATE,
    DEFAULT_V63_TEMPLATE,
    V62_TEMPLATE_ENTRY,
    V62MotorTemplateResource,
    V63_TEMPLATE_ENTRY,
    V63MotorTemplateResource,
    validate_v6_template,
)
from equipeffi.infrastructure.excel.unified_result_writer import (
    UnifiedResultWorkbookWriter,
)
from equipeffi.infrastructure.excel.unified_workbook_reader import UnifiedWorkbookReader


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "src" / "equipeffi" / "resources" / "templates"
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _column_index(letters: str) -> int:
    value = 0
    for char in letters.upper():
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def _sheet_table_target(archive: ZipFile, sheet_name: str) -> str:
    sheet = _sheet_target(archive, sheet_name)
    relation_path = posixpath.join(
        posixpath.dirname(sheet), "_rels", posixpath.basename(sheet) + ".rels")
    root = ET.fromstring(archive.read(relation_path))
    for relation in root.findall(f"{{{REL_NS}}}Relationship"):
        if not str(relation.attrib.get("Type", "")).endswith("/table"):
            continue
        target = str(relation.attrib["Target"])
        if target.startswith("/"):
            return posixpath.normpath(target.lstrip("/"))
        return posixpath.normpath(posixpath.join(posixpath.dirname(sheet), target))
    raise AssertionError(f"找不到{sheet_name}的Table关系")


def _set_cell(root: ET.Element, reference: str, value) -> None:
    sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
    assert sheet_data is not None
    row_number = int("".join(char for char in reference if char.isdigit()))
    row = next((item for item in sheet_data.findall(f"{{{MAIN_NS}}}row")
                if item.attrib.get("r") == str(row_number)), None)
    if row is None:
        row = ET.Element(f"{{{MAIN_NS}}}row", {"r": str(row_number)})
        sheet_data.append(row)
    cell = next((item for item in row.findall(f"{{{MAIN_NS}}}c")
                 if item.attrib.get("r") == reference), None)
    if cell is None:
        cell = ET.SubElement(row, f"{{{MAIN_NS}}}c", {"r": reference})
    for child in list(cell):
        cell.remove(child)
    if isinstance(value, str):
        cell.set("t", "inlineStr")
        inline = ET.SubElement(cell, f"{{{MAIN_NS}}}is")
        ET.SubElement(inline, f"{{{MAIN_NS}}}t").text = value
    else:
        cell.attrib.pop("t", None)
        ET.SubElement(cell, f"{{{MAIN_NS}}}v").text = str(value)
    cells = list(row.findall(f"{{{MAIN_NS}}}c"))
    for item in cells:
        row.remove(item)
    cells.sort(key=lambda item: _column_index(
        "".join(char for char in item.attrib["r"] if char.isalpha())))
    row.extend(cells)


def _workbook_with_motor_values(source: Path, destination: Path,
                                values: dict[str, object]) -> Path:
    with ZipFile(source) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
        motor_part = _sheet_target(archive, "电动机")
    motor_root = ET.fromstring({info.filename: data for info, data in entries}[motor_part])
    for reference, value in values.items():
        _set_cell(motor_root, reference, value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as target:
        for info, data in entries:
            target.writestr(
                info,
                ET.tostring(motor_root, encoding="utf-8", xml_declaration=True)
                if info.filename == motor_part else data)
    return destination


def _defined_names(path: Path) -> dict[str, tuple[str, ...]]:
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("xl/workbook.xml"))
    names: dict[str, list[str]] = {}
    for item in root.findall(f"{{{MAIN_NS}}}definedNames/{{{MAIN_NS}}}definedName"):
        names.setdefault(item.attrib.get("name", ""), []).append(item.text or "")
    return {name: tuple(values) for name, values in names.items()}


class V63MotorTemplateTests(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="equipeffi-v63-motor-")
        self.addCleanup(self._temporary.cleanup)
        self.temp_dir = Path(self._temporary.name)
        self.v62 = TEMPLATE_DIR / DEFAULT_V62_TEMPLATE
        self.v63 = TEMPLATE_DIR / DEFAULT_V63_TEMPLATE

    def test_manifest_asset_and_v62_snapshot_identity(self):
        self.assertEqual(V62_TEMPLATE_ENTRY["template_version"], "V6.2")
        self.assertEqual(V63_TEMPLATE_ENTRY["template_version"], "V6.3")
        self.assertEqual(V63_TEMPLATE_ENTRY["template_id"],
                         "equipeffi.device-efficiency.V6.3")
        self.assertEqual(V63_TEMPLATE_ENTRY["source_filename"], DEFAULT_V62_TEMPLATE)
        self.assertEqual(V63_TEMPLATE_ENTRY["source_sha256"], V62_TEMPLATE_ENTRY["asset_sha256"])
        self.assertEqual(
            hashlib.sha256(self.v62.read_bytes()).hexdigest().upper(),
            V62_TEMPLATE_ENTRY["asset_sha256"])
        self.assertEqual(
            hashlib.sha256(self.v63.read_bytes()).hexdigest().upper(),
            V63_TEMPLATE_ENTRY["asset_sha256"])
        self.assertEqual(self.v62.stat().st_size, V62_TEMPLATE_ENTRY["asset_size_bytes"])
        self.assertEqual(self.v63.stat().st_size, V63_TEMPLATE_ENTRY["asset_size_bytes"])
        self.assertTrue(V62MotorTemplateResource().validate().is_valid)
        self.assertTrue(V63MotorTemplateResource().validate().is_valid)
        motor_fields = {
            field["column"]: field
            for field in next(sheet for sheet in V63_TEMPLATE_ENTRY["sheets"]
                              if sheet["sheet_id"] == "motor")["fields"]
        }
        self.assertEqual(motor_fields["G"]["field_id"], "rated_voltage_v")
        self.assertEqual(motor_fields["G"]["unit"], "V")
        self.assertEqual(motor_fields["M"]["field_id"], "rated_efficiency_pct")
        self.assertEqual(motor_fields["M"]["label"], "额定效率")
        self.assertEqual(motor_fields["I"]["role"], "reserved")
        self.assertNotIn("field_id", motor_fields["I"])
        self.assertEqual(
            V62_TEMPLATE_ENTRY["asset_sha256"],
            "D009850015B4C5E132D9FF72D0DDB1649E67AFFEAA8F457B12187466C75CEC0E")

    def test_v63_builder_changes_only_motor_surface_and_preserves_shared_sheet_bytes(self):
        builder = runpy.run_path(str(ROOT / "tools" / "build_v63_motor_template.py"))
        digest, size = builder["build"](
            output=self.temp_dir / DEFAULT_V63_TEMPLATE, update_manifest=False)
        self.assertEqual(digest, V63_TEMPLATE_ENTRY["asset_sha256"])
        self.assertEqual(size, V63_TEMPLATE_ENTRY["asset_size_bytes"])

        with ZipFile(self.v62) as before, ZipFile(self.v63) as after:
            self.assertEqual(before.namelist(), after.namelist())
            pump_part = _sheet_target(before, "离心泵")
            transformer_part = _sheet_target(before, "变压器")
            motor_part = _sheet_target(before, "电动机")
            configuration_part = _sheet_target(before, "配置")
            instructions_part = _sheet_target(before, "注意事项")
            notes_part = _sheet_target(before, "模板说明")
            table_part = _sheet_table_target(before, "电动机")
            self.assertEqual(before.read(pump_part), after.read(pump_part))
            self.assertEqual(before.read(transformer_part), after.read(transformer_part))
            self.assertEqual(before.read(configuration_part), after.read(configuration_part))
            allowed = {motor_part, "xl/styles.xml", "xl/workbook.xml", table_part,
                       instructions_part, notes_part}
            changed = {name for name in before.namelist()
                       if before.read(name) != after.read(name)}
            self.assertEqual(changed, allowed)

            motor = ET.fromstring(after.read(motor_part))
            cols = motor.findall(f"{{{MAIN_NS}}}cols/{{{MAIN_NS}}}col")
            retired = next(node for node in cols
                           if node.attrib.get("min") == "9"
                           and node.attrib.get("max") == "9")
            self.assertEqual(retired.attrib.get("hidden"), "1")
            self.assertEqual(retired.attrib.get("width"), "0")
            validations = motor.findall(
                f"{{{MAIN_NS}}}dataValidations/{{{MAIN_NS}}}dataValidation")
            self.assertFalse(any(node.attrib.get("sqref", "").startswith("I4:")
                                 for node in validations))
            self.assertTrue(any(
                node.attrib.get("sqref") == "M4:M103"
                and node.attrib.get("type") == "decimal"
                and node.attrib.get("operator") == "between"
                and node.find(f"{{{MAIN_NS}}}formula1").text == "1"
                and node.find(f"{{{MAIN_NS}}}formula2").text == "100"
                for node in validations))
            self.assertTrue(any(
                node.attrib.get("sqref") == "G4:G103"
                and node.attrib.get("type") == "decimal"
                and node.attrib.get("operator") == "greaterThanOrEqual"
                and node.find(f"{{{MAIN_NS}}}formula1").text == "0"
                for node in validations))

            styles = ET.fromstring(after.read("xl/styles.xml"))
            xfs = styles.find(f"{{{MAIN_NS}}}cellXfs")
            assert xfs is not None
            cells = {cell.attrib.get("r"): cell for cell in motor.iter(f"{{{MAIN_NS}}}c")}
            for row_number in range(4, 104):
                cell = cells[f"I{row_number}"]
                self.assertEqual(cell.attrib.get("t"), None)
                self.assertEqual(list(cell), [])
                protection = xfs[int(cell.attrib["s"])].find(
                    f"{{{MAIN_NS}}}protection")
                self.assertIsNotNone(protection)
                self.assertEqual(protection.attrib.get("locked"), "1")
            for reference in ("G4", "M4"):
                protection = xfs[int(cells[reference].attrib["s"])].find(
                    f"{{{MAIN_NS}}}protection")
                self.assertIsNotNone(protection)
                self.assertEqual(protection.attrib.get("locked"), "0")
            protection = motor.find(f"{{{MAIN_NS}}}sheetProtection")
            self.assertIsNotNone(protection)
            self.assertEqual(protection.attrib.get("sheet"), "1")

            with OOXMLWorkbook(self.v63) as book:
                motor_rows = book.rows("电动机")
            self.assertEqual(motor_rows[2][6], "额定电压\n(V)")
            self.assertEqual(motor_rows[2][8], "历史字段（已停用）")
            self.assertEqual(motor_rows[2][12], "额定效率\n(%)")

            defined = _defined_names(self.v63)
            self.assertEqual(defined["EV_MOTOR_V63_CATEGORY"],
                             ("'配置'!$EW$2:$EW$9",))
            self.assertEqual(defined["EV_MOTOR_V63_CATEGORY_IDS"],
                             ("'配置'!$EX$2:$EX$9",))
            self.assertNotIn("EV_MOTOR_V62_BASIS", defined)
            self.assertEqual(
                {name: values for name, values in _defined_names(self.v62).items()
                 if name in {"EV_PUMP_CATEGORY", "EV_TRANSFORMER_CATEGORY"}},
                {name: values for name, values in defined.items()
                 if name in {"EV_PUMP_CATEGORY", "EV_TRANSFORMER_CATEGORY"}})
            names = ET.fromstring(after.read("xl/workbook.xml"))
            revisions = {
                node.attrib.get("name"): node.text
                for node in names.findall(f"{{{MAIN_NS}}}definedNames/{{{MAIN_NS}}}definedName")}
            self.assertEqual(revisions["EQUIPEFFI_SHEET_CONTRACT_motor"], '"motor-input.v3"')

    def test_reader_maps_v62_and_v63_units_and_efficiency_basis_explicitly(self):
        category = MOTOR_CATEGORIES[0]
        old_source = _workbook_with_motor_values(
            self.v62, self.temp_dir / "legacy-v62.xlsx", {
                "B4": "旧模板电机", "D4": 1, "F4": category.label,
                "G4": 0.38, "I4": "按上述口径填报", "M4": 92.4,
            })
        new_source = _workbook_with_motor_values(
            self.v63, self.temp_dir / "rated-v63.xlsx", {
                "B4": "铭牌电机", "D4": 1, "F4": category.label,
                "G4": 380, "H4": 50, "J4": 0.75, "K4": 4, "M4": 92.4,
            })
        reader = UnifiedWorkbookReader()
        old = reader.read(old_source).sheets["电动机"].rows
        new_workbook = reader.read(new_source)
        new = new_workbook.sheets["电动机"].rows
        self.assertEqual(len(old), 1)
        self.assertEqual(old[0].values["rated_voltage_kv"], Decimal("0.38"))
        self.assertEqual(old[0].values["measured_efficiency_pct"], Decimal("92.4"))
        self.assertEqual(old[0].values["efficiency_basis_status"], "按上述口径填报")
        self.assertEqual(len(new), 1)
        self.assertEqual(new_workbook.sheets["电动机"].skipped_blank_rows, 99)
        self.assertEqual(new[0].values["rated_voltage_v"], Decimal("380"))
        self.assertEqual(new[0].values["rated_efficiency_pct"], Decimal("92.4"))
        self.assertEqual(new[0].values["efficiency_basis_status"], "RATED_NAMEPLATE")
        self.assertEqual(new[0].values["input_contract_revision"], "motor-input.v3")
        self.assertNotIn("rated_voltage_kv", new[0].values)
        self.assertNotIn("measured_efficiency_pct", new[0].values)
        self.assertNotIn("efficiency_basis_raw", new[0].values)
        self.assertEqual(new_workbook.template_identity["template_version"], "V6.3")
        self.assertEqual(new_workbook.sheets["电动机"].template_identity["sheet_contract_revision"],
                         "motor-input.v3")

    def test_v63_reader_flags_legacy_i_values_and_unified_reader_keeps_mixed_sheets(self):
        category = MOTOR_CATEGORIES[0]
        source = _workbook_with_motor_values(
            self.v63, self.temp_dir / "legacy-i-v63.xlsx", {
                "B4": "带旧口径残留", "D4": 1, "F4": category.label,
                "G4": 380, "M4": 90, "I4": "仅有铭牌效率",
            })
        workbook = UnifiedWorkbookReader().read(source)
        row = workbook.sheets["电动机"].rows[0]
        self.assertEqual(row.values["rated_voltage_v"], Decimal("380"))
        self.assertEqual(row.values["rated_efficiency_pct"], Decimal("90"))
        self.assertEqual(row.values["efficiency_basis_status"], "RATED_NAMEPLATE")
        self.assertTrue(any("I4" in message and "V6.2" in message
                            for message in row.input_errors))
        self.assertEqual(
            set(workbook.sheets), {"离心泵", "变压器", "电动机"})
        self.assertIn("空压机", workbook.unprocessed_sheets)

    def test_v63_writer_writes_results_and_reimport_retains_rated_inputs(self):
        category = MOTOR_CATEGORIES[0]
        source = _workbook_with_motor_values(
            self.v63, self.temp_dir / "source.xlsx", {
                "B4": "铭牌电机", "D4": 1, "F4": category.label,
                "G4": 380, "H4": 50, "J4": 0.75, "K4": 4, "M4": 92.4,
            })
        outcome = BatchRowOutcome(
            4, True, "1级", "SUCCESS", "1级", messages=("按铭牌额定效率评价。",),
            thresholds={
                "grade_1": {"state": "AVAILABLE", "display_text": "92.50"},
                "grade_2": {"state": "AVAILABLE", "display_text": "90.00"},
                "grade_3": {"state": "AVAILABLE", "display_text": "88.00"},
            })
        summary = {
            "sheets": [{"sheet_name": "电动机", "data_row_count": 1}],
            "unprocessed_sheets": ["空压机"],
            "data_row_count": 1, "total_quantity": 1, "evaluated_quantity": 1,
            "concluded_rows": 1, "unevaluated_rows": 0,
            "input_error_rows": 0, "execution_error_rows": 0,
        }
        output = self.temp_dir / "result.xlsx"
        UnifiedResultWorkbookWriter().write(
            source, {"电动机": {4: outcome}}, output, batch_summary=summary)
        validation = validate_v6_template(output)
        self.assertTrue(validation.is_valid, validation.message)
        with OOXMLWorkbook(output) as workbook:
            rows = workbook.rows("电动机")
            notes = workbook.rows("模板说明")
        self.assertEqual(rows[3][6], Decimal("380"))
        self.assertEqual(rows[3][8], "")
        self.assertEqual(rows[3][12], Decimal("92.4"))
        self.assertEqual(rows[3][13:17], [92.5, 90, 88, "1级"])
        self.assertEqual(rows[3][19], "按铭牌额定效率评价。")
        self.assertEqual(notes[27][1], "V6.3")
        reimported = UnifiedWorkbookReader().read(output)
        rated = reimported.sheets["电动机"].rows[0].values
        self.assertEqual(rated["rated_voltage_v"], Decimal("380"))
        self.assertEqual(rated["rated_efficiency_pct"], Decimal("92.4"))
        self.assertEqual(rated["efficiency_basis_status"], "RATED_NAMEPLATE")


if __name__ == "__main__":
    unittest.main()
