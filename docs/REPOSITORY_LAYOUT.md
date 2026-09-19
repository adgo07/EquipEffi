# GitHub 发布目录说明

本仓库的运行时唯一入口是 `src/equipeffi/`。提交或上传 GitHub 时，按下面的边界整理：

## 应提交

- `src/equipeffi/`：领域评价、应用服务、接口、展示层、已复核标准 JSON、淘汰目录和 V4 模板；
- `tests/`：单元、契约和集成测试；`tests/samples/` 为本机样例，已忽略；
- `tools/`：标准数据审计、发布审计和开发辅助脚本；需要外部 PDF/DOCX 时通过命令行参数提供路径；
- `docs/`、`HANDOFF.md`、`HANDOFF_20260831.md`、`MIGRATION_INVENTORY_20260831.md`：规则、来源、架构和交接记录；
- `android/`、`scripts/`：跨平台桥接和启动脚本；
- 根目录 `main.py`、`pyproject.toml`、`.gitignore`、`README.md`。

## 不应提交

- `outputs/`、`tmp/`、`_codex/`、构建目录和 Python 缓存；
- 根目录 `standards/`、`standards2/`、`template/`：这些是本机原始/校对/旧模板工作区，不是运行时数据源；
- 旧 `core/`、`devices/`、`gui/`、`config.py`、`build.py` 和依赖旧架构的测试入口；
- 旧 `motor_pmsm.json`、粗校对/清洗版 PMSM Excel、`~$` 临时文件和由它们生成的历史结果。

## 标准数据边界

运行时只读取 `src/equipeffi/standard_manifest.json` 显式列出的资源。永磁同步电机只允许
`gb30253_2024_pdf_verified_v1.json`；第一至第四批淘汰目录和产业目录受控子集分别位于
`resources/elimination_catalog_batches_1_4.json`、`resources/elimination_catalog_industry_2024.json`。
原始标准 PDF、四批 DOCX 和人工校对工作簿保留在项目外部或 `outputs/`，不复制进运行时目录。

## Git 操作

整理完成后只从一个命名分支提交，并在提交前检查：

```powershell
git status --short
git diff --cached --name-status
$env:PYTHONPATH = "src"
python -m compileall -q src
python -m unittest discover -s tests -p 'test_*.py'
```

不要使用 `git reset --hard`、`git checkout -- .` 或 `git clean -fd`；如果发现两套工作树，
先保存差异，再决定合并或丢弃。
