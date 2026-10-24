# 来源定位与核验记录

## 平台预检查

- 本仓实际根：`G:/Python Project/EquipEffi`（仅本次执行环境）；origin核验为`https://github.com/adgo07/EquipEffi.git`。
- 开始HEAD：`d9f711068bde583138a7f3dded6f64dcaa339761`，共享分支`codex/six-standard-mappings`；其他会话改动保留。`git fetch origin`首次因`.git/FETCH_HEAD`权限失败，经工具权限提升后成功。默认远端`origin/master`为`2c7807f32ef08d18554014328efd4ceaa356726f`；本地master比origin/master落后46提交。未切分支、重置或修改本地master。
- locked central SHA：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`，锁不变。
- 中央本地clone实际origin已核对。`git ls-remote origin HEAD`得到`854b544563260f9e79c73e714c85f6589e0f19b3`；以该已合并SHA读取GUIDE_INDEX、STANDARD_DEVELOPMENT_GUIDE_V0.1及PRODUCT_DELIVERY_POLICY_V1，而非较旧的本地HEAD。
- 本任务不涉及中央公共 Contract。Stage A只转录标准事实，不声明Numeric Profile或修改运行时数值规则，故无本任务适用Frozen条文需要进一步展开。若后续涉及数值设计，须另按locked SHA读取相应Frozen文件。
- 本次适用MUST：Stage A先整理可追溯Mapping；问题先登记；原文事实/判断/决定分开。MUST NOT：静默纠正标准、开发Calculator、工作簿建第二套算法、自动升级锁/Golden/scope/support。冲突分类N/A，不需修改中央Contract。
- 根台账开始读取时未找到GB37479条目；发现请求A/B/C由总协调登记，未自行分配稳定ID或状态，无既有软件解释变更。

## 原文及官方元数据

|项目|记录|
|---|---|
|用户指定相对文件|`标准原文/15. GB_37479-2019 风管送风式空调机组能效限定值及能效等级.pdf`|
|原PDF SHA256|`cf4bef6fca2b88c5ed1a78006c0a6c411fa74330241e9b373c76d8684a338fde`|
|取得方式|用户提供本地只读文件；原始下载渠道/取得日期未提供|
|页数|5；封面、前言I、正文印刷1、正文印刷2、末页（无印刷页码，顺序正文第3页）|
|封面事实|GB 37479—2019，中文名称一致，发布日期2019-04-04，印刷实施日期2020-05-01|
|官方来源|[国家标准全文公开系统详情](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=40B53B45E279F71D82D19417CAF123EE)，[全国标准信息公共服务平台](https://std.samr.gov.cn/gb/search/gbDetailed?id=86000D0C5CBA0E10E05397BE0A0A5BBB)|
|官方核查2026-10-13|标准号/名称/发布一致；现行，实施2020-11-01；原件日期差异请求C，不悄悄覆盖|
|替代关系|前言无代替声明；详情未显示已生效替代版本，显示修订计划不等于已替代|
|真实性范围|封面和正文身份自洽、官方元数据可关联；未与官方在线全文逐页比对，不以SHA声称全文真实性获得官方认证|

## 页/条款覆盖

|PDF物理页|印刷页|内容及处理|
|---|---|---|
|1|封面无页码|身份、发布/实施、发布机构；原页已看|
|2|I|前言、起草依据/单位/人；提取读取，无业务数值；无代替声明|
|3|1|第1范围、第2四项引用、第3及3.1定义、第4能效等级；原页已看|
|4|2|表1十行、表2十二行，5.1/5.2；原页已看，全部表值/合并/边界视觉自核|
|5|未印（顺序正文第3页）|5.3、5.4 a–d、6.1 a/b、6.2、6.3；原页已看，9条款数值中的8项来源在此|

没有附录、带编号公式、表3或续表。正式源文件及整页渲染均不交付到Git，`_tmp/`由本目录`.gitignore`排除。

## 结构检查（与数值核验分开）

执行者Codex，2026-10-13。人工结构盘点：表1 3物理分支/10行；表2 4物理分支/12行，共7分支22行；每行3等级，全部等级格非空。合并范围记录在主映射第4节。7组首行下界和7组末行上界在工作簿为空，共14个未给端点；不是14个缺失数据。

自动检查：XLSX 3工作表、无计算公式；22行×5个分类/条件字符串=110项与构建转录记录匹配；22行×2端点=44项与转录记录匹配。**这些是导出完整性检查，预期来自同一转录记录，不是独立原文验证。** 原文分类与边界证据来自PDF4图像自核。

## 数值核验

1. 使用pypdf读取PDF4，Unicode NFKC规范化，提取两位小数的等级数值，得到66值；按原页表1、表2行列顺序与XLSX真实单元格I/J/K逐格Decimal比对。66 PASS、0 FAIL、0 ERROR、0 SKIP；逐格来源、预期、实际与坐标见[numeric_audit.csv](numeric_audit.csv)。
2. 执行者对照PDF4图像与生成工作簿预览，自核全部66值及相应7分支22行，没有发现差异。文本提取比对不会独立消除同一执行者误读风险，不等同于另一人或另一会话独立验收。
3. 9条款数值从PDF3/5图像核对并显式列入工作簿`条款数值!B2:B10`，与审计脚本内自核值比较9 PASS、0 FAIL；它是源页自核后的导出核对，不是额外独立来源。数值顺序为0 Pa、0℃、0.95、1.10、2位、29℃、35℃、1.077、0.914。
4. 三张工作表均通过artifact-tool渲染并看图，表头、分支、数值及条件可读；工作簿不是评价器，不设公式结果缓存，不宣称Excel原生计算引擎测试。

本次独立逐格验收：NOT_RUN。引用GB/T 18836、GB/T 17758—2010、GB/T 25128—2010、GB 21455的完整试验工况、年度系数与静压修正规则：NOT_VERIFIED。官方日期调整公告：NOT_VERIFIED。原PDF与官方在线全文同一性：NOT_VERIFIED。生产unittest/compileall/smoke/性能：NOT_RUN（无生产修改，不借此宣称通过）。

## 可复现性

`build_workbook.mjs`使用装载工具提供的Node和`@oai/artifact-tool`生成工作簿；本地`node_modules` junction只指向依赖位置并忽略，不提交依赖。`verify.py`使用装载工具提供的Python/pypdf，读取源PDF和XLSX XML，输出逐格CSV和check_results.json。

构建中`data/table_rows.json`是转录中间数据，非Canonical、非批准业务真值；不允许运行时直接采用。最终XLSX SHA和检查计数见[check_results.json](check_results.json)。重新构建可能改变ZIP元信息，须重新运行verify.py更新实际哈希。渲染PNG、工具inspect输出忽略；可复现脚本保留。
