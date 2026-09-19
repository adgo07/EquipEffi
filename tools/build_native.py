"""构建可审计的桌面原生发布目录。

本工具只负责调用目标机已有的 PyInstaller，不下载依赖、不修改标准数据，
并把包内 JSON/XLSX 资源显式加入构建命令。当前支持在 Windows/Linux 上构建
对应平台的 onedir 目录；Android 仍使用 JSONL 桥接，不把 Tk 打包进移动端。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from typing import Sequence

try:
    from .build_lock import build_lock
except ImportError:  # direct execution
    from build_lock import build_lock


ROOT = Path(__file__).resolve().parents[1]


def _native_zip_info(name: str) -> zipfile.ZipInfo:
    """生成固定时间戳的ZIP条目，保证相同构建输入得到相同封装结果。"""

    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (0o755 if name.endswith(".sh") else 0o644) << 16
    return info


def package_native(
    executable: Path,
    output: Path,
    *,
    report: Path | None = None,
) -> dict[str, object]:
    """将PyInstaller onedir目录封装为可复现ZIP并返回清单摘要。

    ``executable``决定要封装的目录；目录名（通常为``equipeffi``）保留为
    ZIP顶层目录。构建报告可选地放在ZIP根目录，便于审计工具直接读取。
    """

    executable = Path(executable).resolve()
    bundle_root = executable.parent
    output = Path(output).resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"原生启动文件不存在：{executable}")
    if output.is_relative_to(bundle_root):
        raise ValueError("原生ZIP输出不能放在待封装的onedir目录内")
    if report is not None:
        report = Path(report).resolve()
        if not report.is_file():
            raise FileNotFoundError(f"原生构建报告不存在：{report}")
    files = sorted(path for path in bundle_root.rglob("*") if path.is_file())
    archive_files: list[tuple[str, Path]] = [
        (f"{bundle_root.name}/{path.relative_to(bundle_root).as_posix()}", path)
        for path in files
    ]
    if report is not None:
        archive_files.append((report.name, report))
    archive_files.sort(key=lambda item: item[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in archive_files:
            archive.writestr(_native_zip_info(name), path.read_bytes())
    temporary.replace(output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "path": str(output),
        "members": [name for name, _ in archive_files],
        "sha256": digest,
    }


def _data_arg(source: Path, target: str, *, path_separator: str) -> str:
    return f"{source}{path_separator}{target}"


def build_native_command(
    root: Path = ROOT,
    output_dir: Path | None = None,
    *,
    tool: str | Sequence[str] = "pyinstaller",
    name: str = "equipeffi",
    path_separator: str | None = None,
) -> tuple[list[str], Path]:
    """返回不执行的PyInstaller命令和预期exe/启动文件路径。"""

    root = Path(root).resolve()
    destination = (Path(output_dir) if output_dir else root / "dist" / "native").resolve()
    # 不能直接把带相对导入的 equipeffi/entrypoint.py 当脚本交给
    # PyInstaller；独立包装器先以包方式导入它。
    entry = root / "tools" / "native_entrypoint.py"
    package = root / "src" / "equipeffi"
    manifest = package / "standard_manifest.json"
    resources = package / "resources"
    if not entry.is_file() or not manifest.is_file() or not resources.is_dir():
        raise FileNotFoundError("源码包缺少PyInstaller包装器、standard_manifest.json或resources目录")
    separator = path_separator or (";" if __import__("os").name == "nt" else ":")
    distpath = destination / "dist"
    workpath = destination / "build"
    specpath = destination / "spec"
    tool_prefix = [tool] if isinstance(tool, str) else list(tool)
    command = [
        *tool_prefix,
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        name,
        "--distpath",
        str(distpath),
        "--workpath",
        str(workpath),
        "--specpath",
        str(specpath),
        "--paths",
        str(root / "src"),
        "--add-data",
        _data_arg(manifest, "equipeffi", path_separator=separator),
        "--add-data",
        _data_arg(resources, "equipeffi/resources", path_separator=separator),
        "--collect-submodules",
        "equipeffi",
        str(entry),
    ]
    executable = distpath / name / (f"{name}.exe" if separator == ";" else name)
    return command, executable


def build_native(
    root: Path = ROOT,
    output_dir: Path | None = None,
    *,
    tool: str | None = None,
    python_path: str | None = None,
    gui_python_path: str | None = None,
    name: str = "equipeffi",
    timeout: int = 600,
) -> dict[str, object]:
    """调用PyInstaller构建当前平台的onedir目录并返回构建摘要。"""

    if python_path:
        selected_tool: str | Sequence[str] = [python_path, "-m", "PyInstaller"]
    else:
        selected_tool = tool or shutil.which("pyinstaller") or ""
    if not selected_tool:
        raise FileNotFoundError("未找到PyInstaller；请在目标平台安装PyInstaller后重试")
    command, executable = build_native_command(root, output_dir, tool=selected_tool, name=name)
    with build_lock(Path(root).resolve(), operation="原生构建"):
        subprocess.run(command, cwd=str(Path(root).resolve()), check=True, timeout=timeout)
    if not executable.exists():
        raise RuntimeError(f"PyInstaller命令成功但未找到预期启动文件：{executable}")
    digest = __import__("hashlib").sha256(executable.read_bytes()).hexdigest()
    warn_path = executable.parents[2] / "build" / name / f"warn-{name}.txt"
    warning_text = warn_path.read_text(encoding="utf-8", errors="replace") if warn_path.is_file() else ""
    # 静态PyInstaller警告不足以证明窗口可启动：Tcl/Tk运行库可能仍缺失。
    # 诊断工具只读检查目标构建Python，不启动主窗口。
    try:
        # 直接执行``python tools/build_native.py``时，sys.path首项是tools目录，
        # 将仓库根目录补入后才能导入同目录的诊断模块；作为模块导入时无影响。
        if str(Path(root).resolve()) not in sys.path:
            sys.path.insert(0, str(Path(root).resolve()))
        from tools.check_gui_environment import diagnose

        requested_python = gui_python_path or python_path
        if requested_python and Path(requested_python).resolve() != Path(sys.executable).resolve():
            diagnostic_script = Path(root).resolve() / "tools" / "check_gui_environment.py"
            completed = subprocess.run(
                [requested_python, str(diagnostic_script)],
                cwd=str(Path(root).resolve()),
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            gui_environment = json.loads(completed.stdout)
        else:
            gui_environment = diagnose()
    except Exception as exc:  # 构建脚本作为单文件复制时仍能返回可审计结果
        gui_environment = {"ready": False, "error": f"GUI环境诊断失败：{exc}"}
    gui_capable = (
        "missing module named tkinter" not in warning_text.lower()
        and bool(gui_environment.get("ready"))
    )
    return {
        "platform": "windows" if executable.suffix.lower() == ".exe" else "linux",
        "name": name,
        "executable": str(executable),
        "sha256": digest,
        "gui_capable": gui_capable,
        # Even when PyInstaller cannot bundle Tk, the packaged ``--gui``
        # entrypoint can still serve the framework-free Web window.
        "presentation_mode": "native_tk" if gui_capable else "web_fallback",
        "gui_environment_ready": bool(gui_environment.get("ready")),
        "gui_environment_error": str(gui_environment.get("error", "")),
        "warnings_file": str(warn_path) if warn_path.is_file() else "",
        "command": command,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建EquipEffi当前平台PyInstaller桌面目录")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / "native")
    parser.add_argument("--tool", default="", help="PyInstaller可执行文件路径；默认从PATH查找")
    parser.add_argument("--python", dest="python_path", default="", help="用指定Python执行`-m PyInstaller`，可用于带Tk的环境")
    parser.add_argument("--gui-python", default="", help="GUI预检使用的Python；默认跟随--python或当前Python")
    parser.add_argument("--name", default="equipeffi")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--report", type=Path, help="可选：将构建摘要写入JSON")
    parser.add_argument("--zip-output", type=Path, help="可选：将生成的onedir目录封装为可复现ZIP")
    args = parser.parse_args(argv)
    try:
        result = build_native(
            args.root,
            args.output_dir,
            tool=args.tool or None,
            python_path=args.python_path or None,
            gui_python_path=args.gui_python or None,
            name=args.name,
            timeout=args.timeout,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError, RuntimeError) as exc:
        parser.error(str(exc))
    if args.zip_output:
        # 报告作为ZIP旁车文件保留，避免把包含ZIP自身SHA-256的报告再嵌入ZIP
        # 形成循环哈希；`--report`会在下面写入包含package摘要的完整报告。
        result["package"] = package_native(Path(str(result["executable"])), args.zip_output)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        report = Path(args.report).resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
