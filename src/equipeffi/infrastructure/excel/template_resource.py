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

#: Phase 8 起 Windows V1 的**正式**用户模板（V4 退出正式用户模板，仅保留
#: legacy / test 兼容，本阶段不大规模删除旧实现）。
DEFAULT_V6_TEMPLATE = "设备能效分析空白模板_重构版V6_20261005.xlsx"

#: V6 正式模板身份。`source` 是 Owner 指定的模板基线（构建输入，只读）；
#: `source_sha256` 是入仓前基线的 SHA-256，用于证明资产来源与派生关系。
V6_TEMPLATE_IDENTITY: dict[str, str] = {
    "template_id": "equipeffi.device-efficiency.V6",
    "template_version": "V6-20261005",
    "template_kind": "unified-multi-device-blank-template",
    "filename": DEFAULT_V6_TEMPLATE,
    "source_filename": "设备能效分析空白模板_重构版V6_变压器.xlsx",
    "source_sha256": "FDB8C0B09925B5AE0EA0F0A941040B27890B5455E8E5920E02C409EDD4699CA1",
    "asset_sha256": "EE9DBE17A06081739CFB8EF0D330CE30B4634CBA5CE29CCD1EAB058D09348810",
    "generated_by": "tools/build_v6_pump_template.py",
    "authorized_modification": "离心泵",
    "provenance": (
        "Owner 指定 V6 统一模板基线经 Phase 8 授权修改（离心泵 Sheet 业务公式退出、"
        "类别枚举对齐 Application 契约）后入仓；其他 17 个 Sheet 语义不变，"
        "由 tools/check_v6_untouched_sheets.py 机械验证。"
    ),
}

#: V6 模板必须包含的 Sheet（顺序即正式顺序）。
REQUIRED_V6_SHEETS: tuple[str, ...] = (
    "变压器", "电动机", "空压机", "离心泵", "离心通风机", "轴流通风机", "鼓风机",
    "潜水电泵", "工业锅炉", "热处理设备", "热泵和冷水机组", "热泵热水机",
    "风管送风式空调", "单元式空调", "多联式空调", "注意事项", "模板说明", "配置",
)
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


class V6TemplateResource(V4TemplateResource):
    """正式 V6 统一模板资源（Phase 8 起 Windows V1 的正式用户模板）。

    复用 V4 的资源定位与"只复制、不写源文件"语义，只替换模板身份与结构契约。
    """

    def __init__(self, resource_dir: Path | None = None,
                 *, template_name: str = DEFAULT_V6_TEMPLATE):
        super().__init__(resource_dir, template_name=template_name)

    @property
    def identity(self) -> dict[str, str]:
        return dict(V6_TEMPLATE_IDENTITY)

    def validate(self, path: Path | None = None) -> TemplateValidationResult:
        candidate = path or self.template_path
        sheet_names = _workbook_sheet_names(candidate)
        missing = tuple(sheet for sheet in REQUIRED_V6_SHEETS if sheet not in sheet_names)
        digest = sha256(candidate.read_bytes()).hexdigest()
        valid = not missing
        message = "V6模板结构检查通过" if valid else f"缺少V6工作表：{'、'.join(missing)}"
        return TemplateValidationResult(str(candidate), digest, sheet_names, missing, valid, message)

    def download_to(self, destination: Path) -> Path:
        source = self.template_path.resolve()
        target = destination.resolve()
        if source == target:
            raise TemplateResourceError("下载目标不能覆盖内置V6模板")
        if not source.is_file():
            raise TemplateResourceError(f"内置V6模板不存在：{source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target
