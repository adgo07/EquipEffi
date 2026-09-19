# 迁移文件分类清单（2026-08-31）

本清单是对当前工作区的只读审查结果，配合
[HANDOFF_20260831.md](HANDOFF_20260831.md) 使用。

## 一、审查结论

当前工作区处于“新架构已运行，但尚未形成干净Git提交”的迁移状态：

- 15类公开设备入口和17个内部标准profile可运行；
- 新代码主目录为 src/equipeffi/；
- 旧版 core/、devices/、gui/ 和旧测试入口显示为Git删除；
- 新架构源码、测试、工具和文档大部分仍是未跟踪文件；
- outputs/、tmp/、_codex/已加入忽略规则，但本次没有删除；
- src/、tests/、main.py中没有扫描到对旧 core/devices/gui/utils 模块的导入；
- 核心API已通过 application/bootstrap.py 实现V4工作簿懒加载：JSON/status路径不解析XLSX，schema/V4/Web路径按需加载；
- 已完成十个评价器结构切片、公共辅助函数收敛和独立注册表：运行中的变压器、空压机、离心泵、潜水电泵、工业锅炉、热处理设备、鼓风机、通风机、HVAC和电动机评价器分别位于 src/equipeffi/domain/evaluation/evaluators/transformer.py、compressor.py、pump.py、submersible.py、boiler.py、heat_treatment.py、blower.py、fan.py、hvac.py 与 motor.py，共享辅助函数位于 shared.py，17个内部profile注册表位于 evaluator_registry.py，并由旧兼容模块导出；
- 已新增只读设备元数据注册表 src/equipeffi/domain/evaluation/metadata.py：按V4顺序提供15类公共设备的字段、别名、单位、数据类型、必填条件、边界、枚举、UI控件、V4映射和15→17路由来源；API与transformer桌面表单已完成试点接入并保留兼容回退，其他窗口和V4验证仍待逐步切换；
- 已新增 presentation/metadata_projection.py：API和桌面共用的无Tk/Excel字段投影校验入口，严格检查V4字段顺序、显示名称、单位和可编辑状态，不改写输入或模板；transformer和工业锅炉试点已接入。
- 电动机“额定转速”和鼓风机“进口/出口绝对压力、进口/出口温度、叶轮出口宽度/直径、多变效率百分比”已完成单字段数值约束迁移：前者V4/元数据均为`r/min`，压力均为`kPa`，温度为`K`，几何尺寸为`mm`，效率按1～100百分数本值填写；API/桌面回退和V4验证均已覆盖。电动机`rated_frequency`已核对为V4文本字段且无验证规则，仍保留旧规则，不自行发明数值边界。
- standards/motor_pmsm.json 和 standards/transformer.json 存在已跟踪修改，必须单独进行标准数据差异审查。

本清单不授权任何删除、恢复、提交或移动操作。下一位Agent应先审查，再按项目所有者决定建立迁移检查点。

## 二、四类文件分组

### A. 当前正式实现：建议保留并纳入迁移检查点

这些内容组成当前15类输入、标准查表/计算和结果输出的运行链：

    pyproject.toml
    main.py
    src/equipeffi/
    src/equipeffi/application/bootstrap.py
    src/equipeffi/domain/evaluation/evaluators/
    tests/__init__.py
    tests/README.md
    tests/unit/
    tests/integration/
    tests/contract/
    tests/contract/test_device_metadata.py
    tests/fixtures/
    tests/golden/
    android/
    README.md

保留原则：

- src/equipeffi/ 是唯一正式源码入口；
- src/equipeffi/domain/evaluation/evaluators/ 是当前运行评价器拆分目录；
- main.py 只能作为兼容转发入口；
- tests/ 中的测试按新包入口运行；
- android/ 目前是桥接/跨平台骨架，不能误称为完整Android应用；
- README.md 是当前运行和发布说明，但其中的历史发布目录示例后续需要统一。

建议审查命令：

    $env:PYTHONPATH = "src"
    python main.py --status
    python main.py --list-device-types
    python -m compileall -q src main.py

