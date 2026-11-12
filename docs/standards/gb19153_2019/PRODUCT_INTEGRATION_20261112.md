# 空压机GB19153候选接入实施记录

2026-11-12开始。截至2026-11-13：IMPLEMENTED候选；保护修复、容量及原生构建验证完成，最后已完成完整CI为e900失败，三处旧fixture/预期已定向修复；本次HEAD门禁以PR #46实时checks为准，实际GUI内容交互未验证。正式发布范围仍POST_V1；未SUPPORTED、未独立验收PASS、不正式发布，不改变Phase 8状态。

## 平台与授权

仓库adgo07/EquipEffi；主线35b198156586d8a032fdabc2e53793d192aa3abf，设计基线090ab964；Stage B决定提交34b556ad，六表核心提交48df69c0。最终生产候选SHA见配套验证JSON。

锁定中央ee5feb0cc34dbd99790500fadd0c4c932e202a20（Architecture V2.1、Numeric v1/Profile/Conformance）；ACTIVE指南按已合并829853a读取。MUST：精确十进制入口、完整值比较、显式独立Profile传播、不可变历史、同核Qt/Excel；MUST NOT：业务epsilon、显示值反馈比较、Domain依赖UI/Excel/SQLite、第二套Excel算法、覆盖源资产/历史、擅自升级锁。独立精确查表Profile为ALLOWED PROJECT DIFFERENCE，无CENTRAL CONTRACT GAP，无需中央Contract修改。

Owner批准D01仅评价比功率、正常结果直接等级，D02=A及18列统一Excel；决定见OWNER_DECISIONS.md。GB19153-001—003保留PROVISIONAL、004/005 RESOLVED；本次落实软件输出边界，不补造源表指标，不声称整机附加条件符合。QA-COMP-001独立验收前OPEN。

## 最终实现范围

- 源工作簿只读OOXML派生六表，2502数值/417横杠；保留原字面、PDF/印刷页、源行列坐标、表4普通/液冷分支。既有PDF事实核验不重复；旧compressor.json及兼容评价器保留，不拿旧结果作新业务真值。
- EQUIPEFFI_COMPRESSOR_EXACT_LOOKUP_V1使用精确十进制→Fraction，拒绝float/bool/非有限/混合单位；沿用128字符、30有效数字及绝对指数30防护。表内功率向上、压力向下；不插值、不跨横杠、不外推。六表按类别独立选路，便携机压力从0.2起。
- 缺必填/非法输入为INVALID_INPUT不存；范围外OUT_OF_STANDARD_SCOPE，合法无指标/不确定类别INSUFFICIENT_DATA可存；系统异常不伪装业务终态。正常结果仅等级、explanation空，内部assessment_scope保留SPECIFIC_POWER_GRADE_ONLY。
- 专用Application Request/Result/Record流程，不借电机输入或规则。每次合法单台CO记录独立追加，compressor-result.v1及pack/Profile来源一致；沿用现有JSON快照，不改迁移或schema。Qt按类别切换功率/冷却、保留通用设备信息；标准库和历史两页签同核。错误就近提示，分析中/保存反馈保留。
- V6.5只读派生V6.6，18Sheet顺序保留，空压机A:R契约；仅空压机表/其Table/专属配置/身份发生变更，并在共享styles.xml只追加保护样式变体（既有XF不变）。G/K说明额定功率口径与有效综合比功率。L:O及R不含业务公式，软件结果另存。旧V6—V6.5空压机需新模板提示，已有设备继续按旧契约读取。
- 每Workbook一条batch_record，不逐行建单台Record。compressor_row_evidence保留行号、输入词法/规范值、数量、状态/等级/原因、阈值、选点与源格/pack；Sheet只存共享identity。列表只读剔除大证据，单条保留完整JSON。

## 验证与已解决问题

具体计数、字节哈希和日志入口见IMPLEMENTATION_VERIFICATION_20261112.json。阶段性全套在代码仍迭代时主动中断，明确NOT_COMPLETED，不能冒充固定源码最终回归。定向发现并修复V6.6默认断言、pyproject资源漏列、旧空压机未接通夹具、发布status固定字段集；没有放宽业务断言。

初轮全源分支测试107.062秒，独立检查约0.0295秒/评价。按实测只在Calculator实例内预编译派生索引，仍逐次验证包哈希；不做Repository/通用缓存重构。容量和持久化分别记录，不把无持久化测试写作正式保存验证。

## 交付边界

候选不是正式Release，不创建标签或发布产物。真实Windows EXE、实际Excel/WPS以及独立复验状态分别落证据；离屏Qt测试不当作实机验收。另一台干净Windows、125%系统缩放未取得本轮证据，不据此宣布Stage D通过。

Knowledge capture：无新增成熟专业知识；证据与已批准解释已在Mapping/决定落档。


## 2026-11-13容量复核修复

