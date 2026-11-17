# 锅炉GB24500 Stage C实施记录

基线 ff071674e8529b85e79a524d6816f024d27265cd；分支codex/boiler-product-20261117。独立clone核对origin为adgo07/EquipEffi，fetch成功，远端默认master且HEAD同步。根checkout及设计worktree保持原状。

中央locked SHA ee5feb0cc34dbd99790500fadd0c4c932e202a20，已按锁读取Architecture V2.1、Numeric v1、Profiles及Conformance。中央origin验证通过；ACTIVE指南按远端main 829853a943c421e0b9864d84f3d94970d2ddf688的GUIDE_INDEX读取Standard Development、Product Delivery及UI规格/指南/验收清单。

适用MUST：精确数值入口、声明并实际消费Numeric Profile、全值比较、无损快照、同核适配、不可变历史。MUST NOT：float未声明进入权威链、业务epsilon、展示回写、第二套Excel算法、旧历史重算、自动升级锁。分类为ALLOWED PROJECT DIFFERENCE（锅炉独立精确查表Profile），无中央Contract变更；无数据库迁移。

## 2026-11-17：锅炉Stage C实施授权（19列最终方案）

Owner已批准统一工业锅炉A:S共19列（覆盖PR48旧25列稿）：F显式类别含形态/燃烧方式/冷凝基准，G燃料，H对应额定容量，I额定压力，J低位热值，K挥发分，L唯一被评价热效率；M:O等级限值，P结论，Q照片，R用户备注，S自动备注。低热值生物质O条件作为设计限定值输入，其余分支输出；禁止残留输出充当输入。详见本轮[实施记录](docs/standards/gb24500_2020/PRODUCT_INTEGRATION_20261117.md)。

授权范围为固定式水介质蒸汽/热水已确认分支、共享Application/Qt/Record及V6.7批量和Windows未发布候选；有机热载体未开放，混烧合法无法判定。001已答口径及002保持，不改主映射/源表/Approved Golden/中央锁/migrations，不提升SUPPORTED、不合并或发布。QA-BOILER-001继续OPEN。

## 待执行证据

实现、79源值复核、业务边界、适配器/记录、容量、原生Qt/Excel、候选构建及最终CI将在执行后记录实际结果。未执行项不得标通过。Knowledge capture：无。

## 实施中Owner补充决定

2026-11-17：设计限定值必须大于0；允许在S自动备注追加机器可读逐行来源标记，保持19列与现有数据库。已有Workbook只含批次标记，逐行证据原仅存batch_record，无法可靠识别O输出残留；本轮按明确授权补充最小逐行来源。核对原类别/热值/输入、O来源及输出，条件改变或来源不明要求补充设计限值；标记不是业务算法或标准真值。

## 实现与来源边界

- 新Domain为`domain/devices/boiler`；GB24500独立精确十进制→有理数Profile，无插值、D/Q换算、隐式修约或业务epsilon。四表值只从固定SHA工作簿派生；原件、映射、001/002已有解释和Approved Golden保留。
- Qt/Excel调用同一BoilerAnalysisService；L是唯一被评价效率，设计或测试资料采用同一比较规则。低热值生物质单独接收`design_limit_pct`，保留原表三级值、Owner设计下限来源和两个比较结果。
- 有机热载体未开放：support层明确提示且不可形成单台Record；混烧是合法无法判定且可保存。有效范围排除先于无关参数缺失。系统/资源/保存失败分别反馈。
- 现有快照容纳原词法、规范精确值、阈值、限定值、规则与包身份；不改schema/001/002，旧记录只读不重算。
- V6.7只读派生V6.6，原18Sheet顺序保留；其余设备Sheet及旧XF原索引与定义保持。锅炉数据区退出业务公式；全列解锁输入/全范围Validation/all-row Reader，便利数量合计覆盖D4:D1048576。
- O因条件输入需解锁；普通分支所填O不参与业务真值，软件覆盖为正式表值。低热值分支O原输入的XML词法/类型/样式保持，不能清旧结果时误删；S记录来源。可编辑不等于普通O能改变算法。
- S标记含原设备、类别、额定参数、热值、效率、设计输入与O输出及完整性摘要。相同上下文且原O确为设计输入可重导入；条件变化或普通输出残留不采纳。改O补录了不同于旧输出的明确值可接收；需要沿用同值而无法区分操作时，提示使用空白V6.7补录。标记缺失/损坏而行有结果或工作簿有结果标记时，保守要求补录。此摘要防意外损坏，不宣称防恶意篡改。
- 照片Q、备注R不改；结果ZIP只补丁已连接Sheet结果及既有批次说明，保留其他部件。主结论与限定值辅助数量分开，批量只evaluate、只写一条batch_record。

### 旧资产与兼容差异

旧`domain/evaluation/evaluators/boiler.py`和`resources/standards/boiler.json`定为KEEP/VERIFY；本轮未删、未复用其正确性资格。既有generic EvaluationService/JSON兼容表面仍走旧锅炉实现，登记REGISTERED_DEVIATION，disposition为保留历史兼容入口、当前锅炉产品路径使用新服务；后续专项决定其迁移，不把旧电加热3级与新产品混同。未开放有机热载体继续保留001未答边界，程序不自动改问题台账。

