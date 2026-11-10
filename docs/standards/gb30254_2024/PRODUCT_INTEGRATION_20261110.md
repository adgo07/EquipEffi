# 高压电机产品接入实施与验收方案

日期：2026-11-10。Owner已授权先设计、由GPT-6.1-sol medium实施、主会话独立验收并提交PR；Computer Use由GPT-6-astra medium执行。本轮只接GB 30254—2024，永磁留待后续。不合并、不发布、不自行提升SUPPORTED。

## 基线与约束

- 软件基线：master `725d91db9ba2c668e14288662f0dbd1ca114e08a`（包含PR42高压候选内核和PR43界面收口）；分支 `codex/motor-hv-integration-20261110`。
- 中央ACTIVE指南：`829853a943c421e0b9864d84f3d94970d2ddf688`，按GUIDE_INDEX路由采用标准开发、产品交付和当前家族UI指南。
- Frozen Numeric Contract/Profile及Conformance按platform-lock的 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`；不升级锁。MUST：精确十进制入口、独立高压Profile、全值比较、显示隔离、不可变快照。MUST NOT：float隐式权威化、跨表补值、epsilon、显示值回流计算或历史重算。
- 依据：本目录A.3 STANDARD_MAPPING、六表工作簿、INTEGRATION_DESIGN，以及既有MOTOR_HV_CORE_20261104记录。继续QA-HV-001；EQP-STD-GB30254-001/002已解决，沿用既有解释及MOTOR-009输入决定。无已知中央Contract缺口；独立有理数Profile为允许的项目差异。
- 不修改批准映射、源工作簿、Golden真值、既有正式模板、数据库或迁移。新增V6.4派生模板属于本轮已授权接入范围，不能覆盖旧模板。新解释问题先报告，不自行决定。

## 用户流程与实现设计

1. **单一业务链。** 复用已合并Gb30254MotorCalculator与候选包，不重新实现六表算法。增加明确高压输入契约及Application/Rule装配，由Qt和Excel共用。标准号/类别显式路由，不能根据电压猜标准；旧低压入口和语义保持。
2. **产品入口。** 在既有电动机分析流程与标准库加入明确的GB30254高压类别，展示真实“已实现/待验收”状态而非SUPPORTED；不引入新导航或新AppShell。本开发候选可实际执行本轮新功能。范围文档注明本轮授权的候选接入，正式发布范围不变；永磁仍不开。
3. **输入。** 类别为高压三相笼型异步电动机；额定电压V、频率Hz、冷却IC代码、额定功率kW、极数、额定效率%为业务字段；额定效率1～100百分数点。电压有效表值3000/3300/6000/10000；50Hz与文本频率适用行为沿用已批准内核。冷却列表与Application契约同源，不默选造成错误表路由。不增加报告核验、人工签署或新适用性确认框。
4. **界面。** 复用PR43既有布局、精确文本数值输入、整框下拉点击/防滚轮误改、中文标签单位、自动生成记录提示。必要错误及过期提示直接可见；次级查看记录。结果等级、三阈值、原因及查表依据清晰；完整精确追溯留快照，普通用户不必理解技术版本。
5. **记录。** 合法终态自动新增不可变单台Record；非法输入和执行失败不生成记录。快照保存标准身份、原始/规范输入、单位、表包SHA、Profile、Calculator/Rule版本、源格/插值端点与精确阈值。沿用历史两页签，只读旧快照，无migration，不重算。
6. **Excel V6.4 / motor-input.v4。** 沿用一个“电动机”Sheet、A:T列。F显式标准/类别，G电压V、H频率、I高压冷却、J功率、K极数、L保留类别转速语义（高压不使用）、M额定效率；其余回写和通用列沿用设计。配置/下拉与共享契约机械核对。新增派生文件及manifest，旧V6/V6.1/V6.2/V6.3逐字节保持，其他Sheet内容和顺序保持。未知contract/类别明确拒绝或报告未处理，不伪成功。
7. **批量与交付。** Excel词法无损进入同一Application；输出另存、不覆盖输入；一个Workbook只生成一条batch_record，不生成逐行单台记录。打包包含新包和模板，不依赖仓库外标准文件；保留原文件来源但不捆绑标准原件。候选程序使用独立数据目录，不覆盖旧包、不关闭用户程序。

## 实施顺序与交接

- 第一段：输入契约、包资源/身份校验、Application装配及服务测试；提交可审查结果并继续第二段。
- 第二段：标准库、Qt、历史详情接入，保持家族UI；报告代码边界供主会话中途审查。
- 第三段：V6.4派生、Reader/Writer、兼容和容量测试，构建独立候选包；实施者本地提交不自行推送/开PR。
- 主会话独立审查差异和业务证据，复验关键测试；若发现缺陷回交实施者修复。实际窗口由指定astra子agent操作，主会话独立查看证据。通过后推送并提交一个PR，记录未验证项，不自行合并。

## 验收标准

|领域|必须取得的证据|
|---|---|
|六表与精确比较|复用现有全表/中点/Conformance；补Application链的六表路由、三级/未达、等号上下、211kW精确94.055与显示94.06分离；预期来自Mapping/源格，不从被测实现反推|
|异常和范围|缺参数、负数/非有限/float、非50Hz、无极数列、横杠/越界、错误包/Profile、存储失败；不补值不外推，执行失败不落业务记录|
|入口一致性|同一组输入经Qt/Application及Excel得到相同标准/表/等级/精确阈值/原因；高低压显式隔离|
|记录兼容|新增高压记录完整、再次分析新增、历史只读；低压/泵/变压器旧快照与旧模板含V6.2 kV/实测口径不变|
|Excel安全|新旧模板身份与拒绝行为、混合设备Workbook、输入文件哈希不变、一个批次/零单台新增；少量/100/1000/10000行容量实测；追加行/下拉/保护/保存重开能检查的部分实际检查，缺Excel/WPS环境如实列未验证|
|原生Windows|独立候选EXE启动、标准发现、高压类别/冷却/数值输入、分析与记录、导入输出与历史；默认及小窗口可达；离屏不替代真实DPI，未测125%/跨屏不宣称通过|
|回归与PR|相关定向测试、完整Windows CI与Whitespace；受保护资产无变更，包资源自检通过；报告真实数量、退出码、候选源码身份及限制|

该方案不把Stage C完成直接称为Stage D正式支持；验收结论及SUPPORTED决定分开。维护既有TASK_STATE、QA-HV-001和本文件的简短执行记录即可，不新增重复归档体系。


## Stage C执行记录（2026-11-10，待独立验收）

- 按本方案完成共享服务与显式类别/标准路由，不修改六表内核算法。高压结果明确IMPLEMENTED，Record使用2024/motor_hv/GB30254-A.3规则身份，保存原始输入、同Profile解析后的精确数值、单位、源格、插值端点及未舍入阈值。非法输入不落单台Record，包/Profile错误传播执行失败，存储失败明确不保存。
- Qt沿用现有电动机页面、标准库、两页签历史与不可变记录；新增高压IC冷却选项不默选。标准库到MainWindow路由、切回低压、历史无当前服务的静态契约回退均有回归。
- 新V6.4由登记V6.3定点派生，保留旧模板和其他设备Sheet；同核Reader/Writer保留十进制词法、输出另存、一Workbook仅一batch_record。旧v2/v3类别和显式服务契约不能接通高压。批次标准按明确请求类别登记，输入失败不误标低压，未知类别明确输入错误。
- 第一段服务测试12项+6子例exit0；服务/Qt/既有产品兼容定向22项+6子例exit0；后续防跨contract与失败批次定向17项+6子例exit0。完整门禁以最终结果为准，不把中间定向数量相加冒充总量。
- V6.4容量实测：1行3.172s、100行4.343s、1000行21.313s、10000行154.500s；独立临时目录4批次/零单台新增，测试总192.38s、exit0。耗时包含同核评价、输出/回读验证与批次写入，非Excel/WPS交互证据。
- 尚未验证：Excel/WPS真实追加行/下拉/保护/保存重开，真实125%系统DPI、跨屏、另一台干净Windows；离屏自动Qt测试不替代这些事项。原生候选实际窗口由主会话指定人员验收，实施者不自行声称通过。当前全量及构建证据待最终补记。

Knowledge capture：无。


### 2026-11-11 工程复验

首轮Windows完整发现实际执行1277项、1905.311s、exit1：3个架构子例失败（历史页直接导入Domain，已改经Application静态契约）；4个构建锁ERROR（msvcrt.locking errno13，构建与测试并行冲突）；另1个发布审计模块导入ERROR（缺少DEFAULT_V64_TEMPLATE出口，已补齐）。原日志保留于`artifacts/hv-integration/full-suite.log`，不声明该轮通过；发布审计导入失败使该模块当轮未执行，最终CI数量应重新统计。

上述4锁错模块、完整发布审计模块、架构边界以及最新高压Application/Qt/Excel已串行复验：50 passed、5344 subtests passed、1 deselected（仅本地已测容量项）、211.20s、exit0，日志`artifacts/hv-integration/targeted-final.log`。包含wheel真实高压1级/IMPLEMENTED烟测、旧V6.3必需资产、N10公式拒绝、旧contract粘贴高压拒绝、失败批次标准身份与非电机配置保护。成功插值结果增加简短显示精度说明，直查及C16无阈值不加，旧历史不追改。

完整套件未缩减、未新增skip；按主会话安排不重复启动第二份本地全量，最新HEAD的最终全量复验由PR Windows Core CI完成，绿灯前不宣称完整门禁通过。最终Qt关闭时的窗口偏好SQLite错误来自未改动的closeEvent在测试临时目录已清理后关闭残留窗口，既有catch记录后正常退出；Qt线程已quiescent、QApplication已删除，不将该噪声写成高压业务记录失败。


### 最终独立Windows候选（2026-11-11）

- 固定生产源码HEAD：`9e90c7da2cc467e337cb0c1bb7ec6eefca1e7e36`；随后仅追加本段文档，不改生产代码。构建exit0、`status_ready=true`、Qt和运行资源审计通过，真实原生交互验收由主会话另记，不以该自检替代。
- EXE：`D:\project\设备能效软件\EquipEffi-hv-integration\dist\hv-integration-9e90c7d\dist\equipeffi-hv-candidate\equipeffi-hv-candidate.exe`；SHA-256：`2f81d2c26e43ecd92088661bc7ba3cbaec3f814e4ebbb1db63f476188a2742ae`。
- ZIP：`D:\project\设备能效软件\EquipEffi-hv-integration\dist\EquipEffi-hv-candidate-9e90c7d.zip`；SHA-256：`3e83ebc57d0a3fe2352f766cfc6ad9865e1d52e47f0bf02ef00b71fe9a83733c`。首个049f373构建因后续架构补丁已过时，不作最终验收包；没有覆盖旧包。
- 实际启动恢复：默认受限环境的Start-Process无PID返回（session51225已取消、exit1）；非提升Popen的PID17384已确认退出，未创建数据库。随后按已授权的候选测试，在可见用户环境以提升Popen、`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`启动最终EXE，PID25080，已创建独立user.sqlite/records.sqlite；是否窗口交互通过以主会话原生验收为准。没有关闭任何用户或旧程序。
- 可双击独立入口：`D:\project\设备能效软件\HV_review_20261110\启动高压候选_9e90c7d.cmd`（UTF-8/CRLF，先切65001）。它引用上述EXE绝对路径，以系统PATH、Qt windows启动，清空外部Python/Qt插件路径；LOCALAPPDATA固定为`D:\project\设备能效软件\HV_review_20261110\native-9e90c7d-data`，实际数据在其`EquipEffi`子目录，仅供本候选测试，保留该候选历史，不读写原用户数据。此cmd不依赖源码Python，也不复制候选包；双击交互待原生验收。
- 构建报告：`artifacts/hv-integration/native-build-9e90c7d.json`；构建日志同名`.log`；实际启动详情`native-launch-9e90c7d.json`及启动stderr `native-startup-9e90c7d.log`同目录。本机工程证据保留，不捆绑标准原件。

可复现构建（仓库根目录执行，Windows Python 3.12，输出使用新的独立目录，不能覆盖正在验收的包）：

```powershell
$env:PYTHONPATH = 'D:/project/设备能效软件/EquipEffi-hv-integration/src'
$env:PYTHONIOENCODING = 'utf-8'
$env:TEMP = 'D:/project/设备能效软件/EquipEffi-hv-integration/.test-temp'
$env:TMP = $env:TEMP
& 'D:/project/设备能效软件/EquipEffi/.venv/Scripts/python.exe' tools/build_native.py --output-dir dist/hv-integration-9e90c7d-rebuild --name equipeffi-hv-candidate --python 'D:/project/设备能效软件/EquipEffi/.venv/Scripts/python.exe' --report artifacts/hv-integration/native-build-9e90c7d-rebuild.json --zip-output dist/EquipEffi-hv-candidate-9e90c7d-rebuild.zip --timeout 1200
```

最终未验证事项仍包括真实Excel/WPS追加行/下拉/保护/保存重开、真实125%系统DPI/跨屏、另一台干净Windows及最新HEAD的完整PR CI。LibreOffice不能替代Excel/WPS。本轮保持IMPLEMENTED、QA-HV-001 OPEN，不发布、不合并、不自行推送。