独立复核发现初稿保护Sheet仅4—13行可填写，列默认样式锁定，Q1便利数量合计仅覆盖Table十行。此前直接写XML的10000行读算写/持久化证据仍证明软件数据链，但不能证明Excel用户可填写，旧包不作为最终候选。

已在QA-COMP-001登记后修正：只追加共享styles保护变体、既有XF逐项保持；空压机B:K/P:Q默认及既有输入格解锁，所有表头和L:O/R锁定，新增结果格使用锁定结果列样式。Q1使用SUM(D4:D1048576)；容量依赖全列解锁+全范围Validation+Reader全行识别，不依赖受保护Sheet自动扩Table。父agent已独立核对保护和既有XF追加语义，定向产品7tests通过；又增加第14/10003行输入和新结果锁定回归。修复后完整10000行流程和新包验证见下节；完整CI及修复结果见最终门禁段，实际Excel/WPS引擎操作明确NOT_RUN。

此修复不改变Calculator、Numeric Profile、源Canonical、Compressor Application/Record业务文件。c27c3532下独立core 20177断言和Application45检查保留原SHA，以这些生产文件字节一致证明复用，不改写成新SHA重跑。跨设备Excel与保护修复另行复验。首次c27原生构建状态烟测45秒超时，后续不同环境及工作树输出路径探测0.875秒ready=true；该次未单独证实原因；该旧包仍被本次容量修复取代，不混作最终交付。


## 2026-11-13最终候选与验证

运行时固定e900492349bbe1b6a4a8faac9851a499738a8e6e；构建固定cb0a08bedcbcbc8f04540ae00c0b835b736c9faf，后者只改构建烟测临时目录、定向断言与QA，不改运行时src。构建工具注释后续仅按观察事实校正文案。业务core和Application证据保留c27c3532原SHA，以四个生产文件git blob逐字节不变证明复用；最终跨设备Excel41检查为e900。独立JSON分别落档，不改写成新SHA重跑。

修复版2/100/1000/10000行均走默认persist=True路径，分别4.265/6.922/33.375/314.547秒；每档13检查通过，均一条批次、零单台记录，逐行证据完整、列表精简、详情全量、读取不改DB。包含输入默认保护、远行及结果保护机械检查。该证据与实际Excel/WPS操作分别记账，后者NOT_RUN。

最终EXE与ZIP实际哈希、203成员CRC、资源原字节与禁带资产检查见[聚合JSON](IMPLEMENTATION_VERIFICATION_20261112.json)及[evidence目录](evidence-implementation-20261112/)。原生编译及真实EXE状态检查exit0；独立包复核5检查通过。系统Temp状态输出在两种cwd均超时，工作树状态输出在两种cwd均<1秒成功；仅记录相关性，不推断具体系统策略。构建烟测临时状态目录改到本次输出内并自动清理，最终包不含临时状态目录。

本次Popen启动只使用独立review LOCALAPPDATA：`outputs/compressor-implementation/native-cb0a08be-data/EquipEffi`，不使用正常用户数据目录。提升后的进程元数据确认PID45852、Windows窗口4919298和四设备标题；早期非提升快照未取得窗口句柄，不能据此判断无窗口。窗口存在/启动与内容交互验收分开，实际Qt业务操作仍NOT_RUN。

指定Astra在Excel和最终Qt窗口均取得inventory后，内容/AX/截图调用持续阻塞并中断；没有可据以宣布下拉、10k原生填写、保存重开或Qt业务交互通过的证据。Excel和Qt分别落NOT_RUN文件，保留早期恢复经历及最终模板/包SHA。另一台干净Windows和125%系统缩放仍无本轮证据。

完整回归由Windows Core CI全量发现承担（含compileall、tests/contract和资源smoke）。最后完成的e900运行1330tests/1611.725秒，1327通过、2失败/1错误、0跳过；Whitespace与Compileall成功，资源smoke因测试失败未执行。三处均为旧测试fixture/预期：临时zipapp少造新资源、三设备输入对空白第四Sheet的摘要数量仍按三、选点压力仍期待旧有理数表示。未改生产行为，只补齐fixture并增强空摘要零值断言，精确三用例复验3tests/11.343秒通过；相关三模块复验25tests/106.962秒全部通过（0失败/错误/跳过），详见JSON。

本次提交时最后完整CI仍是上述e900失败；已修复的当前HEAD最终门禁以PR #46实时checks为准，不把未完成的新HEAD运行写成PASS。后续CI结果更新PR，不为回填结果制造下一次文档提交。本地阶段性全套NOT_COMPLETED不作替代；cb0构建工具另有7tests/0.142秒通过，后续注释仅按已观察事实校正，无运行时代码变化。PR #46保持draft，不合并、不发布、不提升SUPPORTED。

本机便捷独立验收入口及说明：`outputs/compressor-implementation/launch-compressor-review.cmd`、同名PowerShell脚本与`README_候选独立验收.md`；其数据固定到独立review目录，脚本语法通过，未为测试脚本再次打开窗口。入口和SHA列于聚合JSON，不属于正式发布安装器。
