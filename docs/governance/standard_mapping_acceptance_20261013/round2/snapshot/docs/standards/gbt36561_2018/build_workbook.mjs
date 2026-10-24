import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(fileURLToPath(import.meta.url));
const rows=JSON.parse(await fs.readFile(path.join(root,'data/table_values.json'),'utf8'));
const wb=Workbook.create();
const manifest=[];
const readme=wb.worksheets.add('说明');
readme.showGridLines=false;
const info=[['GB/T 36561—2018 表值审校册',''],['属性','Stage A 草稿；不用于软件正式评价'],['来源','用户指定原PDF；印刷页1～23对应PDF物理页4～26'],['来源SHA-256','f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37'],['表格范围','正文表1～17；资料性附录表A.1～A.12'],['数据记录',rows.length],['数值记录',rows.filter(x=>typeof x.value==='number').length],['数值与精度','数值单元格为数字。%列存百分数的点数，例如2代表2%，不是0.02。'],['特殊源格','—为原文横线；δ为符号变量；空白条件注明，不解释为零。'],['重复与合并','保持原物理分支；表16激光跨8/9的2分仅录一次。'],['核验边界','已逐页图像转录；另行抽样自核见evidence/numeric_review.csv。无独立逐格验收。'],['问题','R01～R10见ISSUE_REGISTRATION_REQUEST.md，待总协调登记。'],['使用方式','按表号、分支、指标、条件共同定位；F列为表值，J/K为页码。'],['配套规则','STANDARD_MAPPING.md；本册没有业务计算公式。']];
readme.getRange('A1').write(info);
readme.getRange('A1:B14').format.font={name:'Microsoft YaHei',size:11};
readme.getRange('A1:B14').format.wrapText=true;
readme.getRange('A1:A14').format.columnWidth=28;
readme.getRange('B1:B14').format.columnWidth=90;
readme.getRange('A1:B14').format.rowHeight=40;
readme.getRange('A1:B1').format.font={name:'Microsoft YaHei',size:15,bold:true};
for(const [name,sel] of [['正文表值',rows.filter(x=>!x.table.startsWith('A'))],['附录系数',rows.filter(x=>x.table.startsWith('A'))]]){
 const sh=wb.worksheets.add(name);sh.showGridLines=false;
 const headers=['记录ID','表号','物理分支/原序号','指标/原列','比较符','表值','单位','适用条件与源格说明','源格定位','印刷页','PDF物理页'];
 sh.getRange('A1').write([headers,...sel.map(r=>[r.record_id,r.table,r.branch,r.metric,r.operator,r.value,r.unit,r.condition,r.source_cell,r.printed_page,r.pdf_page])]);
 const last=sel.length+1;
 sh.getRange(`A1:K${last}`).format.font={name:'Microsoft YaHei',size:10};
 sh.getRange(`A1:K${last}`).format.verticalAlignment='center';
 sh.getRange(`A1:K${last}`).format.wrapText=true;
 const widths=[35,8,47,31,12,13,13,72,60,10,12];
 widths.forEach((w,i)=>sh.getRangeByIndexes(0,i,last,1).format.columnWidth=w);
 sh.getRange('A1:K1').format={fill:'#25445C',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},rowHeight:32,wrapText:true};
 sh.getRange(`F2:F${last}`).setNumberFormat('0');
 for(let i=0;i<sel.length;i++){
  const r=sel[i], row=i+2;
  sh.getRange(`A${row}:K${row}`).format.rowHeight=Math.max(42,Math.ceil(r.condition.length/35)*16+8,Math.ceil(r.branch.length/23)*16+8,Math.ceil(r.source_cell.length/30)*16+8);
  if(i===0||sel[i-1].table!==r.table) sh.getRange(`A${row}:K${row}`).format.borders={top:{style:'thin',color:'#7892A4'}};
  if(typeof r.value==='number'){
   const precision=(r.source_numeric_text.split('.')[1]||'').length;
   sh.getRange(`F${row}`).setNumberFormat(precision?'0.'+'0'.repeat(precision):'0');
  }
  manifest.push({...r,sheet:name,value_cell:`F${row}`,row_range:`A${row}:K${row}`});
 }
 sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(3);
}
wb.recalculate();
await fs.writeFile(path.join(root,'evidence/workbook_coordinates.json'),JSON.stringify(manifest,null,2)+'\n');
await fs.writeFile(path.join(root,'tmp/inspect.ndjson'),(await wb.inspect({kind:'table',range:'正文表值!A1:K6',include:'values,formulas',tableMaxRows:6,tableMaxCols:11})).ndjson);
await fs.writeFile(path.join(root,'tmp/error_scan.ndjson'),(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:30}})).ndjson);
for(const [name,range] of [['说明','A1:B14'],['正文表值','B1:H9'],['附录系数','B1:H13']]){
 const blob=await wb.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(path.join(root,`tmp/workbook_${name}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'data/GBT36561_2018_TABLE_VALUES.xlsx'));
console.log(JSON.stringify({sheets:3,records:rows.length,formulas:0,export:'data/GBT36561_2018_TABLE_VALUES.xlsx'}));
