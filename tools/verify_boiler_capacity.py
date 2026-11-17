"""1/100/1000/10000锅炉行真实批量、保真、重导入及SQLite计数证据。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from contextlib import closing
from hashlib import sha256
import sqlite3
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from tests.test_boiler_product import save_input, LOW_ROW
from equipeffi.composition import create_batch_evaluation_service
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.excel.boiler_workbook_reader import BoilerWorkbookReader
from equipeffi.infrastructure.excel.template_resource import validate_v6_template
from openpyxl import load_workbook


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    evidence=[]
    for count in (1,100,1000,10000):
        with TemporaryDirectory(dir=output) as temp:
            p=Path(temp);paths=AppDataPaths(p/"data")
            started=perf_counter()
            source=save_input(p/"input.xlsx",{n+4:LOW_ROW for n in range(count)})
            before=sha256(source.read_bytes()).hexdigest()
            result=create_batch_evaluation_service(paths=paths).evaluate_workbook(source,destination=p/"out.xlsx")
            elapsed=perf_counter()-started
            assert result.summary.data_row_count==count
            assert result.summary.total_quantity==2*count
            assert result.summary.conclusion_quantities=={"1级":2*count}
            assert result.summary.boiler_minimum_limit["quantities"]=={"未达到限定值":2*count}
            assert not result.batch_record_error
            assert sha256(source.read_bytes()).hexdigest()==before
            rows=BoilerWorkbookReader().read(p/"out.xlsx").rows
            assert len(rows)==count and all(not row.input_errors and str(row.values["design_limit_pct"])=="90" for row in rows)
            check=validate_v6_template(p/"out.xlsx");assert check.is_valid,check.issues
            with closing(sqlite3.connect(paths.records_db)) as db:
                counts=(db.execute("select count(*) from record").fetchone()[0],db.execute("select count(*) from batch_record").fetchone()[0])
                assert counts==(0,1)
            evidence.append(dict(rows=count,quantity=2*count,record_count=counts[0],batch_record_count=counts[1],elapsed_seconds=round(elapsed,3),result="PASS",native_engine="NOT_RUN"))
            print(json.dumps(evidence[-1],ensure_ascii=False),flush=True)
    (output/"capacity.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    run(sys.argv[1] if len(sys.argv)>1 else ROOT/"outputs/boiler-capacity-20261117")
