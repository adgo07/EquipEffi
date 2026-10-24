import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const root=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(root,'table_values.json'),'utf8'));
const wb=Workbook.create();
function col(n){let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;}
for(const t of data.tables){
  const sh=wb.worksheets.add(`表${t.id}`), simple=t.id<=3;
  const headers=simple?['进口流量 m³/h','1级 %','2级 %','3级 %','PDF物理页','印刷页','源网格行']:['标准流量 m³/min','等级',...t.pressures.map(p=>`${p} kPa`),'PDF物理页','印刷页','源网格行'];
  const last=col(headers.length), end=t.rows.length+4;
  sh.showGridLines=false;
  sh.getRange(`A1:${last}${end}`).format.font={name:'Microsoft YaHei',size:10};
  sh.getRange(`A1:${last}${end}`).format.rowHeight=23;
  sh.getRange('A1').values=[[`表${t.id} ${t.name}鼓风机能效等级`]];
  sh.getRange('A1').format.font={name:'Microsoft YaHei',size:14,bold:true};
  sh.getRange('A2').values=[[`来源：GB 28381—2026 表${t.id}；${simple?'效率单位%；实测值不低于限值':'容积比能单位 kJ/m³；实测值不高于限值'}`]];
  sh.getRange('A3').values=[['Stage A 待复核；“—”原样保留；完整定位和核验范围见配套主映射及 CELL_AUDIT.csv']];
  sh.getRange(`A4:${last}4`).values=[headers];
  sh.getRange(`A4:${last}4`).format={fill:'#243C55',font:{name:'Microsoft YaHei',bold:true,color:'#FFFFFF'},rowHeight:36,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
  const matrix=t.rows.map(r=>[Number(r.flow),...(simple?[]:[r.grade]),...r.tokens.map(v=>v==='—'?v:Number(v)),r.page,r.page-4,r.source_row]);
  sh.getRange(`A5:${last}${end}`).values=matrix;
  sh.getRange(`A4:A${end}`).format.columnWidth=22;
  sh.getRange(`B4:${last}${end}`).format.columnWidth=simple?16:12;
  sh.getRange(`A5:${last}${end}`).format.verticalAlignment='center';
  sh.getRange(`A5:${last}${end}`).format.horizontalAlignment='right';
  for(const [i,r] of t.rows.entries()){
    const fp=(r.flow.split('.')[1]||'').length;
    sh.getRange(`A${i+5}`).setNumberFormat(fp?'0.'+'0'.repeat(fp):'0');
    for(const [j,v] of r.tokens.entries()){
      if(v==='—') {sh.getRange(`${col(j+(simple?2:3))}${i+5}`).format.horizontalAlignment='center';continue;}
      const precision=(v.split('.')[1]||'').length;
      sh.getRange(`${col(j+(simple?2:3))}${i+5}`).setNumberFormat(precision?'0.'+'0'.repeat(precision):'0');
    }
  }
  sh.freezePanes.freezeRows(4);
  if(!simple) sh.freezePanes.freezeColumns(2);
}
wb.recalculate();
const inspected=await wb.inspect({kind:'table',range:'表5!A4:L8',include:'values,formulas',tableMaxRows:5,tableMaxCols:12,maxChars:2400});
await fs.writeFile(path.join(root,'_tmp/workbook_inspect.ndjson'),inspected.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},maxChars:1000});
await fs.writeFile(path.join(root,'_tmp/workbook_error_scan.ndjson'),errors.ndjson);
const out=await SpreadsheetFile.exportXlsx(wb);
await out.save(path.join(root,'GB28381_2026_TABLE_VALUES.xlsx'));
await fs.rename(path.join(root,'GB28381_2026_TABLE_VALUES.xlsx.inspect.ndjson'),path.join(root,'_tmp/export_inspect.ndjson')).catch(()=>{});
for(const t of data.tables){
  const last=col((t.id<=3?8:t.pressures.length+6));
  const png=await wb.render({sheetName:`表${t.id}`,range:`A1:${last}12`,scale:1.3,format:'png'});
  await fs.writeFile(path.join(root,`_tmp/workbook-${t.id}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log('Exported 6 sheets with source numeric precision and source dashes; rendered all 6.');
