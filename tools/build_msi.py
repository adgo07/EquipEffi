"""生成并（在目标机具备 WiX 时）构建 EquipEffi 正式 MSI。

本工具只接受已经验收过的 Windows onedir 目录，不重新打包 Python 或
标准数据。当前开发环境未必安装 WiX，因此 --dry-run 可先生成确定性
WiX 源文件和报告；正式构建时使用 WiX v4 的 wix build。
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Iterable, Sequence
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
WIX_NS = "http://wixtoolset.org/schemas/v4/wxs"
ET.register_namespace("", WIX_NS)
UPGRADE_CODE = "{6B2F0B7D-7B89-4B0C-9B0E-0CC9E7F1B3A8}"


def _tag(name: str) -> str:
    return f"{{{WIX_NS}}}{name}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_files(native_dir: Path) -> list[Path]:
    """返回稳定排序的普通文件，并拒绝目录逃逸。"""

    native_dir = native_dir.resolve()
    if not native_dir.is_dir():
        raise FileNotFoundError(f"Windows onedir目录不存在：{native_dir}")
    executable = native_dir / "equipeffi.exe"
    if not executable.is_file():
        raise FileNotFoundError(f"Windows onedir目录缺少入口：{executable}")
    files: list[Path] = []
    for path in native_dir.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        try:
            resolved.relative_to(native_dir)
        except ValueError as exc:
            raise ValueError(f"发现目录外文件：{path}") from exc
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(native_dir).as_posix().lower())


def _stable_id(prefix: str, relative: str) -> str:
    digest = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}_{digest}"


def _directory_tree(root: ET.Element, relative_dirs: Iterable[str]) -> dict[str, str]:
    """在 ProgramFilesFolder 下建立稳定的 WiX 目录 ID 树。"""

    standard = ET.SubElement(root, _tag("Fragment"))
    program = ET.SubElement(standard, _tag("StandardDirectory"), {"Id": "ProgramFilesFolder"})
    install = ET.SubElement(program, _tag("Directory"), {"Id": "INSTALLFOLDER", "Name": "EquipEffi"})
    mapping = {"": "INSTALLFOLDER"}
    elements = {"": install}
    for relative in sorted(set(relative_dirs), key=lambda item: (item.count("/"), item.lower())):
        parts = [part for part in relative.split("/") if part]
        parent = ""
        for part in parts:
            current = f"{parent}/{part}".strip("/")
            if current in elements:
                parent = current
                continue
            directory_id = _stable_id("DIR", current)
            elements[current] = ET.SubElement(
                elements[parent],
                _tag("Directory"),
                {"Id": directory_id, "Name": part},
            )
            mapping[current] = directory_id
            parent = current
    return mapping


def generate_wix_source(native_dir: Path, wix_source: Path, *, version: str = "0.2.1") -> dict[str, Any]:
    """为已构建的 Windows onedir 目录生成 WiX v4 XML 源文件。"""

    native_dir = Path(native_dir).resolve()
    files = _safe_files(native_dir)
    root = ET.Element(_tag("Wix"))
    package = ET.SubElement(
        root,
        _tag("Package"),
        {
            "Name": "EquipEffi 设备能效分析",
            "Manufacturer": "EquipEffi",
            "Version": version,
            "UpgradeCode": UPGRADE_CODE,
            "Scope": "perMachine",
            "Compressed": "yes",
        },
    )
    ET.SubElement(package, _tag("MajorUpgrade"), {"DowngradeErrorMessage": "已安装更高版本的EquipEffi，不能安装旧版本。"})
    ET.SubElement(package, _tag("MediaTemplate"), {"EmbedCab": "yes"})
    feature = ET.SubElement(package, _tag("Feature"), {"Id": "MainFeature", "Title": "EquipEffi", "Level": "1"})
    ET.SubElement(feature, _tag("ComponentGroupRef"), {"Id": "ProductComponents"})

    relative_dirs = {
        path.relative_to(native_dir).parent.as_posix()
        for path in files
        if path.relative_to(native_dir).parent.as_posix() not in ("", ".")
    }
    directories = _directory_tree(root, relative_dirs)
    components_fragment = ET.SubElement(root, _tag("Fragment"))
    group = ET.SubElement(components_fragment, _tag("ComponentGroup"), {"Id": "ProductComponents"})
    component_ids: list[str] = []
    for path in files:
        relative = path.relative_to(native_dir).as_posix()
        parent = path.relative_to(native_dir).parent.as_posix()
        directory_id = directories.get("" if parent in ("", ".") else parent)
        if not directory_id:
            raise ValueError(f"无法为文件定位WiX目录：{relative}")
        component_id = _stable_id("CMP", relative)
        file_id = _stable_id("FIL", relative)
        component_ids.append(component_id)
        component = ET.SubElement(
            components_fragment,
            _tag("Component"),
            {"Id": component_id, "Directory": directory_id, "Guid": "*"},
        )
        ET.SubElement(
            component,
            _tag("File"),
            {"Id": file_id, "Source": path.as_posix(), "KeyPath": "yes"},
        )
        ET.SubElement(group, _tag("ComponentRef"), {"Id": component_id})

    wix_source = Path(wix_source).resolve()
    wix_source.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(wix_source, encoding="utf-8", xml_declaration=True)
    return {
        "native_dir": str(native_dir),
        "wix_source": str(wix_source),
        "file_count": len(files),
        "component_count": len(component_ids),
        "executable": str(native_dir / "equipeffi.exe"),
        "executable_sha256": _sha256(native_dir / "equipeffi.exe"),
        "wix_source_sha256": _sha256(wix_source),
        "upgrade_code": UPGRADE_CODE,
        "version": version,
    }


@dataclass(frozen=True)
class MsiBuildResult:
    output: Path
    wix_source: Path
    report: Path
    built: bool
    details: dict[str, Any]


def build_msi(
    native_dir: Path,
    output: Path,
    *,
    wix_source: Path | None = None,
    report: Path | None = None,
    version: str = "0.2.1",
    wix_executable: str = "wix",
    dry_run: bool = False,
) -> MsiBuildResult:
    output = Path(output).resolve()
    source = Path(wix_source).resolve() if wix_source else output.with_suffix(".wxs")
    report_path = Path(report).resolve() if report else output.with_suffix(".json")
    details = generate_wix_source(native_dir, source, version=version)
    details.update({
        "output": str(output),
        "dry_run": dry_run,
        "wix_executable": wix_executable,
        "wix_available": shutil.which(wix_executable) is not None,
    })
    built = False
    if not dry_run:
        tool = shutil.which(wix_executable)
        if tool is None:
            details["blocked_reason"] = "未找到WiX v4命令wix；已生成WXS源，未伪造MSI"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(details, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
            raise RuntimeError(details["blocked_reason"])
        output.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [tool, "build", str(source), "-o", str(output)],
            cwd=source.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        details.update({
            "wix_returncode": completed.returncode,
            "wix_stdout": completed.stdout[-4000:],
            "wix_stderr": completed.stderr[-4000:],
        })
        if completed.returncode != 0:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(details, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
            raise RuntimeError(f"WiX构建失败，返回码{completed.returncode}")
        built = output.is_file()
        if not built:
            raise RuntimeError(f"WiX命令返回成功但未生成MSI：{output}")
        details["msi_sha256"] = _sha256(output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(details, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    return MsiBuildResult(output, source, report_path, built, details)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成或构建EquipEffi WiX v4 MSI")
    parser.add_argument("--native-dir", type=Path, required=True, help="已验收的Windows onedir目录")
    parser.add_argument("--output", type=Path, required=True, help="MSI输出路径")
    parser.add_argument("--wxs-output", type=Path, help="可选：WXS源输出路径")
    parser.add_argument("--report", type=Path, help="可选：构建报告路径")
    parser.add_argument("--version", default="0.2.1")
    parser.add_argument("--wix", default="wix", help="WiX v4命令路径或名称")
    parser.add_argument("--dry-run", action="store_true", help="只生成WXS和报告，不调用WiX")
    args = parser.parse_args(argv)
    try:
        result = build_msi(
            args.native_dir,
            args.output,
            wix_source=args.wxs_output,
            report=args.report,
            version=args.version,
            wix_executable=args.wix,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, RuntimeError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "built": result.built,
        "output": str(result.output),
        "wix_source": str(result.wix_source),
        "report": str(result.report),
        "file_count": result.details["file_count"],
        "wix_available": result.details["wix_available"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
