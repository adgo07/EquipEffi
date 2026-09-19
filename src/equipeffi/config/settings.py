"""与业务无关的运行配置占位。

标准数据目录、用户数据目录和日志目录将在基础设施层接入后集中管理。
"""

from dataclasses import dataclass
from pathlib import Path

from .. import __version__


@dataclass(frozen=True)
class Settings:
    app_name: str = "设备能效分析工具"
    app_version: str = __version__
    project_root: Path | None = None


DEFAULT_SETTINGS = Settings()
