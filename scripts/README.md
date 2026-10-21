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

在本机已安装项目构建依赖的环境中执行：

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

在目标 Windows Python 环境已安装 PyInstaller 与 PySide6 时，可生成当前 Qt 桌面程序的 onedir 包：

~~~powershell
python tools/build_native.py --python .venv\Scripts\python.exe --report dist/native/native-windows-build.json --zip-output dist/native/equipeffi-windows-qt.zip
python tools/audit_release.py --native-report dist/native/native-windows-build.json
~~~

安装已有原生 ZIP 时，可先解包到临时目录校验，再复制到用户目录：

~~~powershell
.\scripts\install_native_windows.ps1 -PackagePath .\dist\native\equipeffi-windows-qt.zip -CreateShortcut
~~~

原生包安装后通过 equipeffi.exe --status 检查 Qt、V6 模板和正式泵标准包。跨平台源码/包安装与 Windows 原生包均使用 PySide6 Qt，不提供 Web、Tk 或 Android 发布入口。
