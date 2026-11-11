# 永磁电机候选接入实施方案

日期：2026-11-11。Owner授权先推进永磁、新建分支，高压与永磁稍后一并人工验收。延续GPT-6.1-sol medium实施、主会话独立审查、涉及Computer Use使用GPT-6-astra medium的协作。授权候选实现与PR，不合并、不发布、不自行提升SUPPORTED。

## 基线及现有决定

- 独立工作树`EquipEffi-pmsm-integration`，分支`codex/motor-pmsm-integration-20261111`，基于高压PR44的`03ade251868c9f750822d58368114ae10cc8f656`。高压PR44与测试包保持不动；本轮PR以高压分支为base，仅展示永磁增量。高压合并后再核对base，不提前合并。
- 中央ACTIVE指南`829853a943c421e0b9864d84f3d94970d2ddf688`，Frozen按platform-lock `ee5feb0cc34dbd99790500fadd0c4c932e202a20`，不升级锁。沿用标准开发Stage A–D、同核适配、精确全值比较、不可变记录及现有家族UI。
- 依据本目录A.2 STANDARD_MAPPING、29表工作簿、INTEGRATION_DESIGN及根台账001—004。001异常0.0排除，002容差不参与等级，003的600临时锚保持PROVISIONAL且允许临时计算，004按已批准精确双线性、缺角不算。不得改标准源值、Approved Golden、其它标准内核、锁或数据库迁移。
- 本轮授权覆盖五分支A低压异步起动、B高压异步起动、C低压变频、D高压变频、E电梯。历史POST_V1描述保留为历史；新增开发候选入口状态随实际实现标IMPLEMENTED，正式范围和SUPPORTED须待Owner后续验收决定。

## 实施设计

1. 先审计旧PMSM资源/Evaluator用途，不把旧代码当已验收真值。只读29表生成独立可复现候选包，逐格记录原值、表/行列、单位、区间和Issue覆盖；不得调用旧激活/提升脚本改变正式状态。
2. 新建唯一GB30253 Calculator及独立`EQUIPEFFI_MOTOR_PMSM_EXACT_LINEAR_V1` Profile/Conformance。直查、区间命中、一维及双线性全部精确有理数，全值比较、显示隔离、不补值不外推。003只限表8—10的500<n≤600；源区间跳变保留；区间行下界插值按既有设计§4.1。新解释不自行决定，登记后交主会话判断是否需Owner。
3. 五个显式类别ID沿用INTEGRATION_DESIGN；Qt与Excel共用Application/Calculator。额定电压V、功率kW、效率1—100百分数点；A/B频率与极数，B/D冷却，C/D/E额定转速。类别切换清除或排除不适用旧字段，不猜标准，不新增试验/报告确认字段。
4. 沿用现有电动机页、标准库、自动记录、历史两页签；必要时显示简短临时解释说明，不要求确认。合法终态（包括INSUFFICIENT_DATA）可记录，INVALID_INPUT及执行失败不记录。快照保存Issue状态、精确阈值/端点、Profile及包身份，历史只读不重算。
5. **对旧Stage B版本建议的实施更新：新增V6.5 / motor-input.v5**。V6.4已经由高压PR44实现并供验收，不在原身份下增加永磁。新增派生模板仍用同一电动机Sheet A:T：F类别，G V、H Hz、I冷却、J kW、K极数、L按类别的额定/铭牌转速、M效率，N:P/Q/T结果。其它设备Sheet与旧V6—V6.4字节保持。旧contract粘贴永磁须明确拒绝，未知类别不得伪成功。
6. 输出另存，一个Workbook一个批次、零逐行单台记录；混合GB18613/GB30254/GB30253统一执行。包内自足资源，新候选目录和数据隔离，保留原高压包。

## 验证及阶段交接

- 第一段交内核与包/Profile/Conformance：29表源格核验、全部路由、T−δ/T/T+δ、001—004、区间端点/跳变/缺角、环境上下文扰动/float拒绝。主会话用实现前选取的映射/源格独立预期复核，不能从被测实现反推。
- 第二段交Application/Qt/历史与V6.5：五分支字段/切换、来源追溯、输入错误、缺项合法终态、存储失败；旧快照/旧模板不变、三标准混合批次、输出保真及1/100/1000/10000行容量。
- 第三段串行完整回归与候选构建，禁止构建和需要项目锁的测试并行。主会话独立审阅实际diff/测试和输出，指定astra执行原生关键流程及小窗；没有Excel/WPS或DPI环境的项目如实NOT_RUN。
- 维护本文件及TASK_STATE/V1_SCOPE/QA现有状态，不建立额外报告体系。实现者本地提交、不得自行推送；主会话复核后提交永磁增量PR，完整CI通过后交付两个候选供Owner一并验收。不得以工程通过替代Owner正式支持决定。

