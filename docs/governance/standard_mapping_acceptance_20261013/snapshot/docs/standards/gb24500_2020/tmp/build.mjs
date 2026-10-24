import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=new URL('../',import.meta.url);
const wb=Workbook.create();
const sha='e270072e4d3cdefc9a9969524870a50bd454c5405a729c993b2e2584551cf285';
const coal=[['烟煤Ⅱ类','17700≤Qnet,v,ar≤21000','Vdaf>20'],['烟煤Ⅲ类','Qnet,v,ar>21000','Vdaf>20'],['贫煤','Qnet,v,ar≥17700','10<Vdaf≤20'],['无烟煤Ⅱ类','Qnet,v,ar≥21000','Vdaf<6.5'],['无烟煤Ⅲ类','Qnet,v,ar≥21000','6.5≤Vdaf≤10'],['褐煤','Qnet,v,ar≥11500','Vdaf>37']];
const specs=[];
specs.push({name:'表1 层状燃煤',page:4,printed:'2',headers:['源分支','燃料品种','Qnet条件（kJ/kg）','Vdaf条件（%）','等级','D≤20 t/h或Q≤14 MW（%）','D>20 t/h或Q>14 MW（%）'],rows:coal.flatMap((c,i)=>[[85,82,80,86,83,81],[87,84,82,89,86,84],[85,82,80,86,83,81],[85,82,80,86,83,81],[85,82,80,86,83,81],[85,82,80,87,84,82]][i].slice(0,3).map((v,j)=>[`T1-B${i+1}`,...c,j+1,v,[[86,83,81],[89,86,84],[86,83,81],[86,83,81],[86,83,81],[87,84,82]][i][j]])),values:[5,6]});
const c2=[['烟煤Ⅰ类','14400≤Qnet,v,ar<17700','Vdaf>20'],...coal];
specs.push({name:'表2 流化床燃煤',page:5,printed:'3（页码未显示）',headers:['源分支','燃料品种','Qnet条件（kJ/kg）','Vdaf条件（%）','等级','热效率（%）'],rows:c2.flatMap((c,i)=>[89,90,91,90,89,90,91].slice(i,i+1).flatMap(v=>[v,[85,89,90,88,88,88,89][i],[82,86,88,86,86,86,86][i]].map((x,j)=>[`T2-B${i+1}`,...c,j+1,x]))),values:[5]});
specs.push({name:'表3 生物质',page:5,printed:'3（页码未显示）',headers:['源分支','燃料品种','Qnet条件（kJ/kg）','限定值特例','等级','D≤10 t/h或Q≤7 MW（%）','D>10 t/h或Q>7 MW（%）'],rows:[0,1,2].map(j=>['T3-B1','生物质','按燃料实际化验值','Qnet<8374时限定值用设计效率',j+1,[88,84,80][j],[91,88,86][j]]),values:[5,6]});
specs.push({name:'表4 室燃',page:6,printed:'4（页码未显示）',headers:['源分支','燃料及分支','发热量化验口径','源表位置','等级','热效率（%）'],rows:[['天然气非冷凝','低位','天然气左栏',[96,94,92]],['天然气冷凝','低位','天然气右栏脚注a',[103,101,98]],['天然气冷凝','高位','天然气右栏括号脚注b',[93,91,88]],['燃油','低位','燃油效率横向合并格',[95,93,90]],['煤','低位','煤效率横向合并格',[92,90,88]]].flatMap((r,i)=>r[3].map((v,j)=>[`T4-B${i+1}`,r[0],`按实际化验值；${r[1]}`,r[2],j+1,v])),values:[5]});
const audit=[];
for(const s of specs){
 const sh=wb.worksheets.add(s.name);sh.showGridLines=false;
 sh.getRange('A1').values=[[`GB 24500—2020 ${s.name}`]];
 sh.getRange('A2').values=[[`来源：原PDF物理页${s.page}，正文页${s.printed}；额定工况；全部效率值按百分数数值保存，例如85表示85%。`]];
 sh.getRange('A3').values=[['本表为Stage A原文整理。合并标签向各等级展开；具体规则、特例及未决项见主映射。']];
 sh.getRangeByIndexes(4,0,1,s.headers.length).values=[s.headers];
 sh.getRangeByIndexes(5,0,s.rows.length,s.headers.length).values=s.rows;
 sh.getRangeByIndexes(4,0,s.rows.length+1,s.headers.length).format.font={name:'Arial',size:10};
 sh.getRangeByIndexes(4,0,1,s.headers.length).format={fill:'#253B53',font:{color:'#FFFFFF',bold:true},wrapText:true,rowHeight:42};
 sh.getRangeByIndexes(5,0,s.rows.length,s.headers.length).format.rowHeight=42;
 sh.getRangeByIndexes(5,0,s.rows.length,s.headers.length).format.wrapText=true;
 sh.getRange('A:A').format.columnWidth=14;sh.getRange('B:B').format.columnWidth=23;
 sh.getRange('C:C').format.columnWidth=32;sh.getRange('D:D').format.columnWidth=31;
 sh.getRange('E:E').format.columnWidth=9;sh.getRange('F:G').format.columnWidth=24;
 sh.getRange('A1').format.font={size:14,bold:true};
 sh.getRange('A2:A3').format.font={size:10};
 sh.freezePanes.freezeRows(5);
 for(let r=0;r<s.rows.length;r++)for(const c of s.values)audit.push({sheet:s.name,cell:String.fromCharCode(65+c)+(r+6),branch:s.rows[r][0],grade:s.rows[r][4],value:s.rows[r][c],pdf_page:s.page,column:c});
}
const special=wb.worksheets.add('限定值与来源');special.showGridLines=false;
const notes=[['项目','标准事实/定位'],['修订','V0.1；2026-10-13；执行者整理，未独立验收、未冻结'],['原文相对仓库路径','标准原文/11. GB+24500-2020 工业锅炉能效限定值及能效等级.pdf'],['原文SHA256',sha],['5.2 电加热锅炉最低热效率（%）',97],['5.1 水介质/余热回收有机热载体','额定工况下不低于表1～4三级'],['5.1 仅有机热载体换热','不低于设计值；与等级组合输出需确认'],['表3后段 低热值生物质','Qnet,v,ar<8374 kJ/kg：限定值不低于设计热效率，其他等级按表3'],['表4脚注a','燃气冷凝锅炉额定工况各等级效率'],['表4脚注b','括号内为收到基高位发热量计算的效率；不是另一个能效等级'],['第4章前提','满足工业锅炉初始排放浓度要求；本标准未给排放限值'],['第6章试验','GB/T 10180；燃气冷凝锅炉可按NB/T 47066'],['数值复核','4表78个热效率数值均与PDF坐标提取及原页视觉检查核对；详见evidence/cell_verification.csv'],['限定值数值复核','5.2的97%与PDF6原图/文本核对；阈值/范围条件见证据文档'],['未覆盖','独立验收；引用试验标准全文；最终软件解释；实际Excel桌面打开验证'],['权威','本工作簿不是计算引擎；与STANDARD_MAPPING.md配套，原PDF最高'],['官方题录','https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=B31C8D212ACEEC023E752DF6260B63B7']];
special.getRange('A1').write(notes);special.getRange('A:A').format.columnWidth=37;special.getRange('B:B').format.columnWidth=108;
special.getRange('A1:B17').format={font:{name:'Arial',size:10},wrapText:true,rowHeight:40};special.getRange('A1:B1').format={fill:'#253B53',font:{color:'#FFFFFF',bold:true}};
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:"'表4 室燃'!A5:F20",include:'values,formulas',tableMaxRows:16,tableMaxCols:6,maxChars:2000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20}})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save(fileURLToPath(new URL('data/GB24500_2020_TABLE_VALUES.xlsx',root)));
await fs.writeFile(new URL('tmp/expected_cells.json',root),JSON.stringify(audit,null,2));
for(const name of [...specs.map(s=>s.name),'限定值与来源']){
 const render=await wb.render({sheetName:name,range:name==='限定值与来源'?'A1:B17':`A1:${name.startsWith('表1')||name.startsWith('表3')?'G':'F'}${name.startsWith('表3')?8:Math.min(26,5+specs.find(s=>s.name===name).rows.length)}`,scale:1.5});
 await fs.writeFile(new URL(`tmp/preview-${name.slice(0,2)}.png`,root),new Uint8Array(await render.arrayBuffer()));
}
