# GB 30253—2024 来源与核验记录

核验日期：2026-10-13。结论：Stage A交付稿已整理；以下检查通过不等于独立验收或标准解释批准。

## 平台预检查

- 已实际核对工作树、origin、分支、HEAD和工作区，并成功fetch。origin为`https://github.com/adgo07/EquipEffi.git`；分支`codex/six-standard-mappings`；本仓HEAD与fetch后的`origin/master`均为`2c7807f32ef08d18554014328efd4ceaa356726f`。本地master仍为`64b656ee4924fbf09f3fd87596ef1a1a779d1f09`，未切换或修改。
- locked central SHA：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`，未升级。中央本地clone已核验origin并fetch；ACTIVE GUIDE_INDEX、Standard Development Guide、Product Delivery Policy读取自已合并`854b544563260f9e79c73e714c85f6589e0f19b3`。
- **本任务不涉及中央公共 Contract。** 相关Frozen Contract无新增适用实现项；不制定Numeric/Unit/Record契约，不改锁文件，无需中央Contract变更，无已发现的中央契约冲突。
- 适用MUST：标准原文证据先行、Stage A映射与全量表值配套、疑点先请求登记、事实/判断/软件决定分开。MUST NOT：静默修正原文、直接写Calculator、创造第二套业务算法、宣布SUPPORTED、扩大产品范围。
- Standard Issue：读取根台账时未见GB30253专属条目；本目录R1～R3是登记请求，正式编号/状态待总协调写根台账。没有改变既有正式软件解释；本次没有Owner解释决定。

## 来源及提取方法

源PDF身份、51页结构及SHA见[README](../README.md)。原件只读，未上传。正文物理5～51页对应印刷1～47页；表格覆盖物理7～51页。

该PDF表格横置，字体字符编码重排，直接文本抽取出现乱码。`scripts/extract.py`只在忽略目录生成旋转副本，按嵌入CFF字体的字形轮廓哈希识别数字，再按PDF表格网格提取；字体映射按页号和字体名区分。数字映射以原页图像核对，未用历史JSON或生产实现反推。

`scripts/prepare_data.py`按原始未旋转PDF坐标再次逐格读取，转换坐标后比较两路字符串，保留原始页、页内表序、源行列、框坐标及两次读值。两路共享字体解码，因此能检查坐标、排序、抄录及写出一致性，**不构成独立识字或独立人工验收**。功率标签的区间符号规范化与短横线识别均经原页图像确认；未对效率值进行补值、修正或前向填充。

`scripts/build_workbook.mjs`使用`@oai/artifact-tool`创建30张Sheet并渲染预览；`scripts/verify.py`用openpyxl只读回读，不用它写工作簿。

## 覆盖与结果

|检查|结果|范围与限制|
|---|---|---|
|表格结构|PASS|29表、707功率行；各续表归属、表头等级/极数/转速与电压/冷却分支已核对|
|效率位置|PASS|10,803个，其中数字10,651、短横线152；短横线均在表1|
|原PDF两路机械逐格复读|PASS|10,803 MATCH，0 mismatch；共享字体解码的限制见上|
|XLSX实际单元格回读|PASS|10,803效率位置与707功率行，0 mismatch|
|工作簿结构与公式|PASS|索引+表01～29，顺序正确；0公式；0.0疑点与相邻短横线原样保留|
|原文图像查看|已完成|封面、正文物理5～6页、全部表页7～51；重点核对表头、续表、区间、短横线与0.0，不声称人工独立逐一检查所有数字|
|工作簿视觉检查|已完成|30个Sheet均渲染；全部29表数据区域已看预览，索引首屏已看；功率尾随小数点显示问题已修正|
|独立验收|NOT_RUN|未由另一人或另一会话独立逐格人工验收|
|正式unittest / compileall / 产品smoke / 性能|NOT_RUN|仅标准资料整理，无产品代码变更；不将它们记为通过或跳过|

可重跑的最终检查为9 PASS / 0 FAIL / 0 ERROR / 0 SKIP，详细检查项及四份数据资产SHA-256见[verification_result.json](verification_result.json)。提取与整理脚本在移入正式脚本目录后重跑成功，CSV哈希保持一致。

表1为567位置（415数字+152短横线）；表2～7各315；表8～10各392；表11～28各375；表29为420。合并表头展开为明确的等级与坐标标签；数据区没有据空白推断数值。

## 可追溯文件与复跑

- `cell_audit.csv`：每效率格的Sheet坐标、原文坐标、页码、源行列与双路结果。框坐标单位为PDF点，原始页左上为原点。
- `row_audit.csv`：每功率行的原页和原始提取标签。
- `../data/table_values.csv`：条件完整的平面表值，不是生产Canonical。
- `verification_result.json`：最终XLSX/CSV哈希及实际回读检查结果。

在具备pypdf、pdfplumber、fontTools、openpyxl的Python环境运行以下相对路径命令；Node需能解析`@oai/artifact-tool`。原PDF须仍位于README记录的仓库相对路径。脚本不下载依赖、不读生产JSON、不写本目录外资产。

```text
python docs/standards/gb30253_2024/evidence/scripts/extract.py
python docs/standards/gb30253_2024/evidence/scripts/prepare_data.py
node docs/standards/gb30253_2024/evidence/scripts/build_workbook.mjs
python docs/standards/gb30253_2024/evidence/scripts/verify.py
```

本次用Codex捆绑Python/Node；fontTools来自已有本机Python环境，通过PYTHONPATH提供。机器绝对路径不是仓库身份，也不是复跑约束。`tmp/`的旋转PDF、原页图片、渲染图与中间JSON以及本机node_modules连接均被本目录.gitignore忽略，不作为提交资产；未上传原文或这些副本。

## 未解决项与证据边界

R1表1 55 kW/12极/2级原文`0.0`已看原页，工作簿`表01!N23`保留并高亮；不能静默改成94.x。R2引用GB/T755的容差及适用版本尚无全文证据；GB/T22669—2008、GB/T32877—2022仅记录本标准明确引用的试验条款，未冒充已逐条核验外部文件。R3区间转速列与插值的衔接缺少充分解释，不能擅造600 r/min锚点。详细原文事实、技术判断、待决事项见[登记请求](../ISSUE_REGISTRATION_REQUEST.md)。

Knowledge capture：无。根BASELINE/HANDOFF/问题台账由总协调统一更新，本子任务未越界修改。
