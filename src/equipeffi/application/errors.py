"""应用层可由各平台适配器识别的错误类型。"""

from __future__ import annotations


class FeatureNotEnabledError(RuntimeError):
    """当前版本保留接口但尚未启用的功能。

    适配器不应把此类情况伪装成标准数据错误或系统故障；上层可以将
    ``feature``展示为“功能未启用”，并引导用户继续使用当前可用入口。
    """

    def __init__(self, feature: str, detail: str = "") -> None:
        self.feature = str(feature)
        self.detail = str(detail).strip()
        message = f"功能未启用：{self.feature}"
        if self.detail:
            message = f"{message}；{self.detail}"
        super().__init__(message)
