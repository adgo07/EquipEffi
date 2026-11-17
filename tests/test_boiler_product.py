"""同核产品、不可变记录与19列Workbook来源回归。"""
from copy import copy
from contextlib import closing
from datetime import date
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile
import json
import os
import sqlite3
import unittest
from openpyxl import load_workbook
from equipeffi.application.services.boiler_analysis_service import BoilerAnalysisRequest
from equipeffi.composition import create_boiler_analysis_service, create_batch_evaluation_service, create_pump_analysis_service
from equipeffi.infrastructure.excel.template_resource import V67BoilerTemplateResource, V66CompressorTemplateResource, validate_v6_template
from equipeffi.infrastructure.excel.boiler_workbook_reader import BoilerWorkbookReader
from equipeffi.infrastructure.excel.boiler_row_source import decode_source
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from tests.unit.test_boiler_core import BASE
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LOW_ROW = dict(B="锅炉A",D=2,F="固定式水介质蒸汽锅炉／生物质",G="生物质",H=10,I="0.1",J=8000,L=88,O=90,R="保留原备注")


def save_input(path, rows=None, template=None):
    book = load_workbook(template or V67BoilerTemplateResource().template_path)
    sheet = book["工业锅炉"]
    for number, values in (rows or {4: LOW_ROW}).items():
        for col, value in values.items():
            sheet[f"{col}{number}"] = value
            sheet[f"{col}{number}"]._style = copy(sheet[f"{col}4"]._style)
    book.save(path)
    return path


