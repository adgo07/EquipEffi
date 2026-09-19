from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib.resources as resources
from pathlib import Path
import shutil
import tempfile
from typing import Iterable
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


DEFAULT_V4_TEMPLATE = "设备能效分析空白模板_重构版V4_20260825.xlsx"
REQUIRED_V4_SHEETS: tuple[str, ...] = (
    "注意事项",
    "模板说明",
    "配置",
    "变压器",
    "电动机",
    "空压机",
    "离心泵",
    "离心通风机",
    "轴流通风机",
    "鼓风机",
    "潜水电泵",
    "工业锅炉",
    "热处理设备",
    "热泵和冷水机组",
    "热泵热水机",
    "风管送风式空调",
    "单元式空调",
    "多联式空调",
)


class TemplateResourceError(ValueError):
    """模板资源不存在、损坏或结构不符合V4契约。"""


@dataclass(frozen=True)
class TemplateValidationResult:
    path: str
    sha256: str
    sheet_names: tuple[str, ...]
    missing_sheets: tuple[str, ...]
    is_valid: bool
    message: str


def _workbook_sheet_names(path: Path) -> tuple[str, ...]:
    try:
        with ZipFile(path) as archive:
            xml = archive.read("xl/workbook.xml")
    except (BadZipFile, KeyError, OSError) as exc:
        raise TemplateResourceError(f"无法读取Excel工作簿结构：{exc}") from exc
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise TemplateResourceError(f"Excel工作簿结构XML无效：{exc}") from exc
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return tuple(str(node.attrib.get("name", "")) for node in root.findall("main:sheets/main:sheet", namespace) if node.attrib.get("name"))


class V4TemplateResource:
    """内置V4空白模板资源管理器。

    只复制模板，不在源文件上写入；Excel读取/回写由后续适配器负责。
    """

    def __init__(self, resource_dir: Path | None = None, *, template_name: str = DEFAULT_V4_TEMPLATE):
        self._temporary_resource_dir: tempfile.TemporaryDirectory[str] | None = None
        if resource_dir is not None:
            self.resource_dir = Path(resource_dir)
            self.template_path = self.resource_dir / template_name
            return

        filesystem_dir = Path(__file__).resolve().parents[2] / "resources" / "templates"
        filesystem_path = filesystem_dir / template_name
        if filesystem_path.is_file():
            self.resource_dir = filesystem_dir
            self.template_path = filesystem_path
            return

        # A wheel can be imported directly from a zip path (and some mobile
        # bridges use the same resource loader).  ``Path(__file__)`` is then
        # not a real filesystem path, so materialize only this small template
        # into a managed temporary directory.
        try:
            bundled = resources.files("equipeffi").joinpath("resources", "templates", template_name)
            if bundled.is_file():
                self._temporary_resource_dir = tempfile.TemporaryDirectory(prefix="equipeffi-template-")
                self.resource_dir = Path(self._temporary_resource_dir.name)
                self.template_path = self.resource_dir / template_name
                self.template_path.write_bytes(bundled.read_bytes())
                return
        except (FileNotFoundError, ModuleNotFoundError, OSError):
            pass
        self.resource_dir = filesystem_dir
        self.template_path = filesystem_path

    def fingerprint(self) -> str:
        if not self.template_path.is_file():
            raise TemplateResourceError(f"内置V4模板不存在：{self.template_path}")
        digest = sha256()
        with self.template_path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def validate(self, path: Path | None = None) -> TemplateValidationResult:
        candidate = path or self.template_path
        sheet_names = _workbook_sheet_names(candidate)
        missing = tuple(sheet for sheet in REQUIRED_V4_SHEETS if sheet not in sheet_names)
        digest = sha256(candidate.read_bytes()).hexdigest()
        valid = not missing
        message = "V4模板结构检查通过" if valid else f"缺少V4工作表：{'、'.join(missing)}"
        return TemplateValidationResult(str(candidate), digest, sheet_names, missing, valid, message)

    def download_to(self, destination: Path) -> Path:
        source = self.template_path.resolve()
        target = destination.resolve()
        if source == target:
            raise TemplateResourceError("下载目标不能覆盖内置V4模板")
        if not source.is_file():
            raise TemplateResourceError(f"内置V4模板不存在：{source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target
