"""构建不依赖网络的EquipEffi headless 便携包。

该脚本只打包已经构建好的wheel、安装脚本和运行文档，不尝试创建原生
安装程序，也不把用户数据、标准源文件或临时目录带入发布包。Qt桌面依赖
不内置在wheel/.pyz中，桌面安装应按README安装desktop extra。
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from io import BytesIO
from pathlib import Path
import zipfile
from typing import Sequence

try:
    from .build_lock import build_lock
    from .check_distribution_assets import audit_artifact
except ImportError:  # direct execution: ``python tools/build_portable_bundle.py``
    from build_lock import build_lock
    from check_distribution_assets import audit_artifact


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "equipeffi-portable.zip"


@dataclass(frozen=True)
class BundleResult:
    path: Path
    members: tuple[str, ...]
    sha256: str


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_info(name: str) -> zipfile.ZipInfo:
    """返回固定时间戳的ZIP条目，避免仅因打包时间导致校验变化。"""
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    mode = 0o755 if name.endswith(".sh") else 0o644
    info.external_attr = mode << 16
    return info


def _read_required(root: Path, relative: str) -> bytes:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"便携包所需文件不存在：{path}")
    return path.read_bytes()


def _runtime_notes(wheel_name: str, wheel_hash: str, zipapp_name: str = "") -> bytes:
    zipapp_note = f"可直接运行的zipapp：{zipapp_name}\n  python {zipapp_name} --status\n\n" if zipapp_name else ""
    text = f"""EquipEffi 便携运行包

本包包含 headless wheel 与安装/核验脚本，不是Windows原生安装程序。
运行前请确认目标系统已安装Python 3.12（项目支持的版本）。
PySide6 Qt桌面依赖不随wheel或.pyz内置；桌面用户请按README安装desktop extra。

文件：{wheel_name}
wheel SHA-256：{wheel_hash}

{zipapp_note}Windows PowerShell（在本目录执行）：
  .\\scripts\\install_windows.ps1 -WheelPath .\\{wheel_name}

Linux（在本目录执行）：
  sh scripts/install_linux.sh ./{wheel_name}

安装后可运行 `python -m equipeffi --status` 检查正式泵标准包和V6模板资源。
"""
    return text.encode("utf-8")


def _build_bundle_unlocked(
    wheel: Path,
    output: Path,
    *,
    root: Path = ROOT,
    zipapp: Path | None = None,
) -> BundleResult:
    """把指定wheel和跨平台运行资料打包为ZIP。"""
    wheel = Path(wheel).resolve()
    output = Path(output).resolve()
    root = Path(root).resolve()
    if not wheel.is_file():
        raise FileNotFoundError(f"未找到wheel：{wheel}")
    if wheel.suffix.lower() != ".whl":
        raise ValueError(f"wheel路径必须以.whl结尾：{wheel}")
    if output == wheel:
        raise ValueError("输出ZIP不能覆盖输入wheel")

    files: dict[str, bytes] = {
        wheel.name: wheel.read_bytes(),
        "scripts/install_windows.ps1": _read_required(root, "scripts/install_windows.ps1"),
        "scripts/install_native_windows.ps1": _read_required(root, "scripts/install_native_windows.ps1"),
        "scripts/install_linux.sh": _read_required(root, "scripts/install_linux.sh"),
        "scripts/README.md": _read_required(root, "scripts/README.md"),
        "tools/validate_portable_bundle.py": _read_required(root, "tools/validate_portable_bundle.py"),
        "README.md": _read_required(root, "README.md"),
    }
    if zipapp is not None:
        zipapp = Path(zipapp).resolve()
        if not zipapp.is_file() or zipapp.suffix.lower() != ".pyz":
            raise ValueError(f"zipapp路径必须指向存在的.pyz文件：{zipapp}")
        files[zipapp.name] = zipapp.read_bytes()
    wheel_hash = _sha256_bytes(files[wheel.name])
    files["运行说明.txt"] = _runtime_notes(wheel.name, wheel_hash, zipapp.name if zipapp else "")

    lines = ["# EquipEffi便携包SHA-256", "# 文件按ZIP中的路径列出"]
    for name in sorted(files):
        lines.append(f"{_sha256_bytes(files[name])}  {name}")
    files["SHA256SUMS.txt"] = ("\n".join(lines) + "\n").encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            archive.writestr(_zip_info(name), files[name])
    if (root / "pyproject.toml").is_file():
        asset_audit = audit_artifact(output, root=root)
        if not asset_audit.is_valid:
            output.unlink(missing_ok=True)
            raise ValueError("便携包运行资源审计失败: " + "; ".join(asset_audit.errors))
    members = tuple(sorted(files))
    return BundleResult(output, members, _sha256_file(output))


def build_bundle(
    wheel: Path,
    output: Path,
    *,
    root: Path = ROOT,
    zipapp: Path | None = None,
) -> BundleResult:
    """打包便携ZIP时占用项目级互斥锁，避免重复压缩任务并发运行。"""

    with build_lock(Path(root), operation="便携包构建"):
        return _build_bundle_unlocked(wheel, output, root=root, zipapp=zipapp)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建EquipEffi离线跨平台便携ZIP")
    parser.add_argument("--wheel", type=Path, required=True, help="已构建的 equipeffi wheel 路径")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="输出ZIP路径")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录")
    parser.add_argument("--zipapp", type=Path, help="可选：一并收录已构建的.pyz")
    args = parser.parse_args(argv)
    try:
        result = build_bundle(args.wheel, args.output, root=args.root, zipapp=args.zipapp)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"便携包：{result.path}")
    print(f"SHA-256：{result.sha256}")
    print(f"文件数：{len(result.members)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