### B. 标准数据和标准来源：保留，但与代码分开审查

    src/equipeffi/resources/standards/
    src/equipeffi/resources/elimination_catalog_batches_1_4.json
    src/equipeffi/resources/elimination_catalog_industry_2024.json
    standards2/
    standards/标准数据核对报告_20260822.md
    standards/校对表_内部设备_20260822.xlsx

另外存在已跟踪修改：

    standards/motor_pmsm.json
    standards/transformer.json

处理要求：

1. 不把 standards/ 和 standards2/ 直接合并；
2. src/equipeffi/resources/standards/ 是运行时激活数据，应以 standard_manifest.json 和发布审计为准；
3. standards2/ 是整理和验证工作区，不能无审查替换运行时资源；
4. PMSM只允许使用已由PDF重建并人工复核的 gb30253_2024_pdf_verified_v1；
5. 机器JSON、人工校对册和来源页码必须通过现有验证工具逐条一致；
6. 标准数值改动应单独提交，不能与代码拆分混在一起。

标准数据核对的最低命令（只有确认数据确实变化时才运行重审计）：

    $env:PYTHONPATH = "src"
    python -m unittest tests.unit.test_standard_pack_validator tests.unit.test_pmsm_activation tests.unit.test_pmsm_readable_backup -q

### C. 历史实现：暂按“已迁移、不要恢复”处理

以下文件当前为Git删除，且 docs/06_旧实现清理记录.md 已说明其属于旧架构：

    PROGRESS.md
    build.py
    config.py
    core/__init__.py
    core/cleaner.py
    core/evaluator.py
    core/summary.py
    core/writer.py
    devices/__init__.py
    devices/base.py
    devices/blower.py
    devices/boiler.py
    devices/compressor.py
    devices/fan.py
    devices/heat_treatment.py
    devices/motor_hv.py
    devices/motor_lv.py
    devices/motor_pmsm.py
    devices/pump.py
    devices/submersible.py
    devices/transformer.py
    gui/__init__.py
    gui/main_window.py
    utils/__init__.py
    tests/integration_test.py
    tests/poc_writer.py
    tests/verify_devices.py
    docs/02_开发计划与操作方法_v1.md
    docs/03_使用说明_给使用单位.md
    docs/04_维护说明_给现状用户.md

旧标准Excel也显示为删除：

    standards/校对表_20260816.xlsx
    standards/校对表_内部设备_20260817.xlsx

处理要求：

- 不执行恢复；
- 如需追溯，用 git show HEAD:<path> 只读查看；
- 只有发现新架构确实丢失业务且用户明确要求时，才提取旧代码中的规则，并重新写成新架构测试；
- 不把旧写回器、旧GUI或旧评价器重新接入运行链。

### D. 生成物、缓存和待归档资料：不进入源码提交

已加入 .gitignore 的目录：

    outputs/
    tmp/
    _codex/

处理要求：

- 本次只是忽略，没有删除；
- 发布物需要保留时，使用独立归档目录和SHA-256清单；
- 不要因为 git status 看不到它们就重新构建；
- 不要把大型Excel、PDF渲染图、ZIP和原生构建目录复制进源码提交。

## 三、当前已跟踪修改的逐项风险

| 文件 | 当前判断 | 下一步 |
|---|---|---|
| .gitignore | 低风险工程整理 | 保留，检查是否与团队忽略策略冲突 |
| main.py | 低风险入口统一 | 保留，运行根入口与包入口对比 |
| docs/01_方案评审与规则清单_v1.md | 业务规则输入 | 保留，但不要当作标准原文 |
| tools/build_review_sheets.py | 标准/校对工具 | 只有改工具时才单独测试 |
| tools/extract_motor_tables.py | 标准提取工具 | PMSM旧流程禁止重新作为数据来源 |
| standards/motor_pmsm.json | 标准数据修改 | 必须和PDF复核包、人工校对册对比 |
| standards/transformer.json | 标准数据修改 | 必须查明修改原因和来源 |

不要把“低风险代码修改”和“标准JSON修改”一次性混合提交。

## 四、已完成的运行时证据

最近一次轻量基线执行结果：

    python main.py --status       15个公开类型，17个标准包active
    python main.py --list-device-types   15类全部可列出
    python -m unittest ...        217项核心相关测试通过；加入桌面表单试点后为235项，当前轻量组合为493项
    python -m compileall -q ...   通过

