from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import time
import re
import unittest
from zipfile import ZIP_DEFLATED, ZipFile
import base64

from equipeffi.application.ports.v4_workbook import V4WorkbookEvaluationRow
from equipeffi.application.ports.v4_workbook import V4WorkbookRow
from equipeffi.application.services.evaluation_facade import EvaluationFacade
from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.application.services.v4_workbook_service import V4WorkbookService
from equipeffi.domain.common.models import DeviceDraft
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook
from equipeffi.infrastructure.excel.template_resource import V4TemplateResource
from equipeffi.infrastructure.excel.v4_reader import V4WorkbookReaderImpl
from equipeffi.infrastructure.excel.v4_writer import V4WorkbookWriterImpl, _build_trace_sheet, _ensure_trace_sheet, _metric_value, _set_cell, _set_rows_cells
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"


def _copy_with_motor_row(directory: str) -> Path:
    source = Path(directory) / "输入.xlsx"
    shutil.copy2(TEMPLATE, source)
    with OOXMLWorkbook(source) as package:
        sheet_target = package._sheets["电动机"]
    with ZipFile(source, "r") as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    sheet_xml = files[sheet_target].decode("utf-8")
    for column, value in {
        0: 1,
        1: "电机1",
        2: "M1",
        3: 1,
        5: "三相异步电动机（一般用途）",
        6: 0.4,
        9: 7.5,
        10: 4,
        11: 1480,
        12: 98,
    }.items():
        sheet_xml = _set_cell(sheet_xml, 4, column, value)
    files[sheet_target] = sheet_xml.encode("utf-8")
    patched = Path(directory) / "patched.xlsx"
    with ZipFile(patched, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return patched


def _copy_with_anchored_photo(directory: str) -> Path:
    """在电动机sheet注入一个真实OOXML两单元格图片锚点。"""
    source = Path(directory) / "带图片输入.xlsx"
    # 复用带有实际设备数据的输入，确保图片保留验收和结果写回同时发生。
    shutil.copy2(_copy_with_motor_row(directory), source)
    with ZipFile(source, "r") as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    sheet = "xl/worksheets/sheet2.xml"
    rels = "xl/worksheets/_rels/sheet2.xml.rels"
    sheet_xml = files[sheet].decode("utf-8")
    sheet_xml = sheet_xml.replace(
        "</worksheet>",
        '<drawing xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rId2"/></worksheet>',
        1,
    )
    files[sheet] = sheet_xml.encode("utf-8")
    rels_xml = files[rels].decode("utf-8").replace(
        "</Relationships>",
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="/xl/drawings/drawing1.xml"/></Relationships>',
        1,
    )
    files[rels] = rels_xml.encode("utf-8")
    files["xl/drawings/drawing1.xml"] = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<xdr:twoCellAnchor><xdr:from><xdr:col>1</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>3</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from><xdr:to><xdr:col>3</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>8</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>
<xdr:pic><xdr:nvPicPr><xdr:cNvPr id="1" name="photo"/><xdr:cNvPicPr/></xdr:nvPicPr><xdr:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill><xdr:spPr><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr></xdr:pic><xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>'''
    files["xl/drawings/_rels/drawing1.xml.rels"] = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/></Relationships>'''
    files["xl/media/image1.png"] = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    content_types = files["[Content_Types].xml"].decode("utf-8")
    content_types = content_types.replace(
        "</Types>",
        '<Default Extension="png" ContentType="image/png"/><Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>',
        1,
    )
    files["[Content_Types].xml"] = content_types.encode("utf-8")
    with ZipFile(source, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return source


class V4WriterTests(unittest.TestCase):
    def test_existing_trace_sheet_is_forced_hidden_and_protected(self):
        files = {
            "xl/workbook.xml": (
                '<workbook><sheets><sheet name="判定轨迹" sheetId="1" '
                'state="visible" r:id="rId1"/></sheets></workbook>'
            ).encode("utf-8"),
            "xl/_rels/workbook.xml.rels": (
                '<Relationships><Relationship Id="rId1" '
                'Target="worksheets/sheet1.xml"/></Relationships>'
            ).encode("utf-8"),
            "[Content_Types].xml": b"<Types></Types>",
            "xl/worksheets/sheet1.xml": b"old",
        }
        target = _ensure_trace_sheet(files, [])
        self.assertEqual(target, "xl/worksheets/sheet1.xml")
        workbook_xml = files["xl/workbook.xml"].decode("utf-8")
        self.assertIn('name="判定轨迹"', workbook_xml)
        self.assertIn('state="hidden"', workbook_xml)
        self.assertIn('sheetProtection sheet="1"', files[target].decode("utf-8"))

    def test_batch_row_patch_handles_1500_rows_without_repeated_sheet_scan(self):
        rows = [
            f'<row r="{row}"><c r="A{row}" s="1"/><c r="B{row}" s="1"/></row>'
            for row in range(4, 1504)
        ]
        xml = '<worksheet><sheetData>' + "".join(rows) + '</sheetData></worksheet>'
        updates = {row: [(0, row), (1, f"设备{row}")] for row in range(4, 1504)}
        started = time.perf_counter()
        output = _set_rows_cells(xml, updates)
        elapsed = time.perf_counter() - started
        self.assertIn('r="A1503"><v>1503</v>', output)
        self.assertIn('r="B4"><is><t>设备4</t></is>', output)
        self.assertLess(elapsed, 2.0)

    def test_writer_creates_new_workbook_with_locked_results(self):
        with tempfile.TemporaryDirectory() as directory:
            source = _copy_with_motor_row(directory)
            reader = V4WorkbookReaderImpl()
            row = reader.read_rows(source)[0]
            facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
            result = facade.evaluate_v4(row.record_id, row.sheet_name, row.values)
            destination = Path(directory) / "结果.xlsx"
            output = V4WorkbookWriterImpl().write_results(
                source,
                destination,
                [V4WorkbookEvaluationRow(row, result)],
            )
            self.assertEqual(output, destination)
            self.assertTrue(V4TemplateResource().validate(destination).is_valid)
            with ZipFile(source, "r") as before, ZipFile(destination, "r") as after:
                self.assertTrue(set(before.namelist()).issubset(set(after.namelist())))
                self.assertTrue(any(name.startswith("xl/worksheets/sheet") and name not in before.namelist() for name in after.namelist()))
                self.assertEqual(before.read("xl/styles.xml"), after.read("xl/styles.xml"))
                workbook_xml = after.read("xl/workbook.xml").decode("utf-8")
                self.assertIn('name="判定轨迹"', workbook_xml)
                self.assertIn('state="hidden"', workbook_xml)
            with OOXMLWorkbook(destination) as workbook:
                rows = workbook.rows("电动机")
                self.assertIn("判定轨迹", workbook.sheet_names)
                trace_target = workbook._sheets["判定轨迹"]
            with ZipFile(destination, "r") as archive:
                self.assertIn("sheetProtection", archive.read(trace_target).decode("utf-8"))
            # N/P为三个等级指标，Q为结论；写回不改变输入列B/C/M。
            self.assertEqual(rows[3][13], 94)
            self.assertEqual(rows[3][14], 92.6)
            self.assertEqual(rows[3][15], 90.4)
            self.assertEqual(rows[3][16], "1级")
            self.assertEqual(rows[3][1], "电机1")
            self.assertEqual(rows[3][12], 98)
            self.assertIn("铭牌照片", rows[2])
            headers = rows[2]
            self.assertEqual(rows[3][headers.index("采用标准")], "GB 18613-2020")
            self.assertEqual(rows[3][headers.index("匹配表/条款")], "表1")
            self.assertEqual(rows[3][headers.index("参考能效等级")], "")
            self.assertIn("判定为1级", rows[3][headers.index("判定说明")])
            self.assertEqual(rows[3][headers.index("缺失信息")], "")

    def test_writer_preserves_real_excel_image_anchor_and_media_part(self):
        with tempfile.TemporaryDirectory() as directory:
            source = _copy_with_anchored_photo(directory)
            reader = V4WorkbookReaderImpl()
            row = reader.read_rows(source)[0]
            facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
            result = facade.evaluate_v4(row.record_id, row.sheet_name, row.values)
            destination = Path(directory) / "带图片结果.xlsx"
            V4WorkbookWriterImpl().write_results(
                source,
                destination,
                [V4WorkbookEvaluationRow(row, result)],
            )
            with ZipFile(destination, "r") as archive:
                names = set(archive.namelist())
                self.assertIn("xl/media/image1.png", names)
                self.assertIn("xl/drawings/drawing1.xml", names)
                self.assertIn("xl/drawings/_rels/drawing1.xml.rels", names)
                drawing = archive.read("xl/drawings/drawing1.xml").decode("utf-8")
                self.assertIn("<xdr:twoCellAnchor>", drawing)
                self.assertIn("<xdr:from>", drawing)
                self.assertIn("<xdr:to>", drawing)
                self.assertIn('r:embed="rId1"', drawing)
                sheet = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
                self.assertIn('r:id="rId2"', sheet)

    def test_end_to_end_v4_1500_rows_read_evaluate_write_and_reopen(self):
        """正式验收：覆盖V4工作簿读取、判定、写回和重新打开。"""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "批量输入.xlsx"
            destination = Path(directory) / "批量结果.xlsx"
            shutil.copy2(TEMPLATE, source)
            with OOXMLWorkbook(source) as package:
                sheet_target = package._sheets["电动机"]
            with ZipFile(source, "r") as archive:
                files = {name: archive.read(name) for name in archive.namelist()}
            sheet_xml = files[sheet_target].decode("utf-8")
            row_match = re.search(r'<row\b[^>]*\br="4"[^>]*>.*?</row>', sheet_xml, re.DOTALL)
            self.assertIsNotNone(row_match)
            template_row = row_match.group(0)
            duplicate_rows = []
            for row_number in range(5, 1504):
                row_xml = re.sub(r'\br="4"', f'r="{row_number}"', template_row)
                row_xml = re.sub(r'([A-Z]+)4(?=")', rf'\g<1>{row_number}', row_xml)
                duplicate_rows.append(row_xml)
            sheet_xml = sheet_xml.replace("</sheetData>", "".join(duplicate_rows) + "</sheetData>", 1)
            updates = {
                row_number: [
                    (0, row_number - 3), (1, "电机批量"), (2, "M-1500"), (3, 1),
                    (5, "三相异步电动机（一般用途）"), (6, 0.4), (9, 7.5),
                    (10, 4), (11, 1480), (12, 98),
                ]
                for row_number in range(4, 1504)
            }
            from equipeffi.infrastructure.excel.v4_writer import _set_rows_cells
            sheet_xml = _set_rows_cells(sheet_xml, updates)
            files[sheet_target] = sheet_xml.encode("utf-8")
            with ZipFile(source, "w", compression=ZIP_DEFLATED) as archive:
                for name, data in files.items():
                    archive.writestr(name, data)

            reader = V4WorkbookReaderImpl()
            service = V4WorkbookService(
                EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))),
                reader,
            )
            started = time.perf_counter()
            evaluation = service.evaluate_and_write(source, destination, writer=V4WorkbookWriterImpl())
            elapsed = time.perf_counter() - started
            self.assertEqual(evaluation, destination)
            self.assertLess(elapsed, 30.0)
            with OOXMLWorkbook(destination) as workbook:
                output_rows = workbook.rows("电动机")
                self.assertIn("判定轨迹", workbook.sheet_names)
            self.assertEqual(output_rows[1502][16], "1级")
            self.assertEqual(output_rows[1502][12], 98)

    def test_writer_refuses_to_overwrite_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source = _copy_with_motor_row(directory)
            reader = V4WorkbookReaderImpl()
            row = reader.read_rows(source)[0]
            facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
            result = facade.evaluate_v4(row.record_id, row.sheet_name, row.values)
            with self.assertRaises(ValueError):
                V4WorkbookWriterImpl().write_results(source, source, [V4WorkbookEvaluationRow(row, result)])

    def test_writer_maps_nonstandard_result_keys_to_v4_locked_fields(self):
        contract = V4WorkbookReaderImpl().read_contract(TEMPLATE)
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        result = facade.evaluate_v4(
            "BLOWER-1",
            "鼓风机",
            {"category": "单级双支撑低速离心鼓风机", "polytropic_efficiency": 80, "b2": 100, "d2": 1000},
        )
        fields = {field.field_id: field for field in contract.fields_for_sheet("鼓风机")}
        self.assertEqual(str(_metric_value(result, fields["b2_d2"])), "0.1")
        # GB 28381-2012表1中D₂>801、b₂/D₂=0.1的能效限定值为71.5%。
        self.assertEqual(str(_metric_value(result, fields["limit_value"])), "71.5")

    def test_writer_maps_electric_boiler_limit_to_grade3_only(self):
        contract = V4WorkbookReaderImpl().read_contract(TEMPLATE)
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        result = facade.evaluate_v4(
            "BOILER-E", "工业锅炉",
            {"device_name": "电锅炉", "model": "EB-1", "quantity": 1,
             "category": "电锅炉", "fuel": "电力", "thermal_power": 1,
             "design_efficiency": 97, "photo": "photo"},
        )
        fields = {field.field_id: field for field in contract.fields_for_sheet("工业锅炉")}
        self.assertIsNone(_metric_value(result, fields["grade1"]))
        self.assertIsNone(_metric_value(result, fields["grade2"]))
        self.assertEqual(str(_metric_value(result, fields["grade3"])), "97")

    def test_writer_maps_level_specific_eer_and_low_temperature_gates(self):
        contract = V4WorkbookReaderImpl().read_contract(TEMPLATE)
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        fields = {field.field_id: field for field in contract.fields_for_sheet("多联式空调")}
        normal = facade.evaluate_v4(
            "MS-1", "多联式空调",
            {"category": "风冷单冷", "cooling_capacity": 10, "rated_power": 3, "primary_metric_value": 5.5, "eer_min_value": 2.1},
        )
        self.assertEqual(_metric_value(normal, fields["eer_min_l1"]), 3.6)
        self.assertEqual(_metric_value(normal, fields["eer_min_l2"]), 2.9)
        self.assertEqual(_metric_value(normal, fields["eer_min_l3"]), 2.1)

        low_temperature = facade.evaluate_v4(
            "MS-2", "多联式空调",
            {"category": "低温机组", "heating_capacity": 18, "rated_power": 4, "primary_metric_value": 3.4, "cop_minus12_value": 2.2, "cop_minus20_value": 1.8},
        )
        self.assertEqual(str(_metric_value(low_temperature, fields["cop_minus12_limit"])), "2.2")
        self.assertEqual(str(_metric_value(low_temperature, fields["cop_minus20_limit"])), "1.8")

    def test_trace_sheet_retains_elimination_catalog_details(self):
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        result = facade.evaluation_service.evaluate(
            DeviceDraft(
                "TRACE-S8", "transformer", raw_values={
                    "model": "S8-100", "category": "10kV油浸式三相双绕组无励磁调压配电变压器",
                    "capacity_kva": 100, "core_material": "电工钢带", "connection": "Dyn11/Yzn11",
                    "no_load_loss_w": 200, "load_loss_w": 1500,
                }
            )
        )
        row = V4WorkbookEvaluationRow(
            V4WorkbookRow(
                "TRACE-S8", "变压器", {}, 4
            ),
            result,
        )
        xml = _build_trace_sheet([row])
        self.assertIn("高耗能落后机电设备（产品）淘汰目录（第四批）", xml)
        self.assertIn("条目号=1-1", xml)
        self.assertIn("最迟应于", xml)
        self.assertIn("标准查询结果", xml)
        self.assertIn("空载损耗-1级_W", xml)


if __name__ == "__main__":
    unittest.main()
