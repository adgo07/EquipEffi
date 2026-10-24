import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const rows=JSON.parse(await fs.readFile(path.join(base,'_work/decoded_rows.json'),'utf8'));
const wb=Workbook.create();
const voltage={1:'3 kV（含3.3 kV）、6 kV',2:'10 kV',3:'3 kV（含3.3 kV）、6 kV',4:'10 kV',5:'3 kV（含3.3 kV）、6 kV',6:'10 kV'};
const cooling={1:'IC01、IC11、IC21、IC31、IC81W',2:'IC01、IC11、IC21、IC31、IC81W',3:'IC611、IC616、IC511、IC516',4:'IC611、IC616、IC511、IC516',5:'IC411',6:'IC411'};
const sha='53a6d2e8098fea9f81adf6a12fe3298707bf6b22cc8c972110aacdcd8a168135';
const col=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
for(let t=1;t<=6;t++){
 const sh=wb.worksheets.add(`表${t}`), data=rows.filter(r=>r.table===t), poles=t<5?[2,4,6,8,10,12]:[2,4,6,8];
 const nc=1+poles.length*3;
 const headers=['额定功率 kW',...poles.flatMap(p=>[1,2,3].map(g=>`${p}极 ${g}级 %`)),'PDF物理页','印刷页','原页数据行'];
 sh.showGridLines=false;
 sh.getRange('A2').values=[[`GB 30254—2024 表${t}  效率限值（%）`]];
 sh.getRange('A3').values=[[`电压：${voltage[t]}；冷却：${cooling[t]}。50 Hz，连续工作制，额定输出功率下实测效率。`]];
 sh.getRange('A4').values=[['Stage A 表值整理；— 为原表破折号，不是0。容差及无表值分支解释待确认，未独立验收、未冻结。']];
 sh.getRange('A5').values=[['来源：用户提供PDF，物理页见右侧逐行定位；原文SHA-256：'+sha]];
 sh.getRange(`A7:${col(headers.length)}7`).values=[headers];
 const matrix=data.map(r=>[...r.values.map(v=>v==='—'?v:Number(v)),r.pdf_page,r.printed_page,r.page_row]);
 sh.getRange(`A8:${col(headers.length)}${7+data.length}`).values=matrix;
 const used=sh.getRange(`A2:${col(headers.length)}${7+data.length}`);
 used.format.font={name:'Microsoft YaHei',size:10,color:'#233044'};
 used.format.rowHeight=22; used.format.verticalAlignment='center';
 sh.getRange('A2').format.font={name:'Microsoft YaHei',size:14,bold:true,color:'#243B53'};
 sh.getRange('A3:A5').format.font={name:'Microsoft YaHei',size:10,color:'#526574'};
 sh.getRange(`A7:${col(headers.length)}7`).format={fill:'#243B53',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},rowHeight:30,horizontalAlignment:'center'};
 sh.getRange(`A7:A${7+data.length}`).format.columnWidth=15;
 sh.getRange(`B7:${col(nc)}${7+data.length}`).format.columnWidth=12;
 sh.getRange(`${col(nc+1)}7:${col(nc+3)}${7+data.length}`).format.columnWidth=14;
 sh.getRange(`A8:${col(headers.length)}${7+data.length}`).format.horizontalAlignment='right';
 sh.getRange(`A8:A${7+data.length}`).setNumberFormat('0');
 sh.getRange(`B8:${col(nc)}${7+data.length}`).setNumberFormat('0.0');
 sh.getRange(`${col(nc+1)}8:${col(nc+3)}${7+data.length}`).setNumberFormat('0');
 for(let i=0;i<data.length;i++){
  if(i%2===1)sh.getRange(`A${i+8}:${col(headers.length)}${i+8}`).format.fill='#F2F5F8';
  for(let j=1;j<nc;j++)if(data[i].values[j]!=='—'&&!data[i].values[j].includes('.'))sh.getRange(`${col(j+1)}${i+8}`).setNumberFormat('0');
 }
 sh.freezePanes.freezeRows(7);
}
wb.recalculate();
const checks=[];
for(let t=1;t<=6;t++){
 checks.push((await wb.inspect({kind:'table',range:`表${t}!A7:G10`,include:'values,formulas',tableMaxRows:4,tableMaxCols:7})).ndjson);
 const p=await wb.render({sheetName:`表${t}`,range:'A2:M14',scale:1.4,format:'png'});
 await fs.writeFile(path.join(base,`_work/workbook_table${t}.png`),new Uint8Array(await p.arrayBuffer()));
}
checks.push((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20}})).ndjson);
await fs.writeFile(path.join(base,'_work/artifact_checks.txt'),checks.join('\n'));
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(base,'data/GB30254_2024_标准表值.xlsx'));
console.log('Exported six source tables.');
