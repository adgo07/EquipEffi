import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const dir=path.dirname(fileURLToPath(import.meta.url));
const tables=JSON.parse(await fs.readFile(path.join(dir,'data/tables.json'),'utf8'));
const wb=Workbook.create();
for(const t of tables){
 const s=wb.worksheets.add(`表${t.n}`);
 s.showGridLines=false;
 if(t.rows.length>10)s.freezePanes.freezeRows(5);
 const last=String.fromCharCode(69+t.branches.length),end=t.rows.length+5;
 s.getRange(`A1:${last}${end+5}`).format.font={name:'Microsoft YaHei',size:10,color:'#263238'};
 s.getRange('A2').values=[[`GB 32030—2022 表${t.n}  ${t.name}`]];
 s.getRange('A2').format.font={name:'Microsoft YaHei',size:14,bold:true};
 s.getRange('A3').values=[[t.n===5?'引用等级原样保留；具体容差系数尚未核验':`数值为 ${t.base} 上的百分点增量；— 为原表破折号；三级减容差，非绝对效率`]];
 s.getRange('A4').values=[['执行者自核，非独立验收；合并跨度见逐格CSV。']];
 s.getRange(`A5:${last}5`).values=[['等级','下限 kW','关系','上限 kW','关系',...t.branches]];
 const rows=t.rows.map(r=>r.map((v,c)=>c>=5&&v===null?'—':c>=5&&v==='-Δη'&&t.base==='ηgr'?'-Δηgr':v));
 s.getRange(`A6:${last}${end}`).values=rows;
 s.getRange(`A5:${last}5`).format={fill:'#263E55',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},rowHeight:36,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
 s.getRange(`A6:${last}${end}`).format.rowHeight=27;
 s.getRange(`A5:A${end}`).format.columnWidth=7;
 s.getRange(`B5:B${end}`).format.columnWidth=12;
 s.getRange(`D5:D${end}`).format.columnWidth=12;
 s.getRange(`C5:C${end}`).format.columnWidth=6;
 s.getRange(`E5:E${end}`).format.columnWidth=6;
 s.getRange(`F5:${last}${end}`).format.columnWidth=t.n===2?21:16;
 s.getRange(`B6:D${end}`).setNumberFormat('0');
 for(let i=0;i<rows.length;i++)for(const c of [1,3])if(rows[i][c]!==null&&!Number.isInteger(rows[i][c]))s.getRange(`${String.fromCharCode(65+c)}${i+6}`).setNumberFormat('0.0');
 if(t.n!==5)s.getRange(`F6:${last}${end}`).setNumberFormat('0.0');
 s.getRange(`A6:${last}${end}`).format.verticalAlignment='center';
 s.getRange(`C6:C${end}`).format.horizontalAlignment='center';
 s.getRange(`E6:E${end}`).format.horizontalAlignment='center';
 for(let i=0;i<rows.length;i++)for(let c=5;c<rows[i].length;c++)if(typeof rows[i][c]==='string')s.getRange(`${String.fromCharCode(65+c)}${i+6}`).format.horizontalAlignment='center';
 for(let i=0;i<t.rows.length;i++){
  if(i===0||t.rows[i][0]!==t.rows[i-1][0])s.getRange(`A${i+6}:${last}${i+6}`).format.borders={top:{style:'thin',color:'#8193A5'}};
  if(t.rows[i][0]===2)s.getRange(`A${i+6}:${last}${i+6}`).format.fill='#F1F5F8';
 }
 s.getRange(`A${end+2}`).values=[['来源：GB32030—2022，S00；SHA见真实性核验档。']];
 const ps=[...new Set(Object.values(t.pages))];
 s.getRange(`A${end+3}`).values=[[`本地PDF ${ps.join('、')}，印刷页 ${ps.map(p=>p-2).join('、')}；物理源格见逐格CSV。`]];
 s.getRange(`A${end+4}`).values=[['空端点非0；外部基准效率及容差尚未核验。']];
}
wb.recalculate();
await fs.writeFile(path.join(dir,'tmp/workbook_inspect.jsonl'),(await wb.inspect({kind:'table',range:'表1!A5:L14',include:'values,formulas',tableMaxRows:12,tableMaxCols:12,maxChars:5000})).ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:30},summary:'error scan'});
await fs.writeFile(path.join(dir,'tmp/workbook_errors.jsonl'),errors.ndjson);
for(const t of tables){
 const last=String.fromCharCode(69+t.branches.length);
 const blob=await wb.render({sheetName:`表${t.n}`,range:`A1:${last}${t.rows.length+10}`,scale:1.5,format:'png'});
 await fs.writeFile(path.join(dir,`tmp/workbook_table${t.n}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(dir,'data/GB32030_2022_表值映射.xlsx'));
console.log('Exported 6 tables');
