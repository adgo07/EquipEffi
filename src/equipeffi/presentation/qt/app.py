"""Qt 生命周期与消息日志适配；依赖服务由外层注入。"""
import logging

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from ...application.services.settings_service import SettingsService
from .shell import MainWindow


def install_qt_message_handler(logger: logging.Logger):
    levels = {QtMsgType.QtDebugMsg: logging.DEBUG, QtMsgType.QtInfoMsg: logging.INFO,
              QtMsgType.QtWarningMsg: logging.WARNING, QtMsgType.QtCriticalMsg: logging.ERROR,
              QtMsgType.QtFatalMsg: logging.CRITICAL}

    def handler(kind, context, message):
        logger.log(levels.get(kind, logging.WARNING), "Qt: %s", message)

    return qInstallMessageHandler(handler)


def run(settings: SettingsService, logger: logging.Logger, analysis=None,
        *, workspace_id: str | None = None) -> int:
    application = QApplication.instance() or QApplication([])
    previous = install_qt_message_handler(logger)
    try:
        window = MainWindow(settings, analysis, workspace_id=workspace_id)
        window.show()
        return application.exec()
    finally:
        qInstallMessageHandler(previous)
