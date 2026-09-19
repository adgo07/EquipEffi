# 测试结构

- `unit/`：领域模型、清洗规则、指标和判定器。
- `contract/`：标准库、模板和导入导出契约。
- `integration/`：应用服务串联测试。
- `golden/`：脱敏真实样例和人工核对结果。
- `fixtures/`：测试输入文件和标准数据快照。

旧版根目录测试脚本已经删除。当前测试使用Python `unittest`，可在仓库根目录执行：

```text
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_*.py'
```

后续如引入pytest，将保留上述命令作为无第三方依赖的基础验收入口。
