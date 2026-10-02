"""正式外层装配入口。

核心判定不需要读取V4工作簿，也不应因启动JSON/JSONL服务而触发Excel
资源解析。模板契约作为可选能力由本模块按需加载，供CLI、桌面和Web
展示层复用同一套服务构造逻辑。
"""
from __future__ import annotations

import logging
from pathlib import Path
from xml.etree.ElementTree import ParseError
from typing import Any

from .infrastructure.standards.json_repository import JsonStandardRepository
from .presentation.api.application_api import ApplicationApi
from .application.services.evaluation_facade import EvaluationFacade
from .application.services.evaluation_service import EvaluationService


def _default_project_root() -> Path:
    """Locate the source/project root for a checkout or an installed package."""

    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "standard_manifest.json").is_file():
            return candidate
        if (candidate / "src/equipeffi/standard_manifest.json").is_file():
            return candidate
    return Path.cwd().resolve()


def load_v4_contract() -> tuple[Any, Any] | tuple[None, None]:
    """Load the packaged V4 contract only when a presentation layer needs it.

    The returned resource manager is kept alongside the contract so a package
    imported from a zip file retains the temporary materialized workbook for
    the lifetime of the caller.  A missing or invalid template is intentionally
    represented by ``(None, None)``; the public API has a dependency-free
    fallback schema for manual/JSON input.
    """

    # These imports are deliberately local: importing the core API must not
    # initialize the Excel/template adapter or inspect an XLSX file.
    from .infrastructure.excel.template_resource import V4TemplateResource
    from .infrastructure.excel.v4_reader import V4WorkbookReaderImpl
    from .infrastructure.excel.ooxml_reader import OOXMLReadError
    from .infrastructure.excel.template_resource import TemplateResourceError

    try:
        template_resource = V4TemplateResource()
        contract = V4WorkbookReaderImpl().read_contract(template_resource.template_path)
    except (OOXMLReadError, TemplateResourceError, OSError, ParseError) as exc:
        logging.getLogger("equipeffi.composition").warning("V4 契约加载失败，保留兼容回退：%s", exc)
        return None, None
    return contract, template_resource


def create_core_api(*, project_root: Path | None = None) -> ApplicationApi:
    """Create the core JSON/API service without loading the V4 workbook."""

    root = Path(project_root).resolve() if project_root is not None else _default_project_root()
    package_manifest = Path(__file__).resolve().parent / "standard_manifest.json"
    if package_manifest.is_file():
        repository = JsonStandardRepository(package_manifest.parent, manifest=package_manifest)
    else:
        repository = JsonStandardRepository(root)
    facade = EvaluationFacade(EvaluationService(repository))
    return ApplicationApi(facade)


def create_application_api(
    *,
    project_root: Path | None = None,
    load_template: bool = False,
) -> tuple[ApplicationApi, Any, Any]:
    """Create an API and optionally attach the parsed V4 contract.

    Returns ``(api, contract, resource_manager)``.  The latter two values are
    exposed so a desktop/Web caller can retain the resource manager when a
    wheel is imported directly from a zip archive.  Existing callers that only
    need JSON evaluation should use the default ``load_template=False``.
    """

    root = Path(project_root).resolve() if project_root is not None else _default_project_root()
    package_manifest = Path(__file__).resolve().parent / "standard_manifest.json"
    if package_manifest.is_file():
        repository = JsonStandardRepository(package_manifest.parent, manifest=package_manifest)
    else:
        repository = JsonStandardRepository(root)
    contract = resource_manager = None
    if load_template:
        contract, resource_manager = load_v4_contract()
    facade = EvaluationFacade(EvaluationService(repository), contract=contract)
    return ApplicationApi(facade, contract=contract), contract, resource_manager


def create_settings_runtime(*, paths=None, stream=None):
    """唯一 Phase 2 切片装配；不实例化旧 SQLite 空桩或评价服务。"""
    from . import __version__
    from .application.services.settings_service import SettingsService
    from .config.logging import LoggingConfig
    from .infrastructure.persistence.app_data_paths import AppDataPaths
    from .infrastructure.persistence.migrations import migrate_user_database
    from .infrastructure.persistence.sqlite_settings_repository import SqliteSettingsRepository
    from .infrastructure.runtime_logging import configure_logging

    paths = paths if paths is not None else AppDataPaths.default()
    migrate_user_database(paths.user_db, app_version=__version__)
    service = SettingsService(SqliteSettingsRepository(paths.user_db))
    logger = configure_logging(LoggingConfig(paths.logs_dir, service.get("log.level", "INFO")), stream=stream)
    return service, logger


def launch_qt(*, paths=None) -> int:
    from .infrastructure.runtime_logging import close_logging, install_exception_hook
    from .presentation.qt.app import run
    import sys

    service, logger = create_settings_runtime(paths=paths)
    previous = install_exception_hook(logger)
    try:
        return run(service, logger)
    finally:
        sys.excepthook = previous
        close_logging(logger)
