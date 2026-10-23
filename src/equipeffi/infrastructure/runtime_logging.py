"""注入路径的控制台与轮转文件日志；不记录业务输入快照。"""
import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import TextIO

from ..config.logging import LoggingConfig


def configure_logging(config: LoggingConfig, *, stream: TextIO | None = None) -> logging.Logger:
    if config.level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("日志级别无效")
    logger = logging.getLogger("equipeffi")
    close_logging(logger)
    logger.setLevel(config.level)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    console = logging.StreamHandler(stream)
    console.setFormatter(formatter)
    logger.addHandler(console)

    try:
        config.logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        _warn_console_only(
            logger,
            console,
            "无法创建日志目录 %s（%s），将仅写入控制台日志。",
            config.logs_dir,
            error,
        )
        return logger

    log_path = config.logs_dir / "equipeffi.log"
    try:
        file = RotatingFileHandler(
            log_path,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8",
        )
    except OSError as error:
        _warn_console_only(
            logger,
            console,
            "无法打开日志文件 %s（%s），将仅写入控制台日志。",
            log_path,
            error,
        )
        return logger

    file.setFormatter(formatter)
    logger.addHandler(file)
    return logger


def _warn_console_only(
    logger: logging.Logger,
    console: logging.Handler,
    message: str,
    *args,
) -> None:
    """即使应用日志级别高于 WARNING，也把文件日志故障明确写到控制台。"""

    record = logger.makeRecord(
        logger.name, logging.WARNING, __file__, 0, message, args, None
    )
    console.handle(record)


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
