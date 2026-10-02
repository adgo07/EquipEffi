"""注入路径的控制台与轮转文件日志；不记录业务输入快照。"""
import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import TextIO

from ..config.logging import LoggingConfig


def configure_logging(config: LoggingConfig, *, stream: TextIO | None = None) -> logging.Logger:
    if config.level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("日志级别无效")
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("equipeffi")
    close_logging(logger)
    logger.setLevel(config.level)
    logger.propagate = False
    console = logging.StreamHandler(stream)
    file = RotatingFileHandler(config.logs_dir / "equipeffi.log", maxBytes=config.max_bytes,
                               backupCount=config.backup_count, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    for handler in (console, file):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def close_logging(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def install_exception_hook(logger: logging.Logger):
    previous = sys.excepthook

    def hook(exc_type, value, traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            previous(exc_type, value, traceback)
        else:
            logger.critical("未捕获的应用异常", exc_info=(exc_type, value, traceback))

    sys.excepthook = hook
    return previous
