# 来源与平台预检查

核查日期：2026-10-13；执行者：本会话Codex。文件SHA证明文件身份，不独立证明文件真实性。

## 原文身份

|项目|记录|
|---|---|
|标准|GB 19576—2019《单元式空气调节机能效限定值及能效等级》|
|取得方式|Owner指定本机只读原件；原始下载渠道未提供|
|仓库相对定位|`标准原文/16. GB 19576_2019 单元式空气调节机能效限定值及能效等级.pdf`|
|SHA-256|`1c5c97fd39351ed9708fd69f45c9b37dfba8fccea3cc4f810b32de3522876026`|
|物理结构|4页：封面、前言Ⅰ、正文1、正文2；6章、1张跨页表；无附录、无编号公式|
|封面|GB 19576—2019，代替GB 19576—2004；2019-04-04发布，2020-05-01实施；ICS 27.010、F01|
|官方登记|2019-04-04发布、2020-11-01实施、现行、全部代替GB 19576—2004|
|真实性边界|封面身份与官方登记除实施日期外一致；已看封面和两页正文图像；未取得官方全文作逐页同一性比对，不称官方认证副本|

官方证据（2026-10-13读取）：[全文公开系统](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=D34F8444D10AA7DDEED93C9A2C275D61)、[全国标准信息公共服务平台](https://std.samr.gov.cn/gb/search/gbDetailed?id=86000D0C5CBC0E10E05397BE0A0A5BBB)。后者同时显示修订计划20253199-Q-469正在征求意见，不能当作已实施新版本。日期差异见登记请求R01，未找到并核实延期公告正文，不能自行断言原因。

## 页码定位

|PDF物理页（从1计）|印刷页|内容与核验方式|
|---|---|---|
|1|无|封面身份；原页PNG目视|
|2|Ⅰ|前言；文本读取，列出替代2004版与删除旧节能评价值等变化|
|3|1|第1–4章，表1前4分支；文本、原页图像|
|4|2|表1续表9分支及CC注，第5章、第6章；文本、原页图像|

## 平台预检查

- 开工工作树为实际`git rev-parse --show-toplevel`返回的EquipEffi checkout，origin核实为`https://github.com/adgo07/EquipEffi.git`，共享分支`codex/six-standard-mappings`。
- 开工HEAD：`d9f711068bde583138a7f3dded6f64dcaa339761`；任务规范起点：PR #22 `2c7807f32ef08d18554014328efd4ceaa356726f`。共享工作区其它会话改动原样保留。
- `git fetch origin`首次因FETCH_HEAD权限失败，获工具提权后成功。默认远端分支`origin/master`；本地master相对origin/master落后46提交（ahead 0 / behind 46），未切换或更新共享分支。
- 中央本地clone先验证origin为`https://github.com/adgo07/Qingzhou-contracts.git`。`git ls-remote`确认main=`854b544563260f9e79c73e714c85f6589e0f19b3`，与本地origin/main一致。按该SHA读取GUIDE_INDEX、ACTIVE Standard Development Guide及Product Delivery Policy。
- locked central SHA仍为`ee5feb0cc34dbd99790500fadd0c4c932e202a20`。从该SHA读取`contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md`。适用约束：正式十进制必须可复现；不以显示舍入改变比较值；无默认epsilon；标准允差与数值容差分开；不得把Pump Decimal50当全局默认。本任务只整理文字、表值与候选，未建立数值Profile或修改公共契约。
- 冲突分类：未发现LOCAL DEFECT或CENTRAL CONTRACT GAP；无Frozen升级需求。本任务不修改中央公共Contract。表格工作簿是校对资料，不是正式数值入口；字面小数另存CSV供以后受治理的迁移。
- 已读根问题台账，开工未检出GB19576条目；本轮两项登记请求见本目录文件，正式编号与状态由总协调维护。本任务不改变既有软件解释。

## 可复现工具

`build_workbook.mjs`以原页人工转录的字面数值生成单一XLSX及逐格CSV；Artifact Tool导出和预览，Python只读核验。`verify_workbook.py`读取PDF文本表格与真实XLSX坐标对照，不能替代原页目视或独立复核。Node依赖junction与PNG/全文提取仅在忽略路径内，不上传原PDF或整页扫描。
