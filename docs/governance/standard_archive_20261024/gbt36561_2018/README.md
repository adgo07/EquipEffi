# GB/T 36561—2018 标准档案

《清洁节能热处理装备技术要求及评价体系》唯一入口。当前为Stage A整理交付草稿，未冻结，未通过独立逐格验收，未进入软件实现。正式scope/support见根[V1_SCOPE](../../../../V1_SCOPE.md)与[ROADMAP](../../../../ROADMAP.md)，不由本目录另行宣告。

- [主映射](../../../standards/gbt36561_2018/STANDARD_MAPPING.md)：范围、字段、29表路由、正文/附录公式、评分及未决解释。
- [表值工作簿](../../../standards/gbt36561_2018/data/GBT36561_2018_TABLE_VALUES.xlsx)：29表，468条记录，其中456条数值；没有业务计算公式。
- [来源与核验](SOURCE_AND_CHECKS.md)：原件SHA、官方元数据、全页定位、结构检查与数值抽样边界。
- [表/坐标清单](evidence/TABLE_LOCATIONS.md)、[数值抽样记录](evidence/numeric_review.csv)、[检查结果](evidence/check_results.json)。
- [问题登记请求](ISSUE_REGISTRATION_REQUEST.md)：R01～R11为本目录请求键；正式编号/状态在[根台账](../../../../STANDARD_ISSUES_REGISTER.md)。
- [边界候选](BOUNDARY_CANDIDATES.md)：28条，不是Approved Golden。
- [本目录交接](HANDOFF.md)：供总协调收口、登记与提交。

原件：用户指定`标准原文/12. GBT+36561-2018 清洁节能热处理装备技术要求及评价体系.pdf`。SHA-256为`f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37`。原件/整页图像不提交；本目录`tmp/`、依赖junction与提取临时文件已忽略。

`build_data.py`保存人工转录来源，生成可审查的CSV/JSON；`build_workbook.mjs`将同一数据导出XLSX及真实坐标；`verify_assets.py`只读核验XLSX并输出检查证据；`render_source.py`校验原件SHA后重现页图。JSON/CSV均为**文档审校数据**，不是运行时Canonical，也不产生业务等级。