class BoilerProductTests(unittest.TestCase):
    def test_record_immutable_repeated_legal_failures_and_today(self):
        with TemporaryDirectory() as d:
            paths=AppDataPaths(Path(d));service=create_boiler_analysis_service(paths=paths)
            a=service.analyze_and_record(BoilerAnalysisRequest(BASE | dict(qnet_kj_kg="8000",design_limit_pct="90")))
            b=service.analyze_and_record(BoilerAnalysisRequest(BASE))
            mixed=service.analyze_and_record(BoilerAnalysisRequest(dict(category_id="steam_mixed")))
            self.assertEqual((a.record_status,b.record_status,mixed.record_status),("SAVED",)*3)
            self.assertNotEqual(a.record.record_id,b.record.record_id)
            self.assertEqual(a.record.as_of,date.today().isoformat())
            self.assertEqual(a.record.result_snapshot["minimum_limit"]["met"],False)
            self.assertEqual(a.record.input_snapshot["normalized_numeric_values"]["rated_pressure_mpa"]["denominator"],"10")
            self.assertEqual(a.record.result_snapshot["thresholds"]["grade_3"]["original_table_value"],"80")
            saved=json.dumps(a.record.result_snapshot,sort_keys=True)
            for values in (BASE|dict(efficiency_pct="NaN"),dict(category_id="ORGANIC_HEAT_CARRIER")):
                self.assertEqual(service.analyze_and_record(BoilerAnalysisRequest(values)).record_status,"NOT_ELIGIBLE")
            with patch.object(service._calculator,"evaluate",side_effect=RuntimeError("system")):
                with self.assertRaises(RuntimeError):service.analyze_and_record(BoilerAnalysisRequest(BASE))
            with patch.object(service._records,"append_record",side_effect=OSError("db")):
                self.assertEqual(service.analyze_and_record(BoilerAnalysisRequest(BASE)).record_status,"SAVE_FAILED")
            reopened=create_pump_analysis_service(paths=paths).open_record(a.record.record_id)
            self.assertEqual(json.dumps(reopened.result_snapshot,sort_keys=True),saved)
            with closing(sqlite3.connect(paths.records_db)) as c:
                self.assertEqual(c.execute("select count(*) from record").fetchone()[0],3)

    def test_19_column_template_preserved_sheets_styles_and_contract_gate(self):
        old,new=V66CompressorTemplateResource(),V67BoilerTemplateResource()
        self.assertTrue(new.validate().is_valid)
        with OOXMLWorkbook(old.template_path) as a,OOXMLWorkbook(new.template_path) as b:
            self.assertEqual(a.sheet_names,b.sheet_names);self.assertEqual(len(b.sheet_names),18)
            allowed={a._sheets["工业锅炉"],a._sheets["配置"],"xl/styles.xml","xl/workbook.xml","xl/tables/table9.xml"}
            changed={n for n in a.archive.namelist() if a.archive.read(n)!=b.archive.read(n)}
            self.assertTrue(changed<=allowed,changed)
            from xml.etree import ElementTree as ET
            ns="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            x=ET.fromstring(a.archive.read("xl/styles.xml")).find(ns+"cellXfs")
            y=ET.fromstring(b.archive.read("xl/styles.xml")).find(ns+"cellXfs")
            self.assertEqual([ET.tostring(n) for n in x],[ET.tostring(n) for n in y][:len(x)])
            self.assertEqual(len(b.rows("工业锅炉")[2]),19)
        with TemporaryDirectory() as d:
            f=Path(d)/"bad.xlsx";w=load_workbook(new.template_path);w["配置"]["FL2"]="错误类别";w.save(f)
            self.assertFalse(validate_v6_template(f).is_valid)
        with self.assertRaisesRegex(ValueError,"V6.7"):BoilerWorkbookReader().read(old.template_path)

    def test_batch_one_record_dual_statistics_and_same_core_preservation(self):
        with TemporaryDirectory() as d:
            d=Path(d);paths=AppDataPaths(d/"data");service=create_batch_evaluation_service(paths=paths)
            f=save_input(d/"input.xlsx",{4:LOW_ROW,5:dict(B="电锅炉",D=3,F="固定式水介质蒸汽锅炉／电加热",G="电",I="0.1",L=97)})
            original=sha256(f.read_bytes()).hexdigest()
            r=service.evaluate_workbook(f,destination=d/"out.xlsx")
            self.assertEqual(r.batch_record_error,"");self.assertEqual(r.summary.total_quantity,5)
            self.assertEqual(r.summary.conclusion_quantities,{"1级":2,"达到限定值":3})
            self.assertEqual(r.summary.boiler_minimum_limit["quantities"],{"未达到限定值":2,"达到限定值":3})
            self.assertEqual(sha256(f.read_bytes()).hexdigest(),original)
            out=load_workbook(d/"out.xlsx");self.assertEqual(out["工业锅炉"]["O4"].value,90)
            self.assertIsNone(out["工业锅炉"]["O5"].value)
            self.assertEqual(out["工业锅炉"]["R4"].value,"保留原备注")
            self.assertEqual(decode_source(out["工业锅炉"]["S4"].value)["o_kind"],"DESIGN_INPUT")
            direct=create_boiler_analysis_service(with_persistence=False).evaluate(BoilerAnalysisRequest(BASE|dict(qnet_kj_kg="8000",design_limit_pct="90")))
            self.assertEqual(r.outcomes[0]["outcome"].grade,direct.grade)
            with ZipFile(f) as a,ZipFile(d/"out.xlsx") as b:
                with OOXMLWorkbook(f) as book:
                    targets={book._sheets[n] for n in ("工业锅炉","模板说明","离心泵","变压器","电动机","空压机")}
                for name in a.namelist():
                    if name not in targets:self.assertEqual(a.read(name),b.read(name),name)
            with closing(sqlite3.connect(paths.records_db)) as c:
                self.assertEqual(c.execute("select count(*) from record").fetchone()[0],0)
                self.assertEqual(c.execute("select count(*) from batch_record").fetchone()[0],1)
            reopened=service.open_batch_record(r.batch_record_id)
            evidence=reopened.summary["boiler_row_evidence"][0]
            self.assertEqual(evidence["minimum_limit"]["source_kind"],"OWNER_DESIGN_LIMIT")

    def test_o_reimport_changes_and_ambiguous_sources(self):
        with TemporaryDirectory() as d:
            d=Path(d);service=create_batch_evaluation_service(paths=AppDataPaths(d/"data"))
            source=save_input(d/"in.xlsx")
            service.evaluate_workbook(source,destination=d/"result.xlsx",persist=False)
            row=BoilerWorkbookReader().read(d/"result.xlsx").rows[0]
            self.assertFalse(row.input_errors);self.assertEqual(str(row.values["design_limit_pct"]),"90")
            for column,value in (("J4",7999),("F4","固定式水介质热水锅炉／生物质"),("H4",11)):
                book=load_workbook(d/"result.xlsx");book["工业锅炉"][column]=value;book.save(d/"changed.xlsx")
                self.assertTrue(BoilerWorkbookReader().read(d/"changed.xlsx").rows[0].input_errors,column)
            book=load_workbook(d/"result.xlsx");book["工业锅炉"]["S4"]="来源丢失";book.save(d/"unknown.xlsx")
            self.assertTrue(BoilerWorkbookReader().read(d/"unknown.xlsx").rows[0].input_errors)
            # 先普通输出80，再改低热值，绝不可把80当设计输入。
            source=save_input(d/"ordinary.xlsx",{4:LOW_ROW|dict(J=9000,O=None)})
            service.evaluate_workbook(source,destination=d/"ordinary-out.xlsx",persist=False)
            book=load_workbook(d/"ordinary-out.xlsx");self.assertEqual(book["工业锅炉"]["O4"].value,80)
            book["工业锅炉"]["J4"]=8000;book.save(d/"stale.xlsx")
            row=BoilerWorkbookReader().read(d/"stale.xlsx").rows[0]
            self.assertTrue(row.input_errors);self.assertEqual(row.values["design_limit_pct"],"")
            service.evaluate_workbook(d/"stale.xlsx",destination=d/"error-out.xlsx",persist=False)
            self.assertEqual(load_workbook(d/"error-out.xlsx")["工业锅炉"]["O4"].value,80)
            self.assertIsNone(load_workbook(d/"error-out.xlsx")["工业锅炉"]["M4"].value)
            # 新补录75不再是旧输出，许可为设计输入。
            book["工业锅炉"]["O4"]=75;book.save(d/"replenished.xlsx")
            self.assertFalse(BoilerWorkbookReader().read(d/"replenished.xlsx").rows[0].input_errors)

    def test_decimal_o_and_xml_lexical_input_are_preserved(self):
        from xml.etree import ElementTree as ET
        with TemporaryDirectory() as d:
            d=Path(d);f=save_input(d/"decimal.xlsx",{4:LOW_ROW|dict(O=90.5,I=0.1,L=88.5)})
            row=BoilerWorkbookReader().read(f).rows[0]
            self.assertEqual(row.values["design_limit_pct"],"90.5")
            self.assertEqual(row.values["rated_pressure_mpa"],"0.1")
            service=create_batch_evaluation_service(paths=AppDataPaths(d/"data"))
            result=service.evaluate_workbook(f,destination=d/"out.xlsx")
            self.assertFalse(result.batch_record_error)
            again=BoilerWorkbookReader().read(d/"out.xlsx").rows[0]
            self.assertFalse(again.input_errors);self.assertEqual(again.values["design_limit_pct"],"90.5")
            with OOXMLWorkbook(f) as a,OOXMLWorkbook(d/"out.xlsx") as b:
                ns="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                cell=lambda book: ET.fromstring(book.archive.read(book._sheets["工业锅炉"])).find(f".//{ns}c[@r='O4']")
                self.assertEqual(ET.tostring(cell(a)),ET.tostring(cell(b)))

    def test_missing_o_quantity_formula_and_execution_failure(self):
        with TemporaryDirectory() as d:
            d=Path(d);service=create_batch_evaluation_service(paths=AppDataPaths(d/"data"))
            for key,value in (("O",None),("O",0),("D",None),("D",0),("D",-1),("D",1.5),("L","=80+8")):
                source=save_input(d/"in.xlsx",{4:LOW_ROW|{key:value}})
                r=service.evaluate_workbook(source,destination=d/f"out-{key}-{str(value).replace('/','')}.xlsx",persist=False)
                self.assertEqual(r.summary.input_error_rows,1,(key,value))
            source=save_input(d/"system.xlsx")
            with patch.object(service.boiler,"evaluate",side_effect=RuntimeError("system")):
                r=service.evaluate_workbook(source,destination=d/"system-out.xlsx",persist=False)
                self.assertEqual(r.summary.execution_error_rows,1);self.assertEqual(r.summary.conclusion_quantities,{})
            with patch.object(service.writer,"write",side_effect=OSError("disk")):
                with self.assertRaises(OSError):service.evaluate_workbook(source,destination=d/"failed.xlsx")
            with patch.object(service.batch_repository,"append_batch_record",side_effect=OSError("db")):
                r=service.evaluate_workbook(source,destination=d/"db-out.xlsx")
                self.assertTrue(r.batch_record_error)

    def test_old_boiler_notice_preserves_other_device_path(self):
        from equipeffi.infrastructure.excel.unified_workbook_reader import UnifiedWorkbookReader
        with TemporaryDirectory() as d:
            d=Path(d)
            f=save_input(d/"old.xlsx",{4:dict(B="旧锅炉",D=1,L=88)},V66CompressorTemplateResource().template_path)
            book=load_workbook(f)
            comp=book["空压机"]
            for col,value in dict(B="现有空压机",D=1,F="一般用喷油回转空气压缩机",G="1.5",I="0.3",J="风冷",K="5.8").items():
                comp[f"{col}4"]=value
            book.save(f)
            workbook=UnifiedWorkbookReader().read(f)
            self.assertNotIn("工业锅炉",workbook.sheets)
            self.assertTrue(any("V6.7" in x for x in workbook.compatibility_messages))
            result=create_batch_evaluation_service(paths=AppDataPaths(d/"data")).evaluate_workbook(f,destination=d/"out.xlsx")
            self.assertEqual(result.summary.conclusion_quantities,{"1级":1})
            self.assertEqual(load_workbook(d/"out.xlsx")["工业锅炉"]["L4"].value,88)

    def test_qt_conditional_fields_same_result_history_without_recalculation(self):
        from PySide6.QtWidgets import QApplication,QComboBox
        from equipeffi.presentation.qt.pages.boiler_analysis import BoilerAnalysisPage
        from equipeffi.presentation.qt.pages.records import RecordsPage
        app=QApplication.instance() or QApplication([])
        with TemporaryDirectory() as d:
            paths=AppDataPaths(Path(d));page=BoilerAnalysisPage(create_boiler_analysis_service(paths=paths))
            page.category.setCurrentIndex(page.category.findData("steam_biomass"))
            for key,value in BASE.items():
                if key=="category_id":continue
                widget=page.field_inputs[key]
                if isinstance(widget,QComboBox):widget.setCurrentIndex(widget.findData(value))
                else:widget.setText(value)
            page.field_inputs["qnet_kj_kg"].setText("8000")
            self.assertTrue(page.field_inputs["design_limit_pct"].isEnabled())
            page.field_inputs["design_limit_pct"].setText("90")
            result=page.evaluate();self.assertEqual(result.grade,"1");self.assertFalse(result.minimum_limit["met"])
            first=page.last_saved_record_id;page.evaluate();self.assertNotEqual(first,page.last_saved_record_id)
            page.field_inputs["qnet_kj_kg"].setText("8374")
            self.assertFalse(page.field_inputs["design_limit_pct"].isEnabled())
            self.assertEqual(page.field_inputs["design_limit_pct"].text(),"")
            page.category.setCurrentIndex(page.category.findData("steam_gas_condensing_lower"))
            for key,value in dict(fuel="天然气",rated_pressure_mpa="0.1",efficiency_pct="103").items():
                w=page.field_inputs[key]
                if isinstance(w,QComboBox):w.setCurrentIndex(w.findData(value))
                else:w.setText(value)
            self.assertEqual(page.evaluate().grade,"1")
            page.category.setEditText("未选择的类别文本")
            self.assertFalse(page.stale_label.isHidden())
            self.assertEqual(page.evaluate().evaluation_status,"INVALID_INPUT")
            records=RecordsPage(create_pump_analysis_service(paths=paths))
            self.assertIn("1级",records.show_record(first))
            self.assertIn("设计限定值",records.inputs_detail.text())
            from tests.unit.test_motor_qt import _dispose_widget
            _dispose_widget(records);_dispose_widget(page)
