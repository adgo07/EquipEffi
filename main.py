"""设备能效分析入口。

默认提供参数判定CLI；使用 ``python main.py --gui`` 启动跨平台桌面窗口MVP，或用
``python main.py --web`` 启动不依赖Tk的浏览器窗口。
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    from equipeffi import __version__

    if len(sys.argv) == 1:
        print(f"EquipEffi {__version__}: 15类V4公共接口和参数判定服务已就绪。")
        print("启动窗口: python main.py --gui")
        print("启动浏览器窗口: python main.py --web --open-browser")
        print("查看设备类型: python main.py --list-device-types")
        print("查看能力状态: python main.py --status")
        print("查看字段契约: python main.py --device-type transformer --schema")
        print("执行判定: python main.py --device-type transformer --json '{...}'")
        return 0
    # 根目录入口只做源码路径兼容；全部参数语义、错误处理和示例均由
    # 安装包入口维护，避免 tools/evaluate_device.py 形成第二套CLI。
    from equipeffi.entrypoint import main as package_main

    return package_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
