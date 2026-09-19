"""PyInstaller启动包装器；避免把带包内相对导入的模块当作顶层脚本执行。"""
from equipeffi.entrypoint import main


if __name__ == "__main__":
    raise SystemExit(main())
