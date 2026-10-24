# GB 18613 A.2 文档交付记录

实际仓库`adgo07/EquipEffi`；交付分支`codex/standard-mapping-consolidation-20261024`，起点`f9ab7b6e2593f5ca2a56538ba766bfb409b2d530`；PR #32。旧工作区`codex/six-standard-mappings`不是本次提交目标。

## 范围与问题状态

- F1～F4：转速输入分支、事实与解释分层、完整容差引用及插值计算值比较已按Owner确认落实。
- F5：Profile唯一入口V1_SCOPE、A.2修订标识、原验收来源和正式证据归档已补齐。原报告未具名保持原状。
- F6：工作簿旧注释作为A.1历史记录保留；工作簿SHA未变。
- F7：独立文档差异复核及提交树／干净检出检查已通过。最终提交与远端版本身份以PR #32的head为准；使用本次结论前，须核对其文件与本目录哈希清单一致。
- BC-16：两类风扇电机须符合第6章试验工况，表5不按转速选列、不要求单独填写转速。
- Motor Numeric Profile为Stage B后续设计，未宣称已配置；006供电对象问题仍PROVISIONAL且不阻断已明确类型的评价。

本次只整合GB18613相关台账段，保留PR分支其他标准和产品状态。没有恢复退役ROADMAP／HANDOFF／BASELINE。原PDF、工作簿、生产代码和Golden均不变；本任务不升级支持状态、不发布或合并PR。

## 证据与平台预检查

锁定中央SHA `ee5feb0cc34dbd99790500fadd0c4c932e202a20`；已核对Numeric Contract v1 §3/§6/§7/§8，要求计算／比较／显示分离、无显式例外时全值比较，禁止隐式修约及跨设备套用Pump配置；冲突分类N/A（符合锁定规则，无冲突），不修改中央Contract或锁。

[文件哈希](DELIVERY_HASHES.json)固定最终映射、台账、工作簿与修订报告。历史证据原字节与来源见[归档清单](ARCHIVE_MANIFEST.json)；原报告只覆盖其旧SHA。[最终独立文档差异复核](A2_REVIEW.md)另行固定本次版本，复用同SHA工作簿及PDF的全量原文证据，不宣称重跑全量数值审计。

生产unittest／compileall／smoke／性能均NOT_RUN（无软件改动）；本轮只做文档、归档、哈希、引用及变更范围验证。

## 交付检查结果

独立复核者`/root/gb18613_final_review`已对最终固定SHA给出文档差异PASS，原记录按字节归档。执行者`/root`从实际Git暂存树导出完整ZIP至全新目录后检查：51个本地链接可达、26组候选齐全、归档七件原文件哈希一致、1290条历史CSV记录均PASS、四项当前文件哈希一致、退役ROADMAP／HANDOFF／BASELINE均不存在。`git diff --cached --check`通过；生产及冻结目录与起点无差异。检查可用本目录`verify_delivery.py <干净检出根目录>`重放。原PDF不随PR交付，重放原文审计仍需合法取得同SHA PDF及依赖。

## Git字节身份补充

首次提交`506f4e1378c964c1240476328a91ff1f6c575a9d`后，Git blob复核发现根台账在旧Windows工作树为CRLF，而Git存储为LF。两者文本等价，但字节SHA不同。现将根台账显式固定`text eol=lf`；Git与后续检出均使用SHA `cb14ae9161bcd73fc731b3e0c1bd879c04ce82d594b5dde2dd73b9898d76dcc6`，取代旧磁盘SHA `1e8514c228407859ebe9b830dd0c7bebbc68eb305cb81d7efa05768a03397b13`作为交付身份；映射及工作簿SHA不变。原差异复核保留，纯换行等价与当前身份见[Git身份补充复核](A2_GIT_REVIEW.md)。最终检查同时覆盖Git blob和新干净导出，不只核对工作树。

最终补充验证：LF属性与补充复核入树后，重新从全新目录验证58个本地链接、全部清单哈希、26组候选和历史1290条CSV；同时直接读取Git blob验证四项当前资源哈希，均PASS。正文与原表值未改。
