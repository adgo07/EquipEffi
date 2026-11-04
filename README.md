# EquipEffi 设备能效分析工具

EquipEffi 当前正式桌面产品使用 PySide6 Qt。标准映射、配套表值与专业解释见[标准档案总入口](docs/standards/README.md)；当前产品范围见 [V1_SCOPE.md](V1_SCOPE.md)。

## 当前主线功能（0.2.2候选，未正式发布）

- 按 **GB 19762—2025《离心泵能效限定值及能效等级》**评价清水离心泵和石油化工离心泵。
- 按 **GB 20052—2024**评价电力变压器，按 **GB 18613—2020**评价该标准覆盖的电动机；三类设备默认开放。
- 单台分析在形成合法业务结论后自动保存为独立历史记录；历史记录保存当时的输入、结果和标准依据。
- Excel 批量分析使用软件内置的 **V6.3 全设备统一模板**，接通「离心泵」「变压器」「电动机」工作表：每行调用与单台相同的业务内核，另存新的结果工作簿，每次工作簿评价保存一条批次记录。其他设备工作表保留且不参与评价。
- 电动机新输入采用额定效率（1%～100%）和额定电压（V）；旧V6/V6.1/V6.2继续按原契约兼容，V6.2的实测效率/kV语义与历史快照不追溯改写。
- 新分析日期自动取本机当天日期。界面显示供普通用户阅读的评价结论；系统异常会作为执行失败处理，不伪装成业务结论。

主线沿用已授权的离心泵、变压器和GB18613电动机SUPPORTED配置。高压/永磁电机仍仅为接入设计；其他标准资料存在不代表已开放。支持与发布差异以 [V1_SCOPE.md](V1_SCOPE.md) 为准。

当前正式发布仍为 [v0.2.1 Windows免安装版](https://github.com/adgo07/EquipEffi/releases/tag/v0.2.1)：泵SUPPORTED、变压器IMPLEMENTED且默认开放、电机入口默认关闭、模板V6.1。它不包含本轮主线的新输入与模板修正。本轮候选验证见[收口记录](docs/governance/THREE_DEVICE_CANDIDATE_20261103.md)，暂不正式发布。

## Windows 安装与运行

使用 Python **3.12**。在 PowerShell 中从源码安装桌面依赖并启动：

    git clone https://github.com/adgo07/EquipEffi.git
    cd EquipEffi
    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install ".[desktop]"
    .\.venv\Scripts\python.exe -m equipeffi

最后一条命令会启动正式 Qt 桌面窗口。也可以使用虚拟环境中的 equipeffi.exe 启动；无参数启动就是 Qt 产品入口。

在应用「Excel导入」页面，先输出空白模板，再填写「离心泵」「变压器」或「电动机」工作表并选择该文件进行批量评价。软件自动检查工作簿，默认生成带时间戳的新结果文件，不覆盖原始输入；无需预设行数或逐工作表扩容。

## 当前限制与旧入口状态

产品面向 Windows Qt 桌面使用。已有免安装ZIP发布；尚无安装器、数字签名或自动更新器。另一台干净Windows及真实125%系统缩放验证仍待补齐，本机或应用级缩放验证不替代它们。

旧 Tk、Web、ApplicationApi、JSON/JSONL 客户端、Android 桥接和 V4 工作簿处理链已退出维护并删除。命令行保留无参数启动、`--qt` / `--gui`、`--help` 和 `--status`；`--status` 检查 Qt、统一模板及泵、变压器、电动机服务的可用性。无界面集成使用 `create_pump_analysis_service(with_persistence=False)`，与桌面共用正式计算链。
