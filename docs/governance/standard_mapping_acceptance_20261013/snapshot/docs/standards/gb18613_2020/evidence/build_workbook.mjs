import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const dir=path.join(path.dirname(fileURLToPath(import.meta.url)),'../_work');
const data=JSON.parse(await fs.readFile(path.join(dir,'tables.json'),'utf8'));
const wb=Workbook.create();
const col=n=>String.fromCharCode(65+n);
for(const t of data.tables){
  const s=wb.worksheets.add(`表${t.id}`), n=t.labels.length+1, last=col(n+1), end=t.rows.length+5;
  s.showGridLines=false;
  s.getRange(`A1:${last}${end}`).format.font={name:'Microsoft YaHei',size:10,color:'#18232D'};
  s.getRange(`A1:${last}${end}`).format.rowHeight=22;
  s.getRange(`A1:${last}${end}`).format.verticalAlignment='center';
  s.getRange(`A1:${last}${end}`).format.columnWidth=10;
  s.getRange(`A1:A${end}`).format.columnWidth=15;
  s.getRange('A2').values=[[`表${t.id}  ${t.title}`]];
  s.getRange('A2').format.font={name:'Microsoft YaHei',size:14,bold:true};
  s.getRange('A3').values=[[`GB 18613—2020；效率单位 %（数值85.9表示85.9%）；Stage A原文校对资料`]];
  s.getRange('A4').values=[[`来源：用户PDF物理页 ${[...new Set(t.sources.map(x=>x[0]))].join('、')}；源文件SHA与空白/横杠说明见“使用说明”`]];
  const headers=[`额定功率\n${t.unit}`,...t.labels.map(x=>x.replace('/','\n')),'PDF物理页','页内数据行'];
  s.getRange(`A5:${last}5`).values=[headers];
  s.getRange(`A5:${last}5`).format={fill:'#243E57',font:{name:'Microsoft YaHei',color:'#FFFFFF',bold:true,size:10},wrapText:true,rowHeight:42,horizontalAlignment:'center',verticalAlignment:'center'};
  const rows=t.rows.map((r,i)=>[...r.map(v=>v===''?null:/^\d+(\.\d+)?$/.test(v)?Number(v):v),t.sources[i][0],t.sources[i][2]]);
  s.getRange(`A6:${last}${end}`).values=rows;
  s.getRange(`B6:${col(n-1)}${end}`).setNumberFormat('0.0');
  s.getRange(`B6:${col(n-1)}${end}`).format.horizontalAlignment='right';
  if(t.id===6) s.getRange(`K1:M${end}`).format.columnWidth=14;
  for(let i=0;i<rows.length;i++){
    const r=i+6;
    s.getRange(`A${r}`).setNumberFormat(t.rows[i][0].includes('.')?'0.'+'0'.repeat(t.rows[i][0].split('.')[1].length):'0');
    if(i%2===1) s.getRange(`A${r}:${last}${r}`).format.fill='#F1F5F8';
    for(let j=1;j<t.rows[i].length;j++) if(t.rows[i][j]==='—') s.getRange(`${col(j)}${r}`).format.horizontalAlignment='center';
  }
  if(t.id===3){s.getRange('C14').format.fill='#FFF0BF';}
  if(t.id===6){s.getRange('P15').format.fill='#FFF0BF';}
  s.freezePanes.freezeRows(5);
}
const read=wb.worksheets.add('使用说明'); read.showGridLines=false;
const notes=[
 ['内容','说明'],
 ['用途','GB 18613—2020 六表原文校对；与STANDARD_MAPPING.md配套。非正式评价引擎。'],
 ['版本','整理修订A.1，2026-10-13；未经独立验收，未冻结。'],
 ['来源相对路径',data.source_relative_path],
 ['来源SHA256',data.source_sha256],
 ['单位','表1额定功率为kW，表2～6为W；效率全部用百分数点值，例如85.9表示85.9%。'],
 ['原格与精度','效率保留1位小数；表1额定功率保留源精度；315～1000保留区间，不拆成单点。'],
 ['横杠','“—”逐格保留，表示原文未给出数值；不是0，不自动补值或外推。'],
 ['空白','表3!C14为空白，原文2200 W/1级/4极，独立源格；R01待确认，禁止填充。'],
 ['差异值','表6!P15=72.0，75 W/>1300 r/min/3级；保留原文，R04未确认，不改成72.8。'],
 ['表6转速','表头保留原区间；500、700、1000的端点解释见R02，不在本表擅自约定。'],
 ['表6注','驱动电路与电机无法分离时，按整体考核效率（印刷6页／PDF8）。'],
 ['试验口径','额定输出功率下实测效率；三相按GB/T 1032 B法，其他按GB/T 5171.21直接法。'],
 ['风扇电机转速','表5、6对应的额定转速取铭牌标称最高转速（第6章）。'],
 ['第4章容差','引用GB/T 755—2019表21、GB/T 5171.1—2014表18及产品标准；R03证据待补。'],
 ['条件与范围','具体电压、频率、功率、结构和分类条件见配套STANDARD_MAPPING.md；不能仅按功率选表。'],
 ['定位','每表第5行为展开后的完整列头，第6行开始数据；最后两列为PDF页与该页内数据行。'],
 ['完整覆盖','6表、8表段、108功率行；1182阈值格=1149数字+32横杠+1空白。'],
 ['结构核验','PDF网格定位与原页图像自核；数据体无合并源格；表头多层合并已展开。'],
 ['数值核验','pdfplumber逐源格提取，pypdf按原行顺序交叉比对，导出XLSX逐坐标回读；见evidence。'],
 ['核验边界','两种解析器来自同一PDF；执行者原页复看不等于独立验收；外部容差资料未核。'],
 ['问题权威','R01～R04为登记请求定位符；正式编号/状态仅以仓库根STANDARD_ISSUES_REGISTER.md为准。'],
 ['来源元数据','官方平台核对发布2020-05-29、实施2021-06-01及现行状态；原文表值取用户PDF。'],
 ['官方入口','https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=42E6A7FD8C7E4BD896221D92ABA1709B'],
 ['表1条件','1000 V以下、50 Hz三相；120 W～1000 kW；2/4/6/8极；单速封闭自扇冷、N设计、连续工作制；一般用途或一般用途防爆。'],
 ['表2条件','690 V及以下、50 Hz交流；一般用途电容起动异步；120～3700 W；2/4/6极；横杠组合无数值。'],
 ['表3条件','690 V及以下、50 Hz交流；一般用途电容运转异步；120～2200 W；2/4/6极；2200 W四极空白需确认。'],
 ['表4条件','690 V及以下、50 Hz交流；一般用途双值电容异步；250～3700 W；2/4极；250 W二极为横杠。'],
 ['表5条件','空调器风扇用电容运转；10～1100 W；4/6/8极；1100 W八极为横杠；铭牌最高转速试验。'],
 ['表6条件','空调器风扇用无刷直流；10～1100 W；按铭牌最高转速选择五个区间；不可分离驱动电路时整体效率。'],
];
read.getRange(`A1:B${notes.length}`).values=notes;
read.getRange(`A1:B${notes.length}`).format={font:{name:'Microsoft YaHei',size:10},rowHeight:36,wrapText:true,verticalAlignment:'center'};
read.getRange(`A1:A${notes.length}`).format.columnWidth=23;
read.getRange(`B1:B${notes.length}`).format.columnWidth=103;
read.getRange('A1:B1').format={fill:'#243E57',font:{name:'Microsoft YaHei',color:'#FFFFFF',bold:true},rowHeight:27};
read.freezePanes.freezeRows(1);
wb.recalculate();
const inspect=await wb.inspect({kind:'region',sheetId:'表3',range:'A12:L14',maxChars:2600,tableMaxCols:12,tableMaxRows:4});
await fs.writeFile(path.join(dir,'inspect.json'),inspect.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},summary:'formula error scan'});
await fs.writeFile(path.join(dir,'errors.json'),errors.ndjson);
for(const t of data.tables){
 const img=await wb.render({sheetName:`表${t.id}`,range:`A1:${col(t.labels.length+2)}${t.rows.length+5}`,scale:1,format:'png'});
 await fs.writeFile(path.join(dir,`workbook-table-${t.id}.png`),new Uint8Array(await img.arrayBuffer()));
}
const img=await wb.render({sheetName:'使用说明',range:`A1:B${notes.length}`,scale:1,format:'png'});
await fs.writeFile(path.join(dir,'workbook-readme.png'),new Uint8Array(await img.arrayBuffer()));
const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(dir,'../data/GB18613_2020_表1-6校对数据_A1.xlsx'));
console.log('exported 7 sheets');