## 第一段执行记录

- 旧清单的 `active` 表示 `gb30253_2024_pdf_verified_v1` 数据曾启用。其历史 Evaluator 用别名和默认电压/冷却组，变频取旧90%额定转速效率字段，查表也不覆盖已批准的合法功率插值。新候选由 A.2 映射和配套工作簿派生，独立装配并校验身份。保留旧兼容路径。原文逐格核对沿用[既有独立验收](../../governance/device_full_acceptance_20261013/motors/GB30253_2024_ACCEPTANCE.md)，本轮逐格复核工作簿至运行资源及 Calculator。
- 固定工作簿 SHA-256 为 `34cafd69c14bc5b15d4e674ab7a18b49ec8cc55fe34175a698b827074d2004a1`，A.2 映射使用 LF 归一 SHA-256 `3118f05a4fe784e56db36e52ffd25941f2eafadd0a6995e10061541b241c3748`。候选语义哈希为 `b55a45b6de2930708a510b4132ed2a6f18c84f49fbfbdf93388b578ead446da7`。29 表、707 行、10651 个数字（含原异常 0.0）、152 个短横线。001 在运行包显式标记排除，源显示 0.0 保留。
- 第1章明确范围外为 `OUT_OF_STANDARD_SCOPE`。范围内未列极数、源短横线、45 kW 后无合法12极上端点或缺所需角为 `INSUFFICIENT_DATA`，保留具体理由和已查源格。资料缺项为 `INSUFFICIENT_DATA`，非法词法或效率范围为 `INVALID_INPUT`。只有阈值齐全且输入低于三级限值时给出“未达3级”。包校验或执行错误走异常通道。
- 区间行下界用于另一轴固定时的一维功率插值。双轴同时未列时不借区间行补角。功率已落在原区间行时仍可在该固定行内按相邻合法速度端点做一维插值。表8—10在原“>600～900”列及相邻区间保留原跳变。003 只标记实际使用临时600锚的 `500<n≤600`。004用于其余合法双轴插值。
- 定向测试 `tests/unit/test_motor_pmsm_core.py` 9项、16个子测试通过。覆盖10803个源格、29表路由、各级 T−δ/T/T+δ、所有缺角位置、区间拒绝、上下文扰动、float拒绝和修改后重签拒绝。独立 `EQUIPEFFI_MOTOR_PMSM_EXACT_LINEAR_V1` 的8条 Conformance 按冻结 Schema 校验并执行。
- 主会话独立复验覆盖3601个源网格点及31个预先选定的定点案例，共3960次评价和15650项断言。另有3402个功率中点、2259个转速中点、2166个四角中点复算一致。首轮把高压标准的范围外预期误用于本标准源格不足，已按本标准映射修正独立预期，生产状态保持上文映射。证据在外部 `PMSM_review_20261111` 目录。

## 第二段 Application、Qt 与历史

- 共享电动机 Application 只按显式类别选择 GB30253。标准库“按此标准分析”保留原电动机页面，展示五项永磁分支及占位，要求用户选择分支。通用入口提供完整类别。高压笼型入口仍预选其唯一类别。按分支显示频率、极数、冷却或额定转速。不适用字段不进入评价或快照。
- 终态快照保存有效原词法与单位、精确值、逐级源格与 Issue 状态，Qt 只投影已保存证据。延用自动保存合法终态、两页签只读历史。旧记录和数据库结构沿用现有逻辑。
- 源码 Qt、Application、历史和架构边界联合复验28项及5849个子测试通过。首次运行系统临时目录权限阻止 SQLite 创建测试记录，改用工作树内独立测试临时目录。早期新增的 Qt 契约导入已收口到现有 Application 入口。测试 SQLite 连接已在清理前关闭。
- 主会话中途独立 Application 复验427项检查通过，证据 `PMSM_review_20261111/application-r1.log`。该轮核对31个精确阈值、旧输入拒绝、非法输入、资料不足、保存失败、原词法和不可变历史。最终固定源 `c22301f` 已按下节独立复验。

