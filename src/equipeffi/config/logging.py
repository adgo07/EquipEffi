"""外层日志初始化契约；不是业务 Record Audit。"""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoggingConfig:
    logs_dir: Path
    level: str = "INFO"
    max_bytes: int = 2 * 1024 * 1024
    backup_count: int = 3
