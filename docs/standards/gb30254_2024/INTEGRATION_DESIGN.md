# GB 30254—2024 高压电动机接入设计

日期：2026-10-29。状态：**Stage B 设计稿；仅设计，不实现、不提升支持状态。**

本文依据已获Owner批准的[A.3主映射](STANDARD_MAPPING.md)、配套6表数据和[2026-10-29映射确认记录](../../governance/motor_mapping_confirmation_20261029.md)，确定软件接入方案。本文不改映射、数据工作簿、标准问题台账、`V1_SCOPE.md`、代码或模板资产。`motor_hv` 仍按[V1_SCOPE](../../../V1_SCOPE.md)记录为 `POST_V1`；本稿不构成Windows V1范围变化、实现授权、Stage D验收或 `SUPPORTED` 决定。

本次明确采纳Owner产品决定：软件不负责测量或验证试验报告，按用户录入的额定效率值（1～100百分数点值，含端点）与标准限值比较；额定电压输入单位为V。该输入约定不把标准中的“规定测试条件下的实测效率”改写为“铭牌效率等同于实测效率”，也不代表软件验证了试验方法或完整认证符合性。

## 1. 基线与平台预检查

- 本仓 `origin` 已核对为 `https://github.com/adgo07/EquipEffi.git`。工作树分支为 `codex/motor-rated-input-20261029`，基线 `cc0b0735fc3636f1c2bad34645e09e7db0d6e45e`；`git fetch origin` 成功，`origin/master` 与该基线一致。工作区原有未跟踪 `artifacts/` 未读取、未修改。
- `platform-lock.json` locked central SHA：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`。本设计不升级锁、不改公共Contract。
- 按中央当前已合并文件读取：`docs/GUIDE_INDEX.md`（main blob `658b3df9569e2956ff7b9060dab0d1bd0fa2bd58`）、`docs/governance/STANDARD_DEVELOPMENT_GUIDE_V0.1.md`（main blob `ac80a956e5431113509d06d2ca23982165a61558`）、`docs/governance/PRODUCT_DELIVERY_POLICY_V1.md`（main blob `79b11e0817ed7a4dbf113d53e5cb4a06f99b44de`）。适用要求：Stage B须确定Canonical Input、分类、Rule、Calculator输入输出、结果、Record、UI、Excel、测试及追溯；Excel为适配器，不能形成第二套算法；Stage D前不得宣布正式支持。
- 按 locked SHA 读取 `contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md`（文件blob `58469ccfaa690fe19ff16abf6dda8e81ca060e07`）和 `contracts/numeric/NUMERIC_PROFILES_V1_FROZEN.md`（文件blob `39c9195bb2ecbb0b110afed5283f748b3b6f87ed`）。适用MUST：业务十进制值使用确定、可复现的十进制语义；输入不得经未声明的二进制浮点路径变成正式值；每个权威计算Scope声明并传播Numeric Profile；默认全值精确比较，不作隐式预比较修约或epsilon；结果保留Profile与Calculator/Rule追溯。MUST NOT：把泵Decimal50 / `ROUND_HALF_EVEN`作为电机默认；让容差或显示修约改变等级比较。
- Unit Contract当前为DRAFT；本地明确V、kW、Hz和极数/转速字段，不声称中央单位Contract已冻结。电机精确十进制Profile属于`ALLOWED PROJECT DIFFERENCE`。本任务不涉及中央公共语义，未发现`CENTRAL CONTRACT GAP`。
- 相关Standard Issue：`EQP-STD-GB30254-001`（RESOLVED，GB/T 755效率容差仅作知识）和`EQP-STD-GB30254-002`（RESOLVED，按表/极数分支判定可用阈值）。设计沿用这两项已批准软件口径，不改变解释、不改台账。

## 2. 已确认的标准分支与软件结果

### 2.1 显式输入与Canonical Input

标准选择和电机类别由F列受控类别显式选择；不从型号、冷却方式或电压反推“这是GB 30254”。本分支稳定类别ID为`gb30254_cage_induction`；F同时保留现有`OTHER_CATEGORY`和`UNCERTAIN_CATEGORY`选项，这两项不路由到GB30254表，沿用现有类别结果语义。只有明确的标准分支ID映射到`standard_id=GB30254-2024`；结果快照仍显式保存标准号和版本。

|Canonical字段|类型/单位|必要性与规则|
|---|---|---|
|`rated_voltage_v`|十进制词法，V|必填；只接受3000、3300、6000、10000 V四个表定电压值，不把相邻电压四舍五入到表组，也不把3.0/3.3等kV数值猜作V。|
|`rated_frequency_hz`|数字或原始文本（包括5～120等范围），Hz|必填；输入经同一严格解析器规范化为Hz数值后必须精确等于50，否则为不在本标准适用范围。不能因显示格式或字符串猜单位。|
|`cooling_method`|受控IC代码|必填；只接受映射所列精确代码。|
|`rated_output_power_kw`|十进制词法，kW|必填；必须落入已选表/极数组合的有效范围，不能以标准总范围代替具体分支表值。|
|`poles`|正偶数整数，极|必填；按表列极数路由。没有该极数列或没有有效阈值时不借其它极数。|
|`rated_efficiency_pct`|十进制词法，百分数点值|必填；软件输入防误填范围为1～100（含端点）；例如94表示94%，0.94不自动乘100。|
|`quantity`|正整数，台|Excel行启用后必填且>0，遵循现有批量合同。|

通用设备名称、型号、安装位置、备注和照片沿用现有设备输入，不参与选表。**不新增试验口径字段、测量值字段或试验报告确认步骤**；标准试验方法作为依据说明，不在本软件中执行或验证。

### 2.2 确定表号

按额定电压、冷却代码组合确定表，再按极数选列，最后按额定输出功率选行。表号和极数是同一项已选类别下的唯一结果；禁止跨表、跨极数或跨冷却组补值。

|表|额定电压|冷却代码|表列极数|功率范围/解释|
|---|---|---|---|---|
|1|3000、3300、6000 V|IC01、IC11、IC21、IC31、IC81W|2/4/6/8/10/12|各极数按表1实际有效端点；部分大功率格为“—”。|
|2|10000 V|IC01、IC11、IC21、IC31、IC81W|2/4/6/8/10/12|按表2实际有效端点。|
|3|3000、3300、6000 V|IC611、IC616、IC511、IC516|2/4/6/8/10/12|按表3实际有效端点。|
|4|10000 V|IC611、IC616、IC511、IC516|2/4/6/8/10/12|按表4实际有效端点。|
|5|3000、3300、6000 V|IC411|2/4/6/8|没有10/12极列。|
|6|10000 V|IC411|2/4/6/8|没有10/12极列。|

表1～4功率起点为200 kW，但各极数的末端不同；表5末端3150 kW，表6末端2800 kW。实现应从映射配套数据包读取表行与破折号身份，不在UI/Excel常量里复制阈值。

### 2.3 插值、比较与结果状态

仅在同一表、同一极数、同一等级的相邻有效功率端点之间线性插值。表列功率点直接取源值。公式为 `T(P)=T(Pa)+(T(Pb)-T(Pa))×(P-Pa)/(Pb-Pa)`；分母为正。不能跨“—”插值、不能外推、不能把功率区间当端点、不能用标准总功率范围推造缺失的极数值。

三个等级分别比较，按1级→2级→3级选择最高满足等级：`η≥T1`为1级，依次为2级、3级，低于T3为`未达3级`。等于阈值即满足。GB/T 755容差不下调阈值，不加epsilon。

沿用本仓通用结果用语及既有结构化状态，不新增电机专属枚举：明确不属于标准适用范围、或者按002没有对应表/极数/有效阈值时显示`不在范围`并附具体原因；必要类别、数值或冷却分支缺失时显示`无法判定`并列出缺项；非法数值显示`输入错误`，不生成正式等级或Record；包读取、计算、数据库等执行异常进入失败通道，不伪装成`无法判定`。其他类别/不确定类别分别沿用现有类别语义。显示用语不替代底层状态、原因码、保存资格或异常状态。

## 3. Numeric Profile与精确比较

建议给GB 30254单独声明 `numeric_profile_id=EQUIPEFFI_MOTOR_HV_EXACT_LINEAR_V1`、`profile_version=1.0.0`、`numeric_contract_version=v1`、`authoritative_scopes=[motor_hv]`。可与现有GB 18613 Profile复用“有限十进制→精确整数尺度运算”的数学实现，但不共用Profile ID，不暗示计算Scope相同。

|Profile能力|确定值|
|---|---|
|`representation`|Qt原始十进制词法；Excel适配器须从可靠的十进制词法入口生成同一Canonical Input。权威计算使用精确整数尺度/有理数表达，不经Python `float`。|
|`working_precision`|`exact_for_business_operations`；有限十进制输入和表值转为整数系数＋十进制尺度，插值以精确分子/分母表示。|
|`rounding_mode`|权威比较不舍入（`none_for_business_comparison`）。|
|`comparison_policy`|`full_value_exact`；用正分母交叉相乘比较输入效率与精确阈值。|
|`explicit_rounding_policy`|无业务预比较修约。|
|`transcendental_policy`|`not_applicable`。|
|`tolerance_policy`|无业务epsilon；GB/T 755容差不参与等级判断；仅可在数值Conformance中使用用途明确的测试容差。|
|`display_policy`|直查值沿用标准精度；插值阈值可沿用现有电机展示投影显示2位小数、`ROUND_HALF_UP`，但显示值永不回流比较。|

对插值阈值保留约分后的`numerator`、`denominator`（分母>0）、单位`percent_point`、两端源格及未舍入表达。比较`η≥n/d`时使用`d×η≥n`的等价精确关系。Profile、Calculator/Rule版本和表数据包身份必须进入结果引用。Profile传播、全局Decimal上下文扰动、Python float/非有限值拒绝、精确等号边界、分子分母往返及显示隔离均需纳入该Profile自己的Frozen Numeric Conformance Vector；不能用泵Conformance替代。

## 4. Qt、Record与Excel接入

### 4.1 Qt与业务链

Qt通过明确选择`GB30254—2024 高压三相笼型异步电动机`进入本标准；条件字段依次为额定电压(V)、频率(Hz)、冷却方式、功率(kW)、极数、额定效率(%)。应用层把已规范的Canonical Input交给单一Motor Rule/Calculator，计算后共享既有结果投影。标准生命周期提醒不得改变能效等级。输入标签使用“额定效率”，简要说明软件不测量/验证试验数据。

单次合法Qt评价沿用当前不可变Record语义。保存的输入快照至少保留原始输入词法、归一化值及单位；结果快照保留标准/表号、表包哈希、Rule/Calculator版本、Numeric Profile、三个阈值精确结构、源格/插值端点、比较结果与显示值。读取历史只按快照展示，不重新评价、不补造来源，不做数据库迁移。

### 4.2 同一Workbook中的电动机Sheet

V6.2实物已只读检查：工作簿含18张Sheet；“电动机”为20列A:T、100个数据行（表`TblMotor` A3:T103），模板身份`equipeffi.device-efficiency.V6.2`，该Sheet contract为`motor-input.v2`。其G列单位为kV，I列为“实测效率口径说明”，M列为“额定输出功率下实测效率”。**这些V6.2字段和语义必须原样读取，不能按新规则把kV当V、把旧实测效率改称额定效率。**

另只读核查了当前GB18613候选V6.3：仍是18张Sheet；“电动机”A:T、`TblMotor` A3:T103，模板身份V6.3、Sheet contract `motor-input.v3`。F当前只有GB18613受控类别，G为V，H为Hz，I是“历史字段（已停用）”，J为kW、K为极数、L为“铭牌标称最高转速”、M为额定效率，配置Sheet下拉只覆盖GB18613。**本轮不修改或扩展这个GB18613候选**；共享Sheet是后续模板设计建议，不代表V6.3已支持GB30254。

产品设计决定继续“一类设备一张电动机Sheet”，不因增加GB30254拆Sheet。未来模板沿用A:T二十列，由F列受控类别显式选择标准/分支并唯一决定`standard_id`和表路由，绝不按电压猜标准。统一字段为：A:E通用设备信息；F标准/电机分支；G额定电压(V)；H额定频率(Hz)，数字或原始文本（包括5～120等范围）；I受控冷却IC代码（仅高压分支填）；J额定输出功率(kW)；K极数；L按类别表达额定转速或铭牌最高转速（GB30254留空）；M额定效率(%)；N:P软件回写1/2/3级阈值；Q软件结论；R照片；S备注；T评价说明。F类别决定I/L是否必需及字段含义；H为非50 Hz数值或范围文本时对本标准为不在范围；不增加试验口径/报告核验字段。

当前并行的GB 18613工作只实现/修订`motor-input.v3`的V6.3候选。本设计不把GB30254类别、冷却下拉、Rule、模板字段或Excel处理接入该候选。未来统一模板固定采用V6.4与新Sheet contract `motor-input.v4`，在该版本扩展F类别并定义I冷却、H频率和L转速的类别条件；不通过只扩展配置来伪装兼容。V6.2仍按`motor-input.v2`旧单位/口径读取。新软件不能将V6.2数据转给GB30254，旧软件遇到未知的新contract/新分支须拒绝或逐项标明未处理，不能静默跳过后报告成功。

Excel类别由“配置”Sheet登记为机器可读字段/下拉契约，并机械校验与Application输入契约一致；配置变更不能改变Calculator规则，发现不一致则Gate失败。输入工作表不放业务公式、效率阈值公式或自动判级公式；Reader完成数据规范化后调用与Qt相同的Application/Calculator，Writer生成新结果Workbook，不覆盖原始输入。每个Workbook批次沿用一条`batch_record`，逐设备结果在输出Workbook；不为每行创建单台Record。扩展容量沿用现有统一机制，Stage C须实测少量、100、1000、10000行及Excel/WPS追加行、下拉、保护、保存重开。

## 5. 版本兼容与历史

|软件/模板|处理方案|
|---|---|
|新软件 + V6.2 / `motor-input.v2`|按旧列名、kV单位及“实测效率口径说明/额定功率下实测效率”语义读取；仅GB 18613旧输入可由该Sheet评价。没有GB30254标准标签，禁止猜标准或重解释。|
|GB18613-only V6.3候选|保持原候选不动；没有GB30254类别/分支的实现或模板入口。|
|未来新增标准的统一模板|采用V6.4 / `motor-input.v4`，在同一“电动机”Sheet扩充F受控分支与配置契约；使用V单位和额定效率点值，不能沿用V6.2字段语义。|
|旧软件 + 未知/扩展模板契约|必须拒绝新contract或准确列出未处理内容，不能返回“全部评价成功”。|
|已生成的历史Record/batch_record|保留创建时的输入和结果快照、单位、表包和Numeric Profile；不自动迁移、不重算、不覆盖旧展示。|

## 6. Stage B测试与候选案例

下列均是主映射候选的Stage B测试设计，不是Approved Golden或已运行生产测试。测试期望应独立来自主映射、源工作簿和已确认Issue，不从Calculator反推。

|覆盖|映射候选/期望|
|---|---|
|路由六表|主映射C01、C08～C13；验证3/3.3/6kV共享表组、10kV切表及IC01/IC611/IC411组，不能仅按电压路由。|
|三级阈值与等号|C01～C05：94.0/93.1/92.3等典型值；`T−0.001`、`T`、`T+0.001`分别检验等级变化；容差不抬升、epsilon为零。|
|线性插值|C06在200/220kW间产生94.05/93.20/92.40，精确比较不先显示舍入；C07表列点直接读取。|
|分支范围及横杠|C14～C20、C24～C25：表列末端、横杠、无10/12极列、无有效端点、不得借表/极数或外推；C19依002为`不在范围`。|
|适用条件|C22、C23：频率不是50Hz/工作制不符不能显示为能效低；防爆、立式本身不排除。|
|输入校验|C26、C27及效率0.94/94、0/1/100/100.001、缺字段、负功率、非有限数值、错误单位；V字段不得把kV输入猜作V。|
|异常通道|表包缺失/损坏、解析器异常、持久化失败分别检查执行失败提示及Record/batch_record边界。|
|Qt/Excel一致性|同一Canonical Input横向核对两入口的标准分支、状态、等级、未舍入阈值、结果原因和历史快照；输出Workbook不覆盖输入文件。|
|Numeric Conformance|Profile声明/传播、入口十进制词法、无float路径、精确插值、环境上下文独立、阈值等号、展示隔离、Profile不匹配拒绝。|

## 7. 设计决定与实施边界

|事项|本设计决定|
|---|---|
|类别与标准路由|共享同一“电动机”Sheet；F列受控类别显式包含标准号/分支，`OTHER_CATEGORY`和`UNCERTAIN_CATEGORY`保留为不路由到本标准的现有类别。立式/卧式不另设字段，映射已将其纳入范围且不参与选表。|
|输入单位与频率|G统一V，M统一额定效率百分数点值1～100；H允许数字或原始文本（包括5～120等范围），数字按Hz核对，本标准只接受50；非50数值或范围文本为不在范围。|
|字段布局|I为受控冷却IC代码且仅高压类别必填；L按F类别解释转速语义，本标准留空；不加试验口径/报告核验字段。|
|模板版本|新标准进入V6.4 / `motor-input.v4`；当前GB18613-only V6.3候选不扩展，V6.2保持旧单位与字段口径。|
|额定效率产品输入|Qt与Excel统一标“额定效率(%)”，说明该值由用户输入，软件不测量、不核验报告；不改变映射对标准“实测效率”的原文记载。|
|Issue状态|`EQP-STD-GB30254-001/002`继续RESOLVED；本设计不改既有标准解释或台账。|

## 8. 后续阶段顺序

1. Stage C开始前核查相关根台账，保持001/002当前决定与映射解释一致；如实现暴露新的标准解释问题，先登记再定规则。额定效率是已明确的软件输入约定，不将其登记为标准原文修订。
2. Stage C审计已存在的motor metadata/evaluator资产，明确哪些是当前权威、哪些仅是兼容/开发资产；按A.3映射和6表数据生成/校验运行时规则包，落实独立Motor Numeric Profile及Conformance，不改Mapping/数据工作簿。
3. 在共享Calculator/Rule后接Application，再接Qt、不可变Record和Excel Reader/Writer；维持一条业务计算链，不按表复制Algorithm。
4. 对映射候选逐项形成Golden Case Candidate和单元/集成/Excel/Windows用例，保存新历史记录与快照兼容证据。
5. Stage D独立核验标准来源、Mapping、Issues、Rule、Calculator、Conformance、Golden、UI、Record/历史、Excel、Windows交付与Traceability；未通过前保持未支持状态，不正式发布。

**验证记录：**本任务只读检查V6.2工作簿结构并编写Stage B设计。生产测试、Calculator Conformance、Qt/Excel运行、Windows/WPS验收均为`NOT_RUN`。Knowledge capture：无。