## 第二段 V6.5 与批次快照

- 已派生 V6.5 / `motor-input.v5`，固定 SHA-256 `11F767EFCF03D362ED1CFCF7FDFC17ED3909DBD4BC21C48971762FFA0A5CF059`。共用电动机 A:T，L列按类别取额定转速或已有铭牌标称最高转速。五分支必填字段、单位、冷却和速度语义与配置/Manifest机械核对。旧V6至V6.4模板及其它设备部件保持原字节。新增永磁说明的原单元格行高已增加。
- V6/V6.1电机Sheet仍明确保留未处理。已接通电机的V6.2/V6.3/V6.4粘贴永磁ID或中文标签，逐行报告需V6.5。V6.5未知类别、公式输入和非法百分比均明确输入错误。非法行Q列沿用空白、T列错误说明。
- `OTHER_CATEGORY` / `UNCERTAIN_CATEGORY` 保留已有GB18613默认请求身份和provenance，继续既有“不在范围”/“无法判定”语义。“不路由永磁分支”落实为不查永磁表，保留原中性类别快照契约。实现中曾移除V5中性类别provenance，经既有回归及主会话核对已恢复。未修改既有回归预期。
- 一个Workbook追加一条批次，永磁行的 `motor_pmsm_row_evidence` 保存在既有summary JSON顶层，包含有效原词法、单位、终态、精确阈值、逐级源角、权重及Issue状态。包/Profile/规则共享身份在电动机Sheet provenance中保存，行通过 `pack_sha256` 关联。输入错误及执行失败行保留真实错误，不保存前行trace。未新增逐行单台记录或数据库迁移。
- 批次列表SQL只投影剔除V6.5的新大字段，分页、关键字和已有摘要沿用原逻辑。单条加载保留完整证据。测试实际比对列表前后数据库JSON原字节一致，历史只读。
- V6.5最终定向5项、3个子测试通过，84.55s、exit0，日志 `outputs/pmsm-integration-20261111/excel-final.log`。容量1/100/1000/10000行分别1.875/2.141/7.204/56.344s，批次JSON为8718/342160/3373874/33699848字节。10000行的功率及转速逐行不同，每行均经同核评价，4个容量批次、零单台记录。
- 首次联合定向35项及5902个子测试通过，1个新增测试误将非法行Q列期望写为“输入错误”，已按已有Writer纠正测试。随后187项大定向中181项通过，6项失败，日志 `outputs/pmsm-integration-20261111/targeted-final.log` 保留。失败包括2项中性类别provenance回归及4项共享适配器误取结果上的标准字段。适配器已改取权威references，变压器夹具联合6项复验通过，日志 `transformer-adapter-r2.log`。最终大定向再验结果在下节补记。
- 主会话另独立完成36行混合三电机标准169项检查、34永磁行证据497项检查，以及40行五标准跨设备Workbook。后者包含变压器成功/资料不足/范围外、结果重导入、2批次零单台及旧快照不变，共12项通过。证据 `PMSM_review_20261111/excel-r2.log`、`batch-evidence-r1.log`、`cross-device-r1.log`。首轮独立Excel脚本的低压71.43%等级预期已查源纠正为3级，生产结果保持。

## 最终定向与构建安排

- 最新定向187项、9531个子测试通过，195.33s、真实exit0，日志 `outputs/pmsm-integration-20261111/targeted-final-r2.log`。覆盖所有电机内核/产品回归、旧V6.2/V6.3模板、同核批次、不可变历史、架构边界、入口状态及实际wheel构建/资源审计。仅排除已独立执行的2个容量测试，完整CI套件未减项或加skip。
- 本地完整发现未重新执行。按主会话安排，最终最新HEAD的全量回归由PR Windows Core及Whitespace门禁执行，本轮候选记录在其完成前保持待验收。
- 本阶段固定生产源码 `c22301f36278919a798552a800b34f8e2dbafd19` 后已串行构建独立Windows候选，包身份见下节。原高压包及启动器保留。原生窗口交互交主会话指定的独立验收者。
- 尚未验证Excel/WPS真实下拉、追加行、保护及保存重开，实际125%系统DPI、跨屏和另一台干净Windows。文件解析及离屏Qt通过仅按实际覆盖记录。

