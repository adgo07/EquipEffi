# GB 18613—2020 接入实施记录

日期：2026-10-25。当前结论：Owner确认代码与工程验收通过，授权合并并重建最终代码候选包；不声明SUPPORTED、正式发布或Phase PASS。最新证据见末节，前文失败与待验证文字仅记录当时历史。

## 授权、基线及平台预检查

Owner已明确效率输入1～100%（含端点）是软件防呆，并授权设计确定后实施。设计基线为`e5aa673c1add75fdddb71360f11437a3d543f8b6`（PR33），产品基线为`master@2adcef7eba2ff2930f2f5a237028558747cc5b97`。使用真实Git工作树，不向主工作区未提交文件写入。

锁定中央SHA为`ee5feb0cc34dbd99790500fadd0c4c932e202a20`。适用Frozen为Architecture V2.1、Numeric Contract v1、Numeric Profiles v1及Common Core Conformance Vector v1；ACTIVE指南按中央`c5fc6d438c9200060649e47c016b9b48218de72c`的GUIDE_INDEX路由读取。

MUST：核心独立于Qt/Excel/SQLite，各入口调用同一Calculator，输入保留十进制语义，精确全值比较，结果/历史保留数值Profile及来源。MUST NOT：显示舍入反馈判级、二进制float成为业务真值、Excel另建算法、改历史记录、未经独立验收宣布SUPPORTED。电机精确整数尺度与有理数是`ALLOWED PROJECT DIFFERENCE`；查表说明丢失、旧输入路由等是本地实现问题。没有中央Contract缺口，不改锁。无数据库迁移。

标准问题001—005、007—008沿用已解决决定；006保持PROVISIONAL及已批准非阻断处理。人工验收后新增009，记录Owner确认的频率文本/正偶数极数输入软件决定，不改冻结映射。QA登记为QA-MOTOR-001/002/003。Knowledge capture：无新增条目。

## 实施边界

1. 六表新运行包`gb18613_2020_v2`从A.2映射与A.1六表源数据单向派生；保留108功率行、1149数值限值、32横杠、1源空白及来源格。旧motor_lv包与旧低压计算路径退出，高压/永磁候选不接通、不改变支持状态。
2. 六类别及“其他类别/不确定类别”，按条件显示字段；效率按1～100输入，0.85不自动换算。315～1000kW源行保持区间直查，250～315kW使用右端315kW做同分支插值。
3. 统一V6.2仍为20列电机Sheet。V6/V6.1原文件保留；泵、变压器Sheet及共享依赖保持。软件写N:P/Q/T，保留标准无指标与尚未计算的差别，统一固定批次说明区域及再导入。
4. Qt、Excel、历史详情共享输入契约和查表说明；单台合法终态自动存记录，混合Workbook只写一条批次记录。候选入口`--motor-candidate`显式开启，默认入口保持V6.1和既有两设备。

## 已取得证据与修复

- 主会话独立逐格比较源工作簿与新包：1290/1290格一致（108功率格+1182限值格）；不是重新进行PDF逐格审计。
- 内核/输入契约/数值Conformance定向20项通过；10条向量均通过locked Common Core JSON Schema检查。
- 独立执行一致性测试覆盖1149个数值限值的精确边界及上下偏移（3447例）和11个无指标阻断分支，共3458例无差异；测试自身遍历行/分支推导预期，不调用Calculator私有选表逻辑。这不替代上项源格核验。
- 真实三设备混合批量、结果再导入、输入未覆盖、单条MULTI批次记录，以及效率0.85输入错误不存记录的产品流3项通过。
- 电机Qt真实装配、条件字段和历史详情2项通过；既有变压器及Qt产品相关48项通过。
- 从`2adcef7e`提取旧软件源码，实际读取V6.2返回“不支持的模板身份”，未误解析。当前候选`--status`正确报告V6.2独立身份且ready=true。
- 电机Qt、4项产品流及架构边界最新17项通过；历史详情在默认未开启候选时也按已有快照显示中文类别/口径。1000×720首页与640×480电机表单离屏图像已检查并修正小窗口横向挤出；离屏验收不等于原生人工操作。
- Excel定稿：V6.2专项7项、统一adapter 7项、产品流4项通过；包含100/1000/10000行、两行直查/插值交叉再导入及既有样式保护。泵模板检查PASS。V6.2 SHA256为`12780374b2288f7bba706a3df614de6be362e1d46c247df511cd7d8480cf830d`。
- 完整回归初轮在实现期间运行，检出旧候选输入、发布资源夹具、Qt架构白名单和原“只变泵Sheet”的旧测试假设。已按新契约修复且定向复验；固定区只豁免A27:B34，其他Sheet/单元格保护不放宽。B3完整7项、架构/发布审计21项通过。全量最终结果以产品PR固定Head的Windows Core为准，不把初轮记作全部通过。
- 初轮完整结果为1158项、11项失败断言、3项错误、0跳过；相关修复逐项定向复验。末尾发现发布审计需区分默认V6.1与电机候选V6.2，新包追溯审计需识别真实工作簿格坐标而不能补造PDF页码。泵源码身份纳入共享device_types/evaluator_registry，因此同步源码指纹为`064c91cd…`；泵算法文件、标准映射、Golden、输入Sheet和历史快照不变，此变化不是泵业务规则调整。
- 末尾问题复验：发布审计及泵源码指纹13项通过；追溯审计4项通过（17包ID+定位完整，16包具页码；电机1182格保留真实工作簿定位）；R4结构16项、写回失败不得存批次记录1项通过。仅未接通Sheet有数据的真实工作簿拒绝生成成功批次1项通过。
- 独立复核修复：普通trace字典未显示依据；表1区间源文本导致插值右端误显示；历史详情改经Application契约；模板独立身份、说明页错误落点及退役旧文案；直接查表/插值再导入的显示格式。都要求针对真实Calculator和真实保存文件回归，不只检查构造的trace。
- `01b849d9`固定版本联合复验102项全部通过，失败/错误/跳过均为0；原生候选构建及资源审计通过，正常用户目录隔离启动自检exit=0、ready=true、V6.2身份正确，PE窗口子系统为2。原生人工功能验收仍待反馈。
- 同一版本Windows Core run 40167210953的unittest日志为1171项、OK，但步骤最终exit=1，不能认定CI通过。将PowerShell的stderr合并管道替换为独立子进程日志捕获，明确打印并原样传播真实进程退出码；用同时写stdout/stderr且分别返回0、7的命令验证均准确传播。完整门禁须以修订后PR最新Head结果为准，未删除或跳过测试。

