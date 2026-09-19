"""跨平台浏览器窗口层；判定逻辑仍由ApplicationApi提供。"""

from .server import TemplateTransferPort, create_server, run_web

__all__ = ["TemplateTransferPort", "create_server", "run_web"]
