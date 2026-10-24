import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),tmp=path.join(root,'tmp');
const tables=JSON.parse(await fs.readFile(path.join(tmp,'workbook_data.json'),'utf8'));
const wb=Workbook.create();
const font='Arial';
const col=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26)}return s};
function base(s,rows,cols){s.showGridLines=false;s.getRange(`A1:${col(cols)}${rows}`).format.font={name:font,size:10};s.getRange(`A1:${col(cols)}${rows}`).format.rowHeight=22;s.getRange(`A1:${col(cols)}${rows}`).format.verticalAlignment='center';}
function header(s,range){s.getRange(range).format={fill:'#243C56',font:{name:font,size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};}
const idx=wb.worksheets.add('使用说明与索引');base(idx,44,8);
idx.getRange('A2').values=[['GB 30253—2024 标准表值整理']];idx.getRange('A2').format.font={name:font,size:15,bold:true};
idx.getRange('A3').values=[['Stage A 工作资料；未经独立验收或冻结。原文疑点保留，禁止据此直接宣布正式支持。']];
idx.getRange('A4').values=[['数据单位：功率 kW；转速 r/min；效率 %（85.9表示85.9%，并非0.859）。无评价公式。']];
idx.getRange('A5').values=[['来源：用户提供 GB 30253—2024 PDF；PDF物理页7～51，印刷页3～47。完整路径与SHA见README。']];
idx.getRange('A6').values=[['原文短横线保留为“—”；表01!N23的0.0为待确认疑点R1，不能自动视为有效下限。']];
idx.getRange('A8:H8').values=[['表 / Sheet','电机类别','电压','冷却方式','等级','功率行数','PDF物理页','印刷页']];header(idx,'A8:H8');idx.getRange('A8:H8').format.rowHeight=34;
idx.getRange(`A9:H37`).values=tables.map(t=>[t.sheet,t.kind,t.voltage,t.cooling,t.grades.join('、'),t.rows.length,[...new Set(t.rows.map(r=>r.page))].join('、'),[...new Set(t.rows.map(r=>r.printed))].join('、')]);
idx.getRange('A9:H37').format.wrapText=true;idx.getRange('A9:H37').format.rowHeight=40;idx.getRange('E9:H37').format.horizontalAlignment='center';
for(const [c,w] of [['A',14],['B',16],['C',27],['D',47],['E',10],['F',12],['G',21],['H',21]])idx.getRange(`${c}1:${c}44`).format.columnWidth=w;
idx.getRange('A39').values=[['核验：10,803个效率位置（10,651数字、152短横线）逐格机械对照；不是独立逐格人工验收。']];
idx.getRange('A40').values=[['问题：R1疑似0.0笔误；R2 GB/T755容差引用；R3区间速度与插值衔接。详见目录内登记请求。']];
idx.getRange('A41').values=[['每个表第6行是列头；第7行起为完整数据。右侧保留页码、源分表序及源行。']];
idx.freezePanes.freezeRows(8);
for(const t of tables){
 const s=wb.worksheets.add(t.sheet); const n=t.axes.length*t.grades.length, end=7+t.rows.length-1;
 base(s,end,n+5);s.getRange(`A1:${col(n+5)}${end}`).format.columnWidth=12;
 s.getRange(`A1:A${end}`).format.columnWidth=18;
 s.getRange('A2').values=[[`表${t.no} ${t.kind}永磁同步电动机能效等级`]];s.getRange('A2').format.font={name:font,size:14,bold:true};
 s.getRange('A3').values=[[`电压：${t.voltage}；冷却：${t.cooling}；效率单位：%`]];
 s.getRange('A4').values=[[t.no===1?'原文0.0位于N23；R1需确认。短横线不是0，不能前向填充。':'来源：GB 30253—2024；页码见每行右侧；规则须配套阅读STANDARD_MAPPING.md。']];
 s.getRange('A5').values=[['表值原样整理；等级/极数或转速条件不可互换，不是计算工作簿。']];
 const labels=t.grades.flatMap(g=>t.axes.map(a=>`${g}级\n${a}${t.no<=7?'极':' r/min'}`));
 s.getRange(`A6:${col(n+5)}6`).values=[['额定功率 kW',...labels,'PDF物理页','印刷页','页内表序','源行(含表头)']];header(s,`A6:${col(n+5)}6`);s.getRange(`A6:${col(n+5)}6`).format.rowHeight=50;
 if(t.no>=8&&t.no<=10)s.getRange(`B1:E${end}`).format.columnWidth=20;
 s.getRange(`A7:${col(n+5)}${end}`).values=t.rows.map(r=>[r.power,...r.values,r.page,r.printed,r.part,r.source_row]);
 t.rows.forEach((r,i)=>{if(typeof r.power==='number')s.getRange(`A${i+7}`).setNumberFormat(Number.isInteger(r.power)?'0':r.power===0.55||r.power===0.75?'0.00':'0.0');});s.getRange(`B7:${col(n+1)}${end}`).setNumberFormat('0.0');
 s.getRange(`B7:${col(n+5)}${end}`).format.horizontalAlignment='right';
 for(let rr=7;rr<=end;rr+=2)s.getRange(`A${rr}:${col(n+5)}${rr}`).format.fill='#F1F4F7';
 if(t.no===1){s.getRange('N23').format.fill='#FFE5B5';s.getRange('N23').format.font={name:font,size:10,bold:true,color:'#8B3400'};}
 s.freezePanes.freezeRows(6);s.freezePanes.freezeColumns(1);
}
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'表01!L22:P24',include:'values,formulas',tableMaxRows:3,tableMaxCols:5})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},summary:'error scan'})).ndjson);
const out=await SpreadsheetFile.exportXlsx(wb);await out.save(path.join(root,'data/GB30253_2024_TABLE_VALUES.xlsx'));
for(const name of ['使用说明与索引',...tables.map(t=>t.sheet)]){
 const t=tables.find(t=>t.sheet===name);const end=t?col(t.axes.length*t.grades.length+5):'H';
 const blob=await wb.render({sheetName:name,range:`A1:${end}${t?Math.min(34,t.rows.length+6):18}`,scale:1,format:'png'});
 await fs.writeFile(path.join(tmp,`preview-${name}.png`),new Uint8Array(await blob.arrayBuffer()));
 console.log('rendered',name);
}
