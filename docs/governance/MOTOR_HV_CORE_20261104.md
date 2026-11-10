# GB 30254 高压电机候选内核实施记录

日期：2026-11-04。状态：Stage C第一段，完整产品接入未完成，未作Stage D验收。

## 授权与边界

当时Owner要求暂跳过PR #41验收并继续后续，随后确认“先高压电机，再永磁电机”。本轮按已存在的[接入设计](../standards/gb30254_2024/INTEGRATION_DESIGN.md)实现六表候选内核。PR #41随后于2026-11-04由Owner确认验收并合并（`f93525d675a3122f6af43aadacc95fed7c759ce9`），其Head的Windows Core/Whitespace门禁41642255236成功。本分支已rebase到该基线。Phase 8仍为EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE；不进入Phase 9。高压、永磁范围和支持投影不变，未正式发布。

## 平台预检查

- 实际origin：`https://github.com/adgo07/EquipEffi.git`；默认分支master；初始开发基线`e596ee33546ce340b01e0bb83a76c5fd6d782c6c`，复核修订后基线`f93525d675a3122f6af43aadacc95fed7c759ce9`。独立worktree分支`codex/motor-hv-core-20261104`，开始时干净。常规fetch无输出挂起后中断；定向`git -c fetch.recurseSubmodules=false fetch --no-tags origin master`退出0，`ls-remote --symref origin HEAD`及origin/master核验一致。原工作树用户改动未处理。
- locked central SHA：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`，不升级。
- Frozen读取：Numeric Contract v1、Numeric Profiles v1、Numeric Conformance Vector v1。遵循确定十进制语义、独立有效Profile、ambient independence、全值精确比较、显示/比较隔离、拒绝未声明float入口、Profile/Calculator追溯。测试沿用已校验的Frozen Common Core Schema，SHA-256 `bf7e5a4c2723376d3b20921c12298dbd42ab7e4ca46326b78df6bdf9697d4629`。
- ACTIVE依据：中央GUIDE_INDEX路由的Standard Development Guide，按Stage A→B→C→D推进；未以实现完成宣称SUPPORTED。未涉及公共Contract变更；独立exact rational Profile分类为`ALLOWED PROJECT DIFFERENCE`，无中央Contract修改需求。
- 相关Issue：EQP-STD-GB30254-001/002（RESOLVED）及EQP-STD-MOTOR-009。沿用容差仅作知识、无有效表分支不在范围、额定效率/V输入的软件决定；没有新解释或Approved Golden变更。先登记QA-HV-001，再实施。

## 资产与实现

|资产|处理|
|---|---|
|A.3主映射及六表校对工作簿|KEEP，只读，不重存；只作为经批准的本标准事实来源|
|旧`domain/evaluation/evaluators/motor.py`及device registry设备名|KEEP，既有开发/兼容资产；未作为本轮六表正确性Oracle，未替换或删除|
|GB18613独立Calculator、Profile、V6.3|KEEP，不修改|
|本轮候选包|新增到`specs/equipment_efficiency/standards/gb30254_2024_candidate.json`，未注册到产品标准目录、不随resources标准包提供|
|新Calculator|`domain/devices/motor_hv`，调用方明确传入候选包；未接Application/Qt/Excel|

构建器`python -m tools.build_gb30254_motor_pack`通过zip/XML只读源格，复用既有XML读取机制，拒绝公式、源SHA变化、清单不符和显示格式隐含修约。204行、3093个效率数值、285个明确破折号；保存源格、XML数值词法和单元格显示精度。不是重新宣称标准PDF逐格独立验收。

计算按明确类别、电压、冷却、极数选表列；只在同表/极数/等级的相邻有效行插值，横杠、缺列和越界均不补值/外推。独立`EQUIPEFFI_MOTOR_HV_EXACT_LINEAR_V1`使用精确有理数，拒绝float与非有限输入，不受Decimal全局上下文影响。等级比较无epsilon、无预舍入；直接阈值保留原表精度，插值展示两位小数。结果记录包SHA、表号、极数、端点源格、精确分子分母、Profile和Calculator版本；破损包或Profile不匹配抛执行异常。

## 资源基线

|资源|SHA-256|
|---|---|
|A.3 `STANDARD_MAPPING.md`（前后相同）|`6d208c61176461f32a5076dbf8d367b1afd0efab315bf1aad8a8e48e6e5819ba`|
|`GB30254_2024_标准表值.xlsx`（前后相同）|`b3755111a4f20a7f4cf1a6e37e48a4e17d4e0dcb8cea2ab88211fc67cf822912`|
|新包规范内容哈希（sorted compact UTF-8，排除integrity_sha256）|`99940b38c87b3fe15337694979ad3cf94d7c6732f84d468b6fc8c0d0e071b144`|

包身份固定于`pack_identity.py`；不仅检查自报哈希，重算哈希后的非批准内容也拒绝。旧资产、模板、Golden、用户数据、锁文件和数据库均未改。

## 验证

最终定向回归：6个测试模块，41项，pass 41 / fail 0 / error 0 / skip 0，41.773s，exit 0。覆盖高压9项（含8条Frozen Common Core向量）、既有GB18613 Numeric、Calculator、pack builder、rated input、input contract。高压全表回归逐一检查1126个表/极数/功率组合、3093个数值门槛等号、1094个相邻中点；仍为候选回归，不冒称Approved Golden。

新增代码compileall退出0；`git diff --check`退出0。初次提交时全仓门禁尚待结果；现已核实旧Head `6585dce236bde50225c5fedc5bac2aef81745e0b`的[Windows Core 41775604314](https://github.com/adgo07/EquipEffi/actions/runs/41775604314)成功，不将该结果冒充rebase及修订后Head验证。日志在独立worktree的`artifacts/motor-hv-core/targeted.log`、`targeted-r2.log`和`regression.log`。

提交前设计复核补齐原始频率文字语义：`变频`、`50/60`、`50 Hz`保留为非50Hz适用证据，返回不在范围，不猜测单位；公式、非有限值和非法数值仍拒绝。受影响2项追加复验pass 2 / fail 0 / error 0 / skip 0，0.697s，exit 0，见`frequency-review.log`。

首轮7项：pass 6 / fail 1 / error 0 / skip 0，exit 1。失败来自测试把半整数功率中点截成整数；修正测试为精确`.5`词法，未改变计算公式。第二轮高压及既有电机Numeric测试12项：pass 12 / fail 0 / error 0 / skip 0，38.905s，exit 0。此后补强展示隔离向量，用211kW的精确94.055与显示94.06区分业务比较，纳入最终复验。

## 后续交接

### 2026-11-04 审查意见处理

- 两处合并冲突真实存在，实际rebase复现并解决。QA-HV-001位于master已有QA-CAND-001和QA-MOTOR-004（CLOSED）之后；TASK_STATE保留11月3日记录、追加11月4日现状。三份文件及PR正文中的PR41待验收表述改为历史经过与已验收合并事实。
- Numeric Profile补齐本仓`numeric-profile-adoption-1.0`声明格式、Frozen状态与来源、trace入口和其他设备边界，并增加元数据/锁定来源/路径检查。原声明已具备Frozen Numeric必填语义，新增字段是本仓登记一致性补强，不代表原内核违反Frozen Contract，也不改变数值Profile行为或版本。
- 构建器补3条失败回归：源哈希不符、未核验显示格式、效率源格缺失。原缺格会以Decimal异常失败，现在明确抛出含源格坐标的ValueError；仍属执行失败，不生成业务结论。负例只修改临时副本；深层结构测试仅在测试中注入副本哈希，生产哈希门禁及批准源文件保持不变。
- `50 Hz`、范围和频率文字的当前结果符合既有GB18613及高压接入设计，本轮不单改高压。若以后调整为输入错误/规范化提示，应作为跨标准产品口径统一决定；此建议不是当前实现缺陷，不改变既有业务结果。
- 新增[机器可读验证摘要](evidence/motor_hv_review_20261104.json)：记录真实测试计数、模块、退出码、执行文件原始字节SHA、日志SHA、基线及旧Head CI适用边界。原始日志仍留本地，不把JSON摘要称为完整日志；可用列出的模块重新执行验证。

本次修订定向回归6模块45项：pass 45 / fail 0 / error 0 / skip 0，含编译检查总耗时47.4秒，测试及compileall退出码均0。`git diff --check`通过。修订后完整Windows CI待新的PR门禁结果；未做高压产品端到端验收或发布。

1. 本轮完成度仅为候选数据包与内核。QA-HV-001保持OPEN，待完整产品链与Stage D证据；不得把单元测试升级成支持状态。
2. 高压下一段接共享Application/Rule、Qt及不可变Record，再派生V6.4 / motor-input.v4；不改V6.3、V6.2旧语义，不新增数据库migration。
3. 端到端检查明确标准类别、冷却、单位、同核批量结果、新Workbook、历史快照与异常不保存；之后进行独立验收。永磁在高压之后，沿用既有Stage B设计及问题状态。
4. 本轮未做Windows包构建/GUI交互/性能基线/完整高压产品验收；这些为NOT_RUN，不以源内核测试冒充。

Knowledge capture：无新增条目。