测试中出现的参数用法错误文本来自预期的非法输入测试，不是失败。

## 五、接手后的推荐执行顺序

### 第一步：只读确认

    git status --short
    git diff --name-status
    git ls-files
    rg -n "from (core|devices|gui|utils)|import (core|devices|gui|utils)" src tests main.py -g '*.py'

预期：没有旧目录导入；若发现新引用，先修正依赖边界，不恢复旧目录。

### 第二步：建立不改变代码的迁移报告

报告至少包含：

- A/B/C/D四类文件数量；
- 删除文件是否均能由 docs/06_旧实现清理记录.md 解释；
- 新源码是否独立运行；
- 两个已跟踪标准JSON的差异摘要；
- 生成物目录大小和归档位置；
- 是否存在重复入口、重复字段清单或过时测试。

### 第三步：只选一个结构重构点

懒加载装配、十个评价器切片、公共辅助函数、评价器注册表、架构边界测试、统一15类设备元数据与V4字段契约的第一阶段一致性测试、transformer API schema试点、transformer桌面表单试点、变压器数量/正数验证试点、工业锅炉效率边界试点、电动机设备类别/额定电压/极数/冷却枚举回退试点、变压器四组枚举回退试点、空压机类别/冷却枚举回退试点、离心泵类别/单双吸枚举回退试点、潜水电泵设备形式/设备类别枚举回退试点、工业锅炉类别/能源燃料品种枚举回退试点、热处理设备类别/能源类型枚举回退试点、热泵热水机设备类别/加热方式/是否提供水泵枚举回退试点、离心通风机设备类别/传动方式/单双吸枚举回退试点、轴流通风机设备类别/传动方式/是否带进气箱/是否带扩散筒/是否动叶可调/是否可逆转枚举回退试点、鼓风机设备类别/是否多级叶轮/是否悬臂式/是否三元流动叶轮枚举回退试点、风管送风式空调设备类别/冷却方式/机组类型/焓差类型枚举回退试点、缺失V4字段回退投影、单元式空调设备类别/冷却方式/机组类型枚举回退试点、多联式空调水冷式类型/设备类别枚举回退试点已经完成。下一步按P1-2顺序核对电动机“额定频率”等数值规则；每次只移动一个架构职责，并用完整JSON结果逐字段对比。不要把新规则同时写入已有的 src/equipeffi/domain/evaluation/ 垂直骨架。

> **当前状态覆盖说明（2026-08-31）**：上方“下一步按P1-2顺序核对电动机额定频率”等文字属于早期迁移记录，不能作为当前任务。电动机`rated_frequency`已确认是V4文本字段且无数值验证；压力、温度、叶轮几何尺寸、多变效率、风机/鼓风机等熵/绝热指数k、轴流通风机轮毂比、潜水电泵工作温度和离心泵/鼓风机/潜水电泵级数下界试点已完成，当前唯一推荐下一步是选择一个V4边界明确的未迁移数值字段。

### 第四步：结构重构验收

补充状态：鼓风机“进口/出口绝对压力、进口/出口温度、叶轮出口宽度/直径、多变效率”及离心/轴流通风机和鼓风机的等熵/绝热指数k、轴流通风机轮毂比、潜水电泵工作温度、离心泵/鼓风机/潜水电泵级数正整数下界、热处理设备额定温度正数下界、离心/轴流通风机机号正数下界回退试点已完成；电动机`rated_frequency`已核对为V4文本字段且无数值验证，不应自行改成数值规则。新增十二项契约/API/桌面/V4验证测试后完整轻量矩阵为520项通过。下一步只选择一个V4边界明确的未迁移数值字段。

本轮在上述已完成项基础上新增：单元式空调机组类型、多联式空调水冷式类型枚举回退试点；完整轻量矩阵为345项通过。