### 当前自动化证据

首轮核心7项通过；追加固定Numeric向量后另行运行。首轮产品6项中4通过/2错误（过严Workbook公式Gate及测试历史接口名）；修复后第二轮24项中23通过/1测试清理调用错误；第三轮24项全部通过，96.818秒。空压机/入口/Numeric回归26项通过，28.341秒。旧失败日志保留于outputs/boiler-tests-20261117，不以历史测试代替最终Head门禁。

容量实测1/100/1000/10000行全部通过，各一条batch_record和零单台Record，数量分别2/200/2000/20000；生成及评价时间6.689/7.720/16.171/111.829秒。输出重导入来源、输入SHA不变、模板结构复验均通过。此为本机自动化，不冒称原生Excel或干净Windows/125%DPI。

小数O复验：修正Decimal来源标记序列化路径，并直接读取数值格XML原词法（含整数尾零）；27项定向/架构复验全部通过，105.214秒。新增90.5数值O保存重导入及O单元格XML不变断言；未改业务阈值、等级或设计限定值解释。


## 收口与复核入口

同一实施PR为[#49](https://github.com/adgo07/EquipEffi/pull/49)，固定Head以PR实际head SHA及对应Windows Core run为准；最终门禁状态与候选文件身份在该PR补充。PR48旧25列设计未作为实现来源。本报告不宣布独立验收通过。

V6.7交付审计已同步：原“未接通Sheet”回归改用仍未接通的热处理Sheet，三设备与空压机旧兼容路径继续覆盖；新锅炉Sheet加入当前默认模板、包资源及纯标准库wheel烟测，不修改其他设备业务阈值或快照。发布审计22项复验全部通过（31.978秒）；补齐混烧可选范围参数提示后核心/模板9项通过（2.302秒）。原生验证没有取得证据的项目继续NOT_RUN，不用离屏或EXE --status替代。

最终小数O容量复验：1/100/1000/10000行全PASS，分别7.256/8.671/17.481/122.238秒；数量2/200/2000/20000，均一条批次、零单台记录，输出可重导入，输入SHA与O事实保持。原始实测JSON及全部过程日志位于本机outputs/boiler-tests-20261117与outputs/boiler-capacity-final-20261117；工具`verify_boiler_capacity.py`可复核，不将本机自动化等同Excel手工填写证据。

原生验证委派给用户指定gpt-6-astra/low子代理。首次Qt启动发现装配参数遗漏，现已修复并有离屏回归；Excel启动工具调用卡住约23分钟后中断，未获得Workbook操作证据。Qt原生交互仍在按最小隔离案例补查；Excel/WPS编辑、保存重开及真实125%DPI、另一台干净Windows在无实际证据前均NOT_RUN。正式支持、发布与独立验收保持未执行。

Windows候选使用隔离Python3.12.14/PySide6 6.12.0/PyInstaller6.22.3构建，不更改项目版本或创建Release/标签。沙箱内DLL/pip注册表访问失败已保留日志；隔离环境安装与候选构建通过经自动批准的沙箱外执行完成，不操作真实用户记录。过程中的中间候选不得作为最终Head交付；最终文件/hash由本PR身份清单列出。


补充来源身份与适配矩阵：25个Qt离屏／Excel类别及特例投影全部一致（含两种低热值双结果、有机热载体未开放、混烧及其他／不确定类别）；原生GUI资格另计。锅炉Canonical新增`text eol=lf`且派生工具显式LF输出，防止checkout换行改变文件身份；不改78表值/97或任何规则。新建autocrlf=true/false checkout字节与Git blob一致，文件SHA均为696c469873cca486b185422cc3dde60d2fa5663b5ec3080e73a04015e04debf5，核心与新建checkout共9项通过（2.052秒）。该文件哈希取代过程CRLF副本身份；旧历史不重写。

本地初次全量诊断与实施收口修改发生交叠，其失败/错误与过程日志保留，不作为固定Head通过证据；最终完整门禁只采用本PR固定Head的干净Windows CI。最终代码身份、候选资源与测试状态以PR及本机`delivery-manifest.json`核对，不引用任何旧候选或中间Head冒充最终运行。


原生Qt补查事实：用户指定astra/low子代理通过隔离脚本及沙箱外可见启动，窗口清单已确认原生Qt窗口；读取窗口时Computer Use返回“app approval timed out”，未取得截图或表单交互，所以仅“成功启动”有证据，业务操作仍NOT_RUN。清单暴露标题拼接重复锅炉字样，已改为只处理末尾标题后缀，未改业务逻辑。Excel启动工具此前长时间卡住，原生Excel编辑/保存/下拉仍NOT_RUN。不存在以offscreen代替原生验收的声明。

末轮边界复核：电加热追溯中的效率基准明确为NOT_APPLICABLE，不给无关的低位热值标记；可搜索类别框编辑自由文本时立即标记旧结果过期，非法类别不生成记录。等级/限定值算法和模板字节不变；核心、Qt与模板11项定向通过（3.800秒）。
