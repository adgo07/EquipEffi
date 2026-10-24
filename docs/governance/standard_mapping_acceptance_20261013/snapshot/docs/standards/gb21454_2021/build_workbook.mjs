import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const root=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(root,'data/table_values.json'),'utf8'));
const wb=Workbook.create();
for(const t of data.tables){
  const s=wb.worksheets.add(t.name); const end=String.fromCharCode(64+t.headers.length);const last=5+t.rows.length;
  s.showGridLines=false;
  s.getRange(`A1:${end}${last+7}`).format.font={name:'Microsoft YaHei',size:11};
  s.getRange('A2').values=[[`GB 21454—2021 ${t.name} ${t.title}`]];
  s.getRange('A2').format.font={name:'Microsoft YaHei',size:15,bold:true};
  s.getRange('A3').values=[['标准表值整理稿；执行者自核，未经独立逐格验收']];
  s.getRange('A3').format.font={color:'#8A4B08',italic:true};
  s.getRange(`A5:${end}5`).values=[t.headers];
  s.getRange(`A6:${end}${last}`).values=t.rows;
  s.getRange(`A5:${end}5`).format={fill:'#263D55',font:{name:'Microsoft YaHei',size:11,color:'#FFFFFF',bold:true},wrapText:true,rowHeight:42};
  s.getRange(`A6:${end}${last}`).format.rowHeight=28;
  s.getRange(`A5:${end}${last}`).format.verticalAlignment='center';
  s.getRange(`A5:${end}${last}`).format.columnWidth=23;
  s.getRange(`A5:A${last}`).format.columnWidth=27;
  for(let i=0;i<t.headers.length;i++) {
    const c=String.fromCharCode(65+i);
    if(t.numeric.includes(i)) {
      s.getRange(`${c}6:${c}${last}`).setNumberFormat(t.formats[c]||'0.00');
      s.getRange(`${c}6:${c}${last}`).format.horizontalAlignment='center';
    }
  }
  if(t.name==='表3') s.getRange('C5:C9').format.columnWidth=27;
  if(t.name==='表A.3'||t.name==='表A.4') s.getRange(`D5:D${last}`).format.columnWidth=49;
  for(let r=6;r<=last;r++) if(r%2===0) s.getRange(`A${r}:${end}${r}`).format.fill='#F0F4F8';
  const notes=[...t.notes,'原PDF SHA-256：'+data.source_sha256];
  notes.forEach((v,i)=>{s.getRange(`A${last+2+i}`).values=[[v]];s.getRange(`A${last+2+i}`).format.rowHeight=25;});
  s.freezePanes.freezeRows(5);
  if(t.sourceTotal!==undefined){s.getRange(`B${last+1}`).values=[['原文总计 (h)']];s.getRange(`C${last+1}`).values=[[t.sourceTotal]];s.getRange(`C${last+1}`).setNumberFormat('0');}
}
wb.recalculate();
await fs.mkdir(path.join(root,'tmp'),{recursive:true});
const inspections=[];
for(const t of data.tables){
  inspections.push((await wb.inspect({kind:'table',range:`'${t.name}'!A5:${String.fromCharCode(64+t.headers.length)}${5+t.rows.length}`,include:'values,formulas',tableMaxRows:40,tableMaxCols:8})).ndjson);
  const png=await wb.render({sheetName:t.name,range:`A1:${String.fromCharCode(64+Math.max(7,t.headers.length))}${Math.min(5+t.rows.length+6,46)}`,scale:1.3,format:'png'});
  await fs.writeFile(path.join(root,'tmp',t.name+'.png'),new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(path.join(root,'tmp/artifact_inspect.ndjson'),inspections.join('\n'));
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100}});
await fs.writeFile(path.join(root,'tmp/artifact_errors.ndjson'),errors.ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'data/GB21454_2021_标准表值.xlsx'));
await fs.rename(path.join(root,'data/GB21454_2021_标准表值.xlsx.inspect.ndjson'),path.join(root,'tmp/export_inspect.ndjson')).catch(()=>{});
console.log('exported',data.tables.length,'sheets');
