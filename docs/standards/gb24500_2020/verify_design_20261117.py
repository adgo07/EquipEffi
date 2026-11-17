"""只读核对设计引用与已核验源表；不写回标准或模板。"""
from pathlib import Path
from hashlib import sha256
from fractions import Fraction
import csv
import json
import re
import subprocess
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook
from equipeffi.infrastructure.excel.template_resource import V66CompressorTemplateResource

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def main():
    workbook = HERE / 'data/GB24500_2020_TABLE_VALUES.xlsx'
    digest = sha256(workbook.read_bytes()).hexdigest()
    assert digest == '9f8e243b96ea45cd0c1f1a33dc1c0a7b62eaa8a5f2f9095234c427463a68de1a'
    evidence = ROOT/'docs/governance/device_full_acceptance_20261013/compressor_boiler/independent_cells.csv'
    with evidence.open(encoding='utf-8-sig', newline='') as stream:
        expected = [r for r in csv.DictReader(stream) if r['standard']=='GB24500-2020']
    assert len(expected) == 79
    with OOXMLWorkbook(workbook) as source:
        grids = {name:source.rows(name) for name in source.sheet_names}
    for row in expected:
        match = re.fullmatch(r'([A-Z]+)(\d+)',row['cell'])
        column=0
        for c in match[1]: column=column*26+ord(c)-64
        actual=grids[row['sheet']][int(match[2])-1][column-1]
        assert Fraction(str(actual)) == Fraction(row['source']), row
        assert row['result']=='PASS'
    design=(HERE/'INTEGRATION_DESIGN.md').read_text(encoding='utf-8')
    links=re.findall(r'\]\(([^)]+)\)',design)
    local=[link.split('#')[0] for link in links if not re.match(r'https?://',link)]
    for link in local: assert (HERE/link).exists(),link
    template=V66CompressorTemplateResource().template_path
    with OOXMLWorkbook(template) as book:
        names=book.sheet_names
        headers=book.rows('工业锅炉')[2]
    assert len(names)==18 and names[8]=='工业锅炉' and len(headers)==19
    assert headers[11]=='设计热效率\n(%)'
    protected=['platform-lock.json','docs/standards/gb24500_2020/STANDARD_MAPPING.md',
               'docs/standards/gb24500_2020/data/GB24500_2020_TABLE_VALUES.xlsx',
               'src/equipeffi/resources/templates/'+template.name]
    hashes={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in protected}
    changed=subprocess.check_output(['git','diff','--name-only','987e9562','--',*protected],cwd=ROOT,text=True).strip()
    assert not changed,changed
    result=dict(date='2026-11-17',source_baseline='987e9562e8eba448ebce4a477ed67c6295c96075',
                scope='Stage B design and read-only source identity validation',
                workbook_sha256=digest,table_values=78,clause_limit_values=1,
                comparison_to_existing_independent_evidence=dict(pass_count=79,fail=0,error=0,skip=0),
                source_pdf_reaudit='NOT_RUN; inherited fixed-hash original-page evidence',
                local_links_checked=len(local),broken_links=[],
                existing_template=dict(version='V6.6',sheets=names,boiler_headers=headers),
                protected_hashes=hashes,protected_git_diff='EMPTY',
                owner_boundary='Organic heat-carrier unresolved combinations deferred; confirmed branches only',
                unit_tests='NOT_RUN: design-only, production unchanged',
                compileall='NOT_RUN: design-only',smoke='NOT_RUN: design-only',performance='NOT_RUN: design-only',
                implementation_authorized=False,support_status_changed=False)
    (HERE/'DESIGN_VERIFICATION_20261117.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_checks':79,'local_links':len(local),'protected_diff':'EMPTY'},ensure_ascii=False))

if __name__=='__main__': main()
