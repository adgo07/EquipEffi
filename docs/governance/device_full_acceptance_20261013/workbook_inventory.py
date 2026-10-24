"""List actual XLSX worksheets/cells via ZIP/XML without resaving workbooks."""
from pathlib import Path
import json, zipfile, xml.etree.ElementTree as ET, posixpath
OUT=Path(__file__).resolve().parent
source=json.loads((OUT/'preflight_inventory.json').read_text(encoding='utf-8'))
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
items=[]
for standard in source['standards']:
 for book in standard['workbooks']:
  with zipfile.ZipFile(book['absolute_path']) as z:
   wb=ET.fromstring(z.read('xl/workbook.xml'))
   rels={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
   for sheet in wb.findall('m:sheets/m:sheet',NS):
    target=rels[sheet.attrib['{'+REL+'}id']]
    target=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
    xml=ET.fromstring(z.read(target))
    cells=xml.findall('.//m:sheetData/m:row/m:c',NS)
    valued=[c for c in cells if c.find('m:v',NS) is not None or c.find('m:is',NS) is not None or c.find('m:f',NS) is not None]
    items.append({'standard_key':standard['key'],'workbook':book['absolute_path'],
     'workbook_sha256':book['sha256'],'sheet':sheet.attrib['name'],
     'xml_path':target,'dimension':xml.find('m:dimension',NS).attrib.get('ref') if xml.find('m:dimension',NS) is not None else None,
     'stored_cells':len(cells),'valued_cells':len(valued),
     'formula_coordinates':[c.attrib['r'] for c in cells if c.find('m:f',NS) is not None],
     'error_coordinates':[c.attrib['r'] for c in cells if c.attrib.get('t')=='e'],
     'merged_ranges':[m.attrib['ref'] for m in xml.findall('m:mergeCells/m:mergeCell',NS)],
     'semantic_acceptance':'NOT_DETERMINED_BY_STRUCTURAL_INVENTORY'})
(OUT/'workbook_sheet_inventory.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'books':len(set(x['workbook'] for x in items)),'sheets':len(items),'formulas':sum(len(x['formula_coordinates']) for x in items),'errors':sum(len(x['error_coordinates']) for x in items)},ensure_ascii=False))
