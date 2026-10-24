import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(fileURLToPath(import.meta.url));
await fs.mkdir(path.join(root,'data'),{recursive:true});
await fs.mkdir(path.join(root,'evidence'),{recursive:true});
await fs.mkdir(path.join(root,'_tmp'),{recursive:true});
const wb=Workbook.create();
const bounds4=[['CC≤7100',null,7100],['7100<CC≤14000',7100,14000],['14000<CC≤28000',14000,28000],['CC>28000',28000,null]];
const boundsFresh=[['CC≤4500',null,4500],['4500<CC≤7100',4500,7100],['7100<CC≤14000',7100,14000],['CC>14000',14000,null]];
const bounds2=[['CC≤14000',null,14000],['CC>14000',14000,null]];
const blocks=[
 ['表1','风冷式','单冷型','SEER','Wh/Wh',bounds4,[[4.2,3.8,3],[4,3.6,2.9],[3.8,3.4,2.8],[3.2,3,2.6]]],
 ['表1','风冷式','热泵型','APF','Wh/Wh',bounds4,[[3.8,3.4,2.9],[3.6,3.2,2.8],[3.4,3,2.7],[3,2.8,2.4]]],
 ['表1','水冷式','源表未细分冷热型','IPLV','W/W',bounds2,[[4.2,4,3.4],[4,3.8,3.3]]],
 ['表2','风冷式','小焓差','EER','W/W',boundsFresh,[[3.4,3.2,3],[3.2,3,2.8],[3,2.8,2.6],[2.8,2.6,2.4]]],
 ['表2','风冷式','大焓差','EER','W/W',boundsFresh,[[3.2,3,2.8],[3,2.8,2.6],[2.8,2.6,2.4],[2.6,2.4,2.2]]],
 ['表2','水冷式（水环式）','小焓差','EER','W/W',bounds2,[[4.7,4.5,4.3],[4.5,4.3,4.1]]],
 ['表2','水冷式（水环式）','大焓差','EER','W/W',bounds2,[[4.4,4.2,4],[4.2,4,3.8]]],
];
const records=[];
for(const table of ['表1','表2']){
 const name=table==='表1'?'表1_风管机组':'表2_全新风机组';
 const sh=wb.worksheets.add(name); sh.showGridLines=false;
 sh.getRange('A1').values=[[`GB 37479—2019 ${table} 表值转录（Stage A）`]];
 sh.getRange('A2').values=[['来源：原PDF印刷页2 / PDF物理页4；值自核，未独立验收']];
 sh.getRange('A3').values=[['下界严格大于，上界小于等于；空端点=原文未给界限，非0；表2限定值见请求A']];
 const rows=[]; let index=0;
 for(const [t,cooling,branch,metric,unit,bounds,values] of blocks.filter(x=>x[0]===table)){
  values.forEach((v,i)=>{
   index++; const r=5+index;
   rows.push([`${table}-R${String(index).padStart(2,'0')}`,cooling,branch,metric,unit,bounds[i][0],bounds[i][1],bounds[i][2],...v,`第4章/${table}/数据行${index}`,2,4]);
   records.push({table,source_row:index,sheet:name,xlsx_row:r,cooling,branch,metric,unit,condition:bounds[i][0],lower:bounds[i][1],upper:bounds[i][2],grades:v});
  });
 }
 sh.getRange('A5:N5').values=[['源行ID','冷却方式','物理分支','指标','单位','名义制冷量条件/W','下界/W（不含）','上界/W（含）','1级','2级','3级','原文定位','印刷页','PDF页']];
 sh.getRange(`A6:N${rows.length+5}`).values=rows;
 sh.getRange(`A5:N${rows.length+5}`).format.font={name:'Microsoft YaHei',size:10};
 sh.getRange('A5:N5').format={fill:'#243F60',font:{color:'#FFFFFF',bold:true},rowHeight:32};
 sh.getRange(`A6:N${rows.length+5}`).format.rowHeight=26;
 const widths=[16,24,28,10,12,28,20,20,10,10,10,30,10,10];
 widths.forEach((width,i)=>sh.getRange(`${String.fromCharCode(65+i)}5:${String.fromCharCode(65+i)}${rows.length+5}`).format.columnWidth=width);
 sh.getRange(`G6:H${rows.length+5}`).setNumberFormat('0');
 sh.getRange(`I6:K${rows.length+5}`).setNumberFormat('0.00');
 sh.getRange('A1').format.font={name:'Microsoft YaHei',size:14,bold:true};
 sh.freezePanes.freezeRows(5);
}
const sh=wb.worksheets.add('条款数值'); sh.showGridLines=false;
const constants=[
 ['适用性静压边界',0,'Pa','静压>0（表压力）','第1章','1',3],
 ['电辅热室外干球温度边界',0,'℃','温度≥0时电辅热不得自动开启','5.3','未印（正文第3页）',5],
 ['实测能效/标注能效最低比例',0.95,'比值','实测≥标注×0.95；不是等级限值折减','5.4 b)','未印（正文第3页）',5],
 ['实测耗电计算值/标注值最高比例',1.10,'比值','实测计算值≤标注×1.10','5.4 d)','未印（正文第3页）',5],
 ['实测值小数位数',2,'位','舍入方式待补引用标准证据','6.1、6.3','未印（正文第3页）',5],
 ['SEER可选测试温度',29,'℃','额定/中间/最小能力均可选做','6.1 a)','未印（正文第3页）',5],
 ['SEER换算来源温度',35,'℃','对应能力实测值','6.1 a)','未印（正文第3页）',5],
 ['制冷量换算系数',1.077,'比值','29℃制冷量=35℃对应制冷量×1.077','6.1 a)','未印（正文第3页）',5],
 ['功率换算系数',0.914,'比值','29℃功率=35℃对应功率×0.914','6.1 a)','未印（正文第3页）',5],
];
sh.getRange('A1:G10').values=[['参数','数值','单位','条件/关系（文字，不是计算公式）','条款','印刷页','PDF页'],...constants];
sh.getRange('A1:G10').format.font={name:'Microsoft YaHei',size:10};
sh.getRange('A1:G1').format={fill:'#243F60',font:{color:'#FFFFFF',bold:true},rowHeight:30};
[42,12,12,65,16,26,10].forEach((w,i)=>sh.getRange(`${String.fromCharCode(65+i)}1:${String.fromCharCode(65+i)}10`).format.columnWidth=w);
sh.getRange('A2:G10').format.rowHeight=28;
sh.getRange('B2:B3').setNumberFormat('0');
sh.getRange('B4:B5').setNumberFormat('0.00');
sh.getRange('B6:B8').setNumberFormat('0');
sh.getRange('B9:B10').setNumberFormat('0.000');
wb.recalculate();
await fs.writeFile(path.join(root,'data/table_rows.json'),JSON.stringify(records,null,2)+'\n');
for(const s of wb.worksheets.items){
 const name=s.name;
 const preview=await wb.render({sheetName:name,range:name==='条款数值'?'A1:G10':`A1:N${name.startsWith('表1')?15:17}`,scale:1,format:'png'});
 await fs.writeFile(path.join(root,'_tmp',`${name}.png`),new Uint8Array(await preview.arrayBuffer()));
}
const check=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:50},summary:'公式错误扫描'});
await fs.writeFile(path.join(root,'_tmp/inspect.txt'),check.ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'data/GB37479_2019_TABLE_VALUES.xlsx'));
console.log(JSON.stringify({sheets:3,table_rows:records.length,grade_values:records.length*3,clause_numeric_values:constants.length}));
