# 已答标准映射修订记录

Owner回复日期：文件名2026-10-14；本会话补充确认2026-10-23。修订执行2026-10-23～24，完成2026-10-24。

本次只处理8项标准的25个有效回复；第26项GB21454-001仅列编号无答复，及其他未答标准均未修改。源回复逐字保存为[快照](OWNER_REPLY_SNAPSHOT.md)，更正另存[补充确认](OWNER_FOLLOWUP_20261023.md)，不覆盖旧答复。[逐项落实记录](DECISION_APPLICATION.json)保留回复等级、项目规则、未答子项；唯一正式问题状态仍在根台账。

## 文件位置

|标准目录|当前映射|配套文件入口|
|---|---|---|
|GB18613—2020|[主映射](../../standards/gb18613_2020/STANDARD_MAPPING.md)|[入口及配套数据](../../standards/gb18613_2020/STANDARD_MAPPING.md)|
|GB30254—2024|[主映射](../../standards/gb30254_2024/STANDARD_MAPPING.md)|[入口及配套数据](../../standards/gb30254_2024/STANDARD_MAPPING.md)|
|GB30253—2024|[主映射](../../standards/gb30253_2024/STANDARD_MAPPING.md)|[入口及配套数据](../../standards/gb30253_2024/STANDARD_MAPPING.md)|
|GB19153—2019|[主映射](../../standards/gb19153_2019/STANDARD_MAPPING.md)|[入口及配套数据](../../standards/gb19153_2019/STANDARD_MAPPING.md)|
|GB24500—2020|[主映射](../../standards/gb24500_2020/STANDARD_MAPPING.md)|[入口及配套数据](../../standards/gb24500_2020/STANDARD_MAPPING.md)|
|GB29541—2013|[主映射](../../standards/gb29541_2013/STANDARD_MAPPING.md)|[入口及配套数据](../../standards/gb29541_2013/STANDARD_MAPPING.md)|
|GB19576—2019|[主映射](../../standards/gb19576_2019/STANDARD_MAPPING.md)|[入口及配套数据](../../standards/gb19576_2019/STANDARD_MAPPING.md)|
|GB37479—2019|[主映射](../../standards/gb37479_2019/STANDARD_MAPPING.md)|[入口及配套数据](../../standards/gb37479_2019/STANDARD_MAPPING.md)|

原XLSX与源格审计保留为PDF事实；GB18613的空白和GB30253的0.0不篡改成原文横杠，主映射明确其Owner批准的有效解释为“—”。后续迁移必须把主映射解释覆盖与工作簿配套应用，不能单独导入源值。八个工作簿本轮均未重存。

## 落实方式及剩余问题

- a/b级按批准的项目口径记录，不冒称发布机构勘误；c级保留PROVISIONAL，但已有合法资料及端点时不因该标识阻断评价。复合问题仅有部分答复时保持PROVISIONAL并逐子项说明。
- 普通型静态热泵H≥10 kW参照小容量静态行，低温型静态按项目不适用；额定制热量选组为临时口径。
- 压缩机按表内功率向上、压力向下取档；已确认示例0.75 MPa→0.7 MPa。实际7.5 MPa为超范围，不误认作7.5 bar。原测试公式留作参考，不转成软件试验功能。
- 两项空调实施日期已按Owner补充答复更正为2020-11-01；原封面2020-05-01作为历史事实保留。依据国标委发〔2020〕15号；[中国标准化研究院公开文件](https://www.cnis.ac.cn/bydt/zhxw/202004/P020200403418883088891.pdf)、既有专属验收回应保留证据获取边界。
- 电机容差不用于能效输入/阈值折扣，已形成[DRAFT知识](../../../src/equipeffi/resources/knowledge/motor_efficiency_tolerance_owner_20261024.md)。外部全文未在本轮独立核验，知识明确引用Owner查阅记录。
- GB29541、GB37479按Owner c级暂行十进制四舍五入到两位作比较值；保留原输入，不改变表格阈值，不当作平台默认或仅显示修约。

仍可继续回答的复合子项（本轮不猜测）：

1. GB19153-001：表3液冷、表4无液冷值以及横杠组合，是否统一作为无可用指标/不在评价范围？现仅落实功率与压力取档。
2. GB19153-002：额定功率恰等于表末时，§4.3a“大一档”的功率值取何依据？当前不外推、不跳过完整符合性检查；普通表值等级与全项符合性分开。
3. GB24500-001：仅有机热载体换热、低热值生物质与余热回收有机热载体交叉时，设计限定值与表三级采用哪个？当前只落实已回复的低热值生物质分支，其他子项原样保留。

c级本身的最终标准依据仍未补齐，但不再重复请求相同临时方案的批准。未回答的其他问题不在本轮扩展。

## 平台预检查与影响

实际origin为adgo07/EquipEffi，分支codex/six-standard-mappings，HEAD d9f711068bde583138a7f3dded6f64dcaa339761；2026-10-24已fetch。默认master，本地master相对origin/master为0/123；没有重置、合并或切换共享工作区，远端产品阶段不以此旧checkout推断。大量既有未跟踪文件保留。

locked central SHA：ee5feb0cc34dbd99790500fadd0c4c932e202a20，未升级。已读中央当前合并GUIDE_INDEX及路由的ACTIVE Standard Development Guide、Product Delivery Policy §12/20。舍入涉及Numeric，因此读取锁定SHA下Numeric Contract v1及Numeric Profiles v1：必须有明确舍入来源、阶段、位数、模式及comparison_value；不得把显示精度隐式反馈、设平台统一HALF_UP或epsilon。本轮仅记录单标准Owner显式比较修约，未实现Numeric Profile。冲突分类ALLOWED PROJECT DIFFERENCE，无中央Contract修改需求。

相关问题：上述25项。映射解释有变更；生产Calculator、Canonical、Approved Golden、数据库、UI、范围及支持状态无变更。历史验收/源格CSV/交付manifest保留原日期和范围，不把旧快照当成本轮修订后的独立验收。本轮新哈希以[文件清单](FILE_CHANGES.json)及BASELINE附录为准。

## 验证

验证结果见[检查记录](VALIDATION.json)：问题编号/状态一致性、未答Issue正文不变、原数据和冻结资产及既有src/specs哈希、修改文档相对链接、新增舍入案例算术。正式unittest、compileall、smoke、性能测试均NOT_RUN（文档修订，无软件行为改动）；独立验收NOT_RUN，不宣称Stage/支持提升。未提交或推送。
