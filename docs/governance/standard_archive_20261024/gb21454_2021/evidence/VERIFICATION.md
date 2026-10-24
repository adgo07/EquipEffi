# 来源、结构检查与数值自核

执行日期：2026-10-13；执行者：本GB21454映射会话（Codex）。这是执行者自核记录，**不是独立逐格验收或Owner批准**。

后续独立证据：同日第一轮验收已核对本标准216个位置，整理稿有条件通过。详见[回应与覆盖边界](ACCEPTANCE_RESPONSE.md)。下文NOT_RUN保留为首轮执行快照，当前独立覆盖以回应引用的验收CSV为准，不扩展到未验位置。

## 平台 / Contract 预检查

|项目|实查结果|
|---|---|
|工作树与身份|`git rev-parse --show-toplevel`为本次G盘EquipEffi checkout；origin=`https://github.com/adgo07/EquipEffi.git`；路径只是当前环境|
|分支/开始HEAD|`codex/six-standard-mappings` / `d9f711068bde583138a7f3dded6f64dcaa339761`；其他会话未提交改动存在，按分工保留|
|远端同步|首次fetch受`.git/FETCH_HEAD`写权限限制；升级执行后`git fetch origin`成功。origin/HEAD=origin/master；origin/master=`2c7807f32ef08d18554014328efd4ceaa356726f`；本地master与origin/master左右计数0/46，本地master落后46；未切换/更新分支|
|locked central SHA|`ee5feb0cc34dbd99790500fadd0c4c932e202a20`，未修改锁文件|
|中央身份及ACTIVE读取|已验证本地中央clone origin为`adgo07/Qingzhou-contracts`；本地HEAD `14a8704cf08db13dc039769df940fbd6482c1818` 不当成当前远端。`ls-remote origin HEAD`取得`854b544563260f9e79c73e714c85f6589e0f19b3`，再通过本地已存在Git对象`git show <该SHA>:<path>`读取GUIDE_INDEX、Standard Development Guide与Policy相关章节|
|相关Frozen|按locked SHA读`contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md`、`NUMERIC_PROFILES_V1_FROZEN.md`相关规则。未改变架构/运行时契约；Numeric读取仅约束R2与未来接入边界|
|适用MUST|标准源可追溯；未来正式十进制链声明Numeric Profile和入口转换；区分计算/比较/显示值；标准明确修约须记录阶段和来源|
|适用MUST NOT|不把显示精度自动当业务修约；不加默认epsilon；不复制Pump Decimal50为全平台默认；不把整理XLSX或Python/JS数字变成未声明的正式业务数值链；不跳Stage A至实现/支持|
|冲突分类|本任务未发现需改变公共Contract的问题，分类N/A；R1～R4是本标准条款/引用/实现解释待确认，不冒充CENTRAL CONTRACT GAP|
|中央Contract是否需改|否。本任务不改变中央公共Contract。无生产Calculator/Canonical/Schema/数据库/Golden/UI变更|
|Standard Issues|开工检索根台账未有GB21454条目；4项本地登记请求供总协调登记，见同目录请求文件。没有既有软件解释变更|

## 原文身份与页位

原件：`标准原文/17. GB 21454-2021 多联式空调（热泵）机组能效限定值及能效等级.pdf`。

SHA-256：`ae091115094de6dcc2f587e35bd5a9389708fb37714804ef510ea831613a7331`。