### 主会话固定源独立回执

主会话按生产源码 `c22301f36278919a798552a800b34f8e2dbafd19` 再次独立复验，全部真实exit0。内核15650项断言、3960次评价，独立中点和四角插值7827次评价，Application427项、Qt27项、批次行证据497项检查均通过。保护资产及生产差异审阅通过。证据文件保存在 `D:/project/设备能效软件/PMSM_review_20261111/`。

- `independent_core-final-c22301f.log`
- `independent_interpolation-final-c22301f.log`
- `independent_application-final-c22301f.log`
- `independent_qt-final-c22301f.log`
- `independent_batch_evidence-final-c22301f.log`

## 独立Windows候选

- 固定生产源码 `c22301f36278919a798552a800b34f8e2dbafd19`。此后提交仅补执行记录。原生构建及包资源审计真实exit0，`qt_capable=true`、`status_ready=true`。新EXE再次独立执行 `--status`，默认V6.5、GB18613为SUPPORTED、高压与永磁均IMPLEMENTED。实际文件SHA已与构建报告重新比对。
- EXE为 `D:/project/设备能效软件/EquipEffi-pmsm-integration/dist/pmsm-integration-c22301f/dist/equipeffi-pmsm-candidate/equipeffi-pmsm-candidate.exe`，SHA-256 `81a58bf39a45e7df0150781fbb30c04a3986a8986f67fc3c569693ade4ac0a80`。
- ZIP为 `D:/project/设备能效软件/EquipEffi-pmsm-integration/dist/EquipEffi-pmsm-candidate-c22301f.zip`，SHA-256 `48be66b32ff9c5cd72d3ea0b205be42d399b75789a5c8221a8511f99ddb37368`。
- 可双击启动器为 `outputs/pmsm-integration-20261111/启动永磁候选_c22301f.cmd`。以系统PATH、清空外部Python/Qt插件路径、Qt windows环境启动。独立LOCALAPPDATA为 `outputs/pmsm-integration-20261111/native-c22301f-data`，实际测试数据在其 `EquipEffi` 子目录。
- 已在可见用户环境用已授权的提升Popen启动，PID15828。用户环境只读核对路径及窗口标题正确，`Responding=true`，独立user.sqlite和records.sqlite已创建。受限进程清单未显示此PID，用户环境清单及主会话CU均确认窗口存活。只启动一份新候选，保留用户和旧高压程序。
- 构建报告/日志为 `outputs/pmsm-integration-20261111/native-build-c22301f.json` / `.log`，独立状态为 `native-status-c22301f.json`，启动记录为 `native-launch-c22301f.json`，启动日志为 `native-startup-c22301f.log`。主会话指定的独立验收者正在验证实际窗口，本段仅记录构建及启动事实。

## 提交前独立原生复核（2026-11-11）

