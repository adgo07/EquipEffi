// Reproducible, static source-table workbook. Run with @oai/artifact-tool available.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const base=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(base,'data/tables.json'),'utf8'));
const wb=Workbook.create();
for(const [n,rows] of Object.entries(data.tables)){
 const sh=wb.worksheets.add(`表${n}`), end=rows.length+5;
 sh.showGridLines=false;
 sh.getRange(`A1:L${end}`).format.font={name:'Microsoft YaHei',size:10};
 sh.getRange(`A1:L${end}`).format.rowHeight=24;
 sh.getRange('A1').values=[[`GB 28381—2012 表${n} ${rows[0].branch}${Number(n)<=4?'能效限定值':'节能评价值'}`]];
 sh.getRange('A1').format.font={name:'Microsoft YaHei',size:14,bold:true};
 sh.getRange('A2').values=[['来源：9. GB 28381-2012 离心鼓风机能效限定值及节能评价值.pdf；原页定位见I/J列。']];
 sh.getRange('A3').values=[['核验：480格机械一致性；原页视觉抽核另见evidence；非独立验收，不是计算引擎。']];
 sh.getRange('A4').values=[['D:H数值单位：%（51.0代表51.0%）；仅原表基础值，修正规则及疑点见STANDARD_MAPPING。']];
 sh.getRange('A5:L5').values=[['源行','b2/D2 原区间','级数 Z',...data.diameters_mm.map(d=>`D2 ${d} mm`),'印刷页','PDF页','源格组','合并语义']];
 sh.getRange(`A6:L${end}`).values=rows.map(r=>[r.source_row,r.ratio,r.stages,...r.values.map(Number),r.printed_page,r.pdf_page,`T${n}-R${String(r.source_row).padStart(2,'0')}-C1:C5`,Number(n)%2?'无纵向合并':'比值源格跨两级数行，展开保留']);
 sh.getRange('A5:L5').format={fill:'#233E58',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:38};
 sh.getRange(`D6:H${end}`).setNumberFormat('0.0');
 sh.getRange(`A6:A${end}`).setNumberFormat('0');
 sh.getRange(`I6:J${end}`).setNumberFormat('0');
 for(const [col,width] of Object.entries({A:8,B:19,C:10,D:15,E:17,F:17,G:17,H:15,I:9,J:9,K:24,L:37})) sh.getRange(`${col}5:${col}${end}`).format.columnWidth=width;
 sh.getRange(`D6:J${end}`).format.horizontalAlignment='right';
 sh.freezePanes.freezeRows(5);
}
wb.recalculate();
await fs.writeFile(path.join(base,'tmp/artifact_inspect.json'),JSON.stringify(await wb.inspect({kind:'sheet',include:'id,name'})));
await fs.writeFile(path.join(base,'tmp/artifact_errors.json'),JSON.stringify(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20}})));
for(const [n,rows] of Object.entries(data.tables)){
 const image=await wb.render({sheetName:`表${n}`,range:`A1:L${rows.length+5}`,scale:1,format:'png'});
 await fs.writeFile(path.join(base,`tmp/workbook-${n}.png`),new Uint8Array(await image.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(base,'data/GB28381_2012_TABLES.xlsx'));
console.log('Exported eight source-table sheets. No business formulas.');