## 证据限制

2026-10-25人工反馈修订（工作基线4103d6c3）：批次总结及历史详情复用每Sheet既有数量快照，逐设备显示六类结论台数，行数仅辅助；真实一行多台三设备及Qt投影25项通过。Owner补充频率数字/文本及极数任意正偶数输入，内核、Qt、V6.2同步修订，详见设计和EQP-STD-GB18613-009；修订版须重新验证。该展示工作不涉及中央公共Contract，输入适用边界沿用已冻结标准事实，锁和数据库不变。

CI run40168204528已确认不是简单日志误判：1171项OK后测试子进程返回3221226505（0xC0000409原生失败退出），须继续排查Qt/进程结束生命周期；不吞退出码、不以OK文本代替门禁成功。

本轮对新增电机Qt测试补齐窗口close/deleteLater/DeferredDelete清理，并在临时目录退出前关闭日志；本机相同Python 3.12系列下90项Qt/线程相关用例通过且进程exit=0。完整崩溃尚未在本机复现，远端重新验证前不声称已彻底解决；CI启用faulthandler保留后续证据。

输入反馈修订联合复验76项通过，fail/error/skip=0且进程exit=0，覆盖内核边界、Qt、V6.2、100/1000/10000行与保护检查。另补真实Excel→评价→结果文件→批次历史用例：频率5~120及10极为不在范围，3极输入错误只写T列原因、不写Q列等级；各台数分别累计。产品流6项通过。旧冻结资产、V6/V6.1及泵算法对基线diff为空。

本轮V6.2候选SHA256为`D009850015B4C5E132D9FF72D0DDB1649E67AFFEAA8F457B12187466C75CEC0E`，电机契约`motor-input.v2`；旧候选v1真实文件验证为明确拒绝并提示重新导出，未覆盖旧文件。WPS/Excel窗口捕获超时，本轮原生办公软件交互记NOT_RUN，不冒称通过。

2026-10-25 Owner完成d03fe1cf新版原生/WPS人工核验：分设备台数与批次历史均正确；H可填5~120、K无下拉并可填10/12正偶数、第104行追加、保存重开均正常。对应新版输入样例为5行8台：离心泵1台不在范围，变压器1台1级，电机6台（3级1台、不在范围5台）。候选ZIP SHA256为`a8f6b0685a8d5b3546a1c3ae699bb5e9f9198b35ded0d757530305d1ccd17d16`，普通下载目录下独立数据环境启动自检exit0/ready=true。QA-MOTOR-003按此范围关闭；不将旧版证据代替本次核验。

历史完整CI run40176754592：1178项OK后Fatal Python error: Aborted、进程exit3。新增Qt测试局部清理未彻底解决，QA-MOTOR-004继续开放；禁止据人工通过合并失败门禁。没有干净Windows或Sandbox，继续沿用Owner接受的本机隔离验证限制；不声明SUPPORTED、正式发布或Phase PASS。标准原文/扫描件/源校对工作簿不得随运行包分发。

