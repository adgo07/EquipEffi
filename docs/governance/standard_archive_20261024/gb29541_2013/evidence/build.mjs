import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const base = new URL('../', import.meta.url);
await fs.mkdir(new URL('tmp/', base), { recursive: true });
const wb = Workbook.create();
const s = wb.worksheets.add('表1_能效限值');
const rows = [
 ['T1-R01','H<10','普通型','一次加热、循环加热式','不分供泵',4.60,4.40,4.10,3.90,3.70,'表1 数据行1'],
 ['T1-R02','H<10','普通型','静态加热式','不分供泵',4.20,4.00,3.80,3.60,3.40,'表1 数据行2'],
 ['T1-R03','H<10','低温型','一次加热、循环加热式','不分供泵',3.80,3.60,3.40,3.20,3.00,'表1 数据行3'],
 ['T1-R04','H≥10','普通型','一次加热','不分供泵',4.60,4.40,4.10,3.90,3.70,'表1 数据行4'],
 ['T1-R05','H≥10','普通型','循环加热','不提供水泵',4.60,4.40,4.10,3.90,3.70,'表1 数据行5'],
 ['T1-R06','H≥10','普通型','循环加热','提供水泵',4.50,4.30,4.00,3.80,3.60,'表1 数据行6'],
 ['T1-R07','H≥10','低温型','一次加热','不分供泵',3.90,3.70,3.50,3.30,3.10,'表1 数据行7'],
 ['T1-R08','H≥10','低温型','循环加热','不提供水泵',3.90,3.70,3.50,3.30,3.10,'表1 数据行8'],
 ['T1-R09','H≥10','低温型','循环加热','提供水泵',3.80,3.60,3.40,3.20,3.00,'表1 数据行9'],
];
s.getRange('A2').values=[['GB 29541—2013 表1 能源效率等级指标']];
s.getRange('A3').values=[['制热量 H：kW；COP：W/W。原文：PDF物理4／印刷2。全部45个限值保留两位小数。']];
s.getRange('A5:K5').values=[['源行ID','制热量 (kW)','型式','加热方式','水泵分支','1级 (W/W)','2级 (W/W)','3级 (W/W)','4级 (W/W)','5级 (W/W)','原文源行']];
s.getRange('A6:K14').values=rows;
s.getRange('F6:J14').setNumberFormat('0.00');
s.getRange('A17').values=[['说明：源表合并条件已逐行展开；“不分供泵”仅指该行未按供泵分列，不代表免计水泵能耗。']];
s.getRange('A18').values=[['4.2：H>10 kW静态加热参照小容量静态指标；H=10及低温静态的解释缺口见主映射和登记请求。']];
s.getRange('A19').values=[['本工作簿是Stage A表值资料，无评价公式；未独立验收、未冻结，不作软件正式支持声明。']];
s.getRange('A20').values=[['原PDF：标准原文/14. GB 29541 2013 热泵热水机（器）能效限定值及能效等级.pdf']];
s.getRange('A21').values=[['SHA256：94d5f6cc5502e76da01fc030a00d2acd54f40dd83cb967886149fb6b158e15df']];
const c = wb.worksheets.add('条款数值与条件');
c.getRange('A2').values=[['GB 29541—2013 条款数值与条件']];
c.getRange('A3').values=[['来源：同一PDF；条款1—4.1位于物理3／印刷1；4.2—7位于物理4／印刷2；第8章位于物理5／无印刷页码。']];
c.getRange('A5:F5').values=[['条款','项目','数值','单位','条件或比较关系','说明']];
const clauses=[
 ['表1','制热量分界',10,'kW','H<10 与 H≥10','不插值；静态加热见4.2及问题请求001/002'],
 ['4.1','能效等级数',5,'级','1级最高','按实测COP和对应分支判级'],
 ['4.2','静态加热参照边界',10,'kW','H>10','参照小容量静态行，等于10的路由未明确'],
 ['4.3','实测COP/能效标注值最低比率',0.95,'比例','实测COP≥标注COP×0.95','标注COP仍须位于其额定等级的COP范围'],
 ['4.3','实测制热量/标注值最低比率',0.95,'比例','实测制热量≥标注制热量×0.95','额定与实测制热量均须落在对应额定制热量范围'],
 ['4.3','实测制热消耗功率/标注值最高比率',1.10,'比例','实测功率≤标注功率×1.10','独立核查；不得把偏差作为COP等级容差'],
 ['5','能效限定值等级',5,'级','实测COP≥对应5级值','与4.3标注一致性分别检查'],
 ['6','节能评价值等级',2,'级','节能评价值为对应2级值','结合3.2的最小值定义使用'],
 ['7','性能系数实测值小数位',2,'位','保留两位小数','本PDF未指定修约方法'],
 ['8.2','首次抽取样品数',1,'台','测试性能系数','能效限定值为出厂检验抽检项目'],
 ['8.2','首次不满足后再抽样品数',2,'台','再抽两台实测值均应满足规定要求','否则判该批不合格；不是平均值判定'],
 ['7 a','提供水泵产品','不适用','能耗边界','耗电量计入水泵能耗','原文无水泵折减系数或扣除公式'],
 ['7 b','带标配水箱产品','不适用','测试方法','GB/T 23137—2008；计入水泵能耗','不可按H分界替代本条测试方法路由'],
 ['7 c','不带标配水箱产品','不适用','测试方法','GB/T 21362—2008','引用标准原文尚未核验'],
 ['7 d','热水储存性能','不适用','要求','满足相应标准要求','未擅自给出温度或储热限值'],
];
c.getRange('A6:F20').values=clauses;
c.getRange('C9:C11').setNumberFormat('0%');
for(const sheet of [s,c]){
 sheet.showGridLines=false;
 sheet.getUsedRange().format.font={name:'Microsoft YaHei',size:11,color:'#172536'};
 sheet.getUsedRange().format.rowHeight=28;
 sheet.getUsedRange().format.verticalAlignment='center';
 sheet.getRange('A2').format.font={name:'Microsoft YaHei',size:15,bold:true};
 sheet.getRange(sheet===s?'A5:K5':'A5:F5').format={fill:'#29465B',font:{name:'Microsoft YaHei',size:11,bold:true,color:'#FFFFFF'},rowHeight:34};
 sheet.freezePanes.freezeRows(5);
}
for (const [col,width] of Object.entries({A:15,B:17,C:12,D:29,E:19,F:14,G:14,H:14,I:14,J:14,K:20}))s.getRange(`${col}5:${col}14`).format.columnWidth=width;
for (const [col,width] of Object.entries({A:10,B:43,C:13,D:15,E:62,F:64}))c.getRange(`${col}5:${col}20`).format.columnWidth=width;
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'表1_能效限值!A5:K14',include:'values,formulas',tableMaxRows:10,tableMaxCols:11,maxChars:6000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:20}})).ndjson);
for(const [sheet,range,file] of [[s,'A1:K21','table1_preview.png'],[c,'A1:F20','clauses_preview.png']]){
 const preview=await wb.render({sheetName:sheet.name,range,scale:1,format:'png'});
 await fs.writeFile(new URL(`tmp/${file}`,base),new Uint8Array(await preview.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(fileURLToPath(new URL('data/GB29541_2013_标准表值.xlsx',base)));
await fs.writeFile(new URL('tmp/transcribed_rows.json',base),JSON.stringify(rows,null,2));
console.log('EXPORTED');