随后又完成多联式空调设备类别枚举回退试点；完整轻量矩阵为349项通过。
随后完成热泵和冷水机组设备类别枚举回退试点；完整轻量矩阵为353项通过。
随后完成热泵和冷水机组产品标准枚举回退试点；完整轻量矩阵为357项通过。
随后完成热泵和冷水机组机组型式枚举回退试点；完整轻量矩阵为361项通过。
随后完成热泵和冷水机组冷却/热源方式枚举回退试点；完整轻量矩阵为365项通过。
随后完成热泵和冷水机组能效评价指标体系枚举回退试点；完整轻量矩阵为369项通过。
随后完成离心通风机设备类别枚举回退试点；完整轻量矩阵为373项通过。
随后完成轴流通风机设备类别枚举回退试点；完整轻量矩阵为377项通过。
随后完成鼓风机设备类别枚举回退试点；完整轻量矩阵为381项通过。
随后完成鼓风机“是否多级叶轮”枚举回退试点；完整轻量矩阵为385项通过。
随后完成鼓风机“是否悬臂式”枚举回退试点；完整轻量矩阵为389项通过。
随后完成鼓风机“是否三元流动叶轮”枚举回退试点；完整轻量矩阵为393项通过。
随后完成潜水电泵设备类别、工业锅炉能源燃料品种和热处理设备类别枚举回退试点；完整轻量矩阵为405项通过。
随后完成热处理设备能源类型枚举回退试点；完整轻量矩阵为409项通过。
随后完成热泵热水机设备类别枚举回退试点；完整轻量矩阵为413项通过。
随后完成离心通风机“传动方式”枚举回退试点；完整轻量矩阵为417项通过。
随后完成轴流通风机“传动方式”枚举回退试点；完整轻量矩阵为421项通过。
随后完成离心通风机“单双吸”枚举回退试点；完整轻量矩阵为425项通过。
随后完成离心通风机“是否暖通空调用”枚举回退试点；完整轻量矩阵为429项通过。
随后完成离心通风机“是否带进气箱”枚举回退试点；完整轻量矩阵为433项通过。
随后完成轴流通风机“是否带进气箱”枚举回退试点；完整轻量矩阵为437项通过。
随后完成轴流通风机“是否带扩散筒”枚举回退试点；完整轻量矩阵为441项通过。
随后完成轴流通风机“是否动叶可调”枚举回退试点；完整轻量矩阵为445项通过。
随后完成轴流通风机“是否可逆转”枚举回退试点；完整轻量矩阵为449项通过。
随后完成公共电动机“设备类别”枚举回退试点；完整轻量矩阵为453项通过。
随后完成公共电动机“额定电压”枚举回退试点；完整轻量矩阵为457项通过。
随后完成公共电动机“极数”枚举回退试点；完整轻量矩阵为461项通过。
随后完成电动机“额定转速”数值约束回退试点；V4/元数据单位和边界一致，零值、负值、文本与空格质量问题均有测试，完整轻量矩阵为465项通过。

    $env:PYTHONPATH = "src"
    python -m unittest tests.unit.test_device_evaluator_matrix tests.unit.test_evaluation_engine tests.unit.test_public_device_types -q
    python -m compileall -q src main.py

只有结果逐字段一致，才继续下一个设备族。

## 六、禁止把以下事项当作“迁移完成”

- 仅因为 python main.py --status 成功，就认为Git迁移已完成；
- 仅因为最终能效等级一致，就认为评价器重构等价；
- 仅因为人工校对册显示“正确”，就跳过机器JSON和来源页码核对；
- 仅因为Excel按钮可见，就声称Excel上传/回写已经实现；
- 仅因为产业目录有命中条目，就声称产业目录已经全文覆盖；
- 仅因为所有标准包为 active，就省略版本、来源和条款追溯；
- 仅因为忽略规则隐藏了生成物，就删除或重建发布目录。

## 七、完成迁移检查点的条件

在创建正式迁移提交之前，应至少满足：

1. A类正式源码和测试清单已确认；
2. C类旧文件的删除理由已记录；
3. B类标准数据变更与代码变更已分开审查；
4. src/ 无旧目录导入；
5. P0轻量基线通过；
6. 当前运行入口、15类接口和17个标准包状态没有意外变化；
7. 不包含 outputs/、tmp/、_codex/ 中的生成物；
8. 用户或项目维护者确认可以建立Git检查点。

在上述条件满足前，工作区保持现状是安全选项，不要用破坏性命令“整理干净”。