后续CI修订仅涉及测试入口：仍一次完整unittest discovery，结束后检查活动QThread/QThreadPool及非daemon Python工作线程，再正常销毁Qt窗口和QApplication。活动工作线程/清理错误均返回失败，不kill、不跳测、不吞退出码。90项Qt/线程子集通过且全部清理阶段标记出现、exit0；临时失败/异常测试返回1；主会话另用真实活动QThread验证检查确实拒绝未退出线程。产品程序、模板和已获人工确认的d03fe1cf候选内容不变；完整CI仍待固定提交验证。

### 完整 CI 退出复验（2026-10-25）

固定提交 `00e277334daf559062b1a29799f0cbacf351d7ca` 的 Windows CI run `40180005924` 成功。完整 unittest 1178 项、971.987 秒，FAIL=0、ERROR=0、SKIP=0；Qt shutdown 标记到达 after，真实子进程退出码 0。工作线程已静止，显式销毁窗口及 QApplication；没有跳过测试、强制成功退出或掩盖活动线程。QA-MOTOR-004 按该固定版本证据关闭；后续审查修复提交的 CI 单独记录。

### PR33/34审查修复集成

已同步设计职责和QA登记、空类别缺失语义、无外部Decimal上下文依赖的包生成、源精度显示、口径阻断追溯与11条自动schema验证向量。Calculator内部版本v2.0.2；不改已验收频率/极数输入，不重算历史。产品定向56项通过，模板重放SHA不变，详见[逐项修复与复验](PR33_PR34_REVIEW_FIXES.md)。新提交完整CI另行记录，不以00e27733的成功替代。

### PR35第二轮独立意见核实（基线924c13a2）

Owner提供的三份材料受验Head均为00e27733；其中旧CI未完成的判断已过时（run40180005924完整1178项/exit0通过），空类别、pack builder与Conformance三项已由924c13a2集成上一轮修复。当前QA-MOTOR-004保持CLOSED。QA-MOTOR-001/002仍作为整体独立验收项OPEN，不据局部修复自行提升SUPPORTED或发布。

本轮沿用QA-MOTOR-002登记，不新建治理流程。已复现并局部处理的范围：M百分比格式与百分数点值契约冲突、未预建结果格的扩展行写回、无查表trace合法终态的批次来源、说明中W→kW换算的ambient Decimal依赖。不得自动把百分比底值乘100；不能让用户手工预建输出格；不为缺失历史补造来源或新增数据库结构。

其他意见的处理：

- IMPLEMENTED表示已实现的成熟度，不等于V1_SCOPE的发布范围。按记录快照补中文“已接入，尚待正式支持验收”，技术区域将该值标作开发状态，不改快照字段或发布支持状态。
- 频率文本是EQP-STD-GB18613-009已批准决定，不另行收紧为仅范围语法。设计明确表1—4非数值文本不能确认50Hz、按不在范围处理；表5/6仅留痕。没有新增标准解释。
- 旧MotorEvaluator仅剩motor_lv防御拒绝入口；高压/永磁共用算法保留。未发现可达的第二套GB18613低压判级路径，不因报告笼统建议删除其它标准代码。
- 候选入口仍显式开启；默认不开电机的既有自动测试和包资源审计继续保留。沙箱SQLite失败不作为业务正确性的通过或失败证据。

平台预检查：origin为adgo07/EquipEffi，master仍2adcef7e，工作树基线924c13a2，locked SHA保持ee5feb0cc34dbd99790500fadd0c4c932e202a20。Numeric Contract v1的精确入口、环境独立、全值比较和最小来源身份适用；不改Frozen公共契约。中央UI当前索引路由v0.2指南/产品规格/验收清单，仅落实中文状态说明，不借此重做页面。冲突分类LOCAL DEFECT，无中央Contract修改或数据库迁移；Knowledge capture无。

修复后主会话独立复验21项全部通过（新增真实文件/来源9项＋Qt 3项＋V6.2完整专项9项，FAIL=0/ERROR=0/SKIP=0，exit0）。覆盖100/1000/10000行、直查/插值、保存重开、再导入及固定输出区保护。子任务另完成既有电机产品流6项、统一工作簿适配7项（含变压器10000行）、变压器产品流2项、混合Application 6项与电机Application 7项，均通过；不把重叠测试累计成更多独立案例。

主会话首次56项联合测试为55通过、1错误：运行时正值writer补格导入column_number未同步完成，修正导入后上述21项独立复验通过。此中间失败如实保留，不用最后OK覆盖。compileall、diff检查通过；模板资产/Manifest、标准运行包、冻结源、中央锁均无diff。新提交将触发完整Windows CI，其结果不能套用旧Head。此前原生/WPS证据只保留既有实际范围，本轮不声称重新人工验收或干净Windows通过。

## 本次工程验收收口（2026-10-25）

