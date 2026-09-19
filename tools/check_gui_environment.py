"""诊断当前 Python/Tk 运行环境是否适合构建桌面窗口。

该脚本只做只读检查，不启动主窗口、不修改环境变量，也不安装依赖。
它用于原生构建前的门禁：PyInstaller 能找到 ``tkinter`` 并不代表 Tcl/Tk
运行库可用，因此同时尝试创建 Tcl 解释器并记录候选库路径。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Sequence


def _existing(paths: list[Path]) -> list[str]:
    return [str(path) for path in paths if path.is_file() or path.is_dir()]


def diagnose() -> dict[str, Any]:
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "prefix": sys.prefix,
        "tkinter_spec": bool(importlib.util.find_spec("tkinter")),
        "tkinter_imported": False,
        "tcl_interpreter": False,
        "tcl_version": "",
        "tcl_library_env": os.environ.get("TCL_LIBRARY", ""),
        "tk_library_env": os.environ.get("TK_LIBRARY", ""),
        "candidate_tcl_paths": [],
        "candidate_tk_paths": [],
        "ready": False,
        "error": "",
    }
    prefix = Path(sys.prefix)
    tcl_env = Path(os.environ["TCL_LIBRARY"]) if os.environ.get("TCL_LIBRARY") else None
    tk_env = Path(os.environ["TK_LIBRARY"]) if os.environ.get("TK_LIBRARY") else None
    result["candidate_tcl_paths"] = _existing([
        *( [tcl_env] if tcl_env else [] ),
        prefix / "tcl" / "tcl8.6",
        prefix / "tcl" / "tcl8",
        prefix / "lib" / "tcl8.6",
    ])
    result["candidate_tk_paths"] = _existing([
        *( [tk_env] if tk_env else [] ),
        prefix / "tcl" / "tk8.6",
        prefix / "tcl" / "tk8",
        prefix / "lib" / "tk8.6",
    ])
    if not result["tkinter_spec"]:
        result["error"] = "当前Python未提供tkinter模块"
        return result
    try:
        import tkinter  # type: ignore

        result["tkinter_imported"] = True
        result["tkinter_file"] = str(Path(tkinter.__file__).resolve())
        # Tcl() 不要求桌面显示服务器，适合在构建机上做运行库检测。
        interpreter = tkinter.Tcl()
        result["tcl_interpreter"] = True
        result["tcl_version"] = str(interpreter.eval("info patchlevel"))
        result["ready"] = True
    except Exception as exc:  # TclError、ImportError及目标机其他加载错误
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查Python/Tk是否可用于原生GUI构建")
    parser.add_argument("--output", type=Path, help="可选：保存JSON诊断报告")
    parser.add_argument("--require-ready", action="store_true", help="未通过时返回非零状态")
    args = parser.parse_args(argv)
    payload = json.dumps(diagnose(), ensure_ascii=False, indent=2)
    print(payload)
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + "\n", encoding="utf-8")
    return 0 if not args.require_ready or json.loads(payload)["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
