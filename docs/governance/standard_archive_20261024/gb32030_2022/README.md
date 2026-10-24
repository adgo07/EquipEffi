# GB 32030—2022 潜水电泵标准整理

2026-10-13，Stage A 文档交付。**主标准映射与表值转录已完成本轮自核；外部引用依赖尚未闭环，不宣告 Stage A 验收通过或可进入实现。**

阅读顺序：

1. [资料真实性与引用适用性](SOURCE_AUTHENTICITY.md)：主标准及七份相关材料的身份、SHA、官方来源、冲突和限制。
2. [完整标准映射](../../../standards/gb32030_2022/STANDARD_MAPPING.md)：适用范围、输入、六表路由、公式、附加要求及无法评价边界。
3. [六表工作簿](../../../standards/gb32030_2022/data/GB32030_2022_表值映射.xlsx)：相对基准的增量、容差符号、破折号及试验等级；不是计算引擎。
4. [逐格溯源](evidence/cell_trace.csv)、[转录数据](data/tables.json)、[结构计数](evidence/structure_counts.json)。
5. [核验记录](evidence/VERIFICATION.md)、[数值回看记录](evidence/numeric_spot_check.csv)、[机器检查结果](evidence/verification_results.json)。
6. [边界候选](BOUNDARY_CANDIDATES.md)、[问题补充请求](ISSUE_REGISTRATION_REQUEST.md)、[交接](HANDOFF.md)。

正式问题状态只见根台账 `EQP-STD-GB32030-001`；本目录不另设状态权威。七份材料全文真实性、两处发布日期差异、两份旧版引用、缺失 GB/T 2818/7021 及效率容差符号疑点，均不得由本次转录结果掩盖。

## 复核与复现

源文件定位及 SHA 见 [source_inventory.json](evidence/source_inventory.json)。交付文件 SHA 见 [delivery_manifest.json](evidence/delivery_manifest.json)，清单不包含自身及临时文件。

脚本只写本目录。`extract_sources.py` 读取仓库原 PDF，需 pypdf、pypdfium2；`build_data.py` 生成六表结构与源格关系；`build_workbook.mjs` 通过 artifact-tool 生成并渲染工作簿；`verify_delivery.py` 用标准库读取实际 XLSX XML 校验坐标，并输出回看锚点结果。使用当前环境提供的 Python/Node 和依赖，不将某台机器路径当作仓库身份。`tmp/`、`node_modules/` 与渲染预览是忽略的复核辅助材料。

重建工作簿后应重新运行验证、视觉查看六页渲染并更新交付清单；脚本内部的期望值仍来自本次转录，不能替代可信原图核验或独立验收。
