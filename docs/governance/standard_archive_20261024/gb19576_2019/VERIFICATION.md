# 结构检查与数值核验记录

执行者：本会话Codex；日期2026-10-13。属于执行者自核，本节记载初建自核；后续独立报告核对39限值一致，见[验收回应](ACCEPTANCE_RESPONSE.md)，不得将自核执行人改为独立审查人。输入PDF SHA为`1c5c97fd39351ed9708fd69f45c9b37dfba8fccea3cc4f810b32de3522876026`。

## 结构检查

以PDF物理3、4页原图核对表结构，物理1页核对封面；物理2页前言文本已读。表1及表1续是1张逻辑表，2个跨页片段；4+9=13条物理分支，3等级。无其它表、无附录、无编号公式。

核查了风冷大类跨4行、单冷/热泵各跨2行、水冷跨2行、机房跨5行、基站与恒温恒湿横跨类型列的合并标签。所有39个等级源格非空。提取产生的标签None不视作0或缺限值。水冷高容量档在原表先于低容量档，工作簿相同。5类机房分支独立，重复容量条件及相同阈值未去重。工作簿13个完整分支组合唯一，143个数据区单元格（A6:K18）非空，保留页码和源行索引。完整字段非空检查是结构检查，不证明143项均独立校对。

结构脚本断言全部通过；未做软件适用性运行测试。结构位置及合并覆盖详见STANDARD_MAPPING §4。

## 数值自核

1. 从指定PDF转录39个阈值，逐行与PDF3–4页图像比较；对应13分支均已目视。数值精度按原文两位保留。限值逐格记录在`evidence/cell_audit.csv`，真实坐标为`表1!G6:I18`。
2. `verify_workbook.py`用pdfplumber的实际表格列（每源行最后3列），NFKC规范化全角数字；只读打开导出XLSX，以G/H/I实际列号检查值、类型、0.00格式及CSV字面一致性。源数据读PDF，不回读生成器当独立期待。仍属于同一原件的工具交叉检查，不是独立业务验收。
3. 39项组合数值检查：pass=39、fail=0、error=0、skip=0、not_run=0。逐项结果在`evidence/verification_results.json`。该数字仅表示39个表1限值检查，不涵盖引用标准。
4. §5.4的95%、110%及§6.1的29℃、35℃、1.077、0.914已对正文图像自核，未额外编造逐格验收计数。
5. Artifact Tool执行recalculate后inspect与导出；工作簿0业务公式，导出后Python确认无公式单元格。完成唯一Sheet全范围A1:K22的PNG预览并目视复查，标题、13行条件、数值和注记可读。未运行Windows Excel原生程序，原生Excel交互测试=NOT_RUN。本资料没有依赖公式重算、宏或外部链接。

本次最终XLSX SHA-256：`7ee299877c7ed5ab70f2b5c732a20df7056de7e6eec7e75eac9070c9d1df377d`。重新导出可能因文件元数据改变SHA，应重跑核验并更新交接，不静默沿用哈希。

## 未核验范围与检查状态

|项目|状态及限制|
|---|---|
|39阈值执行者自核与PDF提取交叉核对|完成；不冒充独立逐格验收|
|独立逐格数值验收|后续第一轮39个等级限值全部一致；限该范围，见ACCEPTANCE_RESPONSE|
|三份注日期引用原文完整公式、工况、权重|NOT_RUN，R02待补证|
|原件与官方全文逐页同一性|NOT_RUN；只做官方元数据核对与原件结构核验|
|日期差异成因/延期公告正文|后续已补正式延期文件索引正文与附件证据；通知原图/下载SHA仍未取得，见R01及ACCEPTANCE_RESPONSE|
|边界软件测试、Golden、生产回归|NOT_RUN；本轮不改软件，候选未批准|
|unittest / compileall / 产品smoke / 性能基线|NOT_RUN；无生产代码变更，不伪报通过|
|Git diff whitespace|执行；新建未跟踪文件不受普通git diff覆盖，另做本目录链接/文本检查|

## 复现

在本目录建立指向Codex bundled `node_modules`的忽略junction，以bundled Node运行`build_workbook.mjs`，再以bundled Python运行`verify_workbook.py`。脚本使用自身路径定位仓库与原文，不把本机盘符固化为跨机器身份。需要`@oai/artifact-tool`、pdfplumber、openpyxl（只读）。原页查看可用Poppler：`pdftoppm -scale-to 1700 -png <指定原PDF> <本目录tmp/page>`。不上传tmp中的整页PNG、提取全文或依赖junction。
