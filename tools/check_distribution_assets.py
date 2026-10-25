"""Inspect built distribution artifacts for runtime data completeness and source-standard leaks.

Runtime package data is declared once in pyproject.toml and consumed by setuptools,
zipapp, and native builds. This audit inspects actual wheel/sdist/zipapp/portable/native
outputs. It rejects PDFs in install artifacts regardless of path because user-generated
reports belong outside the package. It also recognizes common image signatures so renamed
scan pages cannot pass on filename alone.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from io import BytesIO
import json
from pathlib import Path
import re
import tarfile
import tomllib
from typing import Iterable
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
CORE_RUNTIME_ASSETS = frozenset(
    {
        "standard_manifest.json",
        "resources/TEMPLATE_MANIFEST.json",
        "resources/standards/pump.json",
        "resources/standards/gb20052_2024_v21.json",
        "resources/standards/gb18613_2020.json",
        "resources/templates/设备能效分析空白模板_重构版V6_20261005.xlsx",
        "resources/templates/设备能效分析空白模板_重构版V6_1.xlsx",
        "resources/templates/设备能效分析空白模板_重构版V6_2.xlsx",
    }
)
_SOURCE_PATH_PARTS = frozenset(
    {
        "标准原文",
        "标准原件",
        "扫描页",
        "原始标准",
        "standard-original",
        "standard-originals",
        "standard-source",
        "standard-sources",
        "source-standard",
        "source-standards",
        "source-pages",
        "scan-pages",
        "scans",
        "full-standard-text",
        "full-standard",
    }
)
_TEXT_SUFFIXES = frozenset({".txt", ".md", ".rst", ".html", ".htm", ".xml", ".json", ".rtf"})
_STANDARD_ID = re.compile(r"(?i)\bGB\s*/?\s*T?\s*[-_ ]?\d{4,5}\s*[-—_ ]?\s*\d{4}\b")
_SECTION_HEADING = re.compile(
    r"(?m)^\s*(?:第\s*[一二三四五六七八九十百0-9]+\s*章|[1-9](?:\.\d+)*[、.\s]+)"
    r"\s*(?:范围|规范性引用文件|术语和定义|术语|技术要求|能效等级|检验规则|试验方法)"
)
_STRONG_STANDARD_HEADERS = (
    "中华人民共和国国家标准",
    "国家标准化管理委员会",
    "国家市场监督管理总局",
    "national standard of the people's republic of china",
)
_PAGE_WORDS = ("本标准", "标准号", "标准名称", "发布", "实施", "代替", "范围", "规范性引用文件")


@dataclass(frozen=True)
class AssetAudit:
    path: str
    kind: str
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    checks: dict[str, object] = field(default_factory=dict)


def runtime_asset_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """Return files selected by the setuptools package-data declaration."""
    root = Path(root).resolve()
    pyproject = root / "pyproject.toml"
    package_root = root / "src" / "equipeffi"
    try:
        config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        patterns = config["tool"]["setuptools"]["package-data"]["equipeffi"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Cannot read runtime package-data declaration from {pyproject}: {exc}") from exc
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        raise ValueError("tool.setuptools.package-data.equipeffi must be a list of path patterns")
    package_root = package_root.resolve()
    selected: set[Path] = set()
    for pattern in patterns:
        for path in package_root.glob(pattern):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if not resolved.is_relative_to(package_root):
                raise ValueError(f"Runtime package-data path escapes src/equipeffi: {path}")
            selected.add(resolved)
    missing_core = sorted(
        CORE_RUNTIME_ASSETS
        - {path.relative_to(package_root).as_posix() for path in selected}
    )
    if missing_core:
        raise ValueError("Runtime package-data declaration omits required assets: " + ", ".join(missing_core))
    return tuple(sorted(selected, key=lambda item: item.relative_to(package_root).as_posix()))


def runtime_asset_members(root: Path = ROOT) -> dict[str, Path]:
    package_root = Path(root).resolve() / "src" / "equipeffi"
    return {
        f"equipeffi/{path.relative_to(package_root).as_posix()}": path
        for path in runtime_asset_paths(root)
    }


def _zip_magic(data: bytes) -> bool:
    return data.startswith(b"PK\x03\x04") or data.startswith(b"PK\x05\x06") or data.startswith(b"PK\x07\x08")


def _pdf_magic(data: bytes) -> bool:
    return b"%PDF-" in data[:1024]


def _image_kind(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith((b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")):
        return "tiff"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"BM"):
        return "bmp"
    if data.lstrip().startswith(b"<svg") or (data.lstrip().startswith(b"<?xml") and b"<svg" in data[:4096]):
        return "svg"
    return None


def _image_dimensions(data: bytes, kind: str) -> tuple[int, int] | None:
    if kind == "png" and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if kind == "jpeg":
        index = 2
        while index + 4 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                continue
            if index + 2 > len(data):
                break
            segment_length = int.from_bytes(data[index:index + 2], "big")
            if segment_length < 2 or index + segment_length > len(data):
                break
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height = int.from_bytes(data[index + 3:index + 5], "big")
                width = int.from_bytes(data[index + 5:index + 7], "big")
                return width, height
            index += segment_length
    return None


def _looks_like_page_scan(data: bytes, kind: str) -> bool:
    dimensions = _image_dimensions(data, kind)
    if not dimensions:
        return False
    width, height = dimensions
    if not width or not height or min(width, height) < 1000:
        return False
    ratio = width / height
    return 0.52 <= ratio <= 0.88 or 1.10 <= ratio <= 1.75


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("latin-1", errors="replace")


def _looks_like_full_standard_text(path: str, data: bytes) -> bool:
    suffix = Path(path.split("!", 1)[-1]).suffix.lower()
    if suffix not in _TEXT_SUFFIXES:
        return False
    text = _decode_text(data)
    if len(text) < 1200 or not _STANDARD_ID.search(text):
        return False
    lowered = text.lower()
    has_header = any(marker.lower() in lowered for marker in _STRONG_STANDARD_HEADERS)
    heading_count = len(_SECTION_HEADING.findall(text))
    has_standard_body = sum(word in text for word in _PAGE_WORDS) >= 3
    return has_header and (heading_count >= 2 or (heading_count >= 1 and has_standard_body))


def _path_parts(path: str) -> tuple[str, ...]:
    return tuple(
        part.casefold().replace("_", "-").replace(" ", "-")
        for layer in path.replace("\\", "/").split("!")
        for part in layer.strip("/").split("/")
        if part
    )


def _is_source_path(path: str) -> bool:
    parts = _path_parts(path)
    if any(part in _SOURCE_PATH_PARTS for part in parts):
        return True
    # A national-standard ID in a PDF/image filename is a strong source-document cue.
    leaf = parts[-1] if parts else ""
    if _STANDARD_ID.search(leaf) and _pdf_or_image_path(path):
        return True
    return False


def _pdf_or_image_path(path: str) -> bool:
    suffix = Path(path.split("!", 1)[-1]).suffix.lower()
    return suffix in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp", ".gif", ".svg"}


def _runtime_resource_relative(path: str) -> str | None:
    for layer in path.split("!"):
        normalized = layer.replace("\\", "/")
        marker = "equipeffi/resources/"
        index = normalized.rfind(marker)
        if index >= 0:
            return normalized[index + len(marker):].strip("/")
    return None


def _has_member_for_asset(members: Iterable[str], member: str) -> bool:
    suffixes = (member, "src/" + member)
    for path in members:
        for layer in path.split("!"):
            normalized = layer.replace("\\", "/").strip("/")
            if any(normalized == suffix or normalized.endswith("/" + suffix) for suffix in suffixes):
                return True
    return False


def _collect_zip(data: bytes, prefix: str, found: list[tuple[str, bytes]], depth: int = 0) -> None:
    if depth > 6 or not _zip_magic(data):
        return
    try:
        with ZipFile(BytesIO(data)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                payload = archive.read(info)
                member_path = f"{prefix}!{info.filename}" if prefix else info.filename
                found.append((member_path, payload))
                if _zip_magic(payload):
                    _collect_zip(payload, member_path, found, depth + 1)
    except (BadZipFile, OSError, RuntimeError):
        return


def _collect_tar(data: bytes, prefix: str, found: list[tuple[str, bytes]]) -> None:
    try:
        with tarfile.open(fileobj=BytesIO(data), mode="r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    continue
                payload = stream.read()
                member_path = f"{prefix}!{member.name}" if prefix else member.name
                found.append((member_path, payload))
                if _zip_magic(payload):
                    _collect_zip(payload, member_path, found, 1)
    except (tarfile.TarError, OSError):
        return


def _artifact_members(path: Path) -> list[tuple[str, bytes]]:
    if path.is_dir():
        found: list[tuple[str, bytes]] = []
        for item in sorted(path.rglob("*")):
            if not item.is_file() or item.is_symlink():
                continue
            relative = item.relative_to(path).as_posix()
            data = item.read_bytes()
            found.append((relative, data))
            if _zip_magic(data):
                _collect_zip(data, relative, found, 1)
        return found
    if not path.is_file():
        raise FileNotFoundError(path)
    data = path.read_bytes()
    found = [(path.name, data)]
    if _zip_magic(data):
        _collect_zip(data, "", found)
    elif tarfile.is_tarfile(path):
        _collect_tar(data, "", found)
    return found


def _kind(path: Path) -> str:
    if path.is_dir():
        return "native-directory"
    name = path.name.lower()
    if name.endswith(".whl"):
        return "wheel"
    if name.endswith((".tar.gz", ".tar.bz2", ".tgz")):
        return "sdist"
    if name.endswith(".pyz"):
        return "zipapp"
    if name.endswith(".zip"):
        return "bundle-or-native-zip"
    return "file"


def audit_artifact(path: Path, *, root: Path = ROOT) -> AssetAudit:
    path = Path(path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, object] = {"member_count": 0, "runtime_asset_count": 0}
    try:
        declared_assets = runtime_asset_members(root)
        asset_names = set(declared_assets)
        required_names = set(asset_names)
        checks["declared_runtime_assets"] = sorted(asset_names)
        missing_core = sorted(
            CORE_RUNTIME_ASSETS
            - {name.removeprefix("equipeffi/") for name in asset_names}
        )
        if missing_core:
            raise ValueError("pyproject runtime package-data omits core assets: " + ", ".join(missing_core))
        members = _artifact_members(path)
    except (OSError, ValueError, tarfile.TarError) as exc:
        return AssetAudit(str(path), _kind(path), False, (str(exc),), (), checks)

    names = [name for name, _ in members]
    checks["member_count"] = len(members)
    missing_assets = [
        name for name in sorted(required_names)
        if not _has_member_for_asset(names, name)
    ]
    checks["missing_runtime_assets"] = missing_assets
    if missing_assets:
        errors.append("产物缺少 pyproject.toml 声明的运行资源: " + ", ".join(missing_assets))
    checks["runtime_asset_count"] = len(required_names)

    unexpected_resources: list[str] = []
    source_findings: list[str] = []
    allowed_report_pdfs: list[str] = []
    for member_path, data in members:
        resource_relative = _runtime_resource_relative(member_path)
        if resource_relative is not None and resource_relative not in {
            name.removeprefix("equipeffi/resources/") for name in asset_names
        }:
            unexpected_resources.append(member_path)

        image_kind = _image_kind(data[: min(len(data), 2_000_000)])
        pdf = _pdf_magic(data)
        source_path = _is_source_path(member_path)
        full_text = _looks_like_full_standard_text(member_path, data[: min(len(data), 2_000_000)])

        if full_text:
            source_findings.append(f"{member_path}: 检测到标准号、国家标准标题及多条正文结构")
        elif source_path and (pdf or image_kind or Path(member_path.split("!", 1)[-1]).suffix.lower() in _TEXT_SUFFIXES):
            source_findings.append(f"{member_path}: 路径表明其为标准原件/扫描页来源")
        elif pdf:
            # Runtime-generated reports are user output, not install-package assets.
            # No PDF examples are currently approved for distribution, so paths cannot
            # create an exception. A future package asset needs an explicit allowlist.
            source_findings.append(f"{member_path}: PDF不在显式批准的随包资产清单中")
        elif image_kind and _looks_like_page_scan(data, image_kind):
            source_findings.append(f"{member_path}: {image_kind} 图像具有高分辨率标准页比例")

    if unexpected_resources:
        errors.append("运行包含有 pyproject.toml 未声明的 resources 文件: " + ", ".join(sorted(unexpected_resources)))
    if source_findings:
        errors.append("产物包含未批准的标准原件、扫描页、PDF或完整原文: " + "; ".join(sorted(source_findings)))
    checks["unexpected_runtime_resources"] = sorted(unexpected_resources)
    checks["standard_source_findings"] = sorted(source_findings)
    checks["allowed_report_pdfs"] = sorted(allowed_report_pdfs)
    return AssetAudit(str(path), _kind(path), not errors, tuple(errors), tuple(warnings), checks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查 wheel/sdist/zipapp/便携/native 实际产物的运行资源与标准原件")
    parser.add_argument("artifacts", nargs="+", type=Path, help="一个或多个构建产物或 native 输出目录")
    parser.add_argument("--root", type=Path, default=ROOT, help="含 pyproject.toml 与 src/equipeffi 的源码根目录")
    args = parser.parse_args(argv)
    results = [audit_artifact(path, root=args.root) for path in args.artifacts]
    print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
    return 0 if all(result.is_valid for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
