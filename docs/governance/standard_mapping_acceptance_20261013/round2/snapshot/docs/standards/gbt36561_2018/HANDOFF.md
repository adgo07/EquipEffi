# GB/T 36561—2018 专属交接

2026-10-13。本会话Stage A整理资产已落地，交总协调登记和统一提交；**不是Stage A出口验收通过**，更不是SUPPORTED、冻结或Phase PASS。所有写入局限于`docs/standards/gbt36561_2018/`，未stage/commit/push，未切分支/工作树，未修改公共文件或生产资产。

## 交付

唯一入口[README](README.md)，配套[主映射](STANDARD_MAPPING.md)、[表值工作簿](data/GBT36561_2018_TABLE_VALUES.xlsx)、[来源/检查](SOURCE_AND_CHECKS.md)、[问题登记请求](ISSUE_REGISTRATION_REQUEST.md)、[28条边界候选](BOUNDARY_CANDIDATES.md)。CSV/JSON、真实XLSX坐标、检查证据和可复现脚本均在本目录。

原件SHA-256：`f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37`。工作簿SHA-256：`284ceebe8b76f2b20cbbfe3ebb144e2abd4e85a6f598d6d389510e13f410af0a`。完整交付哈希见[evidence/SHA256SUMS.json](evidence/SHA256SUMS.json)。

开工HEAD `d9f711068bde583138a7f3dded6f64dcaa339761`，origin已验证为adgo07/EquipEffi，fetch成功；共享分支`codex/six-standard-mappings`未变；origin/master为PR #22合并`2c7807f32ef08d18554014328efd4ceaa356726f`。中央ACTIVE指南读取已合并`854b544563260f9e79c73e714c85f6589e0f19b3`，Frozen lock不变。本任务不涉及中央公共Contract。

## 真实检查计数

- PDF26/26页图像审阅；正文表1～17＋附录A.1～A.12共29表。
- 468条表记录，其中456条数值、12条横线/变量/条件文本；是规范化记录数，不是去重原版单元格数。
- 468/468条XLSX真实坐标/值传输一致，失败0、错误0、跳过0。
- 数值原图样本42/42一致，覆盖29表；其余414项无逐格二次自核记录，独立验收NOT_RUN。
- 表16合并后18评分单元合计100分；XLSX业务公式0；3个Sheet均做渲染预览。
- 正式unittest、compileall、smoke、性能均NOT_RUN（无生产改动）。

## 请总协调处理

1. 在根台账登记R01～R10并回填稳定编号：错误表号、表9疑值/量纲、定量评分口径、A.5重叠、500℃缺口、通式/专用式及能耗统计边界、表16序号/引用/零分母、区间端点、表12修正对象、光亮淬火K8缺值。此文件不批准解释，也未私定正式问题状态。
2. 公共标准索引、BASELINE、HANDOFF/TASK_STATE由总协调维护。本目录哈希清单可用于汇总。
3. 使用本目录`.gitignore`排除原页渲染、文字提取、预览、依赖junction和inspect文件。不要提交原PDF/整页扫描，不要修改其他会话资产。

局限：仅核对官方登记元数据，未对本机PDF与官方全文逐字认证；未获得20项引用标准全部细则；PDF26底部未见印刷页码，“印刷23”是连续页推定，可靠定位为PDF26。全部解释请求仍需协调登记/后续有源决定，未开展Stage B/C/D。
