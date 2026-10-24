# GB 18613—2020 A.2 最终文档差异独立复核

复核者：`/root/gb18613_final_review`。日期：2026-10-24。结论：**PASS（限本次文档交付差异）**。

## 固定对象与范围

- 目标仓库 `https://github.com/adgo07/EquipEffi.git`；分支 `codex/standard-mapping-consolidation-20261024`；复核时 HEAD `f9ab7b6e2593f5ca2a56538ba766bfb409b2d530`，为 PR #32 的未提交交付工作树。默认分支为 `master`。本复核不代表 PR、提交树或远端状态已验收。
- [最终主映射](../../standards/gb18613_2020/STANDARD_MAPPING.md) SHA-256：`cc566c039d582c48ad0601e76db537b1dbbf2a006e16118eae86f97d88891d61`；[根问题台账](../../../STANDARD_ISSUES_REGISTER.md) SHA-256：`1e8514c228407859ebe9b830dd0c7bebbc68eb305cb81d7efa05768a03397b13`；[A.1 源工作簿](../../standards/gb18613_2020/data/GB18613_2020_表1-6校对数据_A1.xlsx) SHA-256：`fabb5722cf73afbdaf8fa8c5e76b8eddc86918b4cffe5ce060594afc609164bb`；[修订报告](../gb18613_revision_20261024/REPORT.md) SHA-256：`f9f0ed260ba810d5bd8e7cbe32eff298e42964393c2bae2ed74f75b58baa7ffa`。四项与 [DELIVERY_HASHES.json](DELIVERY_HASHES.json) 一致。
- 以旧工作区 A.2 主映射 SHA `570bb0dc508fd29630c350d1929278d37968fcec961f308d10569bf303035d9b` 为内容对照；核对当前工作树的映射、GB18613 台账段、修订报告、[交付记录](DELIVERY.md)、[归档清单](ARCHIVE_MANIFEST.json)、[原条件验收报告](ACCEPTANCE_REPORT.md)、[R2 附件](historical/ATTACHMENT_R2.md)、证据 CSV／汇总及重放包装器。

## 复核发现

1. **规则与候选：PASS。** 相对旧 A.2，主映射的业务规则正文未发生其他变化；本次差异是删除退役 ROADMAP 链接、将原报告链接改为仓内归档、说明 F1～F7 边界，以及收紧 BC-16。当前映射和候选均体现 Owner 已确认的 `U<1000 V`、表3 C14 源空白但有效指标为“—”、表5/6类型已选时供电对象待核不阻断、表5不要求独立转速输入而表6需有效转速选列、已知第6章试验工况不符时两表均不得使用该效率判级、插值阈值不按显示精度预修约。表5条件与表6条件没有互相偷换。映射不铺问题编号过程段，台账仍为问题状态唯一入口。
2. **台账与范围：PASS。** Git 差异仅在 GB18613 段；001～004 原有状态未变，005、007、008 为 `RESOLVED`，006 为 `PROVISIONAL`。007／008 的项目规则与映射和 BC-04、BC-16、BC-23～26 一致；没有将源事实、项目解释或待核事项写作官方解释。`V1_SCOPE.md` 仍为 `motor_lv` 范围与支持状态入口；本轮未将其提升为 `SUPPORTED`。
3. **来源与归档：PASS。** [归档清单](ARCHIVE_MANIFEST.json)所列七件报告、脚本、CSV、汇总及历史附件的归档文件与原来源逐字节 SHA-256 一致；原条件验收报告只覆盖 `bb9d7231…`，R2 的旧版本结论亦未被借作本 SHA 的验收。未补造原执行者身份。原 CSV 只读统计为 1290 行、1290 `PASS`，六表行数与汇总相合；此处复核的是既有证据的一致性。源工作簿哈希不变，读取 `表3!C14` 仍为 `None`。原 PDF 未纳入归档；[README](README.md)说明 PyMuPDF、openpyxl 依赖及原脚本的历史路径，[replay.py](replay.py)仅在 AST 中替换 `PDF`／`WB`／`OUT` 路径，校验原 PDF／工作簿哈希并要求新输出目录，未改归档的比较算法。
4. **报告与引用：PASS（待本记录归档后闭环）。** 修订报告保留旧工作区、旧 SHA 与当时复核为历史记录，另标明最终交付分支和本记录；其 Numeric 预检查与锁定中央 SHA `ee5feb0cc34dbd99790500fadd0c4c932e202a20` 所述计算／比较／显示分离、默认完整值比较、无全局 Motor 精度／模式一致。相关冲突分类为无冲突，未改锁。主映射 13 个、修订报告 11 个、归档 README 6 个、交付记录 3 个本地链接逐一解析；现有唯一缺失目标均是尚待复制归档的 `A2_REVIEW.md`，复制本记录后应再检查链接。`git diff --check` 通过。
5. **F1～F7：文档范围内 PASS。** F1～F5 已按最终正文与归档证据收口；F6 保留 A.1 工作簿历史说明和原 SHA；F7 的提交树、干净检出和远端 PR 同步由交付执行者后续核验，[交付记录](DELIVERY.md)当时仍写“正在完成”，因此本复核不判定 F7 已完成。

## 限制与判定

本次未重新运行原 PDF 对 1290 格的抽取／原页核验，也未运行生产软件、unittest、compileall、smoke 或性能测试；不构成 Stage D、官方释义、整体 PR 或任何 Phase 的验收。本 worktree 的 Git 管理目录只读，`git fetch origin` 因不能写 `FETCH_HEAD` 失败；已核对现有 `origin`、分支、HEAD、默认分支及本地差异，远端状态留交付执行者确认。

**PASS** 仅表示上述固定 SHA 的最终文档差异、台账范围和证据归档在本次只读复核中一致。若映射、台账或工作簿字节再变，应重新固定哈希并复核。