来源方式：本次任务指定只读文件；未另行证明取得渠道。官方中文元数据[登记页](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=32791D15944EA9E65C8E97FF2FC2039A)核对标题、年份、发布日期2021-10-11、实施日2022-11-01及现行状态，均与封面相容。官方[修订计划](https://std.samr.gov.cn/gb/search/gbDetailed?id=5A7B8D9F48C24A0CE06397BE0A0A42C5)为20264264-Q-469，计划不是正式替代文本。没有下载官方全文与本原件逐字比对，不把SHA或水印当真实性认证。

|PDF物理页|印刷页|覆盖|
|---|---|---|
|1|封面，无页码|标准号、题名、发布日期、实施日、代替2008版|
|2|I|前言与版本差异|
|3|1|1～3章、范围与术语|
|4|2|4.1～4.4，表1/2|
|5|3|表3/4、4.5、5.1～5.6a|
|6|4|5.6b～d、6.1～6.3|
|7|5|6.4、7章|
|8|6|附录A.1、公式A.1、图A.1/A.2|
|9|7|A.2、表A.1/A.2、表A.3前12行|
|10|8|表A.3续表、表A.4|
|11|9|A.3.1.1～1.2、表A.5、图A.3/A.4|
|12|10|图A.5/A.6、A.3.1.3～1.7、A.3.2、A.3.3开头|
|13|未见印刷页码，顺序对应11|公式A.2～A.8及定义；映射“印刷11”指顺序位置，严格定位用PDF13|
|14|末页，无印刷页码|公式A.9与变量定义、版权信息；不可把背面标准号当页码|

已用Poppler将14页渲染并逐页查看；文本提取使用pypdf，仅为辅助。末两页无可见印刷页码已在此明确。`extract_source.py`可复现提取及渲染，临时文件在`tmp/`并由`.gitignore`排除。

## 结构检查

|检查|覆盖/结果|
|---|---|
|表号与行|表1/2各5；表3为4；表4为2；表A.1/A.2各5；表A.3为34；表A.4为32；表A.5为4，共9表96数据行；原表2个总计另存|
|公式/图|A.1～A.9共9个编号公式已映射；图A.1～A.6共6图已定位并摘要，未复制扫描|
|表1/2横杠|各12个EERmin无要求源格，合计24，原样保留|
|表3合并/横杠|IPLV(C)与水环式各覆盖2行；EER覆盖2行；地埋管/地下水容量2个横杠保留；未按相同指标或容量去重|
|表4表头|三级合并标题跨HSPF和2个COP列，表注各等级共用COP条件已核页图|
|工况合并/空白|两表使用侧干/湿球跨5点源格展开；户用<15、工商业15严格区分；热源A点各1横杠不误作0；无未解释空白数据格|
|发生时间|表A.3左右栏及续页按j保序；表A.4左右栏保序，3个0小时保留；每行有原页/左右块/源行|
|坐标|工作簿全部第5行为表头、第6行开始数据；实际坐标见cell_audit.csv，不按非空序号推列|
|最终视觉|9个Sheet均渲染并查看；标题、数据、说明可读；第一次预览的数值/横杠贴邻和A.5预览宽度已修正；最终9Sheet复看，无可见截断或错列|

## 数值自核与导出一致性（分别说明）

**原文数值自核**：执行者对PDF4/5/9/10/11页图的全部9表，逐行读取等级阈值、温度/时数、负荷率与连接台数，按条件转录；之后查看工作簿9Sheet与同一原图比对。包括58个等级/COP数值、工况温度及百分数、66行温度时数、4个最大台数、28个导出横杠和户用<15条件。此方法仍是同一执行者自核，没有第二人/第二Agent独立逐格签认。

**保存文件回读**：`verify_workbook.py`使用openpyxl只读XLSX，逐个真实坐标与页图转录JSON比较。共440个数据区域格（含条件、源位文字）加2个总计，**442/442 MATCH，0 MISMATCH**；数据区域303个数值格、2个数值总计；数值类型检查通过。工况合并源格展开产生重复值，因此305个导出数值格不等于305个独立原文源格。其余文字/条件同样回读，不把导出一致冒充标准真值独立验证。

**交叉算术**：户用34个小时数之和=3663，与原总计一致；工商业32个小时数之和=1015，与原总计一致，2/2通过。求和通过本身不能证明每格正确。

最终工作簿SHA-256：`7c85f6b7b7955e6c15df4fdbb012824b21dcc010d44b90067ed83556065efcc6`。完整机器结果见[check_results.json](check_results.json)，逐格预期/实际、源SHA、页与格见[cell_audit.csv](cell_audit.csv)。导出后若重建文件需重新计算SHA并刷新此记录。

|检查状态|pass|fail|error|skip|not_run|
|---|---:|---:|---:|---:|---:|
|表结构/工作表顺序和表头（表单位）|9|0|0|0|0|
|文件数据及总计回读（格单位）|442|0|0|0|0|
|小时求和（表单位）|2|0|0|0|0|
|最终Sheet视觉（Sheet单位）|9|0|0|0|0|
|保存文件公式/错误格扫描（检查单位）|1|0|0|0|0|
|独立原文逐格验收|0|0|0|0|1|
|原生Microsoft Excel打开/交互|0|0|0|0|1|
|生产unittest/compileall/smoke/性能基线|0|0|0|0|4|

工作簿公式格0、错误格0；Artifact Tool最终recalculate已调用，但本工作簿没有计算公式，不以调用证明业务算法。没有修改生产代码，故正式生产测试未运行；未覆盖三份规范性引用全文、完整试验合规、静压修正算法、Owner解释批准、原始高精度修约、真实机组输入计算与历史回归。

## 复现与维护

使用Codex依赖加载器返回的Python和Node（不依赖仓库业务环境）：

1. `extract_source.py [原PDF路径]`：校验SHA、提取/渲染到忽略目录。
2. `build_data.py`：从保留的页图转录数据生成`data/table_values.json`。
3. 本目录`node_modules` junction指向加载器的Node依赖；用Node运行`build_workbook.mjs`，Artifact Tool建表、inspect、render、recalculate、导出。junction不提交。
4. `verify_workbook.py`：只读回读，更新CSV和机器结果；再次逐Sheet查看渲染图。重新导出产生的文件SHA应更新此档与总协调基线。

任何数值/规则修订都须检查映射、工作簿、JSON、审计、候选与根问题台账；脚本是整理/核验工具，不是生产计算器。Knowledge capture：无。
