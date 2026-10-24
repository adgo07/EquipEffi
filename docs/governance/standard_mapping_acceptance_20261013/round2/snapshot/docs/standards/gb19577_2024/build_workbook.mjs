import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(root,'data/table_values.json'),'utf8'));
const wb=Workbook.create();
const headers=['源行','产品标准','物理分支','容量条件(kW)','等级主指标','1级','2级','3级','附加指标1','3级值','附加指标2','3级值','原文定位','条件说明'];
function base(name,title,heads,last){
  const s=wb.worksheets.add(name);s.showGridLines=false;
  s.getRange(`A1:${last}30`).format.font={name:'Microsoft YaHei',size:10};
  s.getRange('A2').values=[[title]];s.getRange('A2').format.font={bold:true,size:14};
  s.getRange('A3').values=[['Stage A校对资料；非正式算法，非独立验收；配套主映射与问题台账必须同时阅读']];
  s.getRange('A4').values=[['来源：GB 19577—2024 用户PDF；SHA256 '+data.source_sha256]];
  s.getRange(`A5:${last}5`).values=[heads];
  s.getRange(`A5:${last}5`).format={fill:'#213C57',font:{name:'Microsoft YaHei',color:'#FFFFFF',bold:true},rowHeight:32,wrapText:true};
  s.getRange(`A5:${last}5`).format.horizontalAlignment='center';
  s.freezePanes.freezeRows(5);
  return s;
}
for (const [key,rows] of Object.entries(data.tables)){
 const s=base('表'+key,'表'+key+' 能效等级指标',headers,'N');
 const matrix=rows.map(r=>[r.source_row,r.standard,r.branch,r.capacity,r.metric,...r.values.map(Number),r.aux,r.aux_value===null?null:Number(r.aux_value),r.aux2,r.aux2_value===null?null:Number(r.aux2_value),`印刷${r.printed_page} / PDF${r.pdf_page} / 源行${r.source_row}`,r.note]);
 s.getRange(`A6:N${rows.length+5}`).values=matrix;
 s.getRange(`A6:N${rows.length+5}`).format.rowHeight=46;
 s.getRange(`A6:N${rows.length+5}`).format.verticalAlignment='center';
 s.getRange(`B6:E${rows.length+5}`).format.wrapText=true;
 s.getRange(`N6:N${rows.length+5}`).format.wrapText=true;
 s.getRange(`I6:I${rows.length+5}`).format.horizontalAlignment='center';
 s.getRange(`K6:K${rows.length+5}`).format.horizontalAlignment='center';
 const widths=[9,26,34,22,26,10,10,10,15,10,15,10,31,64];
 widths.forEach((w,i)=>s.getRangeByIndexes(4,i,rows.length+1,1).format.columnWidth=w);
 rows.forEach((r,i)=>{
   const vals=[...r.values,r.aux_value,r.aux2_value];
   vals.forEach((v,j)=>{if(v!==null)s.getRange(['F','G','H','J','L'][j]+(i+6)).setNumberFormat(v.includes('.')?'0.'+'0'.repeat(v.split('.')[1].length):'0');});
   if(i%2===1)s.getRange(`A${i+6}:N${i+6}`).format.fill='#F1F5F8';
 });
}
const a1=base('表A.1','表A.1 制冷季节性能系数试验工况',['测试点','负荷率','出水温度(℃)','流量 m³/(h·kW)','干球温度(℃)','湿球温度','源格与条件'],'G');
a1.getRange('A6:G9').values=data.a1.map((r,i)=>[r.point,Number(r.load)/100,Number(r.outlet),Number(r.flow),Number(r.dry),r.wet,`印刷8/PDF14；源行${i+1}；流量原格合并A～D；按名义制冷量明示值确定`]);
a1.getRange('B6:B9').setNumberFormat('0%');a1.getRange('C6:C9').setNumberFormat('0');a1.getRange('D6:D9').setNumberFormat('0.000');
data.a1.forEach((r,i)=>a1.getRange('E'+(i+6)).setNumberFormat(r.dry.includes('.')?'0.'+'0'.repeat(r.dry.split('.')[1].length):'0'));
a1.getRange('A5:F9').format.columnWidth=20;a1.getRange('G5:G9').format.columnWidth=64;a1.getRange('A6:G9').format.rowHeight=40;a1.getRange('G6:G9').format.wrapText=true;
a1.getRange('F6:F9').format.horizontalAlignment='center';
a1.getRange('A11').values=[['标准条件：B/C/D负荷率允差±2%，A点除外；插值/衰减计算仍保持目标点冷凝器侧干球温度。']];
a1.getRange('A12').values=[['B点32.25℃按原表保存；正文32.3℃差异见EQP-STD-GB19577-003。湿球横线不是0℃。']];
const a2=base('表A.2','表A.2 制冷季节温度区间发生时间',['区间j','室外温度(℃)','小时数(h)','原表位置','来源'],'E');
a2.getRange('A6:E20').values=data.a2.map((r,i)=>[r.j,r.temp,r.hours,`${i<8?'左半':'右半'}源行${i%8+1}`,'表A.2 印刷8/PDF14']);
a2.getRange('A21:E21').values=[['合计',null,1007,'原表明示合计','印刷8/PDF14']];
a2.getRange('A5:C21').format.columnWidth=21;a2.getRange('D5:D21').format.columnWidth=22;a2.getRange('E5:E21').format.columnWidth=34;a2.getRange('A6:E21').format.rowHeight=27;
a2.getRange('A6:C21').setNumberFormat('0');
a2.getRange('D6:D21').format.horizontalAlignment='center';
wb.recalculate();
const inspect=await wb.inspect({kind:'region',sheetId:'表1',range:'E6:L11',maxChars:3000,tableMaxRows:6,tableMaxCols:8});
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},maxChars:1500});
await fs.writeFile(path.join(root,'tmp/artifact_inspect.txt'),inspect.ndjson+'\n'+errors.ndjson);
const out=await SpreadsheetFile.exportXlsx(wb);await out.save(path.join(root,'data/GB19577_2024_TABLE_VALUES.xlsx'));
for(const s of wb.worksheets.items){
 const last=s.name==='表A.1'?'G12':s.name==='表A.2'?'E21':'N'+(data.tables[s.name.slice(1)].length+5);
 const pic=await wb.render({sheetName:s.name,range:'A2:'+last,scale:1,format:'png'});
 await fs.writeFile(path.join(root,'tmp',s.name+'.png'),new Uint8Array(await pic.arrayBuffer()));
}
console.log('Exported 10 sheets and rendered all 10.');
