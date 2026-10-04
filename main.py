"""设备能效分析入口。

无参数启动**正式 Windows 产品 Shell**：PySide6 Qt 桌面窗口。
``--gui`` 与 ``--qt`` 是等价的显式别名。

``--web`` / ``--json`` / ``--jsonl`` 仍可用，但属**非正式 adapter**
（compatibility / development surface），不属于 Windows V1 正式用户表面。
legacy Tk 不再是任何用户产品入口。
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    # 根目录入口只做源码路径兼容；全部参数语义、错误处理和示例均由
    # 安装包入口维护，避免形成第二套 CLI。
    from equipeffi.entrypoint import main as package_main

    return package_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
