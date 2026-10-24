# GB 18613 验收证据归档

本目录由 `/root` 于2026-10-24归档。原报告未具名，归档者不是原验收者；不补造身份。原报告、CSV、汇总、来源清单和原复核脚本逐字节保留，见[归档清单](ARCHIVE_MANIFEST.json)。绝对路径只记录原执行环境。

- [原有条件验收报告](ACCEPTANCE_REPORT.md)覆盖映射 `bb9d7231…`，不是最终A.2的验收。
- [附件R2](historical/ATTACHMENT_R2.md)及[Round4](historical/ROUND4_AUDIT.md)保留原结论及其适用版本。
- [最终文档差异复核](A2_REVIEW.md)固定最终映射SHA；沿用未变PDF和工作簿的全量证据，不声称重跑1290格原文审计。

## 重放边界

原[compare_cells.py](compare_cells.py)仅依赖Python标准库、PyMuPDF和openpyxl，无本地模块依赖；其PDF、WB、OUT为历史绝对路径。原PDF不随本目录发布。重放时使用下列包装器显式传入合法原PDF、同SHA工作簿和一个不存在的新输出目录，不改原脚本或覆盖归档证据：

```text
python replay.py --pdf <原PDF路径> --workbook <A1工作簿路径> --output <新输出目录>
```

包装器只替换原脚本三个路径变量，原核验算法不变。重放须自行具备依赖；归档不代表本轮执行了该算法或软件生产测试。

[verify_delivery.py](verify_delivery.py)可对提交树的干净检出执行文档、链接、哈希及归档CSV完整性检查，参数为检出根路径。原历史报告的Markdown双空格换行按原字节保留，仅两份原报告豁免尾空白风格检查；当前映射和新文档仍检查。

根台账最终Git／检出身份以[Git字节身份补充复核](A2_GIT_REVIEW.md)和DELIVERY_HASHES.json为准；原差异复核中的CRLF磁盘哈希属于当时快照，内容一致性结论保留。
