# 安装与构建

EquipEffi Windows V1 的正式桌面入口是 PySide6 Qt；正式业务标准资源是 V6 模板与 GB 19762 离心泵分析服务。wheel 和 .pyz 提供不依赖第三方包的 headless 核心，Qt 依赖通过 desktop extra 安装。

## 从源码安装正式桌面程序

在仓库根目录执行：

~~~powershell
python -m pip install ".[desktop]"
python -m equipeffi --status
python -m equipeffi --qt
~~~

无参数启动和 --gui 也是同一个 PySide6 Qt 桌面程序。--status 不创建窗口或用户数据库；它检查 Qt、V6 模板以及两个正式泵标准包，全部可用时退出码为 0。

如果使用 wheel 安装桌面程序，可在能访问软件索引或已配置 PySide6 wheelhouse 的环境中安装：

~~~powershell
python -m pip install "dist\equipeffi-0.2.1-py3-none-any.whl[desktop]"
python -m equipeffi --status
python -m equipeffi --qt
~~~

## 构建 wheel、zipapp 与便携包

先安装 `setuptools>=68` 和 `wheel`；以下 wheel 构建使用离线、非隔离模式，不会临时下载构建依赖。随后执行：

~~~powershell
python tools/build_release.py --output-dir dist
python tools/build_zipapp.py --output dist/equipeffi.pyz
python tools/build_portable_bundle.py --wheel dist/equipeffi-0.2.1-py3-none-any.whl --zipapp dist/equipeffi.pyz --output dist/equipeffi-portable.zip
python tools/validate_portable_bundle.py dist/equipeffi-portable.zip
~~~

便携 ZIP 包含 headless wheel、校验清单和安装说明；.pyz 是可选成员。它不内置 PySide6。Windows/Linux wheel 安装脚本用于离线安装核心包；如需 Qt 桌面，请另外安装 desktop extra。运行状态命令可用于检查目标环境：

~~~powershell
python -m equipeffi --status
~~~

## Windows 原生 Qt 包

本轮 Windows 验证使用 Python 3.12、PySide6 6.8.3 和 PyInstaller 6.22.3。用独立构建环境，并限制构建时的 PATH，避免把其他软件的同名 DLL 收进包中：

~~~powershell
py -3.12 -m venv .native-build
$buildPython = (Resolve-Path .native-build/Scripts/python.exe).Path
& $buildPython -m pip install PySide6==6.8.3 PyInstaller==6.22.3
$buildOriginalPath = $env:PATH
$buildWindowsDir = [Environment]::GetFolderPath('Windows')
try {
    $env:PATH = "$buildWindowsDir\System32;$buildWindowsDir"
    & $buildPython tools/build_native.py --python $buildPython --report dist/native/native-windows-build.json --zip-output dist/native/equipeffi-windows-qt.zip
} finally {
    $env:PATH = $buildOriginalPath
}
~~~

构建工具会运行实际 EXE 的 `--status`；Qt、V6 或正式泵资源不可用时返回失败且不生成 ZIP。还应把产物复制到独立目录，清空 Python 路径后运行 EXE，检查桌面操作。更换 Qt 或构建器版本需重新做该验证，不能只凭构建命令成功判断可交付。本机隔离验证不等同于干净 Windows 机器验证。

安装已有原生 ZIP 时，可先解包到临时目录校验，再复制到用户目录：

~~~powershell
.\scripts\install_native_windows.ps1 -PackagePath .\dist\native\equipeffi-windows-qt.zip -CreateShortcut
~~~

原生包安装后通过 equipeffi.exe --status 检查 Qt、V6 模板和正式泵标准包。跨平台源码/包安装与 Windows 原生包均使用 PySide6 Qt，不提供 Web、Tk 或 Android 发布入口。