- 指定GPT-6-astra medium使用实际Windows EXE完成交互；主会话独立查看截图、读取最终工作簿和隔离数据库，未仅以执行者自述通过。固定生产源码仍为`c22301f`。五分支A/B/C/D/E均实际计算；C的82.125%为1级、82.124999%为2级，显示限值82.13%，临时说明保留。共6条自动单台记录，非法字母和负值未形成记录。
- 标准库入口保留五类空占位，字段按分支显隐，B/D冷却不默认选中。类别框中部点击展开、滚轮不误改，623×673实际小窗可滚动到分析/查看记录，历史两页签和批次切换可达。首条C历史仍保留82.125、1级和当时临时解释。主会话查看[边界历史截图](evidence-product-20261111/c-boundary-history.png)和[小窗操作截图](evidence-product-20261111/small-window-actions.png)后复核。
- 实际UI导入40行五标准工作簿并另存输出，批次`BATCH-7a33daf840cc`。行口径1级34、2级1、3级1、无法判定2、不在范围1、输入错误1；数量口径43台、42台形成正式结论，1级37台（夹具中变压器3台、泵2台）。不得混用“行数”和“台数”。
- 主会话独立145项检查通过：31个预选永磁案例的原生输出阈值/等级，34行永磁快照，输入未覆盖、输出另存及哈希，最终6单台/1批次。历史打开及批次操作前后，6条单台全列JSON字节一致，SHA-256为`caba67bbd2eb5d888ff0812da9cf22baf05af7a85d1ba6027468fab70f20d5ce`。
- 原生输入SHA-256为`47AECC00544DB912780D691D26418CF6C0627A7898A7790688F8E8D026A716E8`，输出为`3B4891E5D56E4D0201B460B54A59A9DC2C74A27E6F9DF2D2000FC419771AE32B`。完整步骤、输出及独立回执位于本机`PMSM_review_20261111/native-review/`。主会话另核对候选ZIP实际哈希、204个成员及新运行资源，未包含原始PDF、数据库或测试数据。
- 初始Computer Use截图请求长时间未返回，恢复JS会话后文字状态可用；随后独立截图先黑屏再恢复。恢复后完成实际点击、键盘、滚轮、截图和上述业务流程。工具阻碍不被计为测试通过，也未为恢复关闭用户或旧高压程序。
- 本轮已测范围的独立工程复核通过。Excel/WPS实际下拉、追加行、输出保护和保存重开，125%系统DPI、跨屏及另一台干净Windows仍为NOT_RUN。没有用离屏或文件解析代替这些项目。用户尚未进行最终联合验收，不合并、不发布、不提升SUPPORTED；最新PR完整Windows Core与Whitespace结果在PR上记录。
- 供用户联合验收的便捷入口为`D:/project/设备能效软件/PMSM_review_20261111/启动永磁候选_c22301f.cmd`，新包包含高压及永磁候选。原高压PR #44、包、启动器和数据均保留。

## PR #45 首轮CI及标准库回归修正

- PR #45的 `62f4e4b129b66a9c62f428c369c4f680f92a8f09` 在[首轮Windows Core](https://github.com/adgo07/EquipEffi/actions/runs/42941843039)执行1309项，929.238s，1项失败、真实exit1。Whitespace通过。唯一失败为 `LocalPolishTests.test_standard_no_match_clear_retry_and_rated_summary` 的旧四行预期，实际已加入GB30253，标准库五条均为已装配标准。
- 测试改为独立列明GB19762、GB20052、GB18613、GB30254、GB30253五个完整标准号，核对集合及无重复。另检查搜索GB30253后只保留该标准，清除搜索和读取失败重试后恢复完整五条。保留原读取失败提示、重试操作及GB18613“额定效率”“1～100”摘要断言。
- 使用工作树内独立TEMP/TMP，完整执行local_polish、UI family stage2、新永磁产品及既有高压/低压Qt回归，25项通过，22.79s、真实exit0。日志为 `outputs/pmsm-integration-20261111/ci45-standard-catalog-r1.log`。本次修改限该测试与本实施记录，实际候选继续使用固定生产源 `c22301f` 的既有构建和原生验收证据。最新PR完整CI等待主会话独立复验及提交后执行。

- 主会话逐行审阅`9182ab0`的测试修正，并使用独立TEMP/TMP以unittest复验上述25项，13.481s、OK、真实exit0，证据为`PMSM_review_20261111/ci-fix-independent-9182ab0.log`。相对固定构建源码仅测试、文档和截图有变化，无生产改动；原候选包继续适用。最终最新HEAD的完整门禁以PR结果为准。

## PR #44 / #45独立验收整改

