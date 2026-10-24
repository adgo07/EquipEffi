import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const root=path.dirname(fileURLToPath(import.meta.url));
const rows=JSON.parse(await fs.readFile(path.join(root,'data/table_values.json'),'utf8'));
const wb=Workbook.create();
for(let t=1;t<=4;t++){
  const s=wb.worksheets.add(`表${t}`); s.showGridLines=false;
  s.getRange('A1').values=[[`GB 19761—2020 表${t} 原始限值`]];
  s.getRange('A2').values=[['来源：用户PDF；完整SHA及官方元数据见本目录 evidence/SOURCE.md']];
  s.getRange('A3').values=[['百分数点值；未施加结构修正；执行者自核，未经独立逐格验收']];
  const rr=rows.filter(x=>x.table===t);
  const data=[['源分支ID','压力系数/轮毂比','比转速','机号','3级 (%)','2级 (%)','1级 (%)','指标','原文定位','结构与适用说明'],
    ...rr.map(r=>[r.id,r.condition,r.ns,r.size,r.g3??'—',r.g2??'—',r.g1??'—',r.metric,r.source,r.note])];
  const end=4+rr.length;
  s.getRange(`A4:J${end}`).values=data;
  s.getRange(`A1:J${end}`).format.font={name:'Microsoft YaHei',size:10,color:'#202B33'};
  s.getRange('A1').format.font={name:'Microsoft YaHei',size:14,bold:true};
  s.getRange('A2:A3').format.font={name:'Microsoft YaHei',size:10,color:'#586774'};
  s.getRange(`A4:J${end}`).format.rowHeight=30;
  s.getRange('A4:J4').format={fill:'#284A66',font:{name:'Microsoft YaHei',size:10,color:'#FFFFFF',bold:true},horizontalAlignment:'center',verticalAlignment:'center'};
  for(const [c,width] of Object.entries({A:26,B:22,C:19,D:21,E:12,F:12,G:12,H:13,I:42,J:72})) s.getRange(`${c}1:${c}${end}`).format.columnWidth=width;
  s.getRange(`E5:G${end}`).setNumberFormat('0');
  s.getRange(`E5:G${end}`).format.horizontalAlignment='right';
  s.getRange(`A5:J${end}`).format.verticalAlignment='center';
  s.freezePanes.freezeRows(4);
  s.tables.add(`A4:J${end}`,true,`GB19761Table${t}`);
}
wb.recalculate();
const log=[];
for(let t=1;t<=4;t++){
  log.push((await wb.inspect({kind:'region',sheetId:`表${t}`,range:'A4:J8',maxChars:1800,tableMaxCols:10})).ndjson);
  const pic=await wb.render({sheetName:`表${t}`,range:'A1:I10',scale:1.5,format:'png'});
  await fs.writeFile(path.join(root,`_tmp/workbook_table${t}.png`),new Uint8Array(await pic.arrayBuffer()));
}
// Special split row and dash must be visible in a separate close-up.
const special=await wb.render({sheetName:'表2',range:'A43:J53',scale:1.3,format:'png'});
await fs.writeFile(path.join(root,'_tmp/workbook_special.png'),new Uint8Array(await special.arrayBuffer()));
log.push((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:30},summary:'error scan'})).ndjson);
await fs.writeFile(path.join(root,'_tmp/artifact_inspect.txt'),log.join('\n'));
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'data/GB19761_2020_表1-4核对工作簿.xlsx'));
console.log('Exported four source tables, 135 branches; no business formulas.');
