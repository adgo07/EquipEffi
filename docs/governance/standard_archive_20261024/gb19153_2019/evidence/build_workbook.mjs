import fs from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
// Point tmp/node_modules at the bundled runtime modules, never at repo-local dependencies.
const require=createRequire(new URL('../tmp/module-loader.cjs',import.meta.url));
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const root = new URL('../', import.meta.url);
const data=JSON.parse(await fs.readFile(new URL('tmp/table_data.json',root),'utf8'));
const wb=Workbook.create();
const names=['一般用喷油回转','一般用变转速喷油回转','一般用往复活塞（风冷）','全无油润滑往复活塞','有油直联便携往复活塞','无油直联便携往复活塞'];
for(let n=1;n<=6;n++){
  const s=wb.worksheets.add(`表${n}`);s.showGridLines=false;
  s.getRange('A2').values=[[`GB 19153—2019 表${n} ${names[n-1]}`]];
  s.getRange('A3').values=[['原文整理稿；非业务计算器；“—”保留为无表列数值，不能当0。条件解释见配套主映射。']];
  s.getRange('A4').values=[['来源：Owner提供PDF；源SHA与页码说明见表7权重与说明；逐行原页/源格在I:N。']];
  const head=['额定功率 kW','实际输入功率条件 kW','等级','表压 MPa','冷却/数值分支','源格性质','比功率限值','单位','PDF物理页','印刷页','源表行','源表列','源格边界 pt','源格原文字面'];
  s.getRange('A5:N5').values=[head];
  const rows=data.records.filter(r=>r.table===n).map(r=>[r.power_kw,r.actual_input_range_kw,r.grade,r.pressure_gauge_mpa,r.cooling,r.source_kind,r.value===null?'—':r.value,'kW/(m³/min)',r.pdf_page,r.printed_page,r.source_row,r.source_col,r.bbox,r.source_text]);
  s.getRange(`A6:N${rows.length+5}`).values=rows;
  s.getRange(`A2:N${rows.length+5}`).format.font.name='Arial';
  s.getRange(`A2:N${rows.length+5}`).format.font.size=10;
  s.getRange('A2').format.font.size=14;s.getRange('A2').format.font.bold=true;
  s.getRange('A5:N5').format.fill='#244660';s.getRange('A5:N5').format.font.color='#FFFFFF';
  s.getRange('A5:N5').format.font.bold=true;s.getRange('A5:N5').format.wrapText=true;s.getRange('A5:N5').format.rowHeight=34;
  s.getRange(`A6:N${rows.length+5}`).format.rowHeight=21;
  s.getRange(`A5:N${rows.length+5}`).format.verticalAlignment='center';
  for(const [col,w] of [['A',14],['B',23],['C',7],['D',12],['E',22],['F',20],['G',15],['H',18],['I',13],['J',10],['K',11],['L',11],['M',38],['N',24]])s.getRange(`${col}5:${col}${rows.length+5}`).format.columnWidth=w;
  s.getRange(`A6:A${rows.length+5}`).setNumberFormat('0.##');
  s.getRange(`D6:D${rows.length+5}`).setNumberFormat('0.00');
  s.getRange(`G6:G${rows.length+5}`).setNumberFormat('0.0');
  s.getRange(`B6:B${rows.length+5}`).format.horizontalAlignment='center';
  s.getRange(`E6:F${rows.length+5}`).format.horizontalAlignment='center';
  s.getRange(`H6:H${rows.length+5}`).format.horizontalAlignment='center';
  s.freezePanes.freezeRows(5);
  s.tables.add(`A5:N${rows.length+5}`,true,`StandardTable${n}`);
}
const s=wb.worksheets.add('表7权重与说明');s.showGridLines=false;
s.getRange('A2').values=[['GB 19153—2019 表7权重与来源说明']];
s.getRange('A4:D4').values=[['满负荷容积流量比例','权重','PDF物理页','印刷页']];
s.getRange('A5:D7').values=data.weights.map(r=>[...r,17,15]);s.getRange('A5:B7').setNumberFormat('0%');
s.getRange('B5:B7').format.horizontalAlignment='left';
const notes=[['数据边界','表1～6全部数值及破折号组合；表4方括号液冷单独保存；表7全部权重。'],['来源相对路径','标准原文/5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf'],['PDF SHA-256',data.pdf_sha256],['版本及日期','整理稿A.1，2026-10-13；执行者Codex。尚未独立验收/冻结。'],['阈值单位','kW/(m³/min)；压力为额定排气表压MPa；功率栏含义按各表原文。'],['实际输入条件','仅表5/6，保留左开右闭区间；额定功率和实际输入功率不得互换。'],['源格定位','源表行/列含表头，从1起；合并格记左上源格；bbox为PDF左上原点pt坐标。'],['合并覆盖','同一bbox出现多次表示原文同一合并格覆盖多个组合，不是新增或补齐限值。'],['破折号','原文“—”不转成0，不跨行填数，不从邻近功率/压力推断。'],['表4分支','非括号值照录；方括号明确为液冷。未列液冷值的组合不自行继承。'],['附加条件','§4.3功率条件、§6试验要求见主映射；仅满足比功率阈值不足以证明全部符合。'],['核验','2502个限值和417个破折号组合完成两引擎源格核对；不等于独立人工逐格验收。'],['待确认','R01非表列/冷却；R02大一挡；R03变转速PC工况；R04偏差±5%口径。'],['正式状态权威','仓库根STANDARD_ISSUES_REGISTER、V1_SCOPE/ROADMAP；本工作簿不提升支持状态。']];
s.getRange(`A10:B${9+notes.length}`).values=notes;
s.getRange(`A2:D${9+notes.length}`).format.font.name='Arial';s.getRange(`A2:D${9+notes.length}`).format.font.size=10;
s.getRange('A2').format.font.size=14;s.getRange('A2').format.font.bold=true;
s.getRange('A4:D4').format.fill='#244660';s.getRange('A4:D4').format.font.color='#FFFFFF';
s.getRange(`A4:A${9+notes.length}`).format.columnWidth=28;s.getRange(`B4:B${9+notes.length}`).format.columnWidth=105;
s.getRange('C4:D7').format.columnWidth=15;s.getRange('A4:D7').format.rowHeight=24;
s.getRange(`A10:B${9+notes.length}`).format.wrapText=true;s.getRange(`A10:B${9+notes.length}`).format.rowHeight=34;
wb.recalculate();
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},summary:'error scan'})).ndjson);
console.log((await wb.inspect({kind:'table',range:'表4!A6:H10',include:'values,formulas',tableMaxRows:5,tableMaxCols:8})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save(fileURLToPath(new URL('data/GB19153_2019_标准表值.xlsx',root)));
for(const name of [...Array.from({length:6},(_,i)=>`表${i+1}`),'表7权重与说明']){
 const blob=await wb.render({sheetName:name,range:name==='表7权重与说明'?'A4:D7':'A5:H14',scale:1.4,format:'png'});
 await fs.writeFile(new URL(`tmp/preview_${name}.png`,root),new Uint8Array(await blob.arrayBuffer()));
}
console.log('exported and rendered 7 sheets');
