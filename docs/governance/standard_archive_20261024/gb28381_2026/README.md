# GB 28381—2026 鼓风机标准入口

本目录为2026版唯一整理入口，修订A0（2026-10-13），仅Stage A映射交付候选，未独立验收、未冻结。产品scope/support仍以[V1_SCOPE](../../../../V1_SCOPE.md)和[ROADMAP](../../../../ROADMAP.md)为准。

- [主映射](../../../standards/gb28381_2026/STANDARD_MAPPING.md)：范围、六个物理分支、输入、规则、公式、插值和待确认解释。
- [六表工作簿](../../../standards/gb28381_2026/GB28381_2026_TABLE_VALUES.xlsx)：与主映射配套；2,847个数值限值及123个原表“—”。
- [表值转录数据](table_values.json)、[逐格审计](CELL_AUDIT.csv)：保留源文本小数位、压力条件、印刷/PDF页、真实XLSX坐标；仅Stage A数据，不是生产Canonical。
- [来源登记](SOURCE_EVIDENCE.md)、[核验记录](VERIFICATION.md)、[图像抽核记录](VISUAL_SPOTCHECK.csv)。
- [问题登记请求及根台账编号](ISSUE_REGISTRATION_REQUEST.md)、[边界候选](BOUNDARY_CASES.md)、[交接](HANDOFF.md)。

2026-03-31发布，2027-04-01实施；截至本次核对日官方标为“即将实施”，全部代替GB 28381—2012。官方身份见[国家标准登记](https://std.samr.gov.cn/gb/search/gbDetailedCNF?id=4E648C80B6AB7D11E06397BE0A0ADEF1)。旧版另见[2012版入口](../gb28381_2012/README.md)；新旧范围、等级体系及限值不得混用，本任务不自动切换运行时标准。

原PDF只读，不随交付上传。依赖junction、渲染及提取全文在`.gitignore`中排除。复现：bundled Python执行`extract_verify.py`，bundled Node配置依赖junction后执行`build_workbook.mjs`，最后执行`verify_workbook.py`。只在本目录产生输出；可传运行环境依赖路径，禁止将本机盘符视为仓库身份。
