# 标准档案目录整理摘要（2026-10-13）

## 范围与平台预检查

- 仓库origin已确认：`https://github.com/adgo07/EquipEffi.git`；默认分支`master`，开工fetch成功；起点`f12b5f29b306c769c0f0e56f5fe433fda7d75ba7`，任务分支`codex/standard-archive-conventions`。原本地master落后远端，未以其过时状态作为编辑起点。
- locked central SHA：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`；已读取中央当前GUIDE_INDEX和Standard Development Guide（ACTIVE），本轮只是本仓归档维护。**本任务不涉及中央公共 Contract。** 无需修改Frozen Contract或锁文件，未发现中央契约冲突。
- 适用MUST/MUST NOT：单一正文与状态权威；冻结双文件不可改写；迁移不改标准解释、Approved Golden、运行时Canonical、计算/数据契约和支持状态；标准新接入仍走既有Stage A→D。
- 相关Standard Issue：`EQP-STD-GB19762-001`仅更新映射证据路径；`EQP-STD-GB20052-008`的Owner批准RESOLVED事实保留，独立逐格证据与项目批准分开。本轮未改变任何已有软件解释或问题状态。

## 实际变更与资产分类

|资产|分类|处理|
|---|---|---|
|标准总入口、解释模板|REWORK|补目录命名、索引、配套数据与可复现核验规则|
|主映射模板|新增|统一范围/字段/选表/公式/判级/来源/核验/案例结构，按需使用|
|水泵两份Profile映射|MIGRATE|移至`docs/standards/gb19762_2025/profiles/`；新增历史时期说明，仅修正已有Markdown相对链接|
|原Profile路径|KEEP|简短跳转兼容历史报告，正文不再重复维护|
|变压器V2.1全部档案|KEEP|原位保留，新增`gb20052_2024/README.md`稳定入口|
|冻结主映射与XLSX|KEEP / VERIFY|按冻结清单核对SHA，未编辑或重存|
|Golden、原PDF、Canonical、代码与测试|KEEP|不移动、不修改、不重新批准|
|既有未跟踪用户文件|KEEP|不清理、不纳入提交|

根README和AGENTS补入口；HANDOFF/TASK_STATE只更新当前维护任务；BASELINE追加迁移前后哈希，不改Phase 0历史事实。历史Phase报告中的原路径仍由跳转承接。

规则与表值配套；结构检查不替代数值核验；重复容量/同值不同分支不得合并；PDF原页图像、XLSX真实坐标与必要XML复查进入模板。没有独立证据不声称数值验真，已撤回错列不成为修复依据。未对水泵凭旧JSON生成新的“已核验工作簿”。

## 验证与复核方法

1. 读取起点Git blob的两份旧Profile正文，统一LF。与迁移后`preserved-profile-body`标记以下逐字比较，只允许共同契约相对路径由`../../../docs/`改为`../../../`；标题保持一致。两份均PASS，原正文无丢失。
2. 检查新标准目录、总入口、模板和旧跳转中的所有本地Markdown链接，按文档所在目录解析文件/目录目标；不将这项检查冒称外部URL或锚点全面验证。
3. 按冻结清单计算变压器主映射UTF-8/LF SHA及XLSX原始字节SHA，并与起点Git blob比较；两份均一致。
4. `git diff --check`检查空白问题；检查受保护目录及锁文件差异为空；提交前仅暂存本轮明确路径。

|检查|pass|fail|error|skip|not_run / 边界|
|---|---:|---:|---:|---:|---|
|水泵正文保留比较|2|0|0|0|0|
|变压器冻结双文件哈希|2|0|0|0|0|
|新增标准入口/模板/跳转本地链接|59|0|0|0|0；10份文档，仅本地目标存在性|
|`git diff --check`|1|0|0|0|0|
|受保护跟踪路径无差异|1|0|0|0|0；src/tests/Golden/evidence/锁文件/变压器原档案|
|全量unittest / compileall / 产品smoke / 性能基线|0|0|0|0|各1项not_run：纯文档改动，无生产代码/资源修改|
|PDF逐格数值核验 / XLSX错列复验|0|0|0|0|各1项not_run：目录整理没有执行这些业务审计，不声称其通过|

没有新增Phase PASS、软件SUPPORTED或Golden批准。D-08本次不重开；后续逐格证据补强按标准入口记录的要求执行。本次完成的是目录与归档规范，非变压器数值验收。

Knowledge capture：无独立知识文章；用户提供的归档/核验经验已写入维护规范与模板。
