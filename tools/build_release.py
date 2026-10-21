"""构建并审计EquipEffi当前Qt/V6与正式泵分析运行链。

发布流程只依赖当前Python和项目声明的构建后端，不启动Qt窗口、不读取Excel
输入文件。默认使用 ``--no-index``，避免构建过程中意外访问网络；若本机
构建依赖未准备好，命令会明确失败而不是偷偷改变标准数据。

用法：
    python tools/build_release.py
    python tools/build_release.py --output-dir dist --portable-output dist/equipeffi-portable.zip
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence

try:
    from .audit_release import audit_project
    from .build_portable_bundle import build_bundle
    from .build_zipapp import build_zipapp
    from .build_lock import build_lock
    from .validate_portable_bundle import validate as validate_portable_bundle
except ImportError:  # direct execution: ``python tools/build_release.py``
    from audit_release import audit_project
    from build_portable_bundle import build_bundle
    from build_zipapp import build_zipapp
    from build_lock import build_lock
    from validate_portable_bundle import validate as validate_portable_bundle


ROOT = Path(__file__).resolve().parents[1]
# 固定构建纪元，避免 wheel 的 ZIP 时间戳随每次构建漂移；源码内容变化
# 仍会产生新的哈希。该日期与本项目的判定基准日期保持同一发布周期。
REPRODUCIBLE_BUILD_EPOCH = "1787443200"


def release_report_path(output_dir: Path) -> Path:
    """返回发布目录对应的稳定审计文件路径。"""

    target_dir = Path(output_dir).resolve()
    label = target_dir.name or "release"
    if label.lower().startswith("final_"):
        label = label[6:] or "latest"
    return target_dir / f"发布审计_{label}.json"


def write_release_report(payload: dict[str, object], output_dir: Path) -> Path:
    """把最终发布载荷保存为同目录的人可定位审计报告。

    报告不把自身的哈希写回内容，避免产生自引用漂移；其中记录的
    wheel/便携包哈希来自审计或便携包构建结果，可直接用于交付核对。
    """

    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    report = release_report_path(target_dir)
    report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return report


def build_wheel(root: Path = ROOT, output_dir: Path | None = None, *, timeout: int = 180) -> Path:
    """在指定目录构建wheel并返回新生成的文件路径。"""
    root = Path(root).resolve()
    with build_lock(root, operation="wheel构建"):
        target = (Path(output_dir) if output_dir else root / "dist").resolve()
        target.mkdir(parents=True, exist_ok=True)
        # setuptools 的 build_py 会按时间戳复用 root/build/lib；模板等二进制
        # 资源可能被表格工具或外部同步程序替换但保留较早时间戳，导致 wheel
        # 悄悄携带旧资源。build/是受控构建缓存，每次发布前清理可避免资源漂移。
        build_cache = root / "build"
        if build_cache.is_dir():
            shutil.rmtree(build_cache)
        before = {path.name: path.stat().st_mtime_ns for path in target.glob("*.whl")}
        command = [
            sys.executable, "-m", "pip", "wheel", str(root),
            "--no-deps", "--no-build-isolation", "--no-index",
            "--wheel-dir", str(target), "--disable-pip-version-check",
        ]
        build_env = os.environ.copy()
        build_env["SOURCE_DATE_EPOCH"] = REPRODUCIBLE_BUILD_EPOCH
        subprocess.run(command, cwd=str(root), check=True, timeout=timeout, env=build_env)
        candidates = [
            path for path in target.glob("*.whl")
            if path.name not in before or path.stat().st_mtime_ns > before[path.name]
        ]
        if not candidates:
            raise RuntimeError(f"构建命令成功但未在{target}发现新wheel")
        return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def build_sdist(root: Path = ROOT, output_dir: Path | None = None, *, timeout: int = 180) -> Path:
    """Build an offline source distribution and return the new archive."""
    root = Path(root).resolve()
    with build_lock(root, operation="sdist构建"):
        target = (Path(output_dir) if output_dir else root / "dist").resolve()
        target.mkdir(parents=True, exist_ok=True)
        before = {path.name: path.stat().st_mtime_ns for pattern in ("*.tar.gz", "*.tgz") for path in target.glob(pattern)}
        command = [
            sys.executable,
            "-c",
            "import os; from setuptools.build_meta import build_sdist; print(build_sdist(os.environ['EQUIPEFFI_SDIST_DEST']))",
        ]
        build_env = os.environ.copy()
        build_env["SOURCE_DATE_EPOCH"] = REPRODUCIBLE_BUILD_EPOCH
        build_env["EQUIPEFFI_SDIST_DEST"] = str(target)
        subprocess.run(command, cwd=str(root), check=True, timeout=timeout, env=build_env)
        candidates = [
            path for pattern in ("*.tar.gz", "*.tgz") for path in target.glob(pattern)
            if path.name not in before or path.stat().st_mtime_ns > before[path.name]
        ]
        if not candidates:
            raise RuntimeError(f"构建命令成功但未在{target}发现新sdist")
        return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建并审计EquipEffi wheel")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--timeout", type=int, default=180, help="构建超时秒数，默认180")
    parser.add_argument("--sdist", action="store_true", help="同时构建并审计源码分发包")
    parser.add_argument("--portable-output", type=Path, help="审计通过后同时生成离线便携ZIP")
    parser.add_argument(
        "--zipapp-output",
        type=Path,
        help="便携ZIP内的.pyz输出路径；仅在指定--portable-output时使用，默认与ZIP同名改为.pyz",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else root / "dist"
    try:
        wheel = build_wheel(root, output_dir, timeout=args.timeout)
        sdist = build_sdist(root, output_dir, timeout=args.timeout) if args.sdist else None
        audit_kwargs = {"wheel": wheel}
        if sdist is not None:
            audit_kwargs["sdist"] = sdist
        audit = audit_project(root, **audit_kwargs)
        payload = {"wheel": str(wheel), "audit": asdict(audit)}
        if sdist is not None:
            payload["sdist"] = str(sdist)
        if audit.is_valid and args.portable_output:
            portable_output = Path(args.portable_output).resolve()
            zipapp_output = (
                Path(args.zipapp_output).resolve()
                if args.zipapp_output is not None
                else portable_output.with_suffix(".pyz")
            )
            if zipapp_output == portable_output:
                raise ValueError("--zipapp-output不能与--portable-output相同")
            if zipapp_output == Path(wheel).resolve():
                raise ValueError("--zipapp-output不能覆盖刚生成的wheel")
            zipapp = build_zipapp(root, zipapp_output)
            portable = build_bundle(wheel, portable_output, root=root, zipapp=zipapp)
            payload["zipapp"] = str(zipapp)
            payload["portable"] = asdict(portable)
            portable_validation = validate_portable_bundle(portable.path)
            payload["portable_validation"] = portable_validation
            if not portable_validation.get("is_valid"):
                raise RuntimeError("便携ZIP校验失败: " + "; ".join(portable_validation.get("errors", [])))
        report_path = release_report_path(output_dir)
        payload["audit_report"] = str(report_path)
        write_release_report(payload, output_dir)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0 if audit.is_valid else 1
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
