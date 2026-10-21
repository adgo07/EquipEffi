# 第二批简化：标准仓库装配去重

## 范围与平台预检查

- 起点：EquipEffi `master@3d692f6ac6ddfeab15967086ecad95405f3f0d50`，origin 已核验。
- 中央 origin 已核验并 fetch；ACTIVE GUIDE_INDEX 为 `c5fc6d438c9200060649e47c016b9b48218de72c`。本仓 locked SHA 仍为 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`。
- 相关 Frozen：Architecture V2.1。装配留在外层，Domain/Application 不依赖 UI、Excel 或具体持久化实现；不新增循环。本任务不涉及中央公共 Contract 语义变更，无需改中央 Contract。冲突：未发现。
- 标准问题：不改变已有标准解释，无新增 Standard Issue；Canonical、Approved Golden、Numeric、冻结双文件、模板、schema 和锁均不变。
- 主会话设计并独立验收，原 C 线 gpt-6-luna / max 实现。X/P 无对应改动，不启用。

## 调用盘点和取舍

| 原维护位置 | 当前调用路径 | 本批处置 |
|---|---|---|
| composition.create_core_api | 无模板核心 API；现无直接生产调用，保留兼容接口 | 共用标准仓库构造，继续不读 V4 |
| composition.create_application_api | entrypoint 的 JSON/Web/兼容入口 | 共用构造，保留可选模板及资源管理器生命周期 |
| composition.create_pump_analysis_service | Qt 单台；create_batch_evaluation_service 间接用于 Excel | 共用构造，保留持久化开关及各入口新实例 |

三处共同规则均为包内 manifest 优先，缺失才使用显式 project_root 或既有默认根路径。只抽取此现有职责；三段原实现退出。包内优先于显式 root 的现行行为不借重构改变。

不选：Qt/Excel 请求转换属于载体差异；单台 Record 与 batch_record 不同；已共用结果投影不再抽象；Qt 与 batch 服务实例不合并，不创建全局缓存。旧 API 的日期门禁等既有差异不在本批改变。

## 验证记录

- 改动前独立基线：composition、entrypoint、architecture_boundaries 共 48 run / 48 pass / 0 fail / 0 error / 0 skip。
- C 线提交 `a899415245b9dcbe4da933fc84e8f7ea4148f7c9`；集成代码 Head `97e6687`。子会话 composition 5/5，兼容 API 与 Qt/Excel 装配组合 126/126。
- 主会话独立验证：97 run / 97 pass / 0 fail / 0 error / 0 skip（86.324 秒）；包括 composition、entrypoint、architecture_boundaries、GoldenExcelReplayTests、phase7_analysis_history。覆盖 29 条 Approved Golden 的真实 Excel 重放、单台/批次结果一致性及自动保存/历史规则。日志位于集成工作树 artifacts/batch2-independent.log（本地产物不入 Git）。
- 主会话审阅完整差异；三入口旧构造已退出，加载顺序和求值时机保持；关键资源与标准目录对起点 git diff 为空。git diff --check 通过。
- 本地独立验收通过；[PR #25](https://github.com/adgo07/EquipEffi/pull/25) 已提交；远端 CI 待完成，尚不能称远端通过。已有基线问题按原 exact-ID 门禁核对，不扩大允许名单。
- 原生 EXE 构建：NOT_RUN；本批无发布工程。Phase 8 状态不提升。

Knowledge capture：无。