Owner提供只读验收结论，确认PR35代码与工程验收已达到可合并程度，并授权结束Draft、按33→34→35合并。PR33已于a3e90d92、PR34已于32f7da5f合并；QA-MOTOR-001/002据独立意见、修复复验及CI证据关闭。此结论不提升SUPPORTED、V1发布范围或Phase PASS。

最新受验代码55d66f6d30df52e699a22f22bfb5da79e1da9178的Windows Core run40183041126成功：1191项，977.973秒，FAIL=0/ERROR=0/SKIP=0，Qt shutdown到达after、真实进程退出码0；Whitespace与Package/resource smoke均通过。此节取代前文“新Head CI待结果”的当前状态表述；后续本次收口提交只修改QA/实施记录/TASK_STATE，不修改任何运行代码或资产，运行验证证据继续锚定55d66f6d。

交付要求：必须从PR35最终合并代码重新构建候选ZIP，并单独记录新包SHA、启动、批量输出及历史打开的实际检查。旧d03fe1cf候选不含本轮修复，不作为本轮交付成品。其Owner原生/WPS人工证据继续保留于原版本，不声称本次只读验收重新操作了窗口。最终候选检查不冒充干净Windows或正式发布；无干净Windows限制沿用已接受决定。构建清单/自检结果为产物旁车数据，不新增验收文档。


## 三标准正式配置的源指纹修复（2026-10-28，PR #37）

主会话回传0967694的完整Windows CI run40535623955：1228项、803.406秒，唯一失败为泵受审源码指纹常量未随共享注册元数据更新，Whitespace通过；此处不把失败CI登记为通过。

独立按现有12文件、路径加NUL分隔、CRLF规范为LF的原规则对比已发布e140283与0967694：旧聚合值为`064c91cd346d6aff9c522f01c6ca3422392391807af6054cca93b6e574d56da0`，新值为`9877ee571463ade9169f48a40ec1dbcece6ef5b5e1fc6eed4b22dfaa196ba092`。唯一变化文件`domain/evaluation/evaluator_registry.py`仅将GB18613适配器的support_status由IMPLEMENTED提升SUPPORTED，符合本轮Owner授权；它被既有泵源码身份清单覆盖，因此泵来源身份也改变，不代表泵数值算法变化。

清单其余11项逐文件字节一致（均相对`src/equipeffi/`）：`application/services/centrifugal_pump_analysis_service.py`、`application/result_projection.py`、`domain/common/enums.py`、`domain/common/models.py`、`domain/evaluation/decimal_math.py`、`domain/evaluation/device_evaluators.py`、`domain/evaluation/device_types.py`、`domain/evaluation/evaluators/pump.py`、`domain/evaluation/evaluators/shared.py`、`domain/evaluation/grading.py`、`application/services/pump_release_gate.py`。逐文件规范化SHA与唯一差异保存在`outputs/pr37-pump-fingerprint-20261028/source-fingerprint-review.json`。

最小修复仅更新pump_calculator_version.py常量；不删注册依赖、不改散列规则、业务算法、Frozen/Canonical/Golden、模板、迁移或锁。新增真实隔离数据库测试：新记录保存新版本；旧064c91cd版本的顶层字段、references及完整快照重开均不改，不调用evaluate，重开前后数据库SHA相同。

验证命令：`.venv/Scripts/python.exe tools/run_test_log.py outputs/pr37-pump-fingerprint-20261028/targeted.log .venv/Scripts/python.exe -m pytest -q tests/unit/test_simplification_c_service_integrity.py tests/unit/test_pump_numeric_contract_v2.py tests/unit/test_phase3_golden_and_boundaries.py tests/unit/test_phase4_fingerprint_decoupling.py`。TEMP/TMP置于该outputs目录下temp，QT_QPA_PLATFORM=offscreen；56项、134子测试通过，10.32秒，真实exit0。包含既有受审指纹断言、数值契约和Approved Golden回放，不删除或降低原断言。

该修复属于生产来源元数据变更，之前构建的0.2.2候选须按新提交重建；新Head完整CI、合并和候选交付由主会话独立复核后推进。本轮仅本地提交，不推送或发布。125%缩放及干净Windows未验证的限制保持。

主设计会话随后对07738c5独立复核：12文件逐项比较仅共享registry的电机支持状态一行变化，重新散列与新常量一致；独立运行`test_simplification_c_service_integrity`、`test_pump_numeric_contract_v2`、`test_phase2_approved_golden`、`test_three_standards_release`，35项、47子测试通过，19.94秒，真实exit0。日志为`D:/project/设备能效软件/EquipEffi_build_0.2.2_20261028/independent-fix-review.log`，逐文件指纹证据为同目录`fingerprint-review.json`。此补记仅追加既有记录，代码保持07738c5；新Head完整CI和候选重建由主会话继续，不据定向复验声明完整CI通过。
