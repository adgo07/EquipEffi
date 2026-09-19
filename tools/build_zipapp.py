"""从源码生成可直接用 ``python`` 运行的EquipEffi ``.pyz``。

该格式适合Linux服务、Windows便携运行和后续Android桥接层的原型验证；
它不需要安装wheel，也不包含第三方依赖。桌面Tk仍只在显式使用``--gui``时导入。
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile
from typing import Sequence

try:
    from .build_lock import build_lock
except ImportError:  # direct execution: ``python tools/build_zipapp.py``
    from build_lock import build_lock


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "equipeffi"
DEFAULT_OUTPUT = ROOT / "dist" / "equipeffi.pyz"


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o755 << 16 if name == "__main__.py" else 0o644 << 16
    return info


def _build_zipapp_unlocked(source_root: Path = ROOT, output: Path = DEFAULT_OUTPUT) -> Path:
    source_root = Path(source_root).resolve()
    package_root = source_root / "src" / "equipeffi"
    output = Path(output).resolve()
    if not package_root.is_dir():
        raise FileNotFoundError(f"未找到源码包目录：{package_root}")
    files: dict[str, bytes] = {
        "__main__.py": (
            "from equipeffi.entrypoint import main\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    raise SystemExit(main())\n"
        ).encode("utf-8")
    }
    for path in sorted(package_root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        relative = path.relative_to(source_root / "src").as_posix()
        files[relative] = path.read_bytes()
    if "equipeffi/entrypoint.py" not in files or "equipeffi/standard_manifest.json" not in files:
        raise FileNotFoundError("源码包缺少入口或standard_manifest.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            archive.writestr(_zip_info(name), files[name])
    return output


def build_zipapp(source_root: Path = ROOT, output: Path = DEFAULT_OUTPUT) -> Path:
    """生成zipapp时占用项目级互斥锁，避免重复压缩任务并发运行。"""

    with build_lock(Path(source_root), operation="zipapp构建"):
        return _build_zipapp_unlocked(source_root, output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建EquipEffi可直接运行的.pyz")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        output = build_zipapp(args.root, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"zipapp：{output}")
    print(f"SHA-256：{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