- Owner批准整改后，高压分支先以 `906138742061486573fc09f75de2e6a9956c55a4` 固定高压候选LF签出及补齐V6.4提示。永磁分支随后正常merge，提交为 `ba1733bbde3402be26fa43ab2e1ebd6d40b0e192`。合并时保留永磁已有V6.5版本提示，Reader类说明覆盖V6.2至V6.5。
- 在高压精确规则基础上，另为 `src/equipeffi/resources/standards/gb30253_2024_candidate.json` 声明 `text eol=lf`。两候选JSON的Git blob和语义哈希保持，`canonical_package_hash` 继续表示实际加载文件的原始字节SHA。LF文件SHA分别为高压 `1137696E9990ABD6F302BA4A45E6B141FFF325A7CE253B7CA1C507B0B2F2D2AF`、永磁 `44114BBDB6C831CF4271B60AF7935934E65786A9B0D3A1087199721C40E70CFA`。
- 身份回归对两包分别在 `core.autocrlf=true/false` 的全新clone中首次checkout，校验实际文件字节、装载及新增记录。历史CRLF资源按当时原文件验证，新增LF记录后旧记录的全列和原hash保持。
- V6.5低压永磁A/C/E的I列非空值现在明确形成行级输入错误，包含有效但不适用的冷却码、错码、空格和数字0。原输入及输出I单元格原值保留，错误说明定位I列行号。B/D合法冷却仍按原规则计算，来自GB30254等其它分支的错码沿用 `COOLING_OUT_OF_SCOPE`。H/K/L及旧V6.2/V6.3/V6.4校验沿用原契约。
- 新回归覆盖24行混合冷却输入，预期16行输入错误、6行1级、2行不在范围，另验证拒绝批次不改写已有单台记录。旧混合夹具中的低压I改为空，继续验证不适用H/K字段不进入有效输入。模板README补齐V6.5五分支及I/L说明，并把原V6单Sheet接入表述限定为历史基线。
- `standard_manifest.json` 的17包目录服务于现有 `JsonStandardRepository` 及其兼容审计。桌面候选由 `composition.py` 显式装配高压/永磁资源及同核服务。运行文件集由 `pyproject.toml` 声明，`check_distribution_assets.py` 和 `audit_release.py` 校验实际分发物及候选烟测。本轮保留17包目录及原审计语义。
- 主会话独立18行批次54项检查通过，覆盖10行输入错误、6行1级、2行不在范围，原I值保留、源SHA不变、1批次零单台及历史只读，证据 `PMSM_review_20261111/remediation-after/result.json`。主会话另完成身份及产品14项、14个子测试，2.70s、真实exit0。
- 最终整改定向76项、60个子测试通过，132.62s、真实exit0，日志 `outputs/pmsm-integration-20261111/remediation-targeted-r1.log`。覆盖两包首次checkout/装载/新旧Record、永磁输入及内核、旧高压/低压Application/Excel、统一批次及V6.2/V6.3兼容。2个已验证容量项未重复执行，完整CI套件无删减。
- 现有源码发行审计通过、真实exit0，17包目录完整，日志及JSON为 `remediation-release-audit.log` / `remediation-release-audit.json`。保留既有motor_lv来源定位的非阻断提示。主会话另独立复验36行、169项既有Excel真值回归，证据目录 `PMSM_review_20261111/remediation-excel-review/`。

### 整改后的固定联合候选

- 固定生产源码为 `9706781eb8693be8b90bc7963d3ed8c708d1d47e`，此后仅追加本执行记录。按既有 `tools/build_native.py` 串行构建，真实exit0，`qt_capable=true`、`status_ready=true`。再次执行新EXE的 `--status`，默认V6.5、GB18613为SUPPORTED、高压和永磁为IMPLEMENTED。实际ZIP中的两候选JSON逐字节等于当前LF工作文件，主会话已独立核对其SHA与固定Git检出一致。
- EXE为 `D:/project/设备能效软件/EquipEffi-pmsm-integration/dist/motor-remediation-9706781/dist/equipeffi-motor-candidate/equipeffi-motor-candidate.exe`，SHA-256 `d51328ff802f129e2a9f649c0689bc590fa5fb264bd3375d0b4fea46f20d7a7d`。
- ZIP为 `D:/project/设备能效软件/EquipEffi-pmsm-integration/dist/EquipEffi-motor-candidate-9706781.zip`，SHA-256 `1cec3cd038b601af61793836ea5ce966ec87c1a8ab5cc7bfa0d30478a77139bb`。实际EXE及ZIP哈希已与构建报告重新比较。
- 新启动器为 `outputs/pmsm-integration-20261111/启动联合电机候选_9706781.cmd`。独立LOCALAPPDATA为 `outputs/pmsm-integration-20261111/native-9706781-data`，实际数据位于其 `EquipEffi` 子目录。用户环境以系统PATH和清理后的Python/Qt环境启动，Popen PID23228，已只读确认精确新EXE路径、窗口标题及 `Responding=true`，新user.sqlite/records.sqlite已创建。
- 构建报告及日志为 `outputs/pmsm-integration-20261111/native-build-9706781.json` / `.log`，独立状态为 `native-status-9706781.json`，启动回执为 `native-launch-9706781.json`。原c223候选包、原高压包、旧测试数据及用户程序均保留。实际窗口整改复验和最新完整CI由主会话继续记录。

Knowledge capture：无。
