"""正式产品运行时装配入口。"""
from __future__ import annotations

from pathlib import Path

from .infrastructure.standards.json_repository import JsonStandardRepository


def _default_project_root() -> Path:
    """Locate the source/project root for a checkout or an installed package."""

    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "standard_manifest.json").is_file():
            return candidate
        if (candidate / "src/equipeffi/standard_manifest.json").is_file():
            return candidate
    return Path.cwd().resolve()


def _create_standard_repository(project_root: Path | None = None) -> JsonStandardRepository:
    """Create a fresh standard repository using the shared package-first rule."""

    root = Path(project_root).resolve() if project_root is not None else _default_project_root()
    package_manifest = Path(__file__).resolve().parent / "standard_manifest.json"
    if package_manifest.is_file():
        return JsonStandardRepository(package_manifest.parent, manifest=package_manifest)
    return JsonStandardRepository(root)


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


def create_records_runtime(*, paths=None):
    """Phase 3 记录运行时：迁移并装配 records.sqlite 的 Workspace / Record 仓储。

    与 `create_settings_runtime` 的 `user.sqlite` 迁移链**完全独立**；records 使用
    自己的 forward-only runner 与自己的历史表。
    """

    from . import __version__
    from .infrastructure.persistence.app_data_paths import AppDataPaths
    from .infrastructure.persistence.records_migrations import migrate_records_database
    from .infrastructure.persistence.sqlite_records_repository import (
        SqliteRecordRepository,
        SqliteWorkspaceRepository,
    )

    paths = paths if paths is not None else AppDataPaths.default()
    migrate_records_database(paths.records_db, app_version=__version__)
    return (
        SqliteWorkspaceRepository(paths.records_db),
        SqliteRecordRepository(paths.records_db),
    )


def create_pump_analysis_service(*, paths=None, with_persistence: bool = True):
    """装配统一 GB 19762 离心泵分析服务。

    with_persistence=True 时接入 records.sqlite 的 Workspace / Record 仓储。
    """

    from . import __version__
    from .application.services.centrifugal_pump_analysis_service import (
        CentrifugalPumpAnalysisService,
    )

    repository = _create_standard_repository()

    workspaces = records = None
    if with_persistence:
        workspaces, records = create_records_runtime(paths=paths)
    return CentrifugalPumpAnalysisService(
        repository, workspaces, records, version=__version__
    )


def create_transformer_analysis_service(*, paths=None, with_persistence: bool = True):
    """GB20052正式同核入口；只读取派生包，不依赖标准原件。"""
    from . import __version__
    from .application.services.transformer_analysis_service import TransformerAnalysisService
    from .domain.devices.transformer.calculator import TransformerCalculator
    from .infrastructure.standards.transformer_repository import load_transformer_pack

    pack, digest = load_transformer_pack()
    records = create_records_runtime(paths=paths)[1] if with_persistence else None
    return TransformerAnalysisService(pack, TransformerCalculator(), records=records,
                                      pack_sha256=digest, app_version=__version__)


def motor_candidate_enabled() -> bool:
    """兼容旧开关；默认开放电机，显式 0 保留旧版关闭行为。"""
    import os
    return os.environ.get("EQUIPEFFI_ENABLE_MOTOR_CANDIDATE", "1") == "1"


def create_motor_analysis_service(*, paths=None, with_persistence: bool = True):
    from . import __version__
    from .application.services.motor_analysis_service import MotorAnalysisService
    from .domain.devices.motor.calculator import Gb18613MotorCalculator
    from .infrastructure.standards.motor_repository import load_motor_pack

    pack, digest = load_motor_pack()
    records = create_records_runtime(paths=paths)[1] if with_persistence else None
    return MotorAnalysisService(pack, Gb18613MotorCalculator(), records=records,
                                pack_sha256=digest, app_version=__version__)


def create_batch_evaluation_service(*, paths=None, motor_candidate: bool | None = None):
    """创建正式 Excel 批量评价服务，与单台分析复用同一个分析服务。"""

    from .application.services.workbook_evaluation_service import WorkbookEvaluationService
    from . import __version__
    from .infrastructure.excel.unified_result_writer import UnifiedResultWorkbookWriter
    from .infrastructure.excel.unified_workbook_reader import UnifiedWorkbookReader
    from .infrastructure.excel.template_resource import (
        V61_TEMPLATE_IDENTITY,
        V61TransformerTemplateResource,
    )
    from .infrastructure.persistence.app_data_paths import AppDataPaths
    from .infrastructure.persistence.sqlite_batch_record_repository import (
        SqliteBatchRecordRepository,
    )

    paths = paths if paths is not None else AppDataPaths.default()
    analysis = create_pump_analysis_service(paths=paths)
    enabled = motor_candidate_enabled() if motor_candidate is None else motor_candidate
    template_identity = V61_TEMPLATE_IDENTITY
    template_resource = V61TransformerTemplateResource()
    if enabled:
        from .infrastructure.excel.template_resource import V62_TEMPLATE_IDENTITY, V62MotorTemplateResource
        template_identity = V62_TEMPLATE_IDENTITY
        template_resource = V62MotorTemplateResource()
    # 载体端口在装配层注入：Application 只认识 Protocol，不认识 Excel。
    return WorkbookEvaluationService(
        analysis,
        create_transformer_analysis_service(with_persistence=False),
        motor=create_motor_analysis_service(with_persistence=False) if enabled else None,
        reader=UnifiedWorkbookReader(),
        writer=UnifiedResultWorkbookWriter(),
        batch_repository=SqliteBatchRecordRepository(paths.records_db),
        template_identity=template_identity,
        template_resource=template_resource,
        app_version=__version__)


def launch_qt(*, paths=None) -> int:
    from .infrastructure.runtime_logging import close_logging, install_exception_hook
    from .presentation.qt.app import run
    from .infrastructure.external_launch import external_launch_environment
    import sys

    from .infrastructure.persistence.app_data_paths import AppDataPaths

    # 解析真实数据目录并传递给设置页。
    resolved = paths if paths is not None else AppDataPaths.default()
    service, logger = create_settings_runtime(paths=resolved)
    analysis = create_pump_analysis_service(paths=resolved)
    transformer = create_transformer_analysis_service(paths=resolved)
    motor = create_motor_analysis_service(paths=resolved) if motor_candidate_enabled() else None
    # 批量评价复用同一个正式分析服务。
    batch = create_batch_evaluation_service(paths=resolved)
    previous = install_exception_hook(logger)
    try:
        return run(service, logger, analysis, batch=batch,
                   transformer=transformer, motor=motor,
                   data_location=resolved.root,
                   external_launch_context=external_launch_environment)
    finally:
        sys.excepthook = previous
        close_logging(logger)
