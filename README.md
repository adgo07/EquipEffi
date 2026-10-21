# EquipEffi 设备能效分析工具

EquipEffi 当前正式桌面产品使用 PySide6 Qt。标准映射、配套表值与专业解释见[标准档案总入口](docs/standards/README.md)；当前产品范围见 [V1_SCOPE.md](V1_SCOPE.md)。

## 当前正式功能

- 按 **GB 19762—2025《离心泵能效限定值及能效等级》**评价清水离心泵和石油化工离心泵。
- 单台分析在形成合法业务结论后自动保存为独立历史记录；历史记录保存当时的输入、结果和标准依据。
- Excel 批量分析使用软件内置的 **V6 全设备统一模板**。当前只接通「离心泵」工作表：软件将每行交给同一正式泵分析服务计算，另存为新的结果工作簿，并保存一条批次记录。其他设备工作表保留在结果文件中，不在本版本中评价。
- 新分析日期自动取本机当天日期。界面显示供普通用户阅读的评价结论；系统异常会作为执行失败处理，不伪装成业务结论。

产品正式支持范围是 **pump_water**（清水离心泵）和 **pump_chemical**（石油化工离心泵）。仓库中保留的其他设备标准资料、计算器和历史数据不代表它们已成为当前产品功能。

## Windows 安装与运行

使用 Python **3.12**。在 PowerShell 中从源码安装桌面依赖并启动：

    git clone https://github.com/adgo07/EquipEffi.git
    cd EquipEffi
    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install ".[desktop]"
    .\.venv\Scripts\python.exe -m equipeffi

最后一条命令会启动正式 Qt 桌面窗口。也可以使用虚拟环境中的 equipeffi.exe 启动；无参数启动就是 Qt 产品入口。

在应用「Excel导入」页面，先输出空白模板，再填写「离心泵」工作表并选择该文件进行批量评价。软件自动检查工作簿，默认生成带时间戳的新结果文件，不覆盖原始输入；无需预设行数或逐工作表扩容。

## 当前限制与旧入口状态

正式产品面向 Windows Qt 桌面使用。当前评价范围只有 GB 19762—2025 离心泵；V6 模板的其他设备工作表尚未接通评价。当前仓库未提供面向普通用户的独立安装器或已发布安装包，以上为从源码安装的方式。

旧 Tk、Web、ApplicationApi、JSON/JSONL 客户端、Android 桥接和 V4 工作簿处理链已退出维护并删除。命令行保留无参数启动、`--qt` / `--gui`、`--help` 和 `--status`；`--status` 检查 Qt、V6 模板及两个正式泵 Profile 的可用性。无界面集成使用 `create_pump_analysis_service(with_persistence=False)`，与桌面共用正式计算链。
