import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const dir=path.dirname(fileURLToPath(import.meta.url));
// Transcribed from PDF physical pages 3–4, visually checked against the source.
const raw=[
['风冷式单元式空调机','单冷型','7000≤CC≤14000','SEER','Wh/Wh','4.50','3.80','2.90',3,1],
['风冷式单元式空调机','单冷型','CC>14000','SEER','Wh/Wh','3.60','3.00','2.70',3,1],
['风冷式单元式空调机','热泵型','7000≤CC≤14000','APF','Wh/Wh','3.50','3.10','2.70',3,1],
['风冷式单元式空调机','热泵型','CC>14000','APF','Wh/Wh','3.40','3.00','2.60',3,1],
['水冷式单元式空调机','原表未细分冷热型','CC>14000','IPLV','W/W','4.50','4.30','3.70',4,2],
['水冷式单元式空调机','原表未细分冷热型','7000≤CC≤14000','IPLV','W/W','4.00','3.70','3.30',4,2],
['计算机和数据处理机房用','风冷式','原表未列容量分档','AEER','W/W','4.00','3.60','3.00',4,2],
['计算机和数据处理机房用','水冷式','原表未列容量分档','AEER','W/W','4.20','4.00','3.50',4,2],
['计算机和数据处理机房用','乙二醇经济冷却式','原表未列容量分档','AEER','W/W','3.90','3.70','3.20',4,2],
['计算机和数据处理机房用','风冷双冷源式','原表未列容量分档','AEER','W/W','3.60','3.40','2.90',4,2],
['计算机和数据处理机房用','水冷双冷源式','原表未列容量分档','AEER','W/W','4.10','3.90','3.40',4,2],
['通讯基站用单元式空气调节机','原表未细分','原表未列容量分档','COP','W/W','3.20','3.00','2.80',4,2],
['恒温恒湿型单元式空气调节机','原表未细分','原表未列容量分档','AEER','W/W','4.00','3.70','3.00',4,2]];
const wb=Workbook.create(); const s=wb.worksheets.add('表1'); s.showGridLines=false;
s.getRange('A2').values=[['GB 19576—2019 表1能效等级指标值']];
s.getRange('A3').values=[['来源：本地原PDF，SHA及身份见 SOURCE_EVIDENCE.md；自核，未经独立逐格验收。CC单位W。']];
const headers=['源行','设备类型','物理分支','名义制冷量CC（W）','指标','单位','1级','2级','3级','PDF物理页','印刷页'];
s.getRange('A5:K5').values=[headers];
const rows=raw.map((r,i)=>[i+1,...r.slice(0,5),...r.slice(5,8).map(Number),...r.slice(8)]);
s.getRange('A6:K18').values=rows;
s.getRange('A2:K22').format.font={name:'Arial',size:11};
s.getRange('A2').format.font={name:'Arial',size:15,bold:true};
s.getRange('A5:K5').format={fill:'#263D52',font:{color:'#FFFFFF',bold:true},rowHeight:30};
s.getRange('A6:K18').format.rowHeight=32;
for(const [col,width] of Object.entries({A:8,B:38,C:27,D:29,E:10,F:12,G:10,H:10,I:10,J:14,K:10}))s.getRange(`${col}5:${col}18`).format.columnWidth=width;
s.getRange('G6:I18').setNumberFormat('0.00'); s.freezePanes.freezeRows(5);
s.getRange('A20').values=[['表1跨页为同一张表；第5、6源行保持水冷式原始倒序。所有39个等级数值源格均非空。']];
s.getRange('A21').values=[['合并类别展开为逐行条件；合并范围见STANDARD_MAPPING；字面小数及坐标见evidence/cell_audit.csv。']];
s.getRange('A22').values=[['仅标准表值资料，不含评价算法；95%与110%是第5.4条允差，不能用于降低表1限值。']];
wb.recalculate();
await fs.mkdir(path.join(dir,'data'),{recursive:true}); await fs.mkdir(path.join(dir,'evidence'),{recursive:true});
await fs.writeFile(path.join(dir,'tmp/workbook_inspect.json'),(await wb.inspect({kind:'table',range:'表1!A5:K18',include:'values,formulas',tableMaxRows:14,tableMaxCols:11})).ndjson);
await fs.writeFile(path.join(dir,'tmp/workbook.png'),new Uint8Array(await (await wb.render({sheetName:'表1',range:'A1:K22',scale:1.5})).arrayBuffer()));
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(dir,'data/GB19576_2019_TABLE1.xlsx'));
let audit='source_row,pdf_page,printed_page,source_table,source_column,xlsx_cell,source_lexical,branch,verification\n';
raw.forEach((r,i)=>r.slice(5,8).forEach((v,j)=>{audit+=`${i+1},${r[8]},${r[9]},表1,${j+1}级,表1!${'GHI'[j]}${i+6},${v},${r.slice(0,3).join(' / ')},执行者原页图像自核\n`;}));
await fs.writeFile(path.join(dir,'evidence/cell_audit.csv'),audit,'utf8');
console.log('Exported 13 branch rows and 39 grade values.');
