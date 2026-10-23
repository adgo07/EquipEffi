"""构建可审计的桌面原生发布目录。

本工具只负责调用目标机已有的 PyInstaller，不下载依赖、不修改标准数据，
并把包内 JSON/XLSX 资源显式加入构建命令。当前支持在 Windows/Linux 上构建
对应平台的 onedir 目录；构建完成后通过打包后的 ``--status`` 检查 Qt/V6 和正式泵服务。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from typing import Sequence

try:
    from .build_lock import build_lock
    from .check_distribution_assets import audit_artifact, runtime_asset_paths
except ImportError:  # direct execution
    from build_lock import build_lock
    from check_distribution_assets import audit_artifact, runtime_asset_paths


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
        *(["--windowed"] if separator == ";" else []),
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
        "--collect-submodules",
        "equipeffi",
        str(entry),
    ]
    for asset in runtime_asset_paths(root):
        relative = asset.relative_to(package).parent.as_posix()
        destination = f"equipeffi/{relative}" if relative != "." else "equipeffi"
        command.extend(["--add-data", _data_arg(asset, destination, path_separator=separator)])
    executable = distpath / name / (f"{name}.exe" if separator == ";" else name)
    return command, executable


def build_native(
    root: Path = ROOT,
    output_dir: Path | None = None,
    *,
    tool: str | None = None,
    python_path: str | None = None,
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
    asset_audit = audit_artifact(executable.parent, root=Path(root))
    if not asset_audit.is_valid:
        raise RuntimeError("native目录运行资源审计失败: " + "; ".join(asset_audit.errors))
    digest = __import__("hashlib").sha256(executable.read_bytes()).hexdigest()
    warn_path = executable.parents[2] / "build" / name / f"warn-{name}.txt"
    # 用构建后的真实启动程序运行无GUI的 --status，核验打包后 Qt、V6资源和正式泵服务。
    # 该诊断不会创建 QApplication，也不会迁移或写入用户数据库。
    try:
        status_environment = os.environ.copy()
        status_environment["PYTHONIOENCODING"] = "utf-8"
        # windowed executable 的 sys.stdout/sys.stderr 为 None；状态通过专用文件
        # 回传，避免构建核验依赖控制台管道。
        with tempfile.TemporaryDirectory(
                prefix="equipeffi-native-status-"
            ) as status_dir:
            status_file = Path(status_dir) / "status.json"
            status = subprocess.run(
                [str(executable), "--status", "--status-file", str(status_file)],
                cwd=str(Path(root).resolve()),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=status_environment,
                timeout=45,
            )
            if not status_file.is_file():
                detail = status.stderr.strip() or status.stdout.strip()
                suffix = f"；子进程输出：{detail}" if detail else ""
                raise RuntimeError(
                    "打包后的 --status 未生成状态文件 "
                    f"（返回码 {status.returncode}）{suffix}"
                )
            status_payload = json.loads(status_file.read_text(encoding="utf-8"))
        desktop = status_payload.get("desktop", {})
        qt_capable = (
            isinstance(desktop, dict)
            and desktop.get("surface") == "PySide6 Qt"
            and desktop.get("available") is True
        )
        status_ready = status.returncode == 0 and status_payload.get("ready") is True
        qt_environment = {
            "surface": desktop.get("surface", "") if isinstance(desktop, dict) else "",
            "available": qt_capable,
            "status_ready": status_ready,
            "template_available": status_payload.get("template", {}).get("available") is True,
            "pump_profiles": status_payload.get("pump_profiles", {}),
        }
        status_error = ""
        if not status_ready:
            detail = status.stderr.strip() or status.stdout.strip()
            status_error = detail or f"--status返回码{status.returncode}"
    except Exception as exc:  # 构建可保留诊断结果，由发行审计阻止不完整产物
        qt_capable = False
        status_ready = False
        qt_environment = {"surface": "PySide6 Qt", "available": False, "status_ready": False}
        status_error = f"打包后--status检查失败：{type(exc).__name__}: {exc}"
    return {
        "platform": "windows" if executable.suffix.lower() == ".exe" else "linux",
        "name": name,
        "executable": str(executable),
        "sha256": digest,
        "qt_capable": qt_capable,
        "presentation_mode": "pyside6_qt" if qt_capable else "unavailable",
        "status_ready": status_ready,
        "qt_environment": qt_environment,
        "status_smoke_error": status_error,
        "warnings_file": str(warn_path) if warn_path.is_file() else "",
        "command": command,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建EquipEffi当前平台PyInstaller桌面目录")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / "native")
    parser.add_argument("--tool", default="", help="PyInstaller可执行文件路径；默认从PATH查找")
    parser.add_argument("--python", dest="python_path", default="", help="用指定Python执行`-m PyInstaller`；默认用当前解释器")
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
            name=args.name,
            timeout=args.timeout,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError, RuntimeError) as exc:
        parser.error(str(exc))
    if args.zip_output and result.get("status_ready") is True:
        # 报告作为ZIP旁车文件保留，避免把包含ZIP自身SHA-256的报告再嵌入ZIP
        # 形成循环哈希；`--report`会在下面写入包含package摘要的完整报告。
        result["package"] = package_native(Path(str(result["executable"])), args.zip_output)
        package_audit = audit_artifact(Path(str(result["package"]["path"])), root=args.root)
        if not package_audit.is_valid:
            parser.error("native ZIP运行资源审计失败: " + "; ".join(package_audit.errors))
    elif args.zip_output:
        result["package_error"] = "打包后的 --status 未就绪，未生成 native ZIP"
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        report = Path(args.report).resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result.get("status_ready") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
