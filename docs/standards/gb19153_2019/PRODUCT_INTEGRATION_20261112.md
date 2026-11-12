# 空压机GB19153候选接入实施记录

2026-11-12开始。状态：IMPLEMENTED候选，最终回归及Windows候选验证进行中。正式发布范围仍POST_V1；未SUPPORTED、未独立验收PASS、不正式发布，不改变Phase 8状态。

## 平台与授权

仓库adgo07/EquipEffi；主线35b198156586d8a032fdabc2e53793d192aa3abf，设计基线090ab964；Stage B决定提交34b556ad，六表核心提交48df69c0。最终生产候选SHA见配套验证JSON。

锁定中央ee5feb0cc34dbd99790500fadd0c4c932e202a20（Architecture V2.1、Numeric v1/Profile/Conformance）；ACTIVE指南按已合并829853a读取。MUST：精确十进制入口、完整值比较、显式独立Profile传播、不可变历史、同核Qt/Excel；MUST NOT：业务epsilon、显示值反馈比较、Domain依赖UI/Excel/SQLite、第二套Excel算法、覆盖源资产/历史、擅自升级锁。独立精确查表Profile为ALLOWED PROJECT DIFFERENCE，无CENTRAL CONTRACT GAP，无需中央Contract修改。

Owner批准D01仅评价比功率、正常结果直接等级，D02=A及18列统一Excel；决定见OWNER_DECISIONS.md。GB19153-001—003保留PROVISIONAL、004/005 RESOLVED；本次落实软件输出边界，不补造源表指标，不声称整机附加条件符合。QA-COMP-001独立验收前OPEN。

## 最终实现范围

- 源工作簿只读OOXML派生六表，2502数值/417横杠；保留原字面、PDF/印刷页、源行列坐标、表4普通/液冷分支。既有PDF事实核验不重复；旧compressor.json及兼容评价器保留，不拿旧结果作新业务真值。
- EQUIPEFFI_COMPRESSOR_EXACT_LOOKUP_V1使用精确十进制→Fraction，拒绝float/bool/非有限/混合单位；沿用128字符、30有效数字及绝对指数30防护。表内功率向上、压力向下；不插值、不跨横杠、不外推。六表按类别独立选路，便携机压力从0.2起。
- 缺必填/非法输入为INVALID_INPUT不存；范围外OUT_OF_STANDARD_SCOPE，合法无指标/不确定类别INSUFFICIENT_DATA可存；系统异常不伪装业务终态。正常结果仅等级、explanation空，内部assessment_scope保留SPECIFIC_POWER_GRADE_ONLY。
- 专用Application Request/Result/Record流程，不借电机输入或规则。每次合法单台CO记录独立追加，compressor-result.v1及pack/Profile来源一致；沿用现有JSON快照，不改迁移或schema。Qt按类别切换功率/冷却、保留通用设备信息；标准库和历史两页签同核。错误就近提示，分析中/保存反馈保留。
- V6.5只读派生V6.6，18Sheet顺序保留，空压机A:R契约；仅空压机表/其Table/专属配置/身份发生变更。G/K说明额定功率口径与有效综合比功率。L:O及R不含业务公式，软件结果另存。旧V6—V6.5空压机需新模板提示，已有设备继续按旧契约读取。
- 每Workbook一条batch_record，不逐行建单台Record。compressor_row_evidence保留行号、输入词法/规范值、数量、状态/等级/原因、阈值、选点与源格/pack；Sheet只存共享identity。列表只读剔除大证据，单条保留完整JSON。

## 验证与已解决问题

具体计数、字节哈希和日志入口见IMPLEMENTATION_VERIFICATION_20261112.json。阶段性全套在代码仍迭代时主动中断，明确NOT_COMPLETED，不能冒充固定源码最终回归。定向发现并修复V6.6默认断言、pyproject资源漏列、旧空压机未接通夹具、发布status固定字段集；没有放宽业务断言。

初轮全源分支测试107.062秒，独立检查约0.0295秒/评价。按实测只在Calculator实例内预编译派生索引，仍逐次验证包哈希；不做Repository/通用缓存重构。容量和持久化分别记录，不把无持久化测试写作正式保存验证。

## 交付边界

候选不是正式Release，不创建标签或发布产物。真实Windows EXE、实际Excel/WPS以及独立复验状态分别落证据；离屏Qt测试不当作实机验收。另一台干净Windows、125%系统缩放未取得本轮证据，不据此宣布Stage D通过。

Knowledge capture：无新增成熟专业知识；证据与已批准解释已在Mapping/决定落档。


## 2026-11-13容量复核修复

独立复核发现初稿保护Sheet仅4—13行可填写，列默认样式锁定，Q1便利数量合计仅覆盖Table十行。此前直接写XML的10000行读算写/持久化证据仍证明软件数据链，但不能证明Excel用户可填写，旧包不作为最终候选。

已在QA-COMP-001登记后修正：只追加共享styles保护变体、既有XF逐项保持；空压机B:K/P:Q默认及既有输入格解锁，所有表头和L:O/R锁定，新增结果格使用锁定结果列样式。Q1使用SUM(D4:D1048576)；容量依赖全列解锁+全范围Validation+Reader全行识别，不依赖受保护Sheet自动扩Table。父agent已独立核对保护和既有XF追加语义，定向产品7tests通过；又增加第14/10003行输入和新结果锁定回归。修复版仍需固定SHA的CI、完整10000行流程及新包验证；实际Excel/WPS引擎操作若未运行明确NOT_RUN。

此修复不改变Calculator、Numeric Profile、源Canonical、Compressor Application/Record业务文件。c27c3532下独立core 20177断言和Application45检查保留原SHA，以这些生产文件字节一致证明复用，不改写成新SHA重跑。跨设备Excel与保护修复另行复验。首次c27原生构建状态烟测因继承外部环境45秒超时，清Python/Qt环境与系统PATH后0.875秒ready=true；该旧包仍被本次容量修复取代，不混作最终交付。
