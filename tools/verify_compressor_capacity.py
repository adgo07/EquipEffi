"""实测V6.6无软件行数设置的统一容量与同核批量。"""
import json
import os
from pathlib import Path
from hashlib import sha256
from time import monotonic
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from equipeffi.composition import create_batch_evaluation_service
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.excel.template_resource import V66CompressorTemplateResource
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook
from tools.build_v61_transformer_template import _tag, _set_inline
ROOT = Path(__file__).resolve().parents[1]


def verify(counts=(2, 100, 1000, 10000), *, persist=False):
    output = ROOT/"outputs/compressor-implementation"/("capacity-persist" if persist else "capacity")
    output.mkdir(parents=True, exist_ok=True)
    template = V66CompressorTemplateResource().template_path
    with OOXMLWorkbook(template) as book:
        part = book._sheets["空压机"]
    with ZipFile(template) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
    xml = next(data for info, data in entries if info.filename == part)
    results = []
    for count in counts:
        root = ET.fromstring(xml)
        rows = root.find(_tag("sheetData"))
        for row in list(rows):
            if int(row.get("r")) >= 4:
                rows.remove(row)
        for n in range(4, count+4):
            row = ET.SubElement(rows, _tag("row"), r=str(n))
            for col, value in (("B", f"容量验证{n-3}"), ("D", "1"), ("F", "一般用喷油回转空气压缩机"), ("G", "1.5"), ("I", "0.3"), ("J", "风冷"), ("K", "5.8")):
                cell = ET.SubElement(row, _tag("c"), r=f"{col}{n}")
                _set_inline(cell, value)
        source = output/f"空压机_{count}行.xlsx"
        with ZipFile(source, "w") as archive:
            for info, data in entries:
                archive.writestr(info, ET.tostring(root, encoding="utf-8",
                                 xml_declaration=True) if info.filename == part else data)
        before = sha256(source.read_bytes()).hexdigest()
        service = create_batch_evaluation_service(paths=AppDataPaths(output/f"data-{count}"))
        started = monotonic()
        result = service.evaluate_workbook(source, destination=output/f"结果_{count}行.xlsx", persist=persist)
        seconds = monotonic()-started
        assert before == sha256(source.read_bytes()).hexdigest()
        assert result.summary.data_row_count == count
        assert result.summary.conclusion_rows == {"1级": count}
        with OOXMLWorkbook(Path(result.result_workbook)) as book:
            grid = book.rows("空压机")
            assert grid[count+2][14] == "1级"
            assert len(book.sheet_names) == 18
        entry = dict(rows=count, seconds=round(seconds, 3), pass_count=5, fail=0, error=0, skip=0,
                     input_sha256=before, result_sha256=result.result_workbook_sha256,
                     no_software_capacity_setting=True, persist=persist)
        if persist:
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(service.batch_repository.database)) as connection:
                singles = connection.execute("select count(*) from record").fetchone()[0]
                batches = connection.execute("select count(*) from batch_record").fetchone()[0]
            assert singles == 0 and batches == 1
            before_list = sha256(service.batch_repository.database.read_bytes()).hexdigest()
            listed = service.batch_repository.list_batch_records()
            assert "compressor_row_evidence" not in listed[0].summary
            detail = service.batch_repository.load_batch_record(result.batch_record_id)
            evidence = detail.summary["compressor_row_evidence"]
            assert len(evidence) == count and evidence[-1]["row"] == count + 3
            assert evidence[-1]["grade"] == "1" and evidence[-1]["assessment_scope"] == "SPECIFIC_POWER_GRADE_ONLY"
            assert before_list == sha256(service.batch_repository.database.read_bytes()).hexdigest()
            entry.update(persist=True, batch_records=batches, single_records=singles, row_evidence=len(evidence),
                         list_omits_row_evidence=True, full_detail_preserved=True, database_unchanged_by_reads=True, pass_count=11)
        results.append(entry)
        (output/"capacity-results.json").write_text(json.dumps(results,
                                                               ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--rows", type=int, nargs="+", default=[2, 100, 1000, 10000])
    args = parser.parse_args()
    verify(args.rows, persist=args.persist)
