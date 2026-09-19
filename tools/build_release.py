"""构建并审计EquipEffi核心wheel（Windows/Linux通用）。

发布流程只依赖当前Python和项目声明的构建后端，不初始化Tk、不读取Excel
输入文件。默认使用 ``--no-index``，避免构建过程中意外访问网络；若本机
构建依赖未准备好，命令会明确失败而不是偷偷改变标准数据。

用法：
    python tools/build_release.py
    python tools/build_release.py --output-dir dist --skip-review
    python tools/build_release.py --output-dir dist --review-book outputs/review.xlsx
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
    from .audit_release import _default_review_book, audit_project
    from .build_portable_bundle import build_bundle
    from .build_zipapp import build_zipapp
    from .build_lock import build_lock
    from .validate_portable_bundle import validate as validate_portable_bundle
except ImportError:  # direct execution: ``python tools/build_release.py``
    from audit_release import _default_review_book, audit_project
    from build_portable_bundle import build_bundle
    from build_zipapp import build_zipapp
    from build_lock import build_lock
    from validate_portable_bundle import validate as validate_portable_bundle


ROOT = Path(__file__).resolve().parents[1]
V4_TEMPLATE_NAME = "设备能效分析空白模板_重构版V4_20260825.xlsx"
# 固定构建纪元，避免 wheel 的 ZIP 时间戳随每次构建漂移；源码内容变化
# 仍会产生新的哈希。该日期与本项目的判定基准日期保持同一发布周期。
REPRODUCIBLE_BUILD_EPOCH = "1787443200"


def sync_runtime_template(root: Path, output_dir: Path) -> Path | None:
    """Copy the protected runtime V4 template alongside release artifacts.

    The template is a first-class deliverable, but setuptools only places it
    inside the wheel.  Keeping a standalone copy in the release directory
    makes the workbook users download match the code package.  Missing source
    templates are tolerated for isolated unit-test roots; a source/template
    path is never overwritten.
    """
    source = Path(root) / "src" / "equipeffi" / "resources" / "templates" / V4_TEMPLATE_NAME
    if not source.is_file():
        return None
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / V4_TEMPLATE_NAME
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def sync_review_book(review_book: Path | None, output_dir: Path) -> Path | None:
    """Copy the audited human-readable standard workbook into a release dir.

    The review workbook is an explicit release deliverable, but it lives
    outside the Python wheel.  Copying it here keeps the workbook, template,
    audit JSON and executable artifacts in one independently reproducible
    directory.  A source already located in ``output_dir`` is left untouched;
    the original review file is never modified.
    """

    if review_book is None:
        return None
    source = Path(review_book).resolve()
    # 与 ``sync_runtime_template`` 一致：审计层负责报告缺失校对册，
    # 发布层不因可选的人可读副本缺失而改变原有的非强制构建语义。
    # ``--require-activation`` 仍会由 activation gate 阻断该发布。
    if not source.is_file():
        return None
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if source != target:
        shutil.copy2(source, target)
    return target


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建并审计EquipEffi wheel")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--timeout", type=int, default=180, help="wheel构建超时秒数，默认180")
    parser.add_argument("--portable-output", type=Path, help="审计通过后同时生成离线便携ZIP")
    parser.add_argument(
        "--zipapp-output",
        type=Path,
        help="便携ZIP内的.pyz输出路径；仅在指定--portable-output时使用，默认与ZIP同名改为.pyz",
    )
    parser.add_argument(
        "--require-activation",
        action="store_true",
        help="要求校对册已就绪且所有标准包active，否则构建以失败退出",
    )
    parser.add_argument(
        "--review-book",
        type=Path,
        help="人工校对册路径；未指定时按最新交付目录、历史交付目录顺序自动寻找",
    )
    parser.add_argument("--skip-review", action="store_true", help="跳过人工校对册审计")
    args = parser.parse_args(argv)
    if args.require_activation and args.skip_review:
        parser.error("--require-activation不能与--skip-review同时使用")
    root = Path(args.root).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else root / "dist"
    try:
        wheel = build_wheel(root, output_dir, timeout=args.timeout)
        runtime_template = sync_runtime_template(root, output_dir)
        review = None
        if not args.skip_review:
            if args.review_book is not None:
                review = args.review_book.resolve()
            else:
                review = _default_review_book(root)
        audit = audit_project(root, review_book=review, wheel=wheel)
        payload = {"wheel": str(wheel), "audit": asdict(audit)}
        if runtime_template is not None:
            payload["template"] = str(runtime_template)
        synced_review = sync_review_book(review, output_dir)
        if synced_review is not None:
            payload["review_book"] = str(synced_review)
        activation_gate = {"required": bool(args.require_activation), "ready": True, "blockers": []}
        if args.require_activation:
            review_checks = audit.checks.get("human_review_book") or {}
            activation_gate["ready"] = bool(review_checks.get("activation_ready"))
            activation_gate["blockers"] = list(review_checks.get("activation_blockers") or [])
            if not review_checks:
                activation_gate["blockers"] = ["未找到人工校对册或未执行校对册审计"]
        payload["activation_gate"] = activation_gate
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
        return 0 if audit.is_valid and activation_gate["ready"] else 1
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
